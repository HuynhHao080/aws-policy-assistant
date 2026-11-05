"""Offline contract tests using real boto3 calls against moto services."""
import base64
import json
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws
from botocore.exceptions import ClientError

from policy_assistant import app
from tests.unit.pdf_fixture import pdf_bytes
from boto3.dynamodb.types import TypeSerializer


def event(path, method="GET", user="alice", body=None):
    context = {"http": {"method": method, "path": path}, "requestId": "request-1"}
    if user is not None:
        context["authorizer"] = {"jwt": {"claims": {"sub": user}}}
    parts = path.split("/")
    params = {"doc_id": parts[2]} if len(parts) == 4 else {}
    return {"requestContext": context, "pathParameters": params, "body": body}


@pytest.fixture
def services(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-southeast-1")
    monkeypatch.setenv("DOCUMENTS_BUCKET_NAME", "test-policy-documents")
    monkeypatch.setenv("ALLOW_LOCAL_PDF_PARSER", "true")
    with mock_aws():
        db = boto3.resource("dynamodb", region_name="ap-southeast-1")
        table = db.create_table(TableName="TestDocuments", KeySchema=[{"AttributeName": "doc_id", "KeyType": "HASH"}], AttributeDefinitions=[{"AttributeName": k, "AttributeType": "S"} for k in ("doc_id", "owner_id", "created_at", "status", "updated_at")], GlobalSecondaryIndexes=[{"IndexName":"OwnerCreatedAt","KeySchema":[{"AttributeName":"owner_id","KeyType":"HASH"},{"AttributeName":"created_at","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}},{"IndexName":"StatusUpdatedAt","KeySchema":[{"AttributeName":"status","KeyType":"HASH"},{"AttributeName":"updated_at","KeyType":"RANGE"}],"Projection":{"ProjectionType":"ALL"}}], BillingMode="PAY_PER_REQUEST")
        monkeypatch.setattr(app, "document_table", table)
        policy_table = db.create_table(TableName="TestPolicies", KeySchema=[{"AttributeName": "policy_id", "KeyType": "HASH"}], AttributeDefinitions=[{"AttributeName": "policy_id", "AttributeType": "S"}], BillingMode="PAY_PER_REQUEST")
        monkeypatch.setattr(app, "table", policy_table)
        for env_name, name, pk, sk in [("USAGE_TABLE_NAME","TestUsage","pk",None),("HISTORY_TABLE_NAME","TestHistory","owner_id","conversation_id"),("AUDIT_TABLE_NAME","TestAudit","scope","event_id")]:
            attributes=[{"AttributeName":pk,"AttributeType":"S"}]
            keys=[{"AttributeName":pk,"KeyType":"HASH"}]
            if sk:
                attributes.append({"AttributeName":sk,"AttributeType":"S"});keys.append({"AttributeName":sk,"KeyType":"RANGE"})
            db.create_table(TableName=name,AttributeDefinitions=attributes,KeySchema=keys,BillingMode="PAY_PER_REQUEST")
            monkeypatch.setenv(env_name,name)
        s3 = boto3.client("s3", region_name="ap-southeast-1")
        s3.create_bucket(Bucket="test-policy-documents", CreateBucketConfiguration={"LocationConstraint": "ap-southeast-1"})
        s3.put_bucket_versioning(Bucket="test-policy-documents",VersioningConfiguration={"Status":"Enabled"})
        sqs = boto3.client("sqs", region_name="ap-southeast-1")
        queue = sqs.create_queue(QueueName="test-documents")["QueueUrl"]
        monkeypatch.setenv("DOCUMENT_QUEUE_URL", queue)
        yield table, s3, sqs, queue


def call(path, method="GET", user="alice", body=None):
    response = app.lambda_handler(event(path, method, user, body), None)
    return response["statusCode"], json.loads(response["body"])


def session(services, upload=True):
    code, data = call("/documents/upload-session", "POST")
    assert code == 200
    if upload:
        services[1].put_object(Bucket="test-policy-documents", Key=data["s3_key"], Body=pdf_bytes(), ContentType="application/pdf")
    return data


def submit(data, user="alice"):
    return call("/documents/submit", "POST", user, json.dumps({"doc_id": data["doc_id"], "s3_key": data["s3_key"]}))


def test_document_lifecycle_and_duplicate_delivery(services):
    data = session(services)
    doc_id = data["doc_id"]
    assert call(f"/documents/{doc_id}/status")[1]["status"] == "awaiting_upload"
    assert submit(data) == (200, {"doc_id": doc_id, "status": "pending"})
    timestamp = services[0].get_item(Key={"doc_id": doc_id})["Item"]["submitted_at"]
    assert timestamp.endswith("+00:00")
    assert submit(data)[0] == 200
    assert services[0].get_item(Key={"doc_id": doc_id})["Item"]["submitted_at"] == timestamp
    assert call(f"/documents/{doc_id}/download")[0] == 409
    item=services[0].get_item(Key={"doc_id":doc_id})["Item"]
    serializer=TypeSerializer()
    stream={"Records":[{"eventName":"MODIFY","dynamodb":{"SequenceNumber":"123","NewImage":{k:serializer.serialize(v) for k,v in item.items()},"OldImage":{}}}]}
    assert app.dispatch_handler(stream,None)=={"batchItemFailures":[]}
    messages = services[2].receive_message(QueueUrl=services[3], MaxNumberOfMessages=10)["Messages"]
    records = [{"messageId": m["MessageId"], "body": m["Body"]} for m in messages]
    assert app.worker_handler({"Records": records}, None) == {"batchItemFailures": []}
    assert app.worker_handler({"Records": records}, None) == {"batchItemFailures": []}
    assert call(f"/documents/{doc_id}/status")[1]["status"] == "processed"
    code, download = call(f"/documents/{doc_id}/download")
    assert code == 200 and download["download_url"].startswith("https://")
    assert submit(data)[1]["status"] == "processed"


@pytest.mark.parametrize("action", ["status", "download", "submit"])
def test_other_user_cannot_access_or_submit_document(services, action):
    data = session(services)
    result = submit(data, "bob") if action == "submit" else call(f"/documents/{data['doc_id']}/{action}", user="bob")
    assert result[0] == 404
    item = services[0].get_item(Key={"doc_id": data["doc_id"]})["Item"]
    assert item["owner_id"] == "alice" and item["status"] == "awaiting_upload"


@pytest.mark.parametrize("path,method", [("/documents/upload-session", "POST"), ("/documents/submit", "POST"), ("/documents/doc-1/status", "GET"), ("/documents/doc-1/download", "GET")])
def test_document_routes_require_verified_identity(path, method):
    assert call(path, method, user=None)[0] == 401


@pytest.mark.parametrize("body", ["{", "[]", "null", '"text"', "{}", '{"doc_id":12,"s3_key":"x"}'])
def test_submit_rejects_malformed_body(services, body):
    assert call("/documents/submit", "POST", body=body)[0] == 400


def test_missing_upload_and_forged_key_are_rejected(services):
    data = session(services, upload=False)
    assert submit(data)[0] == 409
    assert submit({**data, "s3_key": "uploads/someone-else/document"})[0] == 400
    assert submit({"doc_id": "invented", "s3_key": "invented"})[0] == 404


@pytest.mark.parametrize("content,mime", [(b"", "application/pdf"), (b"x", "text/plain"), (b"x" * (10 * 1024 * 1024 + 1), "application/pdf")], ids=["empty", "wrong-mime", "too-large"])
def test_invalid_uploaded_file_is_rejected(services, content, mime):
    data = session(services, upload=False)
    services[1].put_object(Bucket="test-policy-documents", Key=data["s3_key"], Body=content, ContentType=mime)
    assert submit(data)[0] == 400


def test_stream_dispatch_failure_preserves_pending_metadata(services, monkeypatch):
    data=session(services)
    assert submit(data)[0]==200
    item=services[0].get_item(Key={"doc_id":data["doc_id"]})["Item"]
    serializer=TypeSerializer()
    stream={"Records":[{"eventName":"MODIFY","dynamodb":{"SequenceNumber":"retry-1","NewImage":{k:serializer.serialize(v) for k,v in item.items()},"OldImage":{}}}]}
    monkeypatch.delenv("DOCUMENT_QUEUE_URL")
    assert app.dispatch_handler(stream,None)=={"batchItemFailures":[{"itemIdentifier":"retry-1"}]}
    monkeypatch.setenv("DOCUMENT_QUEUE_URL",services[3])
    assert app.dispatch_handler(stream,None)=={"batchItemFailures":[]}
    assert services[0].get_item(Key={"doc_id":data["doc_id"]})["Item"]["status"]=="pending"


def test_worker_reports_only_failed_records_and_never_creates_missing_document(services):
    data = session(services)
    assert submit(data)[0] == 200
    records = [{"messageId": "good", "body": json.dumps({"doc_id": data["doc_id"]})}, {"messageId": "bad-json", "body": "{"}, {"messageId": "missing", "body": '{"doc_id":"missing"}'}, {"messageId": "bad-schema", "body": "[]"}]
    assert app.worker_handler({"Records": records}, None) == {"batchItemFailures": [{"itemIdentifier": "bad-json"}, {"itemIdentifier": "missing"}, {"itemIdentifier": "bad-schema"}]}
    assert "Item" not in services[0].get_item(Key={"doc_id": "missing"})


def test_worker_retries_database_failure(services):
    with patch.object(app.document_table, "update_item", side_effect=RuntimeError("temporary failure")):
        assert app.worker_handler({"Records": [{"messageId": "retry-me", "body": '{"doc_id":"doc-1"}'}]}, None) == {"batchItemFailures": [{"itemIdentifier": "retry-me"}]}


def test_base64_submit_body_and_exact_routes(services):
    data = session(services)
    request = event("/Prod/documents/submit", "POST", body=base64.b64encode(json.dumps({"doc_id": data["doc_id"], "s3_key": data["s3_key"]}).encode()).decode())
    request["isBase64Encoded"] = True
    assert app.lambda_handler(request, None)["statusCode"] == 200
    assert call(f"/documents/{data['doc_id']}/status-extra")[0] == 404


def test_legacy_metadata_without_owner_is_not_exposed(services):
    services[0].put_item(Item={"doc_id": "legacy", "s3_key": "old", "status": "processed"})
    assert call("/documents/legacy/status")[0] == 404
    assert call("/documents/legacy/download")[0] == 404
