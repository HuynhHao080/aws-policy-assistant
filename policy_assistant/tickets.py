"""Explicitly shared customer support requests; never part of AI retrieval."""
import json
import base64
import re
import time
from uuid import uuid4
from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError
try:
    from .service import Problem, now, text, cursor, encode
except ImportError:
    from service import Problem, now, text, cursor, encode

CATEGORIES = {"general", "warranty", "returns", "shipping", "order"}
PRIORITIES = {"low", "normal", "high"}


def choice(value, allowed, field):
    if not isinstance(value, str) or value not in allowed:
        raise Problem(400, "Invalid support " + field)
    return value


def order_reference(value):
    if not isinstance(value, str) or len(value.strip()) > 80 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise Problem(400, "order_ref must be text of at most 80 characters without control characters")
    return value.strip()


STATES = {"open", "in_progress", "resolved", "closed"}
ID = r"t-[0-9]{20}-[a-f0-9]{32}"
MAX_MESSAGES = 20
RETENTION_DAYS = 90
MAX_INTERNAL_NOTES = 20
MAX_ASSIGNMENT_EVENTS = 10
STAFF_ACTIONS = {"claim", "release", "takeover", "note"}
STAFF_FIELDS = {"assigned_to", "assigned_at", "assignment", "assignment_events", "internal_notes", "internal_note_count", "staff_updated_at", "note", "reason"}


def table(service):
    return service.table("SUPPORT_TABLE_NAME")


def check_owner(service, owner):
    account = service.table("USAGE_TABLE_NAME").get_item(Key={"pk": "account#" + owner}, ConsistentRead=True).get("Item", {})
    if account.get("state") == "deleting":
        raise Problem(404, "Support request is unavailable")


def get(service, owner, ticket_id):
    check_owner(service, owner)
    item = table(service).get_item(Key={"owner_id": owner, "ticket_id": ticket_id}, ConsistentRead=True).get("Item")
    if not item or int(item.get("expires_at", 0)) <= int(time.time()):
        raise Problem(404, "Support request not found")
    return item


def customer_waiting_since(item):
    if item.get("status") not in {"open", "in_progress"}:
        return None
    waiting_since = None
    for message in reversed(item.get("messages", [])):
        if message.get("role") != "customer":
            break
        waiting_since = message.get("created_at")
    return waiting_since


def public(item, summary=False, admin=False, viewer=None):
    keys = {"ticket_id", "subject", "status", "category", "priority", "order_ref", "created_at", "updated_at", "expires_at", "message_count"}
    if not summary:
        keys |= {"messages", "revision"}
    if admin:
        keys |= {"owner_id", "assigned_to", "assigned_at", "staff_updated_at", "internal_note_count"}
        if not summary:
            keys |= {"internal_notes", "assignment_events"}
    result = {**{"category": "general", "priority": "normal", "order_ref": ""}, **{k: v for k, v in item.items() if k in keys}}
    if admin:
        result["assignment"] = "mine" if item.get("assigned_to") == viewer and viewer else "other" if item.get("assigned_to") else "unassigned"
        result.setdefault("internal_note_count", 0)
        result["customer_waiting_since"] = customer_waiting_since(item)
        if not summary:
            result.setdefault("internal_notes", [])
            result.setdefault("assignment_events", [])
    return result


