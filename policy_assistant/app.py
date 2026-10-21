import base64
import json
import os
import logging
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

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
            if remaining in known_routes or remaining.startswith("/policies/") or remaining.startswith("/documents/"):
                return remaining
    return path



def worker_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Worker Lambda: process submitted document metadata."""
    logger.info("Worker received %d records requestId=%s", len(event.get("Records", [])), event.get("requestContext", {}).get("requestId", "unknown"))
    # Minimal processing: update DynamoDB status to "processed" (metadata only; no PDF extraction)
    for record in event.get("Records", []):
        try:
            body = json.loads(record.get("body", "{}"))
            doc_id = body.get("doc_id")
            if doc_id:
                document_table.update_item(
                    Key={"doc_id": doc_id},
                    UpdateExpression="SET #s = :status",
                    ExpressionAttributeNames={"#s": "status"},
                    ExpressionAttributeValues={":status": "processed"},
                )
                logger.info("Processed doc %s requestId=%s", doc_id, event.get("requestContext", {}).get("requestId", "unknown"))
        except Exception as e:
            logger.error("Worker error processing record: %s requestId=%s", e, event.get("requestContext", {}).get("requestId", "unknown"), exc_info=True)
    return {"statusCode": 200, "body": json.dumps({"processed": True})}


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

        request_id = event.get("requestContext", {}).get("requestId", "unknown")
        logger.info("Method: %s, RawPath: %s, Path: %s, PathParams: %s, QueryParams: %s requestId=%s",
                    http_method, raw_path, path, path_parameters, query_parameters, request_id)

        if http_method not in ("GET", "POST") or (http_method == "POST" and path not in ("/documents/upload-session", "/documents/submit")):
            return _error_response(405, "Method not allowed", "Only GET and POST methods are supported")

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

        # Route: POST /documents/upload-session
        if path == "/documents/upload-session" and http_method == "POST":
            return _document_upload_session(event, request_id, path_parameters, query_parameters)

        # Route: POST /documents/submit
        if path == "/documents/submit" and http_method == "POST":
            return _document_submit(event, request_id, path_parameters, query_parameters)

        # Route: GET /documents/{doc_id}/status
        if path.startswith("/documents/") and path != "/documents" and "doc_id" in path_parameters:
            doc_id = path_parameters["doc_id"]
            if "/status" in path:
                return _document_status(doc_id, request_id)
            if "/download" in path:
                return _document_download(doc_id, request_id)
            return _error_response(404, "Not found", "Invalid document endpoint")

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
        response = table.get_item(Key={"policy_id": policy_id.strip()})
        item = response.get("Item")

        if not item:
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
            except ValueError as e:
                return _error_response(400, "Bad request", str(next_token_raw))

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

        items: List[Dict[str, Any]] = []
        last_evaluated_key = None
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
                "Limit": min(remaining_budget, 1000),
            }
            if last_evaluated_key:
                scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = table.scan(**scan_kwargs)
            scanned_count += response.get("ScannedCount", 0)
            items.extend(response.get("Items", []))
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


def _document_upload_session(event: Dict[str, Any], request_id: str, path_params: Dict, query_params: Dict) -> Dict[str, Any]:
    """Generate a presigned S3 upload URL for document ingestion."""
    try:
        s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "ap-southeast-1"))
        bucket = os.environ.get("DOCUMENTS_BUCKET_NAME", "PolicyAssistantDocuments")
        doc_id = f"doc-{request_id[:8]}-{os.urandom(4).hex()}"
        key = f"uploads/{doc_id}/document"
        url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket, "Key": key, "ContentType": "application/pdf"},
            ExpiresIn=300,
        )
        logger.info("Upload session created doc_id=%s requestId=%s", doc_id, request_id)
        return _success_response({"doc_id": doc_id, "upload_url": url, "expires_in": 300})
    except Exception as e:
        logger.error("Upload session error requestId=%s: %s", request_id, e, exc_info=True)
        return _error_response(500, "Internal server error", "Failed to create upload session")


def _document_submit(event: Dict[str, Any], request_id: str, path_params: Dict, query_params: Dict) -> Dict[str, Any]:
    """Submit document metadata for async processing."""
    try:
        body = json.loads(event.get("body") or "{}")
        doc_id = body.get("doc_id")
        s3_key = body.get("s3_key")
        if not doc_id or not s3_key:
            return _error_response(400, "Bad request", "doc_id and s3_key are required")
        # Write metadata to DynamoDB (schemaless; uses policy_id as doc key for simplicity)
        document_table.put_item(Item={
            "doc_id": doc_id,
            "status": "pending",
            "s3_key": s3_key,
            "submitted_at": str(os.environ.get("AWS_REGION", "ap-southeast-1")),
        })
        # Send SQS message for worker
        sqs = boto3.client("sqs", region_name=os.environ.get("AWS_REGION", "ap-southeast-1"))
        queue_url = os.environ.get("DOCUMENT_QUEUE_URL", "")
        if queue_url:
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps({"doc_id": doc_id, "s3_key": s3_key}),
            )
        logger.info("Document submitted doc_id=%s requestId=%s", doc_id, request_id)
        return _success_response({"doc_id": doc_id, "status": "pending"})
    except Exception as e:
        logger.error("Submit error requestId=%s: %s", request_id, e, exc_info=True)
        return _error_response(500, "Internal server error", "Failed to submit document")


def _document_status(doc_id: str, request_id: str) -> Dict[str, Any]:
    """Retrieve document processing status from DynamoDB."""
    try:
        response = document_table.get_item(Key={"doc_id": doc_id})
        item = response.get("Item")
        if not item:
            return _error_response(404, "Not found", f"Document '{doc_id}' not found")
        logger.info("Document status doc_id=%s requestId=%s", doc_id, request_id)
        return _success_response({
            "doc_id": doc_id,
            "status": item.get("status", "unknown"),
            "s3_key": item.get("s3_key"),
            "submitted_at": item.get("submitted_at"),
        })
    except ClientError as e:
        logger.error("Status error doc_id=%s requestId=%s: %s", doc_id, request_id, e, exc_info=True)
        return _error_response(500, "Internal server error", "Failed to retrieve status")


def _document_download(doc_id: str, request_id: str) -> Dict[str, Any]:
    """Generate a presigned download URL for a submitted document."""
    try:
        response = document_table.get_item(Key={"doc_id": doc_id})
        item = response.get("Item")
        if not item:
            return _error_response(404, "Not found", f"Document '{doc_id}' not found")
        s3_key = item.get("s3_key")
        if not s3_key:
            return _error_response(404, "Not found", "Document has no stored file")
        s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "ap-southeast-1"))
        bucket = os.environ.get("DOCUMENTS_BUCKET_NAME", "PolicyAssistantDocuments")
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": s3_key},
            ExpiresIn=300,
        )
        logger.info("Download URL generated doc_id=%s requestId=%s", doc_id, request_id)
        return _success_response({"doc_id": doc_id, "download_url": url, "expires_in": 300})
    except ClientError as e:
        logger.error("Download error doc_id=%s requestId=%s: %s", doc_id, request_id, e, exc_info=True)
        return _error_response(500, "Internal server error", "Failed to generate download URL")


def _success_response(body: Any) -> Dict[str, Any]:
    """Create a successful HTTP response."""
    return {
        "statusCode": 200,
        "headers": _cors_headers(),
        "body": json.dumps(body, default=str)
    }


def _strip_internal_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    """Remove internal lowercase fields from a policy item before returning to client."""
    internal_fields = {
        "title_lower", "category_lower", "content_lower", "keywords_lower"
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
        decoded = base64.b64decode(token.encode('utf-8')).decode('utf-8')
        return json.loads(decoded)
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
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
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