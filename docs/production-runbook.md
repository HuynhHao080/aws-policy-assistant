# Production operations — 2026-10-30

## Release order

1. Install Python/frontend dependencies. Run Python 3.12 tests, frontend tests/build, SAM validation and SAM build.
2. Run `deploy_release.py prepare` with the selected notification email. This uploads one immutable code artifact and creates a non-executing change set. Run `inspect` and review adds/modifications/replacements.
3. Execute the reviewed change set only when the replacement guard passes. Inspect stack events until the update completes; never execute another update while one is active.
4. If the phase was `index-migration`, prepare/inspect/execute the final phase after the first index is active. Both GSIs must exist before frontend publication. Recovery is disabled in the migration phase.
5. Publish compiled frontend assets/config and invalidate CloudFront. Verify public HTTP security headers, sign-in redirect and email-confirmation flow.
6. Run two-user live acceptance with synthetic data: upload, process, exact download-byte hash, isolation, cited AI, history, policy administration, deletion, and OCR. Keep tokens/passwords/presigned forms out of evidence.
7. Grant the selected administrator role only after email confirmation. Confirm the SNS subscription email and verify the budget notifications' recipient. Publish real shared policies through the admin interface; no original sample row becomes customer content automatically.

## Recovery and alarms

- API `5xx` catches handled backend failures that do not increment Lambda Errors. API duration alarm approaches its 29-second timeout.
- Worker/dispatcher errors and worker throttles notify the alert topic. Main worker DLQ, dispatcher failure DLQ and queue-age alarms cover processing backlog.
- Metadata streams are the durable outbox: pending work exists before dispatch. Dispatch returns partial batch failures by DynamoDB sequence number. SQS workers return failed message IDs.
- Scheduled recovery queries the status index every minute. Pending/processing/deleting work older than 10 minutes is recovered. Three exhausted processing attempts become failed. OCR polls resume after about a minute; an OCR job older than one hour becomes failed.
- A failing deletion remains blocked/deleting and retries; investigate alarms rather than claiming the customer's data is already gone. Never assign an unknown historical owner or delete legacy uploads as a generic cleanup step.
- Inspect a failed record's `doc_id`, state and error code, not PDF content or tokens. Do not blindly replay an entire DLQ; repair the root cause and replay only identified synthetic/authorized jobs.

## Retention and privacy

- New quarantine uploads expire after two days, including noncurrent versions. Existing `uploads/` objects are not targeted by that rule.
- Processed sources and extraction/vector files under `documents/` are private and kept until deletion. The selected upload version is copied into this server-controlled prefix before processing is marked complete.
- PDF deletion removes all object versions/delete markers for that document. Metadata tombstones last 30 days. History expires after 30 days; audit events after 90; usage counters after 65 days. TTL deletion is asynchronous.
- Account deletion blocks application access before background purge, removes history and private files, then deletes Cognito identity. Operational audit/counters and recovery backups have their documented retention. Cloud operator credentials still control infrastructure; the customer admin page is not an AWS operator console.
- DynamoDB point-in-time recovery protects tables. A restore is a separate operator action into a new table, followed by verification and an environment update; never restore an entire backup directly over live customer state.
- Data resources use Retain/UpdateReplacePolicy Retain. This guards stack operations, not an authorization to delete customer records through SDKs.

## Budget and scale

- Defaults target a small public launch: 300 uploads/month, 2,000 question attempts/month, 100,000 authenticated application requests/month, 100 signup attempts/month and 1,000 total public signup attempts.
- Atomic daily/monthly counters limit expensive operations. A quota reservation counts an attempt and is not refunded on an ambiguous downstream error. The whole AWS account budget alerts at USD 25/40/50; it does not stop charging automatically.
- S3 stores extracted PDF text. Lexical retrieval ranks bounded sets of up to 20 recent owned documents, 10 explicit PDF selections and 1,000 evaluated policy rows. Existing text indexes remain readable.
- No load benchmark or availability SLA is claimed by unit tests. Increase quotas/concurrency or replace bounded retrieval only after measuring real demand and revisiting the USD 30–50 budget.

