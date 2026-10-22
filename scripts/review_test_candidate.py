"""Read and audit the current unexecuted test change set; never change AWS resources."""
import collections
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import boto3
from botocore.config import Config
import yaml

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / '.aws-sam/test-review'


def audit(template, active_ids):
    resources = template['Resources']
    roles = {key:value for key,value in resources.items() if value['Type']=='AWS::IAM::Role'}
    checks = []
    for key, role in roles.items():
        checks.append((key + ': no broad managed policies', not role['Properties'].get('ManagedPolicyArns')))
    for function, group in [('PolicyAssistantFunction','PolicyAssistantLogGroup'),
                            ('PolicyAssistantWorker','PolicyAssistantWorkerLogGroup'),
                            ('DocumentRecovery','DocumentRecoveryLogs')]:
        variables=resources[function]['Properties']['Environment']['Variables']
        checks.append((function+': data environment uses only new stack references', all(
            variables.get(key)=={'Ref':target} for key,target in {
                'POLICIES_TABLE_NAME':'PoliciesTable','DOCUMENT_METADATA_TABLE_NAME':'DocumentMetadata',
                'DOCUMENTS_BUCKET_NAME':'PolicyAssistantDocumentsBucket','DOCUMENT_QUEUE_URL':'PolicyAssistantDocumentQueue'}.items())))
        policy = resources[function+'LogWritePolicy']['Properties']
        statements = policy['PolicyDocument']['Statement']
        checks.append((function+': exact log-group permission',
            policy['Roles']==[{'Ref':function+'Role'}] and all(
                statement['Resource']=={'Fn::GetAtt':[group,'Arn']} and
                set(statement['Action'])=={'logs:CreateLogStream','logs:PutLogEvents'}
                for statement in statements)))
    statements = []
    for key, resource in resources.items():
        if resource['Type']=='AWS::IAM::Role':
            for policy in resource['Properties'].get('Policies',[]):
                statements += [(key,item) for item in policy['PolicyDocument']['Statement']]
        if resource['Type']=='AWS::IAM::Policy':
            statements += [(key,item) for item in resource['Properties']['PolicyDocument']['Statement']]
    broad = [(key,item) for key,item in statements if item.get('Effect')=='Allow' and (
        item.get('Resource')=='*' or '*' in (item.get('Resource') if isinstance(item.get('Resource'),list) else []))]
    checks.append(('No Allow Resource * in any runtime policy', not broad))
    for key in ['PoliciesTable','DocumentMetadata','PolicyAssistantDocumentsBucket','DocumentsBucketTlsPolicy']:
        checks.append((key+': retained on deletion/replacement',
            resources[key].get('DeletionPolicy')=='Retain' and resources[key].get('UpdateReplacePolicy')=='Retain'))
    deny = resources['DocumentsBucketTlsPolicy']['Properties']['PolicyDocument']['Statement'][0]
    checks.append(('Retained HTTPS deny remains attached to retained document bucket',
        resources['DocumentsBucketTlsPolicy']['Properties']['Bucket']=={'Ref':'PolicyAssistantDocumentsBucket'} and
        deny['Effect']=='Deny' and deny['Condition']['Bool']['aws:SecureTransport']=='false'))
    dlq = resources['PolicyAssistantDocumentDLQ']['Properties']['RedriveAllowPolicy']
    checks.append(('Only the deterministic same-stack queue can use DLQ',dlq=={
        'redrivePermission':'byQueue','sourceQueueArns':[{'Fn::Sub':'arn:${AWS::Partition}:sqs:${AWS::Region}:${AWS::AccountId}:${AWS::StackName}-document-queue'}]}))
    checks.append(('No cross-stack ImportValue', 'Fn::ImportValue' not in json.dumps(template)))
    # Verify resource dependency graph, including implicit Ref/GetAtt/Sub edges.
    def refs(value):
        found=set()
        if isinstance(value,dict):
            if 'Ref' in value and value['Ref'] in resources:found.add(value['Ref'])
            if 'Fn::GetAtt' in value:
                name=value['Fn::GetAtt'][0] if isinstance(value['Fn::GetAtt'],list) else value['Fn::GetAtt'].split('.')[0]
                if name in resources:found.add(name)
            if 'Fn::Sub' in value:
                text=value['Fn::Sub'] if isinstance(value['Fn::Sub'],str) else value['Fn::Sub'][0]
                found.update(name.split('.')[0] for name in re.findall(r'\$\{([^}]+)\}',text) if name.split('.')[0] in resources)
            for item in value.values():found.update(refs(item))
        elif isinstance(value,list):
            for item in value:found.update(refs(item))
        return found
    graph={key:refs(resource) for key,resource in resources.items()}
    for key,resource in resources.items():
        dependencies=resource.get('DependsOn',[])
        graph[key].update(name for name in ([dependencies] if isinstance(dependencies,str) else dependencies) if name in resources)
    visiting=set();done=set()
    def walk(key):
        if key in visiting:raise ValueError('Circular resource dependency')
        if key in done:return
        visiting.add(key)
        for dependency in graph[key]:walk(dependency)
        visiting.remove(key);done.add(key)
    try:
        for key in graph:walk(key)
        acyclic=True
    except ValueError:acyclic=False
    checks.append(('No circular resource dependencies',acyclic))
    return {'checks':[{'check':name,'passed':passed} for name,passed in checks],
        'passed':all(passed for _,passed in checks),'runtime_iam_allow_resource_star':broad,
        'roles':{key:role['Properties'] for key,role in roles.items()},
        'log_policies':{key:item['Properties'] for key,item in resources.items() if item['Type']=='AWS::IAM::Policy'},
        'active_resource_count':len(active_ids),
        'resource_counts':dict(collections.Counter(resources[key]['Type'] for key in active_ids)),
        'resource_inventory':[{'id':key,'type':resources[key]['Type'],'deletion_policy':resources[key].get('DeletionPolicy','Delete (default)'),
            'update_replace_policy':resources[key].get('UpdateReplacePolicy','Delete (default)')} for key in sorted(active_ids)],
        'remaining_scoped_wildcards':['LogGroup.Arn includes :* for streams inside the exact group',
            'S3 uploads/* and frontend-bucket object prefix only','API route/stage wildcard within the new API/account/region',
            'S3 TLS-only Deny uses Principal * and Action s3:* on the named bucket; not an Allow']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cached-processed',action='store_true',help='Audit the actual AWS template saved during creation; does not verify current AWS status')
    args=parser.parse_args()
    os.environ['AWS_EC2_METADATA_DISABLED']='true'
    state=json.loads((PRIVATE/'pending-change-set.json').read_text())
    session=boto3.Session(region_name='ap-southeast-1')
    config=Config(connect_timeout=5,read_timeout=20,retries={'max_attempts':1})
    account=state['account'] if args.cached_processed else session.client('sts',config=config).get_caller_identity()['Account']
    assert account==state['account'] and account.endswith('0098') and state['stack']=='policy-assistant-fcaj-test'
    cf=session.client('cloudformation',config=config)
    if args.cached_processed:
        summary=json.loads((ROOT/'docs/evidence/aws-test-change-set.json').read_text())
        assert summary['change_set_name']==state['change_set_name']
        plan={'Status':summary['status'],'ExecutionStatus':summary['execution_status'],'Changes':[{'ResourceChange':item} for item in summary['changes']]}
        raw=json.loads((PRIVATE/'processed-template.json').read_text())
    else:
        plan=cf.describe_change_set(StackName=state['stack'],ChangeSetName=state['change_set_name'])
        raw=cf.get_template(StackName=state['stack'],ChangeSetName=state['change_set_name'],TemplateStage='Processed')['TemplateBody']
    assert plan['Status']=='CREATE_COMPLETE' and plan['ExecutionStatus']=='AVAILABLE'
    assert all(change['ResourceChange']['Action']=='Add' for change in plan['Changes'])
    template=yaml.safe_load(raw) if isinstance(raw,str) else raw
    report=audit(template,{item['ResourceChange']['LogicalResourceId'] for item in plan['Changes']})
    report.update(observed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Actual processed CloudFormation candidate; not deployed or an effective-permission simulation',
        account_masked='********'+account[-4:],region='ap-southeast-1',stack=state['stack'],change_set=state['change_set_name'],execution_status=plan['ExecutionStatus'])
    report['fresh_aws_status_verified']=not args.cached_processed
    if args.cached_processed:
        report['processed_template_source']='Actual AWS processed template saved during candidate creation; cached audit only'
        report['existing_stack_readonly']={'fresh_recheck':'NOT_PERFORMED_IN_CACHED_MODE','no_write_to_existing_stack_performed':True}
    else:
        old=cf.describe_stacks(StackName='policy-assistant')['Stacks'][0]
        report['existing_stack_readonly']={'status':old['StackStatus'],'last_updated':str(old.get('LastUpdatedTime')),'no_write_to_existing_stack_performed':True}
    report=json.loads(json.dumps(report,default=str).replace(account,'[ACCOUNT]'))
    evidence=ROOT/'docs/evidence'
    (evidence/'aws-test-iam-review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for directory in ['policy_assistant','frontend'] for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    manifest['template.yaml']=hashlib.sha256((ROOT/'template.yaml').read_bytes()).hexdigest()
    (evidence/'aws-review-source-fingerprint.json').write_text(json.dumps({'scope':'Current candidate source fingerprint','files':manifest},indent=2)+'\n',encoding='utf-8')
    (evidence/'iac-review.patch').write_text(subprocess.check_output(['git','diff','--','template.yaml'],cwd=ROOT,text=True,encoding='utf-8'),encoding='utf-8')
    print(json.dumps({'candidate':state['change_set_name'],'status':plan['Status'],'execution_status':plan['ExecutionStatus'],'audit_passed':report['passed'],'resource_counts':report['resource_counts'],'failed_checks':[r['check'] for r in report['checks'] if not r['passed']]},indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        print('Read-only candidate audit blocked:',type(error).__name__,'(raw diagnostics withheld)')
        sys.exit(1)
