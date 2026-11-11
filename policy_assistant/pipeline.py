"""Durable dispatch, bounded PDF extraction, deletion and stuck-job recovery."""
import io
import json
import logging
import time
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

try:
    from .service import MAX_BYTES, Problem, now
except ImportError:
    from service import MAX_BYTES, Problem, now

log = logging.getLogger(__name__)


def extract(raw):
    if not raw.startswith(b"%PDF-"):
        raise Problem(422, "invalid_pdf")
    try:
        reader = PdfReader(io.BytesIO(raw), strict=False)
        if reader.is_encrypted:
            raise Problem(422, "encrypted_pdf")
        if not 1 <= len(reader.pages) <= 100:
            raise Problem(422, "pdf_page_limit")
        chunks = []
        total = 0
        for number, page in enumerate(reader.pages, 1):
            # Do not execute PDF scripts, embedded files, annotations or links.
            if page.get("/AA") or page.get("/JS"):
                raise Problem(422, "active_pdf_content")
            content = (page.extract_text() or "").replace("\x00", "").strip()
            total += len(content)
            if total > 300_000:
                raise Problem(422, "pdf_text_limit")
            for start in range(0, len(content), 1200):
                fragment = content[start:start + 1400].strip()
                if fragment:
                    chunks.append({"page": number, "text": fragment})
        return {"pages": len(reader.pages), "chunks": chunks}
    except (PdfReadError, ValueError, KeyError, TypeError, RecursionError):
        raise Problem(422, "invalid_pdf") from None


def parse_document(service, doc, raw):
    import os
    function = os.environ.get("PDF_PARSER_FUNCTION_NAME")
    if not function:
        # Offline tests use the identical pure parsing function without AWS Lambda.
        if os.environ.get("ALLOW_LOCAL_PDF_PARSER") != "true":
            raise RuntimeError("Isolated PDF parser is not configured")
        return extract(raw)
    url = service.client("s3").generate_presigned_url("get_object", Params={"Bucket": service.bucket, "Key": doc["s3_key"], "VersionId": doc["s3_version"]}, ExpiresIn=120)
    response = service.client("lambda").invoke(FunctionName=function, InvocationType="RequestResponse", Payload=json.dumps({"doc_id": doc["doc_id"], "source_url": url}).encode())
    try:
        payload = json.loads(response["Payload"].read())
    finally:
        response["Payload"].close()
    if response.get("FunctionError") or not isinstance(payload, dict) or payload.get("retry"):
        raise RuntimeError("PDF parser temporarily unavailable")
    allowed_errors = {"invalid_pdf", "encrypted_pdf", "pdf_page_limit", "active_pdf_content", "pdf_text_limit", "pdf_size_limit"}
    if payload.get("error_code") in allowed_errors:
        raise Problem(422, payload["error_code"])
    if type(payload.get("pages")) is not int or not 1 <= payload["pages"] <= 100 or not isinstance(payload.get("chunks"), list) or len(payload["chunks"]) > 500:
        raise RuntimeError("Invalid PDF parser response")
    chunks = []
    for chunk in payload["chunks"]:
        if not isinstance(chunk, dict) or type(chunk.get("page")) is not int or not 1 <= chunk["page"] <= payload["pages"] or not isinstance(chunk.get("text"), str) or len(chunk["text"]) > 1400:
            raise RuntimeError("Invalid PDF parser chunk")
        chunks.append({"page": chunk["page"], "text": chunk["text"]})
    if sum(len(c["text"]) for c in chunks) > 400000:
        raise RuntimeError("PDF parser response exceeded text bound")
    return {"pages": payload["pages"], "chunks": chunks}


def ocr_result(service, job_id):
    args = {"JobId": job_id, "MaxResults": 1000}
    pages = {}
    total = 0
    while True:
        result = service.client("textract").get_document_text_detection(**args)
        if result["JobStatus"] == "IN_PROGRESS":
            return None
        if result["JobStatus"] != "SUCCEEDED":
            raise Problem(422, "ocr_failed")
        for block in result.get("Blocks", []):
            if block.get("BlockType") == "LINE":
                value = block.get("Text", "")
                total += len(value)
                if total > 300_000:
                    raise Problem(422, "pdf_text_limit")
                pages.setdefault(int(block.get("Page", 1)), []).append(value)
        if not result.get("NextToken"):
            break
        args["NextToken"] = result["NextToken"]
    chunks = []
    for number, lines in sorted(pages.items()):
        value = "\n".join(lines)
        chunks.extend({"page": number, "text": value[start:start + 1400]} for start in range(0, len(value), 1200))
    if not chunks:
        raise Problem(422, "ocr_no_text")
    return {"pages": int(result.get("DocumentMetadata", {}).get("Pages", len(pages))), "chunks": chunks, "extraction_method": "textract"}


