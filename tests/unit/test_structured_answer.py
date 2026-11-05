"""Validate model output before private history is persisted."""
import pytest
from tests.unit.test_public_app import services, ai, ready, request  # noqa: F401


def response(value, name="emit_policy_answer", stop="tool_use", duplicate=False):
    block={"toolUse":{"toolUseId":"answer-1","name":name,"input":value}}
    return {"stopReason":stop,"output":{"message":{"content":[block,block] if duplicate else [block]}}}


def test_structured_output_only_allows_retrieved_sources_and_saves_valid_answer(services, ai, monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID","jp.amazon.nova-2-lite-v1:0")
    data=ready(services)
    code,result=request("/ask","POST",data={"question":"Refund deadline?","document_ids":[data["doc_id"]]})
    assert code==200 and result["grounded"] and result["citations"][0]["doc_id"]==data["doc_id"]
    config=ai.calls[-1]["toolConfig"]
    assert len(config["tools"])==1 and "systemTool" not in config["tools"][0]
    assert config["toolChoice"]=={"tool":{"name":"emit_policy_answer"}}
    allowed=config["tools"][0]["toolSpec"]["inputSchema"]["json"]["properties"]["sources"]["items"]["enum"]
    assert allowed and all(source.startswith("S") for source in allowed)
    assert request("/conversations")[1]["conversations"][0]["answer"]==result["answer"]


@pytest.mark.parametrize("output",[
    response({"answer":"Claim","sources":["UNKNOWN"]}),
    response({"answer":"Claim","sources":["S1"]},name="delete_account"),
    response({"answer":"Claim","sources":["S1"]},duplicate=True),
    response({"answer":"Claim","sources":["S1"]},stop="max_tokens"),
    response({"answer":"Claim","sources":["S1"],"operation":"refund"}),
    response(["unexpected array"]),
    response({"sources":["S1"]}),
    response({"answer":"a"*1501,"sources":["S1"]}),
    {"stopReason":"end_turn","output":{"message":{"content":[{"text":'{"answer":"Claim","sources":["S1"]}'}]}}},
])
def test_invalid_or_unexpected_model_output_is_rejected_without_history(services, ai, monkeypatch, output):
    monkeypatch.setenv("BEDROCK_MODEL_ID","jp.amazon.nova-2-lite-v1:0")
    data=ready(services)
    monkeypatch.setattr(ai,"converse",lambda **kwargs:output)
    code,result=request("/ask","POST",data={"question":"Refund deadline?","document_ids":[data["doc_id"]]})
    assert code==502 and result["error"]=="Bad gateway"
    assert "invalid sourced answer" in result["message"]
    assert request("/conversations")[1]["conversations"]==[]
