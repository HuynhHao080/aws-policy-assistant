"""Live admin lifecycle with one disposable identity and one guarded synthetic policy.

AWS CLI handles control calls; application checks use real authenticated HTTP.
No browser session, owner account, owner PDFs or existing policy is modified.
"""
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
import base64
import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
ENV = os.environ.copy()
ENV.update(AWS_MAX_ATTEMPTS="1", AWS_PAGER="", AWS_CLI_FILE_ENCODING="UTF-8")


class UserNotFound(Exception):
    pass


def aws(service, operation, **data):
    with tempfile.TemporaryDirectory(prefix="policy-admin-check-") as folder:
        path = Path(folder) / "request.json"
        path.write_text(json.dumps(data, ensure_ascii=True), encoding="ascii")
        result = subprocess.run(["aws", service, operation, "--cli-input-json", "file://" + str(path), "--region", "ap-southeast-1", "--output", "json", "--no-cli-pager", "--cli-connect-timeout", "5", "--cli-read-timeout", "30"], capture_output=True, env=ENV, timeout=45)
        if result.returncode:
            if b"UserNotFoundException" in result.stderr:
                raise UserNotFound()
            raise RuntimeError("AWS control call failed: " + service + "/" + operation)
        return json.loads(result.stdout.decode("utf-8-sig")) if result.stdout.strip() else {}


