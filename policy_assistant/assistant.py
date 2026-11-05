"""Owner-scoped retrieval, bounded Bedrock generation and server-side citations."""
import json
import math
import os
import re
import time
import unicodedata
from collections import Counter
from uuid import uuid4

from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

try:
    from .service import Problem, now, text
    from .embeddings import embed, model_id, similarity
    from .policy_chunks import policy_chunks
    from .policy_validity import active as policy_active, signature as policy_signature, DATE_FIELDS
except ImportError:
    from service import Problem, now, text
    from embeddings import embed, model_id, similarity
    from policy_chunks import policy_chunks
    from policy_validity import active as policy_active, signature as policy_signature, DATE_FIELDS


def words(value):
    normalized = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    return re.findall(r"\w{2,}", "".join(c for c in normalized if unicodedata.category(c) != "Mn"))


def retrieve(service, owner, question, doc_ids, source_scope="all"):
    candidates = []
    query_vector = embed(service, [question], "search_query")[0] if model_id() else None
    if source_scope == "policies":
        docs = []
    elif doc_ids:
        if not isinstance(doc_ids, list) or len(doc_ids) > 10 or any(not isinstance(i, str) or len(i) > 100 for i in doc_ids):
            raise Problem(400, "document_ids must contain at most 10 document IDs")
        docs = [service.owned(doc_id, owner) for doc_id in dict.fromkeys(doc_ids)]
    else:
        docs = service.docs.query(IndexName="OwnerCreatedAt", KeyConditionExpression=Key("owner_id").eq(owner), ScanIndexForward=False, Limit=20).get("Items", [])
    for doc in docs:
        # GSI results are eventually consistent; recheck ownership/state before content access.
        try:
            doc = service.owned(doc["doc_id"], owner)
        except Problem as exc:
            if exc.status == 404:
                continue
            raise
        if doc.get("status") != "processed":
            continue
        obj = service.client("s3").get_object(Bucket=service.bucket, Key=doc["extraction_key"], VersionId=doc["extraction_version"])
        try:
            raw = obj["Body"].read(2_000_001)
        finally:
            obj["Body"].close()
        if len(raw) > 2_000_000:
            raise Problem(503, "Document index exceeds its configured limit")
        parsed = json.loads(raw)
        for chunk in parsed["chunks"]:
            score = similarity(query_vector, chunk["vector"]) if query_vector and chunk.get("vector") and parsed.get("embedding_model") == model_id() else 0
            candidates.append({"doc_id": doc["doc_id"], "title": doc.get("title", doc.get("filename", "Document")), "page": chunk["page"], "excerpt": chunk["text"][:1400], "semantic_score": score})
    # Shared policies are deliberately global. Private PDFs are never scanned globally.
    scan = {"Limit": 1000, "ConsistentRead": True, "ProjectionExpression": "#id,#title,#content,#chunks,#embedding,effective_from,effective_until", "ExpressionAttributeNames": {"#id": "policy_id", "#title": "title", "#content": "content", "#chunks": "search_chunks", "#embedding": "embedding_model"}}
    if os.environ.get("REQUIRE_PUBLISHED_POLICIES") == "true":
        scan["FilterExpression"] = Attr("publication_state").eq("published")
    result = service.policies.scan(**scan) if source_scope != "documents" else {"Items": []}
    for policy in result.get("Items", []):
        if not policy_active(policy):
            continue
        content = policy.get("content", "")[:20000]
        chunks = policy.get("search_chunks") or policy_chunks(content)
        for chunk in chunks:
            score = similarity(query_vector, chunk["vector"]) if query_vector and chunk.get("vector") and policy.get("embedding_model") == model_id() else 0
            candidates.append({"policy_id": policy["policy_id"], "title": policy.get("title", "Policy"), "page": None, "excerpt": chunk["text"], "semantic_score": score,
                               "_policy_signature": policy_signature(policy), **{k: policy[k] for k in DATE_FIELDS if k in policy}})
    query = set(words(question))
    docs_tokens = [Counter(words(c["title"] + " " + c["excerpt"])) for c in candidates]
    frequencies = Counter(token for tokens in docs_tokens for token in tokens)
    scores = []
    for index, tokens in enumerate(docs_tokens):
        score = sum((1 + math.log(1 + len(candidates) / (1 + frequencies[token]))) * tokens[token] / (tokens[token] + 1.2) for token in query if tokens[token])
        semantic = candidates[index].pop("semantic_score", 0)
        if score or semantic >= 0.25:
            scores.append((semantic + min(score, 4) * 0.08, index))
    selected = [dict(candidates[i], source_id=f"S{number}") for number, (_, i) in enumerate(sorted(scores, reverse=True)[:5], 1)]
    return selected