def dispatch(service, event):
    failures = []
    decode = TypeDeserializer().deserialize
    for record in event.get("Records", []):
        sequence = record.get("dynamodb", {}).get("SequenceNumber")
        try:
            if record.get("eventName") not in ("INSERT", "MODIFY"):
                continue
            new = {k: decode(v) for k, v in record["dynamodb"].get("NewImage", {}).items()}
            old = {k: decode(v) for k, v in record["dynamodb"].get("OldImage", {}).items()}
            if new.get("status") not in ("pending", "ocr_pending", "deleting") or not new.get("dispatch_id") or old.get("dispatch_id") == new["dispatch_id"]:
                continue
            import os
            queue = os.environ.get("DOCUMENT_QUEUE_URL")
            if not queue:
                raise RuntimeError("Queue not configured")
            service.client("sqs").send_message(QueueUrl=queue, MessageBody=json.dumps({"doc_id": new["doc_id"]}), DelaySeconds=60 if new.get("record_type") == "account_deletion" else 0)
        except Exception:
            log.exception("Dispatch failed sequence=%s", sequence)
            if not sequence:
                raise
            failures.append({"itemIdentifier": sequence})
    return {"batchItemFailures": failures}


def purge_files(service, doc_id):
    s3 = service.client("s3")
    for prefix in (f"quarantine/{doc_id}/", f"uploads/{doc_id}/", f"documents/{doc_id}/"):
        for page in s3.get_paginator("list_object_versions").paginate(Bucket=service.bucket, Prefix=prefix):
            objects = [{"Key": entry["Key"], "VersionId": entry["VersionId"]} for field in ("Versions", "DeleteMarkers") for entry in page.get(field, [])]
            for start in range(0, len(objects), 1000):
                result = s3.delete_objects(Bucket=service.bucket, Delete={"Objects": objects[start:start + 1000], "Quiet": True})
                if result.get("Errors"):
                    raise RuntimeError("Some object versions could not be deleted")


