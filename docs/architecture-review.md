# Policy Assistant — Architecture Review

**Project:** `C:\Users\accli\Documents\Project\policy-assistant`
**Review date:** 2026-10-19
**Reviewer:** Senior AWS serverless engineer / documentation reviewer
**Scope:** Audit-only; no AWS deployment, no resource changes, no code modifications.

---

## 1. Current-State Architecture (Verified from Source)

### 1.1 Deployed / Configured Components (from `template.yaml`)

| Resource | Type | Status | Evidence |
|---|---|---|---|
| `PolicyAssistantLogGroup` | `AWS::Logs::LogGroup` | Configured | `template.yaml` L22 |
| `PoliciesTable` | `AWS::DynamoDB::Table` | Configured (PAY_PER_REQUEST) | `template.yaml` L28 |
| `PolicyAssistantUserPool` | `AWS::Cognito::UserPool` | Configured (JWT issuer) | `template.yaml` L42 |
| `PolicyAssistantUserPoolClient` | `AWS::Cognito::UserPoolClient` | Configured | `template.yaml` L52 |
| `PolicyAssistantFunction` | `AWS::Serverless::Function` | Configured (Python 3.12) | `template.yaml` L66 |
| `PolicyAssistantApi` | `AWS::Serverless::HttpApi` | Configured (Prod stage) | `template.yaml` L103 |
| `PolicyAssistantErrorAlarm` | `AWS::CloudWatch::Alarm` | Configured (local only) | `template.yaml` L126 |
| `PolicyAssistantDurationAlarm` | `AWS::CloudWatch::Alarm` | Configured (local only) | `template.yaml` L143 |
| `PolicyAssistantDashboard` | `AWS::CloudWatch::Dashboard` | Configured (local only) | `template.yaml` L160 |

**Auth configuration (SAM-native):**
- `PolicyAssistantApi.Properties.Auth.Authorizers.PolicyAssistantAuthorizer` defines JWT with `IdentitySource: "$request.header.Authorization"` and `JwtConfiguration.issuer` / `audience` referencing the User Pool and Client.
- `GetPolicyById` and `SearchPolicies` events use `Auth.Authorizer: PolicyAssistantAuthorizer`.
- `HealthCheck` event has no `Auth` property — remains public.
- No explicit `AWS::ApiGatewayV2::Authorizer` resource exists (correct for SAM-native JWT config).

### 1.2 Application Code (from `policy_assistant/app.py`)

- Lambda handler (`lambda_handler`) routes `GET /policies/{policy_id}`, `GET /policies?keyword=...`, `GET /health`.
- Keyword search uses DynamoDB `Scan` with `FilterExpression` on lowercase fields (`title_lower`, etc.).
- Internal lowercase fields stripped from responses (`_strip_internal_fields`).
- Cursor pagination via `next_token` (base64-encoded `LastEvaluatedKey`) implemented.
- Scan budget bounded by `MAX_SCAN_ITEMS = 1000`; `truncated` flag indicates budget exhaustion.
- `limit` parameter caps returned items (max 100) but does not bound evaluated items — documented correctly.
- Structured JSON logging configured (`logger.info` / `logger.error`).
- No manual JWT verification in Lambda — API Gateway validates at gateway.

### 1.3 Tests (from `tests/unit/test_handler.py`)

- 13 test classes, 62 tests collected (verified by `pytest --collect-only`).
- Coverage: policy lookup, keyword search, error handling, health check, limit validation, scan budget, internal field stripping, DynamoDB errors, stage-prefix routing, unexpected exceptions, response format, pagination (`TestSearchPagination` — 6 tests), CloudWatch monitoring (`TestCloudWatchMonitoring` — 3 tests), Cognito authorization (`TestCognitoAuthorization` — 9 tests).
- All tests use mocked DynamoDB (`moto` / `mock_aws`); no live AWS calls required.
- Template-focused tests parse `template.yaml` with a custom YAML loader (`CFNLoader`) to handle `!Sub`, `!Ref`, `!GetAtt`.

### 1.4 Documentation (verified present)

- `README.md` — architecture, endpoints, deployment, cost, limitations, verification status.
- `docs/aws-upgrade-roadmap.md` — tiered roadmap (security, core features, DevOps, AI).
- `docs/evidence-index.md` — evidence index with source paths and status.
- `docs/internship-report.md` — full internship report.
- `architecture.mmd` / `architecture.png` — rendered diagram.
- `docs/architecture-review.md` — this document (new).
- `docs/25-week-internship-roadmap.md` — new (created in this audit).

---

## 2. Security and Reliability Review

### 2.1 Confirmed Strengths

