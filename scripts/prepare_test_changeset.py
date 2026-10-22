"""Upload reviewed artifacts and CREATE an isolated test change set; never execute it.

Requires the private artifact-target.json produced by the read-only account inspection.
No existing application stack or application data is modified.
"""
import datetime
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import boto3
from botocore.config import Config

ROOT = Path(__file__).resolve().parents[1]
REGION = 'ap-southeast-1'
STACK = 'policy-assistant-fcaj-test'
TABLE_PREFIX = STACK + '-'
PRIVATE = ROOT / '.aws-sam/test-review'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-pending', action='store_true', help='Allow a new candidate only for our own unexecuted test placeholder')
    args = parser.parse_args()
    os.environ['AWS_EC2_METADATA_DISABLED'] = 'true'
    session = boto3.Session(region_name=REGION)
    config = Config(connect_timeout=5, read_timeout=20, retries={'max_attempts':2})
    context = json.loads((PRIVATE / 'artifact-target.json').read_text(encoding='utf-8'))
    account = session.client('sts', config=config).get_caller_identity()['Account']
    if not account.endswith('0098') or account != context['account'] or context['region'] != REGION:
        raise RuntimeError('Account/region differs from the read-only review')
    cf = session.client('cloudformation', config=config)
    try:
        existing = cf.describe_stacks(StackName=STACK)['Stacks'][0]
    except cf.exceptions.ClientError as error:
        if error.response['Error']['Code'] != 'ValidationError' or 'does not exist' not in error.response['Error']['Message']:
            raise
    else:
        prior = json.loads((PRIVATE/'pending-change-set.json').read_text(encoding='utf-8')) if args.refresh_pending else None
        # Tags are attached on execution; a new REVIEW_IN_PROGRESS placeholder has none.
        # Bind to the exact private candidate/stack IDs instead of assuming tags exist.
        if not prior or prior['account'] != account or prior['stack'] != STACK or existing['StackStatus'] != 'REVIEW_IN_PROGRESS':
            raise RuntimeError('Test target exists outside the reviewed unexecuted placeholder')
        previous_plan = cf.describe_change_set(StackName=STACK,ChangeSetName=prior['change_set_name'])
        if previous_plan['StackId'] != existing['StackId'] or previous_plan['ChangeSetId'] != prior['change_set_id'] or previous_plan['ExecutionStatus'] != 'AVAILABLE':
            raise RuntimeError('Previous candidate is no longer an available unexecuted test plan')
    ddb = session.client('dynamodb', config=config)
    for suffix in ['Policies','DocumentMetadata']:
        try:
            ddb.describe_table(TableName=TABLE_PREFIX + suffix)
        except ddb.exceptions.ResourceNotFoundException:
            pass
        else:
            raise RuntimeError('Test table name is occupied; no shared data may be adopted')
    source_hash = hashlib.sha256((ROOT/'template.yaml').read_bytes() + (ROOT/'policy_assistant/app.py').read_bytes()).hexdigest()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
    name = f'fcaj-review-{stamp}-{source_hash[:8]}'
    artifact_prefix = f'{STACK}/reviews/{name}'
    command = [shutil.which('sam.cmd' if os.name == 'nt' else 'sam'), 'package',
        '--template-file',str(ROOT/'.aws-sam/build/template.yaml'), '--s3-bucket',context['bucket'],
        '--s3-prefix',artifact_prefix,'--region',REGION,'--no-resolve-s3',
        '--output-template-file',str(PRIVATE/'packaged.yaml')]
    completed = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    # CLI diagnostics can contain account/bucket details. Keep them outside report/source packages.
    (PRIVATE/'package-output.log').write_text(completed.stdout+'\n'+completed.stderr,encoding='utf-8')
    if completed.returncode:
        raise RuntimeError('SAM packaging failed; inspect private local diagnostics')
    body = (PRIVATE/'packaged.yaml').read_text(encoding='utf-8')
    if len(body.encode()) > 51200:
        raise RuntimeError('Packaged template exceeds TemplateBody limit; review template upload separately')
    response = cf.create_change_set(StackName=STACK,ChangeSetName=name,ChangeSetType='CREATE',
        Description='Isolated FCAJ test review only. Execution requires separate owner approval.',
        TemplateBody=body,Capabilities=['CAPABILITY_IAM'],
        Parameters=[{'ParameterKey':key,'ParameterValue':value} for key,value in {
            'TableNamePrefix':TABLE_PREFIX,'EnableOwnerIndex':'true',
            'LocalFrontendOrigin':'http://localhost:8080','AlertEmail':''}.items()],
        Tags=[{'Key':'Project','Value':'PolicyAssistant'},{'Key':'Environment','Value':'fcaj-test'},
              {'Key':'Purpose','Value':'FCAJ-demo-review'}],
        ClientToken=name)
    private_state={'account':account,'region':REGION,'stack':STACK,'change_set_name':name,
        'change_set_id':response['Id'],'source_hash':source_hash,'artifact_bucket':context['bucket'],
        'artifact_prefix':artifact_prefix,'parameters':{'TableNamePrefix':TABLE_PREFIX,'EnableOwnerIndex':'true','LocalFrontendOrigin':'http://localhost:8080','AlertEmail':''}}
    (PRIVATE/'pending-change-set.json').write_text(json.dumps(private_state,indent=2)+'\n',encoding='utf-8')
    print('Change set requested; no execution requested.',flush=True)
    for _ in range(90):
        plan=cf.describe_change_set(StackName=STACK,ChangeSetName=name)
        if plan['Status'] in ['CREATE_COMPLETE','FAILED']:
            break
        time.sleep(2)
    def sanitized(value):
        return json.loads(json.dumps(value,default=str).replace(account,'[ACCOUNT]'))
    evidence=ROOT/'docs/evidence'
    summary={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'account_masked':'********'+account[-4:],'region':REGION,'stack':STACK,'change_set_name':name,
        'change_set_type':'CREATE','status':plan['Status'],'execution_status':plan['ExecutionStatus'],
        'source_hash':source_hash,'parameters':private_state['parameters'],
        'changes':[change['ResourceChange'] for change in plan.get('Changes',[])],
        'cloud_writes_performed':['Uploaded built code under isolated prefix in existing artifact bucket','Created unexecuted CREATE change set and REVIEW_IN_PROGRESS stack placeholder'],
        'application_deployed':False,'existing_stack_modified':False}
    (evidence/'aws-test-change-set.json').write_text(json.dumps(sanitized(summary),indent=2)+'\n',encoding='utf-8')
    if plan['Status']=='CREATE_COMPLETE':
        processed=cf.get_template(StackName=STACK,ChangeSetName=name,TemplateStage='Processed')['TemplateBody']
        (PRIVATE/'processed-template.json').write_text(json.dumps(processed,default=str,indent=2),encoding='utf-8')
        # Processed resource properties are reviewed locally; only redacted IAM data is exported next.
    print(json.dumps({'stack':STACK,'change_set':name,'status':plan['Status'],'execution_status':plan['ExecutionStatus'],'resource_changes':len(summary['changes'])}))
    return 0 if plan['Status']=='CREATE_COMPLETE' else 1


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print('Preparation stopped:',type(error).__name__,'(raw AWS diagnostics withheld)')
        sys.exit(1)
