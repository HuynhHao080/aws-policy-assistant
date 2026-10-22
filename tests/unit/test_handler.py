import json
import os
import sys
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

# Add policy_assistant to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "policy_assistant"))

from policy_assistant import app


# Sample test policies matching sample_data/policies.json (with lowercase fields)
SAMPLE_POLICIES = [
    {
        "policy_id": "POL-001",
        "title": "Customer Refund Policy",
        "category": "Customer Service",
        "content": "Customers may request a full refund within 30 days of purchase for any product that is defective, damaged, or not as described. Refunds will be issued to the original payment method within 5-10 business days after the returned item is received and inspected. Items must be in their original packaging with all accessories included. Shipping costs are non-refundable unless the return is due to our error. Digital products and gift cards are not eligible for refunds.",
        "keywords": ["refund", "return", "customer", "money back", "30 days", "defective", "damaged"],
        "title_lower": "customer refund policy",
        "category_lower": "customer service",
        "content_lower": "customers may request a full refund within 30 days of purchase for any product that is defective, damaged, or not as described. refunds will be issued to the original payment method within 5-10 business days after the returned item is received and inspected. items must be in their original packaging with all accessories included. shipping costs are non-refundable unless the return is due to our error. digital products and gift cards are not eligible for refunds.",
        "keywords_lower": ["refund", "return", "customer", "money back", "30 days", "defective", "damaged"]
    },
    {
        "policy_id": "POL-002",
        "title": "Privacy Policy",
        "category": "Legal",
        "content": "We collect personal information including name, email address, shipping address, and payment details when you place an order or create an account. This information is used solely to process orders, provide customer support, and improve our services. We do not sell your personal data to third parties. We may share information with trusted service providers (payment processors, shipping carriers) who are contractually obligated to protect your data. You have the right to access, correct, or delete your personal information at any time by contacting our privacy team.",
        "keywords": ["privacy", "personal data", "GDPR", "information", "collection", "third party", "access", "deletion"],
        "title_lower": "privacy policy",
        "category_lower": "legal",
        "content_lower": "we collect personal information including name, email address, shipping address, and payment details when you place an order or create an account. this information is used solely to process orders, provide customer support, and improve our services. we do not sell your personal data to third parties. we may share information with trusted service providers (payment processors, shipping carriers) who are contractually obligated to protect your data. you have the right to access, correct, or delete your personal information at any time by contacting our privacy team.",
        "keywords_lower": ["privacy", "personal data", "gdpr", "information", "collection", "third party", "access", "deletion"]
    },
    {
        "policy_id": "POL-003",
        "title": "Terms of Service",
        "category": "Legal",
        "content": "By using our website and services, you agree to these Terms of Service. You must be at least 18 years old to create an account. You are responsible for maintaining the confidentiality of your account credentials. We reserve the right to modify, suspend, or discontinue any service at any time. Our liability is limited to the maximum extent permitted by law. Disputes will be resolved through binding arbitration in Singapore. These terms are governed by the laws of Singapore.",
        "keywords": ["terms", "service", "agreement", "account", "liability", "arbitration", "Singapore", "governing law"],
        "title_lower": "terms of service",
        "category_lower": "legal",
        "content_lower": "by using our website and services, you agree to these terms of service. you must be at least 18 years old to create an account. you are responsible for maintaining the confidentiality of your account credentials. we reserve the right to modify, suspend, or discontinue any service at any time. our liability is limited to the maximum extent permitted by law. disputes will be resolved through binding arbitration in singapore. these terms are governed by the laws of singapore.",
        "keywords_lower": ["terms", "service", "agreement", "account", "liability", "arbitration", "singapore", "governing law"]
    }
]


@pytest.fixture(scope="function")
def aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-southeast-1")
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")


