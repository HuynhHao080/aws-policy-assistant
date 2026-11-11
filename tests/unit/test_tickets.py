"""Support privacy, consent, concurrency, limits and deletion lifecycle."""
import time
import boto3
import pytest
from policy_assistant import app
from tests.unit.test_public_app import services, request, run_worker  # noqa: F401

ADMIN = {"cognito:groups": ["administrators"]}


@pytest.fixture
def support(services, monkeypatch):
    db = boto3.resource("dynamodb", region_name="ap-southeast-1")
    table = db.create_table(TableName="TestSupport", KeySchema=[{"AttributeName":"owner_id","KeyType":"HASH"},{"AttributeName":"ticket_id","KeyType":"RANGE"}], AttributeDefinitions=[{"AttributeName":k,"AttributeType":"S"} for k in ("owner_id","ticket_id")], BillingMode="PAY_PER_REQUEST")
    monkeypatch.setenv("SUPPORT_TABLE_NAME", table.name)
    return table


def create(owner="alice", **extra):
    code, item = request("/tickets", "POST", owner=owner, data={"subject":"Support test", "message":"Shared explicitly, no PDF attached.", "consent":True, **extra})
    assert code == 200
    return item


def path(item, admin=False, owner="alice"):
    return ("/admin/tickets/"+owner if admin else "/tickets")+"/"+item["ticket_id"]


@pytest.mark.parametrize("consent", [None, False, "true"])
def test_support_requires_explicit_sharing_consent(support, consent):
    assert request("/tickets","POST",data={"subject":"Test","message":"Private","consent":consent})[0]==400
    assert support.scan()["Items"]==[]


def test_customer_and_staff_thread_status_and_serialization(support):
    item=create()
    assert item["status"]=="open" and "owner_id" not in item and item["message_count"]==1
    code,reply=request(path(item,True),"PATCH",claims=ADMIN,data={"action":"update","expected_revision":item["revision"],"status":"resolved","message":"Please check the policy conditions."})
    assert code==200 and reply["messages"][-1]["role"]=="staff"
    customer=request(path(item))[1]
    assert "owner_id" not in customer and customer["status"]=="resolved"
    code,followup=request(path(item),"PATCH",data={"expected_revision":customer["revision"],"message":"One more question"})
    assert code==200 and followup["status"]=="open" and followup["message_count"]==3
    assert followup["expires_at"]==item["expires_at"]
    audit=request("/admin/audit",claims=ADMIN)[1]["events"]
    assert audit[0]["action"]=="ticket.update" and "message" not in audit[0]


def test_admin_queue_wait_clock_tracks_unanswered_customer_messages(support):
    item = create()
    def row():
        result = request("/admin/tickets", owner="staff", claims=ADMIN)[1]["tickets"][0]
        assert "messages" not in result
        return result

    assert row()["customer_waiting_since"] == item["created_at"]
    assert request("/tickets")[1]["tickets"][0]["last_staff_reply_at"] is None
    status, claimed = request(path(item, True), "PATCH", owner="staff", claims=ADMIN, data={
        "action": "claim", "expected_revision": item["revision"],
    })
    assert status == 200
    assert row()["customer_waiting_since"] == item["created_at"]
    status, reply = request(path(item, True), "PATCH", owner="staff", claims=ADMIN, data={
        "action": "update", "expected_revision": claimed["revision"], "status": "in_progress", "message": "Checking.",
    })
    assert status == 200 and row()["customer_waiting_since"] is None
    customer_summary = request("/tickets")[1]["tickets"][0]
    assert customer_summary["last_staff_reply_at"] == reply["messages"][-1]["created_at"]
    assert "messages" not in customer_summary
    status, followup = request(path(item), "PATCH", data={
        "expected_revision": reply["revision"], "message": "Could you confirm?",
    })
    assert status == 200
    assert row()["customer_waiting_since"] == followup["messages"][-1]["created_at"]
    assert "customer_waiting_since" not in request("/tickets")[1]["tickets"][0]


def test_customers_cannot_access_others_or_staff_queue(support):
    item=create()
    for method,data in [("GET",None),("PATCH",{"expected_revision":item["revision"],"message":"Intrusion"}),("DELETE",{"expected_revision":item["revision"],"confirmation":"DELETE"})]:
        assert request(path(item),method,owner="bob",data=data)[0]==404
    assert request("/tickets",owner="bob")[1]["tickets"]==[]
    assert request("/admin/tickets")[0]==403
    assert request(path(item,True))[0]==403
    summary=request("/admin/tickets",claims=ADMIN)[1]["tickets"][0]
    assert "messages" not in summary and "revision" not in summary and summary["owner_id"]=="alice"


