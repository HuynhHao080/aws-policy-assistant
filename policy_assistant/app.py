import base64
import json
import os
import logging
import hashlib
import time
import re
from datetime import datetime, timezone
from uuid import uuid4
from boto3.dynamodb.conditions import Key
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

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
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s3():
    return boto3.client("s3", region_name=os.environ.get("AWS_REGION", "ap-southeast-1"),
                        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))


def _owner(event):
    """Trust only claims supplied by the API Gateway JWT authorizer."""
    context = event.get("requestContext") or {}
    claims = (((context.get("authorizer") or {}).get("jwt") or {}).get("claims") or {})
    owner = claims.get("sub")
    return owner if isinstance(owner, str) and owner else None


def _owned_document(doc_id, owner):
    item = document_table.get_item(Key={"doc_id": doc_id}, ConsistentRead=True).get("Item")
    return item if item and owner and item.get("owner_sub") == owner else None



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
            known_routes = {"/documents", "/policies", "/policies/", "/health", "/health/", "/documents/upload-session", "/documents/submit", "/documents/upload-session/", "/documents/submit/"}
            if remaining in known_routes or remaining.startswith("/policies/") or remaining.startswith("/documents/"):
                return remaining
    return path



def _mark_failed(item, code):
    """Never let an old delivery fail a newer attempt or a completed document."""
    try:
        document_table.update_item(
            Key={"doc_id": item["doc_id"]},
            UpdateExpression="SET #s = :failed, error_code = :code, failed_at = :now REMOVE dispatch_after",
            ConditionExpression="#s = :pending AND submission_id = :attempt",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":failed": "failed", ":pending": "pending", ":code": code,
                ":now": _now(), ":attempt": item["submission_id"]})
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise


