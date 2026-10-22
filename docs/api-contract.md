# API Contract â€” current local source

Updated 2026-10-21. This describes source behavior, not a live deployment assertion.

All protected routes require a Cognito JWT accepted by API Gateway. Document routes additionally require a nonempty `sub` in API Gateway authorizer claims. Lambda does not validate an arbitrary client-supplied JWT itself. `/health` is public and checks handler liveness only.

## Policy routes

`GET /policies/{policy_id}`: 200 policy without internal lowercase fields; 404 unknown ID; 400 empty ID.

`GET /policies?keyword=...`: keyword is required; `limit` is optional (1â€“100); `next_token` is optional, a base64 JSON resource key `{"policy_id":"..."}`. Invalid cursor shapes return 400. Response fields: `policies`, `count`, `scanned_count`, `truncated`, `next_token` (null when finished). Scans evaluate at most 1,000 records per request. Each Scan page evaluates at most the remaining requested match count, so no matching items are discarded behind the cursor. A cursor is for continuing the same keyword on a stable dataset.

## Document routes

### POST /documents/upload-session

Optional JSON body: `{"filename":"policy.pdf"}`. Filename is display-only, normalized to a basename and limited to 180 characters; the server independently chooses the storage key. Returns 200 with `doc_id`, `s3_key`, `upload_url`, `content_type` (`application/pdf`), `max_bytes` (10485760), `expires_in` (300). Metadata stores the authenticated owner and state `uploading`. The S3 URL is a credential: do not persist it in evidence.

Upload via multipart **POST** to `upload_url`: append every `upload_fields` value then append the file last. Let the browser set the multipart Content-Type boundary. The signed policy constrains key, PDF MIME type and 5–10,485,760 bytes at S3. Do not forward the Cognito Authorization header to S3; fields/URL/signature are temporary capabilities and must not be copied into reports. The response includes `upload_method: "POST"` and `upload_fields`.

### POST /documents/submit

Body: `{"doc_id":"<returned ID>"}`. A legacy `s3_key` is accepted only if it exactly matches the server session. Invalid JSON/body/ID: 400. Unowned/unknown/legacy document: 404. Missing S3 object: 409 when S3 returns 404; without ListBucket, ambiguous S3 HeadObject 403 becomes controlled 503 without enqueue/state transition (upload completion or IAM needs inspection). Invalid content type/size: 400. Disabled versioning or unavailable queue: 503. Concurrent submission transition: 409; retry the same ID.

Successful initial submission freezes the current S3 version and records an ISO-8601 UTC `submitted_at`, changes `uploading` to `pending`, and sends SQS the document ID plus a unique `submission_id`. Due pending work is recoverable by the scheduled dispatcher if the process exits before queue send. Pending retries re-enqueue the same frozen version. Processed retries return `processed` without resetting state. A failed enqueue returns 503 and can be retried using the same ID; scheduled recovery also covers this gap. A document failed with `PROCESSING_FAILED` can be submitted again as a new attempt over the same immutable version. `INVALID_PDF` is terminal for that version and returns 409 on retry; create a new upload.

### GET /documents/{doc_id}/status

Returns 200: `doc_id`, `filename`, `status`, `created_at`, `submitted_at`, `processed_at`, `failed_at`, `error_code`, `sha256`; unavailable timestamps/hash are null. Owner identifiers and S3 keys are not exposed. Other users and legacy unowned records receive 404.

### GET /documents/{doc_id}/download

Returns 200: `doc_id`, `download_url`, `sha256`, `expires_in` (300), only after `processed`. The URL targets the immutable submitted version and requests an attachment filename. Unprocessed: 409; unknown/unowned: 404.

### GET /documents

JWT and owner identity required. Optional `limit` is 1â€“50 (default 20); `next_token` is a base64 JSON resource key containing exactly `doc_id`, `owner_sub` and `created_at`. The cursor must belong to the current owner. Invalid limit/cursor returns 400. Returns 200 with `documents` and `next_token`; entries contain display filename, ID, state, timestamps, hash and failure code only. Neither owner ID nor storage key/version is exposed. The ByOwner index returns newest sessions first and is eventually consistent. `/Prod/documents` is supported by stage normalization.

## Worker and recovery semantics

The worker checks the PDF header/size and hashes the exact submitted version. `processed` is byte verification, not OCR/malware scanning. Duplicate success and stale submission-attempt messages have no side effects. Invalid bytes become `failed / INVALID_PDF` and are acknowledged as permanent input errors. Transient errors return their message IDs in `batchItemFailures`; the event mapping enables `ReportBatchItemFailures`. Other batch records continue. The third delivery records `failed / PROCESSING_FAILED` before returning a batch failure for redrive. Terminal-state writes are best-effort during a DynamoDB outage.

The two-minute recovery function queries up to 20 due `pending` entries through ByStatus, sends the same attempt and advances its deadline by 120 seconds. Send failure leaves the entry due; updates are conditional on pending state/current attempt. This closes the eventual metadata/queue-send gap without changing the version. Live queue redrive, schedule, IAM and consistency behavior still require AWS acceptance.
