"""Explicit source selection never falls back across the selected boundary."""
import json
import pytest
from policy_assistant import app
from tests.unit.test_public_app import services,ai,ready,request  # noqa: F401


def test_policies_only_does_not_query_or_open_private_documents(services, ai, monkeypatch):
    data=ready(services)
    app.table.put_item(Item={"policy_id":"SHARED","title":"Shared refund","content":"Refund within 7 days.","publication_state":"published"})
    service=app._service()
    monkeypatch.setattr(service.docs,"query",lambda **kwargs:pytest.fail("No private document query permitted"))
    monkeypatch.setattr(service,"owned",lambda *args:pytest.fail("No private document read permitted"))
    code,result=request("/ask","POST",data={"question":"Refund deadline?","source_scope":"policies"})
    assert code==200 and result["source_scope"]=="policies"
    assert all(c.get("policy_id")=="SHARED" and "doc_id" not in c for c in result["citations"])
    assert request("/conversations")[1]["conversations"][0]["source_scope"]=="policies"


def test_documents_only_never_queries_shared_policies(services, ai, monkeypatch):
    data=ready(services)
    service=app._service()
    monkeypatch.setattr(service.policies,"scan",lambda **kwargs:pytest.fail("No shared policy read permitted"))
    code,result=request("/ask","POST",data={"question":"Refund deadline?","source_scope":"documents","document_ids":[data["doc_id"]]})
    assert code==200 and result["source_scope"]=="documents"
    assert all(c.get("doc_id")==data["doc_id"] and "policy_id" not in c for c in result["citations"])
    assert request("/ask","POST",owner="bob",data={"question":"Refund?","source_scope":"documents","document_ids":[data["doc_id"]]})[0]==404


@pytest.mark.parametrize("data",[{"source_scope":"other"},{"source_scope":"documents"},{"source_scope":"policies","document_ids":["doc-private"]}])
def test_invalid_scope_is_rejected_before_question_quota_or_model(services,ai,monkeypatch,data):
    monkeypatch.setattr(app._service(),"quota",lambda owner,kind:pytest.fail("Invalid question must not reserve a question") if kind=="question" else None)
    assert request("/ask","POST",data={"question":"Refund?",**data})[0]==400
    assert ai.calls==[]
