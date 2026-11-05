---
title: "Time-bounded policies — controlling AI sources"
date: 2026-11-05
weight: 4
---

# A relevant source may no longer be applicable

A shop assistant can retrieve the right passage from a policy that has expired or is not yet effective. This extension adds business eligibility before retrieval and a final source check before answer persistence. This AI-assisted material requires personal review, execution and explanation by the student.

## Practical behavior

Administrators set **Effective from / Through the end of**, inclusive in **Vietnam UTC+07**. Blank bounds are unlimited; impossible dates and end-before-start are rejected. Existing undated policies remain compatible. This controls eligibility of the current policy source; it does not turn “12months from receipt” into an absolute warranty date or adjudicate historical-order entitlements.

Saving a draft does not change the published window. Publishing a future policy does not activate it immediately. Catalogue filters select active/upcoming/expired/invalid dates. Corrupt imported dates are excluded from lookup but remain editable for repair. The editor separates draft bounds from the existing published snapshot. Account quota cohorts remain UTC and are independent of policy business dates.

## AWS flow and boundaries

1. Authenticated administrators save dates with isolated drafts, revisions and transactional audit. Publication is separate.
2. Exact lookup, search and RAG exclude non-current/invalid policies. Search retains its scan budget and cursor; an empty filtered page can still have continuation.
3. Before saving a sourced result the API consistently rereads each cited policy and checks its published facts/window/state. A detected change returns409without saving the answer or automatically regenerating it.
4. The internal fingerprint covers published facts only, so isolated draft edits do not invalidate an unchanged public snapshot. Fingerprints are excluded from model prompts, history/responses/exports. New citations may retain date metadata.

No service, scheduler, table/index, route or execution IAM grant was added. Original/processed templates differ only in six code keys; additional CloudFormation dependency entries have identical processed properties. Final checks add at most5logical consistent GetItem calls for distinct cited policy IDs. No background task/model invocation occurs at a date boundary.

This is a **point-in-time check**, not a lock until a customer reads the answer or a common policy/history transaction. A policy can change immediately after the final check. History remains its original snapshot. Once bounded publications exist, do not downgrade to a runtime that ignores their dates.

## Actual evidence

| Scope | Result and limit |
|---|---|
| Local Python |298passed,11live skipped;25new cases cover dates, drafts, pagination and changes during generation |
| Frontend |59passed;5new cases cover date validation and editor/filter/repair DOM flows; not real-browser visual acceptance |
| GitHub CI |[Commit5498d92 passed](https://github.com/HuynhHao080/aws-policy-assistant/actions/runs/42056109331): builds/tests/SAM lint/source integrity |
| Live AWS |16authorization/read/draft API checks passed; one suppressed-invitation identity and three operator-seeded non-current/invalid policies |
| Cleanup |Identity and all3temporary rows removed; no `/ask`, publication, embedding, OCR or PDF call in this API run |
| Artifacts |37frontend files and6Lambda hashes match; stackUPDATE_COMPLETE and CloudFront invalidation completed |

[Sanitized evidence and source hashes](/aws-internship-worklog/evidence/policy-validity-2026-11-05.json). Report hashes use canonical JSON so Git CRLF/LF normalization does not change them; the JSON records the formula. Operator fixtures are not model output, live publication or factual-accuracy measurements. Earlier quality/CI/browser reports retain their original scopes/dates. No new load or restore validation is claimed.

## Suggested four-minute personal demo

1. Explain a fictional dated source and distinguish its eligibility window from warranty duration measured from a purchase/receipt.
2. Open the editor, save a future draft and show the published snapshot is unchanged. Understand that explicit publication uses the existing embedding pipeline; do not manipulate real policies for a demo.
3. Run `python -m pytest tests/unit/test_policy_validity.py -q`. Label moto/model mocks clearly; explain UTC+07boundaries, filtered cursors and a change before final checking that returns409without history persistence.
4. Contrast real API evidence with mocked race tests. Explain no-cron design, why consistent reads are not locks, rollback compatibility and historical snapshots.

This is a plan, not a personally recorded/executed presentation. Do not alter the host clock or real shop policies for simulation. The student's own diagram, Calculator, actual blogs and participation evidence remain required; this feature does not guarantee FCAJ points.