def transact(service, item, previous=None, admin=None, delete=False, request_id="unknown", audit_action=None):
    serialize = TypeSerializer().serialize
    owner = item["owner_id"]
    write = {"TableName": table(service).name}
    if delete:
        write["Key"] = {k: serialize(item[k]) for k in ("owner_id", "ticket_id")}
    else:
        write["Item"] = {k: serialize(v) for k, v in item.items()}
    if previous:
        write.update(ConditionExpression="#rev=:old AND expires_at>:clock", ExpressionAttributeNames={"#rev": "revision"}, ExpressionAttributeValues={":old": {"S": previous}, ":clock": {"N": str(int(time.time()))}})
    else:
        write["ConditionExpression"] = "attribute_not_exists(ticket_id)"
    operations = [{"Delete" if delete else "Put": write}, {"ConditionCheck": {
        "TableName": service.table("USAGE_TABLE_NAME").name, "Key": {"pk": {"S": "account#" + owner}},
        "ConditionExpression": "attribute_not_exists(#state) OR #state<>:deleting", "ExpressionAttributeNames": {"#state": "state"}, "ExpressionAttributeValues": {":deleting": {"S": "deleting"}},
    }}]
    if admin:
        audit = {"scope": "admin", "event_id": now() + "#" + uuid4().hex, "actor": admin, "action": audit_action or ("ticket.delete" if delete else "ticket.update"), "resource": item["ticket_id"], "request_id": request_id, "expires_at": int(time.time()) + 90 * 86400}
        operations.append({"Put": {"TableName": service.table("AUDIT_TABLE_NAME").name, "Item": {k: serialize(v) for k, v in audit.items()}}})
    try:
        service.client("dynamodb").transact_write_items(TransactItems=operations)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "TransactionCanceledException" and any(r.get("Code") == "ConditionalCheckFailed" for r in exc.response.get("CancellationReasons", [])):
            raise Problem(409, "Support request changed or its account is unavailable. Reload before retrying.") from None
        raise


