# Demo handover —8minutes, expandable to10

**D4 review, 2026-10-22:** the evidence-only 5–10 minute script below is ready for local presentation. Begin by stating B4 19 PASS, original B5 FAIL, B5-R7 10 PASS, and D3-A BLOCKED_PENDING_OWNER_OPERATIONAL_CONFIRMATION. End with the same security gate and owner confirmation still outstanding. No new login, sign-out, upload, download or AWS request is authorized by D4. The optional live column is a future plan requiring separate approval. Historical AWS counters/alarms/Budget are dated snapshots. See [D4 readiness](d4-final-readiness-review.md).

**D1 rehearsal is evidence-only: no login/upload/API business calls or AWS writes.** Use saved R7 screenshots/JSON and your own student-drawn diagram. A future interactive AWS demo would create Cognito sessions/data and needs separate authorization/quota; do not reuse the exhausted R7 approval. No video recording is claimed to exist.

Frontend reference: https://d3ataim7dfsl7t.cloudfront.net/ ; test stack policy-assistant-fcaj-test/ap-southeast-1. **Owner has not set the environment end date.** Before any future authorized live demo refresh identity/config/code hash/limits/Budget; if not healthy, present dated evidence without pretending it is live.

| Time | Say/show with saved evidence | If separately authorized for live demo |
|---|---|---|
|0:00–0:45|Problem: policy lookup and owner-isolated PDF byte/hash verification. No AI/OCR/RAG. State test environment and date.|Open frontend without exposing configuration secrets.|
|0:45–2:00|Use your official-icon diagram: CloudFront/private frontend S3; Cognito→HTTPAPI→API Lambda; DynamoDB; signed POST to private S3; SQS→Worker; EventBridge→Recovery; DLQ/CloudWatch/SNS.|No infrastructure changes needed.|
|2:00–3:30|R7 TestA login/search evidence, then regional S3 POST201, metadata processed and GET200; desktop screenshot.|TestA login→POL-001/refund→small prepared synthetic PDF→terminal processing→download; stop on failure, no repair/retry beyond quota.|
|3:30–4:30|Explain worker reads frozen version and current product returns original validated PDF, hence input/worker/S3/browser SHA256 should match. This is integrity, not semantic PDF validation.|Show only final hash/status, not Network headers/signed response.|
|4:30–5:30|Ownership: JWT validates identity; backend sub checks owner. R7 TestB cannot list TestA doc, UI status/download404; reverse direction also404. Three GlobalSignOut200 recorded.|Logout TestA, TestB login/own library and approved foreign synthetic ID checks; logout. No new users.|
|5:30–6:30|B4 retry/DLQ: one poison test historical, direct mixed event partial failure versus real BatchSize1 queue redrive. Current main0/DLQapprox1; do not rerun fault injection.|Read-only console observations only if separately authorized; never Receive/Delete/Purge.|
|6:30–7:20|C0:45resources/4Retain. Five alarms exist but SNS has0subscriptions; DLQ ALARM. Budget20USD account-wide, email delivery unverified, not hard cap. Gross6.6306USD model under stated load is not AWS forecast or idle-demo quote.|No Budget/SNS/retention changes.|
|7:20–8:00|Acceptance B4 19PASS, original B5 FAIL, API-only fix, R7 10PASS. GO test demo, NO-GO production. Close with cleanup A/B/C and end date still unconfirmed.|Stop after approved run; no cleanup.|

For5minutes shorten architecture/details, retain integrity/ownership and operational limitations. For10minutes add questions below and explain recovery gap/idempotency. Evidence paths: aws-browser-b5r7-result.md; evidence/approval-b5r7-browser.json; cleanup-c0-inventory-and-acceptance.md. R7 used3login/3logout/2sessions/2uploads/2downloads/1,218bytes/27dynamicrequests in17.702seconds; these are **past actual counters**, not a new demo allowance.

Never display credentials/JWT/refresh tokens/Authorization/complete Cognito responses/presigned URLs/POST signature fields. Use masked R7 screenshots, not an unfiltered browser trace. DPAPI protection is workstation-specific; no credential file is part of Git handover. Reviewer uses their own authorized access, not credentials in chat.

A failed original browser run is retained: global signer host did not fit regional CSP. Virtual addressing fixed POST/GET host; no CSP/CORS/IAM broadening; API-only deployment preserved Worker/Recovery. Do not call local fixtures AWS proof or use old NOT_RUN status to erase R7 evidence.

Production questions remain: confirmed alert recipients/delivery, Budget notification delivery, load/concurrency/SLO, restore rehearsal, identity/credential lifecycle and fuller security review. Student must explain architecture decisions in their own words; architecture.mmd is assistant reference, not proof of student authorship.

## Defense questions — answer in your own words

| Question | Answer checkpoints |
|---|---|
| Why HTTP API/Lambda/DynamoDB? | Managed small workload without idle VM; GetItem versus dataset-dependent bounded Scan, no invented full-text engine. |
| Where is JWT verified? | Gateway validates issuer/audience; Lambda trusts authorizer sub. A unit/direct Invoke event does not prove signature verification. |
| Why Bob gets 404? | Backend owner check denies unknown/unowned IDs; list/cursor is owner-bound. CORS and hidden buttons do not authorize data. |
| Does S3 validate Cognito? | No: temporary signed capability plus IAM/policy. Possession grants access until expiry; fields must remain private. |
| Why POST/versioning? | Storage-side key/MIME/size bound; frozen version survives overwrite. Header/MIME check is not parsing or malware scanning. |
| How are retries safe? | At-least-once queue, conditional state/attempt, harmless duplicates/stale messages, partial responses, receive limit and DLQ. Distinguish permanent invalid input from transient failure. |
| Is metadata-to-SQS atomic? | No; sparse due-time index and scheduled recovery repair a crash gap with safe duplicates. Database outage still needs an operator. |
| What proves partial failure? | Name the experiment: real direct mixed Invoke versus actual BatchSize 1 retry/redrive. Do not claim natural mixed SQS delivery without evidence. |
| Why Errors can be zero? | Partial response/caught HTTP 500 can be successful invocations; inspect HTTP status, safe logs, queue age/backlog/DLQ and actual alarms. |
| How is test isolated? | Separate stack/prefixed tables/private buckets/new users/scoped data ARNs. Existing resources remain unchanged. |
| What does USD 6.63 cover? | Assumed-load intended-system month including logs/alarms/dashboard, before allowances/credits/tax; existing stack, optional extras and actual use are separate. |
| Rollback and cleanup? | Stop failed rollout, restore compatible reviewed test artifacts/mapping as needed, retain document/table data. Deleting retained data needs owner-approved inventory. |

## Student architecture exercise

Use [the worksheet](architecture-self-draw.md) and [official AWS icons](https://aws.amazon.com/architecture/icons/). Draw it yourself, map every box to a real logical resource, label protocol/identity/data on every arrow and show global/regional/auth/owner/capability boundaries plus retry/DLQ/recovery. Save editable source/date. Practice explaining without reading generated answers. Assistant Mermaid/PNG is reference only and must not be submitted as student-authored design. Add the actual test endpoint and student diagram only after they exist.
