# D2 — public credential exposure assessment

**Public exposure CONFIRMED. Credential validity / rotation-revocation / unauthorized access UNKNOWN.** Priority: request prompt containment approval; this is not proof that an attacker authenticated or that AWS IAM/root credentials were exposed.

## Evidence reuse and new work

Reuse D2 local-history and anonymous remote metadata collected2026-10-22 07:45UTC (14:45UTC+7); no unnecessary repeat/fetch. New AWS metadata inspected07:53UTC; exact final timestamps in [D2 evidence](evidence/d2-credential-exposure.json). No Cognito authentication, tests/builds/apps/PoC, Git writes or AWS mutations. Only filtered local assessment docs/evidence were written.

The first metadata attempt expected Cognito outputs that the old stack does not export; resource inventory was used instead. This was a local KeyError, not an AWS connection failure. Subsequent read-only mapping succeeded. No auth/retry/write was performed as a workaround.

## Exact public scope

Anonymous GitHub API reports HuynhHao080/aws-policy-assistant public; credential-free git ls-remote main is **80c4eeffd92c21c0cdd37b53591c2cd0daba3677**, equal to local HEAD. Anonymous commit metadata resolves that SHA. These observations establish public reachability of the content-addressed affected tree at the saved timestamp, not merely cached origin/main. No raw source/patch/password was exported into this report.

| Historical location in80c4eef | Source use / scope |
|---|---|
| get_token.py:3 | Cognito password auth, JWT diagnostics and potential jwt_token.tmp write |
| verify_e2e.py:5 | Same auth input followed by document upload-session/submit/status/download test code |
| verify_jwt.py:3 | Same auth input, JWT/API diagnostic code and potential jwt_token.tmp write |
| verify_search.py:4 | Same auth input and policy search diagnostic code |
| **PROJECT_SUMMARY.md:14** | **Additional disclosure of the same exact password**, found by D2 exact-value history scan |

All four scripts use the **same username, same password, same App Client**; four occurrences do not mean four different accounts/passwords. Comparison happened only in memory; no password hash or username value is in public evidence. The commit date is2026-10-21 09:58:34UTC+7. Root commit does not contain these scripts; no renames/alternate locations found in the locally reachable two-commit app history scanned.

Code invokes real Cognito USER_PASSWORD_AUTH without a mock fixture context. This supports intended live use, not a harmless-fixture classification. Source presence, historical report claims and an existing user do not prove that a prior authentication actually succeeded. These scripts were **not executed** in D2. Potential file/console output paths are static consequences if code runs; no claim that such tokens were actually recorded.

## Affected resource and identity

STS confirms account …0098, ap-southeast-1. Old stack **policy-assistant** resources, rather than its absent Cognito outputs, resolve:

- User Pool: **ap-southeast-1_zzeu6TjQs**.
- App Client: **usn7b60eevhmvgsao7ok63a8l** (public identifier, not a client secret).
- Logical IDs: PolicyAssistantUserPool / PolicyAssistantUserPoolClient.
- User alias in this report: **EXPOSED_LEGACY_IDENTITY_1**. Exact historical USERNAME resolves through AdminGetUser to one Enabled/CONFIRMED user; identity/PII is not printed. Operator must confirm that exact user inside the authorized Console, never infer a natural person's identity from the source string.

This pool/client differ from policy-assistant-fcaj-test TestA/TestB. No evidence this is an IAM access key, root password or permission to manage CloudFormation. Target is the legacy Cognito login profile, not the test users. Don't rotate every account or alter the entire old stack from this finding.

Metadata: client allows ALLOW_USER_PASSWORD_AUTH/ALLOW_REFRESH_TOKEN_AUTH, token revocation enabled, no ClientSecret; pool MFA OFF. User created2026-10-19 15:37:59UTC+7, last modified15:38:06 that day. Neither Enabled/CONFIRMED nor LastModified proves the old password valid or rules out every later security operation. Current token validity fields are recorded raw; empty units/defaults/history do not establish a universal safe-expiry cutoff for all previously issued tokens.

Legacy API has a JWT authorizer matching the pool/client and protected policy/document routes. This is a plausible downstream surface **if valid tokens can be obtained**. We did not invoke business routes or audit all legacy authorization/data effects; do not claim cross-user access, admin privileges or data theft.

## Classification

| Question | Verdict / evidence |
|---|---|
| Public exposure |**CONFIRMED**, exact remote SHA and public visibility |
| Real fixture/placeholder proven invalid |**Not established**; do not label FIXTURE |
| Current password ACTIVE |**UNKNOWN**, never tested |
| Prior successful use |**UNKNOWN**, static SDK calls are not auth-result evidence |
| Rotation/revocation |**UNKNOWN**, no administrative action evidence |
| Unauthorized access |**UNKNOWN**, no incident/audit-log attribution investigation |
| Priority |**HIGH priority containment request**, public candidate credentials tied to enabled user/no MFA; not a compromise declaration |

