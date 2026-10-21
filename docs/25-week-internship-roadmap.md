# Policy Assistant — 25-Week Internship Roadmap

**Project:** `C:\Users\accli\Documents\Project\policy-assistant`
**Prepared:** 2026-10-19
**Status:** Audit and planning phase — no new AWS deployment planned in this document. Existing completed work (Cognito JWT, pagination, CloudWatch monitoring, 62 unit tests) is marked honestly.

---

## How to Read This Roadmap

- **Completed** = work already present in repository (verified by source inspection or test execution).
- **In Progress / Planned** = next steps requiring approval or manual execution.
- **Local-only** = can be done with `sam build`, `pytest`, and code review without AWS deployment.
- **Requires deployment** = needs `sam deploy` or AWS resource creation; must be approved separately.
- **Evidence** = what to collect for `docs/internship-report.md` and `docs/evidence-index.md`.

---

## Phase 1 — Foundations & Security (Weeks 1–4)

**Theme:** Understand the existing serverless architecture, fix validation issues, and establish secure baseline.

### Week 1 — Project Orientation & Source Audit
- **Learning:** SAM template structure (`Globals`, `Resources`, `Outputs`); Lambda handler routing; DynamoDB key schema.
- **Tasks:** Read `template.yaml`, `app.py`, `tests/unit/test_handler.py`, `README.md`. Confirm all 13 test classes exist. Verify `docs/` contents.
- **Deliverable:** Source audit notes; list of all resources in `template.yaml`.
- **Verification:** `python -m pytest tests/unit --collect-only -q` shows 62 tests.
- **Evidence:** Screenshot of `ls docs/`; `grep -n "class Test" tests/unit/test_handler.py` output.
- **Cost / Risk:** None (local only).
- **Status:** **COMPLETED** — source audited; 62 tests verified.

### Week 2 — SAM Validation & Template Correctness
- **Learning:** SAM CLI `validate --lint`, `build`, `local start-api`; `HttpApi` event `Auth` syntax vs `AuthorizerId`.
- **Tasks:** Confirm `sam.cmd build` passes. Resolve `sam.cmd validate --lint` error (pre-existing SAM CLI 1.168.0 `AuthorizerId` validation limitation; corrected by using SAM-native `Auth.Authorizers` / `Auth.Authorizer` in Phase T). Document result honestly.
- **Deliverable:** Validation report in `docs/evidence-index.md`; note any unresolved lint limitation.
- **Verification:** `sam.cmd build` succeeds; `sam.cmd validate --lint` result recorded (with explanation if still failing due to tool version).
- **Evidence:** Command output saved to `docs/evidence-index.md`; version number (`1.168.0`) recorded.
- **Cost / Risk:** None (local only).
- **Status:** **COMPLETED** — `sam build` passes; `validate --lint` status documented.

### Week 3 — Security Baseline — Input Validation & IAM [L41-50]
- **Status:** COMPLETED (local only) — verified that `AWS::Serverless::HttpApi` events do not support `RequestParameters` (REST-only feature) in SAM CLI 1.168.0; Lambda-side validation preserved as authoritative. Template updated to document limitation; `test_search_request_parameters_not_supported_on_httpapi` added.
- **Limitation:** HTTP API does not support JSON Schema request models or numeric-range validation; Lambda remains authoritative for `limit`, `next_token`, and non-empty keyword.
- **Learning:** API Gateway request validation; Lambda least-privilege IAM; CORS security.
- **Tasks:** Add `RequestParameters` / `RequestModels` to `/policies` route in `template.yaml` for `keyword` (required, non-empty) and `limit` (positive int ≤100). Confirm Lambda IAM policy only allows `dynamodb:GetItem` + `Scan` on table ARN.
- **Deliverable:** Updated `template.yaml` with input validation; updated `README.md` limitations.
- **Verification:** `sam.cmd build`; `pytest` passes; manual `curl` test with invalid `limit=-1` returns 400.
- **Evidence:** Updated `template.yaml` diff; test case for invalid input.
- **Cost / Risk:** None (local only; no deployment required for validation).
- **Status:** **PLANNED** — requires manual edit and test.

