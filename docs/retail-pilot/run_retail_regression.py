"""Thirty-case live model regression; no user-session, private-PDF, quota or history writes."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import sys, os, json, csv, time, base64, hashlib, zipfile, re, argparse
import boto3
from botocore.config import Config
sys.stdout.reconfigure(encoding='utf-8')
parser=argparse.ArgumentParser()
parser.add_argument('--prompt-file')
parser.add_argument('--cases')
parser.add_argument('--section-chunks', action='store_true')
parser.add_argument('--context-windows',action='store_true')
parser.add_argument('--thinking-low',action='store_true')
parser.add_argument('--generation-region',choices=['ap-southeast-1','ap-northeast-1'])
parser.add_argument('--model-id', choices=['apac.amazon.nova-micro-v1:0','apac.amazon.nova-lite-v1:0','apac.amazon.nova-pro-v1:0','jp.amazon.nova-2-lite-v1:0'])
args=parser.parse_args()
ROOT=Path(__file__).resolve().parent
APP=ROOT.parents[1]
sys.path.insert(0,str(APP))
from policy_assistant.service import Service
from policy_assistant import assistant
opts=dict(region_name='ap-southeast-1',config=Config(connect_timeout=5,read_timeout=45,retries={'max_attempts':1}))
cf=boto3.client('cloudformation',**opts)
stack=cf.describe_stacks(StackName='policy-assistant')['Stacks'][0]
if stack['StackStatus']!='UPDATE_COMPLETE': raise RuntimeError('Stack is not stable')
fn=cf.describe_stack_resource(StackName='policy-assistant',LogicalResourceId='PolicyAssistantFunction')['StackResourceDetail']['PhysicalResourceId']
config=boto3.client('lambda',**opts).get_function_configuration(FunctionName=fn)
release=json.loads((APP/'.deployment/release.json').read_text(encoding='utf-8'))
expected=base64.b64encode(bytes.fromhex(release['code_sha256'])).decode()
archive=APP/'.deployment/lambda.zip'
if config['CodeSha256']!=expected or hashlib.sha256(archive.read_bytes()).hexdigest()!=release['code_sha256']:
    raise RuntimeError('Live code or artifact drift')
with zipfile.ZipFile(archive) as z:
    for module in (APP/'policy_assistant').glob('*.py'):
        if z.read(module.name)!=module.read_bytes(): raise RuntimeError('Source differs from deployed artifact: '+module.name)
env=config['Environment']['Variables']
for key in ['POLICIES_TABLE_NAME','DOCUMENT_METADATA_TABLE_NAME','AUDIT_TABLE_NAME','HISTORY_TABLE_NAME','EMBEDDING_MODEL_ID','BEDROCK_MODEL_ID','REQUIRE_PUBLISHED_POLICIES','BEDROCK_GENERATION_REGION','BEDROCK_REASONING_EFFORT']:
    os.environ[key]=env.get(key,'')
os.environ['AWS_REGION']='ap-southeast-1'
if args.model_id: os.environ['BEDROCK_MODEL_ID']=args.model_id
class History:
    def put_item(self,**kwargs):
        self.last=kwargs['Item']
class Probe(Service):
    history=History()
    def quota(self,owner,kind): pass
    def table(self,name):
        return self.history if name=='HISTORY_TABLE_NAME' else super().table(name)
db=boto3.resource('dynamodb',**opts)
service=Probe(db.Table(env['DOCUMENT_METADATA_TABLE_NAME']),db.Table(env['POLICIES_TABLE_NAME']))
candidate=None
if args.prompt_file:
    candidate=Path(args.prompt_file).read_text(encoding='utf-8')
    class CandidateModel:
        def __init__(self):
            self.inner=boto3.client('bedrock-runtime',**opts)
            generation_opts=dict(opts)
            generation_opts['region_name']=args.generation_region or opts['region_name']
            self.generator=boto3.client('bedrock-runtime',**generation_opts)
        def invoke_model(self,**kwargs): return self.inner.invoke_model(**kwargs)
        def converse(self,**kwargs):
            kwargs['system']=[{'text':candidate}]
            if args.thinking_low:
                kwargs['inferenceConfig']['maxTokens']=2500
                kwargs['additionalModelRequestFields']={'reasoningConfig':{'type':'enabled','maxReasoningEffort':'low'}}
            response=self.generator.converse(**kwargs)
            self.last_output=''.join(block.get('text','') for block in response['output']['message']['content'])
            self.last_usage=response.get('usage',{})
            return response
    service._clients['bedrock-runtime']=CandidateModel()
    service._clients['bedrock-generation']=service._clients['bedrock-runtime']
if not candidate:
    class ObservedModel:
        def __init__(self,inner): self.inner=inner
        def invoke_model(self,**kwargs): return self.inner.invoke_model(**kwargs)
        def converse(self,**kwargs):
            response=self.inner.converse(**kwargs)
            self.last_usage=response.get('usage',{})
            self.last_output=''.join(b.get('text','') for b in response['output']['message']['content'])
            return response
    observed=ObservedModel(service.generation_client())
    cache_key='bedrock-generation' if os.environ.get('BEDROCK_GENERATION_REGION')!=service.region else 'bedrock-runtime'
    service._clients[cache_key]=observed
if args.section_chunks:
    from policy_assistant.embeddings import embed
    class SectionPolicies:
        def __init__(self,inner): self.inner=inner; self.name=inner.name; self.cache={}
        def scan(self,**kwargs):
            result=self.inner.scan(**kwargs)
            for item in result.get('Items',[]):
                content=item.get('content','')[:20000]
                key=(item['policy_id'],content)
                if key not in self.cache:
                    parts=[part.strip() for part in re.split(r'\n(?=\s*\d+[.)]\s)|\n[ \t]*\n',content) if part.strip()]
                    pieces=[part[start:start+1400] for part in parts for start in range(0,len(part),1200)]
                    vectors=embed(service,[item.get('title','')+'\n'+piece for piece in pieces],'search_document')
                    display=['\n'.join(pieces[max(0,i-1):min(len(pieces),i+2)])[:1400] for i in range(len(pieces))] if args.context_windows else pieces
                    self.cache[key]=[{'text':part,'vector':vector} for part,vector in zip(display,vectors)]
                item['search_chunks']=self.cache[key]
                item['embedding_model']=env['EMBEDDING_MODEL_ID']
            return result
    service.policies=SectionPolicies(service.policies)
owner='internal-retail-pilot-'+uuid4().hex
fixture=ROOT/'30-CAU-HOI-KIEM-THU.csv'
with fixture.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
if len(rows)!=30 or [int(r['STT']) for r in rows]!=list(range(1,31)): raise RuntimeError('Unexpected fixture')
if args.cases:
    selected={int(n) for n in args.cases.split(',')}
    if not selected or not selected<=set(range(1,31)): raise RuntimeError('Invalid case selection')
    rows=[r for r in rows if int(r['STT']) in selected]
run_id=datetime.now(timezone(timedelta(hours=7))).strftime('%Y%m%d-%H%M%S')
output=ROOT/('test-run-'+run_id)
output.mkdir()
report={'run_id':run_id,'started_at':datetime.now(timezone.utc).isoformat(),'code_sha256':release['code_sha256'],'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'scope':'Operator regression harness using byte-matched deployed Python code, live DynamoDB public policies, live Bedrock embeddings and generation. Isolated owner with no private documents; quota and history replaced in memory. Not a browser, authenticated HTTP, or customer-session test.','results':[]}
report['prompt_override_sha256']=hashlib.sha256(candidate.encode()).hexdigest() if candidate else None
report['candidate_prompt_test']=bool(candidate)
report['candidate_model_id']=args.model_id
report['candidate_generation_region']=args.generation_region
report['candidate_section_chunking']=args.section_chunks
report['candidate_context_windows']=args.context_windows
report['thinking_low']=args.thinking_low
report['deployed_model_id']=env['BEDROCK_MODEL_ID']
report['selected_cases']=[int(r['STT']) for r in rows]
if args.section_chunks: report['scope']+=' Candidate section-based shared-policy indexing substituted in memory; no policy writes.'
if candidate: report['scope']+=' Candidate system prompt substituted before the model call; this candidate is not yet deployed.'
def save():
    (output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'LATEST-TEST-RUN.txt').write_text(str(output),encoding='utf-8')
save()
for row in rows:
    number=int(row['STT'])
    started=time.monotonic()
    entry={'id':number,'group':row['Nhóm'],'question':row['Câu hỏi'],'expected':row['Nội dung kỳ vọng'],'expected_policy_codes':row['Mã nguồn DEMO-SHOP tương ứng'].split(','),'check':row['Điểm kiểm tra'],'review_status':'PENDING'}
    try:
        result=assistant.answer(service,owner,{'question':entry['question']})
        if any(s.get('doc_id') for s in result.get('citations',[])): raise RuntimeError('Unexpected private-document source')
        entry.update(answer=result['answer'],grounded=result['grounded'],policy_ids=[s.get('policy_id') for s in result['citations']],citations=[{'source_id':s['source_id'],'policy_id':s.get('policy_id'),'excerpt':s['excerpt']} for s in result['citations']],model_id=result['model_id'])
        entry['flags']=[]
        entry['model_usage']=getattr(service._clients['bedrock-runtime'] if candidate else observed,'last_usage',{})
        if not re.search('[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]',entry['answer'].lower()): entry['flags'].append('language_review')
        if not result['grounded']: entry['flags'].append('no_citation')
        if any(not (p or '').startswith('DEMO-SHOP-') for p in entry['policy_ids']): entry['flags'].append('source_outside_new_demo_pack')
        print(f"{number:02d}/30: {entry['answer'][:190]} | sources={','.join(entry['policy_ids'])}",flush=True)
    except Exception as exc:
        entry.update(error_type=type(exc).__name__,error_message=str(exc)[:350],flags=['request_failed'])
        if candidate: entry['diagnostic_model_output']=getattr(service._clients['bedrock-runtime'],'last_output',None)
        print(f'{number:02d}/30 ERROR: {type(exc).__name__}',flush=True)
    entry['duration_seconds']=round(time.monotonic()-started,2)
    report['results'].append(entry)
    save()
report['completed_at']=datetime.now(timezone.utc).isoformat()
report['completed_cases']=len(report['results'])
report['request_errors']=sum('error_type' in r for r in report['results'])
save()
print('Completed:',len(report['results']),'request errors:',report['request_errors'],'report:',output,flush=True)
