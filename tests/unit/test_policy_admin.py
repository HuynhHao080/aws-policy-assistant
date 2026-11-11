"""Draft isolation, publication, audit and stale-write protection against real moto DynamoDB."""
import json
import pytest
from policy_assistant import app
from tests.unit.test_public_app import services, ai, request  # noqa: F401

ADMIN = {"cognito:groups": ["administrators"]}
PATH = "/admin/policies/PILOT-EDIT"
FIELDS = {"title": "Refund policy", "category": "Support", "content": "Refund within 30 days.", "keywords": ["refund"]}


def change(action, revision=None, draft=None):
    body = {"action": action, "expected_revision": revision}
    if draft is not None:
        body["draft"] = draft
    return request(PATH, "PATCH", data=body, claims=ADMIN)


def publish():
    code, draft = change("save_draft", draft=FIELDS)
    assert code == 200
    code, live = change("publish", draft["revision"])
    assert code == 200
    return live


@pytest.mark.parametrize("path,method,data", [
    ("/admin/policies", "GET", None),
    (PATH, "GET", None),
    (PATH, "PATCH", {"action": "save_draft", "draft": FIELDS}),
    (PATH, "PATCH", {"action": "publish"}),
    (PATH, "PATCH", {"action": "archive"}),
])
def test_admin_policy_management_is_denied_to_customers(services, path, method, data):
    assert request(path, method, data=data)[0] == 403
    assert "Item" not in app.table.get_item(Key={"policy_id": "PILOT-EDIT"})


def test_new_draft_is_private_and_does_not_call_generation(services, ai, monkeypatch):
    monkeypatch.setenv("REQUIRE_PUBLISHED_POLICIES", "true")
    code, draft = change("save_draft", draft=FIELDS)
    assert code == 200 and draft["publication_state"] == "draft" and draft["current"] is None
    assert request("/policies/PILOT-EDIT")[0] == 404
    assert request("/policies", params={"keyword": "refund"})[1]["policies"] == []
    assert request("/ask", "POST", data={"question": "Refund deadline?"})[1]["grounded"] is False
    assert ai.calls == []


def test_editing_draft_preserves_live_snapshot_and_does_not_leak_into_search_or_ai(services, ai, monkeypatch):
    monkeypatch.setenv("REQUIRE_PUBLISHED_POLICIES", "true")
    live = publish()
    before_public = request("/policies/PILOT-EDIT")[1]
    private = dict(FIELDS, title="PRIVATE-DRAFT-MARKER", content="PRIVATE-DRAFT-MARKER refund within 90 days.")
    code, edited = change("save_draft", live["revision"], private)
    assert code == 200 and edited["publication_state"] == "published"
    assert edited["current"]["content"] == FIELDS["content"]
    public = request("/policies/PILOT-EDIT")[1]
    assert public == before_public
    assert public["content"] == FIELDS["content"] and "draft_data" not in public and "revision" not in public
    assert request("/policies", params={"keyword": "PRIVATE-DRAFT-MARKER"})[1]["policies"] == []
    assert request("/ask", "POST", data={"question": "Refund deadline?"})[0] == 200
    assert "PRIVATE-DRAFT-MARKER" not in json.dumps(ai.calls)
    code, published = change("publish", edited["revision"])
    assert code == 200 and published["draft"] is None
    assert request("/policies/PILOT-EDIT")[1]["content"] == private["content"]


def test_archive_restore_and_discard_are_reversible_and_audited(services, monkeypatch):
    monkeypatch.setenv("REQUIRE_PUBLISHED_POLICIES", "true")
    live = publish()
    code, draft = change("save_draft", live["revision"], dict(FIELDS, content="Unapproved 90 days."))
    assert code == 200
    code, discarded = change("discard_draft", draft["revision"])
    assert code == 200 and discarded["draft"] is None and discarded["current"] == live["current"]
    code, archived = change("archive", discarded["revision"])
    assert code == 200 and archived["publication_state"] == "archived"
    assert request("/policies/PILOT-EDIT")[0] == 404
    assert request("/policies", params={"keyword": "refund"})[1]["policies"] == []
    code, restored = change("publish", archived["revision"])
    assert code == 200 and restored["current"] == live["current"]
    actions = {e["action"] for e in request("/admin/audit", claims=ADMIN)[1]["events"]}
    assert {"policy.draft", "policy.publish", "policy.archive", "policy.discard_draft"}.issubset(actions)


