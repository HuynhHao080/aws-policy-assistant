import base64
import io
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import boto3
import pytest
from pypdf import PdfWriter

from policy_assistant import app
from policy_assistant.service import Service
from tests.unit.test_documents import services, session, submit, event  # noqa: F401
from tests.unit.pdf_fixture import pdf_bytes


def request(path, method="GET", owner="alice", data=None, claims=None, params=None):
    payload = event(path, method, owner, json.dumps(data) if data is not None else None)
    payload["queryStringParameters"] = params or {}
    if path.startswith("/policies/"):
        payload["pathParameters"] = {"policy_id": path.split("/")[-1]}
    payload["requestContext"]["authorizer"]["jwt"]["claims"].update(claims or {})
    result = app.lambda_handler(payload, None)
    return result["statusCode"], json.loads(result["body"])


def run_worker(doc_id):
    return app.worker_handler({"Records": [{"messageId": "message-" + doc_id, "body": json.dumps({"doc_id": doc_id})}]}, None)


def ready(services):
    data = session(services)
    assert submit(data)[0] == 200
    assert run_worker(data["doc_id"]) == {"batchItemFailures": []}
    return data


def test_owner_document_listing_and_cursor_cannot_cross_accounts(services):
    first, second = session(services), session(services)
    code, page = request("/documents", params={"limit": "1"})
    assert code == 200 and len(page["documents"]) == 1 and page["next_token"]
    assert request("/documents", owner="bob")[1]["documents"] == []
    assert request("/documents", owner="bob", params={"next_token": page["next_token"]})[0] == 400
    next_page = request("/documents", params={"limit": "1", "next_token": page["next_token"]})[1]
    assert {page["documents"][0]["doc_id"], next_page["documents"][0]["doc_id"]} == {first["doc_id"], second["doc_id"]}


def test_presigned_upload_enforces_size_and_content_type(services):
    data = session(services, upload=False)
    assert data["upload_method"] == "POST"
    assert ".s3.ap-southeast-1.amazonaws.com" in data["upload_url"]
    policy = json.loads(base64.b64decode(data["upload_fields"]["policy"]))
    assert ["content-length-range", 1, 10 * 1024 * 1024] in policy["conditions"]
    assert {"Content-Type": "application/pdf"} in policy["conditions"]


def test_atomic_daily_and_monthly_limits(services, monkeypatch):
    monkeypatch.setenv("UPLOADS_PER_USER_DAY", "1")
    monkeypatch.setenv("UPLOADS_PER_MONTH", "2")
    assert request("/documents/upload-session", "POST")[0] == 200
    assert request("/documents/upload-session", "POST")[0] == 429
    assert request("/documents/upload-session", "POST", owner="bob")[0] == 200
    assert request("/documents/upload-session", "POST", owner="charlie")[0] == 429
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    usage = boto3.resource("dynamodb", region_name="ap-southeast-1").Table("TestUsage")
    assert usage.get_item(Key={"pk": f"global#upload#{month}"})["Item"]["count"] == 2


def test_selected_s3_version_is_immutable_and_deletion_purges_all_versions(services):
    data = session(services)
    assert submit(data)[0] == 200
    services[1].put_object(Bucket="test-policy-documents", Key=data["s3_key"], Body=pdf_bytes("Changed after submission."), ContentType="application/pdf")
    assert run_worker(data["doc_id"]) == {"batchItemFailures": []}
    doc = services[0].get_item(Key={"doc_id": data["doc_id"]})["Item"]
    source = services[1].get_object(Bucket="test-policy-documents", Key=doc["source_key"], VersionId=doc["source_version"])["Body"].read()
    assert source == pdf_bytes()
    assert request(f"/documents/{data['doc_id']}", "PATCH", data={"title": "New title"})[0] == 200
    assert request(f"/documents/{data['doc_id']}", "DELETE")[0] == 200
    assert request(f"/documents/{data['doc_id']}/download")[0] == 409
    assert run_worker(data["doc_id"]) == {"batchItemFailures": []}
    assert request(f"/documents/{data['doc_id']}/status")[0] == 404
    assert request("/documents")[1]["documents"] == []
    for prefix in (f"quarantine/{data['doc_id']}/", f"uploads/{data['doc_id']}/", f"documents/{data['doc_id']}/"):
        result = services[1].list_object_versions(Bucket="test-policy-documents", Prefix=prefix)
        assert not result.get("Versions") and not result.get("DeleteMarkers")


