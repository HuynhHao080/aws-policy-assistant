"""Live language regression probe: real retrieval/model; no customer history/quota writes."""
from pathlib import Path
import sys, os, json, re
sys.stdout.reconfigure(encoding="utf-8")
from uuid import uuid4
from datetime import datetime, timezone
import boto3
from botocore.config import Config
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root))
from policy_assistant.service import Service
from policy_assistant import assistant
opts=dict(region_name='ap-southeast-1',config=Config(connect_timeout=5,read_timeout=45,retries={'max_attempts':1}))
cf=boto3.client('cloudformation',**opts)
fn=cf.describe_stack_resource(StackName='policy-assistant',LogicalResourceId='PolicyAssistantFunction')['StackResourceDetail']['PhysicalResourceId']
config=boto3.client('lambda',**opts).get_function_configuration(FunctionName=fn)['Environment']['Variables']
for name in ['POLICIES_TABLE_NAME','DOCUMENT_METADATA_TABLE_NAME','AUDIT_TABLE_NAME','HISTORY_TABLE_NAME','EMBEDDING_MODEL_ID','BEDROCK_MODEL_ID','REQUIRE_PUBLISHED_POLICIES','BEDROCK_GENERATION_REGION','BEDROCK_REASONING_EFFORT']:
    os.environ[name]=config.get(name,'')
os.environ['AWS_REGION']='ap-southeast-1'
class History:
    def put_item(self,**kwargs):
        self.last=kwargs['Item']
class Probe(Service):
    history=History()
    def quota(self,owner,kind):
        pass
    def table(self,name):
        if name=='HISTORY_TABLE_NAME': return self.history
        return super().table(name)
db=boto3.resource('dynamodb',**opts)
service=Probe(db.Table(config['DOCUMENT_METADATA_TABLE_NAME']),db.Table(config['POLICIES_TABLE_NAME']))
owner='internal-language-regression-'+uuid4().hex
question='Theo chính sách DEMO — Bảo hành phụ kiện, ai chịu phí gửi hàng đi bảo hành?'
cases=[('warranty_shipping_1',question),('warranty_shipping_2',question),('phone_case_unknown','Theo chính sách DEMO — Bảo hành phụ kiện, ốp điện thoại có được bảo hành không?'),('charger_duration','Theo chính sách DEMO — Bảo hành phụ kiện, củ sạc được bảo hành bao lâu?')]
checks=[]
for label,q in cases:
    result=assistant.answer(service,owner,{'question':q})
    answer=result['answer']
    ok=result['grounded'] and any(c.get('policy_id')=='DEMO-SHOP-WARRANTY-001' for c in result['citations']) and bool(re.search('[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]',answer.lower()))
    if label.startswith('warranty_shipping'):
        ok=ok and any(x in answer.lower() for x in ['chưa','không']) and 'phí' in answer.lower()
    if label=='phone_case_unknown': ok=ok and any(x in answer.lower() for x in ['chưa','không'])
    if label=='charger_duration': ok=ok and '12' in answer and 'tháng' in answer.lower()
    checks.append({'case':label,'question':q,'answer':answer,'passed':bool(ok),'policy_ids':[c.get('policy_id') for c in result['citations']]})
    print(('PASS' if ok else 'FAIL')+' '+label+': '+answer,flush=True)
    if not ok: break
report={'passed':len(checks)==len(cases) and all(x['passed'] for x in checks),'verified_at':datetime.now(timezone.utc).isoformat(),'scope':'Real policy retrieval, embeddings and model using local revised answer code; isolated internal owner; no customer quota/history writes; not a browser test.','checks':checks}
(root/'.deployment/vietnamese-language-probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
raise SystemExit(0 if report['passed'] else 1)
