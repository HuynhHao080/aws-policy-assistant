"""Administrator policy drafts, publication and optimistic concurrency.

Drafts share the existing table but never replace a live published snapshot.
Only Service.admin calls this module, after checking the administrator claim.
"""
import base64
import json
import re
from uuid import uuid4

try:
    from .service import Problem, now, text, encode
    from .embeddings import embed, model_id
    from .policy_chunks import policy_chunks
    from .policy_validity import bounds, state as validity_state, DATE_FIELDS
except ImportError:
    from service import Problem, now, text, encode
    from embeddings import embed, model_id
    from policy_chunks import policy_chunks
    from policy_validity import bounds, state as validity_state, DATE_FIELDS

FIELDS = ("title", "category", "content", "keywords", *DATE_FIELDS)


def revision(item):
    return item.get("revision") or item.get("updated_at") or "legacy"


def snapshot(item):
    return {key: item[key] for key in FIELDS if key in item}


def detail(item):
    return {"policy_id": item["policy_id"], "revision": revision(item),
            "publication_state": item.get("publication_state", "unpublished"),
            "validity_state": validity_state(item) if item.get("publication_state") == "published" else "unpublished",
            "current": snapshot(item) if item.get("content") else None,
            "draft": snapshot(item["draft_data"]) if item.get("draft_data") else None,
            "updated_at": item.get("edited_at", item.get("updated_at")), "published_at": item.get("published_at")}


def content(data, previous=None):
    if not isinstance(data, dict):
        raise Problem(400, "draft must be an object")
    item = {"title": text(data.get("title"), "title", 180),
            "category": text(data.get("category"), "category", 80),
            "content": text(data.get("content"), "content", 20000)}
    keywords = data.get("keywords", [])
    if not isinstance(keywords, list) or len(keywords) > 30 or any(not isinstance(k, str) or len(k) > 80 for k in keywords):
        raise Problem(400, "keywords must be a list of at most 30 short strings")
    item["keywords"] = keywords
    try:
        item.update(bounds(data, previous))
    except ValueError as exc:
        raise Problem(400, str(exc)) from None
    return item


def expected_condition(item, expected):
    if item is None:
        if expected is not None:
            raise Problem(409, "Policy no longer exists. Reload before saving.")
        return {"ConditionExpression": "attribute_not_exists(policy_id)"}
    if not isinstance(expected, str) or expected != revision(item):
        raise Problem(409, "Policy changed or was not opened for editing. Reload it before saving.")
    if item.get("revision"):
        return {"ConditionExpression": "#rev = :previous", "ExpressionAttributeNames": {"#rev": "revision"}, "ExpressionAttributeValues": {":previous": {"S": item["revision"]}}}
    if item.get("updated_at"):
        return {"ConditionExpression": "attribute_not_exists(#rev) AND updated_at = :previous", "ExpressionAttributeNames": {"#rev": "revision"}, "ExpressionAttributeValues": {":previous": {"S": item["updated_at"]}}}
    return {"ConditionExpression": "attribute_exists(policy_id) AND attribute_not_exists(#rev) AND attribute_not_exists(updated_at)", "ExpressionAttributeNames": {"#rev": "revision"}}


def indexed(service, fields):
    result = dict(fields)
    for key in ("title", "category", "content"):
        result[key + "_lower"] = result[key].lower()
    result["keywords_lower"] = [k.lower() for k in result["keywords"]]
    if model_id():
        chunks = policy_chunks(result["content"])
        vectors = embed(service, [result["title"] + "\n" + chunk["embedding_text"] for chunk in chunks], "search_document")
        result["search_chunks"] = [{"text": chunk["text"], "vector": vector} for chunk, vector in zip(chunks, vectors)]
        result["embedding_model"] = model_id()
    return result


