"""Verify the deployed PDF text reader with one synthetic text PDF and account."""
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import secrets
import sys
import time
from uuid import uuid4

from pypdf import PdfReader, PdfWriter
import requests

from check_admin_live import aws, UserNotFound

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.unit.pdf_fixture import pdf_bytes


def main():
    stack = aws("cloudformation", "describe-stacks", StackName="policy-assistant")["Stacks"][0]
    assert stack["StackStatus"] == "UPDATE_COMPLETE" and stack["StackId"].split(":")[4] == "629380420098"
    out = {item["OutputKey"]: item["OutputValue"] for item in stack["Outputs"]}
    base = out["PolicyAssistantApiUrl"].rstrip("/")
    assert base == "https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod"
    release = json.loads((ROOT / ".deployment/release.json").read_text())
    assert hashlib.sha256((ROOT / ".deployment/lambda.zip").read_bytes()).hexdigest() == release["code_sha256"]
    fn = aws("cloudformation", "describe-stack-resource", StackName="policy-assistant", LogicalResourceId="PolicyAssistantFunction")["StackResourceDetail"]["PhysicalResourceId"]
    config = aws("lambda", "get-function-configuration", FunctionName=fn)
    assert config["LastUpdateStatus"] == "Successful" and base64.b64decode(config["CodeSha256"]).hex() == release["code_sha256"]

    writer = PdfWriter()
    expected = ["Synthetic QA first page", "Synthetic QA second page"]
    for text in expected:
        writer.add_page(PdfReader(io.BytesIO(pdf_bytes(text))).pages[0])
    buffer = io.BytesIO()
    writer.write(buffer)
    state = ROOT / ".deployment/pdf-text"
    state.mkdir(parents=True, exist_ok=True)
    username = f"pdf-text-qa-{uuid4().hex}@example.invalid"
    password = secrets.token_urlsafe(24) + "Aa1!"
    pool = out["UserPoolId"]
    token = None
    created = False
    report = {"checked_at":datetime.now(timezone.utc).isoformat(), "release":release,
              "checks":[], "account_cleaned":False, "scope":"Synthetic text PDF, real HTTP and account cleanup. Zero model or OCR requests."}
    marker = state / "live-cleanup.json"
    marker.write_text(json.dumps({"username":username, "pool":pool, "attempted":True}))

    def call(path, method="GET", body=None, authenticated=True):
        headers = {"Authorization":"Bearer " + token} if authenticated else {}
        return requests.request(method, base + path, json=body, headers=headers, timeout=30)

    def check(label, passed):
        if not passed:
            raise RuntimeError(label)
        report["checks"].append(label)
        print("PASS " + label, flush=True)

    try:
        aws("cognito-idp", "admin-create-user", UserPoolId=pool, Username=username, MessageAction="SUPPRESS",
            UserAttributes=[{"Name":"email","Value":username},{"Name":"email_verified","Value":"true"}])
        created = True
        aws("cognito-idp", "admin-set-user-password", UserPoolId=pool, Username=username, Password=password, Permanent=True)
        token = aws("cognito-idp", "initiate-auth", ClientId=out["UserPoolClientId"], AuthFlow="USER_PASSWORD_AUTH",
                    AuthParameters={"USERNAME":username,"PASSWORD":password})["AuthenticationResult"]["IdToken"]
        response = call("/documents/upload-session", "POST", {"filename":"synthetic-pdf-text.pdf"})
        check("Upload session", response.status_code == 200)
        session = response.json()
        route = "/documents/" + session["doc_id"]
        check("Anonymous text request rejected", call(route + "/text", authenticated=False).status_code == 401)
        check("Text unavailable before processing", call(route + "/text").status_code == 409)
        response = requests.post(session["upload_url"], data=session["upload_fields"],
                                 files={"file":("synthetic-pdf-text.pdf", buffer.getvalue(), "application/pdf")}, timeout=30)
        check("Synthetic PDF uploaded", response.ok)
        response = call("/documents/submit", "POST", {key:session[key] for key in ("doc_id","s3_key")})
        check("Document submitted", response.status_code == 200)
        for _ in range(36):
            result = call(route + "/status").json()
            if result["status"] in ("processed","failed"):
                break
            time.sleep(4)
        check("Text extraction ready", result["status"] == "processed" and result["page_count"] == 2)
        for page, text in enumerate(expected, 1):
            response = call(route + f"/text?page={page}")
            data = response.json()
            check(f"Page {page} returns its own text", response.status_code == 200 and data["page"] == page
                  and data["page_count"] == 2 and data["chunks"] == [text] and "no-store" in response.headers.get("Cache-Control",""))
        check("Out-of-range page rejected", call(route + "/text?page=3").status_code == 400)
    finally:
        try:
            if token:
                response = call("/account/delete", "POST", {"confirmation":"DELETE"})
                assert response.status_code == 200
                for _ in range(60):
                    try:
                        aws("cognito-idp", "admin-get-user", UserPoolId=pool, Username=username)
                    except UserNotFound:
                        report["account_cleaned"] = True
                        break
                    time.sleep(4)
            elif created:
                aws("cognito-idp", "admin-delete-user", UserPoolId=pool, Username=username)
                report["account_cleaned"] = True
        finally:
            (state / "live-acceptance.json").write_text(json.dumps(report, indent=2))
            if report["account_cleaned"]:
                marker.unlink()
    if not report["account_cleaned"]:
        raise SystemExit("Synthetic account cleanup incomplete")


if __name__ == "__main__":
    main()
