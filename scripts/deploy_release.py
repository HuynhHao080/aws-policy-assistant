"""Prepare, inspect, then execute one immutable CloudFormation change set.

Preparation uploads the Lambda artifact and creates a non-executing change set.
Execution rejects data-resource replacements/removals. Each migration phase is
prepared and reviewed separately; deploy the frontend only after the final phase.
"""
import argparse
import hashlib
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import boto3
import yaml
from botocore.config import Config
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".deployment"
REGION = "ap-southeast-1"


def clients():
    options = {"region_name": REGION, "config": Config(connect_timeout=5, read_timeout=30, retries={"max_attempts": 2})}
    return {name: boto3.client(name, **options) for name in ("cloudformation", "s3", "sts", "dynamodb", "cloudfront")}


def artifact():
    template = yaml.safe_load((ROOT / ".aws-sam/build/template.yaml").read_text(encoding="utf-8"))
    functions = [r for r in template["Resources"].values() if r["Type"] == "AWS::Serverless::Function"]
    base = (ROOT / ".aws-sam/build" / functions[0]["Properties"]["CodeUri"]).resolve()
    path = STATE / "lambda.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(base.rglob("*")):
            if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc":
                archive.write(file, file.relative_to(base).as_posix())
    # All SAM functions share policy_assistant/; reject a stale mixed build.
    for function in functions:
        built = (ROOT / ".aws-sam/build" / function["Properties"]["CodeUri"]).resolve()
        for module in (ROOT / "policy_assistant").glob("*.py"):
            if (built / module.name).read_bytes() != module.read_bytes():
                raise RuntimeError("Lambda build is stale; rebuild before preparing a release")
    return template, path, hashlib.sha256(path.read_bytes()).hexdigest()


def describe_change(cf, stack, name):
    result = cf.describe_change_set(StackName=stack, ChangeSetName=name)
    changes = result.get("Changes", [])
    while result.get("NextToken"):
        result = cf.describe_change_set(StackName=stack, ChangeSetName=name, NextToken=result["NextToken"])
        changes.extend(result.get("Changes", []))
    return result, changes


def check_changes(changes):
    protected = {"AWS::DynamoDB::Table", "AWS::S3::Bucket", "AWS::Cognito::UserPool", "AWS::Cognito::UserPoolClient", "AWS::SQS::Queue"}
    for item in changes:
        resource = item["ResourceChange"]
        if resource["ResourceType"] in protected and (resource["Action"] == "Remove" or resource.get("Replacement") not in (None, "False")):
            raise RuntimeError("Refusing data-resource removal/replacement: " + resource["LogicalResourceId"])


def release_parameters(args, stack, template):
    parameters = [{"ParameterKey": "NotificationEmail", "ParameterValue": args.notification_email}, {"ParameterKey": "MonthlyBudgetUSD", "ParameterValue": "50"}]
    overrides = {"NotificationEmail", "MonthlyBudgetUSD"}
    model = getattr(args, "model_id", None)
    if model:
        if model not in {"apac.amazon.nova-micro-v1:0", "jp.amazon.nova-2-lite-v1:0"}:
            raise ValueError("Unsupported generation profile; global routing is not allowed")
        parameters.append({"ParameterKey": "BedrockModelId", "ParameterValue": model})
        overrides.add("BedrockModelId")
    parameters.extend({"ParameterKey": p["ParameterKey"], "UsePreviousValue": True} for p in stack.get("Parameters", []) if p["ParameterKey"] not in overrides and p["ParameterKey"] in template.get("Parameters", {}))
    return parameters


