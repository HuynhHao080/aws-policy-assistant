import io
import json
from unittest.mock import Mock

import pytest

from policy_assistant import pdf_parser
from policy_assistant.pipeline import parse_document
from tests.unit.pdf_fixture import pdf_bytes

DOC = "doc-" + "a" * 32
URL = f"https://test-documents.s3.ap-southeast-1.amazonaws.com/quarantine/{DOC}/document?signature=not-logged"


@pytest.mark.parametrize("url", ["http://test-documents.s3.ap-southeast-1.amazonaws.com/", "https://attacker.example/file", "http://169.254.169.254/latest/meta-data/", URL.replace("quarantine/", "another-prefix/"), URL + "#fragment"])
def test_parser_rejects_unapproved_sources_without_network(monkeypatch, url):
    monkeypatch.setenv("DOCUMENTS_BUCKET_NAME", "test-documents")
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
    opener = Mock()
    monkeypatch.setattr(pdf_parser, "build_opener", opener)
    assert pdf_parser.handler({"doc_id": DOC, "source_url": url}, None) == {"error_code": "invalid_parser_input"}
    opener.assert_not_called()


def test_isolated_handler_reads_only_selected_source_and_returns_text(monkeypatch):
    monkeypatch.setenv("DOCUMENTS_BUCKET_NAME", "test-documents")
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
    opener = Mock()
    opener.open.return_value = io.BytesIO(pdf_bytes())
    monkeypatch.setattr(pdf_parser, "build_opener", lambda *args: opener)
    result = pdf_parser.handler({"doc_id": DOC, "source_url": URL}, None)
    assert result["pages"] == 1 and "Refund" in result["chunks"][0]["text"]
    opener.open.assert_called_once_with(URL, timeout=20)


def test_isolated_parser_does_not_log_signed_url_on_network_failure(monkeypatch, caplog):
    monkeypatch.setenv("DOCUMENTS_BUCKET_NAME", "test-documents")
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
    opener = Mock()
    opener.open.side_effect = RuntimeError(URL)
    monkeypatch.setattr(pdf_parser, "build_opener", lambda *args: opener)
    assert pdf_parser.handler({"doc_id": DOC, "source_url": URL}, None) == {"retry": True}
    assert "not-logged" not in caplog.text


def test_missing_parser_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("PDF_PARSER_FUNCTION_NAME", raising=False)
    monkeypatch.delenv("ALLOW_LOCAL_PDF_PARSER", raising=False)
    with pytest.raises(RuntimeError, match="not configured"):
        parse_document(None, {}, pdf_bytes())


@pytest.mark.parametrize("payload", [{"pages": 1000, "chunks": []}, {"pages": 1, "chunks": [{"page": 2, "text": "bad"}]}, {"pages": 1, "chunks": [{"page": 1, "text": "x" * 1401}]}])
def test_parent_validates_untrusted_parser_results(monkeypatch, payload):
    monkeypatch.setenv("PDF_PARSER_FUNCTION_NAME", "isolated-parser")
    service = Mock()
    service.bucket = "test-documents"
    s3, aws_lambda = Mock(), Mock()
    s3.generate_presigned_url.return_value = URL
    aws_lambda.invoke.return_value = {"Payload": io.BytesIO(json.dumps(payload).encode())}
    service.client.side_effect = lambda name: s3 if name == "s3" else aws_lambda
    with pytest.raises(RuntimeError, match="Invalid"):
        parse_document(service, {"doc_id": DOC, "s3_key": f"quarantine/{DOC}/document", "s3_version": "v1"}, b"unused")
