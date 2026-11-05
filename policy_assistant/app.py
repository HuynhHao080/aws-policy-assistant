import base64
import json
import os
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
try:
    from .policy_validity import active as policy_active
except ImportError:
    from policy_validity import active as policy_active

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB resource
# Boto3 automatically uses the Lambda runtime's region (AWS_REGION is set by Lambda)
dynamodb = boto3.resource("dynamodb")
table_name = os.environ.get("POLICIES_TABLE_NAME", "PolicyAssistantPolicies")
table = dynamodb.Table(table_name)
document_table_name = os.environ.get("DOCUMENT_METADATA_TABLE_NAME", "PolicyAssistantDocumentMetadata")
document_table = dynamodb.Table(document_table_name)

# Per-request scan budget: maximum number of items DynamoDB may evaluate
# across all Scan pages for a single keyword search request. This bounds
# read capacity consumption per request. The limit query parameter caps
# returned items but does not bound scanned items.
MAX_SCAN_ITEMS = 1000



def _strip_stage_prefix(path: str) -> str:
    """Remove API Gateway stage prefix from path (e.g., /Prod/policies -> /policies).

    Only strips known stage names (Prod, prod, Dev, dev, Test, test, Stage, stage)
    when the remaining path matches a known route pattern.
    """
    if not path:
        return path
    parts = path.split("/")
    if len(parts) >= 3 and parts[0] == "" and parts[1]:
        stage_names = {"prod", "dev", "test", "stage", "staging", "qa", "uat"}
        if parts[1].lower() in stage_names:
            remaining = "/" + "/".join(parts[2:])
            # Only strip if the remaining path matches a known route
            known_routes = {"/policies", "/policies/", "/health", "/health/", "/documents/upload-session", "/documents/submit", "/documents/upload-session/", "/documents/submit/"}
            if remaining in known_routes or remaining in ("/documents", "/ask", "/me", "/account/delete", "/conversations", "/tickets", "/shop") or remaining.startswith(("/policies/", "/documents/", "/admin/", "/conversations/", "/tickets/")):
                return remaining
    return path



def _service():
    try:
        from .service import Service
    except ImportError:
        from service import Service
    return Service(document_table, table)


def worker_handler(event, context):
    try:
        from .pipeline import batch
    except ImportError:
        from pipeline import batch
    return batch(_service(), event)


def dispatch_handler(event, context):
    try:
        from .pipeline import dispatch
    except ImportError:
        from pipeline import dispatch
    return dispatch(_service(), event)


def maintenance_handler(event, context):
    try:
        from .pipeline import recover
    except ImportError:
        from pipeline import recover
    return recover(_service(), event)



