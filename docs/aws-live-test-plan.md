# Isolated AWS acceptance plan — NOT RUN

## B5-R — local fix đã kiểm chứng, chưa deploy

Edge local đã thu CSP connect-src violation với global S3 host; helper virtual addressing sinh regional POST/GET và fixture pipeline/hash PASS. Không đổi template/CSP/CORS/IAM/frontend. 129 backend,17 frontend,3 browser fixture,1 full-stack local PASS; SAM lint/build PASS;9 integration skip=NOT_RUN. [Hồ sơ B5-R](browser-b5r-remediation-review.md), [evidence](evidence/b5r-local-remediation.json).

B5 AWS vẫn FAIL. Chưa tạo change set vì artifact S3 mới đang bị cấm trong B5-R; cần duyệt upload/artifact/change set chưa execute, rồi execute/rerun riêng. Trạng thái chưa sửa local ở phần dưới là lịch sử B5.

## Trạng thái hiện hành — B5 browser FAIL, đã dừng

B5 chạy Edge thật lúc00:19:40–00:19:48 ngày22/10/2026 UTC+7: **2 PASS /1 FAIL /7 NOT_RUN**. Login/search TestA PASS; UI upload lỗi sau session200, chưa có S3 upload/download. Một metadata uploading còn lại; không rerun/fix/deploy/cleanup. Nguyên nhân khả dĩ CSP regional-only không khớp global S3 hostname của signer, chưa capture exact violation. [Báo cáo B5](aws-browser-b5-result.md), [phương án sửa chưa áp dụng](browser-b5-remediation-proposal.md).

**NO-GO browser acceptance.** B4 backend PASS là lịch sử riêng; không ghi browser PASS. Main queue0/QueueAge OK, DLQ1/ALARM, ba alarms Lambda OK. Mọi sửa/triển khai/rerun/cleanup cần duyệt riêng.

## Preparation B5 — read-only sau B4

00:07 ngày22/10/2026 UTC+7: main queue0, queue-age alarm tự OK; DLQ approx1 và DLQ ALARM, ba Lambda alarms OK. Không đọc lại message body, không nhận/xóa message hoặc test writes. [Hồ sơ B5](aws-browser-b5-approval.md) / [read-only evidence](evidence/approval-b5-readonly-review.json). Browser B5 NOT_RUN, chờ duyệt riêng; B4 dưới đây giữ như lịch sử.

## Trạng thái hiện hành — B4 API/SDK E2E hoàn tất

**19 PASS, 0 FAIL/BLOCKED, 1 NOT_RUN (browser thực tế)**. Authentication, hai chiều ownership, PDF/hash/10 MiB/MIME, worker và retry/DLQ thật đã kiểm chứng ngày 21/10/2026 16:47–16:57 UTC. Một poison, ba lần nhận ở queue chính (hai lần retry), DLQ còn 1; follow-up 16:59 UTC ghi DLQ/queue-age ALARM, ba alarms còn lại OK. Không reset/xóa để ép OK. [Báo cáo B4](aws-test-e2e-b4-result.md), [evidence](evidence/approval-b4-e2e.json).

**DỪNG: không tự cleanup, sửa/deploy hoặc commit/push. Browser E2E và email delivery chưa được chứng minh.** Các trạng thái AWS NOT_RUN ở lịch sử dưới đây đã được thay thế theo từng ca bởi báo cáo B4; không thay thế bằng blanket PASS.

B3 đã tạo và read-back hai users Enabled/CONFIRMED; [kết quả](aws-test-cognito-b3-result.md). Chưa đăng nhập hoặc phát hành token; B4 nghiệp vụ/retry/DLQ vẫn NOT_RUN và cần phê duyệt riêng.

B2 static frontend đã publish/verify qua HTTPS; [kết quả B2](aws-test-frontend-b2-result.md). B3 users/B4 nghiệp vụ vẫn chưa được duyệt; static GET không phải AWS E2E.

B1 infrastructure đã CREATE_COMPLETE; [kết quả B1](aws-test-deployment-b1-result.md). A01 control-plane readiness đã được đọc, nhưng chưa chạy runtime/E2E. Frontend/users/E2E cần B2/B3/B4 riêng; nội dung đề nghị execute dưới đây giữ như lịch sử phạm vi ban đầu.

Prepared 2026-10-21. Approval of the named CREATE change set **and the bounded test operations below** is required before execution. No mock or skipped test counts as AWS evidence. No AI/model access is required by this product.

## Hardening revision — preparation only

Use only the latest candidate in `aws-test-deployment-approval.md`; the older a9a40304 candidate is not approved. Before A01 verify three exact-group LogWritePolicy attachments, no broad managed logging/SQS policies, a byQueue DLQ allow policy pointing only to the new main queue, and Retain on both the document bucket and its HTTPS-deny policy. Wait for the entire stack and log policies/groups to be ready before invoking functions. Retention/bucket-policy behavior is verified from configuration; do not transmit a real signed capability/password over HTTP to demonstrate rejection. An anonymous HTTP 403 alone would not prove which deny mechanism caused it.

No test in this preparation deletes a stack to prove Retain. A destructive retention/cleanup experiment needs a separately approved disposable scope. A read-only post-cleanup check must later confirm that the retained bucket still has the TLS deny, public-access block and encryption. Account Budget 20 USD was created by the owner and its configuration is VERIFIED. Recipient is Active (legacy) per owner Console; email verification remains 0/1 and delivery is unverified. Tag Budget 10 USD remains pending. Approval B for deployment/E2E is NOT granted; see `aws-test-deployment-approval-b.md`.

