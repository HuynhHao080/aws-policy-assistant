"""Guarded validity API checks using only non-current synthetic policies.

Creates one invitation-suppressed identity and three nonce-owned inactive rows.
Never calls /ask, publish, embedding, OCR or any model. Does not read private PDFs.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import time
from uuid import uuid4
import zipfile

from boto3.dynamodb.types import TypeSerializer
import requests

from check_admin_live import aws, UserNotFound

ROOT = Path(__file__).resolve().parents[1]


def main():
    stack = aws('cloudformation', 'describe-stacks', StackName='policy-assistant')['Stacks'][0]
    assert stack['StackStatus'] == 'UPDATE_COMPLETE' and stack['StackId'].split(':')[4] == '629380420098'
    outputs = {r['OutputKey']: r['OutputValue'] for r in stack['Outputs']}
    base = outputs['PolicyAssistantApiUrl'].rstrip('/')
    assert base == 'https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod'
    release = json.loads((ROOT / '.deployment/release.json').read_text())
    binary = ROOT / '.deployment/lambda.zip'
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == release['code_sha256']
    with zipfile.ZipFile(binary) as archive:
        assert archive.read('policy_validity.py') == (ROOT / 'policy_assistant/policy_validity.py').read_bytes()
        assert archive.read('app.py') == (ROOT / 'policy_assistant/app.py').read_bytes()
        assert archive.read('assistant.py') == (ROOT / 'policy_assistant/assistant.py').read_bytes()
    function = aws('cloudformation', 'describe-stack-resource', StackName='policy-assistant', LogicalResourceId='PolicyAssistantFunction')['StackResourceDetail']['PhysicalResourceId']
    cfg = aws('lambda', 'get-function-configuration', FunctionName=function)
    assert base64.b64decode(cfg['CodeSha256']).hex() == release['code_sha256'] and cfg['LastUpdateStatus'] == 'Successful'
    assert cfg['Environment']['Variables'].get('REQUIRE_PUBLISHED_POLICIES') == 'true'
    # No fixture is written until the exact validity-aware deployment is proven.
    nonce = uuid4().hex
    username = 'validity-qa-' + nonce + '@example.invalid'
    password = secrets.token_urlsafe(25) + 'Aa1!'
    created = cleaned = False
    token = None
    seeded = []
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'release': release,
              'scope': 'Real API authorization/read/draft validation; one disposable identity, three never-current synthetic policy rows. No model, publish, PDF/OCR or email calls. Operator seeds are not publication/embedding acceptance.',
              'checks': [], 'http_passed': False, 'accounts_cleaned': False, 'policies_cleaned': False}
    state = ROOT / '.deployment/policy-validity'
    state.mkdir(parents=True, exist_ok=True)

    def save():
        (state / 'live-acceptance.json').write_text(json.dumps(report, indent=2) + '\n')
        (state / 'cleanup.json').write_text(json.dumps({'pool': outputs['UserPoolId'], 'username': username, 'created': created, 'cleaned': cleaned, 'nonce': nonce, 'seeded_ids': seeded}, indent=2) + '\n')

    def check(label, condition):
        if not condition:
            raise RuntimeError('Check failed: ' + label)
        report['checks'].append(label)
        save()
        print('PASS ' + label, flush=True)

    def login():
        return aws('cognito-idp', 'initiate-auth', ClientId=outputs['UserPoolClientId'], AuthFlow='USER_PASSWORD_AUTH', AuthParameters={'USERNAME': username, 'PASSWORD': password})['AuthenticationResult']['IdToken']

    def call(path, method='GET', body=None, anonymous=False):
        headers = {'Origin': outputs['FrontendUrl'].rstrip('/')}
        if not anonymous:
            headers['Authorization'] = 'Bearer ' + token
        response = requests.request(method, base + path, json=body, headers=headers, timeout=30)
        return response.status_code, response.json()

    def listing_ids(validity):
        ids = set()
        cursor = None
        for _ in range(20):
            query = '?limit=50&validity=' + validity
            if cursor:
                query += '&next_token=' + requests.utils.quote(cursor, safe='')
            code, result = call('/admin/policies' + query)
            assert code == 200
            ids.update(row['policy_id'] for row in result['policies'])
            cursor = result.get('next_token')
            if not cursor:
                return ids
        raise RuntimeError('Bounded catalogue scan incomplete')

    table = outputs['PoliciesTableName']
    serialize = TypeSerializer().serialize
    fixtures = {}
    try:
        check('Anonymous administrator catalogue is rejected', call('/admin/policies', anonymous=True)[0] == 401)
        aws('cognito-idp', 'admin-create-user', UserPoolId=outputs['UserPoolId'], Username=username, MessageAction='SUPPRESS', UserAttributes=[{'Name': 'email', 'Value': username}, {'Name': 'email_verified', 'Value': 'true'}])
        created = True
        save()
        aws('cognito-idp', 'admin-set-user-password', UserPoolId=outputs['UserPoolId'], Username=username, Password=password, Permanent=True)
        token = login()
        check('Customer cannot inspect administrator validity metadata', call('/admin/policies?validity=expired')[0] == 403)
        for kind, dates in [('upcoming', {'effective_from': '9000-01-01'}), ('expired', {'effective_until': '2000-01-01'}), ('invalid', {'effective_until': 'invalid-qa-date'})]:
            policy_id = 'QA-VALIDITY-' + nonce[:16] + '-' + kind
            fields = {'title': 'SYNTHETIC QA — NOT A BUSINESS POLICY', 'category': 'QA', 'content': 'Synthetic acceptance fixture only. Never current, not for customer transactions.', 'keywords': ['qa-validity-' + nonce]}
            item = {'policy_id': policy_id, **fields, **dates, 'publication_state': 'published', 'revision': nonce + '-' + kind, 'qa_nonce': nonce,
                    'title_lower': fields['title'].lower(), 'category_lower': 'qa', 'content_lower': fields['content'].lower(), 'keywords_lower': fields['keywords']}
            aws('dynamodb', 'put-item', TableName=table, Item={k: serialize(v) for k, v in item.items()}, ConditionExpression='attribute_not_exists(policy_id)')
            seeded.append(policy_id)
            fixtures[kind] = (policy_id, fields)
            save()
            check('Public lookup hides ' + kind + ' source', call('/policies/' + policy_id)[0] == 404)
        aws('cognito-idp', 'admin-add-user-to-group', UserPoolId=outputs['UserPoolId'], Username=username, GroupName='administrators')
        token = login()
        for kind, (policy_id, fields) in fixtures.items():
            code, detail = call('/admin/policies/' + policy_id)
            check('Administrator sees computed ' + kind + ' status', code == 200 and detail['validity_state'] == kind)
            found = listing_ids(kind)
            check('Catalogue filter selects only matching QA ' + kind, policy_id in found and not any(other in found for name, (other, _) in fixtures.items() if name != kind))
        policy_id, fields = fixtures['upcoming']
        code, detail = call('/admin/policies/' + policy_id)
        check('Unknown validity filter is rejected', call('/admin/policies?validity=invented')[0] == 400)
        check('Impossible date is rejected before saving', call('/admin/policies/' + policy_id, 'PATCH', {'action': 'save_draft', 'expected_revision': detail['revision'], 'draft': {**fields, 'effective_until': '2026-02-30'}})[0] == 400)
        check('Stale revision cannot change a window', call('/admin/policies/' + policy_id, 'PATCH', {'action': 'save_draft', 'expected_revision': 'stale', 'draft': fields})[0] == 409)
        code, draft = call('/admin/policies/' + policy_id, 'PATCH', {'action': 'save_draft', 'expected_revision': detail['revision'], 'draft': {**fields, 'effective_from': '', 'effective_until': ''}})
        check('Draft date clearing leaves the published future window intact', code == 200 and draft['validity_state'] == 'upcoming' and 'effective_from' not in draft['draft'] and draft['current']['effective_from'] == '9000-01-01')
        check('Administrator role does not bypass public date checks', call('/policies/' + policy_id)[0] == 404)
        report['http_passed'] = True
    except Exception as exc:
        report['error_type'] = type(exc).__name__
        print('Validity acceptance stopped: ' + type(exc).__name__, flush=True)
    finally:
        policies_cleaned = True
        for policy_id in seeded:
            try:
                aws('dynamodb', 'delete-item', TableName=table, Key={'policy_id': {'S': policy_id}}, ConditionExpression='qa_nonce=:nonce', ExpressionAttributeValues={':nonce': {'S': nonce}})
                if aws('dynamodb', 'get-item', TableName=table, Key={'policy_id': {'S': policy_id}}, ConsistentRead=True).get('Item'):
                    policies_cleaned = False
            except Exception:
                policies_cleaned = False
        report['policies_cleaned'] = policies_cleaned
        if created:
            try:
                if not token:
                    token = login()
                assert call('/account/delete', 'POST', {'confirmation': 'DELETE'})[0] == 200
                deadline = time.monotonic() + 300
                while time.monotonic() < deadline:
                    try:
                        aws('cognito-idp', 'admin-get-user', UserPoolId=outputs['UserPoolId'], Username=username)
                    except UserNotFound:
                        cleaned = True
                        break
                    time.sleep(5)
            except Exception as exc:
                report['account_cleanup_error_type'] = type(exc).__name__
        report['accounts_cleaned'] = not created or cleaned
        save()
        print('Cleanup:', report['accounts_cleaned'], report['policies_cleaned'], flush=True)
    if not all(report[k] for k in ('http_passed', 'accounts_cleaned', 'policies_cleaned')):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
