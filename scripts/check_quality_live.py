"""Quality acceptance with an isolated year-2000 synthetic cohort; zero model calls."""
import sys,json,time,secrets,base64
from pathlib import Path
from uuid import uuid4
from datetime import datetime,timezone
from urllib.parse import quote
import requests
from boto3.dynamodb.types import TypeSerializer,TypeDeserializer
from check_admin_live import aws,UserNotFound
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from policy_assistant.quality import save_answer,COUNTERS


def main():
    stack=aws("cloudformation","describe-stacks",StackName="policy-assistant")["Stacks"][0]
    assert stack["StackStatus"]=="UPDATE_COMPLETE" and stack["StackId"].split(":")[4]=="629380420098"
    out={x["OutputKey"]:x["OutputValue"] for x in stack["Outputs"]};base=out["PolicyAssistantApiUrl"].rstrip("/")
    fn=aws("cloudformation","describe-stack-resource",StackName="policy-assistant",LogicalResourceId="PolicyAssistantFunction")["StackResourceDetail"]["PhysicalResourceId"]
    cfg=aws("lambda","get-function-configuration",FunctionName=fn);env=cfg["Environment"]["Variables"]
    release=json.loads((ROOT/".deployment/release.json").read_text());assert base64.b64decode(cfg["CodeSha256"]).hex()==release["code_sha256"]
    nonce=uuid4().hex;cohort="2000-01";key="quality#"+cohort;convid=datetime.now(timezone.utc).isoformat()+"#"+nonce
    users={r:{"name":"quality-qa-"+nonce+"-"+r+"@example.invalid","password":secrets.token_urlsafe(25)+"Aa1!","token":None,"sub":None,"created":False,"cleaned":False} for r in ['a','b']}
    report={"checked_at":datetime.now(timezone.utc).isoformat(),"release":release,"scope":"Two disposable identities; synthetic private answer stored through actual save_answer using operator CLI transport, isolated unavailable year-2000 cohort. Real feedback APIs and aggregate-only authorization. No model/PDF/email or real current/previous-month metric writes.","checks":[],"http_passed":False,"accounts_cleaned":False,"fixture_cleaned":False}
    reserved=False;encode=TypeSerializer().serialize;decode=TypeDeserializer().deserialize
    def save():
        (ROOT/".deployment/quality-live-acceptance.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        (ROOT/".deployment/quality-test-cleanup.json").write_text(json.dumps({"users":[{k:u[k] for k in ['name','sub','created','cleaned']} for u in users.values()],"pool":out['UserPoolId'],"cohort":cohort,"nonce":nonce,"conversation_id":convid,"metric_reserved":reserved},indent=2),encoding="utf-8")
    def check(label,value):
        if not value:raise RuntimeError("Failed: "+label)
        report['checks'].append(label);save();print('PASS '+label,flush=True)
    def call(role,path,method='GET',data=None,auth=True):
        headers={'Origin':out['FrontendUrl'].rstrip('/')}
        if auth:headers['Authorization']='Bearer '+users[role]['token']
        r=requests.request(method,base+path,json=data,headers=headers,timeout=40)
        try:body=r.json()
        except ValueError:body={}
        return r.status_code,body
    def ok(role,path,method='GET',data=None):
        code,body=call(role,path,method,data)
        if code!=200:raise RuntimeError(path.split('?')[0]+' returned '+str(code))
        return body
    def login(role):
        u=users[role];u['token']=aws('cognito-idp','initiate-auth',ClientId=out['UserPoolClientId'],AuthFlow='USER_PASSWORD_AUTH',AuthParameters={'USERNAME':u['name'],'PASSWORD':u['password']})['AuthenticationResult']['IdToken'];u['sub']=json.loads(base64.urlsafe_b64decode(u['token'].split('.')[1]+'=='))['sub']
    def metric():
        x=aws('dynamodb','get-item',TableName=env['USAGE_TABLE_NAME'],Key={'pk':{'S':key}},ConsistentRead=True).get('Item',{})
        return {k:decode(v) for k,v in x.items()}
    url='/conversations/'+quote(convid,safe='')+'/feedback'
    def vote(rating='helpful',reason=None,revision=None,role='a'):
        return call(role,url,'PATCH',{'rating':rating,'reason':reason,'expected_revision':revision})
    try:
        routes=aws('apigatewayv2','get-routes',ApiId=base.split('//')[1].split('.')[0])['Items']
        chosen=[x for x in routes if x['RouteKey'] in {'PATCH /conversations/{conversation_id}/feedback','GET /admin/quality'}]
        check('Both deployed quality routes enforce JWT',len(chosen)==2 and all(x.get('AuthorizationType')=='JWT' for x in chosen))
        check('Quality API rejects anonymous requests',call('a','/admin/quality',auth=False)[0] in [401,403])
        for role,u in users.items():
            aws('cognito-idp','admin-create-user',UserPoolId=out['UserPoolId'],Username=u['name'],MessageAction='SUPPRESS',UserAttributes=[{'Name':'email','Value':u['name']},{'Name':'email_verified','Value':'true'}]);u['created']=True;save()
            aws('cognito-idp','admin-set-user-password',UserPoolId=out['UserPoolId'],Username=u['name'],Password=u['password'],Permanent=True);login(role)
        check('Customer cannot view global quality analytics',call('a','/admin/quality')[0]==403)
        aws('dynamodb','put-item',TableName=env['USAGE_TABLE_NAME'],Item={k:encode(v) for k,v in {'pk':key,'qa_nonce':nonce,'expires_at':int(time.time())+86400,**{k:0 for k in COUNTERS}}.items()},ConditionExpression='attribute_not_exists(pk)');reserved=True;save()
        class Table:
            def __init__(self,name):self.name=name
        class Transport:
            def transact_write_items(self,**kwargs):return aws('dynamodb','transact-write-items',**kwargs)
        class SeedService:
            def table(self,name):return Table(env[name])
            def client(self,name):assert name=='dynamodb';return Transport()
        item={'owner_id':users['a']['sub'],'conversation_id':convid,'created_at':'2000-01-01T00:00:00+00:00','question':'SYNTHETIC-PRIVATE-'+nonce,'answer':'Synthetic QA fixture, not model-generated','citations':[],'grounded':False,'source_scope':'policies','expires_at':int(time.time())+86400}
        save_answer(SeedService(),users['a']['sub'],item,1234)
        check('Actual save_answer transaction records one answer in isolated cohort',metric()['answers']==1 and metric()['refused']==1 and metric()['latency_ms']==1234)
        check('Another customer cannot rate a known private conversation',vote(role='b')[0]==404)
        code,first=vote();check('Owned feedback records a helpful vote',code==200 and metric()['helpful']==1)
        code,retry=vote();check('Same-target network retry does not double count',code==200 and retry==first and metric()['helpful']==1)
        check('Stale conflicting feedback is rejected',vote('not_helpful','citation','stale')[0]==409)
        code,second=vote('not_helpful','citation',first['feedback']['revision']);m=metric();check('Changing a vote moves counters atomically',code==200 and m['helpful']==0 and m['not_helpful']==1 and m['reason_citation']==1)
        code,third=vote(None,None,second['feedback']['revision']);m=metric();check('Withdrawing a vote restores feedback totals',code==200 and m['not_helpful']==0 and m['reason_citation']==0)
        check('Controlled reason validation rejects invalid feedback',vote('not_helpful','invalid',third['feedback']['revision'])[0]==400)
        aws('cognito-idp','admin-add-user-to-group',UserPoolId=out['UserPoolId'],Username=users['b']['name'],GroupName='administrators');login('b')
        summary=ok('b','/admin/quality');check('Admin report exposes only anonymous aggregate measurements','PRIVATE' not in json.dumps(summary) and nonce not in json.dumps(summary) and 'owner_id' not in json.dumps(summary) and len(summary['available_months'])==2)
        check('Synthetic year-2000 fixture cannot appear in normal dashboard',call('b','/admin/quality?month='+cohort)[0]==400)
        check('Admin role still cannot rate another customer private answer',vote(role='b')[0]==404)
        report['http_passed']=True
    except Exception as exc:report['error']=str(exc)[:300];print('Quality acceptance stopped: '+type(exc).__name__,flush=True)
    finally:
        for role,u in users.items():
            if not u['created']:continue
            try:
                if not u['token']:login(role)
                if call(role,'/account/delete','POST',{'confirmation':'DELETE'})[0]!=200:raise RuntimeError('Synthetic cleanup request failed')
            except Exception as exc:report['cleanup_error_'+role]=type(exc).__name__
        for role,u in users.items():
            if not u['created']:continue
            deadline=time.monotonic()+300
            while time.monotonic()<deadline:
                try:aws('cognito-idp','admin-get-user',UserPoolId=out['UserPoolId'],Username=u['name'])
                except UserNotFound:u['cleaned']=True;break
                time.sleep(5)
        report['accounts_cleaned']=all(not u['created'] or u['cleaned'] for u in users.values())
        report['history_purged']=False
        if report['accounts_cleaned']:
            try:
                remaining=[]
                for u in users.values():
                    if u['sub']:
                        remaining.extend(aws('dynamodb','query',TableName=env['HISTORY_TABLE_NAME'],KeyConditionExpression='owner_id=:owner',ExpressionAttributeValues={':owner':{'S':u['sub']}},ProjectionExpression='owner_id,conversation_id',ConsistentRead=True,Limit=1)['Items'])
                report['history_purged']=not remaining
                if report['history_purged']:report['checks'].append('Disposable history partitions are empty after account purge')
            except Exception as exc:report['history_cleanup_error']=type(exc).__name__
        if reserved and report['accounts_cleaned'] and report['history_purged']:
            try:
                aws('dynamodb','delete-item',TableName=env['USAGE_TABLE_NAME'],Key={'pk':{'S':key}},ConditionExpression='qa_nonce=:nonce',ExpressionAttributeValues={':nonce':{'S':nonce}})
                report['fixture_cleaned']=not metric()
            except Exception as exc:report['fixture_cleanup_error']=type(exc).__name__
        save();print('Synthetic account/cohort cleanup:',report['accounts_cleaned'],report['fixture_cleaned'],flush=True)
    if not all(report[k] for k in ['http_passed','accounts_cleaned','fixture_cleaned','history_purged']):raise SystemExit(1)


if __name__=='__main__':main()
