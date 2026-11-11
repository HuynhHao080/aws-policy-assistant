---
title: "Current proposal — a policy assistant for an accessories shop"
weight: 0
---


**Primary application model:** Global Claude Haiku 5.5. The application ranks extracted PDF and policy text by keywords. Dated verification reports record their respective releases. [Model cutover evidence](https://github.com/HuynhHao080/aws-policy-assistant/blob/main/docs/haiku55-migration.md).
# Policy Assistant — current solution proposal

Document review: **6 November 2026**. This AI-assisted proposal describes published code and the latest recorded deployment evidence. The student must review, practise and explain it. It does not establish FCAJ eligibility or authorize DEMO policies for real transactions. October proposals on the parent page remain historical records.

## 1. Problem, users and value

Small accessories shops repeatedly answer warranty, returns, delivery and payment questions. Scattered text encourages unsupported answers or incorrect conditions. Customers need an explicit handoff to a person when information is insufficient, while controlling what they share.

The solution serves **one shop**, with self-registering customers and trusted administrators. Customers consult policies, ask cited questions, use private PDFs and submit consented support requests. Administrators approve content, manage effective dates, coordinate cases and inspect aggregate feedback. This supports decisions; staff verify actual orders and damage causes outside the application.

| Goal | Verification | Boundary |
|---|---|---|
| Answers customers can inspect | Open source excerpts and PDF page references | Citations do not prove every statement correct |
| Private customer data | Two-user isolation, DTO and backend authorization checks | Application administrators are distinct from AWS operators |
| Avoid expired policies | UTC+07 dates, effective-state filtering and final source checks | Point-in-time checking, not a transaction lock around inference |
| Contextual staff handover | Self-claim, notes, reason-required takeover and revision conflicts | All trusted administrators can read notes; no restricted staff role |
| Costs suitable for a small trial | Quotas, bounded retrieval, budget alerts and usage monitoring | No new load benchmark, completed Calculator estimate or hard spending cap |

## 2. Implemented scope and exclusions

Implemented: signup/email verification/PKCE/password recovery; private, version-pinned PDFs and text/OCR pipeline; policies/PDF/both source selection; cited answers; 30-day history; policy draft/publish/archive/restore/revision/audit; shop configuration; consented support with assignments and notes; aggregate answer feedback; account access blocking followed by background purge.

Not implemented: multiple tenants, order synchronization, payment/refund execution, social channels, automatic support email, SLA timers or a support-only role. The application does not decide real warranty eligibility. Policies remain **DEMO** until a real operator approves business content. [Complete feature inventory and launch conditions](https://github.com/HuynhHao080/aws-policy-assistant/blob/main/docs/FEATURE-STATUS.md).

## 3. Architecture inputs for the student's own diagram

The following is a design description, **not a replacement for a student-designed AWS diagram**. Use correct AWS icons, identity boundaries, private customer data boundaries and model regions; compare with `template.yaml` before submission.

| Flow | Components and responsibilities |
|---|---|
| Web application | CloudFront + S3; Cognito authentication; HTTP API → Python 3.12 Lambda validates JWT/groups/ownership |
| Upload and processing | Private versioned S3 → DynamoDB metadata/Stream → dispatcher → SQS → worker; IAM-isolated PDF parser, Textract for scans; recovery and DLQ |
| Questions | Rank extracted text by lexical relevance → Global Claude Haiku 5.5 → validate source IDs and policy validity → history |
| Administration/support | DynamoDB policy/shop/ticket records; revision + owner-deletion guard + audit transaction; customer DTO excludes internal notes |
| Operations | CloudWatch logs/metrics/alarms, SNS and AWS Budgets; PITR and Retain protect data during infrastructure operations |

Application services, storage and Textract run in Singapore. The Global Claude Haiku 5.5 profile can process questions and excerpts in other AWS Regions.

## 4. Technical decisions and risks

| Risk / tradeoff | Mitigation and remaining measurement |
|---|---|
| Model inference errors or changing sources | Accept retrieved source IDs only, validate structure and recheck public facts before saving; no new accuracy result |
| Cross-account access | JWT-derived ownership, backend checks, private S3 and customer DTO allowlists; AWS operators retain separate infrastructure authority |
| Duplicate/failed background jobs | Version pinning, durable state, bounded retries, partial batch failures, recovery and DLQ; incident exercises need reviewed scope |
| Concurrent staff/customer writes | Revision + transaction; conflict requires reload and review before retry |
| Scan and S3-vector scaling | Bounded retrieval/pagination; measure recall, latency and backlog before raising quotas or replacing storage |
| Costs beyond generation | Include all S3 versions, PITR, logs/alarms, OCR, transfer and failed requests; budgets only alert |
| Deletion and recovery | Block account access before purge; documented retention; logs/backups have separate lifecycles; no new restore acceptance |

## 5. COST — estimation inputs, Calculator pending

The owner's target is **USD 30–50/month**. A USD 50 budget with USD 25/40/50 thresholds sends alerts rather than limiting invoices. The October test estimate does not price the current release. Inputs below are assumptions for Calculator, not measured demand or an already shared estimate.

| Assumed input | Dimensions to estimate |
|---|---|
| 50 MAU; 100 PDFs/month × 10 pages, 2 MiB/PDF | Cognito, API, Lambda and S3; include sources/versions/extraction and retention, not just first-month uploads |
| 20% of pages need OCR = 200 pages/month | Singapore Textract plus worker/poll/retry requests |
| 1,000 answers × 8,000 input and up to 900 output tokens | Global Claude Haiku 5.5 from Singapore. Estimate a higher scenario at 2,000 attempts/month. |
| Support, audit, counters and operations | DynamoDB transactions/indexes/PITR, SQS, logs/alarms/dashboard, SNS, CloudFront/transfer and failed requests |

Total: **PENDING**. No current unit prices or completed estimate have been verified; do not enter zero or assume free tier/credits. Use [AWS Pricing Calculator](https://calculator.aws/) and [official Bedrock pricing](https://aws.amazon.com/bedrock/pricing/), retaining date, regions, assumptions and a share URL/export. Supplement unsupported models/dimensions with explicit calculations from official prices. [Detailed cost inputs]({{< relref "/5-Workshop/5.7-PolicyAssistant/CurrentRelease" >}}).

## 6. Remaining delivery plan — not completed activity

| Proposed effort | Output and responsible reviewer |
|---|---|
| 1–2 days | Shop owner reviews operator identity, contacts, returns address, real policies and consent/retention |
| 1–2 days | Student draws/explains architecture, creates Calculator estimate and agrees a load scenario with the owner |
| 1–2 days | Real-device browser, email/alert and staff workflow checks; plan load/restore exercises within reviewed scope |
| 1 day | Record a synthetic-data demo with secrets hidden; compare commits/artifacts and submit actual evidence |

These are remaining-effort estimates, not internship dates, appointments or a guaranteed completion time.

## 7. Acceptance and evidence

The support runtime recorded **322 Python passes, 11 live skips; 67 frontend passes; 20 HTTP checks passed**. Three QA identities and the test ticket were cleaned; 40 frontend files and six Lambda hashes matched. This is the recorded snapshot dated 5 November UTC (6 November in Vietnam), not a new run whenever this page is opened. That HTTP run did not invoke models, PDF/OCR or email. [Verification report](https://github.com/HuynhHao080/aws-policy-assistant/blob/main/docs/support-team-verification.md), [source CI](https://github.com/HuynhHao080/aws-policy-assistant/actions/runs/42072920395), [support chapter]({{< relref "/5-Workshop/5.7-PolicyAssistant/SupportTeam" >}}), [effective-policy chapter]({{< relref "/5-Workshop/5.7-PolicyAssistant/PolicyValidity" >}}).

Real customers require browser, shop-approved accuracy dataset, email, load, restore and staffing verification. Historical failures/passes remain unchanged. Actually published blogs, event/office evidence, a student-drawn diagram, Calculator and video remain personal deliverables. [Workshop rules](https://hcm-rules.awsfcaj.com/3-project/) require bilingual content and proposal scope/architecture/planning/COST/risks; [scoring guidance](https://hcm-rules.awsfcaj.com/5-scoring/) requires student design and explanation of architecture. These pages were reviewed on 6 November 2026. Additional documentation does not establish a grade or eligibility.