def test_invalid_pdf_is_failed_without_retrying_poison_file(services):
    data = session(services, upload=False)
    services[1].put_object(Bucket="test-policy-documents", Key=data["s3_key"], Body=b"Not a PDF", ContentType="application/pdf")
    assert submit(data)[0] == 200
    assert run_worker(data["doc_id"]) == {"batchItemFailures": []}
    assert request(f"/documents/{data['doc_id']}/status")[1]["error_code"] == "invalid_pdf"
    assert run_worker(data["doc_id"]) == {"batchItemFailures": []}


class FakeAI:
    def __init__(self, answer=None):
        self.answer = answer or {"answer": "Refunds must be requested within 30 days.", "sources": ["S1"]}
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("toolConfig"):
            return {"stopReason": "tool_use", "output": {"message": {"content": [{"toolUse": {"toolUseId": "test-answer", "name": "emit_policy_answer", "input": self.answer}}]}}}
        return {"output": {"message": {"content": [{"text": json.dumps(self.answer)}]}}}

    def invoke_model(self, **kwargs):
        payload = json.loads(kwargs["body"])
        return {"body": io.BytesIO(json.dumps({"embeddings": {"int8": [[1] * 1024 for _ in payload["texts"]]}}).encode())}


@pytest.fixture
def ai(services, monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "test-model")
    fake = FakeAI()
    service = Service(app.document_table, app.table)
    service._clients["bedrock-runtime"] = fake
    monkeypatch.setattr(app, "_service", lambda: service)
    return fake


def test_sourced_answer_and_history_are_owner_scoped(services, ai):
    data = ready(services)
    code, result = request("/ask", "POST", data={"question": "What is the refund deadline?", "document_ids": [data["doc_id"]]})
    assert code == 200 and result["grounded"] is True
    assert result["citations"][0]["doc_id"] == data["doc_id"] and result["citations"][0]["page"] == 1
    assert len(ai.calls) == 1
    prompt = json.loads(ai.calls[0]["messages"][0]["content"][0]["text"])
    assert len(prompt["source_data"]) <= 5
    assert request("/conversations")[1]["conversations"][0]["question"] == "What is the refund deadline?"
    assert request("/conversations", owner="bob")[1]["conversations"] == []
    assert request("/conversations/" + result["conversation_id"], "DELETE")[0] == 200
    assert request("/conversations")[1]["conversations"] == []


def test_other_user_document_ids_never_reach_model(services, ai):
    data = ready(services)
    assert request("/ask", "POST", owner="bob", data={"question": "Refund deadline?", "document_ids": [data["doc_id"]]})[0] == 404
    assert ai.calls == []


def test_semantic_search_finds_cross_language_source(services, ai, monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL_ID", "cohere.embed-multilingual-v3")
    data = ready(services)
    code, result = request("/ask", "POST", data={"question": "Tôi được hoàn tiền trong bao lâu?", "document_ids": [data["doc_id"]]})
    assert code == 200 and result["citations"][0]["doc_id"] == data["doc_id"]


@pytest.mark.parametrize("generated", [{"answer": "Claim", "sources": ["UNKNOWN"]}, {"answer": "Claim", "sources": "S1"}, {"sources": ["S1"]}])
def test_model_cannot_invent_citations(services, ai, generated):
    data = ready(services)
    ai.answer = generated
    assert request("/ask", "POST", data={"question": "Refund deadline?", "document_ids": [data["doc_id"]]})[0] == 502
    assert request("/conversations")[1]["conversations"] == []


def test_no_evidence_returns_refusal_without_model_call(services, ai):
    code, result = request("/ask", "POST", data={"question": "Unrelated topic"})
    assert code == 200 and result["grounded"] is False and result["citations"] == [] and ai.calls == []


@pytest.mark.parametrize("groups", [["administrators"], "[administrators]", '["administrators"]'])
def test_admin_policy_crud_and_audit(services, groups):
    policy = {"title": "Refund policy", "category": "Support", "content": "Refund within 30 days.", "keywords": ["refund"]}
    assert request("/admin/policies/POL-TEST", "PUT", data=policy)[0] == 403
    assert request("/admin/policies/POL-TEST", "PUT", data=policy, claims={"cognito:groups": groups})[0] == 200
    assert request("/admin/overview", claims={"cognito:groups": groups})[0] == 200
    assert request("/admin/audit", claims={"cognito:groups": groups})[1]["events"][0]["action"] == "policy.put"
    assert request("/admin/policies/POL-TEST", "DELETE", claims={"cognito:groups": groups})[0] == 200
    assert "Item" not in app.table.get_item(Key={"policy_id": "POL-TEST"})


def test_recovery_marks_exhausted_job_failed(services):
    data = session(services)
    old = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    services[0].update_item(Key={"doc_id": data["doc_id"]}, UpdateExpression="SET #s=:s, attempts=:n, updated_at=:old", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":s": "processing", ":n": 3, ":old": old})
    assert app.maintenance_handler({}, None)["recovered"] == 1
    assert request(f"/documents/{data['doc_id']}/status")[1]["status"] == "failed"


