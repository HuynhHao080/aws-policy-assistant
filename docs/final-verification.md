# Current acceptance — D1, 2026-10-22

B4 API/SDK19PASS; historical B5 browserFAIL; API-only B5-R6 UPDATE_COMPLETE; B5-R7 browser10PASS. C0:45resources/4Retain. GO bounded test demo; NO-GO production. D1 does not rerun AWS.

Open: DLQ1/ALARM; SNS0subscriptions; Budget20USD email delivery unverified; no cleanup/commit/push. **Environment end date not set by owner.** Prior password literals remain in Git HEAD; rotation/revocation proof is required before public push. DPAPI/private artifacts stay ignored.

[Authoritative D1 review](d1-handover-review.md), [demo script](demo-script.md), [R7](aws-browser-b5r7-result.md), [C0](cleanup-c0-inventory-and-acceptance.md). Local129unit/17frontend/3fixtures/1fullstack and private R4 extra case are separate from AWS evidence.

## Historical snapshots — superseded current-state statements

The earlier local-only dates/counts and pending/live-skipped statements below are retained as history, not current status.

# Verification record — 2026-10-21

Scope: local uncommitted changes after application handover `80c4eef` and worklog handover `846d2ff`. No AWS deployment, push, credential rotation or resource deletion was performed. GitHub Actions has been configured but not executed/verified for these unpushed changes.

| Check | Actual result | Environment / boundary |
|---|---|---|
| Python lint / backend mypy / JS syntax | **PASS** | Fatal-category lint; app.py typecheck; frontend syntax, not whole-repo strict typing |
| Backend `pytest tests/unit -q` | **120 passed** | Python 3.12.10, moto mocked DynamoDB/S3/SQS |
| Frontend `npm test` | **17 passed** | Node built-in test runner; mocked DOM/network |
| Browser `npm run test:browser` | **1 passed** | Real Edge headless; synthetic API/S3 fixtures |
| Full stack `npm run test:local` | **1 passed** | Real Edge → local HTTP adapter → real Lambda handlers → moto services |
| `python -m scripts.verify` | **PASS** | Offline orchestrator; machine-readable results in `docs/evidence/offline-acceptance.json` |
| Live `pytest tests/integration -q` | **9 skipped** | Opt-in variables absent; no live API calls |
| `sam.cmd validate --lint` | **PASS** | Current SAM template |
| `sam.cmd build` | **PASS** | Python 3.12.10 virtual environment with pip |
| Hugo temporary-directory build | **PASS** | v0.167.0; 124 EN / 123 VI pages; theme deprecation warnings |

## Coverage added

- Native Cognito login, new-password/internal-username and MFA challenges, refresh and failed remote signout are frontend-tested with fixtures.
- Owner-index library pagination, scheduled pending recovery, terminal failure/retry attempts and stale message rejection are covered by backend tests.
- User B cannot submit/status/download user A's document; unowned legacy records remain private; missing authorizer identity is rejected.
- Session S3 key cannot be substituted; missing object and malformed submit bodies are rejected.
- Submitted version remains frozen even after overwriting the current S3 object. Worker SHA-256 matches the original bytes, and download is version-specific.
- Queue failure is retryable without resetting version/timestamp; worker failure propagates and can succeed on retry; duplicate completed delivery is safe.
- Non-PDF byte content cannot become downloadable; pending documents return 409 for download.
- Real moto pagination returns every match without skips or duplicates, and invalid cursor shapes return 400.
- Frontend polling, timeout, 401, failed download, checksum mismatch and complete happy/failing flows.
- Actual browser downloads matching bytes, checks original/worker/download hash, handles 401/500 without false success, and fits a 390px mobile viewport. No page exceptions were observed.

## Screenshots

- `docs/evidence/full-stack-desktop.png` and `full-stack-mobile.png`: login, named private library and full PDF workflow against real local backend handlers with simulated AWS/authentication.

- `docs/evidence/frontend-desktop.png`: completed workflow using synthetic fixtures.
- `docs/evidence/frontend-mobile.png`: responsive layout and error handling, synthetic fixtures.

These are local browser evidence, not AWS live screenshots. No real JWT, password or presigned URL appears in them.

## Build note

Initial build attempts found Python 3.13 on PATH, then a Python 3.12 virtual environment without pip. A local `.venv` using the existing Python 3.12.10 interpreter and pip was prepared. With that environment on PATH, the final build succeeded for both the API function and the worker. Node verification ran on v26.3.0; installed test dependencies included pytest 8.4.2, moto 5.2.4 and boto3 1.43.116.

## Report/source hygiene

Hugo v0.167.0 built 124 EN / 123 VI pages (including non-HTML outputs). The generated-site checker inspected 125 HTML files and 11,638 internal href/src/fragment references with zero failures. Earlier root image paths and four child-page links were corrected; theme has three deprecation warnings. Existing history and user edits were retained. Secret-pattern checks are bounded and do not certify Git history. Previously committed passwords remain an owner-rotation requirement.

## Not verified in this iteration

Live stack/CloudFront deployment, native Cognito authentication, deployed IAM/JWT/CORS, two-user ownership on AWS, actual SQS redrive/DLQ alarms, performance, production cost and live SHA-256. Previous handover PASS statements are historical claims, not results for the current local implementation. The credentials previously committed must be rotated before further live testing; Git history has not been rewritten.

## P0 changes verified in this pass

Signed POST key/MIME/size policy; FormData field order/no JWT forwarding; malformed/base64/oversized bodies and ID bounds; no sensitive request/SDK message logging; mixed SQS batch failures and terminal failed-attempt redrive; controlled S3 HeadObject 403; non-overwriting repeatable seed. Storage policy enforcement, queue timing and TLS/IAM effects still need AWS proof. Dashboard uses queue/worker/recovery and separate average duration; Errors alone does not reveal partial failures.

Generated EN/VI Workshop and COST pages were also opened in headless Edge at desktop and 390px mobile sizes. Four page/language combinations have zero page exceptions and no document overflow after table/heading-anchor fixes; see `docs/evidence/worklog-browser.json`. The current bounded source pattern scan checked 169 text files with zero high-confidence AWS key/JWT/presigned-signature matches; it does not certify other secret formats or Git history.


## Hardened candidate revision — 2026-10-21

Current candidate `fcaj-review-20261021-072124-24ba855e` has 45 Add actions; no execution authorized. Local full verifier passed: 128 backend, 17 frontend and two browser suites, lint/typecheck, SAM validate/build. Nine live tests are skipped, not AWS proof. Cached actual processed-template IAM audit passes; fresh AWS reads and ZIP integrity are tracked separately and remain blocked until a successful timestamped check. See [approval packet](aws-test-deployment-approval.md) and `evidence/aws-review-artifact-fingerprint.json`. Earlier counts/status below describe older revisions.