def process(service, doc_id):
    doc = service.docs.get_item(Key={"doc_id": doc_id}, ConsistentRead=True).get("Item")
    if not doc:
        raise ValueError("Document does not exist")
    if doc["status"] in ("processed", "failed", "deleted"):
        return
    if doc.get("record_type") == "account_deletion":
        delete_account(service, doc)
        return
    if doc["status"] == "deleting":
        purge_files(service, doc_id)
        service.docs.update_item(Key={"doc_id": doc_id}, UpdateExpression="SET #s=:deleted, updated_at=:now, expires_at=:ttl REMOVE s3_key, s3_version, source_key, source_version, extraction_key, extraction_version, filename, title, error_code", ConditionExpression="#s=:deleting", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":deleted": "deleted", ":deleting": "deleting", ":now": now(), ":ttl": int(time.time()) + 30 * 86400})
        return
    account = service.table("USAGE_TABLE_NAME").get_item(Key={"pk": f"account#{doc['owner_id']}"}, ConsistentRead=True).get("Item", {})
    if account.get("state") == "deleting":
        service.docs.update_item(Key={"doc_id": doc_id}, UpdateExpression="SET #s=:deleting", ConditionExpression="#s=:pending", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":deleting": "deleting", ":pending": "pending"})
        process(service, doc_id)
        return
    job = uuid4().hex
    clock = int(time.time())
    try:
        service.docs.update_item(Key={"doc_id": doc_id}, UpdateExpression="SET #s=:processing, lease_until=:lease, job_id=:job, updated_at=:now ADD attempts :one", ConditionExpression="#s=:pending OR #s=:ocr OR (#s=:processing AND lease_until < :clock)", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":processing": "processing", ":pending": "pending", ":ocr": "ocr_pending", ":lease": clock + 150, ":clock": clock, ":job": job, ":now": now(), ":one": 1})
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise RuntimeError("Document is not ready or another worker holds its lease") from None
        raise
    try:
        if not doc.get("s3_version") or doc.get("s3_key") != f"quarantine/{doc_id}/document":
            raise Problem(422, "invalid_upload_session")
        s3 = service.client("s3")
        original = s3.get_object(Bucket=service.bucket, Key=doc["s3_key"], VersionId=doc["s3_version"])
        try:
            raw = original["Body"].read(MAX_BYTES + 1)
        finally:
            original["Body"].close()
        if not 0 < len(raw) <= MAX_BYTES:
            raise Problem(422, "pdf_size_limit")
        if doc.get("textract_job_id"):
            parsed = ocr_result(service, doc["textract_job_id"])
            if parsed is None:
                service.docs.update_item(Key={"doc_id": doc_id}, UpdateExpression="SET #s=:ocr, updated_at=:now, attempts=:zero REMOVE lease_until, job_id", ConditionExpression="job_id=:job", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":ocr": "ocr_pending", ":now": now(), ":zero": 0, ":job": job})
                return
        else:
            parsed = parse_document(service, doc, raw)
            if not parsed["chunks"]:
                if parsed["pages"] > 10:
                    raise Problem(422, "ocr_page_limit")
                import hashlib
                token = hashlib.sha256((doc_id + doc["s3_version"]).encode()).hexdigest()
                started = service.client("textract").start_document_text_detection(DocumentLocation={"S3Object": {"Bucket": service.bucket, "Name": doc["s3_key"], "Version": doc["s3_version"]}}, ClientRequestToken=token)
                service.docs.update_item(Key={"doc_id": doc_id}, UpdateExpression="SET #s=:ocr, updated_at=:now, textract_job_id=:tid, ocr_started_at=:now, attempts=:zero REMOVE lease_until, job_id", ConditionExpression="job_id=:job", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":ocr": "ocr_pending", ":now": now(), ":tid": started["JobId"], ":zero": 0, ":job": job})
                return
        # User presigned forms can only write uploads/. Seal the selected version.
        source_key = f"documents/{doc_id}/source.pdf"
        sealed = s3.put_object(Bucket=service.bucket, Key=source_key, Body=raw, ContentType="application/pdf", ServerSideEncryption="AES256")
        extraction_key = f"documents/{doc_id}/extraction.json"
        extracted = s3.put_object(Bucket=service.bucket, Key=extraction_key, Body=json.dumps(parsed, ensure_ascii=False).encode(), ContentType="application/json", ServerSideEncryption="AES256")
        if not sealed.get("VersionId") or not extracted.get("VersionId"):
            raise RuntimeError("Bucket versioning is required")
        service.docs.update_item(Key={"doc_id": doc_id}, UpdateExpression="SET #s=:processed, updated_at=:now, source_key=:source, source_version=:sv, extraction_key=:extraction, extraction_version=:ev, page_count=:pages, chunk_count=:chunks REMOVE lease_until, job_id, error_code", ConditionExpression="#s=:processing AND job_id=:job", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":processed": "processed", ":processing": "processing", ":job": job, ":now": now(), ":source": source_key, ":sv": sealed["VersionId"], ":extraction": extraction_key, ":ev": extracted["VersionId"], ":pages": parsed["pages"], ":chunks": len(parsed["chunks"])})
    except Exception as exc:
        terminal = isinstance(exc, Problem)
        try:
            service.docs.update_item(Key={"doc_id": doc_id}, UpdateExpression="SET #s=:state, updated_at=:now, error_code=:error REMOVE lease_until, job_id", ConditionExpression="job_id=:job", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":state": "failed" if terminal else "pending", ":now": now(), ":error": exc.message if terminal else "processing_temporarily_unavailable", ":job": job})
        except Exception:
            log.exception("Could not record job failure doc_id=%s", doc_id)
        if not terminal:
            raise


def batch(service, event):
    failures = []
    for record in event.get("Records", []):
        try:
            data = json.loads(record.get("body", "{}"))
            if not isinstance(data, dict) or not isinstance(data.get("doc_id"), str) or not data["doc_id"]:
                raise ValueError("Missing doc_id")
            process(service, data["doc_id"])
        except Exception:
            log.exception("Worker failed messageId=%s", record.get("messageId"))
            if not record.get("messageId"):
                raise
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}