def prepare(args, client):
    STATE.mkdir(exist_ok=True)
    cf, s3 = client["cloudformation"], client["s3"]
    stack = cf.describe_stacks(StackName=args.stack)["Stacks"][0]
    if stack["StackStatus"] not in ("CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"):
        raise RuntimeError("Stack is not ready for an update: " + stack["StackStatus"])
    template, binary, digest = artifact()
    managed = cf.describe_stacks(StackName="aws-sam-cli-managed-default")["Stacks"][0]
    bucket = next(v["OutputValue"] for v in managed["Outputs"] if v["OutputKey"] == "SourceBucket")
    code_key = f"{args.stack}/releases/{digest}.zip"
    s3.upload_file(str(binary), bucket, code_key, ExtraArgs={"ServerSideEncryption": "AES256"})
    for resource in template["Resources"].values():
        if resource["Type"] == "AWS::Serverless::Function":
            resource["Properties"]["CodeUri"] = {"Bucket": bucket, "Key": code_key}
    phase = "final"
    try:
        table_name = cf.describe_stack_resource(StackName=args.stack, LogicalResourceId="DocumentMetadata")["StackResourceDetail"]["PhysicalResourceId"]
        existing = client["dynamodb"].describe_table(TableName=table_name)["Table"]
        names = {i["IndexName"] for i in existing.get("GlobalSecondaryIndexes", [])}
        if names - {"OwnerCreatedAt", "StatusUpdatedAt"}:
            raise RuntimeError("Unexpected existing indexes require a migration review")
        if any(i["IndexStatus"] != "ACTIVE" for i in existing.get("GlobalSecondaryIndexes", [])):
            raise RuntimeError("Wait for the existing index operation to finish")
        if len({"OwnerCreatedAt", "StatusUpdatedAt"} - names) > 1:
            phase = "index-migration"
            metadata = template["Resources"]["DocumentMetadata"]["Properties"]
            metadata["GlobalSecondaryIndexes"] = [i for i in metadata["GlobalSecondaryIndexes"] if i["IndexName"] == "OwnerCreatedAt"]
            metadata["AttributeDefinitions"] = [a for a in metadata["AttributeDefinitions"] if a["AttributeName"] not in ("status", "updated_at")]
            template["Resources"]["DocumentRecovery"]["Properties"]["Events"]["EveryFiveMinutes"]["Properties"]["Enabled"] = False
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ValidationError":
            raise
    template_path = STATE / ("template-" + phase + ".yaml")
    template_path.write_text(yaml.safe_dump(template, sort_keys=False), encoding="utf-8")
    template_key = f"{args.stack}/releases/{digest}-{phase}.yaml"
    s3.upload_file(str(template_path), bucket, template_key, ExtraArgs={"ServerSideEncryption": "AES256"})
    name = f"public-{phase}-{int(time.time())}"
    parameters = release_parameters(args, stack, template)
    created = cf.create_change_set(StackName=args.stack, ChangeSetName=name, ChangeSetType="UPDATE", TemplateURL=f"https://{bucket}.s3.{REGION}.amazonaws.com/{template_key}", Capabilities=["CAPABILITY_IAM"], Parameters=parameters, Description=f"Policy Assistant {phase}, code SHA256 {digest}")
    state = {"stack": args.stack, "change_set": name, "change_set_id": created["Id"], "phase": phase, "code_sha256": digest, "template_sha256": hashlib.sha256(template_path.read_bytes()).hexdigest()}
    (STATE / "release.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    (STATE / (name + ".json")).write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps(state, indent=2))


def inspect(client):
    state = json.loads((STATE / "release.json").read_text())
    result, changes = describe_change(client["cloudformation"], state["stack"], state["change_set_id"])
    print("Status:", result["Status"], result.get("StatusReason", ""))
    for item in changes:
        change = item["ResourceChange"]
        print(change["Action"], change["LogicalResourceId"], change["ResourceType"], "replacement=" + str(change.get("Replacement", "False")))
    check_changes(changes)
    print("Data-resource replacement guard: PASS")


def execute(client):
    state = json.loads((STATE / "release.json").read_text())
    result, changes = describe_change(client["cloudformation"], state["stack"], state["change_set_id"])
    if result["Status"] != "CREATE_COMPLETE" or result.get("ExecutionStatus") != "AVAILABLE":
        raise RuntimeError("The reviewed change set is not executable")
    check_changes(changes)
    client["cloudformation"].execute_change_set(StackName=state["stack"], ChangeSetName=state["change_set_id"])
    print("Executing reviewed change set:", state["change_set"], "phase:", state["phase"])


def status(args, client):
    cf = client["cloudformation"]
    stack = cf.describe_stacks(StackName=args.stack)["Stacks"][0]
    print("Stack:", stack["StackStatus"])
    for event in cf.describe_stack_events(StackName=args.stack)["StackEvents"][:12]:
        print(event["LogicalResourceId"], event["ResourceStatus"], event.get("ResourceStatusReason", ""))


def publish(args, client):
    cf = client["cloudformation"]
    stack = cf.describe_stacks(StackName=args.stack)["Stacks"][0]
    if stack["StackStatus"] not in ("CREATE_COMPLETE", "UPDATE_COMPLETE"):
        raise RuntimeError("Stack update is not complete")
    outputs = {x["OutputKey"]: x["OutputValue"] for x in stack["Outputs"]}
    metadata = client["dynamodb"].describe_table(TableName=outputs["DocumentMetadataTableName"])["Table"]
    if {x["IndexName"] for x in metadata.get("GlobalSecondaryIndexes", []) if x["IndexStatus"] == "ACTIVE"} != {"OwnerCreatedAt", "StatusUpdatedAt"}:
        raise RuntimeError("Finish both index migrations before publishing")
    config = {"apiBase": outputs["PolicyAssistantApiUrl"].rstrip("/"), "region": REGION, "userPoolId": outputs["UserPoolId"], "clientId": outputs["UserPoolClientId"], "authDomain": outputs["CognitoDomainUrl"]}
    path = ROOT / "frontend/dist/config.json"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    bucket = outputs["FrontendBucketName"]
    mime = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json", ".ttf": "font/ttf", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}
    # Publish immutable assets first, then config, then HTML entry points.
    files = sorted((ROOT / "frontend/dist").rglob("*"), key=lambda p: (p.suffix == ".html", p.name == "index.html"))
    for file in files:
        if not file.is_file():
            continue
        key = file.relative_to(ROOT / "frontend/dist").as_posix()
        client["s3"].upload_file(str(file), bucket, key, ExtraArgs={"ContentType": mime.get(file.suffix, "application/octet-stream"), "CacheControl": "no-cache" if file.suffix in (".html", ".json", ".js", ".css") else "public,max-age=31536000,immutable", "ServerSideEncryption": "AES256"})
    invalidation = client["cloudfront"].create_invalidation(DistributionId=outputs["FrontendDistributionId"], InvalidationBatch={"Paths": {"Quantity": 1, "Items": ["/*"]}, "CallerReference": str(time.time_ns())})
    print("Published frontend:", outputs["FrontendUrl"])
    print("Invalidation:", invalidation["Invalidation"]["Id"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "inspect", "execute", "status", "publish"])
    parser.add_argument("--stack", default="policy-assistant")
    parser.add_argument("--notification-email")
    parser.add_argument("--model-id", choices=["apac.amazon.nova-micro-v1:0", "jp.amazon.nova-2-lite-v1:0"])
    args = parser.parse_args()
    if args.action == "prepare" and not args.notification_email:
        parser.error("--notification-email is required when preparing")
    if args.action == "prepare":
        prepare(args, clients())
    elif args.action == "inspect":
        inspect(clients())
    elif args.action == "execute":
        execute(clients())
    elif args.action == "status":
        status(args, clients())
    else:
        publish(args, clients())
