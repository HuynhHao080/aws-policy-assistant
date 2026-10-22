# D3-A1 — Read-only legacy identity operational dependency assessment

**D3-A: BLOCKED_PENDING_OWNER_OPERATIONAL_CONFIRMATION. NO-GO containment execution.**

Assessment date: 2026-10-22. AWS account …0098, region ap-southeast-1. Exact pool ap-southeast-1_zzeu6TjQs belongs to legacy stack policy-assistant. Identity is represented only as EXPOSED_LEGACY_IDENTITY_1; username/sub are not published. Current sub was checked against the private D3-A binding. No old password was used. TestA/TestB and their pool were not queried or modified in this assessment.

Metadata review: 08:21:30–08:21:45 UTC. Activity snapshot: 08:24:29 UTC; log follow-up completed 08:25:23 UTC. These are bounded snapshots, not continuous monitoring. Source working-tree/HEAD review covers the application and worklog repositories. Prior D2 exposure evidence is retained; it is not replaced by this review.

## Dependency findings

| Flow / component | Evidence | Classification | Limit |
|---|---|---|---|
| Four legacy auth scripts: get_token.py, verify_e2e.py, verify_jwt.py, verify_search.py | HEAD 80c4eef references the same username and client. Scripts invoke Cognito authentication; previous D2 analysis establishes one shared credential candidate. Working tree no longer contains those exact identity/client literals in these scripts. | HISTORICAL USE / static dependency confirmed | Source alone does not establish execution frequency or a current operational requirement. Interactive configuration can still select the same identity. |
| Legacy Cognito activity | 13 InitiateAuth events matched exact sub in the full CloudTrail event, on 2026-10-19, 15:38:43–18:06:53 UTC+7. No errorCode was recorded for these events. AdminCreateUser and AdminSetUserPassword also matched exact identity on that date. | HISTORICAL USE | No-error InitiateAuth is not by itself proof of completed sign-in, the exact password used, authorized access, or continuing dependency. |
| Legacy API JWT authorizer | Current issuer matches approved legacy pool and audience includes legacy App Client. | Pool/client dependency CONFIRMED; exact-user requirement UNKNOWN | Authorizer trusts the pool/client, not this single username. Protected application calls could still depend on credentials selected outside the repository. |
| Two legacy Lambda environments | Four environment key names inspected per function; no exact username/sub/pool/client reference found in values. API Active, Worker Active; worker has one event source mapping. | NO DEPENDENCY FOUND in inspected environment configuration | Deployed Lambda ZIP code was not downloaded/inspected; external secrets or configuration resolution are not excluded. |
| EventBridge automation | No default-bus rule targets either inspected unqualified legacy function ARN. | NO DEPENDENCY FOUND in this target lookup | Other event buses, aliases/versions, Scheduler, other services, other accounts/regions and external schedulers were not exhaustively enumerated. |
| Application CI and worklog Pages workflow | Working tree and HEAD: neither calls the four auth scripts nor contains the checked direct Cognito auth commands. App workflow has no detected SAM/CloudFormation deployment command; worklog workflow publishes Pages. | NO DEPENDENCY FOUND in inspected workflow definitions | Workflow execution history, GitHub secrets, external reusable automation and local scheduled jobs were not inspected. Static detection is not runtime proof. |
| Operator demos, notebooks, CLI sessions, external applications | No comprehensive inventory/owner confirmation available. | UNKNOWN | These can use credentials without literal references in either repository. |

No **CONFIRMED ACTIVE DEPENDENCY** requiring this exact identity was established. This does not establish that none exists. Priority remains high because public credential exposure was confirmed in D2 and identity remains Enabled/CONFIRMED.

## CloudTrail coverage and recent activity

LookupEvents scanned all 109 returned Cognito management events in three pages, without truncation, for ap-southeast-1 from 2026-07-24 08:24:29 UTC through 2026-10-22 08:24:29 UTC. Returned events range from October 7 to October 22. Exact identity matching was refined to search the entire event JSON in memory, including fields outside requestParameters/responseElements; raw events and identity values were not exported. Pool/client-only events are explicitly distinguished in evidence.