def page(service, owner, params, admin=False):
    assignee = params.get("assignee", "all")
    if not admin and "assignee" in params:
        raise Problem(400, "Assignment filters are for staff only")
    choice(assignee, {"all", "mine", "unassigned", "other"}, "assignee filter")
    try:
        limit = int(params.get("limit", "20"))
        if not 1 <= limit <= 50:
            raise ValueError()
    except (ValueError, TypeError):
        raise Problem(400, "limit must be an integer from 1 to 50") from None
    state = params.get("status")
    if state and (not isinstance(state, str) or state not in STATES):
        raise Problem(400, "Invalid support status")
    args = {"Limit": limit, "ConsistentRead": True, "FilterExpression": Attr("expires_at").gt(int(time.time())),
            "ProjectionExpression": "owner_id,ticket_id,subject,#status,created_at,updated_at,expires_at,message_count,#category,#priority,order_ref", "ExpressionAttributeNames": {"#status": "status", "#category": "category", "#priority": "priority"}}
    if state:
        args["FilterExpression"] &= Attr("status").eq(state)
    for field, allowed, default in (("category", CATEGORIES, "general"), ("priority", PRIORITIES, "normal")):
        value = params.get(field)
        if value is not None and value != "":
            choice(value, allowed, field)
            condition = Attr(field).eq(value)
            if value == default:
                condition |= Attr(field).not_exists()
            args["FilterExpression"] &= condition
    if params.get("order_ref") is not None and params["order_ref"] != "":
        reference = order_reference(params["order_ref"])
        if reference:
            args["FilterExpression"] &= Attr("order_ref").eq(reference)
    if admin:
        args["ProjectionExpression"] += ",assigned_to,assigned_at,staff_updated_at,internal_note_count,messages"
        if assignee == "mine":
            args["FilterExpression"] &= Attr("assigned_to").eq(owner)
        elif assignee == "unassigned":
            args["FilterExpression"] &= Attr("assigned_to").not_exists() | Attr("assigned_to").eq("") | Attr("assigned_to").eq(None)
        elif assignee == "other":
            args["FilterExpression"] &= Attr("assigned_to").exists() & Attr("assigned_to").ne(owner) & Attr("assigned_to").ne("") & Attr("assigned_to").ne(None)
        # A bounded one-shop queue; no global scan of private PDFs/history is involved.
        token = params.get("next_token")
        if token:
            try:
                if not isinstance(token, str) or len(token) > 2048:
                    raise ValueError()
                start = json.loads(base64.b64decode(token, altchars=b"-_", validate=True))
                if not isinstance(start, dict) or set(start) != {"owner_id", "ticket_id", "queue_scope"} or start["queue_scope"] != "support":
                    raise ValueError()
                if not isinstance(start["owner_id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", start["owner_id"]) or not isinstance(start["ticket_id"], str) or not re.fullmatch(ID, start["ticket_id"]):
                    raise ValueError()
                args["ExclusiveStartKey"] = {k: start[k] for k in ("owner_id", "ticket_id")}
            except (ValueError, TypeError, UnicodeError):
                raise Problem(400, "Invalid support queue cursor") from None
        result = table(service).scan(**args)
    else:
        args.update(KeyConditionExpression=Key("owner_id").eq(owner), ScanIndexForward=False)
        start = cursor(params.get("next_token"), owner, {"owner_id", "ticket_id"})
        if start:
            args["ExclusiveStartKey"] = start
        result = table(service).query(**args)
    rows = result.get("Items", [])
    if admin:
        # Recheck deletion markers before exposing any customer request summary.
        filtered = []
        for row in rows:
            try:
                check_owner(service, row["owner_id"])
            except Problem:
                continue
            filtered.append(row)
        rows = filtered
    last = result.get("LastEvaluatedKey")
    if last and admin:
        last = {**last, "queue_scope": "support"}
    return {"tickets": [public(r, summary=True, admin=admin, viewer=owner) for r in rows], "next_token": encode(last) if last else None}


def staff_action(service, item, actor, data, previous, request_id):
    action = data["action"]
    allowed = {"action", "expected_revision"} | ({"note"} if action == "note" else {"reason"} if action == "takeover" else set())
    if set(data) - allowed:
        raise Problem(400, "Unexpected staff action fields")
    stamp = now()
    assigned = item.get("assigned_to")
    if action == "note":
        note = text(data.get("note"), "internal note", 1000)
        notes = item.get("internal_notes", [])
        if len(notes) >= MAX_INTERNAL_NOTES:
            raise Problem(409, "This request reached 20 internal notes")
        item["internal_notes"] = notes + [{"note_id": uuid4().hex, "author": actor, "body": note, "created_at": stamp}]
        item["internal_note_count"] = len(item["internal_notes"])
    else:
        reason = None
        if action == "claim":
            if assigned:
                raise Problem(409, "Yêu cầu đã có người phụ trách. Tải lại trước khi nhận bàn giao.")
            item.update(assigned_to=actor, assigned_at=stamp)
        elif action == "release":
            if assigned != actor:
                raise Problem(409, "Chỉ người đang phụ trách có thể trả yêu cầu về hàng đợi.")
            item.pop("assigned_to", None)
            item.pop("assigned_at", None)
        elif action == "takeover":
            reason = text(data.get("reason"), "handover reason", 300)
            if len(reason) < 10:
                raise Problem(400, "Ghi lý do nhận bàn giao từ 10 đến 300 ký tự.")
            if not assigned or assigned == actor:
                raise Problem(409, "Tải lại yêu cầu trước khi nhận bàn giao từ nhân viên khác.")
            item.update(assigned_to=actor, assigned_at=stamp)
        event = {"action": action, "actor": actor, "created_at": stamp, "from": assigned, "to": item.get("assigned_to")}
        if reason is not None:
            event["reason"] = reason
        item["assignment_events"] = (item.get("assignment_events", []) + [event])[-MAX_ASSIGNMENT_EVENTS:]
    # Internal operations do not fabricate a customer reply or extend retention.
    item.update(staff_updated_at=stamp, revision=uuid4().hex)
    transact(service, item, previous, admin=actor, request_id=request_id, audit_action="ticket." + action)
    return public(item, admin=True, viewer=actor)


def handle(service, method, path, owner, data, params, request_id, admin=False):
    root = "/admin/tickets" if admin else "/tickets"
    if path == root and method == "GET":
        return page(service, owner, params, admin)
    if path == root and method == "POST" and not admin:
        if STAFF_FIELDS & set(data):
            raise Problem(400, "Staff-only support metadata is not accepted from customers")
        if data.get("consent") is not True:
            raise Problem(400, "Confirm sharing this message with support staff")
        subject = text(data.get("subject"), "subject", 180)
        message = text(data.get("message"), "message", 1500)
        category = choice(data.get("category", "general"), CATEGORIES, "category")
        reference = order_reference(data.get("order_ref", ""))
        if "priority" in data:
            raise Problem(400, "Only staff may set support priority")
        service.quota(owner, "ticket")
        stamp = now()
        item = {"owner_id": owner, "ticket_id": "t-" + f"{time.time_ns():020d}" + "-" + uuid4().hex,
                "subject": subject, "status": "open", "category": category, "order_ref": reference, "priority": "normal", "created_at": stamp, "updated_at": stamp,
                "expires_at": int(time.time()) + RETENTION_DAYS * 86400, "revision": uuid4().hex,
                "consent_at": stamp, "message_count": 1, "messages": [{"role": "customer", "body": message, "created_at": stamp}]}
        transact(service, item)
        return public(item)
    pattern = r"/admin/tickets/([A-Za-z0-9_-]{1,128})/(" + ID + r")" if admin else r"/tickets/(" + ID + r")"
    match = re.fullmatch(pattern, path)
    if not match:
        raise Problem(404, "Invalid support endpoint")
    target, ticket_id = match.groups() if admin else (owner, match[1])
    item = get(service, target, ticket_id)
    if method == "GET":
        return public(item, admin=admin, viewer=owner)
    if method not in ("PATCH", "DELETE"):
        raise Problem(405, "Method not allowed")
    expected = data.get("expected_revision")
    if not isinstance(expected, str) or expected != item["revision"]:
        raise Problem(409, "Support request changed. Reload before retrying.")
    if method == "DELETE":
        if admin:
            raise Problem(405, "Only the customer can delete their own support request")
        if data.get("confirmation") != "DELETE":
            raise Problem(400, "Explicit deletion confirmation is required")
        transact(service, item, expected, delete=True)
        return {"deleted": True}
    action = data.get("action", "reply")
    if admin and isinstance(action, str) and action in STAFF_ACTIONS:
        return staff_action(service, item, owner, data, expected, request_id)
    if STAFF_FIELDS & set(data):
        raise Problem(400, "Use an explicit staff action for internal metadata")
    if admin and (not isinstance(action, str) or action not in {"reply", "update"}):
        raise Problem(400, "Invalid staff support action")
    if not admin and (not isinstance(action, str) or action not in {"reply", "close"}):
        raise Problem(400, "Customers can reply or close their request")
    if admin and item.get("assigned_to") and item["assigned_to"] != owner:
        raise Problem(409, "Nhân viên khác đang phụ trách. Nhận bàn giao với lý do trước khi phản hồi hoặc đổi trạng thái.")
    state = data.get("status", item["status"]) if admin else ("closed" if action == "close" else "open")
    if not isinstance(state, str) or state not in STATES:
        raise Problem(400, "Invalid support status")
    if not admin and any(k in data for k in ("priority", "category", "order_ref")):
        raise Problem(400, "Customers cannot change support triage metadata")
    priority = choice(data.get("priority", item.get("priority", "normal")), PRIORITIES, "priority")
    message = data.get("message", "")
    if not isinstance(message, str):
        raise Problem(400, "message must be a string")
    if message:
        message = text(message, "message", 1500)
    elif action == "reply" and not admin:
        raise Problem(400, "Reply must contain a message")
    if message and len(item["messages"]) >= MAX_MESSAGES:
        raise Problem(409, "This request reached 20 messages. Create a new request if further discussion is needed.")
    if not admin and item["status"] == "closed" and action == "reply":
        raise Problem(409, "This request is closed. Create a new request for further support.")
    if message:
        item["messages"] = item["messages"] + [{"role": "staff" if admin else "customer", "body": message, "created_at": now()}]
    item.update(status=state, priority=priority, updated_at=now(), revision=uuid4().hex, message_count=len(item["messages"]))
    transact(service, item, expected, admin=owner if admin else None, request_id=request_id)
    return public(item, admin=admin, viewer=owner)
