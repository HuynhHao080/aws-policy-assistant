# Evidence index — current local implementation

D4 local-only follow-up: [final review](d4-final-readiness-review.md), [manifest/security/readiness checks](evidence/d4-local-readiness.json), [internship report summary](d4-internship-project-summary.md). D3-A BLOCKED; public push/Pages/cleanup NO-GO. No AWS/GitHub calls or E2E rerun.

Latest security operational review (2026-10-22): [D3-A1](d3a1-operational-dependency-assessment.md), [metadata](evidence/d3a1-dependency-metadata.json), [activity](evidence/d3a1-activity-review.json), [decision](evidence/d3a1-dependency-summary.json). Historical exact-identity auth requests found; current operational requirement UNKNOWN. D3-A remains BLOCKED_PENDING_OWNER_OPERATIONAL_CONFIRMATION. No AWS writes or authentication calls. Older sections below remain dated snapshots.

Updated 2026-10-21. Link each report assertion to source and the verification record; distinguish source configuration, offline execution and live execution.

| Evidence | Supports | Status |
|---|---|---|
| `policy_assistant/app.py` | Policy API, cursor, owner-bound PDF version workflow, worker hashing/retry | Current local source |
| `template.yaml` | Cognito, two tables, private/versioned S3, SQS/DLQ, scoped IAM and monitoring | Defined locally; not deployed this iteration |
| `docs/architecture-self-draw.md` | Components, boundaries, decisions, Well-Architected and official-icon drawing checklist | Worksheet ready; student own diagram missing |
| `tests/unit/test_handler.py`, `test_documents.py` | 120 backend tests including ownership/version/retry/pagination | Offline pass on Python 3.12.10 |
| `tests/frontend/flow.test.cjs` | 17 frontend tests | Offline pass |
| `tests/frontend/local.e2e.cjs` | Real browser, real Lambda handlers, simulated services; owner-isolated library and login | 1 full-stack scenario passed |
| `scripts/verify.py` | Offline acceptance orchestrator | Machine-readable result in `docs/evidence/offline-acceptance.json` |
| `tests/frontend/browser.e2e.cjs` | Real browser workflow with synthetic API/S3 | 1 scenario passed on Edge headless |
| `docs/evidence/frontend-desktop.png` | Completed mock workflow and sanitized hash | Local browser evidence |
| `docs/evidence/frontend-mobile.png` | Responsive/error UI with synthetic fixtures | Local browser evidence |
| `docs/final-verification.md` | Commands, results, environment and limitations | Current verification record |
| `docs/demo-script.md` | FCAJ presentation order and evidence boundaries | Prepared; not proof of presentation |
| `.github/workflows/ci.yml` | Reproducible test/build configuration | Configured; remote run pending push |
| `tests/integration/test_api_gateway.py` | Opt-in live read tests with JWT | 9 skipped; not live evidence |
| `scripts/check_live.py` | Explicit live policy/PDF verification without printing secrets | Prepared; not executed |

The original 2026-10-19 handover/deployment assertions are not a substitute for live verification of this code. Current scripts no longer contain the known password literals, but previously exposed credentials remain in Git history until handled by the account/repository owner. Never add credential values, JWTs, presigned URLs, full auth responses or unredacted Network captures to evidence.

Current full-stack screenshots: `full-stack-desktop.png`, `full-stack-mobile.png`. Deployment/operations and a bounded two-phase GSI upgrade are documented in `operations.md`. CloudFront/recovery/SNS resources are source definitions, not deployed evidence.

Additional current evidence: `docs/cost/` (dated official rate snapshot and gross model), `docs/evidence/iac-review.patch` (local diff, not an AWS change set), `docs/evidence/worklog-links.json` (full generated link audit), `docs/evidence/daily-worklog-audit.json` (row/reference coverage, not proof of activity). Three distinct EN/VI blog drafts and the actual product Workshop are prepared in Worklog; publication/attendance/student drawing remain pending.

## Actual AWS predeployment inspection and owner gate (2026-10-21)

