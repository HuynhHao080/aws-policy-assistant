"""Create only the five authorized demo policies using IAM, embeddings and atomic audit writes."""
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
import hashlib, json, os, re, sys, time
import boto3
from boto3.dynamodb.types import TypeSerializer
from botocore.config import Config

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'du-lieu-demo.json'
REGION='ap-southeast-1'
STACK='policy-assistant'
ACCOUNT='629380420098'
EXPECTED={f'DEMO-SHOP-{kind}-001' for kind in ['ORDER','SHIPPING','RETURNS','WARRANTY','SUPPORT']}
opts=dict(region_name=REGION,config=Config(connect_timeout=5,read_timeout=40,retries={'max_attempts':2}))

def main():
    policies=json.loads(SOURCE.read_text(encoding='utf-8'))
    if len(policies)!=5 or {p['policy_id'] for p in policies}!=EXPECTED:
        raise RuntimeError('Refusing any policy outside the authorized five demo IDs')
    for p in policies:
        if not p['content'].startswith('DỮ LIỆU DEMO HƯ CẤU') or not p['title'].startswith('DEMO'):
            raise RuntimeError('Every item must retain fictional demo labeling')
        for name,limit in [('policy_id',80),('title',180),('category',80),('content',20000)]:
            if not isinstance(p[name],str) or not 0<len(p[name].strip())<=limit:
                raise RuntimeError('Invalid policy field: '+name)
        if not re.fullmatch('[A-Za-z0-9_-]{1,80}',p['policy_id']) or not isinstance(p['keywords'],list) or len(p['keywords'])>30 or any(not isinstance(k,str) or len(k)>80 for k in p['keywords']):
            raise RuntimeError('Invalid policy ID or keywords')
    caller=boto3.client('sts',**opts).get_caller_identity()
    if caller['Account']!=ACCOUNT:
        raise RuntimeError('Unexpected AWS account')
    cf=boto3.client('cloudformation',**opts)
    stack=cf.describe_stacks(StackName=STACK)['Stacks'][0]
    if stack['StackStatus'] not in ('UPDATE_COMPLETE','CREATE_COMPLETE'):
        raise RuntimeError('Stack update is not complete')
    resource=cf.describe_stack_resource(StackName=STACK,LogicalResourceId='PolicyAssistantFunction')['StackResourceDetail']['PhysicalResourceId']
    config=boto3.client('lambda',**opts).get_function_configuration(FunctionName=resource)['Environment']['Variables']
    if config.get('REQUIRE_PUBLISHED_POLICIES')!='true':
        raise RuntimeError('Expected published-policy filtering')
    table_name=config['POLICIES_TABLE_NAME']
    audit_name=config['AUDIT_TABLE_NAME']
    db=boto3.resource('dynamodb',**opts)
    table=db.Table(table_name)
    audit=db.Table(audit_name)
    pending=[]
    for p in policies:
        old=table.get_item(Key={'policy_id':p['policy_id']},ConsistentRead=True).get('Item')
        if old:
            if any(old.get(k)!=p[k] for k in ['title','category','content','keywords']) or old.get('publication_state')!='published':
                raise RuntimeError('Existing content differs; refusing overwrite: '+p['policy_id'])
            if not old.get('search_chunks') or old.get('embedding_model')!=config.get('EMBEDDING_MODEL_ID'):
                raise RuntimeError('Existing index differs; refusing overwrite: '+p['policy_id'])
            print('Already present, unchanged:',p['policy_id'],flush=True)
        else:
            pending.append(p)
    model=config.get('EMBEDDING_MODEL_ID')
    if not model:
        raise RuntimeError('Embedding model is not configured')
    os.environ['EMBEDDING_MODEL_ID']=model
    sys.path.insert(0,str(ROOT.parents[1]/'policy_assistant'))
    from embeddings import embed
    class Clients:
        def client(self,name):
            return boto3.client(name,**opts)
    fragments=[]
    for p in pending:
        p['fragments']=[p['content'][start:start+1400] for start in range(0,len(p['content']),1200)]
        fragments.extend(p['fragments'])
    vectors=embed(Clients(),fragments,'search_document') if fragments else []
    actor='aws-operator:'+caller['Arn']
    stamp=datetime.now(timezone.utc).isoformat()
    request='demo-import-'+uuid4().hex
    serialize=TypeSerializer().serialize
    operations=[]
    audit_keys=[]
    offset=0
    for p in pending:
        item={k:p[k] for k in ['policy_id','title','category','content','keywords']}
        for key in ['title','category','content']:
            item[key+'_lower']=item[key].lower()
        item['keywords_lower']=[k.lower() for k in item['keywords']]
        item['publication_state']='published'
        item['embedding_model']=model
        item['search_chunks']=[{'text':fragment,'vector':vectors[offset+i]} for i,fragment in enumerate(p['fragments'])]
        offset+=len(p['fragments'])
        item['updated_at']=stamp
        item['updated_by']=actor
        event={'scope':'admin','event_id':stamp+'#'+uuid4().hex,'actor':actor,'action':'policy.import.demo','resource':p['policy_id'],'request_id':request,'expires_at':int(time.time())+90*86400}
        audit_keys.append({'scope':'admin','event_id':event['event_id']})
        operations.append({'Put':{'TableName':table_name,'Item':{k:serialize(v) for k,v in item.items()},'ConditionExpression':'attribute_not_exists(policy_id)'}})
        operations.append({'Put':{'TableName':audit_name,'Item':{k:serialize(v) for k,v in event.items()},'ConditionExpression':'attribute_not_exists(event_id)'}})
    if operations:
        boto3.client('dynamodb',**opts).transact_write_items(TransactItems=operations,ClientRequestToken=request[-32:])
    checks=[]
    for p in policies:
        stored=table.get_item(Key={'policy_id':p['policy_id']},ConsistentRead=True)['Item']
        if any(stored.get(k)!=p[k] for k in ['title','category','content','keywords']) or stored.get('publication_state')!='published' or stored.get('embedding_model')!=model or not stored.get('search_chunks'):
            raise RuntimeError('Post-import verification failed: '+p['policy_id'])
        checks.append({'policy_id':p['policy_id'],'published':True,'search_chunks':len(stored['search_chunks']),'content_sha256':hashlib.sha256(stored['content'].encode()).hexdigest()})
        print('Verified published and indexed:',p['policy_id'],flush=True)
    for key in audit_keys:
        if audit.get_item(Key=key,ConsistentRead=True).get('Item',{}).get('request_id')!=request:
            raise RuntimeError('Audit verification failed')
    report={'stack':STACK,'region':REGION,'verified':True,'method':'AWS IAM operator; conditional create-only transaction with audit and embeddings','new_records':len(pending),'audit_events_verified':len(audit_keys),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'verified_at':datetime.now(timezone.utc).isoformat(),'policies':checks}
    (ROOT/'KET-QUA-IMPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Complete:',len(checks),'policies;',len(pending),'created;',len(audit_keys),'audit events verified.',flush=True)

if __name__=='__main__':
    main()