def blank_pdf(pages=1):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=600, height=800)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_ocr_job_polls_and_indexes_recognized_text(services, monkeypatch):
    data = session(services, upload=False)
    services[1].put_object(Bucket="test-policy-documents", Key=data["s3_key"], Body=blank_pdf(), ContentType="application/pdf")
    assert submit(data)[0] == 200
    service = Service(app.document_table, app.table)
    class Textract:
        running = True
        def start_document_text_detection(self, **kwargs):
            assert kwargs["DocumentLocation"]["S3Object"]["Version"]
            return {"JobId": "job-1"}
        def get_document_text_detection(self, **kwargs):
            return {"JobStatus": "IN_PROGRESS"} if self.running else {"JobStatus": "SUCCEEDED", "DocumentMetadata": {"Pages": 1}, "Blocks": [{"BlockType": "LINE", "Page": 1, "Text": "Refund within 30 days."}]}
    textract = Textract()
    service._clients["textract"] = textract
    monkeypatch.setattr(app, "_service", lambda: service)
    assert run_worker(data["doc_id"]) == {"batchItemFailures": []}
    assert request(f"/documents/{data['doc_id']}/status")[1]["status"] == "ocr_pending"
    assert run_worker(data["doc_id"]) == {"batchItemFailures": []}
    textract.running = False
    assert run_worker(data["doc_id"]) == {"batchItemFailures": []}
    doc = services[0].get_item(Key={"doc_id": data["doc_id"]})["Item"]
    assert doc["status"] == "processed" and doc["page_count"] == 1


def test_ocr_page_limit_prevents_unbounded_cost(services):
    data = session(services, upload=False)
    services[1].put_object(Bucket="test-policy-documents", Key=data["s3_key"], Body=blank_pdf(11), ContentType="application/pdf")
    assert submit(data)[0] == 200
    assert run_worker(data["doc_id"]) == {"batchItemFailures": []}
    assert request(f"/documents/{data['doc_id']}/status")[1]["error_code"] == "ocr_page_limit"


def test_account_deletion_blocks_access_and_removes_objects_history_and_identity(services, monkeypatch):
    data = ready(services)
    cognito = boto3.client("cognito-idp", region_name="ap-southeast-1")
    pool = cognito.create_user_pool(PoolName="TestAccounts")["UserPool"]["Id"]
    cognito.admin_create_user(UserPoolId=pool, Username="alice", MessageAction="SUPPRESS")
    monkeypatch.setenv("USER_POOL_ID", pool)
    history = boto3.resource("dynamodb", region_name="ap-southeast-1").Table("TestHistory")
    history.put_item(Item={"owner_id": "alice", "conversation_id": "test", "question": "private", "answer": "private"})
    assert request("/account/delete", "POST", data={})[0] == 400
    assert request("/account/delete", "POST", data={"confirmation": "DELETE"}, claims={"cognito:username": "alice"})[0] == 200
    job = services[0].get_item(Key={"doc_id": "account-alice"})["Item"]
    assert request("/account/delete", "POST", data={"confirmation": "DELETE"}, claims={"cognito:username": "alice"})[1]["status"] == "deleting"
    assert services[0].get_item(Key={"doc_id": "account-alice"})["Item"]["dispatch_id"] == job["dispatch_id"]
    assert request("/me")[0] == 410
    assert run_worker("account-alice") == {"batchItemFailures": []}
    assert request(f"/documents/{data['doc_id']}/status")[0] == 410
    assert history.query(KeyConditionExpression=boto3.dynamodb.conditions.Key("owner_id").eq("alice"))["Items"] == []
    with pytest.raises(cognito.exceptions.UserNotFoundException):
        cognito.admin_get_user(UserPoolId=pool, Username="alice")
    assert run_worker("account-alice") == {"batchItemFailures": []}


