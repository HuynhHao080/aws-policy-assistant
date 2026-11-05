"""Untrusted PDF parsing runs with logging-only IAM permissions."""
import logging
import os
import re
from urllib.parse import urlparse, unquote
from urllib.request import build_opener, HTTPRedirectHandler

try:
    from .pipeline import extract
    from .service import Problem, MAX_BYTES
except ImportError:
    from pipeline import extract
    from service import Problem, MAX_BYTES

logging.getLogger("pypdf").disabled = True


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def handler(event, context):
    try:
        doc_id = event.get("doc_id", "")
        url = event.get("source_url", "")
        if not isinstance(doc_id, str) or not re.fullmatch(r"doc-[a-f0-9]{32}", doc_id) or not isinstance(url, str) or len(url) > 8192:
            return {"error_code": "invalid_parser_input"}
        parsed = urlparse(url)
        host = f"{os.environ['DOCUMENTS_BUCKET_NAME']}.s3.{os.environ.get('AWS_REGION', 'ap-southeast-1')}.amazonaws.com"
        if parsed.scheme != "https" or parsed.hostname != host or parsed.port not in (None, 443) or parsed.username or parsed.password or unquote(parsed.path) != f"/quarantine/{doc_id}/document" or parsed.fragment:
            return {"error_code": "invalid_parser_input"}
        with build_opener(NoRedirect).open(url, timeout=20) as response:
            raw = response.read(MAX_BYTES + 1)
        if not 0 < len(raw) <= MAX_BYTES:
            return {"error_code": "pdf_size_limit"}
        return extract(raw)
    except Problem as exc:
        return {"error_code": exc.message}
    except Exception:
        # Never log the signed source URL, request event or document contents.
        return {"retry": True}
