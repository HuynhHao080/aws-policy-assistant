"""Assignment coordination, internal-note isolation and atomic race guards."""
import json
import time
import boto3
import pytest

from policy_assistant import app, tickets
from tests.unit.test_tickets import support, create, path, ADMIN  # noqa: F401
from tests.unit.test_public_app import request, services, ai  # noqa: F401


def staff(item, actor='staff-a'):
    code, result = request(path(item, True), owner=actor, claims=ADMIN)
    assert code == 200
    return result


def action(item, kind, actor='staff-a', **extra):
    return request(path(item, True), 'PATCH', owner=actor, claims=ADMIN,
                   data={'action': kind, 'expected_revision': item['revision'], **extra})


def test_claim_takeover_release_and_public_reply_coordination(support):
    original = create()
    code, claimed = action(original, 'claim')
    assert code == 200 and claimed['assignment'] == 'mine' and claimed['assigned_to'] == 'staff-a'
    other = staff(original, 'staff-b')
    assert other['assignment'] == 'other'
    assert action(other, 'claim', 'staff-b')[0] == 409
    assert action(other, 'release', 'staff-b')[0] == 409
    assert action(other, 'update', 'staff-b', status='resolved', message='Must not be sent')[0] == 409
    assert action(other, 'takeover', 'staff-b', reason='short')[0] == 400
    code, taken = action(other, 'takeover', 'staff-b', reason='Previous staff finished their shift.')
    assert code == 200 and taken['assignment'] == 'mine' and taken['assigned_to'] == 'staff-b'
    assert taken['assignment_events'][-1]['from'] == 'staff-a'
    assert action(taken, 'update', 'staff-b', status='in_progress', message='Public staff reply')[0] == 200
    code, released = action(staff(original, 'staff-b'), 'release', 'staff-b')
    assert code == 200 and released['assignment'] == 'unassigned' and 'assigned_to' not in released
    assert released['expires_at'] == original['expires_at']
    events = request('/admin/audit', owner='staff-a', claims=ADMIN)[1]['events']
    assert {'ticket.claim', 'ticket.takeover', 'ticket.release'}.issubset({e['action'] for e in events})
    assert 'Previous staff' not in json.dumps(events)


def test_internal_note_is_not_a_customer_message_and_never_leaks_into_exports(support):
    original = create()
    marker = 'PRIVATE-STAFF-NOTE-NOT-FOR-CUSTOMER'
    code, noted = action(original, 'note', note=marker)
    assert code == 200 and noted['internal_note_count'] == 1 and noted['internal_notes'][0]['author'] == 'staff-a'
    assert noted['message_count'] == original['message_count']
    assert noted['updated_at'] == original['updated_at'] and noted['expires_at'] == original['expires_at']
    customer = request(path(original))[1]
    customer_admin_role = request(path(original), claims=ADMIN)[1]
    listing = request('/tickets')[1]
    for result in (customer, customer_admin_role, listing):
        raw = json.dumps(result)
        assert marker not in raw and 'staff-a' not in raw
        for key in ('internal_notes', 'internal_note_count', 'assigned_to', 'assignment_events', 'staff_updated_at'):
            assert key not in raw
    assert customer['revision'] != original['revision']  # One opaque revision protects the whole item.
    summary = request('/admin/tickets', owner='staff-a', claims=ADMIN)[1]['tickets'][0]
    assert summary['internal_note_count'] == 1 and 'internal_notes' not in summary
    audit = request('/admin/audit', owner='staff-a', claims=ADMIN)[1]['events']
    assert 'ticket.note' in json.dumps(audit) and marker not in json.dumps(audit)


def test_collaborator_can_add_private_note_but_not_reply_until_handover(support):
    original = create()
    _, claimed = action(original, 'claim')
    code, noted = action(staff(original, 'staff-b'), 'note', 'staff-b', note='Internal collaboration only')
    assert code == 200 and noted['assignment'] == 'other' and noted['assigned_to'] == 'staff-a'
    assert action(noted, 'update', 'staff-b', status='resolved', message='Blocked')[0] == 409
    assert action(claimed, 'release')[0] == 409  # Internal note also advances the revision.


@pytest.mark.parametrize('fields', [
    {'assigned_to': 'staff-a'}, {'internal_notes': []}, {'assignment_events': []},
    {'note': 'Forged internal text'}, {'reason': 'Forged handover reason'},
])
def test_customer_cannot_create_staff_metadata(support, fields):
    assert request('/tickets', 'POST', data={'subject': 'Test', 'message': 'Shared', 'consent': True, **fields})[0] == 400
    assert support.scan()['Items'] == []


