"""Authenticated application operations; no credentials or content in logs."""
import base64
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb.types import TypeSerializer
from botocore.config import Config
from botocore.exceptions import ClientError

log = logging.getLogger(__name__)
MAX_BYTES = 10 * 1024 * 1024
MAX_EXTRACTION_BYTES = 2_000_000
MAX_PAGE_PREVIEW_CHARS = 20_000


class Problem(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def body(event):
    try:
        raw = event.get("body") or "{}"
        if len(raw) > 100_000:
            raise ValueError()
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw, validate=True).decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except (ValueError, TypeError, UnicodeError):
        raise Problem(400, "Body must be a valid JSON object") from None


def text(value, name, maximum=200):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise Problem(400, f"{name} must contain 1–{maximum} characters")
    return value.strip()


def encode(key):
    return base64.urlsafe_b64encode(json.dumps(key, separators=(",", ":")).encode()).decode()


def cursor(value, owner, keys):
    if not value:
        return None
    try:
        if not isinstance(value, str) or len(value) > 2048:
            raise ValueError()
        key = json.loads(base64.b64decode(value, altchars=b"-_", validate=True))
        if not isinstance(key, dict) or set(key) != set(keys) or key.get("owner_id") != owner or not all(isinstance(v, str) and v for v in key.values()):
            raise ValueError()
        return key
    except (ValueError, TypeError, UnicodeError):
        raise Problem(400, "Invalid next_token") from None