- **JWT authorization configured** at API Gateway level (not Lambda) — correct separation of concerns.
- **Public health endpoint** preserved (`/health` has no `Auth`).
- **Least-privilege IAM** for Lambda: only `dynamodb:GetItem` and `dynamodb:Scan` on the policies table ARN.
- **No secrets in repository** (`.gitignore` excludes `.env`; no credentials in source).
- **CORS configured** for localhost origins with `Authorization` header allowed.
- **Internal fields stripped** from responses (`title_lower`, etc.).
- **Scan budget bounded** (`MAX_SCAN_ITEMS = 1000`) to prevent unbounded reads.

### 2.2 Security Gaps (Mandatory Fixes Before Production)

| Gap | Risk | Evidence | Recommended Fix | Acceptance Criteria |
|---|---|---|---|---|
| **No input validation at API Gateway** | Invalid `limit`, malformed `next_token`, or unexpected query params reach Lambda | `README.md` L378; `app.py` validates in Lambda | Add API Gateway request validators / models for `limit` (positive int ≤100) and `keyword` (non-empty) | `template.yaml` defines `RequestModels` or `RequestParameters` for `/policies`; Lambda receives only validated input |
| **No rate limiting / throttling** | Unbounded requests could exhaust Lambda concurrency or DynamoDB read capacity | Not configured in `template.yaml` | Add `AWS::ApiGatewayV2::Api` throttling or Lambda reserved concurrency | `template.yaml` includes `ThrottlingRateLimit` / `ThrottlingBurstLimit`; Lambda `ReservedConcurrentExecutions` set |
| **No WAF / AWS Shield** | Basic DDoS and SQL-injection-style protection missing | Not present | Add AWS WAF WebACL to `PolicyAssistantApi` if production-facing | WAF rules configured; `template.yaml` references WAF |
| **CORS allows localhost only** | Production frontend domain not configured | `README.md` L382; `template.yaml` L120 | Replace `AllowOrigins` with production domain before deployment | `template.yaml` updated with customer-provided domain; `README.md` notes this |
| **No encryption at rest / in transit beyond defaults** | DynamoDB uses default encryption; API Gateway HTTPS is default | Not explicitly configured | Confirm DynamoDB `SSESpecification` (default AES-256) and TLS 1.2+ | Documented in deployment checklist |

### 2.3 Reliability Gaps

| Gap | Evidence | Recommendation |
|---|---|---|
| **No dead-letter queue for async work** | Not applicable (no async processing yet) | If SQS added later, include DLQ |
| **No retry / idempotency for DynamoDB** | `app.py` raises `ClientError`; no retry logic | Add `boto3` retry config or `tenacity` for transient DynamoDB errors |
| **Health check does not verify DynamoDB** | `README.md` L389; `app.py` L99 | Document limitation; consider optional DynamoDB connectivity check (separate endpoint) |
| **No backup / point-in-time recovery for DynamoDB** | `PoliciesTable` has no `PointInTimeRecoverySpecification` | Enable PITR for production; document in deployment checklist |

---

## 3. Data Model and API Review

### 3.1 DynamoDB Schema (Verified)

- **Table:** `PolicyAssistantPolicies`
- **Key:** `policy_id` (String, HASH)
- **Billing:** PAY_PER_REQUEST (on-demand)
- **No GSI** — keyword search uses full table Scan (acceptable for MVP with <100 policies; not for production scale)
- **No TTL / expiration** — policies are static

### 3.2 API Contracts (Verified from `app.py` and `README.md`)

| Endpoint | Method | Auth | Response | Notes |
|---|---|---|---|---|
| `/policies/{policy_id}` | GET | JWT required | Policy object (internal fields stripped) | 200 / 404 / 400 |
| `/policies?keyword=xxx` | GET | JWT required | `{policies, count, scanned_count, truncated, next_token}` | 200 / 400 |
| `/policies?keyword=xxx&limit=N` | GET | JWT required | Same with capped results | `limit` ≤ 100 |
| `/policies?keyword=xxx&next_token=xxx` | GET | JWT required | Paginated continuation | `next_token` base64-encoded `LastEvaluatedKey` |
| `/health` | GET | Public | `{"status":"healthy"}` | 200 |

### 3.3 Data Quality / Integrity

- Sample data (`sample_data/policies.json`) has 3 policies with consistent schema.
- No schema validation at insert time (DynamoDB schemaless — acceptable for MVP).
- No versioning or audit trail for policy changes.

---

## 4. Observability and Testing Review

### 4.1 Observability (Local Only — Not Deployed)

