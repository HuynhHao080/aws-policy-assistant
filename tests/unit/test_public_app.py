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


def test_document_text_is_owner_only_and_reads_the_pinned_extraction(services):
    data = ready(services)
    doc_id = data["doc_id"]
    item = services[0].get_item(Key={"doc_id": doc_id})["Item"]
    services[1].put_object(Bucket="test-policy-documents", Key=item["extraction_key"],
                           Body=json.dumps({"pages": 1, "chunks": [{"page": 1, "text": "Later object version"}]}))
    route = f"/documents/{doc_id}/text"
    code, result = request(route)
    assert code == 200 and result["page"] == result["page_count"] == 1
    assert "Refund requests" in result["chunks"][0] and "Later object version" not in result["chunks"]
    assert set(result) == {"doc_id", "title", "page", "page_count", "chunks", "truncated"}
    assert request(route, owner="bob", claims={"cognito:groups": ["administrators"]})[0] == 404
    assert request(route, params={"page": "2"})[0] == 400
    assert request(route, params={"page": "-1"})[0] == 400
    response = app.lambda_handler(event(route, user=None), None)
    assert response["statusCode"] == 401


def test_document_text_limits_large_pages_and_preserves_empty_pages(services):
    data = ready(services)
    doc_id = data["doc_id"]
    table, s3, *_ = services
    key = f"documents/{doc_id}/extraction.json"
    extracted = {"pages": 2, "chunks": [{"page": 1, "text": "A" * 1400} for _ in range(16)]}
    version = s3.put_object(Bucket="test-policy-documents", Key=key, Body=json.dumps(extracted))["VersionId"]
    table.update_item(Key={"doc_id": doc_id}, UpdateExpression="SET extraction_version=:v", ExpressionAttributeValues={":v": version})
    code, first = request(f"/documents/{doc_id}/text")
    assert code == 200 and first["truncated"] and sum(map(len, first["chunks"])) == 20_000
    code, second = request(f"/documents/{doc_id}/text", params={"page": "2"})
    assert code == 200 and second["chunks"] == [] and not second["truncated"]
    assert request("/documents/" + session(services)["doc_id"] + "/text")[0] == 409


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
        return {"stopReason": "tool_use", "output": {"message": {"content": [{"toolUse": {"toolUseId": "test-answer", "name": "emit_policy_answer", "input": self.answer}}]}}}

    def invoke_model(self, **kwargs):
        pytest.fail("The application must not call an embedding model")


@pytest.fixture
def ai(services, monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", 'global.anthropic.claude-haiku-5-5')
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


def test_followup_uses_previous_question_and_fresh_scoped_sources(services, ai):
    doc = ready(services)
    status, original = request("/ask", "POST", data={"question": "Refund deadline?"})
    assert status == 200
    followup = {
        "question": "And how long?",
        "context_conversation_id": original["conversation_id"],
        "source_scope": "documents",
        "document_ids": [doc["doc_id"]],
    }
    status, result = request("/ask", "POST", data=followup)
    assert status == 200
    assert result["conversation_id"] != original["conversation_id"]
    prompt = json.loads(ai.calls[-1]["messages"][0]["content"][0]["text"])
    assert set(prompt) == {"question", "previous_question", "source_data"}
    assert prompt["previous_question"] == "Refund deadline?"
    assert prompt["question"] == "And how long?"
    assert prompt["source_data"]
    assert all(source["doc_id"] == doc["doc_id"] for source in prompt["source_data"])


def test_unavailable_followup_context_never_reaches_model(services, ai):
    table = app._service().table("HISTORY_TABLE_NAME")
    table.put_item(Item={
        "owner_id": "alice", "conversation_id": "prior", "question": "Refund deadline?",
        "expires_at": int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp()),
    })
    data = {"question": "And how long?", "context_conversation_id": "prior"}
    assert request("/ask", "POST", owner="bob", data=data)[0] == 404
    table.update_item(
        Key={"owner_id": "alice", "conversation_id": "prior"},
        UpdateExpression="SET expires_at = :expired",
        ExpressionAttributeValues={":expired": 1},
    )
    assert request("/ask", "POST", data=data)[0] == 404
    assert request("/conversations/prior", "DELETE")[0] == 200
    assert request("/ask", "POST", data=data)[0] == 404
    assert request("/ask", "POST", data={**data, "context_conversation_id": None})[0] == 400
    assert ai.calls == []


