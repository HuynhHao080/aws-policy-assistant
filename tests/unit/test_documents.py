"""Offline regressions for authorization, immutable bytes, retry and pagination."""
import base64
import hashlib
import importlib
import json
from unittest.mock import Mock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws
from policy_assistant import app

PDF = b"%PDF-1.4\nsynthetic test document\n%%EOF"


def event(path, method="GET", owner="alice", body=None):
    context = {"http": {"path": path, "method": method}, "requestId": "test-request"}
    if owner:
        context["authorizer"] = {"jwt": {"claims": {"sub": owner}}}
    params = {"doc_id": path.split("/")[2]} if path.endswith(("/status", "/download")) else {}
    return {"requestContext": context, "pathParameters": params,
            "body": json.dumps(body) if body is not None else None}


def call(path, method="GET", owner="alice", body=None):
    response = app.lambda_handler(event(path, method, owner, body), None)
    return response["statusCode"], json.loads(response["body"])


@pytest.fixture
def services(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-southeast-1")
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="ap-southeast-1")
        for name, key in [("PolicyAssistantDocumentMetadata", "doc_id"), ("PolicyAssistantPolicies", "policy_id")]:
            indexes = {}
            if key == "doc_id":
                indexes = {"GlobalSecondaryIndexes": [
                    {"IndexName": "ByOwner", "KeySchema": [{"AttributeName": "owner_sub", "KeyType": "HASH"}, {"AttributeName": "created_at", "KeyType": "RANGE"}], "Projection": {"ProjectionType": "ALL"}},
                    {"IndexName": "ByStatus", "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}, {"AttributeName": "dispatch_after", "KeyType": "RANGE"}], "Projection": {"ProjectionType": "ALL"}}]}
            attrs = [{"AttributeName": key, "AttributeType": "S"}]
            if indexes:
                attrs += [{"AttributeName": n, "AttributeType": "S"} for n in ("owner_sub", "created_at", "status")]
                attrs.append({"AttributeName": "dispatch_after", "AttributeType": "N"})
            ddb.create_table(TableName=name, **indexes, KeySchema=[{"AttributeName": key, "KeyType": "HASH"}],
                AttributeDefinitions=attrs, BillingMode="PAY_PER_REQUEST")
        s3 = boto3.client("s3", region_name="ap-southeast-1")
        s3.create_bucket(Bucket="document-tests", CreateBucketConfiguration={"LocationConstraint": "ap-southeast-1"})
        s3.put_bucket_versioning(Bucket="document-tests", VersioningConfiguration={"Status": "Enabled"})
        queue = boto3.client("sqs", region_name="ap-southeast-1").create_queue(QueueName="documents")["QueueUrl"]
        monkeypatch.setenv("DOCUMENTS_BUCKET_NAME", "document-tests")
        monkeypatch.setenv("DOCUMENT_QUEUE_URL", queue)
        monkeypatch.setenv("DOCUMENT_METADATA_TABLE_NAME", "PolicyAssistantDocumentMetadata")
        monkeypatch.setenv("POLICIES_TABLE_NAME", "PolicyAssistantPolicies")
        importlib.reload(app)
        yield s3


def uploaded(services):
    code, session = call("/documents/upload-session", "POST")
    assert code == 200
    services.put_object(Bucket="document-tests", Key=session["s3_key"], Body=PDF, ContentType="application/pdf")
    return session


def worker(doc_id):
    item = app.document_table.get_item(Key={"doc_id": doc_id})["Item"]
    return app.worker_handler({"Records": [{"messageId": "test-message", "body": json.dumps({"doc_id": doc_id, "submission_id": item["submission_id"]})}]}, None)


@pytest.mark.parametrize("path,method", [("/documents/upload-session", "POST"),
    ("/documents/submit", "POST"), ("/documents/doc-test/status", "GET"), ("/documents/doc-test/download", "GET")])
def test_missing_authorizer_identity_is_rejected(services, path, method):
    assert call(path, method, owner=None)[0] == 401


@pytest.mark.parametrize("operation", ["submit", "status", "download"])
def test_other_users_cannot_access_or_replace_a_document(services, operation):
    session = uploaded(services)
    doc_id = session["doc_id"]
    if operation == "submit":
        code, _ = call("/documents/submit", "POST", "bob", {"doc_id": doc_id, "s3_key": session["s3_key"]})
    else:
        code, _ = call(f"/documents/{doc_id}/{operation}", owner="bob")
    assert code == 404
    assert app.document_table.get_item(Key={"doc_id": doc_id})["Item"]["owner_sub"] == "alice"


def test_legacy_unowned_records_are_not_exposed(services):
    app.document_table.put_item(Item={"doc_id": "legacy", "status": "processed", "s3_key": "old"})
    assert call("/documents/legacy/status")[0] == 404
    assert call("/documents/legacy/download")[0] == 404


def test_version_is_frozen_and_worker_computes_original_hash(services):
    session = uploaded(services)
    doc_id = session["doc_id"]
    assert call("/documents/submit", "POST", body={"doc_id": doc_id})[0] == 200
    services.put_object(Bucket="document-tests", Key=session["s3_key"], Body=b"%PDF-replacement", ContentType="application/pdf")
    worker(doc_id)
    worker(doc_id)  # duplicate delivery must not reset/reprocess a finished document
    code, status = call(f"/documents/{doc_id}/status")
    assert code == 200 and status["status"] == "processed"
    assert status["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert "T" in status["submitted_at"] and "owner_sub" not in status
    code, download = call(f"/documents/{doc_id}/download")
    assert code == 200 and "versionId=" in download["download_url"]
    item = app.document_table.get_item(Key={"doc_id": doc_id})["Item"]
    assert services.get_object(Bucket="document-tests", Key=item["s3_key"], VersionId=item["version_id"])["Body"].read() == PDF
    assert call("/documents/submit", "POST", body={"doc_id": doc_id})[1]["status"] == "processed"


def test_download_before_processing_returns_conflict(services):
    session = uploaded(services)
    assert call(f"/documents/{session['doc_id']}/download")[0] == 409


def test_submit_requires_an_uploaded_object(services):
    _, session = call("/documents/upload-session", "POST")
    assert call("/documents/submit", "POST", body={"doc_id": session["doc_id"]})[0] == 409


def test_submit_rejects_key_substitution(services):
    session = uploaded(services)
    assert call("/documents/submit", "POST", body={"doc_id": session["doc_id"], "s3_key": "other/document"})[0] == 400


@pytest.mark.parametrize("body", [[], "bad", {"doc_id": 42}, {}])
def test_submit_rejects_non_object_or_invalid_doc_id(services, body):
    assert call("/documents/submit", "POST", body=body)[0] == 400


def test_queue_failure_can_be_retried_without_resetting_submission(services):
    session = uploaded(services)
    failing = Mock()
    failing.send_message.side_effect = ClientError({"Error": {"Code": "ServiceUnavailable"}}, "SendMessage")
    with patch.object(app.boto3, "client", return_value=failing), patch.object(app, "_s3", return_value=services):
        assert call("/documents/submit", "POST", body={"doc_id": session["doc_id"]})[0] == 503
    first = app.document_table.get_item(Key={"doc_id": session["doc_id"]})["Item"]
    assert first["status"] == "pending"
    assert call("/documents/submit", "POST", body={"doc_id": session["doc_id"]})[0] == 200
    second = app.document_table.get_item(Key={"doc_id": session["doc_id"]})["Item"]
    assert second["version_id"] == first["version_id"]
    assert second["submitted_at"] == first["submitted_at"]


def test_worker_failure_propagates_for_sqs_retry(services):
    session = uploaded(services)
    call("/documents/submit", "POST", body={"doc_id": session["doc_id"]})
    with patch.object(app, "_s3", side_effect=RuntimeError("service unavailable")):
        assert worker(session["doc_id"])["batchItemFailures"] == [{"itemIdentifier": "test-message"}]
    assert call(f"/documents/{session['doc_id']}/status")[1]["status"] == "pending"
    worker(session["doc_id"])
    assert call(f"/documents/{session['doc_id']}/status")[1]["status"] == "processed"


def test_worker_rejects_non_pdf_bytes(services):
    session = uploaded(services)
    services.put_object(Bucket="document-tests", Key=session["s3_key"], Body=b"not a PDF", ContentType="application/pdf")
    call("/documents/submit", "POST", body={"doc_id": session["doc_id"]})
    worker(session["doc_id"])
    assert call(f"/documents/{session['doc_id']}/status")[1]["error_code"] == "INVALID_PDF"
    assert call(f"/documents/{session['doc_id']}/download")[0] == 409


def test_cursor_visits_all_results_without_duplicates_or_skips(services):
    for i in range(8):
        app.table.put_item(Item={"policy_id": f"p-{i}", "title_lower": "legal" if i % 2 else "other"})
    seen, cursor = [], None
    for _ in range(12):
        params = {"keyword": "legal", "limit": "1"}
        if cursor:
            params["next_token"] = cursor
        request = event("/policies")
        request["queryStringParameters"] = params
        response = app.lambda_handler(request, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        seen.extend(p["policy_id"] for p in body["policies"])
        cursor = body["next_token"]
        if not cursor:
            break
    else:
        pytest.fail("Pagination did not terminate")
    assert sorted(seen) == ["p-1", "p-3", "p-5", "p-7"]


@pytest.mark.parametrize("value", [[], None, {"bad": "key"}, {"policy_id": {}}, {"policy_id": ""}])
def test_invalid_cursor_shapes_are_rejected(services, value):
    cursor = base64.b64encode(json.dumps(value).encode()).decode()
    request = event("/policies")
    request["queryStringParameters"] = {"keyword": "legal", "next_token": cursor}
    assert app.lambda_handler(request, None)["statusCode"] == 400


def test_document_list_is_private_and_paginates(services):
    alice = [uploaded(services)["doc_id"] for _ in range(3)]
    call("/documents/upload-session", "POST", "bob")
    ids, cursor = [], None
    for _ in range(4):
        request = event("/documents")
        request["queryStringParameters"] = {"limit": "1", **({"next_token": cursor} if cursor else {})}
        response = app.lambda_handler(request, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        ids += [item["doc_id"] for item in body["documents"]]
        assert all("owner_sub" not in item and "s3_key" not in item for item in body["documents"])
        cursor = body["next_token"]
        if not cursor: break
    assert sorted(ids) == sorted(alice)
    assert call("/documents", owner=None)[0] == 401


def test_list_rejects_another_owners_cursor(services):
    cursor = base64.b64encode(json.dumps({"owner_sub": "bob", "created_at": "2026", "doc_id": "x"}).encode()).decode()
    request = event("/documents")
    request["queryStringParameters"] = {"next_token": cursor}
    assert app.lambda_handler(request, None)["statusCode"] == 400


def test_last_worker_failure_is_visible_and_retry_uses_a_new_attempt(services):
    session = uploaded(services)
    doc_id = session["doc_id"]
    call("/documents/submit", "POST", body={"doc_id": doc_id})
    old = app.document_table.get_item(Key={"doc_id": doc_id})["Item"]
    stale = {"messageId": "old-message", "body": json.dumps({"doc_id": doc_id, "submission_id": old["submission_id"]}),
             "attributes": {"ApproximateReceiveCount": "3"}}
    with patch.object(app, "_s3", side_effect=RuntimeError("offline service error")):
        assert app.worker_handler({"Records": [stale]}, None)["batchItemFailures"] == [{"itemIdentifier": "old-message"}]
    assert call(f"/documents/{doc_id}/status")[1]["status"] == "failed"
    assert call("/documents/submit", "POST", body={"doc_id": doc_id})[0] == 200
    new = app.document_table.get_item(Key={"doc_id": doc_id})["Item"]
    assert new["submission_id"] != old["submission_id"]
    assert new["version_id"] == old["version_id"]
    # Old failure deliveries cannot fail/process a new attempt.
    with patch.object(app, "_s3", side_effect=AssertionError("stale message touched storage")):
        app.worker_handler({"Records": [stale]}, None)
    assert call(f"/documents/{doc_id}/status")[1]["status"] == "pending"
    worker(doc_id)
    assert call(f"/documents/{doc_id}/status")[1]["status"] == "processed"


def test_recovery_requeues_pending_work_after_metadata_queue_gap(services):
    session = uploaded(services)
    doc_id = session["doc_id"]
    failing = Mock()
    failing.send_message.side_effect = ClientError({"Error": {"Code": "ServiceUnavailable"}}, "SendMessage")
    with patch.object(app.boto3, "client", return_value=failing), patch.object(app, "_s3", return_value=services):
        assert call("/documents/submit", "POST", body={"doc_id": doc_id})[0] == 503
    app.document_table.update_item(Key={"doc_id": doc_id}, UpdateExpression="SET dispatch_after = :due", ExpressionAttributeValues={":due": 0})
    assert app.recovery_handler({}, None)["recovered"] == 1
    assert app.recovery_handler({}, None)["recovered"] == 0
    import os
    queue = boto3.client("sqs", region_name="ap-southeast-1")
    records = queue.receive_message(QueueUrl=os.environ["DOCUMENT_QUEUE_URL"])["Messages"]
    assert len(records) == 1
    app.worker_handler({"Records": [{"messageId": records[0]["MessageId"], "body": records[0]["Body"]}]}, None)
    assert call(f"/documents/{doc_id}/status")[1]["status"] == "processed"
    assert "dispatch_after" not in app.document_table.get_item(Key={"doc_id": doc_id})["Item"]


def test_filename_is_display_metadata_not_a_storage_path(services):
    code, session = call("/documents/upload-session", "POST", body={"filename": "../../private.pdf"})
    assert code == 200
    item = app.document_table.get_item(Key={"doc_id": session["doc_id"]})["Item"]
    assert item["filename"] == "private.pdf"
    assert item["s3_key"].startswith("uploads/doc-")


def test_invalid_pdf_cannot_be_retried_as_a_transient_failure(services):
    session = uploaded(services)
    services.put_object(Bucket="document-tests", Key=session["s3_key"], Body=b"invalid", ContentType="application/pdf")
    call("/documents/submit", "POST", body={"doc_id": session["doc_id"]})
    worker(session["doc_id"])
    assert call("/documents/submit", "POST", body={"doc_id": session["doc_id"]})[0] == 409


def test_upload_policy_enforces_type_key_and_size_before_storage(services):
    _, session = call("/documents/upload-session", "POST")
    assert session["upload_method"] == "POST"
    policy = json.loads(base64.b64decode(session["upload_fields"]["policy"]))
    assert ["content-length-range", 5, app.MAX_DOCUMENT_BYTES] in policy["conditions"]
    assert {"Content-Type": "application/pdf"} in policy["conditions"]
    assert {"key": session["s3_key"]} in policy["conditions"]


@pytest.mark.parametrize("raw", ["null", "[]", "not-json", 42, {"x": "y"}, "x" * 16385])
@pytest.mark.parametrize("path", ["/documents/submit", "/documents/upload-session"])
def test_bad_json_bodies_never_write(services, raw, path):
    request = event(path, "POST")
    request["body"] = raw
    before = app.document_table.scan()["Count"]
    assert app.lambda_handler(request, None)["statusCode"] == 400
    assert app.document_table.scan()["Count"] == before


def test_mixed_batch_retries_only_failed_record_and_keeps_good_result(services):
    good = uploaded(services)["doc_id"]
    call("/documents/submit", "POST", body={"doc_id": good})
    item = app.document_table.get_item(Key={"doc_id": good})["Item"]
    response = app.worker_handler({"Records": [
        {"messageId": "bad-record", "body": "invalid-json"},
        {"messageId": "good-record", "body": json.dumps({"doc_id": good, "submission_id": item["submission_id"]})},
    ]}, None)
    assert response == {"batchItemFailures": [{"itemIdentifier": "bad-record"}]}
    assert call(f"/documents/{good}/status")[1]["status"] == "processed"


def test_failed_current_attempt_is_never_acknowledged_as_success(services):
    doc_id = uploaded(services)["doc_id"]
    call("/documents/submit", "POST", body={"doc_id": doc_id})
    item = app.document_table.get_item(Key={"doc_id": doc_id})["Item"]
    app._mark_failed(item, "PROCESSING_FAILED")
    assert worker(doc_id)["batchItemFailures"] == [{"itemIdentifier": "test-message"}]


def test_request_values_and_sdk_error_messages_are_not_logged(services, caplog):
    sentinel = "DO_NOT_LOG_THIS_VALUE"
    request = event("/policies")
    request["queryStringParameters"] = {"keyword": sentinel}
    with caplog.at_level("INFO"):
        app.lambda_handler(request, None)
        with patch.object(app.table, "scan", side_effect=ClientError({"Error": {"Code": "Unavailable", "Message": sentinel}}, "Scan")):
            assert app.lambda_handler(request, None)["statusCode"] == 500
    assert sentinel not in caplog.text


def test_base64_upload_session_and_invalid_id_validation(services):
    request = event("/documents/upload-session", "POST")
    request["body"] = base64.b64encode(json.dumps({"filename": "safe.pdf"}).encode()).decode()
    request["isBase64Encoded"] = True
    assert app.lambda_handler(request, None)["statusCode"] == 200
    assert call("/documents/submit", "POST", body={"doc_id": "x" * 129})[0] == 400
    assert call("/documents/" + "x" * 129 + "/status")[0] == 400


@pytest.mark.parametrize("error_code", ["403", "AccessDenied"])
def test_ambiguous_s3_head_denial_does_not_enqueue_or_transition(services, error_code):
    _, session = call("/documents/upload-session", "POST")
    storage = Mock()
    storage.head_object.side_effect = ClientError({"Error":{"Code":error_code,"Message":"sensitive detail"}}, "HeadObject")
    with patch.object(app, "_s3", return_value=storage):
        code, body = call("/documents/submit", "POST", body={"doc_id":session["doc_id"]})
    assert code == 503
    assert "sensitive detail" not in json.dumps(body)
    item = app.document_table.get_item(Key={"doc_id":session["doc_id"]})["Item"]
    assert item["status"] == "uploading"
    assert "submission_id" not in item