Skill triage verdict is confirmed **disclosure of credential-candidate inputs**, not confirmed successful sign-in. [triage-finding/v0 evidence](evidence/d2-triage.json) includes source/sink/control, boundary, confidence, rank1 and a separately authorized remediation handoff. No applicable SECURITY.md was resolved; user/README non-disclosure requirement is the policy basis.

## Two-repository scope and limits

Application:2locally reachable commits/46file versions. Worklog:1local commit/448file versions. Neither checkout shallow. All local refs and tracked/untracked nonignored working candidates scanned for AWS access-key patterns, JWT, signed queries, private-key blocks and exact exposed password. Only history matches are the five app paths above; current candidates and inspected worklog source/history have no matches. This is bounded secret-pattern review, not an exhaustive encoded/binary/vulnerability audit.

Ignored/never-stage paths include .aws-sam private state/vault/raw diffs, DPAPI, .env, jwt_token.tmp/session/URL files, HAR/auth-state, builds/dependencies. No tracked private-path matches or staged changes were found. Files ignored by Git were checked as metadata/ignore scope, not read wholesale to search for sensitive contents. Current D1 manifest is a candidate snapshot, not a staged commit or commit authorization.

Both repos are public at remote-metadata timestamp. Worklog main846d2ff matches local; remote gh-pages=f45b9fa07f4b5a6b5b522a5a9099cca4afd150a5. **Remote-only gh-pages content/history, PR refs, forks, caches, other clones, unreachable/reflog objects, GitHub Actions artifacts/logs and full-image OCR are not fully scanned.** No fetch/ref update/clone/push was performed to expand scope. No other secret matches does not mean every remote artifact is clean.

Worklog main push triggers Pages; existing force_orphan=true replaces publication-branch history. App CI performs offline checks, not a SAM deployment. Neither workflow was triggered. Public contact remains owner-confirmation pending; no email recipients are exposed here.

## Deploy safety — static only

samconfig.toml still defaults to **policy-assistant**, not test. README explicitly warns not to default deploy/sync. Current source SAM shares CodeUri; reviewed deployed test state is API=new ZIP, Worker/Recovery=old ZIP. B5-R6/C0/D1 document this; no claim that generic sam package/deploy reproduces the API-only plan. No config changes/deploy occurred. Any later safety hardening of defaults requires its own review, not a silent architecture change in D2.

## Remediation choices

| Choice | Conditions / decision |
|---|---|
| A: keep history as invalid fixture |Only with authoritative evidence values never worked/are irreversibly unusable; **not supported now** |
| B: contain/revoke/rotate |**Recommended D3**, exact one legacy identity, sessions + password considered separately. Old stack exception and legitimate-user disruption require explicit approval |
| C: clean history |Only after credential safety; separate Git approval, isolated clone/secure backup, all affected five paths/refs/tags, collaborator/CI/PR coordination and sanitized validation. No rewrite now |

Removing history cannot recall forks/caches/copies and does not revoke credentials. Rewriting changes commit IDs, can invalidate tags/signatures and break evidence links; old clones can reintroduce content. Preserve a restricted incident record and old→new SHA mapping without passwords, plan branch protections/lease checks and owner-authorized remote update. Do not overwrite the current dirty worktree or force-push without a separate concrete plan. GitHub Support availability/caches are not guaranteed to be purged. [GitHub guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

## D3 scope and Git gates

[Prepared D3 approval plan](d3-credential-containment-approval.md) is **NOT_APPROVED**: targeted disable/global sign-out, then optional approved password replacement while user stays disabled; no old-password test. Owner confirms target and disruption within AWS Console, not chat. No TestA/TestB changes, IAM/client/pool/API updates or data deletion included.

**Local selected commit:** GO to request separate approval after a staged-content scan; committing does not sanitize ancestor history. No staging/commit in D2. New report files change D1's candidate manifest; refresh it before any approved selection.

**App public push:** NO-GO until approved containment/rotation evidence and residual-token handling/history decision. Repo is already public: stopping new pushes does **not** contain existing exposure; do not postpone D3 while planning Git cleanup.

**Worklog Pages:** no matching secret in inspected source/history, but **NO-GO publish now**: no publication approval, remote-only publication artifacts not fully scanned, potential sensitive-source reintroduction in later content, and contact/screenshot/effect scope must be accepted. This is not a claim that worklog contains the same password. Worklog local commit can be proposed independently; automatic Pages deployment must be explicit in any push approval.

AWS WRITES0; AUTHENTICATION0; ROTATE/REVOKE NOT_EXECUTED; STAGE/COMMIT/PUSH/REWRITE/PAGES/CLEANUP/DEPLOY NOT_EXECUTED. DỪNG chờ D3 riêng.