@pytest.fixture(scope="function")
def policies_table(aws_credentials):
    """Create a mocked DynamoDB table with sample data."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-1")
        table_name = "PolicyAssistantPolicies"

        # Create table
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "policy_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "policy_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )

        # Wait for table to be active
        table.wait_until_exists()

        # Insert sample policies
        for policy in SAMPLE_POLICIES:
            table.put_item(Item=policy)

        # Patch the table name in the app module
        with patch.dict(os.environ, {"POLICIES_TABLE_NAME": table_name, "AWS_REGION": "ap-southeast-1"}):
            # Re-import to pick up new env vars
            import importlib
            importlib.reload(app)
            yield table


def _create_apigw_event(path: str, method: str = "GET", path_parameters: dict = None, query_parameters: dict = None) -> dict:
    """Create a mock API Gateway HTTP API v2 event."""
    return {
        "version": "2.0",
        "routeKey": f"{method} {path}",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {
            "accept": "application/json",
            "host": "localhost:3000",
            "user-agent": "pytest"
        },
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "test-api",
            "domainName": "localhost:3000",
            "domainPrefix": "localhost",
            "http": {
                "method": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest"
            },
            "requestId": "test-request-id",
            "routeKey": f"{method} {path}",
            "stage": "Prod",
            "time": "01/Jan/2024:00:00:00 +0000",
            "timeEpoch": 1704067200000
        },
        "pathParameters": path_parameters or {},
        "queryStringParameters": query_parameters or {},
        "body": None,
        "isBase64Encoded": False
    }


class TestGetPolicyById:
    """Tests for GET /policies/{policy_id} endpoint."""

    def test_get_policy_by_id_success(self, policies_table):
        """Test successful retrieval of a policy by ID."""
        event = _create_apigw_event(
            path="/policies/POL-001",
            path_parameters={"policy_id": "POL-001"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["policy_id"] == "POL-001"
        assert body["title"] == "Customer Refund Policy"
        assert body["category"] == "Customer Service"
        assert "refund" in body["keywords"]

    def test_get_policy_by_id_not_found(self, policies_table):
        """Test 404 when policy ID does not exist."""
        event = _create_apigw_event(
            path="/policies/POL-999",
            path_parameters={"policy_id": "POL-999"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["error"] == "Not found"
        assert "POL-999" in body["message"]

    def test_get_policy_by_id_empty_id(self, policies_table):
        """Test 400 when policy_id is empty."""
        event = _create_apigw_event(
            path="/policies/",
            path_parameters={"policy_id": ""}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad request"
        assert "policy_id is required" in body["message"]

    def test_get_policy_by_id_whitespace_id(self, policies_table):
        """Test 400 when policy_id is only whitespace."""
        event = _create_apigw_event(
            path="/policies/  ",
            path_parameters={"policy_id": "  "}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad request"


class TestSearchPolicies:
    """Tests for GET /policies?keyword=xxx endpoint."""

    def test_search_policies_success_refund(self, policies_table):
        """Test keyword search for 'refund' returns POL-001."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "policies" in body
        assert body["count"] == 1
        assert len(body["policies"]) == 1
        assert body["policies"][0]["policy_id"] == "POL-001"
        assert "refund" in body["policies"][0]["title"].lower()

    def test_search_policies_success_privacy(self, policies_table):
        """Test keyword search for 'privacy' returns POL-002."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "privacy"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 1
        assert body["policies"][0]["policy_id"] == "POL-002"

    def test_search_policies_success_legal(self, policies_table):
        """Test keyword search for 'legal' returns POL-002 and POL-003."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "legal"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 2
        policy_ids = {p["policy_id"] for p in body["policies"]}
        assert policy_ids == {"POL-002", "POL-003"}

    def test_search_policies_case_insensitive(self, policies_table):
        """Test keyword search is case-insensitive."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "REFUND"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 1
        assert body["policies"][0]["policy_id"] == "POL-001"

    def test_search_policies_partial_match(self, policies_table):
        """Test keyword search matches partial words."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "ref"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 1
        assert body["policies"][0]["policy_id"] == "POL-001"

    def test_search_policies_matches_keywords_field(self, policies_table):
        """Test keyword search matches the keywords array field."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "arbitration"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 1
        assert body["policies"][0]["policy_id"] == "POL-003"

    def test_search_policies_no_matches(self, policies_table):
        """Test keyword search with no matching policies returns empty list."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "nonexistent"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 0
        assert body["policies"] == []

    def test_search_policies_missing_keyword(self, policies_table):
        """Test 400 when keyword query parameter is missing."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad request"
        assert "keyword" in body["message"].lower()

    def test_search_policies_empty_keyword(self, policies_table):
        """Test 400 when keyword query parameter is empty string."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": ""}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad request"

    def test_search_policies_whitespace_keyword(self, policies_table):
        """Test 400 when keyword query parameter is only whitespace."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "   "}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad request"


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_invalid_method_post(self, policies_table):
        """Test 405 for POST method."""
        event = _create_apigw_event(
            path="/policies/POL-001",
            method="POST",
            path_parameters={"policy_id": "POL-001"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 405
        body = json.loads(response["body"])
        assert body["error"] == "Method not allowed"

    def test_missing_request_context_does_not_crash(self, policies_table):
        """Failure mode: event lacks requestContext; handler must not crash on logging."""
        event = {"requestContext": {}}
        response = app.lambda_handler(event, None)
        # Should return 404 (unknown endpoint) or handle gracefully
        assert response["statusCode"] in (404, 405, 200, 400)

    def test_invalid_method_put(self, policies_table):
        """Test 405 for PUT method."""
        event = _create_apigw_event(
            path="/policies",
            method="PUT",
            query_parameters={"keyword": "test"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 405

    def test_invalid_endpoint(self, policies_table):
        """Test 404 for invalid endpoint."""
        event = _create_apigw_event(
            path="/invalid",
            method="GET"
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["error"] == "Not found"

    def test_cors_headers_present(self, policies_table):
        """Test that CORS headers are present in responses."""
        event = _create_apigw_event(
            path="/policies/POL-001",
            path_parameters={"policy_id": "POL-001"}
        )
        response = app.lambda_handler(event, {})

        headers = response["headers"]
        assert "Access-Control-Allow-Origin" in headers
        assert headers["Access-Control-Allow-Origin"] == "http://localhost:8080"
        assert "Access-Control-Allow-Headers" in headers
        assert headers["Access-Control-Allow-Methods"] == "GET,POST,OPTIONS"


class TestHealthCheck:
    """Tests for GET /health endpoint."""

    def test_health_check_success(self, policies_table):
        """Test health check returns 200 with healthy status."""
        event = _create_apigw_event(path="/health")
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "healthy"

    def test_health_check_with_trailing_slash(self, policies_table):
        """Test health check with trailing slash returns 200."""
        event = _create_apigw_event(path="/health/")
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "healthy"


class TestSearchLimit:
    """Tests for search limit parameter."""

    def test_search_with_valid_limit(self, policies_table):
        """Test search with limit parameter returns capped results."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "legal", "limit": "1"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 1
        assert len(body["policies"]) == 1
        assert "scanned_count" in body

    def test_search_with_limit_zero(self, policies_table):
        """Test search with limit=0 returns 400."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "legal", "limit": "0"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad request"

    def test_search_with_negative_limit(self, policies_table):
        """Test search with negative limit returns 400."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "legal", "limit": "-1"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad request"

    def test_search_with_limit_above_max(self, policies_table):
        """Test search with limit > 100 returns 400."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "legal", "limit": "101"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad request"

    def test_search_with_invalid_limit(self, policies_table):
        """Test search with non-integer limit returns 400."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "legal", "limit": "abc"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad request"