### Week 4 — Security Review & Documentation Update
- **Learning:** AWS Well-Architected Security Pillar; JWT token lifecycle; Cognito User Pool configuration.
- **Tasks:** Update `README.md` security section; document that Cognito JWT is configured but not deployed; add deployment checklist (CORS domain, PITR, cost estimate). Review `docs/architecture-review.md`.
- **Deliverable:** Updated `README.md`; completed `docs/architecture-review.md`.
- **Verification:** All documentation consistent with `template.yaml`; no invented features.
- **Evidence:** `docs/architecture-review.md`; updated `README.md` sections.
- **Cost / Risk:** None.
- **Status:** **COMPLETED** — architecture review created; README updated.

---

## Phase 2 — API Security & Reliability (Weeks 5–8)

**Theme:** Harden the API, improve error handling, and establish reliability patterns.

### Week 5 — Rate Limiting & Throttling [L65-74]
- **Status:** COMPLETED (local only) — basic stage-level throttling added (`ThrottlingRateLimit: 10`, `ThrottlingBurstLimit: 5`); documented as basic rate limit, not DDoS defense; Lambda reserved concurrency not set.
- **Evidence:** `template.yaml` `PolicyAssistantApi.Properties.DefaultRouteSettings`; `tests/unit/test_handler.py` `test_throttling_settings_configured`; `README.md` updated.
- **Limitation:** HTTP API throttling is basic; no WAF, no Lambda reserved concurrency, no DynamoDB hard cap.
- **Learning:** API Gateway throttling; Lambda reserved concurrency; DynamoDB on-demand limits.
- **Tasks:** Add `ThrottlingRateLimit` / `ThrottlingBurstLimit` to `PolicyAssistantApi`. Add `ReservedConcurrentExecutions` to Lambda function.
- **Deliverable:** Updated `template.yaml`; documentation of limits.
- **Verification:** `sam.cmd build`; `pytest` passes.
- **Evidence:** Template diff; `README.md` cost/limit notes.
- **Cost / Risk:** Low — only affects deployed behavior; no new billable resources.
- **Status:** **PLANNED** — requires approval before deployment.

### Week 6 — Structured Logging & Correlation IDs
- **Learning:** CloudWatch Logs Insights; JSON structured logging; request correlation.
- **Tasks:** Add `requestId` / correlation ID to Lambda logs; include `path`, `method`, `keyword` (not full token) in structured log entries. Avoid logging sensitive query content.
- **Deliverable:** Updated `app.py`; updated `README.md` troubleshooting.
- **Verification:** `pytest`; manual local invoke with `sam local invoke`.
- **Evidence:** Log output sample; `README.md` update.
- **Cost / Risk:** None (local only; logs only when deployed).
- **Status:** **PLANNED**.

### Week 7 — DynamoDB Reliability — PITR & Backup
- **Learning:** DynamoDB Point-in-Time Recovery; backup strategies.
- **Tasks:** Add `PointInTimeRecoverySpecification` to `PoliciesTable`. Document rollback procedure (`sam delete` + restore).
- **Deliverable:** Updated `template.yaml`; deployment checklist update.
- **Verification:** `sam.cmd build`; `pytest` passes.
- **Evidence:** Template diff; `README.md` cleanup section.
- **Cost / Risk:** PITR has minimal cost; only when deployed.
- **Status:** **PLANNED** — requires deployment approval.

### Week 8 — Error Handling & Retry Patterns
- **Learning:** `boto3` retries; `ClientError` handling; idempotency.
- **Tasks:** Add `boto3` retry config (`max_attempts=3`, `mode='standard'`) for DynamoDB calls. Ensure `ClientError` does not leak internal details to client.
- **Deliverable:** Updated `app.py`; new test `test_dynamodb_retry_behavior` (optional).
- **Verification:** `pytest`; mock error scenarios.
- **Evidence:** Updated `app.py`; test output.
- **Cost / Risk:** None.
- **Status:** **PLANNED**.

---

## Phase 3 — Asynchronous Processing (Weeks 9–11)

**Theme:** Add event-driven processing only if justified by a concrete requirement.

