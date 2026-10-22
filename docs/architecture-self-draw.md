> D1 current-state note: C0 confirms45resources/4Retain; SNS0subscriptions, DLQ1/ALARM, Budget20USD external/account-wide with delivery unverified. Deployed API new ZIP; Worker/Recovery old ZIP. Environment end date not set. Reference only; student must draw/validate official-icon architecture themselves.

# Architecture worksheet — student must draw and explain the submitted diagram

Verified against `template.yaml` and `policy_assistant/app.py`, 2026-10-21; not a live AWS inventory. Download [official AWS architecture icons](https://aws.amazon.com/architecture/icons/), choose your drawing tool, create/edit the diagram yourself and keep its editable source and revision history. Existing `architecture.mmd`/PNG are reference artifacts only, not evidence of student authorship. No new diagram is supplied as a substitute for your own design.

## Components and rationale

| Boundary/component | IaC resource(s) | Role and reason |
|---|---|---|
| External browser | frontend/index.html, app.js | Native login, policy search, personal library, file/hash UX; untrusted client |
| Global delivery | FrontendDistribution, FrontendAccessControl, FrontendBucket | HTTPS static delivery; private S3 origin with OAC, no public website bucket |
| Identity | PolicyAssistantUserPool, PolicyAssistantUserPoolClient | Cognito Lite, administrator onboarding, public client without secret; managed JWT identity |
| Public API | PolicyAssistantApi | HTTP API validates JWT issuer/audience on protected routes; public /health is liveness only |
| API compute | PolicyAssistantFunction | Validation, owner checks, bounded search, signed S3 capabilities and submit state transition |
| Application storage | PoliciesTable, DocumentMetadata | On-demand policy reads and per-document state; ByOwner library and sparse ByStatus recovery indexes |
| Binary storage | PolicyAssistantDocumentsBucket | Private encrypted versioned PDFs; key chosen by server, immutable version chosen at submission |
| Async buffer | PolicyAssistantDocumentQueue, PolicyAssistantDocumentDLQ | Standard queue decouples short HTTP requests from verification, at-least-once retries, visible failed work |
| Async compute | PolicyAssistantWorker | Reads frozen version, validates header/size and SHA-256, conditional terminal update |
| Recovery | DocumentRecovery, RecoverPending scheduled rule | Queries due pending attempts every 2 minutes to repair metadata-to-queue crash gap |
| Operations | log groups, PolicyAssistantDashboard, five alarms, AlertTopic | 30-day JSON logs, latency/errors/backlog/DLQ; optional confirmed SNS email |

IAM roles are separate per function and scoped to required table/index, queue and S3-prefix ARNs. S3 TLS-only policies, public access block and SSE-S3 are declared. There is no VPC, NAT Gateway or endpoint in this application's IaC. S3/VPC learning pages are a separate lab.

## Draw these connections with labels

1. Browser → CloudFront → private frontend S3: HTTPS / signed OAC origin request. The S3 origin trusts the named distribution, not any anonymous reader.
2. Browser → Cognito: HTTPS authentication/challenge/refresh, public app client. Tokens stay in JS memory; password fields are cleared. Do not include actual tokens or passwords in the diagram.
3. Browser → HTTP API → API Lambda: bearer JWT verified at the gateway; trusted `sub` forwarded as authorizer claims. Mark `/health` public. Lambda's test events do not themselves validate JWT signatures.
4. API Lambda → policy table: GetItem or bounded Scan; all authenticated users share the policy catalogue. API Lambda → metadata: owner-tagged sessions, owner checks and conditional transitions; private document ownership differs from the shared catalogue.
5. API Lambda → browser → document S3: short-lived signed POST fields constrain key, MIME and 5–10 MiB range (minimum 5 bytes, maximum 10 MiB); this is a bearer capability. Anyone possessing the capability can use it until expiry. Do not draw S3 as validating a Cognito JWT. Do not put raw signed URLs on slides.
6. Browser → API submit → S3 HeadObject → metadata pending → SQS SendMessage: freeze `version_id` and `submission_id`. These are separate writes, not a cross-service atomic transaction. Recovery queries ByStatus and resends due attempts.
7. SQS → worker → exact S3 version → conditional metadata processed/failed. Duplicate/stale attempts do not overwrite newer state. Transient record failures return `batchItemFailures`; mapping enables ReportBatchItemFailures. Queue visibility 180 s, worker timeout 30 s, three receives then DLQ, DLQ retention 14 days. Permanent invalid PDF is failed/acknowledged intentionally.
8. Browser polls owner status and requests download → API signs GET for frozen version → S3 bytes → browser SHA-256 matches worker and original upload before reporting completion.
9. Functions → CloudWatch logs/metrics; queue → AWS/SQS metrics; five alarms → SNS topic; C0 found0subscriptions, so no confirmed-recipient arrow should be drawn as current state. Partial record failures may not increment Lambda Errors: backlog/age/DLQ and safe logs matter.

## Trust boundaries to show

Internet/untrusted browser; global CloudFront distribution; regional managed AWS services in ap-southeast-1; authenticated API boundary; owner-authorization checks in Lambda; privileged SDK roles; temporary S3 capability boundary; operational administrator access. Regional services do not imply a customer VPC. The browser cannot select owner_sub, bucket, storage key or worker role. No administrator credentials enter frontend/config.json. Mark administrative deployment access separately from application traffic.

## Design decisions and limits

| Decision | Benefit | Tradeoff / trigger to revisit |
|---|---|---|
| HTTP API + Lambda | Small managed MVP, no idle VM | Live JWT/CORS/IAM validation still required; Lambda API caught 5xx must be observed via API/UX and logs |
| On-demand DynamoDB | No fixed database instance; conditional updates | Keyword Scan is dataset-dependent; pagination is not a concurrent snapshot; monitor consumed reads |
| S3 POST + version pin | Storage enforces byte range; overwrite cannot change submitted version | Short-lived bearer capability remains shareable; MIME/header checks do not establish full PDF safety |
| SQS Standard + conditional attempt | Retry and duplicate safety with bounded worker | At-least-once delivery, DLQ/operator action, eventual consistency; recovery is not transactional outbox |
| CloudFront/OAC | Private origin and HTTPS UI | Separate publish/config/cache step, cache rollout must coordinate upload protocol changes |
| Cognito Lite/admin onboarding | Fits existing login without adding signup flows | MFA defaults off; no public registration/reset UX; user migration/tier changes need live review |
| Existing managed services, no VPC/NAT | Keeps cost and operations small | Does not claim private network traffic; use HTTPS and IAM boundaries |

## Well-Architected review

Use the [six AWS Well-Architected pillars](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-pillars-of-the-framework.html) as questions, not a certification claim.

- **Security:** owner-negative tests, trusted JWT claims, private storage, scoped IAM, bounded upload, no raw SDK/request secrets in logs. Remaining: owner rotates old demo credentials in history, AWS JWT/CORS/IAM proof, account MFA and deployment least privilege.
- **Reliability:** immutable versions, conditional attempt/state updates, partial batch failures, DLQ and scheduled recovery. Remaining: approved live fault injection, measured recovery time and restore exercise. No multi-region DR claim.
- **Operational excellence:** reproducible verifier and SAM build, runbook, JSON logs, queue/worker dashboard and five alarms. Remaining: real notification receipt, meaningful API failure-rate measurement and student-owned incident response.
- **Cost optimization:** dated gross estimate and load assumptions, on-demand compute/database, 30-day logs, no NAT/AI spend, explicit version retention. Remaining: budget recipient setup, actual consumed reads/duration/storage replacing assumptions.
- **Performance efficiency:** bounded Scan, indexes for owner/recovery and direct S3 transfer. Remaining: benchmark under approved representative load; no invented p95 or throughput.
- **Sustainability:** small managed footprint, avoid unused infrastructure and repeated tests/large artifacts. Remaining: clean up authorized demo resources and retained versions after evidence export.

## Student review checklist

- [ ] I drew the final diagram using current official icons and saved an editable source.
- [ ] Every box maps to an actual resource/code path; global/regional boundaries are clear.
- [ ] I can explain each arrow, identity, encryption and error path without reading an AI answer.
- [ ] I show no invented VPC/NAT/AI service or already-deployed claim.
- [ ] I can explain 404 owner isolation, POST policy, version pinning, duplicate attempts, retries/DLQ and recovery gaps.
- [ ] I show dated costs and name the assumptions I would measure in AWS.
- [ ] I inserted my diagram/evidence date into the Workshop and reviewed it against the actual deployed stack after approval.