## Rollback

Keep the previous source backup and the release artifact/checksum. Use a reviewed CloudFormation update to restore the previous application artifact when appropriate. Retain new user data and indexes. A pre-v2 handler does not understand the new owner/extraction workflow; do not blindly downgrade the public API to the old demo implementation. If public acceptance fails, keep the frontend unpublished or place a clear maintenance page while repairing the revision.

## Current answer serialization

Global Claude Haiku 5.5 uses Converse with one forced `emit_policy_answer` tool. The application validates the answer, source IDs and current policy facts before history is written. The request has a 900 output token cap, disabled thinking and low effort. The SDK makes one attempt.

See [AWS Claude tool use](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages-tool-use.html) and [migration verification](haiku55-migration.md). Source IDs are checked against the retrieved excerpts. Review the actual content when assessing factual quality.

When local Python SDK networking is unavailable, `scripts/check_retail_live.py --aws-cli` uses AWS CLI control calls and real HTTP application requests. It creates only an invitation-suppressed disposable test identity and cleans it after the run. Credentials remain in memory or a short-lived user temp file and are not printed. Review its ignored report `.deployment/retail-http-acceptance.json`, including cleanup status. `scripts/run_retail_regression_cli.py` tests the deployed, byte-matched public-policy answer code with CLI model transport; it does not test browser interaction or private-PDF workflows. `--candidate` explicitly permits only a local assistant.py candidate and records that different scope. Keep candidate and deployed evidence separate.

## Policy draft operations and frontend compatibility

Administrators use the catalogue and draft workflow in HUONG-DAN-QUAN-TRI.md. Publishing builds text search fields. Archive retains content for republishing. API consumers fetch the current revision before changing a policy and reload after a 409.

Build the frontend before its tests: the build contract check validates generated HTML/JS/CSS. The build uses content-fingerprinted bundle filenames, removes only the two obsolete fixed-name generated local files, and never deletes old hosted bundles. Publish assets/config before entry HTML, preserve MIME types, then invalidate CloudFront. Do not copy the synthetic `.deployment/admin-ui-fixture` build or mock auth module into frontend/dist or hosting. The production build fails if known fixture-auth markers appear. Validate the immutable Lambda artifact/new authenticated routes before publishing the matching frontend.

For repeatable live admin acceptance, `scripts/check_admin_live.py` creates one invitation-suppressed synthetic identity, initially verifies ordinary-user denials, then temporarily grants that test identity administrator membership. It modifies only a nonce-guarded QA-ADMIN policy, archives/deletes it and deletes the test account through the application. Review both ignored acceptance and cleanup reports; never use the owner's identity or real policies as disposable test fixtures. A small clearly marked synthetic policy is briefly published, so run this only as an authorized acceptance workflow. Earlier helper/fixtures are not extra production stacks.

## Support release operations — 2026-11-04 handover

Current release/evidence: [support verification](support-verification.md). SupportTable is on-demand, encrypted, PITR-enabled, TTL expires_at, Retain on deletion/replacement. It has no secondary index; staff queue scans at most the requested 1–50 evaluated records/page. Monitor cost/queue usage before increasing traffic; do not infer total backlog from a filtered page. TICKETS_PER_MONTH defaults200 and customer creation5/day UTC. Content expires90days from creation; audit stores action metadata only.

Account deletion now strongly queries and batch-deletes owned support rows before Cognito deletion. Failed purge must remain blocked and retry through the existing worker/recovery path. Never remove the identity first to conceal an incomplete purge. Do not roll back to a worker that lacks ticket purge after real support data exists; preserve compatible cleanup code or block account deletion while preparing a reviewed fix. Retained tables/backups need a separate operator-approved recovery/retention process; TTL does not imply immediate removal from backups.

