"""Build an OFF-only CloudFormation candidate and AI ZIP entirely offline.

Input must be a separately verified TEST processed template snapshot. This tool
never discovers AWS resources, uploads, creates change sets or deploys anything.
"""
import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TEST_STACK = "policy-assistant-fcaj-test"
EXISTING_FUNCTIONS = ("PolicyAssistantFunction", "PolicyAssistantWorker", "DocumentRecovery")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def corpus_check():
    items = json.loads((ROOT / "sample_data/policies.json").read_text(encoding="utf-8"))
    candidates = json.loads((ROOT / "infra/ai-corpus-candidates.json").read_text(encoding="utf-8"))
    approved_ids = {"POL-001", "POL-002", "POL-003"}
    if set(candidates["candidates"]) != approved_ids or {x["policy_id"] for x in items} != approved_ids:
        raise ValueError("Candidate corpus scope changed")
    for item in items:
        fields = {k: item.get(k) for k in ("policy_id", "title", "content", "owner_sub")}
        digest = sha(json.dumps(fields, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())
        if item.get("owner_sub") or digest != candidates["candidates"][item["policy_id"]]["sha256"]:
            raise ValueError("Candidate corpus hash or ownership changed")
    return candidates


def candidate(base):
    """Preserve all deployed resources except exact additive API/stage edits."""
    if "Globals" in base or "Transform" in base:
        raise ValueError("Use a verified processed template, not a shared SAM source template")
    source = base["Resources"]
    for name in EXISTING_FUNCTIONS:
        item = source[name]
        if item["Type"] != "AWS::Lambda::Function" or set(item["Properties"]["Code"]) != {"S3Bucket", "S3Key"}:
            raise ValueError("Existing Lambda must have pinned deployed S3 code")
    result = copy.deepcopy(base)
    fragment = json.loads((ROOT / "infra/ai-off-fragment.json").read_text(encoding="utf-8"))
    for section in ("Parameters", "Conditions", "Resources"):
        result.setdefault(section, {})
        if set(result[section]) & set(fragment[section]):
            raise ValueError("AI fragment collides with an existing logical ID")
        result[section].update(fragment[section])
    api = result["Resources"]["PolicyAssistantApi"]
    if api["Type"] != "AWS::ApiGatewayV2::Api":
        raise ValueError("Expected existing processed HTTP API")
    body = api["Properties"]["Body"]
    auth_name = "PolicyAssistantAuthorizer"
    scheme = body["components"]["securitySchemes"][auth_name]
    authorizer = scheme["x-amazon-apigateway-authorizer"]
    if authorizer.get("type") != "jwt" or not authorizer.get("jwtConfiguration"):
        raise ValueError("Existing JWT authorizer not proven")
    if "/ai/ask" in body["paths"]:
        raise ValueError("AI route already exists; stop rather than overwrite")
    body["paths"]["/ai/ask"] = {"post": {
        "security": [{auth_name: []}], "responses": {"200": {"description": "AI OFF fallback or verified source excerpts"}},
        "x-amazon-apigateway-integration": {
            "type": "aws_proxy", "httpMethod": "POST", "payloadFormatVersion": "2.0", "timeoutInMillis": 15000,
            "uri": {"Fn::Sub": "arn:${AWS::Partition}:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${AIFunction.Arn}/invocations"}}}}
    cors = body["x-amazon-apigateway-cors"]
    if not isinstance(cors.get("allowHeaders"), list):
        raise ValueError("Existing CORS headers not proven")
    if "idempotency-key" not in {x.lower() for x in cors["allowHeaders"]}:
        cors["allowHeaders"].append("Idempotency-Key")
    stage = result["Resources"]["PolicyAssistantApiProdStage"]["Properties"]
    if stage["StageName"] != "Prod" or stage["ApiId"] != {"Ref": "PolicyAssistantApi"}:
        raise ValueError("Wrong stage or API")
    stage.setdefault("RouteSettings", {})["POST /ai/ask"] = {"ThrottlingRateLimit": 1, "ThrottlingBurstLimit": 2}
    changes = {k for k in source if source[k] != result["Resources"][k]}
    if changes != {"PolicyAssistantApi", "PolicyAssistantApiProdStage"}:
        raise ValueError("Unexpected existing-resource change")
    for name in EXISTING_FUNCTIONS:
        if source[name] != result["Resources"][name]:
            raise ValueError("Existing Lambda changed")
    result.setdefault("Metadata", {})["AIReadiness"] = {
        "Mode": "OFF_ONLY_DRAFT", "Enablement": "BLOCKED_CONCURRENCY_AND_COUNTTOKENS_AND_OWNER_APPROVAL",
        "NoReservedConcurrency": "Shares account capacity; not equivalent to reserved concurrency2",
        "Corpus": "PENDING", "Subjects": "PENDING", "APACRouting": "PENDING"}
    return result


def artifact(destination):
    """Use only known pure-Python SDK distributions, no credentials/site customizers."""
    modules = {"boto3": "boto3", "botocore": "botocore", "jmespath": "jmespath",
               "s3transfer": "s3transfer", "python-dateutil": "dateutil", "urllib3": "urllib3", "six": "six.py"}
    entries = {"ai.py": (ROOT / "policy_assistant/ai.py").read_bytes()}
    locked = json.loads((ROOT / "infra/ai-sdk-versions.json").read_text(encoding="utf-8"))
    if set(locked) != set(modules):
        raise ValueError("SDK distribution allowlist changed")
    versions = {}
    for name, module in modules.items():
        dist = importlib.metadata.distribution(name)
        versions[name] = dist.version
        if dist.version != locked[name]:
            raise ValueError("SDK environment differs from reviewed version lock")
        for file in dist.files or []:
            relative = file.as_posix()
            parts = relative.split("/")
            if ".." in parts or "__pycache__" in parts or relative.endswith((".pyc", ".pyo")):
                continue
            if parts[0] == module or parts[0].endswith(".dist-info"):
                path = Path(str(dist.locate_file(file)))
                if path.is_file():
                    entries[relative] = path.read_bytes()
    with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None or "app.py" in archive.namelist():
            raise ValueError("Artifact failed integrity or isolation")
    if destination.stat().st_size > 50 * 1024 * 1024:
        raise ValueError("ZIP exceeds direct deployment artifact planning bound")
    return {"sha256": sha(destination.read_bytes()), "bytes": destination.stat().st_size,
            "file_count": len(entries), "dependencies": versions, "ai_source_sha256": sha(entries["ai.py"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--expected-baseline-sha256", required=True)
    parser.add_argument("--stack-name", required=True, choices=[TEST_STACK])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    target = args.output.resolve()
    if target.is_relative_to(ROOT) or ROOT.is_relative_to(target):
        raise ValueError("Output must be outside repository and not its ancestor")
    if target.exists() and any(target.iterdir()):
        raise ValueError("Output is nonempty; no automatic overwrite or cleanup")
    base = json.loads(args.baseline.read_text(encoding="utf-8-sig"))
    digest = sha(json.dumps(base, sort_keys=True).encode())
    if digest != args.expected_baseline_sha256:
        raise ValueError("Baseline fingerprint mismatch")
    corpus_check()
    result = candidate(base)
    target.mkdir(parents=True, exist_ok=True)
    package = artifact(target / "ai-only.zip")
    (target / "candidate.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    added = sorted(set(result["Resources"]) - set(base["Resources"]))
    report = {"stack": TEST_STACK, "baseline_sha256": digest, "artifact": package,
              "added_resources_including_false_condition": added,
              "modified_existing_resources": ["PolicyAssistantApi", "PolicyAssistantApiProdStage"],
              "existing_functions": "BYTE_IDENTICAL_RESOURCE_DEFINITIONS_AND_CODE_REFS",
              "mode": "OFF_ONLY", "enablement": "BLOCKED_CONCURRENCY", "aws_calls": 0,
              "count_tokens": "NOT_RUN_EXACT_PROFILE_UNKNOWN", "artifact_upload": "NOT_EXECUTED"}
    (target / "build-evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
