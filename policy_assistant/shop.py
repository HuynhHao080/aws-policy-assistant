"""Shared shop contact profile, separate from policies, AI and private customer data."""
import re
import time
from uuid import uuid4
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError
try:
    from .service import Problem, now
except ImportError:
    from service import Problem, now

KEY = "app#shop-profile"
FIELDS = {"shop_name": 100, "support_email": 254, "support_phone": 40,
          "support_hours": 240, "returns_instructions": 1000, "support_message": 1000}


def profile(raw):
    if not isinstance(raw, dict) or set(raw) - (set(FIELDS) | {"mode"}):
        raise Problem(400, "Shop draft contains unsupported fields")
    result = {}
    for field, maximum in FIELDS.items():
        value = raw.get(field, "")
        if not isinstance(value, str) or len(value.strip()) > maximum or any(ord(c) < 32 and c not in "\n\r\t" for c in value):
            raise Problem(400, "Invalid shop field: " + field)
        result[field] = value.strip()
    mode = raw.get("mode", "demo")
    if not isinstance(mode, str) or mode not in ("demo", "live"):
        raise Problem(400, "Invalid shop profile mode")
    result["mode"] = mode
    email, phone = result["support_email"], result["support_phone"]
    if email and not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}", email):
        raise Problem(400, "Invalid support email")
    if phone and (not re.fullmatch(r"[+0-9 ().-]{5,40}", phone) or sum(c.isdigit() for c in phone) < 5):
        raise Problem(400, "Invalid support phone")
    return result


def ready(value):
    if not value["shop_name"]:
        raise Problem(400, "Shop name is required before publication")
    if value["mode"] == "live" and (not (value["support_email"] or value["support_phone"]) or not value["support_hours"] or not value["returns_instructions"]):
        raise Problem(400, "Live profile requires a verified contact, support hours and return reception instructions")


def load(service):
    return service.table("USAGE_TABLE_NAME").get_item(Key={"pk": KEY}, ConsistentRead=True).get("Item")


def customer(item):
    # Only a reviewed published snapshot is visible, never its draft/revision/author.
    current = item.get("current") if item else None
    return {"configured": bool(current), "profile": current, "published_at": item.get("published_at") if current else None}


def detail(item):
    item = item or {}
    return {"revision": item.get("revision"), "current": item.get("current"),
            "draft": item.get("draft"), "updated_at": item.get("updated_at"), "published_at": item.get("published_at")}


def handle(service, method, owner=None, data=None, request_id="unknown"):
    current = load(service)
    if method == "GET":
        return detail(current)
    if method != "PATCH":
        raise Problem(405, "Method not allowed")
    expected = data.get("expected_revision")
    if "expected_revision" not in data or expected != (current or {}).get("revision"):
        raise Problem(409, "Shop profile changed. Reload before saving")
    action = data.get("action")
    if not isinstance(action, str) or action not in ("save_draft", "publish", "unpublish", "discard_draft"):
        raise Problem(400, "Invalid shop profile action")
    item = dict(current or {"pk": KEY})
    if action == "save_draft":
        item["draft"] = profile(data.get("draft"))
    elif action == "publish":
        if data.get("confirmed") is not True:
            raise Problem(400, "Confirm that the saved shop information may be shared with customers")
        if not item.get("draft"):
            raise Problem(409, "Save a draft before publication")
        ready(item["draft"])
        item["current"] = item.pop("draft")
        item["published_at"] = now()
    elif action == "unpublish":
        if not item.get("current"):
            raise Problem(409, "No published shop profile")
        item.pop("current")
        item.pop("published_at", None)
    else:
        if not item.get("draft"):
            raise Problem(409, "No shop draft to discard")
        item.pop("draft")
    item.update(revision=uuid4().hex, updated_at=now())
    serialize = TypeSerializer().serialize
    write = {"TableName": service.table("USAGE_TABLE_NAME").name, "Item": {k: serialize(v) for k,v in item.items()},
             "ConditionExpression": "#rev=:old" if current else "attribute_not_exists(pk)"}
    if current:
        write.update(ExpressionAttributeNames={"#rev": "revision"}, ExpressionAttributeValues={":old": serialize(expected)})
    audit = {"scope": "admin", "event_id": now()+"#"+uuid4().hex, "actor": owner, "action": "shop."+action, "resource": "shop-profile", "request_id": request_id, "expires_at": int(time.time())+90*86400}
    guard = {"TableName": service.table("USAGE_TABLE_NAME").name, "Key": {"pk": {"S": "account#"+owner}},
             "ConditionExpression": "attribute_not_exists(#state) OR #state<>:deleting", "ExpressionAttributeNames": {"#state": "state"}, "ExpressionAttributeValues": {":deleting": {"S": "deleting"}}}
    try:
        service.client("dynamodb").transact_write_items(TransactItems=[{"Put": write}, {"Put": {"TableName": service.table("AUDIT_TABLE_NAME").name, "Item": {k: serialize(v) for k,v in audit.items()}}}, {"ConditionCheck": guard}])
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "TransactionCanceledException" and any(x.get("Code") == "ConditionalCheckFailed" for x in exc.response.get("CancellationReasons", [])):
            raise Problem(409, "Shop profile or account changed. Reload before retrying") from None
        raise
    return detail(item)
