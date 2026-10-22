"""Offline contract: signed document URLs must fit the deployed regional CSP."""
import base64
import json
from urllib.parse import parse_qs, urlsplit

from policy_assistant import app


def test_document_presigner_uses_regional_hosts_and_keeps_signature_constraints(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "LOCALFIXTURE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "LOCALFIXTURE")
    client = app._s3()
    post = client.generate_presigned_post(
        Bucket="fcaj-local-fixture", Key="uploads/doc-fixture/document",
        Fields={"Content-Type": "application/pdf", "success_action_status": "201"},
        Conditions=[{"Content-Type": "application/pdf"}, {"success_action_status": "201"},
                    ["content-length-range", 5, app.MAX_DOCUMENT_BYTES]], ExpiresIn=300)
    download = client.generate_presigned_url("get_object", Params={
        "Bucket": "fcaj-local-fixture", "Key": "uploads/doc-fixture/document",
        "VersionId": "fixture-frozen-version"}, ExpiresIn=300)

    expected = "fcaj-local-fixture.s3.ap-southeast-1.amazonaws.com"
    assert urlsplit(post["url"]).hostname == expected
    assert urlsplit(download).hostname == expected
    assert urlsplit(download).scheme == "https"
    assert urlsplit(download).path == "/uploads/doc-fixture/document"
    params = parse_qs(urlsplit(download).query)
    assert params["versionId"] == ["fixture-frozen-version"]
    assert params["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    assert params["X-Amz-Expires"] == ["300"]
    policy = json.loads(base64.b64decode(post["fields"]["policy"]))
    assert {"Content-Type": "application/pdf"} in policy["conditions"]
    assert ["content-length-range", 5, 10 * 1024 * 1024] in policy["conditions"]
    assert post["fields"]["key"] == "uploads/doc-fixture/document"
