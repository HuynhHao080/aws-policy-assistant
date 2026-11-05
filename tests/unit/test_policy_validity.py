"""Business dates, draft isolation, source races and public pagination."""
import json
from datetime import datetime, timezone

import pytest

from policy_assistant import app, policy_validity as validity
from tests.unit.test_public_app import services, ai, request  # noqa: F401
from tests.unit.test_policy_admin import FIELDS, change


@pytest.mark.parametrize('window,expected', [
    ({}, 'active'),
    ({'effective_from': '2026-11-05', 'effective_until': '2026-11-05'}, 'active'),
    ({'effective_from': '2026-11-06'}, 'upcoming'),
    ({'effective_until': '2026-11-04'}, 'expired'),
    ({'effective_from': '2026-02-30'}, 'invalid'),
    ({'effective_from': '2026-12-01', 'effective_until': '2026-11-01'}, 'invalid'),
    ({'effective_until': True}, 'invalid'),
])
def test_inclusive_dates_and_fail_closed_corrupt_windows(window, expected):
    assert validity.state(window, '2026-11-05') == expected


def test_business_day_uses_vietnam_boundary_not_utc_or_host(monkeypatch):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(validity, 'datetime', FrozenDatetime)
    assert validity.today() == '2026-11-05'


@pytest.fixture
def day(monkeypatch):
    monkeypatch.setattr(validity, 'today', lambda: '2026-11-05')
    monkeypatch.setenv('REQUIRE_PUBLISHED_POLICIES', 'true')
    monkeypatch.delenv('EMBEDDING_MODEL_ID', raising=False)


def seed(**window):
    item = {'policy_id': 'DATE-POLICY', **FIELDS, 'publication_state': 'published',
            'title_lower': FIELDS['title'].lower(), 'category_lower': FIELDS['category'].lower(),
            'content_lower': FIELDS['content'].lower(), 'keywords_lower': ['refund'], **window}
    app.table.put_item(Item=item)
    return item


@pytest.mark.parametrize('window', [
    {'effective_from': '2026-11-06'}, {'effective_until': '2026-11-04'},
    {'effective_until': 'not-a-date'},
])
def test_inactive_source_is_hidden_everywhere_without_generation(services, ai, day, window):
    seed(**window)
    assert request('/policies/DATE-POLICY')[0] == 404
    assert request('/policies', params={'keyword': 'refund'})[1]['policies'] == []
    code, answer = request('/ask', 'POST', data={'question': 'Refund deadline?', 'source_scope': 'policies'})
    assert code == 200 and not answer['grounded'] and not answer['citations']
    assert ai.calls == []


def test_last_day_is_inclusive_and_no_internal_fingerprint_leaks(services, ai, day):
    seed(effective_from='2026-11-05', effective_until='2026-11-05')
    assert request('/policies/DATE-POLICY')[0] == 200
    code, answer = request('/ask', 'POST', data={'question': 'Refund deadline?', 'source_scope': 'policies'})
    assert code == 200 and answer['grounded']
    assert answer['citations'][0]['effective_until'] == '2026-11-05'
    assert '_policy_signature' not in json.dumps([answer, ai.calls, request('/conversations')[1]])


@pytest.mark.parametrize('mode', ['expire', 'archive', 'replace', 'delete'])
def test_policy_change_during_generation_rejects_without_history(services, ai, day, monkeypatch, mode):
    item = seed()
    converse = ai.converse
    def changed(**kwargs):
        if mode == 'delete':
            app.table.delete_item(Key={'policy_id': item['policy_id']})
        else:
            if mode == 'expire': item['effective_until'] = '2026-11-04'
            if mode == 'archive': item['publication_state'] = 'archived'
            if mode == 'replace': item['content'] = 'Refund within 90 days.'
            app.table.put_item(Item=item)
        return converse(**kwargs)
    monkeypatch.setattr(ai, 'converse', changed)
    assert request('/ask', 'POST', data={'question': 'Refund deadline?', 'source_scope': 'policies'})[0] == 409
    assert request('/conversations')[1]['conversations'] == []


