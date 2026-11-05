"""Read-only 30-case regression with AWS CLI transport when local Python SDK DNS fails."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from uuid import uuid4
import subprocess,os,json,io,csv,time,hashlib,base64,zipfile,sys,re,argparse
from boto3.dynamodb.types import TypeDeserializer
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.stdout.reconfigure(encoding='utf-8')
from policy_assistant.service import Service
from policy_assistant import assistant
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--candidate',action='store_true',help='Permit a local assistant.py candidate; all other runtime modules must match deployment.')
parser.add_argument('--cases',help='Comma-separated fixture IDs; default all 30.')
parser.add_argument('--repeats',type=int,choices=range(1,4),default=1)
args=parser.parse_args()
run_id=datetime.now(timezone(timedelta(hours=7))).strftime('%Y%m%d-%H%M%S')
OUT=ROOT/'.deployment'/('retail-cli-'+run_id);OUT.mkdir()
child_env=os.environ.copy();child_env.update({'AWS_MAX_ATTEMPTS':'1','AWS_PAGER':'','PYTHONIOENCODING':'utf-8','AWS_CLI_FILE_ENCODING':'UTF-8','AWS_CLI_OUTPUT_ENCODING':'UTF-8'})
sequence=0

def cli(service,operation,data=None,region='ap-southeast-1',outfile=None):
    global sequence
    sequence+=1
    req=OUT/f'request-{sequence}.json'
    req.write_text(json.dumps(data or {},ensure_ascii=True),encoding='ascii')
    if service=='bedrock-runtime' and operation=='invoke-model':
        body=OUT/f'body-{sequence}.json'
        value=data['body']
        body.write_bytes(value if isinstance(value,bytes) else value.encode('utf-8'))
        command=['aws',service,operation,'--model-id',data['modelId'],'--body','fileb://'+str(body),'--content-type',data['contentType'],'--accept',data['accept']]
    else:
        command=['aws',service,operation,'--cli-input-json','file://'+str(req)]
        if service=='bedrock-runtime': command+=['--model-id',data['modelId']]
    command+=['--region',region,'--output','json','--cli-connect-timeout','5','--cli-read-timeout','25','--no-cli-pager']
    if operation=='scan': command+=['--no-paginate']
    if outfile: command+=[str(outfile)]
    result=subprocess.run(command,capture_output=True,env=child_env,timeout=40)
    if result.returncode:
        raise RuntimeError('AWS CLI '+service+'/'+operation+' failed: '+result.stderr.decode('utf-8',errors='replace')[:250])
    return json.loads(result.stdout.decode('utf-8-sig')) if result.stdout.strip() else {}

stack=cli('cloudformation','describe-stacks',{'StackName':'policy-assistant'})['Stacks'][0]
if stack['StackStatus']!='UPDATE_COMPLETE' or stack['StackId'].split(':')[4]!='629380420098': raise RuntimeError('Wrong stack or state')
fn=cli('cloudformation','describe-stack-resource',{'StackName':'policy-assistant','LogicalResourceId':'PolicyAssistantFunction'})['StackResourceDetail']['PhysicalResourceId']
config=cli('lambda','get-function-configuration',{'FunctionName':fn})
release=json.loads((ROOT/'.deployment/release.json').read_text(encoding='utf-8'))
archive=ROOT/'.deployment/lambda.zip'
if config['CodeSha256']!=base64.b64encode(bytes.fromhex(release['code_sha256'])).decode() or hashlib.sha256(archive.read_bytes()).hexdigest()!=release['code_sha256']: raise RuntimeError('Code drift')
with zipfile.ZipFile(archive) as z:
    for module in (ROOT/'policy_assistant').glob('*.py'):
        if z.read(module.name)!=module.read_bytes() and not (args.candidate and module.name=='assistant.py'): raise RuntimeError('Source drift: '+module.name)
env=config['Environment']['Variables']
for key in ['EMBEDDING_MODEL_ID','BEDROCK_MODEL_ID','REQUIRE_PUBLISHED_POLICIES','BEDROCK_GENERATION_REGION','BEDROCK_REASONING_EFFORT']: os.environ[key]=env[key]
if env['BEDROCK_MODEL_ID']!='jp.amazon.nova-2-lite-v1:0' or env['BEDROCK_GENERATION_REGION']!='ap-northeast-1': raise RuntimeError('Expected Japan model route')
deserialize=TypeDeserializer().deserialize
class Policies:
    name=env['POLICIES_TABLE_NAME']
    def scan(self,**kwargs):
        request={'TableName':self.name,'ConsistentRead':kwargs.get('ConsistentRead',False),'Limit':kwargs['Limit'],'ProjectionExpression':kwargs['ProjectionExpression'],'ExpressionAttributeNames':kwargs['ExpressionAttributeNames']}
        if kwargs.get('FilterExpression') is not None:
            request.update(FilterExpression='publication_state = :published',ExpressionAttributeValues={':published':{'S':'published'}})
        response=cli('dynamodb','scan',request)
        response['Items']=[{k:deserialize(v) for k,v in item.items()} for item in response.get('Items',[])]
        return response
class NoPrivateDocuments:
    def query(self,**kwargs): return {'Items':[]}
class History:
    def put_item(self,**kwargs): pass
class Runtime:
    def __init__(self,region): self.region=region;self.usage={};self.last_response={}
    def invoke_model(self,**kwargs):
        response_path=OUT/('embedding-'+uuid4().hex+'.json')
        cli('bedrock-runtime','invoke-model',kwargs,self.region,response_path)
        return {'body':io.BytesIO(response_path.read_bytes())}
    def converse(self,**kwargs):
        response=cli('bedrock-runtime','converse',kwargs,self.region)
        self.usage=response.get('usage',{})
        self.last_response={'stopReason':response.get('stopReason'),'text':''.join(block.get('text','') for block in response.get('output',{}).get('message',{}).get('content',[]))}
        return response
class Probe(Service):
    def __init__(self):
        self.region='ap-southeast-1';self.docs=NoPrivateDocuments();self.policies=Policies();self.history=History();self.generator=Runtime('ap-northeast-1');self._clients={'bedrock-runtime':Runtime('ap-southeast-1'),'bedrock-generation':self.generator}
    def save_answer(self,owner,item,response_ms):
        # Isolated model probe must never persist history or global quality totals.
        self.history.put_item(Item=item)
    def quota(self,*args): pass
    def table(self,name):
        if name!='HISTORY_TABLE_NAME': raise RuntimeError('Unexpected write target')
        return self.history
service=Probe();owner='internal-cli-regression-'+uuid4().hex
fixture=ROOT/'docs/retail-pilot/30-CAU-HOI-KIEM-THU.csv'
with fixture.open(encoding='utf-8-sig',newline='') as f: cases=list(csv.DictReader(f))
if len(cases)!=30: raise RuntimeError('Unexpected fixture')
if args.cases:
    selected={int(value) for value in args.cases.split(',')}
    if not selected or not selected.issubset(set(range(1,31))): raise ValueError('Unknown case ID')
    cases=[row for row in cases if int(row['STT']) in selected]
cases=cases*args.repeats
report={'candidate':args.candidate,'local_assistant_sha256':hashlib.sha256((ROOT/'policy_assistant/assistant.py').read_bytes()).hexdigest(),'repeats':args.repeats,'run_id':run_id,'code_sha256':release['code_sha256'],'model_id':env['BEDROCK_MODEL_ID'],'generation_region':env['BEDROCK_GENERATION_REGION'],'scope':'Actual byte-matched deployed answer/retrieval code; live public-policy scan, embeddings and generation via AWS CLI transport. Private documents excluded by design, quota/history in memory. Not browser or authenticated HTTP testing. No prompt/model/index overrides.','results':[]}
if args.candidate: report['scope']='LOCAL assistant.py candidate; other runtime modules byte-match deployment. Live public policies and model; no private PDFs or persisted history/quota. Not browser or authenticated HTTP testing.'
for row in cases:
    number=int(row['STT']);started=time.monotonic();item={'id':number,'question':row['Câu hỏi'],'expected':row['Nội dung kỳ vọng'],'review_status':'pending'}
    try:
        result=assistant.answer(service,owner,{'question':item['question']})
        item.update(answer=result['answer'],grounded=result['grounded'],policy_ids=[c.get('policy_id') for c in result['citations']],citations=[{'source_id':c['source_id'],'policy_id':c.get('policy_id'),'excerpt':c['excerpt']} for c in result['citations']],usage=service.generator.usage)
        print(f"{number:02d}/30: {result['answer'][:160]}",flush=True)
    except Exception as exc:
        item.update(error_type=type(exc).__name__,error=str(exc)[:300],model_response=service.generator.last_response);print(f'{number:02d}/30 ERROR: {type(exc).__name__}',flush=True)
    item['seconds']=round(time.monotonic()-started,2);report['results'].append(item)
    (OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
report['completed_at']=datetime.now(timezone.utc).isoformat();report['request_errors']=sum('error' in r for r in report['results'])
(OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/('.deployment/LATEST-RETAIL-CANDIDATE.txt' if args.candidate else '.deployment/LATEST-RETAIL-CLI.txt')).write_text(str(OUT),encoding='utf-8')
print('Finished:',len(report['results']),'request errors:',report['request_errors'],flush=True)
