import importlib.util
from pathlib import Path

import pytest
import yaml


def test_account_deletion_can_persist_blocking_marker_with_api_role():
    class TemplateLoader(yaml.SafeLoader):
        pass
    TemplateLoader.add_multi_constructor("!", lambda loader, tag, node: loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode) else loader.construct_sequence(node))
    template = yaml.load((Path(__file__).resolve().parents[2] / "template.yaml").read_text(), Loader=TemplateLoader)
    statements = [statement for policy in template["Resources"]["PolicyAssistantFunction"]["Properties"]["Policies"] if isinstance(policy, dict) for statement in policy.get("Statement", [])]
    assert any(statement.get("Effect") == "Allow" and statement.get("Resource") == "UsageTable.Arn" and "dynamodb:PutItem" in statement.get("Action", []) for statement in statements)

spec = importlib.util.spec_from_file_location("release_helper", Path(__file__).resolve().parents[2] / "scripts/deploy_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


@pytest.mark.parametrize("resource_type", ["AWS::S3::Bucket", "AWS::DynamoDB::Table", "AWS::Cognito::UserPool", "AWS::Cognito::UserPoolClient", "AWS::SQS::Queue"])
@pytest.mark.parametrize("action,replacement", [("Remove", "False"), ("Modify", "True"), ("Modify", "Conditional")])
def test_data_resources_and_auth_clients_cannot_be_replaced_or_removed(resource_type, action, replacement):
    with pytest.raises(RuntimeError, match="Refusing"):
        release.check_changes([{"ResourceChange": {"ResourceType": resource_type, "LogicalResourceId": "Protected", "Action": action, "Replacement": replacement}}])


def test_non_replacing_updates_and_monitoring_replacements_are_allowed():
    release.check_changes([{"ResourceChange": {"ResourceType": "AWS::DynamoDB::Table", "LogicalResourceId": "Metadata", "Action": "Modify", "Replacement": "False"}}, {"ResourceChange": {"ResourceType": "AWS::CloudWatch::Alarm", "LogicalResourceId": "Alarm", "Action": "Modify", "Replacement": "True"}}])


def test_stale_lambda_build_is_rejected_before_release(monkeypatch, tmp_path):
    root = tmp_path / "project"
    built = root / ".aws-sam/build/Api"
    built.mkdir(parents=True)
    (root / "policy_assistant").mkdir()
    (root / "policy_assistant/app.py").write_text("new source")
    (built / "app.py").write_text("old source")
    (root / ".aws-sam/build/template.yaml").write_text(yaml.safe_dump({"Resources": {"Api": {"Type": "AWS::Serverless::Function", "Properties": {"CodeUri": "Api"}}}}))
    state = root / ".deployment"
    state.mkdir()
    monkeypatch.setattr(release, "ROOT", root)
    monkeypatch.setattr(release, "STATE", state)
    with pytest.raises(RuntimeError, match="stale"):
        release.artifact()



def test_release_without_override_selects_haiku_and_preserves_quotas():
    from types import SimpleNamespace
    stack = {"Parameters": [{"ParameterKey": "BedrockModelId"}, {"ParameterKey": "MonthlyQuestionLimit"}]}
    template = {"Parameters": {"BedrockModelId": {}, "MonthlyQuestionLimit": {}}}
    values = release.release_parameters(SimpleNamespace(notification_email="owner@example.invalid"), stack, template)
    indexed = {p["ParameterKey"]: p for p in values}
    assert indexed["BedrockModelId"]["ParameterValue"] == "global.anthropic.claude-haiku-5-5"
    assert indexed["MonthlyQuestionLimit"]["UsePreviousValue"] is True
    assert indexed["MonthlyBudgetUSD"]["ParameterValue"] == "50"


def test_haiku_model_override_is_explicit_and_unique():
    from types import SimpleNamespace
    args = SimpleNamespace(notification_email="owner@example.invalid", model_id="global.anthropic.claude-haiku-5-5")
    values = release.release_parameters(args, {"Parameters": [{"ParameterKey": "BedrockModelId"}]}, {"Parameters": {"BedrockModelId": {}}})
    models = [p for p in values if p["ParameterKey"] == "BedrockModelId"]
    assert models == [{"ParameterKey": "BedrockModelId", "ParameterValue": "global.anthropic.claude-haiku-5-5"}]


def test_other_model_is_rejected_before_a_release():
    from types import SimpleNamespace
    with pytest.raises(ValueError, match="Unsupported generation profile"):
        release.release_parameters(SimpleNamespace(notification_email="owner@example.invalid", model_id="unsupported.fixture-model"), {}, {})