def test_stale_revision_cannot_overwrite_or_publish_someone_elses_draft(services):
    live = publish()
    code, fresh = change("save_draft", live["revision"], dict(FIELDS, content="New staff draft"))
    assert code == 200
    for action in ["save_draft", "publish", "archive", "discard_draft"]:
        assert change(action, live["revision"], FIELDS)[0] == 409
    assert request(PATH, claims=ADMIN)[1]["draft"]["content"] == "New staff draft"
    assert fresh["revision"] != live["revision"]


def test_atomic_condition_detects_race_after_read_and_does_not_write_audit(services, monkeypatch):
    live = publish()
    service = app._service()
    monkeypatch.setattr(app, "_service", lambda: service)
    original = service.client("dynamodb").transact_write_items
    before = request("/admin/audit", claims=ADMIN)[1]["events"]
    def race(**kwargs):
        if kwargs["TransactItems"][0].get("Put", {}).get("TableName") == app.table.name:
            app.table.update_item(Key={"policy_id": "PILOT-EDIT"}, UpdateExpression="SET #rev=:other", ExpressionAttributeNames={"#rev": "revision"}, ExpressionAttributeValues={":other": "concurrent-edit"})
        return original(**kwargs)
    monkeypatch.setattr(service.client("dynamodb"), "transact_write_items", race)
    code, _ = change("save_draft", live["revision"], dict(FIELDS, content="Stale draft"))
    assert code == 409
    assert request(PATH, claims=ADMIN)[1]["draft"] is None
    assert request("/admin/audit", claims=ADMIN)[1]["events"] == before


def test_legacy_publication_can_create_but_existing_edits_need_revision(services):
    assert request(PATH, "PUT", data=FIELDS, claims=ADMIN)[0] == 200
    assert request(PATH, "PUT", data=dict(FIELDS, content="Overwrite"), claims=ADMIN)[0] == 409
    version = request(PATH, claims=ADMIN)[1]["revision"]
    assert request(PATH, "PUT", data={**FIELDS, "expected_revision": version}, claims=ADMIN)[0] == 200


def test_existing_legacy_item_with_timestamp_gets_concurrency_protection(services):
    app.table.put_item(Item={"policy_id": "PILOT-EDIT", **FIELDS, "publication_state": "published", "updated_at": "2026-10-30T00:00:00+00:00"})
    version = request(PATH, claims=ADMIN)[1]["revision"]
    assert change("save_draft", version, FIELDS)[0] == 200
    assert change("archive", version)[0] == 409


def test_listing_paginates_and_never_returns_content_vectors_or_edit_tokens(services):
    for n in range(4):
        app.table.put_item(Item={"policy_id": f"LIST-{n}", "draft_data": dict(FIELDS, title=f"Draft {n}"), "publication_state": "draft", "revision": "private-edit-token"})
    page = request("/admin/policies", claims=ADMIN, params={"limit": "1"})[1]
    seen = []
    while True:
        seen.extend(page["policies"])
        if not page["next_token"]:
            break
        page = request("/admin/policies", claims=ADMIN, params={"limit": "1", "next_token": page["next_token"]})[1]
    assert len(seen) == 4
    assert all(row["has_draft"] and "content" not in row and "revision" not in row and "draft_data" not in row for row in seen)
    assert request("/admin/policies", claims=ADMIN, params={"keyword": "Draft 2"})[1]["policies"][0]["policy_id"] == "LIST-2"


@pytest.mark.parametrize("params", [{"limit":"0"},{"limit":"51"},{"next_token":"bad"},{"keyword":"x"*201}])
def test_invalid_policy_list_input_is_rejected(services, params):
    assert request("/admin/policies", claims=ADMIN, params=params)[0] == 400


def test_unknown_actions_or_missing_drafts_cannot_publish(services):
    assert change("publish")[0] == 404
    code, draft = change("save_draft", draft=FIELDS)
    assert code == 200
    assert change("unknown", draft["revision"])[0] == 400
    assert change("save_draft", draft["revision"], {"title":"Missing content"})[0] == 400
    code, empty = change("discard_draft", draft["revision"])
    assert code == 200 and empty["publication_state"] == "archived"
    assert change("publish", empty["revision"])[0] == 409
