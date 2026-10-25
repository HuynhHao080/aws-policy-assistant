# AWS Policy Assistant — bounded AI pilot completion

Status recorded on 25 October 2026: **LIVE_UI_ACCEPTANCE_PASS_BY_OWNER** for the TEST pilot. This is a dated deployment/acceptance summary, not a fresh service-health check or a production certification.

The deployed pilot includes reviewed local integration changes that have not yet been published to the repository's current main branch. Publishing this document alone does not make the deployed application reproducible from that branch. Source publication needs its own review and approval.

## Delivered functionality

- Policy lookup and keyword search, including the shared Customer Refund Policy.
- Owner-isolated PDF upload sessions, asynchronous byte/header/size verification, version/hash tracking, status and download flows. These are not OCR, malware scanning, semantic search or extraction of uploaded policy text.
- A personal document library with status display and refresh. Owner observations confirmed three documents and preserved statuses; separately approved read-only tests checked own-document access and cross-owner denial.
- A restricted AI panel with one fixed question about POL-001 and a server-validated answer/source reference. There is no free-text input or automatic inference when the page opens.

PDF functionality has historical implementation/test evidence; the final AI acceptance did not upload or mutate documents again.

## Architecture

CloudFront serves the static frontend from private S3. Cognito supplies the authenticated session; the existing client API flow sends requests to an API Gateway JWT authorizer. Existing Lambda handlers use DynamoDB for policy and owner-isolated document metadata. Document uploads use presigned S3 requests, SQS, a verification worker, a dead-letter queue and scheduled pending-work recovery.

AI uses a separate Lambda: authorization and approved-policy hash checks → bounded request validation → atomic DynamoDB quota/idempotency reservation → Bedrock Runtime Converse → structured answer validation → server-generated citation → frontend response/source validation.

The model is `apac.amazon.nova-lite-v1:0`, using the APAC inference profile from Singapore. The approved sample-data scope permits possible processing in Singapore, Sydney, Tokyo, Seoul, Osaka and Mumbai. Uploaded PDFs, private document metadata, JWTs, user identifiers and credentials are not sent to the model. The AI role has no S3/PDF permission; Bedrock access is scoped to the approved profile/model resources. Client visibility does not replace server authorization.

Nova Lite is forced to return `submit_policy_answer` tool input with `answer`, `policy_id` and `quote`. The backend verifies stop reason, tool/schema, allowed policy, exact quote, answer evidence and usage before generating a source reference. It does not execute an external tool or send a tool result.

## Deployment and acceptance timeline

| Date | Milestone | Evidence classification |
| --- | --- | --- |
| 24 October 2026 | TEST AI infrastructure deployed with the feature OFF; existing application checks continued through separate acceptance steps | Saved CloudFormation and read-only deployment evidence; deployment completion alone was not full acceptance |
| 25 October 2026 | Restricted AI-ON backend applied: one Bedrock policy added and the AI Lambda environment updated | Saved deployment/configuration verification; no claim that IAM simulation alone proved inference |
| 25 October 2026 | One authorized owner-operated API acceptance completed for the approved pilot identity | API response/citation PASS_BY_OWNER plus one-invocation bounded AWS runtime audit |
| 25 October 2026 | Four static frontend files released with configuration last and verified integrity/cache propagation | Saved release and offline/static verification |
| 25 October 2026 | Owner confirmed permitted/denied profile visibility and provided screenshot-derived answer/source evidence after one native UI click | LIVE_UI_ACCEPTANCE_PASS_BY_OWNER; offline source/hash comparison plus saved bounded AWS audit |
| Before activation acceptance | Synthetic CloudWatch alarm action reached the confirmed email recipient | END_TO_END_DELIVERY_PASS_BY_OWNER, corroborated by successful AWS action history; not a test of every threshold |

TestA and TestB below are role labels only, not login identifiers. The pilot is **TestA-only / POL-001 / one fixed synthetic refund-period question**. TestB is not authorized for AI and did not see the panel in owner observations.

## Observed answer, quota and usage

The displayed answer accurately stated a 30-day period from purchase for defective, damaged or not-as-described products. The displayed source was POL-001, `/policies/POL-001`, with the approved policy hash. The owner-transcribed answer matched the approved source excerpt and pinned answer/quote hash offline. This is not acceptance of unrestricted refund advice or arbitrary questions.

The API/helper request and native UI click were different admissions. Each bounded audit window contained one application ModelAttempts and usage of **588 input /85 output tokens**. Actual Errors, Fallbacks and QuotaDenied datapoints were zero in those windows. The two audited requests total 1176 input/170 output tokens; this is not the complete account or historical operator-trial total.

The first admission produced one idempotency record and five quota counters at one. The second added its own idempotency record and minute counters; the shared day/month counters increased to two. The implementation reserves idempotency plus five counters in one DynamoDB transaction. Snapshot consistency supports this bounded result, not a full transaction history or direct distributed trace. Reservations are not refunded after timeout or failure.

## Operating limits and retained exceptions

- User/global limits: 2 per minute and 5 per day; global 100 per month, using UTC buckets. Idempotency is scoped by user and UTC day. Existing attempt markers/ledger are not reset or replayed.
- Serialized model body <=2048 bytes; system <=512; messages <=512; tool configuration <=768; output <=200 tokens. No inference retry, fallback or streaming.
- CountTokens was not proven operational. The owner approved bounded-input control for this pilot; byte caps and post-response usage checks **do not guarantee <=6000 actual input tokens before inference**.
- UUID → Lambda association remains **INFERRED**, provider request ID **UNKNOWN**. UI evidence is **OWNER_PROVIDED_UI_EVIDENCE**, not an independently replayed browser/API capture. The screenshot contents were owner-reported; the original image was not independently inspected in the final reconciliation.
- TestB batch-control remains **FAIL** and the original TestB procedure **INCONCLUSIVE**. The owner accepted the observed denial security evidence with a documented exception; this was not retroactive authorization of the retired-batch dispatch. No denial rerun was used to erase the deviation.
- The native UI click was later clarified by the owner and preceded separate UI-click execution approval in the recorded workflow. Functional acceptance does not erase that procedural deviation.
- The OFF recovery procedure and conditional operating scope are prepared, but **live rollback is NOT TESTED**. OFF does not cancel in-flight inference. Frontend hiding is not a backend kill switch.
- CloudWatch → SNS → email delivery passed for the approved synthetic alarm-action test; this does not prove every threshold, future delivery or full audit continuity. Missing metrics are not zero failures.
- The monthly **USD 20 budget alert is not a hard spending cap**. Model tokens and AWS infrastructure have separate costs; billing/notifications can lag.

## Lessons and next steps

HTTP 200 is insufficient without output, evidence and citation validation. Structured tool output helps enforce a contract but does not establish factual correctness by itself. IAM simulation, availability metadata and runtime access are different forms of evidence. Logs, ledger reservations, usage and owner observations must retain their provenance.

Keep the existing narrow pilot and sanitized audit evidence. Future requests, additional users, free-text input, more policies, private-document processing, durable tracing or production rollout need their own security/data/cost review and approval. No new request or deployment is authorized by this summary.
