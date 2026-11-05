# Quality feedback and FCAJ readiness extension — 2026-11-04

Primary remains djreo5eptvwk5.cloudfront.net / policy-assistant. Application source is the canonical policy-assistant folder. The actual student worklog is the separate aws-internship-worklog repository; inspected read-only and not modified. Earlier reference-submodule edits were restored, with optional technical drafts archived locally.

## Delivered features

- Owned answer feedback: helpful/not-helpful, controlled reasons, change and withdrawal; explicit revisions and same-target retry idempotency.
- Aggregate-only administrator dashboard with current/previous UTC answer cohorts, citation presence, mean server processing time, scope/refusal and feedback counts; JSON export.
- Atomic history+quality persistence, signed feedback deltas, underflow guards and account-deletion conditions. Bounded identical-token retries apply only to DynamoDB transaction conflicts, never model generation.
- New tracking version only: no private-history backfill. Expired history is hidden before TTL deletion. Anonymous rollups do not contain owner/conversation IDs, questions, answers or source excerpts.

## Actual verification

- Python3.12 full suite: **251 passed, 11 opt-in live skipped**.
- Frontend: **54 passed**, including isolated synthetic DOM feedback/dashboard flows; production build and fingerprint checks passed. No real-browser visual acceptance is claimed.
- SAM lint/validation/build succeeded. Source-template diff is exactly six artifact keys and two explicitly JWT-protected routes. No new table, execution IAM grant, model/budget/quota parameter or fixed-cost service was added; SAM adds the API invoke permissions.
- Change set `public-final-1793788043`. Lambda SHA256 `974197f606822d42a51a922694a30de95be06ac57a5a4ff30c1837089ab94273`. Template SHA256 `81b292927bff436f13e2b08861997f2b312d1b89b37e628029d65aa9158adfed`.
- **15 live metadata/API/cleanup checks passed**. Two disposable identities, actual save_answer persistence via operator CLI transport and real feedback APIs used a nonce-protected year2000 synthetic cohort excluded from normal dashboards. Ownership/admin restrictions, no double counting, counter movement/withdrawal, reason validation and aggregate sanitization passed.
- Both identities and owned history partitions are gone, and the synthetic cohort was conditionally deleted with its nonce. No real current/previous-month cohort was seeded, model/PDF call made, owner account/policy changed or email sent. Seeded1234ms is a test fixture, not a real model-latency result. See [live evidence](quality-live-acceptance.json).
- Latest frontend publication/hash and six Lambda checks are recorded in [artifact verification](quality-artifact-verification.json).

## Scope and limits

Citation rate is not correctness; feedback is opinion; timing excludes persistence/browser latency. The monthly rollup key is a deliberate small-load trade-off, not a high-throughput benchmark. Real-history/account deletion can leave identifier-free cohort totals; retention is65 days after the last metric update. Old history is not migrated. No new model accuracy, load, restore, alert delivery or hosted-login/visual test was run.

FCAJ sources were reviewed from the user-provided rules. The code upgrade does not certify academic eligibility or personal authorship. Worklogs, blogs, attendance/events and the final student-designed AWS diagram remain personal evidence. The actual worklog already has VI/EN technical material and historical checks; [readiness](fcaj/READINESS.md) and [handoff](fcaj/WORKLOG-HANDOFF.md) propose reconciliation without rewriting it. The reference Hugo preview succeeded with pinned0.134.3, but it is not a build/publication of the separate worklog.

Guide: [Chất lượng AI](HUONG-DAN-CHAT-LUONG-AI.md). Official requirements/scoring links are in the readiness matrix.