API SupportTable permissions: GetItem/PutItem/DeleteItem/Query/Scan. Worker: Query/BatchWriteItem. Account-deletion guard uses ConditionCheckItem only on UsageTable. Staff replies remain in-app; schedule human review of the queue and do not promise automatic email delivery.

Verification helper: `scripts/check_support_live.py` creates only disposable identities/synthetic data, invokes real model requests within quotas and cleans them through the account workflow. Keep its ignored cleanup manifest until every cleanup flag is true. Do not publish credentials/JWT/presigned forms. Review any changes to its target stack/account before running.

## Daily operational metadata check

Run `python scripts/operational_status.py --aws-cli` when CLI networking is preferred. The script verifies the expected AWS account before reading further and records deployment state, selected account verification/group membership, SNS confirmation, alarm states/actions, approximate queue sizes and support-table TTL/PITR. It never queries support messages or PDF contents. Output is `.deployment/operational-status.json`. This is a point-in-time snapshot, not proof that alert email arrived or a database restore succeeded.

Support triage adds category/order-reference filters and staff-only priority without additional tables, indexes, routes, IAM grants or AWS services. Exact-reference filters remain a bounded scan, suitable for the current single-shop quota. Revisit indexed access patterns after measuring larger real workloads. UI monthly support usage counts creation attempts; it is not a count of open tickets. Review high-priority and unprocessed requests each work shift as described in HUONG-DAN-HO-TRO.md.

For regression without any AI calls or PDF uploads: `python scripts/check_support_live.py --triage-only`. It creates only two invitation-suppressed disposable test identities and synthetic support messages, then cleans both via account deletion. Preserve ignored cleanup evidence until identities_cleaned/support_purged are true. Full PDF/model acceptance is a separate, explicitly selected test scope; prior results must not be described as rerun by triage-only mode.

## Shop profile operations

The selected primary website remains djreo5eptvwk5.cloudfront.net / stack policy-assistant; policy-assistant-fcaj-test is a separate reference environment. Shared shop contact data lives at UsageTable pk app#shop-profile, without TTL, separate from quota keys and all AI policy retrieval. It survives individual administrator account deletion like other shared shop content. Do not remove the entire UsageTable as a counter reset. Backups may retain prior shared values; unpublish is visibility removal, not a backup purge.

Only explicitly published fields are returned to signed-in customers. Protect draft publication and run normal human review of contact accuracy. The profile's live label does not approve DEMO policy terms, verify an email inbox, connect an order system or add an SLA. No automatic copying of owner email occurs. Audit events record action/resource/actor only.

`python scripts/check_shop_live.py` verifies the expected deployment hash/account before creating an invitation-suppressed synthetic identity. It refuses to overwrite an existing operator draft; only saves/discards a nonce-guarded private incomplete draft and tests rejected publication. It never publishes fake contact details, invokes AI or modifies a real policy/PDF. Preserve .deployment/shop-test-cleanup.json until profile_cleaned and account_cleaned are true. Full successful publication/withdrawal paths are verified offline; if not exercised live, keep that limit in the acceptance report.

## Quality rollups and safe acceptance

Monthly quality counters reuse UsageTable `quality#YYYY-MM`; private feedback stays in owned HistoryTable rows. Existing execution IAM suffices because the owned lookup uses an exact partition/sort-key Query and replacement Put, with UsageTable Update/ConditionCheck. No global history scan or administrator PDF privilege is added. Counters track newly persisted answers only; retain source/version-specific historical acceptance reports.

Monthly aggregate keys can contend at higher throughput. Existing small quotas/concurrency bound this design; quality.commit retries only transaction-conflict persistence up to3 identical-token attempts, never the model. Revisit rollup sharding/stream aggregation after measuring larger traffic, not merely to add services. Conditional conflicts, counter underflow and deletion races fail atomically.