def test_conflicts_and_confirmation_protect_customer_deletion(support):
    item=create()
    assert request(path(item),"DELETE",data={"expected_revision":item["revision"]})[0]==400
    assert request(path(item),"PATCH",data={"expected_revision":"stale","message":"Wrong"})[0]==409
    assert request(path(item),"DELETE",data={"expected_revision":"stale","confirmation":"DELETE"})[0]==409
    assert request(path(item),"DELETE",data={"expected_revision":item["revision"],"confirmation":"DELETE"})[0]==200
    assert request(path(item))[0]==404


def test_expired_records_are_hidden_before_ttl_cleanup(support):
    item=create()
    support.update_item(Key={"owner_id":"alice","ticket_id":item["ticket_id"]},UpdateExpression="SET expires_at=:old",ExpressionAttributeValues={":old":int(time.time())-1})
    assert request(path(item))[0]==404
    assert request("/tickets")[1]["tickets"]==[]
    assert request("/admin/tickets",claims=ADMIN)[1]["tickets"]==[]


def test_close_reopen_and_message_cap_are_enforced(support):
    item=create()
    messages=[{"role":"customer","body":"Seeded message","created_at":item["created_at"]} for _ in range(20)]
    support.update_item(Key={"owner_id":"alice","ticket_id":item["ticket_id"]},UpdateExpression="SET messages=:m,message_count=:n",ExpressionAttributeValues={":m":messages,":n":20})
    assert request(path(item),"PATCH",data={"expected_revision":item["revision"],"message":"Too many"})[0]==409
    code,closed=request(path(item),"PATCH",data={"action":"close","expected_revision":item["revision"]})
    assert code==200 and closed["status"]=="closed" and closed["message_count"]==20
    assert request(path(item),"PATCH",data={"expected_revision":closed["revision"],"message":"Closed thread"})[0]==409
    code,reopened=request(path(item,True),"PATCH",claims=ADMIN,data={"action":"update","expected_revision":closed["revision"],"status":"in_progress"})
    assert code==200 and reopened["status"]=="in_progress"


def test_support_creation_quota_is_bounded(support, monkeypatch):
    monkeypatch.setenv("TICKETS_PER_USER_DAY","1")
    create()
    assert request("/tickets","POST",data={"subject":"Again","message":"Again","consent":True})[0]==429
    assert len(support.scan()["Items"])==1


def test_owner_and_admin_cursors_are_not_interchangeable(support):
    first=create();create();create("bob")
    one=request("/tickets",params={"limit":"1"})[1]
    assert one["next_token"]
    assert request("/tickets",owner="bob",params={"next_token":one["next_token"]})[0]==400
    assert request("/admin/tickets",claims=ADMIN,params={"next_token":one["next_token"]})[0]==400
    admin=request("/admin/tickets",claims=ADMIN,params={"limit":"1"})[1]
    assert admin["next_token"]
    assert request("/tickets",params={"next_token":admin["next_token"]})[0]==400
    assert request("/admin/tickets",claims=ADMIN,params={"next_token":admin["next_token"]})[0]==200
    assert request(path(first))[0]==200


def test_account_blocking_race_prevents_new_support_rows(support, monkeypatch):
    service=app._service();monkeypatch.setattr(app,"_service",lambda:service)
    original=service.client("dynamodb").transact_write_items
    def race(**kwargs):
        if kwargs["TransactItems"][0].get("Put",{}).get("TableName")==support.name:
            service.table("USAGE_TABLE_NAME").put_item(Item={"pk":"account#alice","state":"deleting"})
        return original(**kwargs)
    monkeypatch.setattr(service.client("dynamodb"),"transact_write_items",race)
    assert request("/tickets","POST",data={"subject":"Race","message":"Must not persist","consent":True})[0]==409
    assert support.scan()["Items"]==[]


def test_deleting_owners_are_hidden_from_staff_queue(support):
    item=create()
    app._service().table("USAGE_TABLE_NAME").put_item(Item={"pk":"account#alice","state":"deleting"})
    assert request("/admin/tickets",owner="staff",claims=ADMIN)[1]["tickets"]==[]
    assert request(path(item,True),owner="staff",claims=ADMIN)[0]==404


