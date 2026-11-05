# Reviewed public release — 2026-10-30

Target: existing `policy-assistant` stack in Singapore, account 629380420098. Requested public self-registration and sourced AI functionality; operating budget target USD 30–50/month; notification budget set to USD 50.

Validation: 187 offline Python 3.12 tests, 18 frontend tests, production frontend build, SAM validation/build, and minimal live embedding/generation probes passed. Six Lambda handlers: API, orchestrator/worker, isolated PDF parser, stream dispatcher, recovery and signup guard. The parser has no S3, DynamoDB or Cognito IAM grant; only the orchestrator can invoke it and supply the short-lived version-pinned input URL.

Latest immutable Lambda zip SHA-256: `b3971f78369dac2aab0675dbb7973f7abbae158a2fe8021381a19fdf9eceaed6`.

Both metadata index migrations have completed, and recovery is enabled. The account-deletion fix change set `public-final-1793300471` completed successfully, adding the API's required UsageTable PutItem permission discovered by live account-deletion testing. Its template SHA-256 is `9007d21b577dea5b9ae5fc45dc6e680dcc8e792df4940408375ec05d517904a8`. Data tables, document bucket, user pool, client ID and queues were not removed or replaced. Historical automatically created worker logs remain intact; the worker writes to a managed v2 log group.

The application adds CloudFront/private frontend storage, Cognito hosted login, email alarms and account-budget notifications. SNS subscriptions need the recipient's email confirmation. The owner-selected administrator is granted only to a confirmed account. Existing sample policies are hidden until explicit administrative publication. Existing `uploads/` objects are preserved; two-day temporary cleanup applies only to new `quarantine/` objects.

The frontend was published after both indexes became active: https://djreo5eptvwk5.cloudfront.net/. CloudFront reports Deployed. Actual acceptance and remaining owner actions are recorded in final-verification.md. Source originals are backed up and file hashes are checked before applying the prepared source.


Vietnamese response follow-up: change set `public-final-1793331454` completed successfully. Original-template comparison showed only six immutable CodeUri keys changed; IAM statements, account configuration and data resources matched the previous template. Template SHA-256: `678282aa6c2a24ecea9bb8ff24546a03e124088a3ae67c28147cb499db450c35`. The API deployment checksum was verified. Evidence: language-fix-verification.md.

Earlier retail follow-up: `public-final-1793335754` completed from the canonical original repo. Section-based policy context and Japan Nova 2 Lite low reasoning replace the previous generation configuration. IAM permits only the Japan profile and its Tokyo/Osaka model destinations; embeddings/storage/OCR remain Singapore. Data resources were preserved. See retail-pilot-verification.md for test scope and three remaining answer-wording limitations.

Previous answer refinement: `public-final-1793345584` completed. Only immutable application artifact references changed in the source template; data-resource guard passed. A forced serialization schema and final validation reject malformed/truncated output and unknown source IDs before history writes. No model-selected transaction or external tool is executed. Final evidence: 169 tests passed, 11 opt-in live skipped; 30 public-policy requests completed without errors (three secondary semantic/style notes); nine authenticated HTTP questions passed and test identity cleanup confirmed. See retail-pilot-verification.md.

Latest administrator release: `public-final-1793347694` completed. Three authenticated admin catalogue/detail/edit routes were added. Existing IAM data access, Cognito configuration, storage, quota/budget/model configuration and previous routes were preserved; API invoke permissions cover the new routes. Separate drafts, explicit publish/archive/discard and conditional policy+audit transactions protect live content and stale edits. Frontend fingerprints retain old asset compatibility. 187 Python/18 frontend tests, 16 live admin checks and four real AI HTTP questions passed. Cleanup and CloudFront invalidation were confirmed. Evidence: admin-verification.md.

## Current support/source-scope release

`public-final-1793350855`; Lambda SHA-256 `34358298ca99b859430600d21a01efac12dc0872ca74a391a99053e10e823500`; template SHA-256 `3fb19ef3066ab2fa614cf23b4905b98529819dd497ca4fd6a304ac6d8e3ca4e4`. Adds SupportTable, eight JWT-protected routes, scoped SupportTable grants and UsageTable transaction condition check. Existing identity/storage resources preserved by release guards. 209 Python/26 frontend passes and 28 live checks with successful synthetic data cleanup. Details and limitations: [support-verification.md](support-verification.md). Earlier paragraphs above are release history, not the latest immutable artifact.


Latest practical triage release (2026-11-04): 218 Python/28 frontend passes; 29 live support/API checks and successful disposable-account cleanup; no new model calls/PDF uploads. See [current verification](practical-release-verification.md). Earlier sections describe their respective historical releases.


Bản chính đã chọn ngày 04/11/2026: djreo5eptvwk5.cloudfront.net / policy-assistant. Thông tin shop có thể lưu nháp, công bố và ngừng công bố ngay trong quản trị. [Hướng dẫn cấu hình](HUONG-DAN-CAU-HINH-SHOP.md) · [Nghiệm thu hiện tại](shop-release-verification.md). Các báo cáo trên thuộc phạm vi bản phát hành tương ứng.
