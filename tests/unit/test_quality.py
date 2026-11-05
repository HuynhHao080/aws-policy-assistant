import time
from datetime import datetime,timezone
from urllib.parse import quote
import pytest
from policy_assistant import app
from policy_assistant.quality import save_answer,COUNTERS
from tests.unit.test_public_app import services,request,ai  # noqa:F401
ADMIN={"cognito:groups":["administrators"]}


def seeded(owner="alice",suffix="one"):
    stamp=datetime.now(timezone.utc).isoformat();item={"owner_id":owner,"conversation_id":stamp+"#"+suffix,"created_at":stamp,"question":"PRIVATE QUESTION","answer":"PRIVATE ANSWER","citations":[],"grounded":False,"source_scope":"policies","expires_at":int(time.time())+86400}
    save_answer(app._service(),owner,item,1234);return item


def vote(item,rating="helpful",reason=None,revision=None,owner="alice"):
    return request("/conversations/"+quote(item["conversation_id"],safe="")+"/feedback","PATCH",owner=owner,data={"rating":rating,"reason":reason,"expected_revision":revision})


def stats():return request("/admin/quality",owner="staff",claims=ADMIN)[1]


def test_recorded_answers_have_aggregate_only_latency_and_scope(services):
    item=seeded();summary=stats();assert summary["counts"]["answers"]==1 and summary["counts"]["refused"]==1
    assert summary["average_response_ms"]==1234 and summary["counts"]["scope_policies"]==1
    assert "PRIVATE" not in str(summary) and "owner_id" not in str(summary)
    assert request("/conversations")[1]["conversations"][0]["quality_version"]==1
    with pytest.raises(Exception):save_answer(app._service(),"alice",item,1234)
    assert stats()["counts"]["answers"]==1


def test_vote_changes_clear_and_network_retry_do_not_inflate_totals(services):
    item=seeded();code,first=vote(item);assert code==200
    assert vote(item)[1]==first  # Old-revision retry with same target is a no-op.
    assert stats()["counts"]["helpful"]==1
    code,second=vote(item,"not_helpful","citation",first["feedback"]["revision"]);assert code==200
    s=stats();assert s["counts"]["helpful"]==0 and s["counts"]["not_helpful"]==1 and s["counts"]["reason_citation"]==1
    code,third=vote(item,"not_helpful","unclear",second["feedback"]["revision"]);assert code==200
    s=stats();assert s["counts"]["not_helpful"]==1 and s["counts"]["reason_citation"]==0 and s["counts"]["reason_unclear"]==1
    assert vote(item,None,None,third["feedback"]["revision"])[0]==200
    s=stats();assert s["counts"]["not_helpful"]==0 and s["counts"]["reason_unclear"]==0 and s["helpful_rate"] is None


def test_owned_feedback_conflicts_and_private_content_is_not_exposed_to_admin(services):
    item=seeded();assert vote(item,owner="bob")[0]==404
    first=vote(item)[1];assert vote(item,"not_helpful","other",revision="stale")[0]==409
    assert request("/admin/quality")[0]==403
    assert stats()["counts"]["helpful"]==1
    assert request("/conversations",owner="staff",claims=ADMIN)[1]["conversations"]==[]


@pytest.mark.parametrize("rating,reason",[("bad",None),([],None),("not_helpful",None),("not_helpful",[]),("not_helpful","bad"),("helpful","citation"),(None,"other")])
def test_invalid_feedback_is_rejected_before_updates(services,rating,reason):
    item=seeded();assert vote(item,rating,reason)[0]==400
    assert stats()["counts"]["helpful"]==0


def test_feedback_does_not_extend_history_or_resurrect_expired_records(services):
    item=seeded();vote(item)
    history=app._service().table("HISTORY_TABLE_NAME");row=history.get_item(Key={k:item[k] for k in ["owner_id","conversation_id"]})["Item"]
    assert int(row["expires_at"])==item["expires_at"]
    history.update_item(Key={k:item[k] for k in ["owner_id","conversation_id"]},UpdateExpression="SET expires_at=:old",ExpressionAttributeValues={":old":int(time.time())-1})
    assert vote(item)[0]==404 and request("/conversations")[1]["conversations"]==[]
    assert stats()["counts"]["helpful"]==1  # Anonymous historical cohort is independent of private history.


def test_empty_quality_and_month_allowlist(services):
    summary=stats();assert summary["counts"]["answers"]==0 and summary["citation_rate"] is None and summary["helpful_rate"] is None
    for month in ["2000-01","2030-01","invalid"]:assert request("/admin/quality",claims=ADMIN,params={"month":month})[0]==400


def test_legacy_history_cannot_create_unbacked_quality_counts(services):
    item=seeded();history=app._service().table("HISTORY_TABLE_NAME");history.update_item(Key={k:item[k] for k in ["owner_id","conversation_id"]},UpdateExpression="REMOVE quality_version")
    assert vote(item)[0]==409 and stats()["counts"]["helpful"]==0


