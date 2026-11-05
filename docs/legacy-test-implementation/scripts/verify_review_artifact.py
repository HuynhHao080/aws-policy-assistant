"""Read-only verification of the pending candidate and its Lambda ZIPs; no AWS writes."""
import datetime
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse
import zipfile

import boto3
from botocore.config import Config
import yaml


class CfnLoader(yaml.SafeLoader):
    pass


def intrinsic(loader, tag, node):
    value = (loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode)
             else loader.construct_sequence(node) if isinstance(node, yaml.SequenceNode)
             else loader.construct_mapping(node))
    name = tag if tag in ['Ref', 'Condition'] else 'Fn::' + tag
    if tag == 'GetAtt' and isinstance(value, str):
        value = value.split('.', 1)
    return {name: value}


CfnLoader.add_multi_constructor('!', intrinsic)


def yaml_parse(value):
    return yaml.load(value, Loader=CfnLoader)

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / '.aws-sam/test-review'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--independent-reads', action='store_true',
                        help='Read CFN/S3 without retrying blocked STS; never claims STS identity verified')
    args = parser.parse_args()
    state = json.loads((PRIVATE / 'pending-change-set.json').read_text())
    report = {'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'candidate': state['change_set_name'], 'scope': 'Read-only candidate and artifact integrity verification',
              'status': 'BLOCKED', 'checks': [], 'expected_account_masked': '********0098', 'region': 'ap-southeast-1'}
    phase = 'local source fingerprint'
    try:
        source_hash = hashlib.sha256((ROOT / 'template.yaml').read_bytes() + (ROOT / 'policy_assistant/app.py').read_bytes()).hexdigest()
        assert source_hash == state['source_hash'], 'Source differs from candidate'
        report['checks'].append({'check': phase, 'passed': True, 'sha256': source_hash})
        os.environ['AWS_EC2_METADATA_DISABLED'] = 'true'
        session = boto3.Session(region_name='ap-southeast-1')
        config = Config(connect_timeout=5, read_timeout=20, retries={'max_attempts': 1})
        account = state['account']
        if not args.independent_reads:
            phase = 'STS account identity'
            account = session.client('sts', config=config).get_caller_identity()['Account']
            assert account == state['account'] and account.endswith('0098')
            report['checks'].append({'check': phase, 'passed': True})
            report['identity_verification'] = 'VERIFIED_STS'
        else:
            report['checks'].append({'check': 'STS account identity', 'status': 'BLOCKED',
                                     'note': 'Not retried; preceding attempt timed out. CFN ARN identity must be checked separately.'})
            report['identity_verification'] = 'NOT_VERIFIED_BY_STS'
        assert account.endswith('0098')
        assert state['region'] == 'ap-southeast-1' and state['stack'] == 'policy-assistant-fcaj-test'
        cf = session.client('cloudformation', config=config)
        phase = 'live candidate identity and actions'
        plan = cf.describe_change_set(StackName=state['stack'], ChangeSetName=state['change_set_name'])
        assert plan['ChangeSetId'] == state['change_set_id']
        for arn in [plan['ChangeSetId'], plan['StackId']]:
            parts = arn.split(':', 5)
            assert parts[2:5] == ['cloudformation', 'ap-southeast-1', account]
        assert plan['StackName'] == state['stack']
        report['candidate_arn_identity'] = 'VERIFIED_EXPECTED_ACCOUNT_REGION_STACK'
        assert plan['Status'] == 'CREATE_COMPLETE' and plan['ExecutionStatus'] == 'AVAILABLE'
        changes = [item['ResourceChange'] for item in plan['Changes']]
        assert len(changes) == 45 and all(item['Action'] == 'Add' and item.get('Replacement') not in ['True', 'Conditional'] for item in changes)
        report['checks'].append({'check': phase, 'passed': True, 'status': plan['Status'],
                                 'execution_status': plan['ExecutionStatus'], 'add': 45, 'modify_remove_replace': 0})
        phase = 'original candidate matches packaged template'
        original = cf.get_template(StackName=state['stack'], ChangeSetName=state['change_set_name'], TemplateStage='Original')['TemplateBody']
        original = yaml_parse(original) if isinstance(original, str) else original
        packaged = yaml_parse((PRIVATE / 'packaged.yaml').read_text())
        assert original == packaged
        report['checks'].append({'check': phase, 'passed': True})
        phase = 'processed candidate matches saved AWS template'
        processed = cf.get_template(StackName=state['stack'], ChangeSetName=state['change_set_name'], TemplateStage='Processed')['TemplateBody']
        processed = yaml_parse(processed) if isinstance(processed, str) else processed
        cached = json.loads((PRIVATE / 'processed-template.json').read_text())
        cached = yaml_parse(cached) if isinstance(cached, str) else cached
        assert processed == cached
        report['checks'].append({'check': phase, 'passed': True})
        phase = 'live processed IAM SQS S3 and resource isolation audit'
        from scripts.review_test_candidate import audit
        audited = audit(processed, {item['LogicalResourceId'] for item in changes})
        assert audited['passed']
        audited = json.loads(json.dumps(audited, default=str).replace(account, '[ACCOUNT]'))
        report['processed_audit'] = audited
        report['checks'].append({'check': phase, 'passed': True})
        phase = 'S3 ZIP contents match all local built functions'
        s3 = session.client('s3', config=config)
        downloaded = {}
        verified_functions = 0
        for logical_id, resource in packaged['Resources'].items():
            if resource['Type'] != 'AWS::Serverless::Function':
                continue
            uri = urlparse(resource['Properties']['CodeUri'])
            assert uri.scheme == 's3' and uri.netloc == state['artifact_bucket']
            key = uri.path.lstrip('/')
            assert key.startswith(state['artifact_prefix'] + '/')
            code = processed['Resources'][logical_id]['Properties']['Code']
            assert code['S3Bucket'] == uri.netloc and code['S3Key'] == key
            if key not in downloaded:
                body = s3.get_object(Bucket=uri.netloc, Key=key)['Body'].read()
                downloaded[key] = body
            body = downloaded[key]
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                actual = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist() if not name.endswith('/')}
            directory = ROOT / '.aws-sam/build' / logical_id
            expected = {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in directory.rglob('*') if p.is_file()}
            assert actual == expected, 'Archive differs from built function'
            report['checks'].append({'check': phase, 'function': logical_id, 'passed': True,
                                     'zip_sha256': hashlib.sha256(body).hexdigest(), 'files': len(actual), 'bytes': len(body)})
            verified_functions += 1
        assert verified_functions == 3
        phase = 'existing stack read-only status'
        old = cf.describe_stacks(StackName='policy-assistant')['Stacks'][0]
        report['checks'].append({'check': phase, 'passed': True, 'status': old['StackStatus'],
                                 'last_updated': str(old.get('LastUpdatedTime'))})
        report['status'] = 'PARTIAL' if args.independent_reads else 'PASS'
    except Exception as error:
        if isinstance(error, AssertionError):
            report['status'] = 'FAIL'
        report['blocked_phase'] = phase
        report['error_type'] = type(error).__name__
        # Raw exceptions can contain signed request details; never publish them.
    report['completed_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (ROOT / 'docs/evidence/aws-review-artifact-fingerprint.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