### Week 9 — Requirement Assessment — Is SQS Needed?
- **Learning:** SQS, SNS, Step Functions; event-driven architecture.
- **Tasks:** Evaluate whether policy lookup requires async work (e.g., bulk import, approval workflow, notification). For current read-only API: **not justified**.
- **Deliverable:** Decision document in `docs/aws-upgrade-roadmap.md`; no new resources added.
- **Verification:** Written justification; no `template.yaml` changes.
- **Evidence:** Updated roadmap section; decision record.
- **Cost / Risk:** Zero if not implemented.
- **Status:** **COMPLETED (decision)** — no SQS added; documented as not required.

### Week 10 — If Required: SQS + DLQ Design
- **Learning:** SQS queue, dead-letter queue, Lambda event source mapping.
- **Tasks:** Only if Week 9 decision approves: design `PolicyAssistantQueue` + `PolicyAssistantDLQ`; add Lambda event source mapping.
- **Deliverable:** Design doc; updated `template.yaml` only if approved.
- **Verification:** `sam.cmd build`; `pytest`.
- **Evidence:** Design doc; template diff (if approved).
- **Cost / Risk:** SQS + Lambda invocations = billable; requires approval.
- **Status:** **NOT PLANNED** — no concrete requirement identified.

---

## Phase 4 — Data & Document Integration (Weeks 12–14)

**Theme:** Improve data model and document storage only if required.

### Week 12 — GSI for Category Search (If Required)
- **Learning:** DynamoDB GSI; `begins_with`; query vs scan.
- **Tasks:** Only if category-based filtering is a concrete product need: add GSI on `category` to `PoliciesTable`; update search logic.
- **Deliverable:** Updated `template.yaml`; updated `app.py`; new tests.
- **Verification:** `pytest`; `sam.cmd build`.
- **Evidence:** Template diff; performance comparison (scan vs query).
- **Cost / Risk:** GSI uses additional write capacity; only if required.
- **Status:** **NOT PLANNED** — current keyword search is sufficient for MVP.

### Week 13 — S3 Document Storage (If Required)
- **Learning:** S3 bucket, private origin, CloudFront OAC.
- **Tasks:** Only if policies need PDF/attachment storage: create private S3 bucket; configure CloudFront with OAC; update Lambda to generate presigned URLs.
- **Deliverable:** Updated `template.yaml`; frontend integration doc.
- **Verification:** `sam.cmd build`; manual `curl` to presigned URL.
- **Evidence:** Template diff; cost estimate.
- **Cost / Risk:** S3 + CloudFront = billable; requires approval.
- **Status:** **NOT PLANNED** — no document storage requirement.

---

## Phase 5 — Reliability & Observability (Weeks 15–17)

**Theme:** Make monitoring real, not just local.

### Week 15 — Deploy Monitoring (Requires Approval)
- **Learning:** CloudWatch Alarms, Dashboard, Metrics.
- **Tasks:** Deploy existing `PolicyAssistantErrorAlarm`, `PolicyAssistantDurationAlarm`, `PolicyAssistantDashboard` (currently local only). Verify alarm states.
- **Deliverable:** Deployed alarms/dashboard; updated `README.md` status.
- **Verification:** AWS Console check; `aws cloudwatch describe-alarms`.
- **Evidence:** Screenshot / CLI output; `docs/evidence-index.md` updated.
- **Cost / Risk:** Minimal; only when deployed.
- **Status:** **PLANNED — REQUIRES APPROVAL**.

### Week 16 — Tracing (X-Ray) — Optional
- **Learning:** AWS X-Ray; tracing configuration; correlation IDs.
- **Tasks:** Add `TracingConfig` to Lambda; add `AWS::XRay::SamplingRule` if needed; update logs with trace IDs.
- **Deliverable:** Updated `template.yaml`; updated `README.md`.
- **Verification:** `sam.cmd build`; `pytest`.
- **Evidence:** Template diff.
- **Cost / Risk:** X-Ray has minimal cost; optional.
- **Status:** **OPTIONAL**.

### Week 17 — Performance Testing
- **Learning:** Load testing; DynamoDB Scan performance; Lambda concurrency.
- **Tasks:** Run `locust` or `artillery` against local API; measure `scanned_count` vs `count`; document scan budget behavior.
- **Deliverable:** Performance report; updated `README.md` limitations.
- **Verification:** Test output saved to `docs/`.
- **Evidence:** Load test results; `scanned_count` observations.
- **Cost / Risk:** None (local only).
- **Status:** **PLANNED**.