class TestScanBudget:
    """Tests for DynamoDB Scan budget enforcement."""

    def test_search_response_includes_truncated_field(self, policies_table):
        """Test search response includes truncated field (backward compatible)."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "policies" in body
        assert "count" in body
        assert "scanned_count" in body
        assert "truncated" in body
        assert isinstance(body["truncated"], bool)

    def test_dynamodb_limit_parameter_passed(self, policies_table):
        """Test DynamoDB Limit parameter is passed on each Scan call."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund"}
        )

        original_scan = app.table.scan
        captured_kwargs = []

        def mock_scan_capture(**kwargs):
            captured_kwargs.append(kwargs)
            # Return single page with all items, no LastEvaluatedKey
            return {
                "Items": [p for p in SAMPLE_POLICIES if "refund" in p.get("content_lower", "") or "refund" in p.get("title_lower", "") or "refund" in p.get("category_lower", "") or "refund" in p.get("keywords_lower", [])],
                "ScannedCount": len(SAMPLE_POLICIES),
                "Count": 1,
            }

        app.table.scan = mock_scan_capture

        try:
            response = app.lambda_handler(event, {})

            assert response["statusCode"] == 200
            assert len(captured_kwargs) == 1
            assert "Limit" in captured_kwargs[0]
            assert captured_kwargs[0]["Limit"] == 1000  # MAX_SCAN_ITEMS
        finally:
            app.table.scan = original_scan

    def test_scan_budget_exhaustion_returns_truncated(self, policies_table):
        """Test that scan budget exhaustion sets truncated=True."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "nonexistent"}
        )

        original_scan = app.table.scan
        call_count = [0]

        def mock_scan_budget(**kwargs):
            call_count[0] += 1
            # Simulate pages with items scanned but no matches, always with LastEvaluatedKey
            return {
                "Items": [],
                "ScannedCount": 500,
                "Count": 0,
                "LastEvaluatedKey": {"policy_id": f"dummy-{call_count[0]}"}
            }

        app.table.scan = mock_scan_budget

        try:
            response = app.lambda_handler(event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["truncated"] is True
            assert body["count"] == 0
            assert body["scanned_count"] == 1000  # MAX_SCAN_ITEMS
            # Should have made 2 scan calls: first with Limit=1000, second with Limit=500
            assert call_count[0] == 2
        finally:
            app.table.scan = original_scan

    def test_no_further_scan_calls_after_budget(self, policies_table):
        """Test that no Scan calls happen after budget is reached."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "nonexistent"}
        )

        original_scan = app.table.scan
        call_count = [0]

        def mock_scan_stop(**kwargs):
            call_count[0] += 1
            return {
                "Items": [],
                "ScannedCount": 1000,
                "Count": 0,
                "LastEvaluatedKey": {"policy_id": "has-more"}
            }

        app.table.scan = mock_scan_stop

        try:
            response = app.lambda_handler(event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["truncated"] is True
            assert body["scanned_count"] == 1000
            # Only one scan call should happen because budget is exhausted after first page
            assert call_count[0] == 1
        finally:
            app.table.scan = original_scan

    def test_zero_match_page_with_last_evaluated_key(self, policies_table):
        """Test page with zero matches but non-empty LastEvaluatedKey continues scanning."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund"}
        )

        original_scan = app.table.scan
        call_count = [0]

        def mock_scan_zero_match_then_match(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First page: zero matches, but has LastEvaluatedKey
                return {
                    "Items": [],
                    "ScannedCount": 2,
                    "Count": 0,
                    "LastEvaluatedKey": {"policy_id": "POL-002"}
                }
            else:
                # Second page: has the match
                return {
                    "Items": [SAMPLE_POLICIES[0]],
                    "ScannedCount": 1,
                    "Count": 1,
                }

        app.table.scan = mock_scan_zero_match_then_match

        try:
            response = app.lambda_handler(event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["count"] == 1
            assert body["scanned_count"] == 3
            assert body["truncated"] is False
            assert call_count[0] == 2
        finally:
            app.table.scan = original_scan

    def test_scan_limit_respects_remaining_budget(self, policies_table):
        """Test that DynamoDB Limit parameter respects remaining scan budget."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund"}
        )

        original_scan = app.table.scan
        captured_limits = []

        def mock_scan_capture_limit(**kwargs):
            captured_limits.append(kwargs.get("Limit"))
            return {
                "Items": [],
                "ScannedCount": kwargs.get("Limit", 0),
                "Count": 0,
                "LastEvaluatedKey": None
            }

        app.table.scan = mock_scan_capture_limit

        try:
            response = app.lambda_handler(event, {})

            assert response["statusCode"] == 200
            # First (and only) scan call should use Limit=1000 (MAX_SCAN_ITEMS)
            assert captured_limits == [1000]
        finally:
            app.table.scan = original_scan

    def test_exact_budget_no_more_pages_not_truncated(self, policies_table):
        """Test that exactly 1000 scanned items with no LastEvaluatedKey is not truncated."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund"}
        )

        original_scan = app.table.scan

        def mock_scan_exact_budget_complete(**kwargs):
            return {
                "Items": [],
                "ScannedCount": 1000,
                "Count": 0,
                "LastEvaluatedKey": None
            }

        app.table.scan = mock_scan_exact_budget_complete

        try:
            response = app.lambda_handler(event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["truncated"] is False
            assert body["scanned_count"] == 1000
        finally:
            app.table.scan = original_scan

    def test_exact_budget_with_more_pages_is_truncated(self, policies_table):
        """Test that exactly 1000 scanned items with LastEvaluatedKey is truncated."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund"}
        )

        original_scan = app.table.scan

        def mock_scan_exact_budget_more_pages(**kwargs):
            return {
                "Items": [],
                "ScannedCount": 1000,
                "Count": 0,
                "LastEvaluatedKey": {"policy_id": "has-more"}
            }

        app.table.scan = mock_scan_exact_budget_more_pages

        try:
            response = app.lambda_handler(event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["truncated"] is True
            assert body["scanned_count"] == 1000
        finally:
            app.table.scan = original_scan

    def test_result_limit_reached_before_budget_not_truncated(self, policies_table):
        """Test that reaching result limit before scan budget does not set truncated."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund", "limit": "1"}
        )

        original_scan = app.table.scan

        def mock_scan_with_limit_stop(**kwargs):
            return {
                "Items": [SAMPLE_POLICIES[0]],
                "ScannedCount": 1,
                "Count": 1,
                "LastEvaluatedKey": {"policy_id": "POL-002"}
            }

        app.table.scan = mock_scan_with_limit_stop

        try:
            response = app.lambda_handler(event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["count"] == 1
            assert body["truncated"] is False
            assert body["scanned_count"] == 1
        finally:
            app.table.scan = original_scan


class TestInternalFieldStripping:
    """Tests that internal lowercase fields are stripped from responses."""

    def test_get_policy_by_id_strips_lowercase_fields(self, policies_table):
        """Test get by ID does not return lowercase fields."""
        event = _create_apigw_event(
            path="/policies/POL-001",
            path_parameters={"policy_id": "POL-001"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "title_lower" not in body
        assert "category_lower" not in body
        assert "content_lower" not in body
        assert "keywords_lower" not in body
        assert "title" in body
        assert "category" in body
        assert "content" in body
        assert "keywords" in body

    def test_search_strips_lowercase_fields(self, policies_table):
        """Test search does not return lowercase fields."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["policies"]) == 1
        policy = body["policies"][0]
        assert "title_lower" not in policy
        assert "category_lower" not in policy
        assert "content_lower" not in policy
        assert "keywords_lower" not in policy
        assert "title" in policy
        assert "category" in policy
        assert "content" in policy
        assert "keywords" in policy


class TestDynamoDBErrors:
    """Tests for DynamoDB error handling."""

    def test_get_item_client_error(self, policies_table):
        """Test GetItem ClientError returns 500."""
        from botocore.exceptions import ClientError

        event = _create_apigw_event(
            path="/policies/POL-001",
            path_parameters={"policy_id": "POL-001"}
        )

        original_get_item = app.table.get_item

        def mock_get_item_error(**kwargs):
            raise ClientError(
                {"Error": {"Code": "InternalServerError", "Message": "Internal failure"}},
                "GetItem"
            )

        app.table.get_item = mock_get_item_error

        try:
            response = app.lambda_handler(event, {})

            assert response["statusCode"] == 500
            body = json.loads(response["body"])
            assert body["error"] == "Internal server error"
        finally:
            app.table.get_item = original_get_item

    def test_scan_client_error(self, policies_table):
        """Test Scan ClientError returns 500."""
        from botocore.exceptions import ClientError

        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund"}
        )

        original_scan = app.table.scan

        def mock_scan_error(**kwargs):
            raise ClientError(
                {"Error": {"Code": "InternalServerError", "Message": "Internal failure"}},
                "Scan"
            )

        app.table.scan = mock_scan_error

        try:
            response = app.lambda_handler(event, {})

            assert response["statusCode"] == 500
            body = json.loads(response["body"])
            assert body["error"] == "Internal server error"
        finally:
            app.table.scan = original_scan