`aws-predeployment-readonly.json` records observed existing resources without data contents; `aws-test-change-set.json` is the actual current unexecuted candidate; `aws-test-iam-review.json` reviews processed roles and retention; `aws-review-source-fingerprint.json` / `aws-review-artifact-fingerprint.json` pin the candidate. `aws-test-acceptance-pending.json` marks all real application E2E NOT_RUN. `aws-preparation-local-checks.json` records 123 backend tests, lint and SAM build/validate for the test-isolation/explicit-worker-role changes. Read `aws-test-deployment-approval.md` before executing; no current-release AWS PASS is claimed.


## Hardened candidate revision — 2026-10-21

Current candidate `fcaj-review-20261021-072124-24ba855e` has 45 Add actions; no execution authorized. Local full verifier passed: 128 backend, 17 frontend and two browser suites, lint/typecheck, SAM validate/build. Nine live tests are skipped, not AWS proof. Cached actual processed-template IAM audit passes; fresh AWS reads and ZIP integrity are tracked separately and remain blocked until a successful timestamped check. See [approval packet](aws-test-deployment-approval.md) and `evidence/aws-review-artifact-fingerprint.json`. Earlier counts/status below describe older revisions.

Current resumption evidence: [final readiness](evidence/aws-final-readiness.json), [local template consistency](evidence/aws-local-template-consistency.json), [artifact verification BLOCKED](evidence/aws-review-artifact-fingerprint.json), [processed snapshot IAM review](evidence/aws-test-iam-review.json), [Budget draft](budget-test-proposal.md). Latest fresh attempt: 2026-10-21 07:41 UTC, STS ConnectTimeoutError; no fresh AWS PASS.


Latest 4G recovery supersedes earlier connectivity BLOCKED observations: signed STS/CFN/GetObject checks succeeded 2026-10-21 08:07:43–08:08:59 UTC, fresh audit also passed. All three Lambda artifacts content-verified; exact 45 Add candidate AVAILABLE. [Current readiness](evidence/aws-final-readiness.json): technical verification GO; execution remains unapproved, runtime E2E NOT_RUN.
# Budget 20 USD preparation packet — 2026-10-21

Status PREPARED_NOT_CREATED; recipient PENDING_USER_CONFIRMATION; Budget creation and application deployment NOT_EXECUTED. [Approval](budget-20usd-approval.md), [Budget JSON](budget/account-monthly-20usd-proposal.json), [Notification JSON](budget/account-monthly-20usd-notifications.json), [pending-field manifest](budget/account-monthly-20usd-preparation.json), [Console guide](budget/account-monthly-20usd-console.md). New evidence: [read-only account/name/config baseline](evidence/budget-20usd-preparation-readonly.json), [offline shape and semantic validation](evidence/budget-20usd-local-validation.json). Existing baseline/forecast figures remain historical AWS evidence and planning assumptions respectively; no duplicate cost query was performed for this packet.
# Owner-created Budget — latest read-only verification

Budget configuration CONFIGURED_VERIFIED; overall PARTIAL because recipient activation is unverified. CloudTrail CreateBudget 2026-10-21 09:11:39 UTC confirms all three PERCENTAGE alerts; current Budget reads confirm USD20/COST/MONTHLY/UnblendedCost/exclusions, common recipient configuration, no Actions and unchanged six old configuration fingerprints. No email address is exported. Delivery remains DELIVERY_NOT_VERIFIED. [Current report](budget-20usd-verification.md), [Budget evidence](evidence/budget-20usd-created-readonly-verification.json), [CloudTrail](evidence/budget-20usd-cloudtrail-readonly.json), [candidate AVAILABLE/45 Add](evidence/aws-candidate-after-budget-readonly.json). Agent writes 0; deployment NOT_EXECUTED, E2E NOT_RUN. Earlier preparation/blocked states below are historical.

## Budget Console confirmation và Approval B

- [Console confirmation do người dùng cung cấp](evidence/budget-20usd-user-console-confirmation.json): cấu hình VERIFIED, legacy Active, verification 0/1, delivery chưa xác minh.
- [Approval B chưa được cấp](aws-test-deployment-approval-b.md) và [manifest](evidence/approval-b-preparation.json): 45 Add, không triển khai/E2E.

- [Approval B final preflight read-only 09:32–09:33 UTC](evidence/approval-b-final-preflight-readonly.json): identity/candidate/artifact/Budget/cost fresh; authorization NOT_GRANTED.