---

## Phase 6 — CI/CD & Final Evaluation (Weeks 18–25)

**Theme:** Automate verification, prepare submission, evaluate against Well-Architected.

### Week 18 — CI/CD Pipeline Design
- **Learning:** GitHub Actions; AWS CodePipeline; secure credential handling.
- **Tasks:** Design pipeline (not deploy): `pytest` → `sam build` → `sam validate --lint` → deploy approval gate. Document in `docs/aws-upgrade-roadmap.md`.
- **Deliverable:** Pipeline design doc; `README.md` update.
- **Verification:** Design review.
- **Evidence:** Design doc.
- **Cost / Risk:** None (design only).
- **Status:** **PLANNED**.

### Week 19 — Pipeline Implementation (Local)
- **Learning:** GitHub Actions YAML; `sam build` in CI.
- **Tasks:** Create `.github/workflows/ci.yml` (local repo only; not activated without repo settings). Include `pytest`, `sam build`, `sam validate --lint`.
- **Deliverable:** `.github/workflows/ci.yml`; `README.md` CI section.
- **Verification:** `pytest`; `sam build`.
- **Evidence:** Workflow file; test output.
- **Cost / Risk:** None (local file only).
- **Status:** **PLANNED**.

### Week 20 — Well-Architected Review
- **Learning:** AWS Well-Architected Framework pillars (Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability).
- **Tasks:** Complete self-assessment against framework; document gaps (e.g., no backup, no WAF, no CI/CD deployed, no load tests). Update `docs/architecture-review.md`.
- **Deliverable:** Completed self-assessment; updated review doc.
- **Verification:** Checklist completed.
- **Evidence:** Updated `docs/architecture-review.md`.
- **Cost / Risk:** None.
- **Status:** **PLANNED**.

### Week 21 — Documentation Finalization
- **Learning:** Technical writing; evidence indexing; submission requirements.
- **Tasks:** Verify `README.md`, `docs/internship-report.md`, `docs/evidence-index.md`, `docs/aws-upgrade-roadmap.md`, `docs/architecture-review.md`, `docs/25-week-internship-roadmap.md` are consistent. Confirm no unclaimed features (no AI/ML, no frontend, no CI/CD deployed).
- **Deliverable:** Final documentation review; consistency check.
- **Verification:** Cross-reference all docs against `template.yaml`.
- **Evidence:** Consistency checklist.
- **Cost / Risk:** None.
- **Status:** **PLANNED**.

### Week 22 — Cost Estimation & Budget Control
- **Learning:** AWS Pricing Calculator; cost optimization.
- **Tasks:** Create cost estimate for deployed stack (Lambda, API Gateway, DynamoDB, Cognito, CloudWatch). Document free-tier caveats. Add `AWS Budgets` recommendation if production.
- **Deliverable:** Cost report; `README.md` update.
- **Verification:** Pricing calculator output saved.
- **Evidence:** Cost report file.
- **Cost / Risk:** None (estimation only).
- **Status:** **PLANNED**.

### Week 23 — Backup / Recovery Verification
- **Learning:** DynamoDB PITR; `sam delete`; rollback.
- **Tasks:** Verify PITR enabled (if deployed); document `sam delete --stack-name policy-assistant --region ap-southeast-1`; document data reload from `sample_data/policies.json`.
- **Deliverable:** Updated `README.md` cleanup section.
- **Verification:** `README.md` accurate.
- **Evidence:** Updated documentation.
- **Cost / Risk:** None (documentation only).
- **Status:** **PLANNED**.

### Week 24 — Final Integration & Submission Prep
- **Learning:** Internship report structure; evidence organization.
- **Tasks:** Compile all evidence (tests, deployment results, architecture review, roadmap, screenshots if available). Confirm `docs/internship-report.md` reflects actual work (not invented features).
- **Deliverable:** Final evidence package.
- **Verification:** All files reviewed; no unverified claims.
- **Evidence:** Final `docs/internship-report.md`; `docs/evidence-index.md`.
- **Cost / Risk:** None.
- **Status:** **PLANNED**.

