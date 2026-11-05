"""Offline shape/invariance tests; no CloudFormation/AWS calls."""
import copy
import json
from pathlib import Path

import pytest

from policy_assistant import ai
from scripts import prepare_ai_infrastructure as prepare

ROOT = Path(__file__).parents[2]


def baseline():
    resources = {name: {"Type": "AWS::Lambda::Function", "Properties": {
        "Code": {"S3Bucket": "synthetic-deployment", "S3Key": name + ".zip"},
        "Handler": "app.lambda_handler", "Environment": {"Variables": {"DOCUMENTS_BUCKET_NAME": "synthetic-documents"}}}}
        for name in prepare.EXISTING_FUNCTIONS}
    resources["PolicyAssistantApi"] = {"Type": "AWS::ApiGatewayV2::Api", "Properties": {"Body": {
        "paths": {"/policies": {"get": {"security": [{"PolicyAssistantAuthorizer": []}]}}},
        "components": {"securitySchemes": {"PolicyAssistantAuthorizer": {"x-amazon-apigateway-authorizer": {
            "type": "jwt", "jwtConfiguration": {"issuer": "synthetic-issuer", "audience": ["synthetic-client"]}}}}},
        "x-amazon-apigateway-cors": {"allowHeaders": ["Content-Type", "Authorization"], "allowOrigins": ["https://synthetic.invalid"]}}}}
    resources["PolicyAssistantApiProdStage"] = {"Type": "AWS::ApiGatewayV2::Stage", "Properties": {
        "StageName": "Prod", "ApiId": {"Ref": "PolicyAssistantApi"}, "DefaultRouteSettings": {
            "ThrottlingRateLimit": 10, "ThrottlingBurstLimit": 5}}}
    return {"Resources": resources}


def fragment():
    return json.loads((ROOT / "infra/ai-off-fragment.json").read_text())


def test_existing_lambdas_and_routes_are_preserved():
    before = baseline(); snapshot = copy.deepcopy(before); after = prepare.candidate(before)
    assert before == snapshot
    for name in prepare.EXISTING_FUNCTIONS:
        assert before["Resources"][name] == after["Resources"][name]
    original = before["Resources"]["PolicyAssistantApi"]["Properties"]["Body"]
    changed = after["Resources"]["PolicyAssistantApi"]["Properties"]["Body"]
    assert changed["paths"]["/policies"] == original["paths"]["/policies"]
    assert changed["components"] == original["components"]
    assert changed["x-amazon-apigateway-cors"]["allowOrigins"] == original["x-amazon-apigateway-cors"]["allowOrigins"]
    assert changed["paths"]["/ai/ask"]["post"]["security"] == [{"PolicyAssistantAuthorizer": []}]
    assert "Idempotency-Key" in changed["x-amazon-apigateway-cors"]["allowHeaders"]
    assert after["Resources"]["PolicyAssistantApiProdStage"]["Properties"]["DefaultRouteSettings"] == {
        "ThrottlingRateLimit": 10, "ThrottlingBurstLimit": 5}


@pytest.mark.parametrize("bad", ["globals", "local_code", "route_exists", "authorizer", "collision"])
def test_builder_rejects_unsafe_or_unexpected_baselines(bad):
    b = baseline()
    if bad == "globals": b["Globals"] = {"Function": {"Environment": {"Variables": {"SECRET": "synthetic"}}}}
    if bad == "local_code": b["Resources"]["PolicyAssistantFunction"]["Properties"]["Code"] = {"ZipFile": "synthetic"}
    if bad == "route_exists": b["Resources"]["PolicyAssistantApi"]["Properties"]["Body"]["paths"]["/ai/ask"] = {}
    if bad == "authorizer": b["Resources"]["PolicyAssistantApi"]["Properties"]["Body"]["components"]["securitySchemes"]["PolicyAssistantAuthorizer"]["x-amazon-apigateway-authorizer"]["type"] = "request"
    if bad == "collision": b["Resources"]["AIQuotaTable"] = {}
    with pytest.raises(ValueError): prepare.candidate(b)


def test_off_is_locked_and_cannot_select_actual_subjects_or_model_permissions():
    f = fragment()
    for key, only in [("AIFeatureEnabled", "false"), ("AIApprovedSubjects", ""),
                      ("AIApprovedPolicyManifest", "{}"), ("AIBedrockPermissionApproval", "PENDING")]:
        assert f["Parameters"][key]["Default"] == only
        assert f["Parameters"][key]["AllowedValues"] == [only]
    assert f["Resources"]["AIBedrockPolicy"]["Condition"] == "AIBedrockPermissionApproved"
    assert f["Conditions"]["AIBedrockPermissionApproved"] == {"Fn::Equals": [{"Ref": "AIBedrockPermissionApproval"}, "APPROVED"]}


