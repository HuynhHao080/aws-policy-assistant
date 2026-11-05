"""Explicit live checks. Document mode creates synthetic AWS data; never run by CI."""
import argparse
import getpass
import hashlib
import json
import time
from urllib.parse import urlsplit

import boto3
import requests


def main(default_mode=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--region", default="ap-southeast-1")
    parser.add_argument("--mode", choices=["policies", "documents"], default=default_mode or "policies")
    args = parser.parse_args()
    url = urlsplit(args.api_url)
    if url.scheme != "https" or url.username or url.password or url.query or url.fragment:
        parser.error("Use an HTTPS API base URL without credentials or query parameters")
    try:
        password = getpass.getpass("Cognito password (not saved): ")
        auth = boto3.client("cognito-idp", region_name=args.region).initiate_auth(
            ClientId=args.client_id, AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": args.username, "PASSWORD": password})
        del password
        token = auth["AuthenticationResult"]["IdToken"]
        def api(path, method="GET", body=None):
            response = requests.request(method, args.api_url.rstrip("/") + path,
                headers={"Authorization": "Bearer " + token}, json=body, timeout=20, allow_redirects=False)
            if response.status_code != 200:
                raise RuntimeError(f"API returned HTTP {response.status_code}")
            return response.json()
        api("/policies/POL-001")
        api("/policies?keyword=refund")
        print("Authenticated policy lookup/search: PASS")
        if args.mode == "documents":
            data = b"%PDF-1.4\nSynthetic Policy Assistant verification fixture\n%%EOF"
            expected = hashlib.sha256(data).hexdigest()
            session = api("/documents/upload-session", "POST")
            print("Document ID:", session["doc_id"])
            upload = requests.post(session["upload_url"], data=session["upload_fields"],
                files={"file": ("synthetic.pdf", data, "application/pdf")}, timeout=30, allow_redirects=False)
            if not upload.ok:
                raise RuntimeError(f"S3 upload returned HTTP {upload.status_code}")
            api("/documents/submit", "POST", {"doc_id": session["doc_id"]})
            for _ in range(30):
                status = api(f"/documents/{session['doc_id']}/status")
                if status["status"] == "failed":
                    raise RuntimeError("Document processing failed")
                if status["status"] == "processed":
                    break
                time.sleep(2)
            else:
                raise RuntimeError("Worker timeout; document is not verified")
            info = api(f"/documents/{session['doc_id']}/download")
            download = requests.get(info["download_url"], timeout=30, allow_redirects=False)
            if not download.ok or hashlib.sha256(download.content).hexdigest() != expected or info["sha256"] != expected:
                raise RuntimeError("Download/integrity verification failed")
            print("Document upload/worker/download SHA-256: PASS")
        return 0
    except Exception as exc:
        # SDK/HTTP exception strings can contain URLs or credentials; print no raw exception/body.
        print("Live verification FAILED:", type(exc).__name__, "(details withheld; inspect sanitized service logs)")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