def test_isolated_draft_revision_does_not_invalidate_published_facts(services, ai, day, monkeypatch):
    item = seed()
    converse = ai.converse
    def draft_only(**kwargs):
        item['revision'] = 'new-draft-revision'
        item['draft_data'] = dict(FIELDS, content='PRIVATE DRAFT refund after 90 days.', effective_until='2026-11-04')
        app.table.put_item(Item=item)
        return converse(**kwargs)
    monkeypatch.setattr(ai, 'converse', draft_only)
    code, answer = request('/ask', 'POST', data={'question': 'Refund deadline?', 'source_scope': 'policies'})
    assert code == 200 and answer['grounded']
    assert 'PRIVATE DRAFT' not in json.dumps(answer)


def test_legacy_edits_preserve_dates_and_explicit_blanks_clear_on_publish(services, day):
    code, draft = change('save_draft', draft=dict(FIELDS, effective_from='2026-11-06', effective_until='2026-11-10'))
    assert code == 200
    code, live = change('publish', draft['revision'])
    assert code == 200 and live['validity_state'] == 'upcoming'
    code, edited = change('save_draft', live['revision'], FIELDS)
    assert code == 200 and edited['draft']['effective_until'] == '2026-11-10'
    code, cleared = change('save_draft', edited['revision'], dict(FIELDS, effective_from='', effective_until=''))
    assert code == 200 and 'effective_from' not in cleared['draft']
    assert request('/policies/PILOT-EDIT')[0] == 404  # Saved draft does not alter the future live snapshot.
    code, final = change('publish', cleared['revision'])
    assert code == 200 and final['validity_state'] == 'active'
    public = request('/policies/PILOT-EDIT')[1]
    assert 'effective_from' not in public and 'effective_until' not in public


@pytest.mark.parametrize('window', [
    {'effective_from': '2026-2-01'}, {'effective_from': '0000-01-01'},
    {'effective_until': '2026-02-30'}, {'effective_until': 20261105},
    {'effective_from': '2026-11-10', 'effective_until': '2026-11-09'},
])
def test_bad_draft_dates_rejected_before_persistence(services, day, window):
    assert change('save_draft', draft=dict(FIELDS, **window))[0] == 400
    assert 'Item' not in app.table.get_item(Key={'policy_id': 'PILOT-EDIT'})


def test_search_keeps_scanning_after_expired_result_without_skipping_cursor(services, day, monkeypatch):
    seen = []
    pages = [{'Items': [{'policy_id': 'OLD', 'effective_until': '2026-11-04'}], 'ScannedCount': 1, 'LastEvaluatedKey': {'policy_id': 'OLD'}},
             {'Items': [{'policy_id': 'LIVE', 'content': 'refund'}], 'ScannedCount': 1}]
    def scan(**kwargs):
        seen.append(kwargs)
        return pages.pop(0)
    monkeypatch.setattr(app.table, 'scan', scan)
    code, result = request('/policies', params={'keyword': 'refund', 'limit': '1'})
    assert code == 200 and [p['policy_id'] for p in result['policies']] == ['LIVE']
    assert result['scanned_count'] == 2 and result['next_token'] is None
    assert seen[1]['ExclusiveStartKey'] == {'policy_id': 'OLD'}


def test_admin_filter_uses_published_dates_not_private_draft(services, day):
    seed(effective_until='2026-11-04', draft_data=dict(FIELDS, effective_from='2027-01-01'))
    admin={'cognito:groups':['administrators']}
    rows=request('/admin/policies', claims=admin, params={'validity':'expired'})[1]['policies']
    assert len(rows)==1 and rows[0]['validity_state']=='expired' and rows[0]['has_draft']
    assert request('/admin/policies', claims=admin, params={'validity':'upcoming'})[1]['policies']==[]
    assert request('/admin/policies', claims=admin, params={'validity':'invented'})[0]==400