The latest observed exact-identity authentication request was **2026-10-19 18:06:53 UTC+7**, event ID `3a0fd360-cc5d-4aca-9bfd-7fdd04f17225`. No later exact-identity authentication event was found in this snapshot. October 22 AdminGetUser events reflect metadata review, not a user login or operational dependency. ListGroups and pool-level metadata calls cannot be attributed to this user.

No trail was returned by DescribeTrails(includeShadowTrails=false), and no event data store was returned by ListEventDataStores in the queried region. This does not assert absence of shadow/organization trails or stores elsewhere. No Lake query was started and no new logging was enabled.

CloudTrail Event History is regional, limited to 90 days and management events. Cognito masks private fields and records UserSub for user-specific requests; usernames are not a reliable event join key. Neither missing events nor an error-free authentication request establishes whether the exposed password is valid now. [AWS Event History](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events.html), [AWS Cognito CloudTrail logging](https://docs.aws.amazon.com/cognito/latest/developerguide/logging-using-cloudtrail.html).

## CloudWatch and Cognito logging limits

Both existing legacy Lambda log groups were inspected using exact username/sub filters, with pagination exhausted within the ten-page bound per filter. No matching message was found. API log retention is 30 days; worker retention is indefinite. Generic Lambda activity does not establish who invoked the application. Raw messages were not exported.

Legacy API stage Prod has no access-log destination configured. Cognito GetLogDeliveryConfiguration returns an empty LogConfigurations list. AdminListUserAuthEvents returns UserPoolAddOnNotEnabledException: specialized user auth history is unavailable with the current threat-protection configuration. Nothing was enabled or changed to expand coverage. Lack of an exact marker in these logs does not prove inactivity; the application may omit identity claims from logs intentionally.

## Known, unknown and containment risk

- Public exposure: CONFIRMED by D2; not re-probed publicly in D3-A1.
- Current identity Enabled=true, UserStatus=CONFIRMED: VERIFIED.
- Historical exact-identity auth requests: VERIFIED, with the qualification above.
- Current required operational dependency: UNKNOWN.
- Exposed password current validity, rotation/revocation, and unauthorized access: UNKNOWN. Provisioning-time password setting is not evidence of remediation after exposure.
- Disabling now could interrupt a still-used manual demo, smoke test, local automation or external application. Repository/telemetry inspection cannot replace owner confirmation.
- Remaining enabled permits a potentially exposed credential to remain a security concern. Do not assume the old password works, and do not test it.

## Owner confirmation needed before D3-A

The owner must identify whether any required legacy demo, script, scheduled task, notebook, client application or shared operator workflow still uses this identity, including configurations outside these two repositories. Confirm whether existing sessions may be interrupted and whether any unresolved operational use must first migrate to another approved identity/authentication method. No replacement identity is created under D3-A1.

If a required dependency exists: document its operator and migration/validation plan before containment; request separate permission for any replacement or configuration changes. If none is required: obtain explicit owner confirmation accepting interruption of this identity, then refresh the narrow D3-A account/pool/identity/IAM preflight before the two conditionally approved containment calls. This report itself is not that confirmation.

**GO to present these findings for owner operational review. NO-GO to resume D3-A writes at present.** Do not run AdminDisableUser or AdminUserGlobalSignOut until the missing confirmation is explicit. Offline JWT validation can continue until token expiry even after Cognito revocation; do not claim all tokens or unauthorized access have been eliminated.

## Evidence and execution boundary

- [Static/configuration evidence](evidence/d3a1-dependency-metadata.json)
- [CloudTrail and log evidence](evidence/d3a1-activity-review.json)
- [Decision summary](evidence/d3a1-dependency-summary.json)
- [Prior D3-A result](d3a-containment-result.md)

AWS writes: **0**. Authentication calls: **0**. AdminDisableUser / AdminUserGlobalSignOut / password reset: **NOT_EXECUTED**. IAM/logging changes, deployment, cleanup, Git stage/commit/push/history rewrite: **NOT_EXECUTED**. Only local assessment documents/evidence were added or linked. No application tests were rerun because no runtime code changed.