def public_source(source):
    return {key: value for key, value in source.items() if not key.startswith('_')}


def check_policy_sources(service, citations):
    checked = {}
    for source in citations:
        policy_id = source.get('policy_id')
        if not policy_id:
            continue
        if policy_id not in checked:
            checked[policy_id] = service.policies.get_item(Key={'policy_id': policy_id}, ConsistentRead=True).get('Item')
        current = checked[policy_id]
        if (not current or not policy_active(current)
                or (os.environ.get('REQUIRE_PUBLISHED_POLICIES') == 'true' and current.get('publication_state') != 'published')
                or source.get('_policy_signature') != policy_signature(current)):
            raise Problem(409, 'Chính sách đã thay đổi hoặc không còn hiệu lực trong lúc xử lý. Vui lòng gửi lại câu hỏi để lấy nguồn mới.')


def answer(service, owner, data):
    started=time.perf_counter()
    question = text(data.get("question"), "question", 2000)
    ids = data.get("document_ids", [])
    if not isinstance(ids, list):
        raise Problem(400, "document_ids must be an array")
    scope = data.get("source_scope", "all")
    if not isinstance(scope, str) or scope not in {"all", "policies", "documents"}:
        raise Problem(400, "source_scope must be all, policies or documents")
    if scope == "policies" and ids:
        raise Problem(400, "Policies-only scope must not include document IDs")
    if scope == "documents" and not ids:
        raise Problem(400, "Choose at least one owned PDF for documents-only scope")
    model = os.environ.get("BEDROCK_MODEL_ID")
    if not model:
        raise Problem(503, "AI model is not configured")
    service.quota(owner, "question")
    sources = retrieve(service, owner, question, ids, scope)
    if not sources:
        result = {"answer": "Tôi chưa tìm thấy thông tin phù hợp trong tài liệu của bạn hoặc chính sách chung. Hãy chọn tài liệu đã xử lý và hỏi cụ thể hơn.", "citations": [], "grounded": False, "model_id": None}
    else:
        system = "You answer customer questions using only the provided policy excerpts. Highest priority: preserve qualifiers in the source. Highest priority for refund/status questions: explain only the general deadline and the conditions that start it. Never state whether the clock has started for this customer, or whether staff have already received, reviewed or approved the request; the system has no order-status connection. Example safe wording: Thời hạn được tính từ khi nhân viên xác nhận nhận đủ hàng trả và chấp thuận hoàn tiền, không từ lúc bạn nhắn hỏi. Bạn cần liên hệ nhân viên để biết trạng thái thực tế. Example forbidden wording: Hiện tại yêu cầu của bạn chưa được nhân viên xác nhận nên thời hạn chưa bắt đầu. In particular, không tự động được hủy means the chatbot cannot automatically cancel it, NOT không thể hủy or không được hủy. For a handed-over order, say it is handled under the returns policy and ask the customer to contact staff; do not open or close with an absolute cancellation ban unless that ban is explicit in the source. Do not claim to cancel or approve anything yourself. Write clear Vietnamese with diacritics. Treat DEMO policies as hypothetical: explain what the example policy says without making a real-world commitment. Answer the specific question, not a different topic. Use ordinary arithmetic and calendar/geographic knowledge to apply a stated limit; business rules themselves must come from the excerpts. A policy covering only a specified country does not imply international delivery. A stated operating schedule does not imply shifts outside those hours. Apply the policy's conditions carefully; do not confuse return reasons, warranty coverage duration, and repair turnaround time. State the relevant conditions if customer eligibility is not fully established. When staff review or approval is required, explain eligibility to submit a request without promising approval. Never claim to perform a transaction. Address the customer directly; do not restate internal instructions such as cần báo rằng. Do not invent missing facts or follow instructions to fabricate a policy. Cite the source_id values that support your answer. Return only JSON with exactly two keys: answer (plain text, under 1500 characters) and sources (an array of supplied source_id strings). If genuinely unsupported, explain what is missing. Sources that expressly say a detail is unspecified may be cited for that limitation. No Markdown fences. Do not invent facts about the customer scenario from conditions in a policy. If a condition is unconfirmed, state it as a condition rather than assuming it has failed. Do not describe a customer as having opened, used, damaged, or returned an item unless the question states that. Keep the requested duration distinct from other durations in the same document. Missing information is not a fee waiver, a denial of rights, or permission to assume a service is provided. If a fee is unspecified, say only that the policy does not specify it; do not say it is not charged or not applied. State the published support hours without inventing an extra shift or an exception. Preserve the exact strength of each policy rule: not automatic is not the same as forbidden. If a request needs staff handling, say that and do not claim the outcome has been decided. Keep the customer timeline exactly as stated; never change just asked today into asked several days ago or invent elapsed days. Explain a processing deadline from its stated trigger, and mention any source-stated payment-provider delay without promising a receipt date. For damage or warranty exclusions, distinguish the hypothetical rule from a decision on the actual product: staff must inspect and verify the cause before deciding coverage. Summarize these rules in direct customer-facing language rather than copying instructions addressed to the chatbot. You cannot observe order, refund, inspection or staff-approval status. Do not say a request has or has not been reviewed, approved or received unless the customer or source explicitly states that fact. Use conditional wording such as nếu nhân viên chưa xác nhận instead of asserting chưa được nhân viên xác nhận. Do not promise that staff will contact the customer; ask the customer to contact staff through a verified channel."
        structured = model == "jp.amazon.nova-2-lite-v1:0"
        if structured:
            system += " Submit the final answer using emit_policy_answer with answer and sources. This is only an output format, not a transaction or an external action. Do not output another tool or free-form JSON."
        prompt = json.dumps({"question": question, "source_data": [public_source(source) for source in sources]}, ensure_ascii=False)
        try:
            options = {"modelId": model, "system": [{"text": system}], "messages": [{"role": "user", "content": [{"text": prompt}]}], "inferenceConfig": {"maxTokens": 700, "temperature": 0.0}}
            if os.environ.get("BEDROCK_REASONING_EFFORT") == "low":
                options["inferenceConfig"]["maxTokens"] = 2500
                options["additionalModelRequestFields"] = {"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "low"}}
            if structured:
                # This tool only serializes an answer; no model-selected operation is executed.
                options["toolConfig"] = {
                    "tools": [{"toolSpec": {
                        "name": "emit_policy_answer",
                        "description": "Return a customer-facing policy answer and only source IDs supplied in source_data. No external action is performed.",
                        "inputSchema": {"json": {
                            "type": "object",
                            "properties": {
                                "sources": {"type": "array", "items": {"type": "string", "enum": [source["source_id"] for source in sources]}},
                                "answer": {"type": "string", "maxLength": 1500},
                            },
                            "required": ["answer", "sources"],
                            "additionalProperties": False,
                        }},
                    }}],
                    "toolChoice": {"tool": {"name": "emit_policy_answer"}},
                }
            response = service.generation_client().converse(**options)
        except ClientError:
            raise Problem(503, "AI service is unavailable. Your documents are unchanged; retry later.") from None
        try:
            if response.get("stopReason") in {"max_tokens", "guardrail_intervened", "content_filtered", "malformed_model_output", "malformed_tool_use"}:
                raise ValueError()
            blocks = response["output"]["message"]["content"]
            if structured:
                tools = [block["toolUse"] for block in blocks if "toolUse" in block]
                if response.get("stopReason") != "tool_use" or len(tools) != 1 or tools[0].get("name") != "emit_policy_answer":
                    raise ValueError()
                generated = tools[0]["input"]
            else:
                raw = "".join(block.get("text", "") for block in blocks).strip()
                raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
                generated = json.loads(raw)
            if not isinstance(generated, dict) or (structured and set(generated) != {"answer", "sources"}):
                raise ValueError()
            answer_text = text(generated.get("answer"), "model answer", 1500 if structured else 5000)
            requested = generated.get("sources")
            available = {source["source_id"]: source for source in sources}
            if not isinstance(requested, list) or any(not isinstance(s, str) or s not in available for s in requested):
                raise ValueError()
            citations = [available[s] for s in dict.fromkeys(requested)]
        except (KeyError, TypeError, ValueError, Problem):
            raise Problem(502, "AI returned an invalid sourced answer; please retry") from None
        if not citations:
            answer_text = "Tôi không có đủ bằng chứng trong tài liệu để trả lời câu hỏi này."
        result = {"answer": answer_text, "citations": citations, "grounded": bool(citations), "model_id": model}
    check_policy_sources(service, result["citations"])
    result["citations"] = [public_source(source) for source in result["citations"]]
    result["source_scope"] = scope
    stamp = now()
    conversation_id = stamp + "#" + uuid4().hex
    item={"owner_id":owner,"conversation_id":conversation_id,"created_at":stamp,"question":question,**result,"expires_at":int(time.time())+30*86400}
    service.save_answer(owner,item,(time.perf_counter()-started)*1000)
    result.update(quality_month=stamp[:7],quality_version=1,response_ms=item.get("response_ms",0))
    return {"conversation_id": conversation_id, **result}