class Service:
    def __init__(self, documents, policies):
        self.docs, self.policies = documents, policies
        self.region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-1"))
        self.db = boto3.resource("dynamodb", region_name=self.region)
        self.bucket = os.environ.get("DOCUMENTS_BUCKET_NAME", "")
        self._clients = {}

    def client(self, name):
        if name not in self._clients:
            options = {"signature_version": "s3v4", "s3": {"addressing_style": "virtual"}} if name == "s3" else {}
            endpoint = {"endpoint_url": f"https://s3.{self.region}.amazonaws.com"} if name == "s3" else {}
            self._clients[name] = boto3.client(name, region_name=self.region, config=Config(connect_timeout=3, read_timeout=75 if name == "lambda" else 35, retries={"max_attempts": 2}, **options), **endpoint)
        return self._clients[name]

    def generation_client(self):
        if "bedrock-runtime" not in self._clients:
            self._clients["bedrock-runtime"] = boto3.client(
                "bedrock-runtime", region_name=self.region,
                config=Config(connect_timeout=3, read_timeout=20, retries={"total_max_attempts": 1}),
            )
        return self._clients["bedrock-runtime"]

    def table(self, env):
        name = os.environ.get(env)
        if not name:
            raise Problem(503, "Service configuration is incomplete")
        return self.db.Table(name)

    def owned(self, doc_id, owner):
        doc = self.docs.get_item(Key={"doc_id": doc_id}, ConsistentRead=True).get("Item")
        if not doc or doc.get("owner_id") != owner or doc.get("status") == "deleted":
            raise Problem(404, "Document not found")
        return doc

    def quota(self, owner, kind):
        """Both per-user/day and global/month reservations succeed atomically."""
        table = self.table("USAGE_TABLE_NAME")
        stamp = datetime.now(timezone.utc)
        limits = {
            "upload": (int(os.environ.get("UPLOADS_PER_USER_DAY", "5")), int(os.environ.get("UPLOADS_PER_MONTH", "300"))),
            "question": (int(os.environ.get("QUESTIONS_PER_USER_DAY", "20")), int(os.environ.get("QUESTIONS_PER_MONTH", "2000"))),
            "request": (1000, 100000),
            "feedback": (50,5000),
            "ticket": (int(os.environ.get("TICKETS_PER_USER_DAY", "5")), int(os.environ.get("TICKETS_PER_MONTH", "200"))),
        }
        daily, monthly = limits[kind]
        keys = [(f"user#{owner}#{kind}#{stamp:%Y-%m-%d}", daily), (f"global#{kind}#{stamp:%Y-%m}", monthly)]
        updates = []
        for key, limit in keys:
            updates.append({"Update": {
                "TableName": table.name,
                "Key": {"pk": {"S": key}},
                "UpdateExpression": "SET expires_at = :ttl ADD #n :one",
                "ConditionExpression": "attribute_not_exists(#n) OR #n < :limit",
                "ExpressionAttributeNames": {"#n": "count"},
                "ExpressionAttributeValues": {
                    ":ttl": {"N": str(int(time.time()) + 65 * 86400)},
                    ":one": {"N": "1"}, ":limit": {"N": str(limit)},
                },
            }})
        try:
            self.client("dynamodb").transact_write_items(TransactItems=updates)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "TransactionCanceledException" and any(reason.get("Code") == "ConditionalCheckFailed" for reason in exc.response.get("CancellationReasons", [])):
                raise Problem(429, "Usage limit reached. Try again after the daily or monthly reset.") from None
            raise

    def audit(self, owner, action, resource, request_id):
        self.table("AUDIT_TABLE_NAME").put_item(Item={"scope": "admin", "event_id": now() + "#" + uuid4().hex, "actor": owner, "action": action, "resource": resource, "request_id": request_id, "expires_at": int(time.time()) + 90 * 86400})

    def policy_change(self, owner, action, policy_id, request_id, item=None, condition=None):
        serialize = TypeSerializer().serialize
        audit = {"scope": "admin", "event_id": now() + "#" + uuid4().hex, "actor": owner, "action": action, "resource": policy_id, "request_id": request_id, "expires_at": int(time.time()) + 90 * 86400}
        change = {"Put": {"TableName": self.policies.name, "Item": {k: serialize(v) for k, v in item.items()}}} if item else {"Delete": {"TableName": self.policies.name, "Key": {"policy_id": {"S": policy_id}}}}
        if condition:
            change["Put" if item else "Delete"].update(condition)
        try:
            self.client("dynamodb").transact_write_items(TransactItems=[change, {"Put": {"TableName": self.table("AUDIT_TABLE_NAME").name, "Item": {k: serialize(v) for k, v in audit.items()}}}])
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "TransactionCanceledException" and any(reason.get("Code") == "ConditionalCheckFailed" for reason in exc.response.get("CancellationReasons", [])):
                raise Problem(409, "Policy changed while saving. Reload before retrying.") from None
            raise

    def list_docs(self, owner, params):
        try:
            limit = int(params.get("limit", "20"))
            if not 1 <= limit <= 50:
                raise ValueError()
        except (ValueError, TypeError):
            raise Problem(400, "limit must be an integer from 1 to 50") from None
        args = {"IndexName": "OwnerCreatedAt", "KeyConditionExpression": Key("owner_id").eq(owner), "ScanIndexForward": False, "Limit": limit, "FilterExpression": Attr("status").ne("deleted") & Attr("record_type").not_exists()}
        start = cursor(params.get("next_token"), owner, {"owner_id", "created_at", "doc_id"})
        if start:
            args["ExclusiveStartKey"] = start
        result = self.docs.query(**args)
        return {"documents": [self.public_doc(d) for d in result.get("Items", [])], "next_token": encode(result["LastEvaluatedKey"]) if result.get("LastEvaluatedKey") else None}

    @staticmethod
    def public_doc(doc):
        fields = {"doc_id", "filename", "title", "status", "created_at", "submitted_at", "updated_at", "page_count", "chunk_count", "size_bytes", "error_code", "s3_key"}
        return {key: value for key, value in doc.items() if key in fields}

    def upload(self, owner, data):
        filename = text(data.get("filename", "document.pdf"), "filename", 180)
        if "/" in filename or "\\" in filename or not filename.lower().endswith(".pdf") or any(ord(c) < 32 for c in filename):
            raise Problem(400, "Choose a PDF filename without path components")
        self.quota(owner, "upload")
        doc_id = "doc-" + uuid4().hex
        key = f"quarantine/{doc_id}/document"
        post = self.client("s3").generate_presigned_post(Bucket=self.bucket, Key=key, Fields={"Content-Type": "application/pdf"}, Conditions=[["content-length-range", 1, MAX_BYTES], {"Content-Type": "application/pdf"}], ExpiresIn=300)
        stamp = now()
        self.docs.put_item(Item={"doc_id": doc_id, "owner_id": owner, "filename": filename, "title": filename[:-4], "s3_key": key, "status": "awaiting_upload", "created_at": stamp, "updated_at": stamp}, ConditionExpression="attribute_not_exists(doc_id)")
        return {"doc_id": doc_id, "s3_key": key, "upload_url": post["url"], "upload_fields": post["fields"], "upload_method": "POST", "expires_in": 300}

    def submit(self, owner, data):
        doc_id = text(data.get("doc_id"), "doc_id", 100)
        key = text(data.get("s3_key"), "s3_key", 250)
        doc = self.owned(doc_id, owner)
        if key != doc.get("s3_key"):
            raise Problem(400, "s3_key must match the upload session")
        if doc["status"] in ("processed", "pending", "processing", "ocr_pending"):
            return {"doc_id": doc_id, "status": doc["status"]}
        if doc["status"] != "awaiting_upload":
            raise Problem(409, "Create a new upload session for this document")
        try:
            uploaded = self.client("s3").head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                raise Problem(409, "Upload the file before submitting") from None
            raise
        if uploaded.get("ContentType") != "application/pdf" or not 0 < uploaded.get("ContentLength", 0) <= MAX_BYTES:
            raise Problem(400, "Upload must be a non-empty PDF of at most 10 MiB")
        version = uploaded.get("VersionId")
        if not version or version == "null":
            raise Problem(503, "Document bucket versioning must be enabled")
        stamp = now()
        self.docs.update_item(Key={"doc_id": doc_id}, UpdateExpression="SET #s=:pending, updated_at=:now, submitted_at=:now, s3_version=:v, size_bytes=:size, dispatch_id=:dispatch, attempts=:zero", ConditionExpression="owner_id=:owner AND #s=:awaiting", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":pending": "pending", ":now": stamp, ":v": version, ":size": uploaded["ContentLength"], ":dispatch": uuid4().hex, ":zero": 0, ":owner": owner, ":awaiting": "awaiting_upload"})
        # The DynamoDB stream is the durable outbox. Do not send inline to SQS.
        return {"doc_id": doc_id, "status": "pending"}

    def read_extraction(self, doc):
        """Read a bounded extraction from the server-selected object version."""
        key = doc.get("extraction_key")
        version = doc.get("extraction_version")
        if not key or not version:
            raise Problem(503, "Extracted text is unavailable")
        obj = self.client("s3").get_object(Bucket=self.bucket, Key=key, VersionId=version)
        try:
            raw = obj["Body"].read(MAX_EXTRACTION_BYTES + 1)
        finally:
            obj["Body"].close()
        if len(raw) > MAX_EXTRACTION_BYTES:
            raise Problem(503, "Document index exceeds its configured limit")
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict) or not isinstance(parsed.get("chunks"), list):
                raise ValueError()
            return parsed
        except (ValueError, UnicodeError):
            raise Problem(503, "Extracted text is unavailable") from None

    def document_text(self, owner, doc, params):
        raw_page = params.get("page", "1")
        if not isinstance(raw_page, str) or not re.fullmatch(r"[1-9][0-9]{0,2}", raw_page):
            raise Problem(400, "page must be an integer from 1 to 100")
        page = int(raw_page)
        if page > 100:
            raise Problem(400, "page must be an integer from 1 to 100")
        if doc["status"] != "processed":
            raise Problem(409, "Document is not processed yet")
        extracted = self.read_extraction(doc)
        pages = extracted.get("pages")
        if type(pages) is not int or not 1 <= pages <= 100:
            raise Problem(503, "Extracted text is unavailable")
        if page > pages:
            raise Problem(400, "Page is outside this document")
        chunks = []
        remaining = MAX_PAGE_PREVIEW_CHARS
        truncated = False
        for chunk in extracted["chunks"]:
            if not isinstance(chunk, dict) or chunk.get("page") != page:
                continue
            value = chunk.get("text")
            if not isinstance(value, str) or not value:
                continue
            if len(value) > remaining:
                if remaining:
                    chunks.append(value[:remaining])
                truncated = True
                break
            chunks.append(value)
            remaining -= len(value)
        current = self.owned(doc["doc_id"], owner)
        account = self.table("USAGE_TABLE_NAME").get_item(Key={"pk": f"account#{owner}"}, ConsistentRead=True).get("Item", {})
        if account.get("state") == "deleting":
            raise Problem(410, "Account deletion is in progress")
        if current.get("status") != "processed" or current.get("extraction_version") != doc["extraction_version"]:
            raise Problem(409, "Document changed while loading extracted text")
        return {"doc_id": doc["doc_id"], "title": current.get("title") or current.get("filename"), "page": page,
                "page_count": pages, "chunks": chunks, "truncated": truncated}

    def document_route(self, method, path, owner, data, params):
        if path == "/documents" and method == "GET":
            return self.list_docs(owner, params)
        if path == "/documents/upload-session" and method == "POST":
            return self.upload(owner, data)
        if path == "/documents/submit" and method == "POST":
            return self.submit(owner, data)
        match = re.fullmatch(r"/documents/(doc-[a-f0-9]{32})(?:/(status|download|text))?", path)
        if not match:
            raise Problem(404, "Invalid document endpoint")
        doc_id, action = match.groups()
        doc = self.owned(doc_id, owner)
        if method == "GET" and action == "status":
            return {**self.public_doc(doc), "s3_key": doc.get("s3_key")}
        if method == "GET" and action == "text":
            return self.document_text(owner, doc, params)
        if method == "GET" and action == "download":
            if doc["status"] != "processed":
                raise Problem(409, "Document is not processed yet")
            url = self.client("s3").generate_presigned_url("get_object", Params={"Bucket": self.bucket, "Key": doc["source_key"], "VersionId": doc["source_version"], "ResponseContentDisposition": "attachment; filename=policy-document.pdf"}, ExpiresIn=300)
            return {"doc_id": doc_id, "download_url": url, "expires_in": 300}
        if method == "PATCH" and action is None:
            title = text(data.get("title"), "title", 180)
            self.docs.update_item(Key={"doc_id": doc_id}, UpdateExpression="SET title=:title", ConditionExpression="owner_id=:owner AND #s<>:deleted AND #s<>:deleting", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":title": title, ":owner": owner, ":deleted": "deleted", ":deleting": "deleting"})
            return {"doc_id": doc_id, "title": title}
        if method == "DELETE" and action is None:
            if doc["status"] == "deleting":
                return {"doc_id": doc_id, "status": "deleting"}
            if doc["status"] == "processing" and int(doc.get("lease_until", 0)) > int(time.time()):
                raise Problem(409, "Processing is in progress; retry deletion shortly")
            self.docs.update_item(Key={"doc_id": doc_id}, UpdateExpression="SET #s=:deleting, updated_at=:now, dispatch_id=:dispatch", ConditionExpression="owner_id=:owner AND #s<>:processing", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":owner": owner, ":deleting": "deleting", ":processing": "processing", ":now": now(), ":dispatch": uuid4().hex})
            return {"doc_id": doc_id, "status": "deleting"}
        raise Problem(405, "Method not allowed")

    def save_answer(self,owner,item,response_ms):
        try:
            from .quality import save_answer
        except ImportError:
            from quality import save_answer
        save_answer(self,owner,item,response_ms)

    def history(self, method, path, owner, params):
        table = self.table("HISTORY_TABLE_NAME")
        if method == "GET" and path == "/conversations":
            args = {"KeyConditionExpression": Key("owner_id").eq(owner), "ScanIndexForward": False, "Limit": 20, "ConsistentRead": True,"FilterExpression":Attr("expires_at").gt(int(time.time()))}
            key = cursor(params.get("next_token"), owner, {"owner_id", "conversation_id"})
            if key:
                args["ExclusiveStartKey"] = key
            result = table.query(**args)
            return {"conversations": result.get("Items", []), "next_token": encode(result["LastEvaluatedKey"]) if result.get("LastEvaluatedKey") else None}
        match = re.fullmatch(r"/conversations/([^/]{1,100})", path)
        if match and method == "DELETE":
            table.delete_item(Key={"owner_id": owner, "conversation_id": match[1]})
            return {"deleted": True}
        raise Problem(405, "Method not allowed")

    def admin(self, method, path, owner, claims, data, params, request_id):
        groups = claims.get("cognito:groups", [])
        if isinstance(groups, str):
            groups = groups.strip("[]").replace('"', '').split(",")
        if "administrators" not in groups:
            raise Problem(403, "Administrator access required")
        if path == "/admin/quality" and method=="GET":
            try:
                from .quality import summary
            except ImportError:
                from quality import summary
            return summary(self,params)
        if path == "/admin/shop":
            try:
                from .shop import handle
            except ImportError:
                from shop import handle
            return handle(self, method, owner, data, request_id)
        if path == "/admin/overview" and method == "GET":
            usage = self.table("USAGE_TABLE_NAME")
            month = datetime.now(timezone.utc).strftime("%Y-%m")
            totals = {kind: int(usage.get_item(Key={"pk": f"global#{kind}#{month}"}, ConsistentRead=True).get("Item", {}).get("count", 0)) for kind in ("upload", "question", "ticket", "request")}
            return {"month": month, "usage": totals, "model_configured": bool(os.environ.get("BEDROCK_MODEL_ID")), "limits": {"uploads": int(os.environ.get("UPLOADS_PER_MONTH", "300")), "questions": int(os.environ.get("QUESTIONS_PER_MONTH", "2000")), "tickets": int(os.environ.get("TICKETS_PER_MONTH", "200")), "requests": 100000}}
        if path == "/admin/audit" and method == "GET":
            args = {"KeyConditionExpression": Key("scope").eq("admin"), "ScanIndexForward": False, "Limit": 30}
            if params.get("next_token"):
                try:
                    key = json.loads(base64.urlsafe_b64decode(params["next_token"]))
                    if set(key) != {"scope", "event_id"} or key["scope"] != "admin" or not isinstance(key["event_id"], str):
                        raise ValueError()
                    args["ExclusiveStartKey"] = key
                except (ValueError, TypeError):
                    raise Problem(400, "Invalid next_token") from None
            result = self.table("AUDIT_TABLE_NAME").query(**args)
            return {"events": result.get("Items", []), "next_token": encode(result["LastEvaluatedKey"]) if result.get("LastEvaluatedKey") else None}
        if path == "/admin/tickets" or path.startswith("/admin/tickets/"):
            try:
                from .tickets import handle
            except ImportError:
                from tickets import handle
            return handle(self, method, path, owner, data, params, request_id, admin=True)
        if path == "/admin/policies" or path.startswith("/admin/policies/"):
            try:
                from .policy_admin import handle
            except ImportError:
                from policy_admin import handle
            return handle(self, method, path, owner, data, params, request_id)
        raise Problem(404, "Invalid administrator endpoint")

    def handle(self, event, method, path, owner, claims):
        params = event.get("queryStringParameters") or {}
        data = body(event) if method in ("POST", "PUT", "PATCH") else {}
        if path == "/account/delete" and method == "POST":
            if data.get("confirmation") != "DELETE":
                raise Problem(400, "Explicit account deletion confirmation is required")
            username = claims.get("cognito:username")
            if not isinstance(username, str) or not username:
                raise Problem(503, "Account identity is incomplete")
            self.table("USAGE_TABLE_NAME").put_item(Item={"pk": f"account#{owner}", "state": "deleting", "expires_at": int(time.time()) + 65 * 86400})
            job_id = "account-" + owner
            existing = self.docs.get_item(Key={"doc_id": job_id}, ConsistentRead=True).get("Item")
            if existing:
                if existing.get("owner_id") != owner or existing.get("record_type") != "account_deletion":
                    raise Problem(409, "Account deletion state requires operator review")
                if existing.get("status") in ("deleting", "deleted"):
                    return {"status": existing["status"], "message": "Account deletion has already been accepted."}
            stamp = now()
            self.docs.put_item(Item={"doc_id": job_id, "record_type": "account_deletion", "owner_id": owner, "username": username, "status": "deleting", "created_at": stamp, "updated_at": stamp, "dispatch_id": uuid4().hex})
            return {"status": "deleting", "message": "Your account and private documents are scheduled for permanent deletion."}
        account = self.table("USAGE_TABLE_NAME").get_item(Key={"pk": f"account#{owner}"}, ConsistentRead=True).get("Item", {})
        if account.get("state") == "deleting":
            raise Problem(410, "Account deletion is in progress")
        self.quota(owner, "request")
        if path == "/me" and method == "GET":
            groups = claims.get("cognito:groups", [])
            return {"user_id": owner, "email": claims.get("email", ""), "groups": groups, "limits": {"uploads_per_day": int(os.environ.get("UPLOADS_PER_USER_DAY", "5")), "questions_per_day": int(os.environ.get("QUESTIONS_PER_USER_DAY", "20")), "tickets_per_day": int(os.environ.get("TICKETS_PER_USER_DAY", "5"))}, "ai_available": bool(os.environ.get("BEDROCK_MODEL_ID"))}
        if path == "/shop" and method == "GET":
            try:
                from .shop import customer, load
            except ImportError:
                from shop import customer, load
            return customer(load(self))
        if path == "/documents" or path.startswith("/documents/"):
            return self.document_route(method, path, owner, data, params)
        if path == "/tickets" or path.startswith("/tickets/"):
            try:
                from .tickets import handle
            except ImportError:
                from tickets import handle
            return handle(self, method, path, owner, body(event) if method == "DELETE" else data, params, event.get("requestContext", {}).get("requestId", "unknown"))
        feedback_match=re.fullmatch(r"/conversations/([^/]{1,150})/feedback",path)
        if feedback_match and method=="PATCH":
            try:
                from .quality import feedback
            except ImportError:
                from quality import feedback
            return feedback(self,owner,feedback_match[1],data)
        if path.startswith("/conversations"):
            return self.history(method, path, owner, params)
        if path.startswith("/admin/"):
            return self.admin(method, path, owner, claims, data, params, event.get("requestContext", {}).get("requestId", "unknown"))
        if path == "/ask" and method == "POST":
            try:
                from .assistant import answer
            except ImportError:
                from assistant import answer
            return answer(self, owner, data)
        raise Problem(404, "Invalid endpoint")