def listing(service, params):
    validity = params.get("validity", "all")
    if not isinstance(validity, str) or validity not in {"all", "active", "upcoming", "expired", "invalid"}:
        raise Problem(400, "validity must be all, active, upcoming, expired or invalid")
    try:
        limit = int(params.get("limit", "20"))
        if not 1 <= limit <= 50:
            raise ValueError()
    except (ValueError, TypeError):
        raise Problem(400, "limit must be an integer from 1 to 50") from None
    keyword = params.get("keyword", "")
    if not isinstance(keyword, str) or len(keyword) > 200:
        raise Problem(400, "keyword must be at most 200 characters")
    args = {"Limit": limit, "ConsistentRead": True,
            "ProjectionExpression": "policy_id, #title, category, publication_state, updated_at, edited_at, #rev, effective_from, effective_until, draft_data.#title, draft_data.category",
            "ExpressionAttributeNames": {"#title": "title", "#rev": "revision"}}
    token = params.get("next_token")
    if token:
        try:
            if not isinstance(token, str) or len(token) > 2048:
                raise ValueError()
            key = json.loads(base64.b64decode(token, altchars=b"-_", validate=True))
            if not isinstance(key, dict) or set(key) != {"policy_id"} or not isinstance(key["policy_id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", key["policy_id"]):
                raise ValueError()
            args["ExclusiveStartKey"] = key
        except (ValueError, TypeError, UnicodeError):
            raise Problem(400, "Invalid administrator policy cursor") from None
    result = service.policies.scan(**args)
    rows = []
    for item in result.get("Items", []):
        status = validity_state(item) if item.get("publication_state") == "published" else "unpublished"
        if validity != "all" and status != validity:
            continue
        draft = item.get("draft_data", {})
        title = draft.get("title") or item.get("title") or item["policy_id"]
        category = draft.get("category") or item.get("category", "")
        if keyword.casefold() not in (item["policy_id"] + " " + title + " " + item.get("title", "") + " " + category).casefold():
            continue
        rows.append({"policy_id": item["policy_id"], "title": title, "category": category,
                     "publication_state": item.get("publication_state", "unpublished"),
                     "validity_state": status,
                     **{k: item[k] for k in DATE_FIELDS if k in item},
                     "has_draft": bool(draft), "updated_at": item.get("edited_at", item.get("updated_at"))})
    return {"policies": rows, "next_token": encode(result["LastEvaluatedKey"]) if result.get("LastEvaluatedKey") else None}


def handle(service, method, path, owner, data, params, request_id):
    if path == "/admin/policies" and method == "GET":
        return listing(service, params)
    match = re.fullmatch(r"/admin/policies/([A-Za-z0-9_-]{1,80})", path)
    if not match:
        raise Problem(404, "Invalid administrator policy endpoint")
    policy_id = match[1]
    current = service.policies.get_item(Key={"policy_id": policy_id}, ConsistentRead=True).get("Item")
    if method == "GET":
        if not current:
            raise Problem(404, "Policy not found")
        return detail(current)
    if method not in ("PATCH", "PUT", "DELETE"):
        raise Problem(405, "Method not allowed")
    # Legacy creation remains supported; existing policies require a revision for edits.
    expected = data.get("expected_revision")
    if method == "DELETE" and expected is None and current:
        expected = revision(current)
    condition = expected_condition(current, expected)
    if method == "DELETE":
        service.policy_change(owner, "policy.delete", policy_id, request_id, condition=condition)
        return {"deleted": True}
    action = data.get("action") if method == "PATCH" else "legacy_publish"
    if action not in {"save_draft", "publish", "archive", "discard_draft", "legacy_publish"}:
        raise Problem(400, "Unknown policy action")
    if not current and action not in {"save_draft", "legacy_publish"}:
        raise Problem(404, "Policy not found")
    item = dict(current or {"policy_id": policy_id, "publication_state": "draft"})
    if action == "save_draft":
        item["draft_data"] = content(data.get("draft"), item.get("draft_data") or item)
    elif action in {"publish", "legacy_publish"}:
        fields = content(data, item) if action == "legacy_publish" else item.get("draft_data")
        if fields is None and item.get("publication_state") == "archived" and item.get("content"):
            fields = snapshot(item)
        if fields is None:
            raise Problem(409, "Save a draft before publishing")
        # Revalidate even stored drafts before indexing; clear removed bounds.
        fields = content(fields)
        for field in DATE_FIELDS:
            item.pop(field, None)
        for field in ("search_chunks", "embedding_model"):
            item.pop(field, None)
        item.update(indexed(service, fields))
        item.pop("draft_data", None)
        item.update(publication_state="published", published_at=now(), published_by=owner)
    elif action == "archive":
        if item.get("publication_state") != "published":
            raise Problem(409, "Only a published policy can be archived")
        item["publication_state"] = "archived"
    elif action == "discard_draft":
        if not item.get("draft_data"):
            raise Problem(409, "No draft to discard")
        item.pop("draft_data")
        if not item.get("content"):
            item["publication_state"] = "archived"
    stamp = now()
    item.update(edited_at=stamp, updated_by=owner, revision=uuid4().hex)
    if current is None or action not in {"save_draft", "discard_draft"}:
        item["updated_at"] = stamp
    audit_action = {"save_draft": "policy.draft", "publish": "policy.publish", "legacy_publish": "policy.put", "archive": "policy.archive", "discard_draft": "policy.discard_draft"}[action]
    service.policy_change(owner, audit_action, policy_id, request_id, item, condition=condition)
    return {"saved": True, **detail(item)}