def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Policy Assistant API.

    Handles two endpoints:
    - GET /policies/{policy_id} - Retrieve a policy by exact ID
    - GET /policies?keyword=xxx - Case-insensitive keyword search

    Parameters
    ----------
    event: dict
        API Gateway HTTP API v2 event format
    context: object
        Lambda Context

    Returns
    -------
    dict
        API Gateway HTTP API v2 response format
    """
    request_id = event.get("requestContext", {}).get("requestId", "unknown")
    logger.info("Request received method=%s path=%s requestId=%s", event.get("requestContext", {}).get("http", {}).get("method", ""), event.get("requestContext", {}).get("http", {}).get("path", ""), request_id)

    try:
        http_method = event.get("requestContext", {}).get("http", {}).get("method", "")
        # API Gateway HTTP API includes stage prefix in path (e.g., /Prod/policies/...)
        # Strip the stage prefix for routing
        raw_path = event.get("requestContext", {}).get("http", {}).get("path", "")
        path = _strip_stage_prefix(raw_path)
        path_parameters = event.get("pathParameters") or {}
        query_parameters = event.get("queryStringParameters") or {}
        claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
        owner_id = claims.get("sub")
        application_route = path in ("/documents", "/ask", "/me", "/account/delete", "/conversations", "/tickets", "/shop") or path.startswith(("/documents/", "/admin/", "/conversations/", "/tickets/"))
        if application_route:
            if not isinstance(owner_id, str) or not owner_id:
                return _error_response(401, "Unauthorized", "A verified user identity is required")
            try:
                from .service import Problem
            except ImportError:
                from service import Problem
            try:
                return _success_response(_service().handle(event, http_method, path, owner_id, claims))
            except Problem as exc:
                return _error_response(exc.status, {400: "Bad request", 401: "Unauthorized", 403: "Forbidden", 404: "Not found", 405: "Method not allowed", 409: "Conflict", 429: "Usage limit reached", 502: "Bad gateway", 503: "Service unavailable"}.get(exc.status, "Request failed"), exc.message)
            except ClientError as exc:
                if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                    return _error_response(409, "Conflict", "Document state changed; refresh before retrying")
                logger.exception("Application backend error requestId=%s", request_id)
                return _error_response(503, "Service unavailable", "Backend temporarily unavailable; retry later")

        request_id = event.get("requestContext", {}).get("requestId", "unknown")
        logger.info("Method: %s, RawPath: %s, Path: %s, PathParams: %s, QueryParams: %s requestId=%s",
                    http_method, raw_path, path, path_parameters, query_parameters, request_id)

        if http_method not in ("GET", "POST") or (http_method == "POST" and path not in ("/documents/upload-session", "/documents/submit")):
            return _error_response(405, "Method not allowed", "Only GET and POST methods are supported")

        if path.startswith("/policies") and os.environ.get("USAGE_TABLE_NAME"):
            if not isinstance(owner_id, str) or not owner_id:
                return _error_response(401, "Unauthorized", "A verified user identity is required")
            service = _service()
            account = service.table("USAGE_TABLE_NAME").get_item(Key={"pk": f"account#{owner_id}"}, ConsistentRead=True).get("Item", {})
            if account.get("state") == "deleting":
                return _error_response(410, "Account unavailable", "Account deletion is in progress")
            try:
                service.quota(owner_id, "request")
            except Exception as exc:
                if getattr(exc, "status", None) == 429:
                    return _error_response(429, "Usage limit reached", exc.message)
                raise

        # Route: GET /policies/{policy_id}
        if path.startswith("/policies/") and path != "/policies" and "policy_id" in path_parameters:
            policy_id = path_parameters["policy_id"]
            return _get_policy_by_id(policy_id, request_id)

        # Route: GET /policies?keyword=xxx
        if path == "/policies" or path == "/policies/":
            keyword = query_parameters.get("keyword")
            return _search_policies(keyword, query_parameters, request_id)

        # Route: GET /health
        # Lightweight liveness check: verifies the Lambda handler is reachable.
        # Does NOT verify DynamoDB connectivity or any downstream dependency.
        if path == "/health" or path == "/health/":
            return _success_response({"status": "healthy"})

        return _error_response(404, "Not found", "Invalid endpoint")

    except ClientError as e:
        request_id = event.get("requestContext", {}).get("requestId", "unknown")
        logger.error("DynamoDB ClientError: %s requestId=%s", e, request_id, exc_info=True)
        return _error_response(500, "Internal server error", "Database error occurred")
    except Exception as e:
        request_id = event.get("requestContext", {}).get("requestId", "unknown")
        logger.error("Unexpected error: %s requestId=%s", e, request_id, exc_info=True)
        return _error_response(500, "Internal server error", "An unexpected error occurred")


def _get_policy_by_id(policy_id: str, request_id: str = "unknown") -> Dict[str, Any]:
    """Retrieve a policy by its exact ID using GetItem."""
    if not policy_id or not policy_id.strip():
        return _error_response(400, "Bad request", "policy_id is required")

    try:
        response = table.get_item(Key={"policy_id": policy_id.strip()}, ConsistentRead=True)
        item = response.get("Item")

        if not item or not policy_active(item) or (os.environ.get("REQUIRE_PUBLISHED_POLICIES") == "true" and item.get("publication_state") != "published"):
            return _error_response(404, "Not found", f"Policy with ID '{policy_id}' not found")

        logger.info("Policy found: %s requestId=%s", policy_id, request_id)
        return _success_response(_strip_internal_fields(item))

    except ClientError as e:
        logger.error("GetItem error for policy_id=%s: %s requestId=%s", policy_id, e, request_id)
        raise


def _search_policies(keyword: Optional[str], query_parameters: Optional[Dict[str, str]] = None, request_id: str = "unknown") -> Dict[str, Any]:
    """Search policies by keyword across title, category, content, and keywords (case-insensitive).

    Uses pre-computed lowercase fields (title_lower, category_lower, content_lower, keywords_lower)
    for efficient case-insensitive matching with DynamoDB's contains function.

    Each request is bounded by MAX_SCAN_ITEMS: DynamoDB's Scan Limit parameter
    is passed on every page, and scanning stops when the cumulative ScannedCount
    reaches the budget. When the budget is exhausted before enough matches are
    found, the response includes "truncated": true to indicate results may be
    incomplete.
    """
    if not keyword or not keyword.strip():
        return _error_response(400, "Bad request", "Query parameter 'keyword' is required")

    keyword_lower = keyword.strip().lower()
    logger.info("Searching policies with keyword: %s requestId=%s", keyword_lower, request_id)

    # Parse optional limit parameter
    limit = None
    if query_parameters:
        limit_raw = query_parameters.get("limit")
        if limit_raw is not None:
            try:
                limit = int(limit_raw)
                if limit <= 0:
                    return _error_response(400, "Bad request", "Query parameter 'limit' must be a positive integer")
                if limit > 100:
                    return _error_response(400, "Bad request", "Query parameter 'limit' must not exceed 100")
            except (ValueError, TypeError):
                return _error_response(400, "Bad request", "Query parameter 'limit' must be a valid integer")

    # Parse optional next_token parameter for cursor-based pagination
    next_token = None
    if query_parameters:
        next_token_raw = query_parameters.get("next_token")
        if next_token_raw is not None:
            try:
                next_token = _decode_next_token(next_token_raw)
            except ValueError:
                return _error_response(400, "Bad request", "Invalid next_token")

    try:
        # Use Scan with FilterExpression on lowercase fields for case-insensitive search
        # Note: Scan reads entire table - suitable for small MVP dataset only
        # For production, consider GSI or OpenSearch
        filter_expression = (
            "contains(#title, :kw) OR contains(#category, :kw) OR "
            "contains(#content, :kw) OR contains(#keywords, :kw)"
        )
        expression_attribute_names = {
            "#title": "title_lower",
            "#category": "category_lower",
            "#content": "content_lower",
            "#keywords": "keywords_lower"
        }
        expression_attribute_values = {
            ":kw": keyword_lower
        }
        if os.environ.get("REQUIRE_PUBLISHED_POLICIES") == "true":
            filter_expression = f"({filter_expression}) AND #publication = :published"
            expression_attribute_names["#publication"] = "publication_state"
            expression_attribute_values[":published"] = "published"

        items: List[Dict[str, Any]] = []
        last_evaluated_key = next_token
        scanned_count = 0
        truncated = False

        # Handle pagination - Scan returns max 1MB per request
        while True:
            # Compute remaining scan budget for this page
            remaining_budget = MAX_SCAN_ITEMS - scanned_count
            if remaining_budget <= 0:
                truncated = True
                break

            scan_kwargs = {
                "FilterExpression": filter_expression,
                "ExpressionAttributeNames": expression_attribute_names,
                "ExpressionAttributeValues": expression_attribute_values,
                # Pass DynamoDB's Limit parameter to bound items evaluated per page
                "Limit": min(remaining_budget, limit - len(items) if limit is not None else 1000),
            }
            if last_evaluated_key:
                scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = table.scan(**scan_kwargs)
            scanned_count += response.get("ScannedCount", 0)
            items.extend(item for item in response.get("Items", []) if policy_active(item))
            last_evaluated_key = response.get("LastEvaluatedKey")

            # Stop if we've reached the requested limit
            if limit is not None and len(items) >= limit:
                items = items[:limit]
                break

            # Stop if scan budget exhausted
            if scanned_count >= MAX_SCAN_ITEMS:
                # Only mark truncated if more items may remain unprocessed
                if last_evaluated_key:
                    truncated = True
                break

            # Stop if no more pages
            if not last_evaluated_key:
                break

        # Strip internal lowercase fields from client-facing responses
        sanitized_items = [_strip_internal_fields(item) for item in items]

        # Encode LastEvaluatedKey as next_token for pagination
        next_token_response = None
        if last_evaluated_key:
            next_token_raw = json.dumps(last_evaluated_key, separators=(',', ':'))
            next_token_response = base64.b64encode(next_token_raw.encode('utf-8')).decode('utf-8')

        logger.info("Found %d policies matching keyword: %s (scanned: %d, truncated: %s) requestId=%s", len(items), keyword_lower, scanned_count, truncated, request_id)
        return _success_response({
            "policies": sanitized_items,
            "count": len(sanitized_items),
            "scanned_count": scanned_count,
            "truncated": truncated,
            "next_token": next_token_response
        })

    except ClientError as e:
        logger.error("Scan error for keyword=%s: %s requestId=%s", keyword_lower, e, request_id)
        raise


def _success_response(body: Any) -> Dict[str, Any]:
    """Create a successful HTTP response."""
    return {
        "statusCode": 200,
        "headers": _cors_headers(),
        "body": json.dumps(body, default=lambda value: int(value) if isinstance(value, Decimal) and value == value.to_integral_value() else float(value) if isinstance(value, Decimal) else str(value))
    }


def _strip_internal_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    """Remove internal lowercase fields from a policy item before returning to client."""
    internal_fields = {
        "title_lower", "category_lower", "content_lower", "keywords_lower", "search_chunks", "embedding_model", "updated_by", "draft_data", "revision", "published_by", "edited_at"
    }
    return {k: v for k, v in item.items() if k not in internal_fields}


def _decode_next_token(token: str) -> Dict[str, Any]:
    """Decode a base64-encoded next_token into a DynamoDB key dict.

    Args:
        token: Base64-encoded JSON string of LastEvaluatedKey.

    Returns:
        Dict representing the DynamoDB key to use as ExclusiveStartKey.

    Raises:
        ValueError: If the token is invalid base64 or invalid JSON.
    """
    try:
        if not isinstance(token, str) or len(token) > 2048:
            raise ValueError("Invalid cursor size")
        decoded = base64.b64decode(token.encode('utf-8'), validate=True).decode('utf-8')
        key = json.loads(decoded)
        if not isinstance(key, dict) or set(key) != {"policy_id"} or not isinstance(key["policy_id"], str) or not key["policy_id"]:
            raise ValueError("Invalid cursor key")
        return key
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid next_token: {e}")


def _encode_next_token(last_evaluated_key: Dict[str, Any]) -> str:
    """Encode LastEvaluatedKey as a base64-encoded next_token.

    Args:
        last_evaluated_key: DynamoDB LastEvaluatedKey dict.

    Returns:
        Base64-encoded JSON string suitable for use as next_token query parameter.
    """
    token_raw = json.dumps(last_evaluated_key, separators=(',', ':'))
    return base64.b64encode(token_raw.encode('utf-8')).decode('utf-8')


def _cors_headers() -> Dict[str, str]:
    """Return CORS headers for API responses."""
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "http://localhost:8080",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    }


def _error_response(status_code: int, error: str, message: str) -> Dict[str, Any]:
    """Create an error HTTP response."""
    return {
        "statusCode": status_code,
        "headers": _cors_headers(),
        "body": json.dumps({
            "error": error,
            "message": message
        })
    }
