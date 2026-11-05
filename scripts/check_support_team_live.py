"""Guarded support collaboration checks: three disposable users, one owned ticket.

No real customer is contacted; invitations are suppressed. No model/PDF/OCR call.
Attempt markers precede identity creation; account purges cover ambiguous ticket writes.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import time
from uuid import uuid4
import zipfile

import requests
from check_admin_live import aws, UserNotFound

ROOT = Path(__file__).resolve().parents[1]


def main():
    stack = aws('cloudformation', 'describe-stacks', StackName='policy-assistant')['Stacks'][0]
    assert stack['StackStatus'] == 'UPDATE_COMPLETE' and stack['StackId'].split(':')[4] == '629380420098'
    out = {x['OutputKey']: x['OutputValue'] for x in stack['Outputs']}
    base = out['PolicyAssistantApiUrl'].rstrip('/')
    assert base == 'https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod'
    release = json.loads((ROOT / '.deployment/release.json').read_text())
    binary = ROOT / '.deployment/lambda.zip'
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == release['code_sha256']
    with zipfile.ZipFile(binary) as archive:
        assert archive.read('tickets.py') == (ROOT / 'policy_assistant/tickets.py').read_bytes()
    fn = aws('cloudformation', 'describe-stack-resource', StackName='policy-assistant', LogicalResourceId='PolicyAssistantFunction')['StackResourceDetail']['PhysicalResourceId']
    cfg = aws('lambda', 'get-function-configuration', FunctionName=fn)
    assert cfg['LastUpdateStatus'] == 'Successful' and base64.b64decode(cfg['CodeSha256']).hex() == release['code_sha256']
    assert cfg['Environment']['Variables']['SUPPORT_TABLE_NAME'] == out['SupportTableName']
    nonce = uuid4().hex
    users = {role: {'name': 'team-qa-' + nonce + '-' + role + '@example.invalid', 'password': secrets.token_urlsafe(25) + 'Aa1!',
                    'attempted': False, 'created': False, 'app_used': False, 'cleaned': False, 'token': None, 'sub': None}
             for role in ('customer', 'a', 'b')}
    state = ROOT / '.deployment/support-team'
    state.mkdir(parents=True, exist_ok=True)
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'release': release,
              'scope': 'One synthetic consented support ticket and three invitation-suppressed identities (customer/two staff). Real HTTP privacy, assignment, note, revision and cleanup checks; no real customer, model, embedding, PDF/OCR or email operation.',
              'checks': [], 'http_passed': False, 'accounts_cleaned': False, 'support_purged': False}
    ticket_id = None

    def save():
        (state / 'live-acceptance.json').write_text(json.dumps(report, indent=2) + '\n')
        (state / 'cleanup.json').write_text(json.dumps({'pool': out['UserPoolId'], 'nonce': nonce, 'ticket_id': ticket_id,
            'users': [{key: u[key] for key in ('name', 'sub', 'attempted', 'created', 'app_used', 'cleaned')} for u in users.values()]}, indent=2) + '\n')

    def check(label, passed):
        if not passed:
            raise RuntimeError('Check failed: ' + label)
        report['checks'].append(label)
        save()
        print('PASS ' + label, flush=True)

    def login(role):
        u = users[role]
        u['token'] = aws('cognito-idp', 'initiate-auth', ClientId=out['UserPoolClientId'], AuthFlow='USER_PASSWORD_AUTH', AuthParameters={'USERNAME': u['name'], 'PASSWORD': u['password']})['AuthenticationResult']['IdToken']
        u['sub'] = json.loads(base64.urlsafe_b64decode(u['token'].split('.')[1] + '=='))['sub']
        save()

    def call(role, path, method='GET', body=None, auth=True):
        assert path.startswith(('/tickets', '/admin/tickets', '/admin/audit', '/account/delete'))
        headers = {'Origin': out['FrontendUrl'].rstrip('/')}
        if auth:
            users[role]['app_used'] = True
            save()
            headers['Authorization'] = 'Bearer ' + users[role]['token']
        r = requests.request(method, base + path, json=body, headers=headers, timeout=35)
        return r.status_code, r.json()

    def ok(role, path, method='GET', body=None):
        code, result = call(role, path, method, body)
        if code != 200:
            raise RuntimeError('Unexpected API status ' + str(code))
        return result

    def mutation(role, action, record, **fields):
        return call(role, staff_path, 'PATCH', {'action': action, 'expected_revision': record['revision'], **fields})

    def queue(role, scope):
        found, cursor = set(), None
        for _ in range(20):
            path = '/admin/tickets?limit=50&assignee=' + scope
            if cursor:
                path += '&next_token=' + requests.utils.quote(cursor, safe='')
            page = ok(role, path)
            found.update(r['ticket_id'] for r in page['tickets'])
            cursor = page.get('next_token')
            if not cursor:
                return found
        raise RuntimeError('Bounded support queue scan incomplete')

    private = 'PRIVATE-TEAM-NOTE-' + nonce
    reason = 'SYNTHETIC-STAFF-HANDOVER-' + nonce
    try:
        check('Anonymous staff queue rejected', call('customer', '/admin/tickets', auth=False)[0] == 401)
        for role, u in users.items():
            try:
                aws('cognito-idp', 'admin-get-user', UserPoolId=out['UserPoolId'], Username=u['name'])
                raise RuntimeError('Planned disposable identity already exists')
            except UserNotFound:
                pass
            u['attempted'] = True
            save()
            aws('cognito-idp', 'admin-create-user', UserPoolId=out['UserPoolId'], Username=u['name'], MessageAction='SUPPRESS', UserAttributes=[{'Name': 'email', 'Value': u['name']}, {'Name': 'email_verified', 'Value': 'true'}])
            u['created'] = True
            save()
            aws('cognito-idp', 'admin-set-user-password', UserPoolId=out['UserPoolId'], Username=u['name'], Password=u['password'], Permanent=True)
            if role != 'customer':
                aws('cognito-idp', 'admin-add-user-to-group', UserPoolId=out['UserPoolId'], Username=u['name'], GroupName='administrators')
            login(role)
        check('Customer cannot inspect staff queue', call('customer', '/admin/tickets')[0] == 403)
        original = ok('customer', '/tickets', 'POST', {'subject': 'SYNTHETIC QA SUPPORT — ' + nonce[:8], 'message': 'Synthetic consented request, not a real order or policy.', 'consent': True})
        ticket_id = original['ticket_id']
        assert re.fullmatch(r't-[0-9]{20}-[a-f0-9]{32}', ticket_id)
        save()
        customer_path = '/tickets/' + ticket_id
        staff_path = '/admin/tickets/' + users['customer']['sub'] + '/' + ticket_id
        check('Customer cannot call private-note action', call('customer', customer_path, 'PATCH', {'action': 'note', 'note': private, 'expected_revision': original['revision']})[0] == 400)
        r = ok('a', staff_path)
        code, claimed = mutation('a', 'claim', r)
        check('First staff claim uses its authenticated identity', code == 200 and claimed['assignment'] == 'mine' and claimed['assigned_to'] == users['a']['sub'])
        other = ok('b', staff_path)
        check('Second staff sees another assignee', other['assignment'] == 'other')
        check('Second staff cannot double claim', mutation('b', 'claim', other)[0] == 409)
        check('Other assignee cannot send a public reply', mutation('b', 'update', other, status='resolved', message='Must never reach customer')[0] == 409)
        code, noted = mutation('b', 'note', other, note=private)
        check('Collaborator can add an internal note', code == 200 and noted['internal_note_count'] == 1 and noted['internal_notes'][0]['body'] == private)
        customer = ok('customer', customer_path)
        own_list = ok('customer', '/tickets')
        private_keys = {'assigned_to', 'assigned_at', 'assignment', 'assignment_events', 'internal_notes', 'internal_note_count', 'staff_updated_at'}
        check('Customer detail/list export data excludes internal metadata', not private_keys.intersection(customer) and all(not private_keys.intersection(row) for row in own_list['tickets']) and private not in json.dumps([customer, own_list]))
        check('Internal action preserves public timestamps, message count and retention', customer['updated_at'] == original['updated_at'] and customer['message_count'] == 1 and customer['expires_at'] == original['expires_at'])
        check('Opaque revision prevents stale overwrite after an internal note', mutation('a', 'update', claimed, status='resolved', message='Stale message')[0] == 409)
        current = ok('b', staff_path)
        check('Handover requires a meaningful reason', mutation('b', 'takeover', current, reason='short')[0] == 400)
        code, taken = mutation('b', 'takeover', current, reason=reason)
        check('Explicit handover changes assignee and retains internal reason', code == 200 and taken['assignment'] == 'mine' and taken['assignment_events'][-1]['reason'] == reason)
        check('Former assignee cannot release another staff member', mutation('a', 'release', ok('a', staff_path))[0] == 409)
        check('Mine/other queue filters follow authenticated staff', ticket_id in queue('b', 'mine') and ticket_id in queue('a', 'other') and ticket_id not in queue('a', 'unassigned'))
        code, replied = mutation('b', 'update', taken, status='in_progress', message='Synthetic public staff response')
        check('Assigned staff can reply without exposing notes', code == 200 and replied['message_count'] == 2)
        customer = ok('customer', customer_path)
        check('Customer receives public reply only', customer['messages'][-1]['body'] == 'Synthetic public staff response' and private not in json.dumps(customer) and reason not in json.dumps(customer))
        customer = ok('customer', customer_path, 'PATCH', {'expected_revision': customer['revision'], 'message': 'Synthetic customer follow-up'})
        current = ok('b', staff_path)
        check('Customer follow-up preserves private notes and assignment', customer['message_count'] == 3 and current['internal_note_count'] == 1 and current['assigned_to'] == users['b']['sub'])
        code, released = mutation('b', 'release', current)
        check('Current assignee can release to unassigned queue', code == 200 and released['assignment'] == 'unassigned' and ticket_id in queue('a', 'unassigned'))
        audit = ok('a', '/admin/audit?limit=50')
        check('Audit stores actions rather than note or reason text', private not in json.dumps(audit) and reason not in json.dumps(audit) and 'ticket.note' in json.dumps(audit))
        report['http_passed'] = True
    except Exception as exc:
        report['error_type'] = type(exc).__name__
        print('Support team acceptance stopped: ' + type(exc).__name__, flush=True)
    finally:
        for role, u in users.items():
            if not u['attempted']:
                continue
            try:
                try:
                    record = aws('cognito-idp', 'admin-get-user', UserPoolId=out['UserPoolId'], Username=u['name'])
                except UserNotFound:
                    u['cleaned'] = True
                    continue
                attrs = {a['Name']: a['Value'] for a in record.get('UserAttributes', [])}
                assert attrs.get('email') == u['name'] and nonce in u['name']
                if not u['app_used']:
                    # No authenticated application request existed; also covers an
                    # ambiguous create/password failure after the durable marker.
                    aws('cognito-idp', 'admin-delete-user', UserPoolId=out['UserPoolId'], Username=u['name'])
                else:
                    try:
                        if not u['token']:
                            login(role)
                        call(role, '/account/delete', 'POST', {'confirmation': 'DELETE'})
                    except Exception as exc:
                        report['cleanup_request_' + role] = type(exc).__name__
                deadline = time.monotonic() + 240
                while time.monotonic() < deadline:
                    try:
                        aws('cognito-idp', 'admin-get-user', UserPoolId=out['UserPoolId'], Username=u['name'])
                    except UserNotFound:
                        u['cleaned'] = True
                        break
                    time.sleep(5)
            except Exception as exc:
                report['cleanup_error_' + role] = type(exc).__name__
            save()
        report['accounts_cleaned'] = all(not u['attempted'] or u['cleaned'] for u in users.values())
        if users['customer']['sub']:
            try:
                remaining = aws('dynamodb', 'query', TableName=out['SupportTableName'], KeyConditionExpression='owner_id=:owner', ExpressionAttributeValues={':owner': {'S': users['customer']['sub']}}, ProjectionExpression='owner_id,ticket_id', ConsistentRead=True, Limit=1)['Items']
                report['support_purged'] = not remaining
            except Exception as exc:
                report['support_cleanup_error'] = type(exc).__name__
        else:
            report['support_purged'] = not users['customer']['app_used']
        save()
        print('Synthetic cleanup:', report['accounts_cleaned'], report['support_purged'], flush=True)
    if not all(report[k] for k in ('http_passed', 'accounts_cleaned', 'support_purged')):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