def test_other_user_document_ids_never_reach_model(services, ai):
    data = ready(services)
    assert request("/ask", "POST", owner="bob", data={"question": "Refund deadline?", "document_ids": [data["doc_id"]]})[0] == 404
    assert ai.calls == []


def test_lexical_search_maps_refund_terms(services, ai):
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


def test_generation_client_uses_stack_region_and_disables_automatic_retries(services, monkeypatch):
    service = Service(app.document_table, app.table)
    generation = object()
    calls = []
    def make_client(name, **kwargs):
        calls.append((name, kwargs["region_name"], kwargs["config"].retries))
        return generation
    monkeypatch.setattr("policy_assistant.service.boto3.client", make_client)
    assert service.generation_client() is generation
    assert service.generation_client() is generation
    assert calls == [("bedrock-runtime", service.region, {"total_max_attempts": 1})]


def test_customer_cannot_raise_reasoning_budget_or_override_model(services, ai, monkeypatch):
    data = ready(services)
    code, result = request("/ask", "POST", data={"question": "Refund deadline?", "document_ids": [data["doc_id"]], "reasoning_effort": "high", "max_tokens": 65000, "model_id": "global.unapproved"})
    assert code == 200 and result["grounded"]
    call = ai.calls[0]
    assert call["modelId"] == 'global.anthropic.claude-haiku-5-5'
    assert call["inferenceConfig"]["maxTokens"] == 900
    assert call["additionalModelRequestFields"]["thinking"] == {"type": "disabled"}


def test_admin_publication_indexes_separate_clauses_with_context(services, ai):
    content = "1. Lỗi sản phẩm được đề nghị kiểm tra.\n2. Đổi ý yêu cầu chưa mở hộp."
    policy = {"title": "Điều kiện mẫu", "category": "Thử nghiệm", "content": content, "keywords": ["đổi trả"]}
    code, _ = request("/admin/policies/SECTION-TEST", "PUT", data=policy, claims={"cognito:groups": ["administrators"]})
    assert code == 200
    item = app.table.get_item(Key={"policy_id": "SECTION-TEST"})["Item"]
    assert item["content"] == content and "search_chunks" not in item and "embedding_model" not in item
    code, result = request("/ask", "POST", data={"question": "Đổi ý mở hộp?", "source_scope":"policies"})
    assert code == 200 and "chưa mở hộp" in result["citations"][0]["excerpt"]
    assert request("/policies/SECTION-TEST")[1].get("search_chunks") is None


def test_ask_from_exact_policy_excludes_other_sources_and_checks_availability(services, ai):
    for policy_id, state in (("SELECTED", "published"), ("OTHER", "published"), ("DRAFT", "draft")):
        app.table.put_item(Item={
            "policy_id": policy_id, "title": policy_id, "content": "Refund eligibility and deadline.",
            "publication_state": state,
        })
    app.table.put_item(Item={
        "policy_id": "EXPIRED", "title": "Expired", "content": "Refund eligibility.",
        "publication_state": "published", "effective_until": "2000-01-01",
    })
    payload = {"question": "Refund deadline?", "source_scope": "policies", "policy_id": "SELECTED"}
    status, result = request("/ask", "POST", data=payload)
    assert status == 200 and result["source_policy_id"] == "SELECTED"
    assert result["source_policy_title"] == "SELECTED"
    prompt = json.loads(ai.calls[0]["messages"][0]["content"][0]["text"])
    assert {source["policy_id"] for source in prompt["source_data"]} == {"SELECTED"}
    assert request("/conversations")[1]["conversations"][0]["source_policy_id"] == "SELECTED"
    for policy_id in ("DRAFT", "EXPIRED", "MISSING"):
        assert request("/ask", "POST", data={**payload, "policy_id": policy_id})[0] == 404
    for invalid in ({"source_scope": "all"}, {"policy_id": "../OTHER"}, {"document_ids": ["pdf"]}):
        assert request("/ask", "POST", data={**payload, **invalid})[0] == 400
    assert len(ai.calls) == 1