## Target and write scope

STS-verified account ending **0098**, explicit region **ap-southeast-1**, new stack **policy-assistant-fcaj-test**. Validate the exact account/stack IDs against ignored local context, resource names and Environment=fcaj-test tag after creation before every write. Existing `policy-assistant`, its users, tables, objects, queues and logs are outside the write scope. Stop if source/template fingerprints differ from the approved candidate.

Included in requested approval: execute the named change set; seed three synthetic policies only into the new table; publish exactly four frontend/config files to the new frontend bucket and invalidate those assets; create two new test Cognito users with invitation suppressed, privately generated passwords and no email/SMS; exercise real API/S3/worker; send at most one poison SQS probe; directly invoke the test worker with a controlled mixed batch; read test logs/metrics/dashboard/alarms. Successful test queue messages are normally acknowledged by Lambda. No production fault injection, dependency shutdown, IAM weakening, queue purge or resource/data deletion is included.

The account Lambda concurrency limit observed is **10**, shared with two existing functions. Use sequential low-volume tests, no stress/load test or reserved-concurrency change. Stop on unexpected throttling. AlertEmail remains empty: no SNS email, budget subscription or claimed delivery receipt.

## Real AWS test matrix

| ID | Operation | Expected outcome and evidence |
|---|---|---|
| A01 | Inspect completed stack, functions, tables/indexes, storage policies and mapping | New resources only; functions Active, both GSIs ACTIVE, S3 versioning/BPA/TLS; sanitized live settings |
| A02 | Native Cognito login/logout with two users; missing/invalid JWT | Valid identity accepted, local state cleared; unauthenticated protected API denied; HTTP codes and safe screenshot |
| A03 | POL-001 lookup, refund search/pagination and invalid cursor | Correct shared catalogue results and validation; actual IDs/counts/codes |
| A04 | Synthetic syntactically valid PDF → signed POST → submit → poll → download | S3 201, processed state, frozen version, worker timestamp; original/worker/download SHA-256 equal |
| A05 | Bob list/submit/status/download Alice's document | Own library excludes document; submit/status/download 404 |
| A06 | One maximum+1-byte upload with real constrained POST | S3 rejects; no false submit success; size and rejection code, no signed fields in report |
| A07 | Tampered MIME/key POST; non-PDF bytes labelled PDF | Tampering rejected by S3; labelled bad bytes may upload but real worker sets INVALID_PDF, download 409 |
| A08 | Overwrite current version after submit; duplicate/re-submit | Frozen/downloaded original hash remains; no reset of terminal success |
| A09 | Direct real Lambda Invoke with one healthy and one failing SQS-shaped record using real test S3/DynamoDB | batchItemFailures contains only failed ID; healthy document completes; label this as direct invocation |
| A10 | One malformed message through actual SQS mapping | Retry then actual DLQ redrive, valid work continues; safe error classes/time window and observed SQS metadata/metrics |
| A11 | Mapping/queue/DLQ live attributes | ReportBatchItemFailures, BatchSize 1, visibility 180 s, maxReceiveCount 3, DLQ retention 14 days |
| A12 | CloudWatch logs/dashboard/five alarms; CloudFront UI/security headers and origin CORS | Real settings/states and bounded secret-pattern findings; real browser happy/negative cases; no invented OK or metric values |

## Retry/partial-batch evidence boundary

Reviewed mapping uses **BatchSize 1**. A real direct Lambda mixed event with real dependencies proves handler response semantics; it does not prove natural two-record SQS delivery. Actual event-source retry/DLQ is a separate experiment at BatchSize 1. Report both methods explicitly. A natural mixed-delivery test would require a separately approved temporary mapping change/restoration; do not silently introduce configuration drift.

Poison payload fails before touching any document. Allow about 15 minutes for 180-second visibility, three receives, redrive and metric propagation; record actual times. Do not reduce visibility or purge to manufacture fast results. Prefer DLQ attributes; if one scoped ReceiveMessage is needed, do not DeleteMessage, record its temporary visibility effect and let it become visible again. Leave diagnostic test messages/data for approved cleanup.

New alarms can be INSUFFICIENT_DATA; an intentional DLQ probe can cause ALARM. Record literal states. Partial failures and caught HTTP 500 may leave Lambda Errors zero, so correlate safe logs and queue metrics. This test does not prove SNS email delivery. Missing permissions, service availability or observed evidence are BLOCKED/FAIL, never PASS.

## Sanitized evidence and failure response

For every test save UTC start/end, exact candidate fingerprint, command/operation without credentials, expected/actual result, safe HTTP/AWS error code, artifact path and limits. Statuses: NOT_RUN/PASS/FAIL/BLOCKED. Passwords/JWTs/auth replies/signed URLs/POST fields stay in memory, never evidence. Screenshot only after passwords clear; exclude Network panels. Inspect raw logs privately/in memory and export only redacted excerpts or aggregate pattern findings with event count/time window; bounded scans are not proof of all possible leaks.

Stop on account/scope mismatch, unexpected replacement/deletion, denial, unavailable service, throttling or core acceptance failure. Preserve test state; do not widen IAM or edit the old stack to bypass a failure. Update both Workshop languages from actual execution only. Resource/data cleanup and existing-account credential changes require separate approval.