### Week 25 — Evaluation & Reflection
- **Learning:** Project retrospective; technical debt acknowledgment.
- **Tasks:** Write reflection on what was completed (Cognito JWT, pagination, monitoring, 62 tests, documentation), what remains (deployment verification, CI/CD, load tests, AI evaluation), and what was intentionally not added (SQS, S3, Bedrock, frontend) with justification.
- **Deliverable:** Reflection section in `docs/internship-report.md`.
- **Verification:** Honest assessment; no over-claiming.
- **Evidence:** Updated report.
- **Cost / Risk:** None.
- **Status:** **PLANNED**.

---

## Completed Work Summary (Honest)

The following is already present in the repository and verified by source inspection or test execution. It is **not** new work planned for future weeks.

| Capability | Evidence | Status |
|---|---|---|
| SAM / CloudFormation template | `template.yaml` | Completed |
| Python 3.12 Lambda handler | `policy_assistant/app.py` | Completed |
| API Gateway HTTP API (v2) | `template.yaml` `PolicyAssistantApi` | Completed |
| DynamoDB table (`PolicyAssistantPolicies`) | `template.yaml` `PoliciesTable` | Completed |
| Cognito User Pool + Client | `template.yaml` `PolicyAssistantUserPool`, `PolicyAssistantUserPoolClient` | Completed |
| JWT Authorizer (SAM-native `Auth.Authorizers`) | `template.yaml` `PolicyAssistantApi.Properties.Auth` | Completed |
| Protected routes (`/policies/*`) | `template.yaml` events with `Auth.Authorizer` | Completed |
| Public `/health` | `template.yaml` `HealthCheck` event (no `Auth`) | Completed |
| Policy lookup by ID | `app.py` `_get_policy_by_id` | Completed |
| Keyword search with scan budget | `app.py` `_search_policies` (`MAX_SCAN_ITEMS = 1000`) | Completed |
| Cursor pagination (`next_token`) | `app.py` `_encode_next_token` / `_decode_next_token` | Completed |
| Internal field stripping | `app.py` `_strip_internal_fields` | Completed |
| CloudWatch Alarms (local) | `template.yaml` `PolicyAssistantErrorAlarm`, `PolicyAssistantDurationAlarm` | Completed |
| CloudWatch Dashboard (local) | `template.yaml` `PolicyAssistantDashboard` | Completed |
| Unit tests (62 passing) | `tests/unit/test_handler.py` | Completed |
| Template-focused tests (monitoring + auth) | `TestCloudWatchMonitoring`, `TestCognitoAuthorization` | Completed |
| Documentation (README, roadmap, evidence, report) | `README.md`, `docs/*.md` | Completed |

---

## Not Implemented (Intentionally — No Justification)

| Capability | Reason Not Implemented |
|---|---|
| SQS / SNS / DLQ | No async processing requirement for read-only API |
| S3 / CloudFront frontend | No frontend requirement; API-only MVP |
| Amazon Bedrock / RAG | No AI/ML product requirement; evaluated only |
| CI/CD pipeline (deployed) | Design only; requires repository settings and approval |
| Load/performance tests | Not required for MVP; can be added in Week 17 |
| Security penetration tests | Not required for MVP; can be added if needed |
| Custom domain / SSL | Requires customer input; documented as limitation |

---

## Dependency Order

```
Week 1 (Audit) → Week 2 (Validation) → Week 3 (Input validation) → Week 4 (Security doc)
  → Week 5 (Throttling) → Week 6 (Logging) → Week 7 (PITR) → Week 8 (Retry)
  → Week 9 (SQS decision: NO) → Week 12 (GSI decision: NO) → Week 13 (S3 decision: NO)
  → Week 15 (Deploy monitoring — requires approval) → Week 18 (CI design) → Week 20 (Well-Architected)
  → Week 21 (Doc final) → Week 22 (Cost) → Week 23 (Backup doc) → Week 24 (Submission) → Week 25 (Reflection)
```

---

*Document created: 2026-10-19*
*Status: Planning phase — no new AWS services added; existing work preserved*