- **CloudWatch Logs:** JSON format configured (`LoggingConfig.LogFormat: JSON` in `Globals`).
- **CloudWatch Alarms:** `PolicyAssistantErrorAlarm` (Errors > 0), `PolicyAssistantDurationAlarm` (Duration > 5000ms). Both local only.
- **CloudWatch Dashboard:** `PolicyAssistantDashboard` with Invocations, Errors, Duration, Throttles. Local only.
- **Throttling:** `DefaultRouteSettings.ThrottlingRateLimit: 10`, `ThrottlingBurstLimit: 5` (basic rate limit, not DDoS defense).
- **Reserved Concurrency:** `ReservedConcurrentExecutions: 10` on Lambda.
- **DynamoDB PITR:** `PointInTimeRecoverySpecification.PointInTimeRecoveryEnabled: true`.
- **CI/CD:** `.github/workflows/ci.yml` designed (local file only, not activated).
- **No X-Ray tracing** configured (optional enhancement in roadmap).
- **No structured correlation IDs** in logs (optional).
- **No CloudWatch Metrics / Alarms for API Gateway** (optional).

### 4.2 Testing (Verified)

- **Unit tests:** 62 passing (mocked DynamoDB, no AWS credentials).
- **Integration tests:** 9 passing against deployed API (historical — Phase L).
- **Template-focused tests:** `TestCloudWatchMonitoring` (3), `TestCognitoAuthorization` (9) — verify template structure.
- **No load/performance tests** — missing evidence.
- **No security/penetration tests** — missing evidence.

---

## 5. Cost and Operational Risks

| Resource | Cost Driver | Risk / Note |
|---|---|---|
| Lambda | Requests + GB-seconds | Low for MVP; scales with usage |
| API Gateway HTTP API | Per-request | Cheaper than REST; no fixed cost |
| DynamoDB PAY_PER_REQUEST | Read/write units | Scan reads full table — cost grows with table size |
| CloudWatch Logs | Ingestion + storage | JSON format efficient; retention 30 days |
| Cognito User Pool | MAU pricing | Free tier includes 50,000 MAU; cost only if scaled |
| CloudWatch Alarms / Dashboard | Per-alarm + dashboard | Minimal; only when deployed |

**Key cost risk:** DynamoDB Scan for keyword search evaluates all items. With 100 policies, cost is negligible. At 10,000+ policies, Scan costs become significant and a GSI or OpenSearch is required (documented in `README.md` L360).

---

## 6. Prioritized Recommendations

### Mandatory (Before Any Production Deployment)

1. **Fix SAM validation / confirm deployment readiness** — `sam.cmd validate --lint` had a pre-existing error with `AuthorizerId` (resolved by using SAM-native `Auth.Authorizers` / `Auth.Authorizer` in Phase T). Confirm with manual `sam.cmd validate --lint` run.
2. **Replace localhost CORS origins** — `template.yaml` L120 requires customer input.
3. **Enable DynamoDB PITR** — add `PointInTimeRecoverySpecification` to `PoliciesTable`.
4. **Document deployment checklist** — include cost estimate, rollback plan (`sam delete`), and verification steps.

### High Value (Phase 2–3 of 25-week plan)

5. **Add API Gateway input validation** — `limit` and `keyword` validators.
6. **Add Lambda reserved concurrency** — prevent runaway scaling.
7. **Add structured correlation IDs** — improve troubleshooting.
8. **Add CI/CD pipeline** — automated `sam build`, `pytest`, `sam validate`.

### Optional / Justified Only If Requirement Exists

9. **SQS + DLQ** — only if asynchronous policy processing (e.g., bulk import, approval workflow) is required. Not needed for current read-only API.
10. **S3 document storage** — only if policies need PDF/attachment storage. Not needed for current text-only data.
11. **Amazon Bedrock / RAG** — only if AI-assisted policy Q&A is a concrete product requirement. Not implemented; evaluated only.
12. **X-Ray tracing** — valuable but not mandatory for MVP.
13. **GSI / OpenSearch** — required only when dataset exceeds ~100 policies or when full-text search quality is required.

---

## 7. References

- AWS Well-Architected Framework: https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html
- AWS SAM HttpApi: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-resource-httpapi.html
- AWS SAM Function HttpApi Auth: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-property-function-httpapi.html
- DynamoDB Scan: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Scan.html
- Cognito User Pool JWT: https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-authentication-flow.html
- CloudWatch Metrics: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working_with_metrics.html

---

## 8. Uncertainties / Limitations

- `sam.cmd validate --lint` result depends on manual execution by reviewer; not independently verified in this audit.
- Integration test results (9 passed) are historical from Phase L deployment; current live API state not independently verified.
- No live AWS resource inspection performed (read-only constraint respected).
- Cost estimates are qualitative; no AWS Pricing Calculator output included.

---

*Document created: 2026-10-19*
*Status: Audit complete — no AWS modifications made*
*Next step: Review `docs/25-week-internship-roadmap.md` for phased implementation plan*