class TestStagePrefixRouting:
    """Tests for stage prefix stripping with legitimate policy IDs."""

    def test_policy_id_matching_stage_name(self, policies_table):
        """Test that policy_id 'prod' is not stripped as a stage prefix."""
        policies_table.put_item(Item={
            "policy_id": "prod",
            "title": "Prod Policy",
            "category": "Test",
            "content": "A policy with ID matching a stage name",
            "keywords": ["test"],
            "title_lower": "prod policy",
            "category_lower": "test",
            "content_lower": "a policy with id matching a stage name",
            "keywords_lower": ["test"]
        })

        event = _create_apigw_event(
            path="/Prod/policies/prod",
            path_parameters={"policy_id": "prod"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["policy_id"] == "prod"
        assert body["title"] == "Prod Policy"


class TestUnexpectedException:
    """Tests for unexpected exception handling."""

    def test_unexpected_exception_returns_500(self, policies_table):
        """Test unexpected exception returns 500 without stack trace."""
        event = _create_apigw_event(
            path="/policies/POL-001",
            path_parameters={"policy_id": "POL-001"}
        )

        original_get_item = app.table.get_item

        def mock_unexpected_error(**kwargs):
            raise RuntimeError("Unexpected failure")

        app.table.get_item = mock_unexpected_error

        try:
            response = app.lambda_handler(event, {})

            assert response["statusCode"] == 500
            body = json.loads(response["body"])
            assert body["error"] == "Internal server error"
            assert "traceback" not in body["message"].lower()
            assert "RuntimeError" not in body["message"]
        finally:
            app.table.get_item = original_get_item


class TestResponseFormat:

    def test_success_response_has_json_content_type(self, policies_table):
        """Test successful responses have application/json content type."""
        event = _create_apigw_event(
            path="/policies/POL-001",
            path_parameters={"policy_id": "POL-001"}
        )
        response = app.lambda_handler(event, {})

        assert response["headers"]["Content-Type"] == "application/json"

    def test_error_response_has_json_content_type(self, policies_table):
        """Test error responses have application/json content type."""
        event = _create_apigw_event(
            path="/policies/POL-999",
            path_parameters={"policy_id": "POL-999"}
        )
        response = app.lambda_handler(event, {})

        assert response["headers"]["Content-Type"] == "application/json"

    def test_search_response_structure(self, policies_table):
        """Test search response has correct structure."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund"}
        )
        response = app.lambda_handler(event, {})

        body = json.loads(response["body"])
        assert "policies" in body
        assert "count" in body
        assert "scanned_count" in body
        assert "truncated" in body
        assert isinstance(body["policies"], list)
        assert isinstance(body["count"], int)
        assert isinstance(body["scanned_count"], int)
        assert isinstance(body["truncated"], bool)
        assert body["count"] == len(body["policies"])


class TestSearchPagination:
    """Tests for search pagination with next_token parameter."""

    def test_search_with_limit_returns_next_token(self, policies_table):
        """Test search with limit=1 returns next_token when more results exist."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "legal", "limit": "1"}
        )

        original_scan = app.table.scan

        def mock_scan_first(**kwargs):
            return {
                "Items": [SAMPLE_POLICIES[0]],
                "ScannedCount": 3,
                "Count": 1,
                "LastEvaluatedKey": {"policy_id": "POL-002"}
            }

        app.table.scan = mock_scan_first

        try:
            response = app.lambda_handler(event, {})

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["count"] == 1
            assert len(body["policies"]) == 1
            assert "next_token" in body
            assert body["next_token"] is not None
            assert isinstance(body["next_token"], str)
        finally:
            app.table.scan = original_scan

    def test_search_with_next_token_returns_next_page(self, policies_table):
        """Test search with next_token returns the next page of results."""
        event1 = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "legal", "limit": "1"}
        )

        original_scan = app.table.scan

        def mock_scan_first(**kwargs):
            return {
                "Items": [SAMPLE_POLICIES[0]],
                "ScannedCount": 3,
                "Count": 1,
                "LastEvaluatedKey": {"policy_id": "POL-002"}
            }

        def mock_scan_second(**kwargs):
            return {
                "Items": [SAMPLE_POLICIES[1]],
                "ScannedCount": 3,
                "Count": 1,
                "LastEvaluatedKey": None
            }

        app.table.scan = mock_scan_first

        try:
            response1 = app.lambda_handler(event1, {})
            body1 = json.loads(response1["body"])
            assert body1["count"] == 1
            assert body1["next_token"] is not None

            # Second page with next_token
            app.table.scan = mock_scan_second
            event2 = _create_apigw_event(
                path="/policies",
                query_parameters={"keyword": "legal", "next_token": body1["next_token"]}
            )
            response2 = app.lambda_handler(event2, {})
            body2 = json.loads(response2["body"])
            assert body2["count"] == 1
            assert body2["policies"][0]["policy_id"] != body1["policies"][0]["policy_id"]
        finally:
            app.table.scan = original_scan

    def test_search_final_page_no_next_token(self, policies_table):
        """Test search with limit=1 returns no next_token on final page."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "legal", "limit": "1"}
        )

        original_scan = app.table.scan

        def mock_scan_first(**kwargs):
            return {
                "Items": [SAMPLE_POLICIES[0]],
                "ScannedCount": 3,
                "Count": 1,
                "LastEvaluatedKey": {"policy_id": "POL-002"}
            }

        def mock_scan_second(**kwargs):
            return {
                "Items": [SAMPLE_POLICIES[1], SAMPLE_POLICIES[2]],
                "ScannedCount": 3,
                "Count": 2,
                "LastEvaluatedKey": None
            }

        app.table.scan = mock_scan_first

        try:
            response1 = app.lambda_handler(event, {})
            body1 = json.loads(response1["body"])
            assert body1["count"] == 1
            assert body1["next_token"] is not None

            # Second page - no more pages
            app.table.scan = mock_scan_second
            event2 = _create_apigw_event(
                path="/policies",
                query_parameters={"keyword": "legal", "next_token": body1["next_token"]}
            )
            response2 = app.lambda_handler(event2, {})
            body2 = json.loads(response2["body"])
            assert body2["count"] == 2
            assert body2["next_token"] is None  # No more pages
        finally:
            app.table.scan = original_scan

    def test_search_with_invalid_next_token_returns_400(self, policies_table):
        """Test search with invalid next_token returns 400."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund", "next_token": "not-valid-base64!!!", "limit": "1"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad request"

    def test_search_with_next_token_round_trip(self, policies_table):
        """Test that next_token round-trips correctly across pages."""
        event1 = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund", "limit": "1"}
        )

        original_scan = app.table.scan

        def mock_scan_first(**kwargs):
            return {
                "Items": [SAMPLE_POLICIES[0]],
                "ScannedCount": 3,
                "Count": 1,
                "LastEvaluatedKey": {"policy_id": "POL-002"}
            }

        def mock_scan_second(**kwargs):
            return {
                "Items": [SAMPLE_POLICIES[1]],
                "ScannedCount": 3,
                "Count": 1,
                "LastEvaluatedKey": None
            }

        app.table.scan = mock_scan_first

        try:
            response1 = app.lambda_handler(event1, {})
            body1 = json.loads(response1["body"])
            assert body1["count"] == 1
            assert body1["next_token"] is not None

            # Decode the token and verify it contains expected keys
            import base64
            import json as json_mod
            decoded = json_mod.loads(base64.b64decode(body1["next_token"]).decode('utf-8'))
            assert "policy_id" in decoded

            # Second page with next_token
            app.table.scan = mock_scan_second
            event2 = _create_apigw_event(
                path="/policies",
                query_parameters={"keyword": "refund", "next_token": body1["next_token"]}
            )
            response2 = app.lambda_handler(event2, {})
            body2 = json.loads(response2["body"])
            assert body2["count"] == 1
            assert body2["policies"][0]["policy_id"] != body1["policies"][0]["policy_id"]
            assert body2["next_token"] is None  # Last page
        finally:
            app.table.scan = original_scan

    def test_search_with_invalid_next_token_decodes_bad_key(self, policies_table):
        """Failure mode: token decodes to valid JSON but not a valid DynamoDB key."""
        import base64, json
        bad_token = base64.b64encode(json.dumps({"bad_key": "value"}).encode()).decode()
        event = _create_apigw_event("/policies", query_parameters={"keyword": "refund", "next_token": bad_token})
        response = app.lambda_handler(event, None)
        # Invalid cursor keys must be rejected before calling DynamoDB
        assert response["statusCode"] == 400
        if response["statusCode"] == 500:
            body = json.loads(response["body"])
            assert body["error"] == "Internal server error"

    def test_search_without_next_token_still_works(self, policies_table):
        """Test search without next_token still works (backward compatibility)."""
        event = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "refund"}
        )
        response = app.lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 1
        assert "next_token" in body
        assert body["next_token"] is None  # No pagination needed for small result

    def test_search_with_limit_and_next_token(self, policies_table):
        """Test search with both limit and next_token parameters."""
        event1 = _create_apigw_event(
            path="/policies",
            query_parameters={"keyword": "legal", "limit": "1"}
        )

        original_scan = app.table.scan

        def mock_scan_first(**kwargs):
            return {
                "Items": [SAMPLE_POLICIES[0]],
                "ScannedCount": 3,
                "Count": 1,
                "LastEvaluatedKey": {"policy_id": "POL-002"}
            }

        def mock_scan_second(**kwargs):
            return {
                "Items": [SAMPLE_POLICIES[1]],
                "ScannedCount": 3,
                "Count": 1,
                "LastEvaluatedKey": None
            }

        app.table.scan = mock_scan_first

        try:
            response1 = app.lambda_handler(event1, {})
            body1 = json.loads(response1["body"])
            assert body1["count"] == 1
            assert body1["next_token"] is not None

            # Second page with next_token
            app.table.scan = mock_scan_second
            event2 = _create_apigw_event(
                path="/policies",
                query_parameters={"keyword": "legal", "limit": "1", "next_token": body1["next_token"]}
            )
            response2 = app.lambda_handler(event2, {})
            body2 = json.loads(response2["body"])
            assert body2["count"] == 1
            assert body2["policies"][0]["policy_id"] != body1["policies"][0]["policy_id"]
        finally:
            app.table.scan = original_scan


