import os
from urllib.parse import quote
from uuid import uuid4

import boto3
import pytest
import requests

"""
Integration tests for the deployed Policy Assistant API.

Requirements:
- AWS credentials configured (via ~/.aws/credentials or environment)
- Environment variable AWS_SAM_STACK_NAME set to the CloudFormation stack name
  (default: "policy-assistant")
- Stack must be deployed in the same region as the boto3 client (default: ap-southeast-1)

These tests call the LIVE deployed API. They are skipped by default unless
AWS_SAM_STACK_NAME is explicitly set.
"""


def _get_stack_output(stack_name: str, output_key: str, region: str = "ap-southeast-1") -> str:
    """Retrieve a specific output value from a CloudFormation stack."""
    client = boto3.client("cloudformation", region_name=region)
    response = client.describe_stacks(StackName=stack_name)
    stacks = response["Stacks"]
    stack_outputs = stacks[0]["Outputs"]
    matches = [output for output in stack_outputs if output["OutputKey"] == output_key]
    if not matches:
        raise KeyError(f"Output '{output_key}' not found in stack '{stack_name}'")
    return matches[0]["OutputValue"]


@pytest.fixture(scope="session")
def api_gateway_url():
    """
    Get the API Gateway URL from CloudFormation stack outputs.

    Uses the 'PolicyAssistantApiUrl' output key (not the legacy 'HelloWorldApi').
    Requires AWS_SAM_STACK_NAME environment variable to be set.
    """
    if not os.environ.get("AWS_SAM_STACK_NAME"):
        pytest.skip("Set AWS_SAM_STACK_NAME explicitly for live tests")
    stack_name = os.environ["AWS_SAM_STACK_NAME"]
    region = os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-1")

    try:
        return _get_stack_output(stack_name, "PolicyAssistantApiUrl", region)
    except Exception as e:
        pytest.fail(f"Cannot retrieve configured stack API URL: {e}")


@pytest.fixture
def authenticated_http(api_gateway_url):
    token = os.environ.get("POLICY_ASSISTANT_ID_TOKEN")
    if not token:
        pytest.fail("Set POLICY_ASSISTANT_ID_TOKEN for protected live tests")
    with requests.Session() as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.fixture
def published_case():
    policy_id = os.environ.get("POLICY_ASSISTANT_TEST_POLICY_ID")
    keyword = os.environ.get("POLICY_ASSISTANT_TEST_KEYWORD")
    if not policy_id or not keyword:
        pytest.skip("Set explicit published policy ID and keyword for read-only policy fixture tests; use scripts/smoke_live.py for disposable full acceptance")
    return policy_id, keyword


class TestDeployedApiGateway:
    """Integration tests against the deployed API Gateway endpoint."""

    def test_get_policy_by_id_success(self, api_gateway_url, authenticated_http, published_case):
        """GET /policies/POL-001 returns 200 with policy data."""
        url = f"{api_gateway_url.rstrip('/')}/policies/{quote(published_case[0], safe='')}"
        response = authenticated_http.get(url, timeout=10)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["policy_id"] == published_case[0]
        assert data["title"]
        assert "content" in data
        assert "keywords" in data

    def test_get_policy_by_id_not_found(self, api_gateway_url, authenticated_http):
        """GET /policies/POL-999 returns 404."""
        url = f"{api_gateway_url.rstrip('/')}/policies/MISSING-{uuid4().hex}"
        response = authenticated_http.get(url, timeout=10)

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "Not found"

    def test_search_policies_by_keyword(self, api_gateway_url, authenticated_http, published_case):
        """GET /policies?keyword=refund returns matching policies."""
        url = f"{api_gateway_url.rstrip('/')}/policies?keyword={quote(published_case[1], safe='')}"
        response = authenticated_http.get(url, timeout=10)

        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
        assert "count" in data
        assert data["count"] >= 1
        assert any(p["policy_id"] == published_case[0] for p in data["policies"])

    def test_search_policies_case_insensitive(self, api_gateway_url, authenticated_http, published_case):
        """Keyword search is case-insensitive."""
        url = f"{api_gateway_url.rstrip('/')}/policies?keyword={quote(published_case[1].upper(), safe='')}"
        response = authenticated_http.get(url, timeout=10)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1

    def test_search_policies_no_matches(self, api_gateway_url, authenticated_http):
        """Search with no matches returns empty list."""
        url = f"{api_gateway_url.rstrip('/')}/policies?keyword={uuid4().hex}"
        response = authenticated_http.get(url, timeout=10)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["policies"] == []

    def test_search_missing_keyword(self, api_gateway_url, authenticated_http):
        """Missing keyword parameter returns 400."""
        url = f"{api_gateway_url.rstrip('/')}/policies"
        response = authenticated_http.get(url, timeout=10)

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Bad request"

    def test_search_empty_keyword(self, api_gateway_url, authenticated_http):
        """Empty keyword parameter returns 400."""
        url = f"{api_gateway_url.rstrip('/')}/policies?keyword="
        response = authenticated_http.get(url, timeout=10)

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Bad request"

    def test_cors_preflight(self, api_gateway_url):
        """OPTIONS preflight returns 204 with CORS headers."""
        url = f"{api_gateway_url.rstrip('/')}/policies/POL-001"
        response = requests.options(
            url,
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
            timeout=10,
        )

        assert response.status_code == 204
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert "GET" in response.headers.get("access-control-allow-methods", "")

    def test_invalid_method_returns_404(self, api_gateway_url):
        """POST to a GET-only endpoint returns 404 (API Gateway behavior)."""
        url = f"{api_gateway_url.rstrip('/')}/policies/POL-001"
        response = requests.post(url, timeout=10)

        # API Gateway returns 404 for unsupported methods on existing routes
        assert response.status_code == 404

    def test_health_is_public(self, api_gateway_url):
        response = requests.get(f"{api_gateway_url.rstrip('/')}/health", timeout=10)
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_policies_require_authentication(self, api_gateway_url):
        response = requests.get(f"{api_gateway_url.rstrip('/')}/policies?keyword=refund", timeout=10)
        assert response.status_code == 401
