"""Authenticated HTTP acceptance with one disposable, invitation-suppressed identity."""
from pathlib import Path
from uuid import uuid4
from datetime import datetime,timezone
import base64,json,secrets,sys,time,os,subprocess,tempfile,argparse
from types import SimpleNamespace
import boto3,requests
from botocore.config import Config
from botocore.exceptions import BotoCoreError
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
opts=dict(region_name='ap-southeast-1',config=Config(connect_timeout=5,read_timeout=30,retries={'max_attempts':1}))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--aws-cli',action='store_true',help='Use CLI transport for AWS control calls; API requests remain real HTTP.')
parser.add_argument('--cases',nargs='+',type=int,choices=[3,18,23,6,10,14,24,25,26])
parser.add_argument('--report-name',choices=['retail-http-acceptance.json','admin-ai-regression.json'],default='retail-http-acceptance.json')
args=parser.parse_args()
class TestUserNotFound(Exception): pass
class CLIClient:
    exceptions=SimpleNamespace(UserNotFoundException=TestUserNotFound)
    def __init__(self,name):self.name=name
    def __getattr__(self,method):
        def invoke(**data):
            # Secrets only enter a short-lived user temp file, never command-line arguments or reports.
            with tempfile.TemporaryDirectory(prefix='policy-http-') as tmp:
                path=Path(tmp)/'request.json';path.write_text(json.dumps(data,ensure_ascii=True),encoding='ascii')
                child=os.environ.copy();child.update(AWS_MAX_ATTEMPTS='1',AWS_PAGER='',AWS_CLI_FILE_ENCODING='UTF-8')
                response=subprocess.run(['aws',self.name,method.replace('_','-'),'--cli-input-json','file://'+str(path),'--region','ap-southeast-1','--output','json','--no-cli-pager','--cli-connect-timeout','5','--cli-read-timeout','30'],capture_output=True,env=child,timeout=45)
                if response.returncode:
                    if b'UserNotFoundException' in response.stderr:raise TestUserNotFound()
                    raise RuntimeError('AWS control request failed: '+self.name+'/'+method)
                return json.loads(response.stdout.decode('utf-8-sig')) if response.stdout.strip() else {}
        return invoke
def client(name):return CLIClient(name) if args.aws_cli else boto3.client(name,**opts)

cf=client('cloudformation')
stack=cf.describe_stacks(StackName='policy-assistant')['Stacks'][0]
if stack['StackStatus']!='UPDATE_COMPLETE': raise RuntimeError('Stack is not ready')
outputs={v['OutputKey']:v['OutputValue'] for v in stack['Outputs']}
fn=cf.describe_stack_resource(StackName='policy-assistant',LogicalResourceId='PolicyAssistantFunction')['StackResourceDetail']['PhysicalResourceId']
f=client('lambda').get_function_configuration(FunctionName=fn)
release=json.loads((ROOT/'.deployment/release.json').read_text(encoding='utf-8'))
if f['CodeSha256']!=base64.b64encode(bytes.fromhex(release['code_sha256'])).decode(): raise RuntimeError('Unexpected deployed code')
env=f['Environment']['Variables']
if env['BEDROCK_MODEL_ID']!='jp.amazon.nova-2-lite-v1:0' or env.get('BEDROCK_GENERATION_REGION')!='ap-northeast-1' or env.get('BEDROCK_REASONING_EFFORT')!='low': raise RuntimeError('Expected generation configuration is not deployed')
cognito=client('cognito-idp')
username='pilot-qa-'+uuid4().hex+'@example.invalid'
password=secrets.token_urlsafe(30)+'Aa1!'
token=None;created=False
report={'verified_at':datetime.now(timezone.utc).isoformat(),'scope':'Real authenticated HTTP API using one disposable synthetic Cognito user; no access to the owner account, browser session or private owner PDFs.','code_sha256':release['code_sha256'],'transport':'aws-cli' if args.aws_cli else 'boto3','checks':[],'test_account_cleaned':False}
base=outputs['PolicyAssistantApiUrl'].rstrip('/')
def call(path,method='GET',data=None,auth=True):
    headers={'Origin':outputs['FrontendUrl'].rstrip('/')}
    if auth: headers['Authorization']='Bearer '+token
    r=requests.request(method,base+path,json=data,headers=headers,timeout=45)
    try: body=r.json()
    except ValueError: body={}
    return r.status_code,body