def test_deleting_account_race_rolls_back_feedback_and_aggregate(services,monkeypatch):
    item=seeded();service=app._service();monkeypatch.setattr(app,"_service",lambda:service)
    actual=service.client("dynamodb").transact_write_items
    def race(**kwargs):
        service.table("USAGE_TABLE_NAME").put_item(Item={"pk":"account#alice","state":"deleting"})
        return actual(**kwargs)
    monkeypatch.setattr(service.client("dynamodb"),"transact_write_items",race)
    assert vote(item)[0]==409
    row=service.table("HISTORY_TABLE_NAME").get_item(Key={k:item[k] for k in ["owner_id","conversation_id"]})["Item"]
    assert "feedback" not in row and stats()["counts"]["helpful"]==0


def test_recorded_no_evidence_answer_does_not_invoke_generation_and_is_measured(services,ai):
    code,result=request("/ask","POST",data={"question":"Unknown policy?","source_scope":"policies"})
    assert code==200 and result["quality_version"]==1 and not result["grounded"]
    assert ai.calls==[] and stats()["counts"]["refused"]==1


def test_feedback_quota_failure_does_not_change_vote_or_rollup(services):
    item=seeded();db=app._service().table("USAGE_TABLE_NAME");today=datetime.now(timezone.utc).strftime("%Y-%m-%d")
    db.put_item(Item={"pk":"user#alice#feedback#"+today,"count":50})
    assert vote(item)[0]==429 and stats()["counts"]["helpful"]==0


def test_corrupt_aggregate_cannot_underflow_or_commit_half_a_vote(services):
    item=seeded();first=vote(item)[1]
    app._service().table("USAGE_TABLE_NAME").update_item(Key={"pk":"quality#"+item["quality_month"]},UpdateExpression="SET helpful=:zero",ExpressionAttributeValues={":zero":0})
    assert vote(item,None,None,first["feedback"]["revision"])[0]==409
    row=app._service().table("HISTORY_TABLE_NAME").get_item(Key={k:item[k] for k in ["owner_id","conversation_id"]})["Item"]
    assert row["feedback"]["rating"]=="helpful" and stats()["counts"]["helpful"]==0


def test_quality_routes_explicitly_use_gateway_jwt():
    from pathlib import Path
    import yaml
    class Loader(yaml.SafeLoader):pass
    def tag(loader,suffix,node):
        if isinstance(node,yaml.ScalarNode):return loader.construct_scalar(node)
        if isinstance(node,yaml.SequenceNode):return loader.construct_sequence(node)
        return loader.construct_mapping(node)
    Loader.add_multi_constructor("!",tag)
    template=yaml.load((Path(__file__).resolve().parents[2]/"template.yaml").read_text(encoding="utf-8"),Loader=Loader)
    events=template["Resources"]["PolicyAssistantFunction"]["Properties"]["Events"]
    for name in ["AnswerFeedback","AdminQuality"]:assert events[name]["Properties"]["Auth"]["Authorizer"]=="PolicyAssistantAuthorizer"


def test_transient_metric_contention_reuses_idempotency_token_without_duplicate_answer(services,monkeypatch):
    from botocore.exceptions import ClientError
    service=app._service();monkeypatch.setattr(app,"_service",lambda:service);actual=service.client("dynamodb").transact_write_items;tokens=[]
    def conflict_once(**kwargs):
        if "ClientRequestToken" not in kwargs:return actual(**kwargs)
        tokens.append(kwargs["ClientRequestToken"])
        if len(tokens)==1:raise ClientError({"Error":{"Code":"TransactionCanceledException","Message":"Synthetic conflict"},"CancellationReasons":[{"Code":"None"},{"Code":"TransactionConflict"},{"Code":"None"}]},"TransactWriteItems")
        return actual(**kwargs)
    monkeypatch.setattr(service.client("dynamodb"),"transact_write_items",conflict_once)
    seeded();assert len(tokens)==2 and len(set(tokens))==1 and stats()["counts"]["answers"]==1


def test_transaction_conflict_retries_are_bounded_and_leave_no_partial_history(services,monkeypatch):
    from botocore.exceptions import ClientError
    service=app._service();monkeypatch.setattr(app,"_service",lambda:service);calls=[];actual=service.client("dynamodb").transact_write_items
    def conflict(**kwargs):
        if "ClientRequestToken" not in kwargs:return actual(**kwargs)
        calls.append(kwargs)
        raise ClientError({"Error":{"Code":"TransactionCanceledException","Message":"Synthetic conflict"},"CancellationReasons":[{"Code":"TransactionConflict"}]},"TransactWriteItems")
    monkeypatch.setattr(service.client("dynamodb"),"transact_write_items",conflict)
    with pytest.raises(ClientError):seeded()
    assert len(calls)==3 and request("/conversations")[1]["conversations"]==[] and stats()["counts"]["answers"]==0
