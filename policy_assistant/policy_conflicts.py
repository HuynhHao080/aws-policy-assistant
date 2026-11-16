"""Evidence-first comparison of explicitly labelled deadlines."""
import re
import unicodedata

from boto3.dynamodb.conditions import Attr

try:
    from .policy_validity import bounds, today
    from .service import Problem
except ImportError:
    from policy_validity import bounds, today
    from service import Problem

DEADLINE = re.compile(
    r"^\s*(?:[-*]\s+|\d+[.)]\s+)?([^:\n]{3,100}):\s*([0-9]{1,4})\s*"
    r"(ngày(?:\s+làm việc|\s+lịch)?|(?:business |calendar )?days?)\s*\.?\s*$", re.I
)
MAX_PAGES = 4
MAX_FINDINGS = 20


def deadlines(content):
    for number, line in enumerate(content.splitlines(), 1):
        match = DEADLINE.fullmatch(line)
        if match:
            label, value, unit = match.groups()
            label = " ".join(unicodedata.normalize("NFC", label).casefold().split())
            unit = " ".join(unit.casefold().split())
            unit = {
                "business day": "ngày làm việc", "business days": "ngày làm việc",
                "calendar day": "ngày lịch", "calendar days": "ngày lịch",
                "day": "ngày", "days": "ngày",
            }.get(unit, unit)
            yield label, int(value), unit, number, line.strip()


def review(service, item):
    draft = item.get("draft_data")
    if not draft:
        raise Problem(409, "Lưu bản nháp trước khi rà soát.")
    draft_facts = {}
    for label, value, unit, line, excerpt in deadlines(draft["content"]):
        draft_facts.setdefault(label, []).append((value, unit, line, excerpt))
    result = {"findings": [], "checked_policies": 0, "draft_deadlines": sum(map(len, draft_facts.values())), "truncated": False}
    if not draft_facts:
        return result

    draft_window = bounds(draft)
    first_day = max(today(), draft_window.get("effective_from", ""))
    args = {"Limit": 25, "ConsistentRead": True,
            "FilterExpression": Attr("publication_state").eq("published"),
            "ProjectionExpression": "policy_id,#title,content,published_at,effective_from,effective_until",
            "ExpressionAttributeNames": {"#title": "title"}}
    for _ in range(MAX_PAGES):
        page = service.policies.scan(**args)
        for policy in page.get("Items", []):
            if policy["policy_id"] == item["policy_id"]:
                continue
            try:
                window = bounds(policy)
            except ValueError:
                continue
            overlap_start = max(first_day, window.get("effective_from", ""))
            overlap_end = min(draft_window.get("effective_until", "9999-12-31"), window.get("effective_until", "9999-12-31"))
            if overlap_start > overlap_end:
                continue
            result["checked_policies"] += 1
            for label, value, unit, line, excerpt in deadlines(policy.get("content", "")):
                for draft_value, draft_unit, draft_line, draft_excerpt in draft_facts.get(label, []):
                    if (draft_value, draft_unit) == (value, unit):
                        continue
                    if len(result["findings"]) >= MAX_FINDINGS:
                        result["truncated"] = True
                        return result
                    result["findings"].append({
                        "label": label,
                        "draft": {"line": draft_line, "excerpt": draft_excerpt},
                        "published": {"policy_id": policy["policy_id"], "title": policy.get("title", policy["policy_id"]),
                                      "line": line, "excerpt": excerpt, "published_at": policy.get("published_at")},
                        "overlap_from": overlap_start,
                        "overlap_until": overlap_end if overlap_end != "9999-12-31" else None,
                    })
        cursor = page.get("LastEvaluatedKey")
        if not cursor:
            return result
        args["ExclusiveStartKey"] = cursor
    result["truncated"] = True
    return result