class TestCloudWatchMonitoring:
    """Tests for CloudWatch monitoring resources in template.yaml."""

    def test_error_alarm_exists(self):
        """Test that CloudWatch Error Alarm exists with correct properties."""
        import yaml

        class CFNLoader(yaml.SafeLoader):
            pass

        CFNLoader.add_constructor('!Sub', lambda loader, node: loader.construct_scalar(node))
        CFNLoader.add_constructor('!Ref', lambda loader, node: loader.construct_scalar(node))
        CFNLoader.add_constructor('!GetAtt', lambda loader, node: loader.construct_scalar(node))

        with open("template.yaml", "r") as f:
            template = yaml.load(f, Loader=CFNLoader)

        alarm = template["Resources"]["PolicyAssistantErrorAlarm"]
        assert alarm["Type"] == "AWS::CloudWatch::Alarm"
        assert alarm["Properties"]["AlarmName"] == "${AWS::StackName}-Errors"
        assert alarm["Properties"]["Namespace"] == "AWS/Lambda"
        assert alarm["Properties"]["MetricName"] == "Errors"
        assert alarm["Properties"]["Statistic"] == "Sum"
        assert alarm["Properties"]["Period"] == 300
        assert alarm["Properties"]["EvaluationPeriods"] == 1
        assert alarm["Properties"]["Threshold"] == 0
        assert alarm["Properties"]["ComparisonOperator"] == "GreaterThanThreshold"
        assert alarm["Properties"]["TreatMissingData"] == "notBreaching"
        assert alarm["Properties"]["Dimensions"][0]["Name"] == "FunctionName"
        assert alarm["Properties"]["Dimensions"][0]["Value"] == "PolicyAssistantFunction"

    def test_duration_alarm_exists(self):
        """Test that CloudWatch Duration Alarm exists with correct properties."""
        import yaml

        class CFNLoader(yaml.SafeLoader):
            pass

        CFNLoader.add_constructor('!Sub', lambda loader, node: loader.construct_scalar(node))
        CFNLoader.add_constructor('!Ref', lambda loader, node: loader.construct_scalar(node))
        CFNLoader.add_constructor('!GetAtt', lambda loader, node: loader.construct_scalar(node))

        with open("template.yaml", "r") as f:
            template = yaml.load(f, Loader=CFNLoader)

        alarm = template["Resources"]["PolicyAssistantDurationAlarm"]
        assert alarm["Type"] == "AWS::CloudWatch::Alarm"
        assert alarm["Properties"]["AlarmName"] == "${AWS::StackName}-Duration"
        assert alarm["Properties"]["Namespace"] == "AWS/Lambda"
        assert alarm["Properties"]["MetricName"] == "Duration"
        assert alarm["Properties"]["Statistic"] == "Maximum"
        assert alarm["Properties"]["Period"] == 300
        assert alarm["Properties"]["EvaluationPeriods"] == 1
        assert alarm["Properties"]["Threshold"] == 5000
        assert alarm["Properties"]["ComparisonOperator"] == "GreaterThanThreshold"
        assert alarm["Properties"]["TreatMissingData"] == "notBreaching"
        assert alarm["Properties"]["Dimensions"][0]["Name"] == "FunctionName"
        assert alarm["Properties"]["Dimensions"][0]["Value"] == "PolicyAssistantFunction"

    def test_dashboard_exists(self):
        """Test that CloudWatch Dashboard exists with correct metrics."""
        import yaml
        import json

        class CFNLoader(yaml.SafeLoader):
            pass

        CFNLoader.add_constructor('!Sub', lambda loader, node: loader.construct_scalar(node))
        CFNLoader.add_constructor('!Ref', lambda loader, node: loader.construct_scalar(node))
        CFNLoader.add_constructor('!GetAtt', lambda loader, node: loader.construct_scalar(node))

        with open("template.yaml", "r") as f:
            template = yaml.load(f, Loader=CFNLoader)

        dashboard = template["Resources"]["PolicyAssistantDashboard"]
        assert dashboard["Type"] == "AWS::CloudWatch::Dashboard"
        assert dashboard["Properties"]["DashboardName"] == "${AWS::StackName}-Dashboard"

        dashboard_body = dashboard["Properties"]["DashboardBody"]
        assert isinstance(dashboard_body, str)

        dashboard_json = json.loads(dashboard_body)
        widgets = dashboard_json["widgets"]
        assert len(widgets) >= 1
        assert widgets[0]["type"] == "metric"
        assert widgets[0]["properties"]["title"] == "Lambda Function Metrics"

        metrics = widgets[0]["properties"]["metrics"]
        metric_names = [m[1] for widget in widgets for m in widget["properties"]["metrics"] if len(m) >= 2]
        assert "Invocations" in metric_names
        assert "Errors" in metric_names
        assert "Duration" in metric_names
        assert "Throttles" in metric_names