def worker_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Isolate standard-queue failures; never acknowledge a failed record."""
    records = event.get("Records", [])
    if any(not isinstance(record.get("messageId"), str) or not record["messageId"] for record in records):
        raise ValueError("SQS records must contain messageId")
    failures = []
    for record in records:
        try:
            _process_document_record(record)
        except Exception as exc:
            # Never log payloads, signed URLs or raw SDK exception strings.
            logger.error("Worker record failed error_type=%s", type(exc).__name__)
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}


def _process_document_record(record):
    body = json.loads(record["body"])
    doc_id = body["doc_id"]
    item = document_table.get_item(Key={"doc_id": doc_id}, ConsistentRead=True).get("Item")
    if not item or not item.get("owner_sub") or not item.get("version_id"):
        raise ValueError("Document has no valid submission")
    if body.get("submission_id") != item.get("submission_id"):
        return  # stale message from an earlier attempt
    if item.get("status") == "processed":
        return
    if item.get("status") == "failed":
        if item.get("error_code") == "INVALID_PDF":
            return
        raise RuntimeError("Failed attempt must remain failed for DLQ redrive")
    if item.get("status") != "pending":
        raise ValueError("Document is not pending")
    try:
        obj = _s3().get_object(Bucket=os.environ["DOCUMENTS_BUCKET_NAME"],
            Key=item["s3_key"], VersionId=item["version_id"])
        try:
            data = obj["Body"].read(MAX_DOCUMENT_BYTES + 1)
        finally:
            obj["Body"].close()
        if not data.startswith(b"%PDF-") or len(data) > MAX_DOCUMENT_BYTES:
            _mark_failed(item, "INVALID_PDF")
            return  # permanent user input error; uploading a new PDF is required
        try:
            document_table.update_item(
                Key={"doc_id": doc_id},
                UpdateExpression="SET #s = :done, sha256 = :hash, processed_at = :time REMOVE dispatch_after, error_code, failed_at",
                ConditionExpression="#s = :pending AND submission_id = :attempt",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":done": "processed", ":pending": "pending",
                    ":attempt": item["submission_id"], ":hash": hashlib.sha256(data).hexdigest(), ":time": _now()})
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
    except Exception:
        if int(record.get("attributes", {}).get("ApproximateReceiveCount", "1")) >= 3:
            _mark_failed(item, "PROCESSING_FAILED")
        raise  # SQS retries and redrives the last failed delivery to DLQ
    logger.info("Document delivery completed")


def recovery_handler(event, context):
    """Re-enqueue due pending work, covering a crash between metadata and SQS.

    The sparse status/due-time index keeps each scheduled invocation bounded.
    Duplicate messages are safe; failed sends remain due for the next invocation.
    """
    due = document_table.query(IndexName="ByStatus",
        KeyConditionExpression=Key("status").eq("pending") & Key("dispatch_after").lte(int(time.time())),
        Limit=20).get("Items", [])
    queue = boto3.client("sqs", region_name=os.environ.get("AWS_REGION", "ap-southeast-1"))
    recovered = 0
    for item in due:
        queue.send_message(QueueUrl=os.environ["DOCUMENT_QUEUE_URL"], MessageBody=json.dumps({
            "doc_id": item["doc_id"], "submission_id": item["submission_id"]}))
        try:
            document_table.update_item(Key={"doc_id": item["doc_id"]},
                UpdateExpression="SET dispatch_after = :due",
                ConditionExpression="#s = :pending AND submission_id = :attempt",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":due": int(time.time()) + 120, ":pending": "pending",
                    ":attempt": item["submission_id"]})
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
        recovered += 1
    return {"recovered": recovered}


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
    logger.info("Request received requestId=%s", request_id)

    try:
        http_method = event.get("requestContext", {}).get("http", {}).get("method", "")
        # API Gateway HTTP API includes stage prefix in path (e.g., /Prod/policies/...)
        # Strip the stage prefix for routing
        raw_path = event.get("requestContext", {}).get("http", {}).get("path", "")
        path = _strip_stage_prefix(raw_path)
        path_parameters = event.get("pathParameters") or {}
        query_parameters = event.get("queryStringParameters") or {}

        request_id = event.get("requestContext", {}).get("requestId", "unknown")

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

        if (path == "/documents" or path.startswith("/documents/")) and not _owner(event):
            return _error_response(401, "Unauthorized", "A verified user identity is required")

        if path == "/documents" and http_method == "GET":
            return _document_list(_owner(event), query_parameters)

        # Route: POST /documents/upload-session
        if path == "/documents/upload-session" and http_method == "POST":
            return _document_upload_session(event, request_id, path_parameters, query_parameters)

        # Route: POST /documents/submit
        if path == "/documents/submit" and http_method == "POST":
            return _document_submit(event, request_id, path_parameters, query_parameters)

        # Route: GET /documents/{doc_id}/status
        if path.startswith("/documents/") and path != "/documents" and "doc_id" in path_parameters:
            doc_id = path_parameters["doc_id"]
            if not _valid_document_id(doc_id):
                return _error_response(400, "Bad request", "Invalid document ID")
            if path == f"/documents/{doc_id}/status":
                return _document_status(doc_id, request_id, _owner(event))
            if path == f"/documents/{doc_id}/download":
                return _document_download(doc_id, request_id, _owner(event))
            return _error_response(404, "Not found", "Invalid document endpoint")

        return _error_response(404, "Not found", "Invalid endpoint")

    except ClientError as e:
        request_id = event.get("requestContext", {}).get("requestId", "unknown")
        logger.error("AWS request failed requestId=%s error_type=%s", request_id, type(e).__name__)
        return _error_response(500, "Internal server error", "Database error occurred")
    except Exception as e:
        request_id = event.get("requestContext", {}).get("requestId", "unknown")
        logger.error("Request failed requestId=%s error_type=%s", request_id, type(e).__name__)
        return _error_response(500, "Internal server error", "An unexpected error occurred")


def _get_policy_by_id(policy_id: str, request_id: str = "unknown") -> Dict[str, Any]:
    """Retrieve a policy by its exact ID using GetItem."""
    if not isinstance(policy_id, str) or not policy_id.strip() or len(policy_id) > 256:
        return _error_response(400, "Bad request", "policy_id is required")

    try:
        response = table.get_item(Key={"policy_id": policy_id.strip()})
        item = response.get("Item")

        if not item:
            return _error_response(404, "Not found", f"Policy with ID '{policy_id}' not found")

        logger.info("Policy lookup succeeded requestId=%s", request_id)
        return _success_response(_strip_internal_fields(item))

    except ClientError as e:
        logger.error("Policy lookup failed requestId=%s error_type=%s", request_id, type(e).__name__)
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
    if not isinstance(keyword, str) or not keyword.strip() or len(keyword) > 256:
        return _error_response(400, "Bad request", "Query parameter 'keyword' is required")

    keyword_lower = keyword.strip().lower()
    logger.info("Policy search started requestId=%s", request_id)

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

        logger.info("Policy search finished count=%d scanned=%d truncated=%s requestId=%s", len(items), scanned_count, truncated, request_id)
        return _success_response({
            "policies": sanitized_items,
            "count": len(sanitized_items),
            "scanned_count": scanned_count,
            "truncated": truncated,
            "next_token": next_token_response
        })

    except ClientError as e:
        logger.error("Policy search failed requestId=%s error_type=%s", request_id, type(e).__name__)
        raise


def _json_body(event):
    raw = event.get("body")
    if raw is None or raw == "":
        return {}
    if not isinstance(raw, str) or len(raw) > 16384:
        raise ValueError("Invalid JSON body")
    try:
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw, validate=True).decode("utf-8")
        body = json.loads(raw)
    except (ValueError, UnicodeError, TypeError):
        raise ValueError("Invalid JSON body") from None
    if not isinstance(body, dict):
        raise ValueError("Expected a JSON object")
    return body


def _valid_document_id(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value) is not None


def _document_upload_session(event, request_id, path_params, query_params):
    """Create an owner-bound upload session; legacy unowned records stay private."""
    owner = _owner(event)
    if not owner:
        return _error_response(401, "Unauthorized", "A verified user identity is required")
    try:
        body = _json_body(event)
    except ValueError:
        return _error_response(400, "Bad request", "Expected a JSON object")
    if not isinstance(body, dict) or not isinstance(body.get("filename", "document.pdf"), str):
        return _error_response(400, "Bad request", "filename must be a string")
    filename = re.split(r"[\\/]", body.get("filename", "document.pdf"))[-1]
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)[:180] or "document.pdf"
    doc_id = "doc-" + uuid4().hex
    key = f"uploads/{doc_id}/document"
    post = _s3().generate_presigned_post(
        Bucket=os.environ["DOCUMENTS_BUCKET_NAME"], Key=key,
        Fields={"Content-Type": "application/pdf", "success_action_status": "201"},
        Conditions=[{"Content-Type": "application/pdf"}, {"success_action_status": "201"},
                    ["content-length-range", 5, MAX_DOCUMENT_BYTES]], ExpiresIn=300)
    document_table.put_item(Item={
        "doc_id": doc_id, "owner_sub": owner, "s3_key": key,
        "status": "uploading", "created_at": _now(), "filename": filename,
    }, ConditionExpression="attribute_not_exists(doc_id)")
    return _success_response({"doc_id": doc_id, "s3_key": key, "upload_url": post["url"],
                              "upload_method": "POST", "upload_fields": post["fields"],
                              "content_type": "application/pdf", "max_bytes": MAX_DOCUMENT_BYTES,
                              "expires_in": 300})


def _document_submit(event, request_id, path_params, query_params):
    """Freeze an uploaded version. Retrying pending submissions re-enqueues safely."""
    owner = _owner(event)
    if not owner:
        return _error_response(401, "Unauthorized", "A verified user identity is required")
    try:
        body = _json_body(event)
    except ValueError:
        return _error_response(400, "Bad request", "Expected a bounded JSON object")
    if not _valid_document_id(body.get("doc_id")):
        return _error_response(400, "Bad request", "A valid doc_id is required")
    doc_id = body["doc_id"]
    item = _owned_document(doc_id, owner)
    if not item:
        return _error_response(404, "Not found", "Document not found")
    if "s3_key" in body and body["s3_key"] != item["s3_key"]:
        return _error_response(400, "Bad request", "s3_key does not match the upload session")
    if item["status"] == "processed":
        return _success_response({"doc_id": doc_id, "status": "processed"})
    queue_url = os.environ.get("DOCUMENT_QUEUE_URL")
    if not queue_url:
        return _error_response(503, "Unavailable", "Document processing is unavailable")
    if item["status"] == "uploading":
        try:
            obj = _s3().head_object(Bucket=os.environ["DOCUMENTS_BUCKET_NAME"], Key=item["s3_key"])
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return _error_response(409, "Conflict", "Upload the PDF before submitting")
            if exc.response["Error"]["Code"] in ("403", "AccessDenied"):
                # Without ListBucket, S3 intentionally cannot distinguish a missing
                # key from denied access. Keep least privilege and the uploading state.
                logger.warning("Upload verification unavailable requestId=%s", request_id)
                return _error_response(503, "Unavailable", "Upload could not be verified; confirm it completed or contact the administrator")
            raise
        if obj.get("ContentType") != "application/pdf" or not 0 < obj.get("ContentLength", 0) <= MAX_DOCUMENT_BYTES:
            return _error_response(400, "Bad request", "Expected a PDF no larger than 10 MiB")
        version = obj.get("VersionId")
        if not version or version == "null":
            return _error_response(503, "Unavailable", "Document versioning must be enabled")
        try:
            document_table.update_item(
                Key={"doc_id": doc_id},
                UpdateExpression="SET #s = :pending, version_id = :version, submitted_at = :time, submission_id = :attempt, dispatch_after = :due",
                ConditionExpression="owner_sub = :owner AND #s = :uploading",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":pending": "pending", ":uploading": "uploading",
                    ":version": version, ":time": _now(), ":owner": owner, ":attempt": uuid4().hex, ":due": int(time.time()) + 120})
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return _error_response(409, "Conflict", "Submission changed; retry this request")
            raise
    elif item["status"] == "failed" and item.get("error_code") == "PROCESSING_FAILED":
        try:
            document_table.update_item(Key={"doc_id": doc_id},
                UpdateExpression="SET #s = :pending, submission_id = :new, dispatch_after = :due REMOVE error_code, failed_at",
                ConditionExpression="owner_sub = :owner AND #s = :failed AND submission_id = :old",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":pending": "pending", ":new": uuid4().hex,
                    ":due": int(time.time()) + 120, ":owner": owner, ":failed": "failed", ":old": item["submission_id"]})
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return _error_response(409, "Conflict", "Submission changed; retry this request")
            raise
    elif item["status"] != "pending":
        return _error_response(409, "Conflict", "Document cannot be submitted in its current state")
    item = _owned_document(doc_id, owner)
    try:
        boto3.client("sqs", region_name=os.environ.get("AWS_REGION", "ap-southeast-1")).send_message(
            QueueUrl=queue_url, MessageBody=json.dumps({"doc_id": doc_id, "submission_id": item["submission_id"]}))
    except ClientError:
        logger.warning("Enqueue failed doc_id=%s requestId=%s", doc_id, request_id)
        return _error_response(503, "Unavailable", "Queue unavailable; retry submitting this document")
    return _success_response({"doc_id": doc_id, "status": "pending"})


def _document_status(doc_id, request_id, owner):
    item = _owned_document(doc_id, owner)
    if not item:
        return _error_response(404, "Not found", "Document not found")
    return _success_response({key: item.get(key) for key in
        ("doc_id", "filename", "status", "created_at", "submitted_at", "processed_at", "sha256", "error_code", "failed_at")})


def _document_list(owner, params):
    try:
        limit = int(params.get("limit", "20"))
        if not 1 <= limit <= 50:
            raise ValueError()
        kwargs = {"IndexName": "ByOwner", "KeyConditionExpression": Key("owner_sub").eq(owner),
                  "ScanIndexForward": False, "Limit": limit}
        if params.get("next_token"):
            raw = params["next_token"]
            if len(raw) > 8192:
                raise ValueError()
            key = json.loads(base64.b64decode(raw, validate=True))
            if not isinstance(key, dict) or set(key) != {"doc_id", "owner_sub", "created_at"} or key["owner_sub"] != owner:
                raise ValueError()
            if not all(isinstance(value, str) and value for value in key.values()):
                raise ValueError()
            kwargs["ExclusiveStartKey"] = key
        response = document_table.query(**kwargs)
    except (ValueError, TypeError):
        return _error_response(400, "Bad request", "Invalid list limit or cursor")
    fields = ("doc_id", "filename", "status", "created_at", "submitted_at", "processed_at", "sha256", "error_code")
    return _success_response({"documents": [{k: item.get(k) for k in fields} for item in response.get("Items", [])],
        "next_token": _encode_next_token(response["LastEvaluatedKey"]) if response.get("LastEvaluatedKey") else None})


def _document_download(doc_id, request_id, owner):
    item = _owned_document(doc_id, owner)
    if not item:
        return _error_response(404, "Not found", "Document not found")
    if item.get("status") != "processed" or not item.get("version_id"):
        return _error_response(409, "Conflict", "Document is not processed yet")
    url = _s3().generate_presigned_url("get_object", Params={
        "Bucket": os.environ["DOCUMENTS_BUCKET_NAME"], "Key": item["s3_key"],
        "VersionId": item["version_id"], "ResponseContentType": "application/pdf",
        "ResponseContentDisposition": 'attachment; filename="policy-document.pdf"'}, ExpiresIn=300)
    return _success_response({"doc_id": doc_id, "download_url": url,
                              "sha256": item.get("sha256"), "expires_in": 300})


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
        if len(token) > 2048:
            raise ValueError("Cursor is too long")
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
