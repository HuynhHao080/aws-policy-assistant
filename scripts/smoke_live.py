"""Live acceptance using disposable synthetic accounts and files only.

Creates two suppressed-invitation Cognito users, exercises the public API, and
requests account/data deletion. Passwords, JWTs and presigned forms stay in memory.
The optional --ocr probe uses a one-page scanned synthetic PDF and incurs Textract
inference charges within the application's configured quotas.
"""
import argparse
import hashlib
import io
import json
import secrets
import sys
import time
from pathlib import Path
from uuid import uuid4

import boto3
import requests
from botocore.config import Config
from botocore.exceptions import ClientError
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, NumberObject, DecodedStreamObject

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.unit.pdf_fixture import pdf_bytes


def scanned_pdf():
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (1200, 500), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=42)
    draw.text((50, 100), "SYNTHETIC POLICY", font=font, fill="black")
    draw.text((50, 200), "Refund requests: within 30 days.", font=font, fill="black")
    encoded = io.BytesIO()
    image.save(encoded, format="JPEG", quality=95)
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=750)
    picture = DecodedStreamObject()
    picture.set_data(encoded.getvalue())
    picture.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"), NameObject("/Width"): NumberObject(1200), NameObject("/Height"): NumberObject(500), NameObject("/ColorSpace"): NameObject("/DeviceRGB"), NameObject("/BitsPerComponent"): NumberObject(8), NameObject("/Filter"): NameObject("/DCTDecode")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): writer._add_object(picture)})})
    content = DecodedStreamObject()
    content.set_data(b"q 550 0 0 230 25 430 cm /Im0 Do Q")
    page[NameObject("/Contents")] = writer._add_object(content)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class Probe:
    def __init__(self, stack):
        opts = {"region_name": "ap-southeast-1", "config": Config(connect_timeout=5, read_timeout=30, retries={"max_attempts": 1})}
        self.stack = stack
        self.cf = boto3.client("cloudformation", **opts)
        self.cognito = boto3.client("cognito-idp", **opts)
        self.aws_lambda = boto3.client("lambda", **opts)
        self.s3 = boto3.client("s3", **opts)
        self.outputs = {x["OutputKey"]: x["OutputValue"] for x in self.cf.describe_stacks(StackName=stack)["Stacks"][0]["Outputs"]}
        self.base = self.outputs["PolicyAssistantApiUrl"].rstrip("/")
        self.origin = self.outputs["FrontendUrl"].rstrip("/")
        self.pool = self.outputs["UserPoolId"]
        self.client_id = self.outputs["UserPoolClientId"]
        self.users = []
        self.passed = []
        self.stage = "initialization"
        self.policy_id = None

    def check(self, condition, name):
        self.stage = name
        if not condition:
            raise RuntimeError(name)
        self.passed.append(name)
        print("PASS", name, flush=True)

    def user(self, label):
        email = f"readiness-{uuid4().hex}-{label}@example.invalid"
        password = secrets.token_urlsafe(32) + "Aa1!"
        self.cognito.admin_create_user(UserPoolId=self.pool, Username=email, MessageAction="SUPPRESS", UserAttributes=[{"Name": "email", "Value": email}, {"Name": "email_verified", "Value": "true"}])
        result = {"username": email, "password": password, "token": None}
        self.users.append(result)
        self.cognito.admin_set_user_password(UserPoolId=self.pool, Username=email, Password=password, Permanent=True)
        self.login(result)
        return result

    def login(self, user):
        response = self.cognito.initiate_auth(ClientId=self.client_id, AuthFlow="USER_PASSWORD_AUTH", AuthParameters={"USERNAME": user["username"], "PASSWORD": user["password"]})
        user["token"] = response["AuthenticationResult"]["IdToken"]

    def request(self, user, path, method="GET", body=None):
        headers = {"Origin": self.origin}
        if user:
            headers["Authorization"] = "Bearer " + user["token"]
        response = requests.request(method, self.base + path, json=body, headers=headers, timeout=45, allow_redirects=False)
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        return response.status_code, payload, response.headers

    def upload(self, user, raw, name, wait=180):
        self.stage = "create upload session"
        code, data, headers = self.request(user, "/documents/upload-session", "POST", {"filename": name})
        self.check(code == 200, "create owned upload session")
        self.check(headers.get("access-control-allow-origin") == self.origin, "API CORS uses deployed frontend")
        self.stage = "S3 multipart upload"
        response = requests.post(data["upload_url"], data=data["upload_fields"], files={"file": (name, raw, "application/pdf")}, headers={"Origin": self.origin}, timeout=45, allow_redirects=False)
        self.check(response.status_code in (200, 201, 204), "presigned multipart upload")
        self.check(response.headers.get("access-control-allow-origin") == self.origin, "S3 CORS uses deployed frontend")
        code, result, _ = self.request(user, "/documents/submit", "POST", {"doc_id": data["doc_id"], "s3_key": data["s3_key"]})
        self.check(code == 200 and result.get("status") == "pending", "durable submission accepted")
        deadline = time.monotonic() + wait
        seen = None
        while time.monotonic() < deadline:
            code, status, _ = self.request(user, f"/documents/{data['doc_id']}/status")
            self.stage = "wait for processing"
            if code != 200 or status.get("status") == "failed":
                raise RuntimeError("Document processing failed: " + str(status.get("error_code", code)))
            if status.get("status") != seen:
                seen = status.get("status")
                print("Processing status:", seen, flush=True)
            if seen == "processed":
                self.check(status.get("page_count") == 1, "processed one-page document")
                return data["doc_id"]
            time.sleep(3)
        raise RuntimeError("Processing acceptance timed out")

    def run(self, include_ocr):
        self.check(self.request(None, "/health")[0] == 200, "public health")
        self.check(self.request(None, "/documents")[0] == 401, "unauthenticated library denied")
        self.stage = "public signup guard role"
        resource = self.cf.describe_stack_resource(StackName=self.stack, LogicalResourceId="SignupGuard")["StackResourceDetail"]["PhysicalResourceId"]
        probe = self.aws_lambda.invoke(FunctionName=resource, Payload=json.dumps({"triggerSource": "PreSignUp_SignUp", "request": {"userAttributes": {"email": "synthetic@example.invalid"}}, "response": {}}).encode())
        probe["Payload"].close()
        self.check(not probe.get("FunctionError"), "public registration guard executes with scoped IAM")
        self.stage = "create disposable test identities"
        first, second = self.user("a"), self.user("b")
        self.check(self.request(first, "/me")[0] == 200, "real Cognito JWT accepted")
        raw = pdf_bytes("Synthetic readiness policy. Refund requests must be submitted within 30 days.")
        doc_id = self.upload(first, raw, "synthetic-readiness.pdf")
        self.check(self.request(second, f"/documents/{doc_id}/status")[0] == 404, "cross-account status denied")
        self.check(self.request(second, f"/documents/{doc_id}/download")[0] == 404, "cross-account download denied")
        self.check(self.request(second, "/ask", "POST", {"question": "Refund deadline?", "document_ids": [doc_id]})[0] == 404, "cross-account source selection denied")
        self.check(self.request(second, "/documents")[1].get("documents") == [], "cross-account library empty")
        code, data, _ = self.request(first, f"/documents/{doc_id}/download")
        self.check(code == 200, "owner download URL")
        downloaded = requests.get(data["download_url"], timeout=30, allow_redirects=False)
        self.check(downloaded.status_code == 200 and hashlib.sha256(downloaded.content).digest() == hashlib.sha256(raw).digest(), "download byte hash matches original")
        self.stage = "multilingual sourced AI"
        code, answer, _ = self.request(first, "/ask", "POST", {"question": "Tôi được yêu cầu hoàn tiền trong bao nhiêu ngày?", "document_ids": [doc_id]})
        self.check(code == 200 and answer.get("grounded") is True and "30" in answer.get("answer", "") and any(c.get("doc_id") == doc_id and c.get("page") == 1 for c in answer.get("citations", [])), "Vietnamese AI answer grounded in English PDF")
        self.check(self.request(first, "/conversations")[1].get("conversations"), "owner conversation history")
        self.check(self.request(second, "/conversations")[1].get("conversations") == [], "cross-account history empty")
        self.check(self.request(first, "/admin/overview")[0] == 403, "customer cannot access administrator view")
        self.stage = "synthetic administrator provisioning"
        self.cognito.admin_add_user_to_group(UserPoolId=self.pool, Username=first["username"], GroupName="administrators")
        self.login(first)
        self.check(self.request(first, "/admin/overview")[0] == 200, "administrator group enforced")
        self.policy_id = "READINESS-" + uuid4().hex
        content = {"title": "Disposable synthetic policy", "category": "Readiness testing", "content": "Synthetic readiness content only. Refund within 30 days.", "keywords": ["readiness"]}
        self.check(self.request(first, "/admin/policies/" + self.policy_id, "PUT", content)[0] == 200, "administrator publishes shared policy")
        code, policy, _ = self.request(second, "/policies/" + self.policy_id)
        self.check(code == 200 and "search_chunks" not in policy and "content_lower" not in policy, "published policy omits internal indexing fields")
        self.check(self.request(first, "/admin/audit")[0] == 200, "administrator audit log")
        self.check(self.request(first, "/admin/policies/" + self.policy_id, "DELETE")[0] == 200, "synthetic policy deletion")
        self.policy_id = None
        if include_ocr:
            self.stage = "synthetic OCR acceptance"
            ocr_id = self.upload(first, scanned_pdf(), "synthetic-scan.pdf", wait=360)
            code, answer, _ = self.request(first, "/ask", "POST", {"question": "What is the refund deadline in this scanned policy?", "document_ids": [ocr_id]})
            self.check(code == 200 and answer.get("grounded") and "30" in answer.get("answer", ""), "live OCR text supports sourced answer")
        self.check(self.request(first, f"/documents/{doc_id}", "PATCH", {"title": "Renamed readiness test"})[0] == 200, "owner document rename")
        code, fresh_download, _ = self.request(first, f"/documents/{doc_id}/download")
        self.check(code == 200, "fresh download URL before purge")
        self.check(self.request(first, f"/documents/{doc_id}", "DELETE")[0] == 200, "permanent document deletion accepted")
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline and self.request(first, f"/documents/{doc_id}/status")[0] != 404:
            time.sleep(3)
        self.check(self.request(first, f"/documents/{doc_id}/status")[0] == 404, "deleted document no longer accessible")
        self.check(requests.get(fresh_download["download_url"], timeout=30, allow_redirects=False).status_code in (403, 404), "deleted source download denied")
        bucket = self.cf.describe_stack_resource(StackName=self.stack, LogicalResourceId="PolicyAssistantDocumentsBucket")["StackResourceDetail"]["PhysicalResourceId"]
        for prefix in (f"documents/{doc_id}/", f"quarantine/{doc_id}/"):
            pages = self.s3.get_paginator("list_object_versions").paginate(Bucket=bucket, Prefix=prefix)
            self.check(all(not page.get("Versions") and not page.get("DeleteMarkers") for page in pages), "all document versions purged: " + prefix.split('/')[0])

    def cleanup(self):
        failures = []
        if self.policy_id and self.users:
            try:
                self.request(self.users[0], "/admin/policies/" + self.policy_id, "DELETE")
            except Exception:
                failures.append("synthetic policy cleanup")
        pending = []
        for user in self.users:
            if not user.get("token"):
                # Identity creation succeeded but authentication failed: no app data exists.
                self.cognito.admin_delete_user(UserPoolId=self.pool, Username=user["username"])
                continue
            try:
                code, _, _ = self.request(user, "/account/delete", "POST", {"confirmation": "DELETE"})
                if code not in (200, 410):
                    failures.append("synthetic account deletion request: HTTP " + str(code))
                else:
                    pending.append(user)
            except Exception:
                failures.append("synthetic account deletion request")
        deadline = time.monotonic() + 240
        while pending and time.monotonic() < deadline:
            for user in pending[:]:
                try:
                    self.cognito.admin_get_user(UserPoolId=self.pool, Username=user["username"])
                except self.cognito.exceptions.UserNotFoundException:
                    pending.remove(user)
            if pending:
                time.sleep(5)
        if pending:
            failures.append("synthetic account purge still pending")
        if failures:
            raise RuntimeError("; ".join(failures))
        print("PASS synthetic account/data cleanup", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stack", default="policy-assistant")
    parser.add_argument("--ocr", action="store_true")
    args = parser.parse_args()
    probe = None
    ok = False
    cleaned = False
    try:
        probe = Probe(args.stack)
        probe.run(args.ocr)
        ok = True
    except Exception as exc:
        print("FAILED stage:", probe.stage if probe else "initialization", "error type:", type(exc).__name__, flush=True)
        if isinstance(exc, ClientError):
            print("AWS error code:", exc.response.get("Error", {}).get("Code"), flush=True)
        elif isinstance(exc, RuntimeError):
            print(str(exc), flush=True)
    finally:
        if probe:
            try:
                probe.cleanup()
                cleaned = True
            except Exception as exc:
                ok = False
                print("FAILED synthetic cleanup:", type(exc).__name__, flush=True)
            report = {"passed": ok, "checks": probe.passed, "ocr_requested": args.ocr, "test_accounts_cleaned": cleaned}
            folder = ROOT / ".deployment"
            folder.mkdir(exist_ok=True)
            (folder / "live-acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    raise SystemExit(0 if ok else 1)