def test_public_registration_limits_are_atomic_and_admin_provisioning_bypasses_them(services):
    from policy_assistant.signup import handler
    usage = boto3.resource("dynamodb", region_name="ap-southeast-1").Table("TestUsage")
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    usage.put_item(Item={"pk": f"global#signup#{month}", "count": 99})
    usage.put_item(Item={"pk": "global#signup#lifetime", "count": 999})
    payload = {"triggerSource": "PreSignUp_SignUp", "response": {}}
    assert handler(payload, None) == payload
    with pytest.raises(ValueError, match="Registration"):
        handler(payload, None)
    assert usage.get_item(Key={"pk": f"global#signup#{month}"})["Item"]["count"] == 100
    assert usage.get_item(Key={"pk": "global#signup#lifetime"})["Item"]["count"] == 1000
    admin = {"triggerSource": "PreSignUp_AdminCreateUser", "response": {}}
    assert handler(admin, None) == admin


def test_unpublished_legacy_policies_do_not_become_customer_content(services, ai, monkeypatch):
    monkeypatch.setenv("REQUIRE_PUBLISHED_POLICIES", "true")
    app.table.put_item(Item={"policy_id": "SAMPLE", "title": "Legacy sample", "content": "Refund within 30 days.", "content_lower": "refund within 30 days."})
    assert request("/policies/SAMPLE")[0] == 404
    assert request("/policies", params={"keyword": "refund"})[1]["policies"] == []
    assert request("/ask", "POST", data={"question": "Refund deadline?"})[1]["grounded"] is False


def test_generation_routing_does_not_move_embedding_client(services, ai, monkeypatch):
    service = app._service()
    embedding_client = service.client("bedrock-runtime")
    monkeypatch.setenv("BEDROCK_GENERATION_REGION", "ap-northeast-1")
    generation = object()
    calls = []
    def make_client(name, **kwargs):
        calls.append((name, kwargs["region_name"]))
        return generation
    monkeypatch.setattr("policy_assistant.service.boto3.client", make_client)
    assert service.generation_client() is generation
    assert service.generation_client() is generation
    assert service.client("bedrock-runtime") is embedding_client
    assert calls == [("bedrock-runtime", "ap-northeast-1")]


def test_customer_cannot_raise_reasoning_budget_or_override_model(services, ai, monkeypatch):
    monkeypatch.setenv("BEDROCK_REASONING_EFFORT", "low")
    data = ready(services)
    code, result = request("/ask", "POST", data={"question": "Refund deadline?", "document_ids": [data["doc_id"]], "reasoning_effort": "high", "max_tokens": 65000, "model_id": "global.unapproved"})
    assert code == 200 and result["grounded"]
    call = ai.calls[0]
    assert call["modelId"] == "test-model"
    assert call["inferenceConfig"]["maxTokens"] == 2500
    assert call["additionalModelRequestFields"]["reasoningConfig"] == {"type": "enabled", "maxReasoningEffort": "low"}


def test_admin_publication_indexes_separate_clauses_with_context(services, ai, monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL_ID", "cohere.embed-multilingual-v3")
    content = "1. Lỗi sản phẩm được đề nghị kiểm tra.\n2. Đổi ý yêu cầu chưa mở hộp."
    policy = {"title": "Điều kiện mẫu", "category": "Thử nghiệm", "content": content, "keywords": ["đổi trả"]}
    code, _ = request("/admin/policies/SECTION-TEST", "PUT", data=policy, claims={"cognito:groups": ["administrators"]})
    assert code == 200
    item = app.table.get_item(Key={"policy_id": "SECTION-TEST"})["Item"]
    assert item["content"] == content and len(item["search_chunks"]) == 2
    assert all("Lỗi sản phẩm" in c["text"] and "chưa mở hộp" in c["text"] for c in item["search_chunks"])
    assert request("/policies/SECTION-TEST")[1].get("search_chunks") is None
