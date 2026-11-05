# Support staff collaboration — deployed verification

Primary application: https://djreo5eptvwk5.cloudfront.net/. Runtime source commit: `6225d5c66ed5f114be1e3cf004df937ab0e58f67`; [GitHub CI passed](https://github.com/HuynhHao080/aws-policy-assistant/actions/runs/42068819957). Evidence timestamps below are UTC, 5 November 2026 (6 November in Vietnam).

Administrators can claim their own assignment, release it, or take over with a reason. Other assignees must explicitly take over before public reply/status/priority changes. Collaborators can add internal notes. This coordinates trusted administrators; it does not introduce a restricted staff role or hide notes from another administrator.

The private panel separates notes from messages sent to customers. Unsaved drafts are guarded on reload, close and navigation; clearing the session clears private UI state. Customer detail/list/export DTOs exclude assignment, notes and reasons, including an administrator's own customer view. No support content enters AI retrieval. Internal actions preserve public update time, message count and the original 90-day expiry.

| Verification | Observed result |
|---|---|
| Python 3.12 suite | 322 passed, 11 opt-in live tests skipped |
| Frontend unit/DOM suite | 67 passed; simulated DOM, not visual browser acceptance |
| Build | Frontend build, SAM build and validate/lint passed |
| Real HTTP | 20 checks passed with one synthetic consented ticket and three invitation-suppressed QA identities |
| Cleanup | Three accounts deleted and customer Support partition confirmed empty; audit metadata retains its normal lifetime |
| Deployment | CloudFormation UPDATE_COMPLETE; 6 Lambda hashes matched; 40 frontend files matched local bytes; invalidation Completed |

The HTTP run checked customer/admin boundaries, self-claim, double-claim conflict, public-reply protection, collaborating notes, reason-required takeover, mine/other/unassigned filters, stale revision rejection, customer follow-up preservation and audit text exclusion. It did not invoke generation, embedding, PDF/OCR or email delivery. See [live results](support-team-live-acceptance.json), [artifact evidence](support-team-artifact-verification.json) and [template review](support-team-template-review.json).

Code SHA-256: `5528dd1d91ab278545472fdb861f7e2678df2a3fdce47bdc5745f851f1a1a359`.

Template SHA-256: `95666c09c6a7e849bc36f4730ceea31930bea2bbf07a0d587fc7e8a5b0e3a8fa`.

Original and processed templates differed only at six Lambda code keys. CloudFormation listed twelve resources because of dependent references; their reviewed non-code properties were identical. No table, index, route, IAM grant, service, model, quota or budget was added.

## Operational limits

Notes: maximum 20 per ticket, 1,000 characters each. Assignment history: rolling last 10 events; reasons can age out. Public messages retain their independent limit of 20 × 1,500 characters. Shared ticket revisions intentionally make simultaneous staff/customer writes conflict; reload and review before retry. Transactions also reject writes when the owner starts account deletion.

Assignment labels use shortened staff IDs, not a staff directory. No realtime push, automatic email, SLA timer or new confidentiality tier is claimed. Internal notes share the customer's ticket lifecycle; deleting a staff account does not erase that staff member's contributions on customer-owned tickets. Audit stores action metadata, not note/reason bodies. TTL is asynchronous; application reads/writes enforce expiry.

Rollback must keep the preceding policy-validity checks, customer DTO allowlists and account-purge behavior. Prefer a forward fix; do not deploy a pre-validity runtime that ignores effective dates. Historical pilot Change Sets and canary markers were left untouched. No new visual browser, load, restore, AI accuracy or alert-delivery acceptance was performed. DEMO policies remain DEMO, and personal FCAJ evidence remains pending.

Operator guide: [Phối hợp hỗ trợ](HUONG-DAN-PHOI-HOP-HO-TRO.md). Automated live helper: `scripts/check_support_team_live.py`; its opt-in fixture writes and cleanup are separate from ordinary unit tests. Private cleanup manifests stay in ignored `.deployment`, not public evidence.
