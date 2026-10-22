# D3 proposal — targeted legacy Cognito containment

**PREPARED_NOT_APPROVED. No AWS write/login/rotation/revocation in D2.** This is an approval proposal, not an executable script. Do not place passwords in CLI arguments, chat, docs, environment dumps or Git.

## Exact boundary requiring owner approval

- AWS account …0098, ap-southeast-1.
- **Legacy stack policy-assistant**, Cognito pool **ap-southeast-1_zzeu6TjQs**, client **usn7b60eevhmvgsao7ok63a8l**.
- Exactly one user: **EXPOSED_LEGACY_IDENTITY_1**, resolved from the identical USERNAME in the four auth scripts of commit80c4eeffd92c21c0cdd37b53591c2cd0daba3677. Operator must match the exact profile in the authorized AWS Console before approving; do not guess a person, send the username/password in chat or select another similarly named account.
- This needs an **explicit narrow exception** to the existing “do not change legacy resources” boundary. It is not approval to update the CloudFormation stack, UserPool/AppClient configuration, API, roles or other users.
- Current D2 metadata Enabled/CONFIRMED, native password auth allowed/no MFA; password validity, historical success, rotation and unauthorized access UNKNOWN.

Owner must confirm account ownership, target profile and acceptable legitimate-user disruption. If identity/account mapping changes, stop. Do not substitute TestA/TestB or create/delete a user: preserving the original sub avoids changing ownership bindings.

## Proposed approval options — choose explicitly

| Option | Maximum intended writes | Result / limitation |
|---|---|---|
| D3-A containment only, recommended first |1AdminDisableUser +1AdminUserGlobalSignOut for this user |Prevents new sign-in while disabled and revokes Cognito sessions; **does not prove every offline-validated JWT immediately stops**. No new password; user remains disabled |
| D3-B optional rotation after A |1AdminSetUserPassword with owner-approved permanent/temporary mode, then1additional AdminUserGlobalSignOut |New unique secret via authorized Console/password manager or memory-only tool flow, user stays disabled. No automatic enable or authentication. Temporary/permanent choice must be approved, not assumed |
| D3-C restore access/verify new login |Separate future scope, not included in A/B |Possible enable/new-credential login and API checks require explicit separate approval and data/request bounds |

If owner approves A+B together: caps are **1disable,1password-set,2global-sign-outs** across the whole approved operation. No automatic retries or alternative remediation after timeout/failure. If only A is approved, do not perform B. Sending notifications/reset emails/SMS is not approved; select a non-notification administrative workflow and stop if delivery/recipient action becomes necessary.

No credentials generated or vaulted in D2. For B, choose a private handoff inside AWS Console/password manager; if an agent sets it later, use memory-only API parameters and a new separately protected secret destination, never overwrite the B3 TestA/TestB DPAPI vault. Do not place new password or a password hash in evidence. Read pool password policy/permissions first; don't change IAM to obtain missing rights.

## Preflight before any future authorized write

1. STS exact account, region, old/test stack identities; source commit/client/pool/profile mapping refreshed. Confirm this is the source identity, not either B3 user.
2. Confirm current Enabled/UserStatus, client revocation setting and pool password policy; avoid email/user attributes in public evidence.
3. Owner confirms profile and disruption via authorized Console. Record an approval reference/alias, not identity/secret text. Unknown impact or wrong target => STOP.
4. Verify selected caps/action list and secure new-credential handoff if B is approved. No use of exposed password, InitiateAuth/AdminInitiateAuth/RespondToAuthChallenge or old-token probes.
5. Preserve current metadata and evidence; do not snapshot raw authentication replies. No CloudFormation change set or code deployment.

## Execution and failure handling — only after explicit approval

Disable exact user; read Enabled state. Perform approved administrative global sign-out; record timestamp, API success/error code and request identifier without raw exceptions. If B approved, set the new secret under the selected policy/mode then perform the second approved global sign-out. Keep user disabled.

An uncertain timeout requires read-only metadata/audit inspection first; do not automatically retry writes. Some revocation results have no read-only state getter proving completion: mark PARTIAL/BLOCKED when the administrative result cannot be evidenced, not PASS. Do not escalate to deleting users/pool/client, changing APIs/IAM or disabling the whole legacy application.

No rollback to the exposed password. Re-enable is a separately approved access-restoration action, not an automatic rollback. Global sign-out is disruptive and existing sessions cannot be restored by undoing a flag.

## Token and containment caveat

Cognito global sign-out invalidates Cognito token use/refresh, but some other services that validate JWT signature/expiration can still accept a previously issued token until expiry. Managed-login session cookies are also not cleared by the admin call. [AWS global sign-out behavior](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_AdminUserGlobalSignOut.html).

Therefore do **not** label all access REVOKED from Enabled=false/API200 alone. Establish effective access/ID token lifetime and relevant issuance/config history, clock-skew/cache/session behavior before stating a containment cutoff. D2 observed validity fields1/1/30 with empty unit map; default units and historical configuration must be confirmed, and current settings alone don't prove the lifetime of every old token. Do not assume the legacy API authorizer consults revocation status on every request. [AWS revocation limitations](https://docs.aws.amazon.com/cognito/latest/developerguide/token-revocation.html).

Any emergency per-user API deny/authorizer/pool/client/config change to block residual JWTs requires its own approval and impact review; it is not silently included in D3-A/B. Do not test old passwords/tokens to prove rejection. Authentication testing of a new secret remains D3-C or another separate bounded approval.

## Acceptance evidence

- Administrative action responses and timestamps, exact target guard passed, Enabled=false read back; password-set acceptance only if B approved; no secret text/values or hashes.
- Cognito refresh/global revocation action result versus downstream JWT residual window recorded separately; UNKNOWN if unproven.
- Test users/pool, stack templates, IAM/API/Budget/SNS/data untouched. No logout/delete against unrelated identities.
- No conclusion of unauthorized access from absence of logs. A separate read-only incident review may inspect available event metadata/auth telemetry without changing logging/tier/billing; coverage/retention limits must be explicit.
- Owner checks other services for reuse privately if applicable; no assumption password was reused and no automatic broad rotation.
- Refresh secret scan/staged diff before any later Git approval. History cleanup is a separate Git operation **after** credential safety, never a replacement for revocation.

## Required approval text elements

State A-only or A+B; acknowledge this exact legacy-user exception; confirm target in AWS Console and disruption; choose B password mode/handoff if applicable; accept token residual-window limitations; approve explicit caps and STOP-on-uncertainty. Exclude enable/login, other users, pool/client/IAM changes, CloudFormation, deploy, cleanup, Git commit/push/history rewrite and notifications.

Official API references: [AdminDisableUser](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_AdminDisableUser.html), [AdminUserGlobalSignOut](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_AdminUserGlobalSignOut.html), [AdminSetUserPassword](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_AdminSetUserPassword.html). Sources checked22/10/2026. All actions here remain **NOT_EXECUTED**.
