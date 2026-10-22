> D2 follow-up: public exposure now confirmed; same literal additionally in historical PROJECT_SUMMARY.md:14; target is one legacy-pool identity. See [D2](d2-secret-exposure-review.md). D1 manifests are prior snapshots, not a staged commit.

# D1 — final documentation, Git readiness and demo handover

Date:2026-10-22, UTC+7. **LOCAL ONLY; AWS calls/writes0, no E2E/cleanup/commit/push.** AWS status is the dated B4/R7/C0 evidence, not a fresh live health assertion. Owner has **not set the environment end date**.

## Decision

**GO to request approval for a selected local commit set; NO-GO public push now.** HEAD still contains previously committed password literals; source removal is verified but rotation/revocation proof is unavailable. Never send passwords/tokens in chat to resolve this. Worklog main push also publishes GitHub Pages; its existing force_orphan=true workflow replaces the gh-pages publication-branch history (not main history), so these effects need explicit approval. No staging or history rewriting was done in D1.

GO bounded test demo using saved evidence; NO-GO production. Any new live demo/login/upload needs separate scope/quotas. Cleanup remains Approval C, independent of Git actions.

## Git review scope and evidence

Canonical repo: policy-assistant-github. Initial inventory:25modified tracked files,176untracked files,0deletions, empty index; tracked diff211,607bytes. Final exact per-file added/modified/deleted/index status and commit grouping: [Git file manifest](evidence/d1-git-files.json). Counts change as D1 docs/evidence are added; use [final readiness](evidence/d1-git-readiness.json), not initial counts, for approval.

Reviewed tracked diff and untracked candidates for publication hygiene; all candidate text files scanned, all40Python files AST parsed and JSON parsed. Runtime/frontend/CI/SAM/tests, auth helpers, public configuration, B1–R7/C0 reports and evidence were included. Checks follow changed code/configuration boundaries; this is **not an exhaustive vulnerability audit, dependency-advisory scan or production certification**. Private raw diff contains removed history literals and stays under ignored .aws-sam; never attach it publicly.

User changes were preserved. No reset/revert/clean/remove/add/commit/push. Runtime/template source-pair SHA remains e16c8529fdc8fe2fde6d20714699a19ce5ff8af5c962fd8e68021f2e7e34fbea. Worklog sibling review is separate; changes there are not included in an app-repo commit automatically.

## Security/publication findings

| Finding | Evidence / classification | D1 action / release gate |
|---|---|---|
| Credential literals in existing history | CONFIRMED HEAD PASSWORD literals: get_token.py:3, verify_e2e.py:5, verify_jwt.py:3, verify_search.py:4. Activity/rotation UNKNOWN; no values exported | Current files are guarded interactive wrappers; exact old password values absent from current candidates. **Block public push pending rotation/revocation proof and owner-reviewed history handling**. No credential/IAM changes or rewrite |
| Current candidate scan | No matched access-key/JWT/signed-query/private-key/full-account values or current auth-secret literals in inspected scope | Automated pattern/exact-value checks, not proof against every encoded/novel secret |
| Public identifiers | Cognito public client/pool IDs, API/CloudFront URLs, synthetic doc IDs/keys and SHA256 are configuration/evidence, not authentication secrets | Keep only necessary IDs; full account/ARN account segments masked in evidence. Public client has no ClientSecret. Do not use obscurity instead of JWT/owner checks |
| Private runtime artifacts | DPAPI, .aws-sam private state/raw diff/build ZIPs, .env, sessions, HAR/auth-state/traces | Gitignored and not tracked; added DPAPI/HAR/auth-state defense-in-depth rules. Ignore does not untrack existing files; verified no tracked DPAPI/.env/session/HAR in inspected paths |
| Screenshots/PDFs |18docs PNGs visually triaged via local QA sheet; R7 masked screenshots have dated network/hash evidence. Existing architecture.png is old reference, not current/student-authored architecture | Preserve originals; no raw browser trace/HAR intended for commit. Local fixture screenshots are not AWS proof; contact-sheet review is not exhaustive OCR. PDFs are2small synthetic fixtures |
| Personal contact exposure in worklog | Existing author/home contact email was unnecessary public metadata, not a credential or Budget recipient | Replaced Hugo author with existing GitHub handle; home contact is PENDING_OWNER_PUBLIC_CONTACT_APPROVAL in VI/EN. No email value in report; no AWS recipient changed |
| Default deploy target | samconfig.toml targets old policy-assistant; current source shares CodeUri while deployed test API/new and Worker/Recovery/old are intentional | Config left unchanged; README/runbook warn not to default deploy/sync. Future deployment needs account/stack/plan approval |
| Handover ZIP helper | scripts.build_release selects directories/extensions; not exact per-file allowlist and not comprehensive Gitignore/secret enforcement | Documented limitation; no ZIP built/published/certified in D1. Review full archive manifest before sharing; do not assume ignored JSON nested in docs is excluded |

History pattern scan traversed2local HEAD ancestors/46file versions; no matched AWS key/JWT/signed-query patterns. Password AST finding above remains. Remote refs, reflogs, deleted/unreachable objects, other clones and validity of old credentials are not verified. Revocation/rotation cannot be inferred from absence in working tree.

## Documentation consistency

Current README/PROJECT_SUMMARY/handover/verification/report and ten canonical workshop/proposal pages VI/EN now distinguish:

