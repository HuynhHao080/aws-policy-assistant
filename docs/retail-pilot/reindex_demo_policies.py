"""Prepare/apply a create-only-index migration for exactly five authorized demo records."""
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4
import argparse,hashlib,json,os,sys,time
import boto3
from boto3.dynamodb.types import TypeSerializer
ROOT=Path(__file__).resolve().parent
APP=ROOT.parents[1]
sys.path.insert(0,str(APP))
from policy_assistant.policy_chunks import policy_chunks
from policy_assistant.embeddings import embed
from policy_assistant.service import Service
parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','apply']);args=parser.parse_args()
identity=boto3.client('sts',region_name='ap-southeast-1').get_caller_identity()
if identity['Account']!='629380420098': raise RuntimeError('Unexpected account')
cf=boto3.client('cloudformation',region_name='ap-southeast-1')
fn=cf.describe_stack_resource(StackName='policy-assistant',LogicalResourceId='PolicyAssistantFunction')['StackResourceDetail']['PhysicalResourceId']
env=boto3.client('lambda',region_name='ap-southeast-1').get_function_configuration(FunctionName=fn)['Environment']['Variables']
for key in ['EMBEDDING_MODEL_ID','AUDIT_TABLE_NAME']: os.environ[key]=env.get(key,'')
os.environ['AWS_REGION']='ap-southeast-1'
db=boto3.resource('dynamodb',region_name='ap-southeast-1');table=db.Table(env['POLICIES_TABLE_NAME'])
service=Service(db.Table(env['DOCUMENT_METADATA_TABLE_NAME']),table)
fixtures=json.loads((ROOT/'du-lieu-demo.json').read_text(encoding='utf-8'))
allowed={f'DEMO-SHOP-{k}-001' for k in ['ORDER','SHIPPING','RETURNS','WARRANTY','SUPPORT']}
if len(fixtures)!=5 or {p['policy_id'] for p in fixtures}!=allowed: raise RuntimeError('Unexpected fixture scope')
serialize=TypeSerializer().serialize
path=ROOT/'retail-index-plan.json'
chunk_hash=hashlib.sha256((APP/'policy_assistant/policy_chunks.py').read_bytes()).hexdigest()

def validate(item,fixture):
    if item.get('publication_state')!='published' or any(item.get(k)!=fixture[k] for k in ['title','category','content','keywords']): raise RuntimeError('Demo content changed; refusing: '+fixture['policy_id'])

if args.phase=='prepare':
    plan={'chunker_sha256':chunk_hash,'embedding_model':env['EMBEDDING_MODEL_ID'],'table':table.name,'audit_table':env['AUDIT_TABLE_NAME'],'request_id':'retail-reindex-'+uuid4().hex,'items':[]}
    for p in fixtures:
        item=table.get_item(Key={'policy_id':p['policy_id']},ConsistentRead=True)['Item'];validate(item,p)
        chunks=policy_chunks(p['content'])
        vectors=embed(service,[p['title']+'\n'+c['embedding_text'] for c in chunks],'search_document')
        plan['items'].append({'policy_id':p['policy_id'],'expected_updated_at':item['updated_at'],'original_typed_item':{k:serialize(v) for k,v in item.items()},'search_chunks':[{'text':c['text'],'vector':v} for c,v in zip(chunks,vectors)]})
    if path.exists(): raise RuntimeError('An index plan exists; inspect before preparing again')
    path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Prepared five index updates; no database writes:',[len(p['search_chunks']) for p in plan['items']],flush=True)
else:
    plan=json.loads(path.read_text(encoding='utf-8'))
    if plan['table']!=table.name or plan['embedding_model']!=env['EMBEDDING_MODEL_ID'] or plan['chunker_sha256']!=chunk_hash: raise RuntimeError('Plan/configuration drift')
    if {p['policy_id'] for p in plan['items']}!=allowed: raise RuntimeError('Unexpected plan scope')
    current={}
    for p in fixtures:
        item=table.get_item(Key={'policy_id':p['policy_id']},ConsistentRead=True)['Item'];validate(item,p);current[p['policy_id']]=item
    if all(current[p['policy_id']].get('search_chunks')==p['search_chunks'] for p in plan['items']):
        print('Planned indexes already applied and verified.',flush=True)
    else:
        if any(current[p['policy_id']]['updated_at']!=p['expected_updated_at'] for p in plan['items']): raise RuntimeError('Concurrent update; nothing applied')
        stamp=plan.setdefault('apply_stamp',datetime.now(timezone.utc).isoformat())
        actor=plan.setdefault('actor','aws-operator:'+identity['Arn'])
        for p in plan['items']: p.setdefault('audit_event_id',stamp+'#'+uuid4().hex)
        path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
        operations=[]
        for p in plan['items']:
            item=current[p['policy_id']]
            values={':chunks':p['search_chunks'],':model':plan['embedding_model'],':now':stamp,':actor':actor,':old':p['expected_updated_at'],':content':item['content'],':published':'published'}
            operations.append({'Update':{'TableName':table.name,'Key':{'policy_id':{'S':p['policy_id']}},'UpdateExpression':'SET search_chunks=:chunks, embedding_model=:model, updated_at=:now, updated_by=:actor','ConditionExpression':'updated_at=:old AND #body=:content AND publication_state=:published','ExpressionAttributeNames':{'#body':'content'},'ExpressionAttributeValues':{k:serialize(v) for k,v in values.items()}}})
            event={'scope':'admin','event_id':p['audit_event_id'],'actor':actor,'action':'policy.reindex','resource':p['policy_id'],'request_id':plan['request_id'],'expires_at':int(time.time())+90*86400}
            operations.append({'Put':{'TableName':plan['audit_table'],'Item':{k:serialize(v) for k,v in event.items()}}})
        boto3.client('dynamodb',region_name='ap-southeast-1').transact_write_items(TransactItems=operations,ClientRequestToken=plan['request_id'][-32:])
        for p in plan['items']:
            item=table.get_item(Key={'policy_id':p['policy_id']},ConsistentRead=True)['Item']
            if item['search_chunks']!=p['search_chunks'] or item['content']!=current[p['policy_id']]['content']: raise RuntimeError('Post-index verification failed')
        plan['applied']=True;path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Applied and verified five indexes with audit; policy content unchanged and originals backed up.',flush=True)
