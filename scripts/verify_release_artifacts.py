"""Verify existing AWS deployment artifacts; no page, user session or model calls."""
import argparse
import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from check_admin_live import aws

ROOT = Path(__file__).resolve().parents[1]


def main(invalidation_id):
    release = json.loads((ROOT / ".deployment/release.json").read_text(encoding="utf-8"))
    stack = aws("cloudformation", "describe-stacks", StackName=release["stack"])["Stacks"][0]
    assert stack["StackStatus"] == "UPDATE_COMPLETE", "Stack is not ready"
    assert stack["StackId"].split(":")[4] == "629380420098", "Wrong AWS account"
    outputs = {x["OutputKey"]: x["OutputValue"] for x in stack["Outputs"]}
    dist = ROOT / "frontend/dist"
    config = json.loads((dist / "config.json").read_text(encoding="utf-8"))
    assert config["apiBase"] == outputs["PolicyAssistantApiUrl"].rstrip("/")
    files = []
    for path in sorted(dist.rglob("*")):
        if not path.is_file():
            continue
        key, data = path.relative_to(dist).as_posix(), path.read_bytes()
        head = aws("s3api", "head-object", Bucket=outputs["FrontendBucketName"], Key=key)
        assert head["ContentLength"] == len(data), key + " size mismatch"
        assert head["ETag"].strip('"') == hashlib.md5(data).hexdigest(), key + " byte mismatch"
        assert head["ServerSideEncryption"] == "AES256", key + " encryption mismatch"
        if path.suffix in (".html", ".json", ".js", ".css"):
            assert head["CacheControl"] == "no-cache", key + " cache policy mismatch"
        files.append({"key": key, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "content_type": head["ContentType"]})
    resources = aws("cloudformation", "list-stack-resources", StackName=release["stack"])["StackResourceSummaries"]
    functions = []
    for resource in resources:
        if resource["ResourceType"] != "AWS::Lambda::Function":
            continue
        cfg = aws("lambda", "get-function-configuration", FunctionName=resource["PhysicalResourceId"])
        digest = base64.b64decode(cfg["CodeSha256"]).hex()
        assert digest == release["code_sha256"], resource["LogicalResourceId"] + " code mismatch"
        assert cfg.get("LastUpdateStatus") == "Successful"
        functions.append({"logical_id": resource["LogicalResourceId"], "code_sha256": digest, "update_status": cfg["LastUpdateStatus"]})
    assert len(functions) == 6
    invalidation = aws("cloudfront", "get-invalidation", DistributionId=outputs["FrontendDistributionId"], Id=invalidation_id)["Invalidation"]
    assert invalidation["Status"] == "Completed", "Wait for CloudFront invalidation before marking publication verified"
    distribution = aws("cloudfront", "get-distribution", Id=outputs["FrontendDistributionId"])["Distribution"]
    assert distribution["Status"] == "Deployed"
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "release": release, "stack_status": stack["StackStatus"], "invalidation_id": invalidation_id, "invalidation_status": invalidation["Status"], "distribution_status": distribution["Status"], "files": files, "deployed_functions": functions, "method": "AWS artifact metadata and content checksums only; no live-browser/session or model access"}
    target = ROOT / ".deployment/triage-artifact-verification.json"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(files)} frontend files match local bytes; six Lambda hashes match release; CloudFront invalidation completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invalidation-id", required=True)
    main(parser.parse_args().invalidation_id)
