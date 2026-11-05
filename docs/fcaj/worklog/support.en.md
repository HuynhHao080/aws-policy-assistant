---
title: "Support collaboration — assignment and internal notes"
weight: 5
---

# Coordinating support staff

This AI-assisted technical chapter requires student review and explanation. It is not a student activity log or an FCAJ scoring decision. The [primary application](https://djreo5eptvwk5.cloudfront.net/) still uses DEMO policies.

## Practical problem

Two staff members opening one case can duplicate replies or lose handover context. Administrators can claim a case for themselves, release it, or take over with a reason. Mine/unassigned/other filters organize the queue. A different assignee must explicitly take over before replying publicly or changing status/priority. All trusted administrators can still read notes; assignment is coordination, not a new restricted staff role.

The staff-only panel separates notes from customer replies. Unsaved draft warnings, reload and revision conflicts protect concurrent work. Staff labels use shortened IDs. No staff directory, realtime push, automatic email or SLA timer is claimed.

## Data and consistency

- Up to 20 internal notes of 1,000 characters; assignment history retains the latest 10 events. Public messages retain their independent 20 × 1,500-character limit.
- Assignment comes from the authenticated JWT identity. Takeover requires a 10–300-character reason. Customers cannot inject private fields.
- Staff and customer writes share a revision. DynamoDB transactions check both revision and account-deletion state. On conflict, reload, inspect new content and retry deliberately.
- Customer detail/list/export DTOs exclude notes, assignees and reasons, including an administrator using their own customer view. Support content is not AI retrieval material.
- Notes share the ticket's original maximum 90-day lifetime. Internal activity does not extend it. Customer account deletion purges the ticket; staff account deletion does not remove contributions on customer-owned tickets. Audit stores action metadata, not note/reason bodies. Application expiry checks remain effective while asynchronous TTL cleanup is pending.

No table, index, route, IAM grant or AWS service was added. Queue filters use bounded scans and pagination, not a global count.

## Observed verification

| Scope | Result |
|---|---|
| Python 3.12 | 322 passed, 11 opt-in live tests skipped; unit fixtures/mocks are not real model acceptance |
| Frontend | 67 unit/DOM passes; not browser visual acceptance |
| Real AWS API | 20 HTTP checks with 3 invitation-suppressed QA identities and one synthetic consented support ticket |
| Cleanup | Three accounts deleted; the test customer's Support partition confirmed empty; audit metadata retains its normal lifecycle |
| Artifacts | 40 frontend files and 6 Lambda hashes matched; UPDATE_COMPLETE and Completed invalidation |

The run did not invoke generation, embeddings, PDF/OCR, email delivery or real customer processing. Reports are timestamped 5 November 2026 UTC, corresponding to 6 November in Vietnam. [Sanitized JSON](/aws-internship-worklog/evidence/support-team.json) includes checks and canonical JSON hashes of source reports without tokens, customer IDs or ticket content.

[Source verification and limits](https://github.com/HuynhHao080/aws-policy-assistant/blob/main/docs/support-team-verification.md). [Operator guide](https://github.com/HuynhHao080/aws-policy-assistant/blob/main/docs/HUONG-DAN-PHOI-HOP-HO-TRO.md). [Runtime source CI](https://github.com/HuynhHao080/aws-policy-assistant/actions/runs/42068819957).

## Four-minute demo plan — not a recorded demonstration

1. Customer submits a consented case; staff A claims it.
2. Staff B adds an internal note; the customer's refreshed view still contains public conversation only.
3. B takes over with a reason. A's stale revision conflicts; reload and inspect assignment history.
4. B replies publicly, then the customer follows up without losing internal context. Explain cleanup, retention and administrator access boundaries.

Test counts do not establish accuracy, SLA or FCAJ grades. The student must draw and explain the AWS diagram; three actually published blogs, office/event evidence, Pricing Calculator and a demo video remain personal deliverables. Historical B4/B5/B5-R7 results stay unchanged.