- **B4 AWS API/SDK19PASS,1browserNOT_RUN at that stage**.
- Original **B5FAIL**, preserved; not erased or relabelled.
- B5-R6 approved API-only deployment UPDATE_COMPLETE; virtual S3 addressing fits regional CSP without IAM/CSP/CORS broadening.
- **B5-R7 10browserPASS**,3login/3logout/2sessions/2uploads/2downloads/1,218bytes/27dynamicrequests. Real Edgeheadless, not local mocks.
- C0 inventory45resources/4Retain, DLQapprox1/ALARM, SNS0subscriptions, account20USD Budget/email delivery unverified; no cleanup or production-ready claim.

Local baseline129backend/17frontend/3browserfixtures/1fullstack; R4 additional private mixed-version test made130in that run, not130canonical tests. Nine live integration skips remain NOT_RUN. D1 does not rerun AWS or substitute local checks for AWS evidence.

Historical reports/counts/pending statements are explicitly labelled superseded snapshots; original evidence JSON/images stay byte-for-byte unchanged. No invented worklog dates/blog publication/events/office attendance/student drawing/demo expiry. Student facts/contact/artwork still need authentic owner evidence.

architecture.mmd is an assistant reference only, now showing SNS topic0subscriptions. Student must draw/check/explain their own official-icon diagram using architecture-self-draw.md; do not submit reference PNG/Mermaid as proof of student authorship.

## Files for future commit approval

Use explicit paths from Git manifest; do not blanket git add . including private files. Suggested sequence (messages only, **not executed**):

| Commit | Intended paths / purpose | Suggested message |
|---|---|---|
|1Backend/security |policy_assistant/, tests/unit/, runtime/test requirements, guarded get_token/test_auth/verify_* helpers |fix: enforce owner-bound versioned PDF processing and safe auth helpers |
|2IaC |template.yaml, deployment guard tests; retain existing user changes |infra: scope IAM logs and isolate retained test resources |
|3Frontend/CI |frontend/, package.json/package-lock.json, tests/frontend/, .github/workflows/ci.yml, offline verifier/demo support needed by checks |feat: verify browser upload processing and download integrity |
|4Tooling/runbooks |scripts/ remaining reviewed helpers, .gitignore, README/PROJECT_SUMMARY/architecture reference, operations/demo/student worksheet |docs: prepare test demo handover and explicit deployment boundaries |
|5Evidence |B1–R7/C0/D1 docs, sanitized JSON/screenshots/patches, synthetic fixtures, dated cost tables |docs: record AWS acceptance and cleanup inventory without secrets |
|Worklog separately |Existing sibling changes plus D1 VI/EN current-state/contact updates, Hugo workflow/config |docs: align bilingual workshop with AWS acceptance and open operational items |

Dependency order must leave a reviewable final set; CI may require frontend tooling and scripts in the same logical commit. Backend/IaC/frontend work largely predates D1 and must not be attributed to D1 alone. Empty index means no prepared commit selection exists yet. Worklog67modified+27new at D1 review includes earlier work, not67D1 edits.

Exclude: .aws-sam/**, DPAPI/vault/private target files, raw Git diff, credentials/.env/session/token URLs, Lambda ZIPs/packaged templates, node_modules/.venv/build/dist, HAR/browser auth-state/traces, raw cloud logs and recipient addresses. Sanitized docs/evidence JSON/PNG are intentionally different from private AWS API dumps; review before staging any new evidence.

## Checks actually run in D1

Fresh: candidate text/secret-pattern/exact-old-secret scans; Python AST/JSON validation; Ruff selected fatal rules; mypy backend; JS syntax; ignore/tracked-private checks; runtime/template fingerprint; git diff --check; Hugo0.167.0 build; internal HTML link checker. Hugo generated EN130/VI129 pages;131HTML/12,602references/0failures. Three existing theme deprecation warnings remain. No website publication.

No backend/frontend/browser suite rerun in D1 because runtime/tests unchanged; R4/R7 evidence remains dated. No AWS calls, release ZIP generation, cloud deployment or E2E. Local helper scan is not a substitute for a future approved secret scanner/dependency assessment before production.

## Demo and next approvals

[8minute demo script](demo-script.md), adjustable5–10minutes, defaults to saved masked evidence. Flow: problem→student diagram→login/search→regional upload→processing/frozen-version download/hash→two-user404/logout→SQS/DLQ/CloudWatch→cost/Retain/open items. No new live actions authorized by reading the script.

Before any push: approve exact staged diff/files; confirm rotation/revocation in an authorized environment (no secrets in chat); rescan staged content/history, exclude private artifacts, review screenshot provenance; preserve B5FAIL and NO-GOproduction; verify destination/branch; explicitly approve worklog main push's GitHub Pages publication effect. Push/commit approval and cleanup approval are independent.

Open operational items: SNS0subscriptions, Budget delivery unverified, DLQ diagnostic/ALARM, unknown environment expiry, restoration/load/concurrency/full security readiness, student-authored diagram and genuine FCAJ attendance/worklog evidence. **Nothing in D1 changes these AWS conditions.**

**LOCAL COMMIT PROPOSAL: READY_FOR_SEPARATE_APPROVAL. PUBLIC PUSH: NO_GO_PENDING_HISTORY_CREDENTIAL_GATE. COMMIT/PUSH/CLEANUP: NOT_EXECUTED.**