@pytest.mark.parametrize('payload', [
    {'action': 'claim'}, {'action': 'note', 'note': 'Forged'},
    {'action': 'takeover', 'reason': 'Forged reason for takeover'},
    {'action': 'reply', 'message': 'Public', 'assigned_to': 'staff-a'},
])
def test_customer_cannot_mutate_private_fields_or_other_accounts(support, payload):
    original = create()
    data = {'expected_revision': original['revision'], **payload}
    assert request(path(original), 'PATCH', data=data)[0] == 400
    assert request(path(original), 'PATCH', owner='bob', data=data)[0] == 404
    assert staff(original)['internal_notes'] == []


@pytest.mark.parametrize('kind,fields', [
    ('claim', {'assigned_to': 'someone-else'}),
    ('note', {'note': ''}), ('note', {'note': 'x' * 1001}),
    ('note', {'note': 'Private', 'message': 'Accidental public reply'}),
    ('update', {'internal_notes': [], 'status': 'open'}),
])
def test_staff_actions_validate_body_and_reject_mixed_public_private_payloads(support, kind, fields):
    original = create()
    assert action(original, kind, **fields)[0] == 400
    assert staff(original)['revision'] == original['revision']


def test_assignment_filters_combine_with_queue_without_exposing_private_note_text(support):
    first, second = create(), create(owner='bob')
    assert action(first, 'claim')[0] == 200
    def queue(actor, value):
        code, result = request('/admin/tickets', owner=actor, claims=ADMIN, params={'assignee': value, 'status': 'open'})
        assert code == 200
        return result['tickets']
    assert [r['ticket_id'] for r in queue('staff-a', 'mine')] == [first['ticket_id']]
    assert [r['ticket_id'] for r in queue('staff-b', 'other')] == [first['ticket_id']]
    assert [r['ticket_id'] for r in queue('staff-a', 'unassigned')] == [second['ticket_id']]
    assert queue('staff-b', 'mine') == []
    assert request('/tickets', params={'assignee': 'mine'})[0] == 400
    assert request('/admin/tickets', owner='staff-a', claims=ADMIN, params={'assignee': 'invalid'})[0] == 400


def test_note_limit_is_separate_from_customer_message_limit(support):
    original = create()
    item = support.get_item(Key={'owner_id': 'alice', 'ticket_id': original['ticket_id']})['Item']
    item.update(internal_notes=[{'body': 'Internal', 'author': 'staff-a', 'created_at': item['created_at']} for _ in range(20)], internal_note_count=20)
    support.put_item(Item=item)
    assert action(original, 'note', note='Too many')[0] == 409
    assert action(original, 'update', status='open', message='Public response still allowed')[0] == 200
    assert request(path(original))[1]['message_count'] == 2


def test_assignment_history_is_bounded_without_blocking_handover(support):
    record = create()
    for _ in range(6):
        code, record = action(record, 'claim')
        assert code == 200
        code, record = action(record, 'release')
        assert code == 200
    assert len(record['assignment_events']) == 10
    assert record['assignment'] == 'unassigned'


@pytest.mark.parametrize('race', ['revision', 'deleting'])
def test_atomic_guard_drops_private_note_and_audit_on_race(support, monkeypatch, race):
    original = create()
    transact = tickets.transact
    def raced(service, item, *args, **kwargs):
        if race == 'revision':
            saved = support.get_item(Key={'owner_id': 'alice', 'ticket_id': original['ticket_id']})['Item']
            saved['revision'] = 'concurrent-staff-write'
            support.put_item(Item=saved)
        else:
            service.table('USAGE_TABLE_NAME').put_item(Item={'pk': 'account#alice', 'state': 'deleting'})
        return transact(service, item, *args, **kwargs)
    monkeypatch.setattr(tickets, 'transact', raced)
    assert action(original, 'note', note='Must not persist')[0] == 409
    saved = support.get_item(Key={'owner_id': 'alice', 'ticket_id': original['ticket_id']})['Item']
    assert 'internal_notes' not in saved
    events = request('/admin/audit', owner='staff-a', claims=ADMIN)[1]['events']
    assert not any(event['action'] == 'ticket.note' for event in events)


def test_expired_request_cannot_receive_internal_writes(support):
    original = create()
    saved = support.get_item(Key={'owner_id': 'alice', 'ticket_id': original['ticket_id']})['Item']
    saved['expires_at'] = int(time.time()) - 1
    support.put_item(Item=saved)
    assert action(original, 'claim')[0] == 404
    assert action(original, 'note', note='Expired')[0] == 404


def test_internal_notes_do_not_enter_ai_sources_or_private_history(support, ai):
    original = create()
    marker = 'PRIVATE-TEAM-REFUND-SECRET'
    assert action(original, 'note', note=marker)[0] == 200
    app.table.put_item(Item={'policy_id': 'SHARED', 'title': 'Refund policy', 'content': 'Refund within 7 days.', 'publication_state': 'published'})
    code, answer = request('/ask', 'POST', data={'question': 'Refund deadline?', 'source_scope': 'policies'})
    assert code == 200 and answer['grounded']
    assert marker not in json.dumps([answer, ai.calls, request('/conversations')[1]])
