"""Read readiness metadata only; never query customer PDF/support contents."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REGION = "ap-southeast-1"


def main(use_cli=False):
    if use_cli:
        from check_admin_live import aws
        def call(service, method, **kwargs):
            return aws(service, method.replace("_", "-"), **kwargs)
    else:
        import boto3
        clients = {}
        def call(service, method, **kwargs):
            if service not in clients:
                clients[service] = boto3.client(service, region_name=REGION)
            return getattr(clients[service], method)(**kwargs)
    stack = call("cloudformation", "describe_stacks", StackName="policy-assistant")["Stacks"][0]
    if stack["StackId"].split(":")[4] != "629380420098":
        raise RuntimeError("Unexpected AWS account; no additional reads performed")
    outputs = {v["OutputKey"]: v["OutputValue"] for v in stack["Outputs"]}
    resources = call("cloudformation", "list_stack_resources", StackName="policy-assistant")["StackResourceSummaries"]
    by_name = {v["LogicalResourceId"]: v["PhysicalResourceId"] for v in resources}
    distribution = call("cloudfront", "get_distribution", Id=outputs["FrontendDistributionId"])["Distribution"]
    subscriptions = []
    for sub in call("sns", "list_subscriptions_by_topic", TopicArn=by_name["AlertTopic"])["Subscriptions"]:
        subscriptions.append({"protocol": sub["Protocol"], "confirmed": sub["SubscriptionArn"] != "PendingConfirmation"})
    users = call("cognito-idp", "list_users", UserPoolId=outputs["UserPoolId"], Filter='email = "huynhhao080@gmail.com"', Limit=2)["Users"]
    owner, administrator = "not_registered", False
    if len(users) == 1:
        attrs = {a["Name"]: a["Value"] for a in users[0]["Attributes"]}
        owner = "verified" if users[0]["UserStatus"] == "CONFIRMED" and attrs.get("email_verified") == "true" else "awaiting_verification"
        groups = call("cognito-idp", "admin_list_groups_for_user", UserPoolId=outputs["UserPoolId"], Username=users[0]["Username"])["Groups"]
        administrator = any(g["GroupName"] == "administrators" for g in groups)
    alarm_names = [v["PhysicalResourceId"] for v in resources if v["ResourceType"] == "AWS::CloudWatch::Alarm"]
    alarms = call("cloudwatch", "describe_alarms", AlarmNames=alarm_names)["MetricAlarms"] if alarm_names else []
    alarm_report = [{"name": a["AlarmName"], "state": a["StateValue"], "actions_enabled": a["ActionsEnabled"], "has_alarm_action": bool(a.get("AlarmActions"))} for a in alarms]
    queues = []
    for resource in resources:
        if resource["ResourceType"] == "AWS::SQS::Queue":
            attrs = call("sqs", "get_queue_attributes", QueueUrl=resource["PhysicalResourceId"], AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible", "ApproximateNumberOfMessagesDelayed"])["Attributes"]
            queues.append({"logical_id": resource["LogicalResourceId"], **{k: int(v) for k,v in attrs.items()}})
    support_table = outputs.get("SupportTableName")
    support = None
    if support_table:
        ttl = call("dynamodb", "describe_time_to_live", TableName=support_table)["TimeToLiveDescription"]
        recovery = call("dynamodb", "describe_continuous_backups", TableName=support_table)["ContinuousBackupsDescription"]["PointInTimeRecoveryDescription"]
        support = {"ttl_status": ttl["TimeToLiveStatus"], "ttl_attribute": ttl.get("AttributeName"), "pitr_status": recovery["PointInTimeRecoveryStatus"]}
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "stack": stack["StackStatus"], "frontend": outputs["FrontendUrl"], "distribution": distribution["Status"], "alert_subscriptions": subscriptions, "selected_admin_account": owner, "selected_account_is_admin": administrator, "alarms": alarm_report, "queues": queues, "support_table": support, "limits": "Metadata snapshot only; does not prove alert delivery, restore success, current billing or an availability SLA."}
    folder = Path(__file__).resolve().parents[1] / ".deployment"
    folder.mkdir(exist_ok=True)
    (folder / "operational-status.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aws-cli", action="store_true", help="Use AWS CLI transport instead of boto3 networking")
    main(use_cli=parser.parse_args().aws_cli)