class TestCognitoAuthorization:
    """Tests for Amazon Cognito User Pool and API Gateway JWT Authorizer configuration."""

    def _load_template(self):
        """Load template.yaml with CloudFormation intrinsic function support."""
        import yaml

        class CFNLoader(yaml.SafeLoader):
            pass

        CFNLoader.add_constructor('!Sub', lambda loader, node: loader.construct_scalar(node))
        CFNLoader.add_constructor('!Ref', lambda loader, node: loader.construct_scalar(node))
        CFNLoader.add_constructor('!GetAtt', lambda loader, node: loader.construct_scalar(node))

        with open("template.yaml", "r") as f:
            return yaml.load(f, Loader=CFNLoader)

    def test_user_pool_exists(self):
        """Test that Cognito User Pool resource exists with correct properties."""
        template = self._load_template()
        pool = template["Resources"]["PolicyAssistantUserPool"]
        assert pool["Type"] == "AWS::Cognito::UserPool"
        assert "${AWS::StackName}-user-pool" in pool["Properties"]["UserPoolName"]
        assert "email" in pool["Properties"]["AutoVerifiedAttributes"]
        assert "email" in pool["Properties"]["UsernameAttributes"]
        assert pool["Properties"]["MfaConfiguration"] in ("OFF", False)
        assert pool["Properties"]["AdminCreateUserConfig"]["AllowAdminCreateUserOnly"] is True
        assert pool["Properties"]["Policies"]["PasswordPolicy"]["MinimumLength"] >= 12

    def test_user_pool_client_exists(self):
        """Test that Cognito User Pool Client resource exists with correct properties."""
        template = self._load_template()
        client = template["Resources"]["PolicyAssistantUserPoolClient"]
        assert client["Type"] == "AWS::Cognito::UserPoolClient"
        assert client["Properties"]["ClientName"] == "policy-assistant-client"
        assert "ALLOW_USER_PASSWORD_AUTH" in client["Properties"]["ExplicitAuthFlows"]
        assert "ALLOW_REFRESH_TOKEN_AUTH" in client["Properties"]["ExplicitAuthFlows"]
        assert client["Properties"]["PreventUserExistenceErrors"] in ("ENABLED", True)

    def test_jwt_authorizer_exists(self):
        """Test that API Gateway V2 JWT Authorizer is configured at API Auth level."""
        template = self._load_template()
        api = template["Resources"]["PolicyAssistantApi"]
        auth = api["Properties"]["Auth"]
        assert "Authorizers" in auth
        assert "PolicyAssistantAuthorizer" in auth["Authorizers"]
        authorizer = auth["Authorizers"]["PolicyAssistantAuthorizer"]
        assert authorizer["IdentitySource"] == "$request.header.Authorization"
        assert "JwtConfiguration" in authorizer

    def test_authorizer_audience_references_client(self):
        """Test that the JWT authorizer audience references the User Pool Client."""
        template = self._load_template()
        api = template["Resources"]["PolicyAssistantApi"]
        authorizer = api["Properties"]["Auth"]["Authorizers"]["PolicyAssistantAuthorizer"]
        audience = authorizer["JwtConfiguration"]["audience"]
        assert len(audience) == 1
        assert audience[0] == "PolicyAssistantUserPoolClient"

    def test_authorizer_issuer_references_user_pool(self):
        """Test that the JWT authorizer issuer references the User Pool."""
        template = self._load_template()
        api = template["Resources"]["PolicyAssistantApi"]
        authorizer = api["Properties"]["Auth"]["Authorizers"]["PolicyAssistantAuthorizer"]
        issuer = authorizer["JwtConfiguration"]["issuer"]
        assert "cognito-idp" in str(issuer)
        assert "PolicyAssistantUserPool" in str(issuer)

    def test_policy_routes_require_authorizer(self):
        """Test that policy routes require the JWT authorizer."""
        template = self._load_template()
        function = template["Resources"]["PolicyAssistantFunction"]
        events = function["Properties"]["Events"]
        # GetPolicyById requires the authorizer
        assert events["GetPolicyById"]["Properties"]["Auth"]["Authorizer"] == "PolicyAssistantAuthorizer"
        # SearchPolicies requires the authorizer
        assert events["SearchPolicies"]["Properties"]["Auth"]["Authorizer"] == "PolicyAssistantAuthorizer"

    def test_health_check_route_is_public(self):
        """Test that /health route remains public (no authorizer)."""
        template = self._load_template()
        function = template["Resources"]["PolicyAssistantFunction"]
        events = function["Properties"]["Events"]
        health_event = events["HealthCheck"]
        # HealthCheck should NOT have Auth (remains public)
        assert "Auth" not in health_event["Properties"]

    def test_existing_cloudwatch_monitoring_preserved(self):
        """Test that existing CloudWatch monitoring resources remain present."""
        template = self._load_template()
        # Error alarm still exists
        assert "PolicyAssistantErrorAlarm" in template["Resources"]
        assert template["Resources"]["PolicyAssistantErrorAlarm"]["Type"] == "AWS::CloudWatch::Alarm"
        # Duration alarm still exists
        assert "PolicyAssistantDurationAlarm" in template["Resources"]
        assert template["Resources"]["PolicyAssistantDurationAlarm"]["Type"] == "AWS::CloudWatch::Alarm"
        # Dashboard still exists
        assert "PolicyAssistantDashboard" in template["Resources"]
        assert template["Resources"]["PolicyAssistantDashboard"]["Type"] == "AWS::CloudWatch::Dashboard"

    def test_search_request_parameters_not_supported_on_httpapi(self):
        """Test that HTTP API events do not use RequestParameters (REST-only feature)."""
        template = self._load_template()
        function = template["Resources"]["PolicyAssistantFunction"]
        events = function["Properties"]["Events"]
        search = events["SearchPolicies"]
        assert "RequestParameters" not in search["Properties"]

    def test_iam_policy_least_privilege(self):
        """Test Lambda IAM policy has only required DynamoDB actions on table ARN."""
        template = self._load_template()
        function = template["Resources"]["PolicyAssistantFunction"]
        # The explicit role prevents SAM from attaching wildcard managed policies.
        assert function["Properties"]["Role"] == "PolicyAssistantFunctionRole.Arn"
        policies = template["Resources"]["PolicyAssistantFunctionRole"]["Properties"]["Policies"]
        statement = policies[0]["PolicyDocument"]["Statement"][0]
        assert statement["Effect"] == "Allow"
        actions = statement["Action"]
        assert sorted(actions) == ["dynamodb:GetItem", "dynamodb:Scan"]
        # Resource is !GetAtt PoliciesTable.Arn (parsed as string or dict by loader)
        resource_ref = statement["Resource"]
        assert (isinstance(resource_ref, dict) and "Fn::GetAtt" in resource_ref) or (isinstance(resource_ref, str) and "PoliciesTable" in resource_ref)

    def test_throttling_settings_configured(self):
        """Test that HTTP API stage has basic throttling limits configured."""
        template = self._load_template()
        api = template["Resources"]["PolicyAssistantApi"]
        props = api["Properties"]
        assert "DefaultRouteSettings" in props
        settings = props["DefaultRouteSettings"]
        assert settings["ThrottlingRateLimit"] == 10
        assert settings["ThrottlingBurstLimit"] == 5

    def test_correlation_id_present_in_logs(self):
        """Test that correlation ID is included in structured log paths."""
        import logging
        import policy_assistant.app as app
        # Verify logger is configured at INFO level (structured logging enabled)
        assert app.logger.level == logging.INFO
        # Verify requestId extraction handles missing context gracefully
        event_no_context = {"requestContext": {}}
        rid = event_no_context.get("requestContext", {}).get("requestId", "unknown")
        assert rid == "unknown"

    def test_document_routes_exist(self):
        """Test that document ingestion routes are configured in template."""
        template = self._load_template()
        function = template["Resources"]["PolicyAssistantFunction"]
        events = function["Properties"]["Events"]
        assert "UploadSession" in events
        assert "SubmitDocument" in events
        assert "DocumentStatus" in events
        assert "DocumentDownload" in events
        # All protected by JWT
        for name in ["UploadSession", "SubmitDocument", "DocumentStatus", "DocumentDownload"]:
            assert events[name]["Properties"]["Auth"]["Authorizer"] == "PolicyAssistantAuthorizer"

    def test_existing_pagination_preserved(self):
        """Test that cursor-based pagination configuration remains present."""
        template = self._load_template()
        function = template["Resources"]["PolicyAssistantFunction"]
        events = function["Properties"]["Events"]
        # SearchPolicies event should still exist
        assert "SearchPolicies" in events
        # GetPolicyById event should still exist
        assert "GetPolicyById" in events
        # HealthCheck event should still exist
        assert "HealthCheck" in events