`python scripts/check_quality_live.py` validates expected account/artifact/routes, creates two invitation-suppressed identities and reserves a nonce-guarded year2000 test cohort outside the dashboard month allowlist. The actual save_answer helper seeds one synthetic private answer through operator CLI transport; real feedback APIs then test ownership, retry/idempotency, change, withdrawal and admin-only sanitized reporting. No model or PDF call occurs and no real current-month cohort is seeded. Account cleanup uses the application workflow; the isolated metric item is conditionally deleted only with its nonce after identity cleanup. Keep `.deployment/quality-test-cleanup.json` until both cleanup flags are true. A seeded fixture is not real model generation or latency measurement.
## Policy validity operations

Published policy bounds are inclusive Vietnam UTC+07 calendar dates; quota cohorts remain UTC. No scheduler changes state: public lookup/search/RAG compute it when reading. Administrators can filter active/upcoming/expired/invalid published snapshots; isolated draft dates do not control the public snapshot. Existing no-date rows remain unbounded. Keep scan cursors/budgets and distinguish a filtered page from total backlog.

Before saving a cited policy answer the API consistently rechecks current published facts/date bounds. A409requires a fresh user question attempt, not an automatic generation retry. This is a point-in-time check, not a lock held until a customer reads the response. Historical answers remain snapshots. Additional reads are bounded by unique cited policy IDs (at most5).

Do not roll back to a pre-validity API once bounded published policies exist: that handler ignores the bounds. Preserve validity-aware read/revalidation code or use a separately reviewed maintenance plan; never silently clear dates/reset the table to make old code work.

The guarded `check_policy_validity_live.py` checks the exact deployed artifact before writes and uses one suppressed-invitation identity plus three non-current synthetic rows. It never calls generation, embedding, OCR, PDF upload or publish. Review both acceptance/cleanup flags. Operator-seeded non-current rows and draft API tests are not live publication/model acceptance. Existing quality counters are not seeded; HTTP request quotas/audit and normal cloud operations still apply.


## Support staff coordination

Use the [staff guide](HUONG-DAN-PHOI-HOP-HO-TRO.md) and [release evidence](support-team-verification.md). Assignment coordinates trusted administrators; it is not a separate restricted role. Claim only assigns the authenticated staff identity. Another assignee must explicitly take over with a reason before a public update. All administrators may collaborate through internal notes. Never paste secrets into notes; audit metadata omits note/reason bodies.

Limits: 20 internal notes × 1,000 characters, rolling last 10 assignment events, independent public message limit. Notes do not extend the original 90-day ticket expiry or alter its public update timestamp. Deleting the customer purges the ticket; deleting staff does not erase contributions on customer-owned records. Revision conflicts are expected across public and internal activity: reload and review before retrying. Filtering uses bounded scans and cursors; an empty page is not a global queue count.

The live helper `scripts/check_support_team_live.py` is opt-in and writes synthetic fixtures. Review its primary-account/artifact guards and private cleanup manifest before running; never substitute real customers. Acceptance verified three suppressed QA identities and one ticket removed through the account-deletion workflow. Audit metadata and retained logs/backups follow their lifecycle; an empty Support partition is not proof that every historical copy is erased. No extra IAM/table/index/service was required.

## Cognito hosted sign-in branding

The production client uses Cognito Hosted UI (classic). The CSS and PNG wordmark are in `frontend/branding`. This client-level setting is applied separately from the SAM stack and frontend build. Read the pool and client IDs from stack outputs before applying it.

```powershell
aws cognito-idp set-ui-customization --region ap-southeast-1 --user-pool-id $poolId --client-id $clientId --css file://frontend/branding/cognito-classic.css --image-file fileb://frontend/branding/cognito-wordmark.png
```

Keep CSS and logo together in the request. Check the hosted sign-in page from the application's normal sign-in entry point after the CDN serves the new assets. [AWS hosted UI branding reference](https://docs.aws.amazon.com/cognito/latest/developerguide/hosted-ui-classic-branding.html).