def test_native_lambda_has_no_inherited_document_config_or_reserved_concurrency():
    f = fragment()["Resources"]["AIFunction"]
    assert f["Type"] == "AWS::Lambda::Function"
    props = f["Properties"]
    assert "ReservedConcurrentExecutions" not in props
    assert props["Handler"] == "ai.lambda_handler" and props["Timeout"] == 15
    assert set(props["Environment"]["Variables"]) == {
        "AI_ENABLED", "AI_ALLOWED_SUBS", "AI_POLICY_MANIFEST", "AI_QUOTA_TABLE", "POLICIES_TABLE_NAME", "AI_MODEL_PROFILE"}


def test_role_actions_scope_and_transaction_only_ledger():
    f = fragment()["Resources"]
    statements = f["AIRole"]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]
    actions = {a for s in statements for a in s["Action"]}
    assert actions == {"logs:CreateLogStream", "logs:PutLogEvents", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"}
    assert all(s["Resource"] != "*" for s in statements)
    assert statements[1]["Condition"]["ForAllValues:StringEquals"]["dynamodb:LeadingKeys"] == ["POL-001", "POL-002", "POL-003"]
    assert statements[2]["Condition"]["ForAnyValue:StringEquals"]["dynamodb:EnclosingOperation"] == ["TransactWriteItems"]
    permission = f["AIInvokePermission"]["Properties"]
    assert permission["Principal"] == "apigateway.amazonaws.com"
    assert permission["SourceArn"]["Fn::Sub"].endswith("${PolicyAssistantApi}/Prod/POST/ai/ask")


def test_count_permission_is_foundation_only_without_profile_condition():
    stmts = fragment()["Resources"]["AIBedrockPolicy"]["Properties"]["PolicyDocument"]["Statement"]
    count = stmts[-1]
    assert count["Action"] == "bedrock:CountTokens"
    assert "foundation-model/amazon.nova-lite-v1:0" in count["Resource"]["Fn::Sub"]
    assert "Condition" not in count
    assert all(s["Action"] != "bedrock:*" and s["Resource"] != "*" for s in stmts)


def test_quota_retention_and_observability_configuration():
    f = fragment()["Resources"]
    assert f["AIQuotaTable"]["DeletionPolicy"] == f["AIQuotaTable"]["UpdateReplacePolicy"] == "Retain"
    assert f["AIQuotaTable"]["Properties"]["TimeToLiveSpecification"] == {"AttributeName": "expires", "Enabled": True}
    assert f["AILogGroup"]["Properties"]["RetentionInDays"] == 7
    assert f["AIFallbackAlarm"]["Properties"]["MetricName"] == "Fallbacks"
    assert f["AIFunction"]["Properties"]["LoggingConfig"]["LogFormat"] == "Text"


def test_corpus_hashes_are_candidates_not_runtime_approval():
    c = prepare.corpus_check()
    assert c["not_a_runtime_manifest"] and c["approval_status"].startswith("PENDING")


def test_feature_off_emf_is_safe_and_no_client_created(monkeypatch, capsys):
    monkeypatch.delenv("AI_ENABLED", raising=False)
    def no_clients():
        raise AssertionError("OFF must not initialize any AWS SDK clients")
    monkeypatch.setattr(ai, "_clients", no_clients)
    event = {"requestContext": {"http": {"method": "POST", "path": "/ai/ask"},
                              "authorizer": {"jwt": {"claims": {"sub": "synthetic-private-subject"}}}},
             "body": "synthetic-private-question"}
    r = ai.lambda_handler(event, None)
    log = capsys.readouterr().out
    assert json.loads(r["body"])["reason"] == "AI_DISABLED"
    assert "synthetic-private" not in log
    emf = json.loads(log)
    assert emf["Fallbacks"] == 0 and emf["ModelAttempts"] == 0
    assert emf["_aws"]["CloudWatchMetrics"][0]["Namespace"] == "PolicyAssistant/AI"


def test_failure_logs_only_fixed_stage_and_operational_fallback(capsys):
    ai._emit("dependency_or_model_failure", stage="MODEL")
    ai.fallback("AI_UNAVAILABLE", ["POL-001"])
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert events[0]["stage"] == "MODEL"
    assert events[1]["Fallbacks"] == 1
    assert set(events[0]) == {"event", "stage", "FunctionName", "ModelAttempts", "Fallbacks", "QuotaDenied", "_aws"}