def delete_account(service, job):
    """Keep access blocked until every private record and object version is purged."""
    import os
    if not os.environ.get("USER_POOL_ID"):
        raise RuntimeError("User pool not configured")
    owner = job["owner_id"]
    args = {"ConsistentRead": True, "FilterExpression": Attr("owner_id").eq(owner), "Limit": 100}
    evaluated = 0
    while True:
        result = service.docs.scan(**args)
        evaluated += result.get("ScannedCount", 0)
        if evaluated > 10000:
            raise RuntimeError("Account purge requires operator assistance above 10000 metadata records")
        for doc in result.get("Items", []):
            if doc["doc_id"] == job["doc_id"] or doc.get("status") == "deleted":
                continue
            if doc.get("status") == "processing" and int(doc.get("lease_until", 0)) > int(time.time()):
                raise RuntimeError("Wait for the document worker lease to expire")
            service.docs.update_item(Key={"doc_id": doc["doc_id"]}, UpdateExpression="SET #s=:deleting", ConditionExpression="owner_id=:owner AND (#s<>:processing OR lease_until < :clock)", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":owner": owner, ":deleting": "deleting", ":processing": "processing", ":clock": int(time.time())})
            process(service, doc["doc_id"])
        if not result.get("LastEvaluatedKey"):
            break
        args["ExclusiveStartKey"] = result["LastEvaluatedKey"]
    history = service.table("HISTORY_TABLE_NAME")
    args = {"KeyConditionExpression": Key("owner_id").eq(owner), "ConsistentRead": True}
    while True:
        result = history.query(**args)
        with history.batch_writer() as batch_writer:
            for item in result.get("Items", []):
                batch_writer.delete_item(Key={"owner_id": owner, "conversation_id": item["conversation_id"]})
        if not result.get("LastEvaluatedKey"):
            break
        args["ExclusiveStartKey"] = result["LastEvaluatedKey"]
    if os.environ.get("SUPPORT_TABLE_NAME"):
        support = service.table("SUPPORT_TABLE_NAME")
        args = {"KeyConditionExpression": Key("owner_id").eq(owner), "ConsistentRead": True, "Limit": 50}
        while True:
            result = support.query(**args)
            with support.batch_writer() as batch_writer:
                for item in result.get("Items", []):
                    batch_writer.delete_item(Key={"owner_id": owner, "ticket_id": item["ticket_id"]})
            if not result.get("LastEvaluatedKey"):
                break
            args["ExclusiveStartKey"] = result["LastEvaluatedKey"]
    try:
        service.client("cognito-idp").admin_delete_user(UserPoolId=os.environ["USER_POOL_ID"], Username=job["username"])
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "UserNotFoundException":
            raise
    service.docs.update_item(Key={"doc_id": job["doc_id"]}, UpdateExpression="SET #s=:deleted, updated_at=:now, expires_at=:ttl REMOVE username", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":deleted": "deleted", ":now": now(), ":ttl": int(time.time()) + 30 * 86400})


def recover(service, event):
    """Scheduled backstop for stream failures, queue failures and Lambda timeouts."""
    threshold = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    updated = 0
    for status in ("pending", "processing", "ocr_pending", "deleting"):
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat() if status == "ocr_pending" else threshold
        result = service.docs.query(IndexName="StatusUpdatedAt", KeyConditionExpression=Key("status").eq(status) & Key("updated_at").lt(cutoff), Limit=100)
        for doc in result.get("Items", []):
            ocr_expired = status == "ocr_pending" and doc.get("ocr_started_at", now()) < (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            failed = ocr_expired or (status not in ("deleting", "ocr_pending") and int(doc.get("attempts", 0)) >= 3)
            next_state = "failed" if failed else (status if status in ("deleting", "ocr_pending") else "pending")
            try:
                service.docs.update_item(Key={"doc_id": doc["doc_id"]}, UpdateExpression="SET #s=:next, updated_at=:now, dispatch_id=:dispatch, error_code=:error REMOVE lease_until, job_id", ConditionExpression="#s=:previous AND updated_at=:old", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":next": next_state, ":now": now(), ":dispatch": uuid4().hex, ":error": "processing_retry_limit" if failed else "recovering_stalled_job", ":previous": status, ":old": doc["updated_at"]})
                updated += 1
            except ClientError as exc:
                if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                    raise
    return {"recovered": updated}