def main():
    stack = aws("cloudformation", "describe-stacks", StackName="policy-assistant")["Stacks"][0]
    if stack["StackStatus"] != "UPDATE_COMPLETE" or stack["StackId"].split(":")[4] != "629380420098":
        raise RuntimeError("Unexpected stack or deployment state")
    outputs = {v["OutputKey"]: v["OutputValue"] for v in stack["Outputs"]}
    function = aws("cloudformation", "describe-stack-resource", StackName="policy-assistant", LogicalResourceId="PolicyAssistantFunction")["StackResourceDetail"]["PhysicalResourceId"]
    config = aws("lambda", "get-function-configuration", FunctionName=function)
    release = json.loads((ROOT / ".deployment/release.json").read_text(encoding="utf-8"))
    if config["CodeSha256"] != base64.b64encode(bytes.fromhex(release["code_sha256"])).decode():
        raise RuntimeError("Unexpected deployed code checksum")
    nonce = uuid4().hex
    username = "admin-qa-" + nonce + "@example.invalid"
    policy_id = "QA-ADMIN-" + nonce
    password = secrets.token_urlsafe(30) + "Aa1!"
    base = outputs["PolicyAssistantApiUrl"].rstrip("/")
    pool, client = outputs["UserPoolId"], outputs["UserPoolClientId"]
    token = None
    created = policy_attempted = False
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "release": release, "scope": "Real HTTP admin lifecycle, one invitation-suppressed synthetic identity, one uniquely named DEMO policy. No owner session/private PDFs/existing policy changed.", "checks": [], "policy_cleaned": False, "account_cleaned": False}
    report_file = ROOT / ".deployment/admin-live-acceptance.json"
    def save():
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    def check(label, value):
        if not value:
            raise RuntimeError("Failed: " + label)
        report["checks"].append(label)
        save()
        print("PASS " + label, flush=True)
    def call(path, method="GET", data=None, auth=True, override=None):
        headers = {"Origin": outputs["FrontendUrl"].rstrip("/")}
        if auth:
            headers["Authorization"] = "Bearer " + (override or token)
        response = requests.request(method, base + path, json=data, headers=headers, timeout=45)
        try:
            body = response.json()
        except ValueError:
            body = {}
        return response.status_code, body
    def edit(action, version=None, draft=None):
        body = {"action": action, "expected_revision": version}
        if draft is not None:
            body["draft"] = draft
        code, result = call("/admin/policies/" + policy_id, "PATCH", body)
        if code != 200:
            raise RuntimeError("Policy action " + action + " returned HTTP " + str(code))
        return result
    try:
        check("New admin routes require JWT", call("/admin/policies", auth=False)[0] == 401)
        aws("cognito-idp", "admin-create-user", UserPoolId=pool, Username=username, MessageAction="SUPPRESS", UserAttributes=[{"Name": "email", "Value": username}, {"Name": "email_verified", "Value": "true"}])
        created = True
        (ROOT / ".deployment/admin-test-cleanup.json").write_text(json.dumps({"username": username, "pool": pool, "policy_id": policy_id, "nonce": nonce, "cleaned": False}), encoding="utf-8")
        aws("cognito-idp", "admin-set-user-password", UserPoolId=pool, Username=username, Password=password, Permanent=True)
        def sign_in():
            return aws("cognito-idp", "initiate-auth", ClientId=client, AuthFlow="USER_PASSWORD_AUTH", AuthParameters={"USERNAME": username, "PASSWORD": password})["AuthenticationResult"]["IdToken"]
        token = sign_in()
        ordinary = token
        check("Customer cannot list administrator policies", call("/admin/policies")[0] == 403)
        check("Customer cannot read administrator policy detail", call("/admin/policies/" + policy_id)[0] == 403)
        check("Customer cannot save policy drafts", call("/admin/policies/" + policy_id, "PATCH", {"action": "save_draft"})[0] == 403)
        aws("cognito-idp", "admin-add-user-to-group", UserPoolId=pool, Username=username, GroupName="administrators")
        token = sign_in()
        code, listing = call("/admin/policies?limit=1")
        check("Admin catalogue returns bounded metadata only", code == 200 and len(listing["policies"]) <= 1 and all(not any(k in r for k in ("content", "draft_data", "search_chunks", "revision")) for r in listing["policies"]))
        if listing.get("next_token"):
            from urllib.parse import quote
            check("Admin catalogue pagination works", call("/admin/policies?limit=1&next_token=" + quote(listing["next_token"], safe=""))[0] == 200)
        fields = {"title": "DEMO — Kiểm thử quản trị tạm " + nonce, "category": "Kiểm thử nội bộ", "content": "DỮ LIỆU KIỂM THỬ TẠM THỜI, KHÔNG ÁP DỤNG GIAO DỊCH THẬT. Mã kiểm tra: " + nonce, "keywords": [nonce]}
        policy_attempted = True
        draft = edit("save_draft", draft=fields)
        check("New policy remains an unpublished draft", draft["publication_state"] == "draft" and draft["current"] is None and call("/policies/" + policy_id)[0] == 404)
        check("Draft content is excluded from customer keyword search", call("/policies?keyword=" + nonce)[1].get("policies") == [])
        check("Stale revision returns conflict", call("/admin/policies/" + policy_id, "PATCH", {"action": "publish", "expected_revision": "stale"})[0] == 409)
        live = edit("publish", draft["revision"])
        code, public_before = call("/policies/" + policy_id)
        check("Explicit publish indexes and exposes only approved content", code == 200 and public_before["content"] == fields["content"] and all(k not in public_before for k in ("search_chunks", "draft_data", "revision", "edited_at", "published_by")))
        changed = dict(fields, content="DRAFT-ONLY-" + nonce)
        drafted = edit("save_draft", live["revision"], changed)
        check("Editing a live policy preserves the full public snapshot", call("/policies/" + policy_id)[1] == public_before)
        check("Customer JWT still cannot read the draft after a role refresh", call("/admin/policies/" + policy_id, override=ordinary)[0] == 403)
        discarded = edit("discard_draft", drafted["revision"])
        check("Discarding draft preserves published content", discarded["draft"] is None and call("/policies/" + policy_id)[1] == public_before)
        archived = edit("archive", discarded["revision"])
        check("Archive removes the policy from customer lookup and search", call("/policies/" + policy_id)[0] == 404 and call("/policies?keyword=" + nonce)[1].get("policies") == [])
        restored = edit("publish", archived["revision"])
        check("Archived policy can be republished without retyping", restored["current"]["content"] == fields["content"] and call("/policies/" + policy_id)[0] == 200)
        edit("archive", restored["revision"])
        code, audit = call("/admin/audit")
        own_events = [e for e in audit.get("events", []) if e.get("resource") == policy_id]
        actions = {e["action"] for e in own_events}
        check("Lifecycle audit records are present without policy content", code == 200 and {"policy.draft", "policy.publish", "policy.archive", "policy.discard_draft"}.issubset(actions) and all("content" not in e for e in own_events))
        report["http_passed"] = True
    except Exception as exc:
        report["error"] = str(exc)[:300]
        print("Acceptance stopped: " + type(exc).__name__, flush=True)
    finally:
        save()
        if policy_attempted and token:
            code, own = call("/admin/policies/" + policy_id)
            if code == 404:
                report["policy_cleaned"] = True
            elif code == 200:
                safe = policy_id == own.get("policy_id") and any(nonce in (own.get(k) or {}).get("content", "") for k in ("current", "draft"))
                if not safe:
                    raise RuntimeError("Refusing cleanup of a policy without its synthetic nonce")
                report["policy_cleaned"] = call("/admin/policies/" + policy_id, "DELETE")[0] == 200
        elif not policy_attempted:
            report["policy_cleaned"] = True
        if created:
            if token and call("/account/delete", "POST", {"confirmation": "DELETE"})[0] == 200:
                report["deleting_account_blocked"] = call("/admin/policies")[0] == 410
                deadline = time.monotonic() + 240
                while time.monotonic() < deadline:
                    try:
                        aws("cognito-idp", "admin-get-user", UserPoolId=pool, Username=username)
                    except UserNotFound:
                        report["account_cleaned"] = True
                        break
                    time.sleep(5)
            else:
                aws("cognito-idp", "admin-remove-user-from-group", UserPoolId=pool, Username=username, GroupName="administrators")
                aws("cognito-idp", "admin-delete-user", UserPoolId=pool, Username=username)
                report["account_cleaned"] = True
        save()
        if created:
            (ROOT / ".deployment/admin-test-cleanup.json").write_text(json.dumps({"username": username, "pool": pool, "policy_id": policy_id, "policy_cleaned": report["policy_cleaned"], "cleaned": report["account_cleaned"]}), encoding="utf-8")
        print("Policy/account cleanup:", report["policy_cleaned"], report["account_cleaned"], flush=True)
    if not report.get("http_passed") or not report["policy_cleaned"] or not report["account_cleaned"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
