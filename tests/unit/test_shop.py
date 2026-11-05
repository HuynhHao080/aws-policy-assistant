"""Shared shop profile stays separate from drafts, AI policy rows and private accounts."""
import boto3
import pytest
from policy_assistant import app
from policy_assistant.shop import KEY
from tests.unit.test_public_app import services,request,event  # noqa: F401

ADMIN={"cognito:groups":["administrators"]}
DRAFT={"shop_name":"DEMO shop", "support_email":"", "support_phone":"", "support_hours":"", "returns_instructions":"", "support_message":"Fictional fixture", "mode":"demo"}


def change(revision,action="save_draft",**extra):
    return request("/admin/shop","PATCH",claims=ADMIN,data={"expected_revision":revision,"action":action,**extra})


def test_customer_can_only_see_published_snapshot(services):
    assert request("/shop")[1]=={"configured":False,"profile":None,"published_at":None}
    assert request("/admin/shop")[0]==403
    code,first=change(None,draft=DRAFT)
    assert code==200 and first["draft"]==DRAFT and first["current"] is None
    assert request("/shop")[1]["profile"] is None
    assert change(first["revision"],"publish")[0]==400
    code,published=change(first["revision"],"publish",confirmed=True)
    assert code==200 and published["draft"] is None
    public=request("/shop")[1]
    assert public["profile"]==DRAFT and set(public)=={"configured","profile","published_at"}
    code,saved=change(published["revision"],draft={**DRAFT,"shop_name":"Private draft name"})
    assert code==200 and request("/shop")[1]["profile"]["shop_name"]==DRAFT["shop_name"]
    assert app.table.scan()["Items"]==[]  # Never creates an AI policy row.
    assert change(saved["revision"],"discard_draft")[0]==200
    assert request("/shop")[1]["profile"]==DRAFT
    current=request("/admin/shop",claims=ADMIN)[1]
    assert change(current["revision"],"unpublish")[0]==200
    assert request("/shop")[1]["configured"] is False


def test_new_and_existing_revisions_cannot_overwrite_other_admin(services):
    first=change(None,draft=DRAFT)[1]
    assert change(None,draft={**DRAFT,"shop_name":"Collision"})[0]==409
    newer=change(first["revision"],draft={**DRAFT,"shop_name":"Newer"})[1]
    assert change(first["revision"],"publish",confirmed=True)[0]==409
    assert request("/admin/shop",claims=ADMIN)[1]["revision"]==newer["revision"]


@pytest.mark.parametrize("extra",[{"support_email":"not-an-email"},{"support_email":"x@y.com\nBcc:secret"},{"support_phone":"javascript:bad"},{"mode":[]},{"shop_name":123},{"shop_name":"x"*101},{"unknown":"bad"}])
def test_invalid_draft_is_rejected_before_mutation(services,extra):
    assert change(None,draft={**DRAFT,**extra})[0]==400
    assert request("/admin/shop",claims=ADMIN)[1]["revision"] is None


def test_live_publication_requires_complete_information_and_explicit_confirmation(services):
    first=change(None,draft={**DRAFT,"mode":"live"})[1]
    assert change(first["revision"],"publish",confirmed=True)[0]==400
    live={**DRAFT,"mode":"live","support_email":"support@example.invalid","support_hours":"09:00–17:00 UTC+7","returns_instructions":"Contact staff to verify the receiving address first."}
    saved=change(first["revision"],draft=live)[1]
    assert change(saved["revision"],"publish",confirmed="true")[0]==400
    assert change(saved["revision"],"publish",confirmed=True)[0]==200
    assert request("/shop")[1]["profile"]==live
    audit=request("/admin/audit",claims=ADMIN)[1]["events"]
    assert audit[0]["action"]=="shop.publish" and "support@example.invalid" not in str(audit)


def test_snapshot_and_audit_fail_atomically_and_deleting_admin_cannot_publish(services,monkeypatch):
    service=app._service();monkeypatch.setattr(app,"_service",lambda:service)
    saved=change(None,draft=DRAFT)[1]
    actual=service.client("dynamodb").transact_write_items
    def race(**kwargs):
        service.table("USAGE_TABLE_NAME").put_item(Item={"pk":"account#alice","state":"deleting"})
        return actual(**kwargs)
    monkeypatch.setattr(service.client("dynamodb"),"transact_write_items",race)
    assert change(saved["revision"],"publish",confirmed=True)[0]==409
    assert request("/shop",owner="bob")[1]["configured"] is False
    assert len(request("/admin/audit",owner="staff",claims=ADMIN)[1]["events"])==1
    row=service.table("USAGE_TABLE_NAME").get_item(Key={"pk":KEY})["Item"]
    assert row["revision"]==saved["revision"] and "expires_at" not in row


def test_methods_auth_and_stage_routes(services):
    assert app._strip_stage_prefix("/Prod/shop")=="/shop"
    assert app.lambda_handler(event("/shop", "GET", None),None)["statusCode"]==401
    assert request("/admin/shop","PATCH",data={"action":"publish","expected_revision":None,"confirmed":True})[0]==403
    assert request("/admin/shop","POST",claims=ADMIN)[0]==405
    assert change(None,"publish",confirmed=True)[0]==409
    assert request("/admin/shop","PATCH",claims=ADMIN,data={"action":"save_draft","draft":DRAFT})[0]==409


def test_every_shop_route_explicitly_requires_the_gateway_authorizer():
    from pathlib import Path
    import yaml
    class Loader(yaml.SafeLoader):
        pass
    def tag(loader,suffix,node):
        if isinstance(node,yaml.ScalarNode):return loader.construct_scalar(node)
        if isinstance(node,yaml.SequenceNode):return loader.construct_sequence(node)
        return loader.construct_mapping(node)
    Loader.add_multi_constructor("!",tag)
    template=yaml.load((Path(__file__).resolve().parents[2]/"template.yaml").read_text(encoding="utf-8"),Loader=Loader)
    events=template["Resources"]["PolicyAssistantFunction"]["Properties"]["Events"]
    for name in ["ShopProfile","AdminShopProfile","AdminEditShopProfile"]:
        assert events[name]["Properties"]["Auth"]["Authorizer"]=="PolicyAssistantAuthorizer"