try:
    code,_=call('/health',auth=False)
    if code!=200: raise RuntimeError('Health check failed')
    cognito.admin_create_user(UserPoolId=outputs['UserPoolId'],Username=username,MessageAction='SUPPRESS',UserAttributes=[{'Name':'email','Value':username},{'Name':'email_verified','Value':'true'}])
    created=True
    (ROOT/'.deployment/retail-test-cleanup.json').write_text(json.dumps({'username':username,'pool':outputs['UserPoolId'],'cleaned':False}),encoding='utf-8')
    cognito.admin_set_user_password(UserPoolId=outputs['UserPoolId'],Username=username,Password=password,Permanent=True)
    token=cognito.initiate_auth(ClientId=outputs['UserPoolClientId'],AuthFlow='USER_PASSWORD_AUTH',AuthParameters={'USERNAME':username,'PASSWORD':password})['AuthenticationResult']['IdToken']
    for suffix in ['ORDER','SHIPPING','RETURNS','WARRANTY','SUPPORT']:
        code,p=call('/policies/DEMO-SHOP-'+suffix+'-001')
        if code!=200 or 'search_chunks' in p: raise RuntimeError('Published policy API check failed: '+suffix)
    if call('/policies/DEMO-REFUND-001')[0]!=404: raise RuntimeError('Legacy demo should be archived')
    print('PASS JWT, five policy reads, index privacy and archived-demo exclusion',flush=True)
    cases=[(3,'Đơn đã bàn giao rồi, bạn hủy giúp tôi được không?'),(18,'Tôi vừa nhắn xin hoàn tiền, 5 ngày nữa chắc có tiền phải không?'),(23,'Tai nghe bị rơi vào nước có được bảo hành theo mẫu không?'),(6,'Shop có giao sang Singapore không?'),(10,'Phụ phí vùng xa là bao nhiêu?'),(14,'Tôi đổi ý sau 2 ngày, hộp còn nguyên có đề nghị trả được không?'),(24,'Bảo hành cần giấy tờ gì?'),(25,'Nhắn hỏi hôm nay thì 7 ngày nữa bảo hành xong chứ?'),(26,'Theo chính sách DEMO — Bảo hành phụ kiện, ai chịu phí gửi hàng đi bảo hành?')]
    if args.cases: cases=[case for case in cases if case[0] in args.cases]
    for number,question in cases:
        code,result=call('/ask','POST',{'question':question})
        if code!=200 or not result.get('grounded') or not result.get('citations'): raise RuntimeError('Question API failed: '+str(number)+' HTTP '+str(code))
        if any(not c.get('policy_id','').startswith('DEMO-SHOP-') for c in result['citations']): raise RuntimeError('Unexpected source scope')
        row={'case':number,'question':question,'status':code,'answer':result['answer'],'policy_ids':[c['policy_id'] for c in result['citations']],'semantic_review':'pending'}
        report['checks'].append(row)
        print(str(number)+': '+result['answer'],flush=True)
    if not call('/conversations')[1].get('conversations'): raise RuntimeError('History was not saved')
    report['http_passed']=True
finally:
    (ROOT/'.deployment'/args.report_name).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if created:
        if token:
            code,_=call('/account/delete','POST',{'confirmation':'DELETE'})
            if code!=200: raise RuntimeError('Disposable account deletion request failed')
            deadline=time.monotonic()+240
            while time.monotonic()<deadline:
                try: cognito.admin_get_user(UserPoolId=outputs['UserPoolId'],Username=username)
                except cognito.exceptions.UserNotFoundException:
                    report['test_account_cleaned']=True
                    break
                except BotoCoreError:
                    time.sleep(5)
                    continue
                time.sleep(5)
        else:
            cognito.admin_delete_user(UserPoolId=outputs['UserPoolId'],Username=username)
            report['test_account_cleaned']=True
    (ROOT/'.deployment'/args.report_name).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if created: (ROOT/'.deployment/retail-test-cleanup.json').write_text(json.dumps({'username':username,'pool':outputs['UserPoolId'],'cleaned':report['test_account_cleaned']}),encoding='utf-8')
    print('Disposable account cleaned:',report['test_account_cleaned'],flush=True)
if not report.get('http_passed') or not report['test_account_cleaned']: raise SystemExit(1)