def test_account_purge_removes_all_support_pages_and_preserves_other_customers(support, monkeypatch):
    item=create();other=create("bob")
    for i in range(55):support.put_item(Item={"owner_id":"alice","ticket_id":"seed-"+str(i)})
    cognito=boto3.client("cognito-idp",region_name="ap-southeast-1")
    pool=cognito.create_user_pool(PoolName="SupportAccounts")["UserPool"]["Id"]
    cognito.admin_create_user(UserPoolId=pool,Username="alice",MessageAction="SUPPRESS")
    monkeypatch.setenv("USER_POOL_ID",pool)
    assert request("/account/delete","POST",data={"confirmation":"DELETE"},claims={"cognito:username":"alice"})[0]==200
    assert run_worker("account-alice")=={"batchItemFailures":[]}
    assert support.query(KeyConditionExpression=boto3.dynamodb.conditions.Key("owner_id").eq("alice"))["Items"]==[]
    assert request(path(other),owner="bob")[0]==200


@pytest.mark.parametrize("body", [{"action":"unknown"},{"status":"unknown"},{"message":{}},{"message":"x"*1501}])
def test_invalid_staff_updates_are_rejected(support, body):
    item=create()
    assert request(path(item,True),"PATCH",claims=ADMIN,data={"expected_revision":item["revision"],**body})[0]==400


def test_structured_support_is_consented_and_staff_controls_priority(support):
    item=create(category="warranty",order_ref="  DEMO-ORDER-001  ")
    assert (item["category"],item["order_ref"],item["priority"]) == ("warranty","DEMO-ORDER-001","normal")
    for field,value in [("priority","high"),("category","returns"),("order_ref","DIFFERENT")]:
        assert request(path(item),"PATCH",data={"expected_revision":item["revision"],"message":"Change",field:value})[0]==400
    code,updated=request(path(item,True),"PATCH",claims=ADMIN,data={"expected_revision":item["revision"],"action":"update","priority":"high","status":"in_progress"})
    assert code==200 and updated["priority"]=="high" and updated["message_count"]==1
    assert updated["order_ref"]==item["order_ref"] and updated["expires_at"]==item["expires_at"]
    assert request(path(item))[1]["priority"]=="high"
    assert request(path(item,True),"PATCH",claims=ADMIN,data={"expected_revision":item["revision"],"priority":"low"})[0]==409
    audit=request("/admin/audit",claims=ADMIN)[1]["events"]
    assert "DEMO-ORDER-001" not in str(audit)


@pytest.mark.parametrize("extra",[{"category":"unknown"},{"category":[]},{"order_ref":None},{"order_ref":"x"*81},{"order_ref":"order\nnext"},{"priority":"high"}])
def test_bad_support_metadata_never_creates_a_record(support,extra):
    assert request("/tickets","POST",data={"subject":"Test","message":"Test","consent":True,**extra})[0]==400
    assert support.scan()["Items"]==[]


def test_support_combined_filters_are_exact_and_preserve_legacy_defaults(support):
    first=create(category="returns",order_ref="ORDER-ONE");other=create("bob",category="shipping",order_ref="ORDER-TWO")
    assert request("/admin/tickets",claims=ADMIN,params={"category":"returns","priority":"normal","order_ref":"ORDER-ONE"})[1]["tickets"][0]["ticket_id"]==first["ticket_id"]
    assert request("/admin/tickets",claims=ADMIN,params={"category":"shipping","order_ref":"ORDER-ONE"})[1]["tickets"]==[]
    assert request("/tickets",params={"order_ref":"ORDER-TWO"})[1]["tickets"]==[]
    legacy=create()
    support.update_item(Key={"owner_id":"alice","ticket_id":legacy["ticket_id"]},UpdateExpression="REMOVE category, priority, order_ref")
    found=request("/admin/tickets",claims=ADMIN,params={"category":"general","priority":"normal"})[1]["tickets"]
    assert len(found)==1 and found[0]["ticket_id"]==legacy["ticket_id"] and found[0]["priority"]=="normal"
    assert request(path(legacy))[1]["order_ref"]==""
    for params in [{"category":"bad"},{"priority":"urgent"},{"order_ref":"x"*81}]:
        assert request("/admin/tickets",claims=ADMIN,params=params)[0]==400


def test_support_quota_configuration_and_actual_monthly_usage(support,monkeypatch):
    monkeypatch.setenv("TICKETS_PER_USER_DAY","3");monkeypatch.setenv("TICKETS_PER_MONTH","9")
    create()
    assert request("/me")[1]["limits"]["tickets_per_day"]==3
    result=request("/admin/overview",claims=ADMIN)[1]
    assert result["limits"]["tickets"]==9 and result["usage"]["ticket"]==1 and result["usage"]["request"]>=3
