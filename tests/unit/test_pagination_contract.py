import json
import base64

import pytest

from policy_assistant import app
from tests.unit.test_handler import policies_table, aws_credentials, _create_apigw_event  # noqa: F401


def test_real_scan_cursor_never_skips_or_repeats_matching_items(policies_table):
    for policy_id in ("POL-001", "POL-002", "POL-003"):
        policies_table.update_item(Key={"policy_id": policy_id}, UpdateExpression="SET title_lower = :title", ExpressionAttributeValues={":title": "shared keyword"})
    ids = []
    token = None
    for _ in range(10):
        params = {"keyword": "shared", "limit": "1"}
        if token:
            params["next_token"] = token
        response = app.lambda_handler(_create_apigw_event("/policies", query_parameters=params), None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] <= 1
        ids.extend(p["policy_id"] for p in body["policies"])
        token = body["next_token"]
        if not token:
            break
    else:
        pytest.fail("Cursor did not terminate")
    assert sorted(ids) == ["POL-001", "POL-002", "POL-003"]


@pytest.mark.parametrize("key", [[], None, {}, {"bad_key": "x"}, {"policy_id": 12}, {"policy_id": {"S": "POL-001"}}, {"policy_id": ""}])
def test_cursor_rejects_invalid_key_schema(key):
    token = base64.b64encode(json.dumps(key).encode()).decode()
    response = app.lambda_handler(_create_apigw_event("/policies", query_parameters={"keyword": "policy", "next_token": token}), None)
    assert response["statusCode"] == 400