def test_ask_retrieves_policy_after_first_dynamodb_page(services, ai, monkeypatch):
    from policy_assistant import assistant

    monkeypatch.setattr(assistant, "MAX_POLICY_PAGE_ITEMS", 1)
    monkeypatch.setenv("REQUIRE_PUBLISHED_POLICIES", "true")
    for policy_id, text, state in (
        ("A-DRAFT", "Private sapphire refund.", "draft"),
        ("B-OTHER", "Office hours and delivery.", "published"),
        ("C-REFUND", "Sapphire refund requests are accepted within seven days.", "published"),
    ):
        app.table.put_item(Item={"policy_id": policy_id, "title": policy_id, "content": text, "publication_state": state})
    code, result = request("/ask", "POST", data={"question": "Sapphire refund?", "source_scope": "policies"})
    assert code == 200 and result["citations"][0]["policy_id"] == "C-REFUND"
    sources = json.loads(ai.calls[0]["messages"][0]["content"][0]["text"])["source_data"]
    assert all("_section_text" not in source for source in sources)
    assert all(source["policy_id"] != "A-DRAFT" for source in sources)


def test_general_retrieval_does_not_generate_from_a_truncated_policy_catalogue(services, ai, monkeypatch):
    from policy_assistant import assistant

    monkeypatch.setattr(assistant, "MAX_POLICY_PAGE_ITEMS", 1)
    monkeypatch.setattr(assistant, "MAX_POLICY_SCAN_PAGES", 1)
    for policy_id in ("A", "B"):
        app.table.put_item(Item={
            "policy_id": policy_id, "title": policy_id, "content": "Refund deadline.", "publication_state": "published",
        })
    assert request("/ask", "POST", data={"question": "Refund?", "source_scope": "policies"})[0] == 503
    assert ai.calls == []
    code, result = request("/ask", "POST", data={"question": "Refund?", "source_scope": "policies", "policy_id": "B"})
    assert code == 200 and result["source_policy_id"] == "B"


def test_evidence_ranks_matching_section_above_neighbouring_context():
    from policy_assistant.assistant import rank_evidence

    excerpt = "Bảo hành củ sạc 12 tháng. Thời gian sửa chữa từ 7 đến 15 ngày."
    candidates = [
        {"policy_id":"WARRANTY","title":"Bảo hành", "excerpt":excerpt, "_section_text":"Bảo hành củ sạc 12 tháng."},
        {"policy_id":"WARRANTY","title":"Bảo hành", "excerpt":excerpt, "_section_text":"Thời gian sửa chữa từ 7 đến 15 ngày."},
    ]
    sources = rank_evidence(candidates, "Thời gian sửa chữa là bao nhiêu ngày?", "Bảo hành củ sạc bao lâu?")
    assert sources[0]["_section_text"] == candidates[1]["_section_text"]
    assert sources[0]["excerpt"] == excerpt


def test_demo_retrieval_retains_expected_sources_for_all_thirty_questions():
    import csv
    from pathlib import Path
    from types import SimpleNamespace

    from policy_assistant.assistant import retrieve

    fixtures = Path(__file__).resolve().parents[2] / "docs" / "retail-pilot"
    policies = json.loads((fixtures / "du-lieu-demo.json").read_text(encoding="utf8"))
    service = SimpleNamespace(policies=SimpleNamespace(scan=lambda **_: {"Items": policies}))
    misses = []
    first_matches = 0
    with (fixtures / "30-CAU-HOI-KIEM-THU.csv").open(encoding="utf-8-sig", newline="") as csv_file:
        cases = list(csv.reader(csv_file))[1:]
    assert len(cases) == 30
    for number, _, question, _, labels, *_ in cases:
        expected = {f"DEMO-SHOP-{label}-001" for label in labels.split(",")}
        actual = [source["policy_id"] for source in retrieve(service, "fixture", question, [], "policies")]
        if not expected.intersection(actual):
            misses.append(number)
        first_matches += bool(expected.intersection(actual[:1]))
    assert misses == []
    assert first_matches >= 28