- [B1 CREATE_COMPLETE result](aws-test-deployment-b1-result.md): [execution/events/45-resource inventory](evidence/approval-b1-execution.json), [post-create service/deployed-template checks](evidence/approval-b1-service-readiness.json). B2/B3/B4 pending; AWS E2E NOT_RUN.

- [B2 frontend static result](aws-test-frontend-b2-result.md) và [summary JSON](evidence/approval-b2-result.json): bốn assets SHA-256 khớp S3/CloudFront, HTTP301/HTTPS200; B3/B4 pending.

- [B3 Cognito result](aws-test-cognito-b3-result.md): [preflight](evidence/approval-b3-preflight.json), [two synthetic users read-back](evidence/approval-b3-users.json). DPAPI credentials private; B4 login/E2E NOT_RUN.

- [B4 real AWS API/SDK E2E](aws-test-e2e-b4-result.md): [19 PASS/1 browser NOT_RUN](evidence/approval-b4-e2e.json), [alarm follow-up](evidence/approval-b4-alarm-followup.json); cleanup not authorized.

- [B5 browser approval preparation](aws-browser-b5-approval.md): [read-only AWS state](evidence/approval-b5-readonly-review.json), [bounded proposal/local fixtures](evidence/approval-b5-proposal.json). No login/write; execution pending independent approval; cleanup C separate.

- [B5 real-browser FAIL/STOPPED](aws-browser-b5-result.md): [result](evidence/approval-b5-result.json), [post-read-only diagnosis](evidence/approval-b5-post-readonly.json); [remediation proposal not implemented](browser-b5-remediation-proposal.md). No rerun/deploy/cleanup.

- [B5-R local remediation](browser-b5r-remediation-review.md): [summary](evidence/b5r-local-remediation.json), [red](evidence/b5r-prepatch-csp-browser.json), [green](evidence/b5r-local-csp-browser.json), [build comparison](evidence/b5r-build-vs-deployed.json), [runtime patch](evidence/b5r-runtime.patch). No AWS writes/deploy/rerun.

- [B5-R2 artifact/change-set NO-GO](browser-b5r2-deployment-approval.md): [AWS evidence](evidence/b5r2-preparation.json), CREATED_NOT_EXECUTED;6 Modify/1Conditional.

- [B5-R3 impact audit](browser-b5r3-impact-audit.md): [read-only evidence](evidence/b5r3-impact-audit.json), NO-GO.

- [B5-R4 minimal update strategy](browser-b5r4-minimal-update-review.md): [local/read-only evidence](evidence/b5r4-strategy.json), API-only preparation GO, execution NO-GO.

- [B5-R5 API-only change set review](browser-b5r5-change-set-review.md): [evidence](evidence/b5r5-change-set.json), CREATED_NOT_EXECUTED; NO-GO scope.

- [B5-R6 deployment result](browser-b5r6-deployment-result.md): [evidence](evidence/b5r6-execution.json), UPDATE_COMPLETE_VERIFIED; browser rerun NOT_RUN.

- [B5-R7 real Edge Browser E2E](aws-browser-b5r7-result.md): [summary](evidence/approval-b5r7-result.json),10PASS; cleanup Approval C pending.

- [C0 cleanup inventory/final test acceptance](cleanup-c0-inventory-and-acceptance.md): [inventory](evidence/approval-c0-inventory.json), [summary](evidence/approval-c0-summary.json). Read-only; no deletion. SNS0subscriptions; GO bounded demo / NO-GO production.

- [D1 local handover/Git review](d1-handover-review.md): [file inventory](evidence/d1-git-files.json), [readiness](evidence/d1-git-readiness.json), [Hugo links](evidence/d1-workshop-links.json). No AWS calls/commit/push; public push blocked pending historical-credential gate.

- [D2 public credential exposure assessment](d2-secret-exposure-review.md): [filtered evidence](evidence/d2-credential-exposure.json), [static triage](evidence/d2-triage.json). [D3 proposal](d3-credential-containment-approval.md) NOT_APPROVED. No authentication/credential changes/Git writes.

- [D3-A pending containment preflight](d3a-containment-result.md): [evidence](evidence/d3a-preflight.json), technicalPASS/ownercondition5PENDING; no AWS writes.
