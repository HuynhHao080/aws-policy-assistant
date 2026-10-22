# FCAJ gap analysis — 2026-10-21

## Verified scope and working trees

Application: HuynhHao080/aws-policy-assistant, local checkout `policy-assistant-github`, baseline HEAD `80c4eef` plus existing uncommitted changes. Report: HuynhHao080/aws-internship-worklog, baseline HEAD `846d2ff` plus existing changes. Stack/region are `policy-assistant` / `ap-southeast-1`, explicitly read from samconfig.toml. No AGENTS.md was found in these repository trees or checked parent directories. The originally selected `policy-assistant` checkout has pre-existing staged changes and a modified workshop submodule; those must remain intact.

Existing services and features are verified from code/IaC, not live AWS: policy lookup/search, Cognito, owned document library, versioned S3, SQS/worker/recovery, CloudWatch/SNS and CloudFront hosting definitions. No AI/RAG is implemented. Do not rename the project or add unrelated services.

| Requirement | Current finding before this pass | Evidence | Required action | Priority |
|---|---|---|---|---|
| Worker failure isolation | Exceptions fail whole invocation; no ReportBatchItemFailures; stale/failed paths need regression checks | app.py worker_handler, SQS event in template.yaml | Per-record responses, mapping flag and mixed-batch/DLQ regressions | P0 |
| Upload bounds at storage | Presigned PUT allows arbitrary bytes to reach S3 before submit checks | _document_upload_session, browser upload | Bounded signed POST policy; align browser/demo/live-check helper and add regressions | P0 |
| Validation | Non-object/wrongly typed bodies and oversized IDs can fall through to 500; upload lacks base64 parity | lambda_handler and document routes | Shared JSON/schema validation; assert 400/no write | P0 |
| No secret logs | Raw request paths/query values and exception messages are logged | lambda_handler, _search_policies, _get_policy_by_id | Log route/correlation/error class only; sentinel leak regression | P0 |
| Ownership | Bound to authorizer sub; separate queries and condition writes exist | _owned_document, ByOwner, existing tests | Re-run isolation, cursor tampering, unknown/mutation-method cases | P0 |
| IAM/S3/CORS | Scoped ARNs, BPA, local/CloudFront origins; HTTPS-only bucket policy not explicit | template.yaml | Add TLS deny to existing buckets; explicit queue encryption; inspect CORS for new POST | P0 |
| Demo evidence | Existing local full stack uses real handlers + moto; no new live proof | tests/frontend, demo_server, previous verification | Re-run actual changed code, preserve local/AWS/unverified labels | P1 |
| Build/quality | SAM/unit/browser checks exist; no current lint/type result for this pass | verify.py, CI | Add/run appropriate static checks, compile/syntax, regression and browser checks | P1 |
| Architecture ownership | Mermaid/old PNG are assistant-generated references; cannot count as student design | architecture.mmd/png | Supply inventory, boundaries, decisions, official-icon self-drawing checklist; no new AI diagram | P1 |
| Well-Architected | Operational notes exist, no rubric-aligned assessment | docs/operations.md | Security/reliability/operations/cost tradeoffs and concrete evidence | P1 |
| Mandatory COST | Previous report deliberately has no numbers | README/report | Official dated regional rate snapshot, explicit load, gross/itemized totals and calculator inputs; no invented estimate URL | P1 |
| Workshop matches project | Existing Workshop covers separate S3/VPC Endpoint learning lab | Worklog content/5-Workshop | Preserve that material as separate learning; add complete Policy Assistant workshop EN/VI | P2 |
| Daily Week 1–12 | Historical pages exist; completion/references require evidence | content/1-Worklog | Audit day/reference coverage; preserve original facts and mark missing confirmation | P2 |
| Three technical blogs | Existing three articles duplicate a different subject | content/3-BlogsPosted | Prepare three distinct EN/VI drafts grounded in actual fixes; do not claim published | P2 |
| Student/events/self-assessment | Personal entries/claims lack verified evidence | home/events/evaluation/feedback | Mark needing student confirmation, no fabricated achievements | P2 / student |
| Attendance | No independently verified 10 office sessions or 3 face check-ins in this pass | student evidence pending | Student supplies original dated evidence; eligibility remains unverified | Student |
| Deployment authorization | No authorization to execute AWS writes/deletes/publish | user instructions | Prepare local IaC diff, cost, rollback and staged-index plan; do not deploy | Gate |

## Scoring gates to keep open

Missing blog OR daily log can zero Worklog. Missing architecture OR Proposal/Workshop presentation can zero Workshop. A local simulation does not establish a live AWS product. Missing cost can zero presentation. An assistant-generated diagram is not student-designed architecture. Attendance/attitude and bonus cannot be manufactured or guaranteed by code changes. Detailed completion evidence and remaining student work must be reported separately.

## End-of-pass status (local evidence only)

| Requirement group | Result | Remaining gate |
|---|---|---|
| P0 validation/logging/upload/ownership/worker | Fixed locally; 120 backend and 17 frontend tests passed; both browser suites passed | Actual JWT/S3 policy/IAM/CORS and SQS behavior on AWS |
| IaC security/monitoring | SAM lint/build passed; TLS-only buckets, SQS SSE, explicit Lite tier, per-record mapping and queue/worker/recovery dashboard | Reviewed AWS change set, account/tier compatibility and deployment acceptance |
| COST | Official dated regional rate snapshot, Calculator quantities, gross itemized 6.6306 USD/month and stress 34.7081 USD | Actual usage, eligible allowance, budget recipient; no Calculator estimate created |
| Architecture | Exact inventory/arrows/trust boundaries/decisions/Well-Architected and official-icon worksheet ready | Student draws, checks and explains own editable diagram |
| Workshop/report | Actual EN/VI product workshop, proposal timeline/scope/risk/cost, demo/runbook and three distinct technical drafts | Student publication/review/presentation; no publication done here |
| Daily/personal evidence | Week 1–12 row/reference audit, no historical backfill; source/personal/event claims flagged | Confirm dates and genuine daily artifacts, 10 office and 3 face-visible event records |
| Website | Hugo build passed; full internal href/src/anchor scan zero failures | Three legacy theme deprecation warnings; no external-site/publication certification |
| Operations | Concrete local IaC diff, maintenance/rollback/retained-data cleanup plan ready | Owner approval for AWS writes; no cloud modifications/deletion/push |
