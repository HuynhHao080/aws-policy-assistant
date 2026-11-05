---
title: "Primary release — features, verification and handover"
date: 2026-11-04
weight: 0
---

# Policy Assistant — primary release, 4 November 2026

Application: [Policy Assistant](https://djreo5eptvwk5.cloudfront.net/). Application repository: `HuynhHao080/aws-policy-assistant`, canonical folder `C:\Users\accli\Documents\Project\policy-assistant`. Separate worklog: `HuynhHao080/aws-internship-worklog`. Unpushed local source is not automatically available in the public repository. This guide is AI-assisted review material, not a record of the student's personal execution or FCAJ approval.

On5November the student requested local synchronization into `C:\Users\accli\Documents\Project\policy-assistant-github`. This is a second checkout of the same application GitHub repository, not the worklog or a new AWS target. Local synchronization does not commit/push or publish a website; historical evidence and environment-specific configuration are retained/backed up as recorded in the synchronization report.

## Problem and product boundaries

Help a small shop answer policy questions using published sources and customer-private documents, with explicit consent before handing a question to staff. Current shop policies are fictional DEMO content. There is no order/payment integration, automatic refund, diagnosis of product damage or binding business commitment. No real operator has approved business policies.

## Implemented functionality and personal verification

| Flow | Behavior and boundary to explain |
|---|---|
| Identity | Cognito signup, verification, PKCE login and recovery; administrator authorization enforced on the backend |
| Private PDFs | 10 MiB/file, 100 text pages or 10 scanned pages; pinned S3 version, explicit failure state, owned library/rename/download/delete |
| Background work | Metadata stream → dispatcher → SQS → worker; isolated parser, Textract for scans, recovery/retries/DLQs |
| Answers | Cohere multilingual/int8 S3 vectors; shared policies, selected PDFs or both; Nova 2 Lite cited excerpts/pages and insufficient-evidence behavior |
| History | Owner-only, 30-day expiry, export/delete; expired records hidden before asynchronous TTL removal |
| Policies | Separate drafts/publication, archive/restore/discard, revisions and audit; administrators cannot read private customer PDFs by virtue of their role |
| Support | Explicit customer consent, unverified category/order reference, in-app replies; staff filters/status/priority; no automatic email or PDF/history attachments |
| Shop | Draft/publish/withdraw/discard contacts; live mode requires details and confirmation; configuration is not automatically an AI source |
| Quality | Helpful/not-helpful, controlled reasons, change/withdrawal; revisions/idempotency; aggregate-only administrator dashboard for current/previous UTC answer cohorts and JSON export |
| Account deletion | Block access first, asynchronously purge private data and all object versions; identifier-free cohort totals may outlive private history |

Source references: `policy_assistant/app.py`, `assistant.py`, `pipeline.py`, `quality.py`, `tickets.py`, `shop.py`, `policy_admin.py`, `pdf_parser.py`, `template.yaml`, `frontend/src/`. Read `docs/api-contract.md` and `docs/production-runbook.md`. Verify actual route names before writing examples; do not invent endpoint names.

## Data flows for the student's own architecture

A private frontend S3 origin is served through CloudFront HTTPS. Cognito supplies identity; API Gateway validates JWTs; Lambda authorizes each resource. Owned PDFs enter private versioned S3, and persisted DynamoDB metadata drives asynchronous dispatch. The parser has no general service permissions. Bounded retrieval precedes generation; answer/history and quality persistence use transactions with deletion guards.

Stack, storage, embedding and OCR are in Singapore. Generation uses `jp.amazon.nova-2-lite-v1:0`, low reasoning; retrieved excerpts may be processed in Tokyo/Osaka. Explain cross-region processing and read the privacy notice before using sensitive documents. Citation presence is not factual correctness; user feedback is opinion. Server processing time is not end-to-end browser latency. Aggregate retention is 65 days after the last update; private history is 30 days and support is 90 days.

**The final diagram is still missing.** Personally design/draw it with [official AWS icons](https://aws.amazon.com/architecture/icons/). Mark trust boundaries, private/shared data, synchronous/asynchronous calls, retries/DLQs and cross-region excerpts. Explain payload, authorization and failure handling for each arrow. An AI worksheet is not a student-designed final architecture.

## Recorded verification — not rerun by building this worklog

[Download sanitized evidence](/aws-internship-worklog/evidence/policy-assistant-2026-11-04.json). Only allowlisted fields and source-report hashes are exported; no JWTs, customer IDs or question/answer text. The JSON includes original check times.

| Type | 4 November release report | Scope |
|---|---|---|
| Python 3.12 | 251 passed, 11 skipped | Local/mocked suite; opt-in live tests disabled |
| Frontend | 54 passed and build | Node/synthetic DOM, not browser visual acceptance |
| Real quality APIs | 15 checks passed | Two disposable identities and year-2000 fixture excluded from normal dashboard; operator persistence helper plus actual feedback APIs; no model/PDF/email calls |
| Fixture cleanup | Passed in report | Disposable identities, history partitions and cohort removed; no current-month seeding |
| Artifacts | 6 Lambdas, 31 frontend files | Release hash/metadata comparisons; not screenshots, benchmarks or fresh login acceptance |

Code SHA-256: `974197f606822d42a51a922694a30de95be06ac57a5a4ff30c1837089ab94273`. No new load, backup-restore, alert delivery, model accuracy or visual-browser result is asserted. Historical October B4/B5/B5-R7 and CI evidence belongs to the earlier environment and is retained unchanged.

## Local reproduction and worklog synchronization

Use Python 3.12, Node 26 and AWS SAM CLI. Follow the application README: install `policy_assistant/requirements.txt` and `tests/requirements.txt`; run `npm ci --prefix frontend --ignore-scripts`, `npm run build --prefix frontend`, `npm test --prefix frontend`, `python -m pytest tests -q`, `sam validate --lint --region ap-southeast-1`, and `sam build`. Local unit/build results do not establish deployed AWS configuration. Do not enable live-test variables or invoke smoke/model scripts for local checks. Example frontend configuration has no real backend and disables login.

```powershell
# Application repo: read-only drift check, no AWS/Git/site writes
python scripts/sync_fcaj_worklog.py --worklog C:/Users/accli/Documents/Project/aws-internship-worklog
# Apply managed technical notes, backing up every changed destination
python scripts/sync_fcaj_worklog.py --worklog C:/Users/accli/Documents/Project/aws-internship-worklog --apply
# Worklog repo, exact extended Hugo version used in CI
hugo --minify
```

The tool only updates managed blocks in an explicit page allowlist, the two release guides and sanitized JSON. It does not edit daily records/photos/profile or publish blogs, push Git or deploy. Backups/manifests are stored in the application's `.deployment/worklog-sync-*`. Use Hugo extended **0.167.0**, matching CI, and verify official download checksums before execution.

## Seven-minute demo — not yet personally recorded/executed

| Minute | Personal action and explanation |
|---|---|
| 0–1 | Explain the shop problem, DEMO label and your own architecture |
| 1–2 | Account A uploads a synthetic PDF and follows processing; claim OCR only if a scanned PDF was actually used |
| 2–3 | Ask one supported and one unspecified-policy question; inspect source/page and explain retrieval scope |
| 3–4 | Account B cannot read A's PDFs/history; keep tokens and signed URLs out of recordings |
| 4–5 | Submit consented support and staff reply; show private content is not silently attached |
| 5–6 | Rate/change/withdraw feedback; view aggregates and explain why they are not accuracy |
| 6–7 | Draft/publication, audit, costs and limits; use only measurements with matching provenance/date |

This is a plan, not passing evidence. Seeded API latency is not real model output or a performance measurement. Do not run poison/load/fault tests or delete infrastructure during the demo. Cloud cleanup requires a separate defined scope and inventory of data, versions and retained resources. No cloud cleanup occurs in this synchronization.

## Current COST preparation — Calculator artifact still missing

The owner targets USD 30–50/month; deployment reports record an account budget of USD 50 with notifications at USD 25/40/50. These are alerts, not a hard cap or freshly read invoice. Preserve the 21 October test-environment estimate as history; it does not fully include current Nova2/OCR/embedding/vector/counter costs.

A **proposed, unmeasured Calculator scenario**, not yet approved by the owner: 50 MAU; 100 PDFs/month × 10 pages, 20% needing OCR → 200 OCR pages; 2 MiB/PDF; 2,000 document embedding chunks plus 1,000 query embeddings/month; 1,000 generations × 8,000 input tokens and 2,500 output/reasoning tokens as planning headroom. These token quantities are assumptions, not measurements or an enforced input limit; current Nova2 maxTokens is 2,500. Also model the 2,000-attempt monthly quota scenario. Stored versions accumulate; one month's uploads are not total retained storage.

Enter each service in [AWS Pricing Calculator](https://calculator.aws/) with the actual regions: Japan generation; Singapore embedding/Textract/API/Lambda/DynamoDB/S3; CloudFront according to audience geography. Include parser/recovery/dispatcher/signup Lambdas, failed/duplicate work, transactions/indexes/PITR, all object versions/vectors, transfer, Cognito, CloudWatch logs/alarms/dashboard and SNS. Do not assume free-tier eligibility or subtract credits. Use [official Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) and each service's dated pricing page. No new verified unit rates or total USD are claimed for this scenario. If Calculator lacks a model/dimension, attach an explicit calculation from official pricing instead of omitting it. Save the real share URL/export, date and assumptions before marking COST complete.

## Personal requirements still pending

### Additional source handover verification — 5 November 2026

An integrity-checked source ZIP was extracted into a new folder. A separate Python3.12 virtual environment installed the extracted requirements; frontend dependencies used `npm ci` and the extracted lockfile. **273Python tests passed,11live tests skipped;54frontend tests passed; SAM build for all six functions and validate/lint passed.** The initial SAM build failed because PATH selected Python3.13; selecting the actual Python3.12 directory fixed it without relaxing the runtime requirement.

This new local result includes22additional synchronization/export safeguards; it does not replace the historical cloud-release251/54/15counts above. System toolchains and package download caches were shared; this was not a new machine/container/AWS account. No model or live AWS acceptance was run. `scripts/source_bundle.py` excludes real connection settings, credentials, builds/dependencies and Git history; pattern checks are not a full secret audit. Application references: `docs/reproducibility/README.md`, `VERIFICATION-2026-11-05.md`, and `requirements-verified-2026-11-05.txt`. CI now includes a local archive integrity step, but no new GitHub CI run or public publication is claimed.

Articles 3.4–3.6 are drafts: review technical details, add actual personal contributions, publish and record real URLs/dates. Office/event evidence, internship dates, a self-designed diagram, Calculator and demo recording require genuine evidence. Do not generate attendance dates, photographs or self-assessment scores. Read the [workshop rules](https://hcm-rules.awsfcaj.com/3-project/) and [scoring criteria](https://hcm-rules.awsfcaj.com/5-scoring/) before submitting; test counts do not establish a grade or eligibility.
