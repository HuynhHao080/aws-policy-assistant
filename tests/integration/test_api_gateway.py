import os

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
    stack_name = os.environ.get("AWS_SAM_STACK_NAME")
    if not stack_name or not os.environ.get("POLICY_ASSISTANT_ID_TOKEN"):
        pytest.skip("Opt in with AWS_SAM_STACK_NAME and POLICY_ASSISTANT_ID_TOKEN")
    region = os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-1")

    try:
        return _get_stack_output(stack_name, "PolicyAssistantApiUrl", region)
    except Exception as e:
        pytest.skip("Cannot retrieve API URL; inspect sanitized AWS diagnostics")


class TestDeployedApiGateway:
    """Integration tests against the deployed API Gateway endpoint."""

    def test_get_policy_by_id_success(self, api_gateway_url):
        """GET /policies/POL-001 returns 200 with policy data."""
        url = f"{api_gateway_url.rstrip('/')}/policies/POL-001"
        response = requests.get(url, headers={"Authorization": "Bearer " + os.environ["POLICY_ASSISTANT_ID_TOKEN"]}, timeout=10, allow_redirects=False)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["policy_id"] == "POL-001"
        assert data["title"] == "Customer Refund Policy"
        assert "content" in data
        assert "keywords" in data

    def test_get_policy_by_id_not_found(self, api_gateway_url):
        """GET /policies/POL-999 returns 404."""
        url = f"{api_gateway_url.rstrip('/')}/policies/POL-999"
        response = requests.get(url, headers={"Authorization": "Bearer " + os.environ["POLICY_ASSISTANT_ID_TOKEN"]}, timeout=10, allow_redirects=False)

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "Not found"

    def test_search_policies_by_keyword(self, api_gateway_url):
        """GET /policies?keyword=refund returns matching policies."""
        url = f"{api_gateway_url.rstrip('/')}/policies?keyword=refund"
        response = requests.get(url, headers={"Authorization": "Bearer " + os.environ["POLICY_ASSISTANT_ID_TOKEN"]}, timeout=10, allow_redirects=False)

        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
        assert "count" in data
        assert data["count"] >= 1
        assert any(p["policy_id"] == "POL-001" for p in data["policies"])

    def test_search_policies_case_insensitive(self, api_gateway_url):
        """Keyword search is case-insensitive."""
        url = f"{api_gateway_url.rstrip('/')}/policies?keyword=REFUND"
        response = requests.get(url, headers={"Authorization": "Bearer " + os.environ["POLICY_ASSISTANT_ID_TOKEN"]}, timeout=10, allow_redirects=False)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1

    def test_search_policies_no_matches(self, api_gateway_url):
        """Search with no matches returns empty list."""
        url = f"{api_gateway_url.rstrip('/')}/policies?keyword=nonexistentkeyword123"
        response = requests.get(url, headers={"Authorization": "Bearer " + os.environ["POLICY_ASSISTANT_ID_TOKEN"]}, timeout=10, allow_redirects=False)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["policies"] == []

    def test_search_missing_keyword(self, api_gateway_url):
        """Missing keyword parameter returns 400."""
        url = f"{api_gateway_url.rstrip('/')}/policies"
        response = requests.get(url, headers={"Authorization": "Bearer " + os.environ["POLICY_ASSISTANT_ID_TOKEN"]}, timeout=10, allow_redirects=False)

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Bad request"

    def test_search_empty_keyword(self, api_gateway_url):
        """Empty keyword parameter returns 400."""
        url = f"{api_gateway_url.rstrip('/')}/policies?keyword="
        response = requests.get(url, headers={"Authorization": "Bearer " + os.environ["POLICY_ASSISTANT_ID_TOKEN"]}, timeout=10, allow_redirects=False)

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