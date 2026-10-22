# AWS test deployment — owner approval required

Reviewed at 2026-10-21T06:42:31.110673+00:00. **NOT EXECUTED.**

## Exact candidate

- Account: STS verified, ending **0098**; exact ID is checked privately before any execution.
- Region: **ap-southeast-1**. CLI default is us-west-2; explicit region is mandatory.
- New stack: **policy-assistant-fcaj-test**. Existing policy-assistant is outside write scope.
- Change set: **fcaj-review-20261021-064014-a9a40304**, type CREATE, status **CREATE_COMPLETE / AVAILABLE**.
- Candidate fingerprint (template.yaml + app.py): `a9a403047e4b6d0ab52696a55251c843d04b4aca85492eea6f39620dcea543d3`. Per-file fingerprint: [evidence/aws-review-source-fingerprint.json](evidence/aws-review-source-fingerprint.json).
- Parameters: TableNamePrefix=policy-assistant-fcaj-test-, EnableOwnerIndex=true, LocalFrontendOrigin=http://localhost:8080, AlertEmail empty.
- **42 Add, 0 Modify, 0 Remove, 0 Replace.** No import or adoption of existing resources. This is the real AWS change set, not a guessed local diff. Its successful preparation does not prove all execution permissions or service quotas.
- Earlier `fcaj-review-20261021-063231-1f5cb969` is **superseded and must not be executed**. It retained the SAM-generated broad SQS policy; the current candidate removes that policy. No candidate has been executed or deleted.

## Existing resources: read-only observations

At 2026-10-21 06:27 UTC, existing policy-assistant was UPDATE_COMPLETE (last update 2026-10-19 11:10:29 UTC), no Environment tag and no termination protection. Re-read after candidate preparation showed the same update timestamp/status. Its two ACTIVE DynamoDB tables have approximate counts of 3 policies/1 document record and no metadata GSI. Its private document bucket contains objects and versioning is disabled. Existing SQS queue visibility is 30 seconds; worker mapping enabled, BatchSize 1, no partial-response types. Cognito is ESSENTIALS, MFA OFF, self-registration not administratively disabled, estimated one user. Two existing alarms reported OK; that does not prove release correctness. No item contents, user identities/passwords, stored PDFs or message bodies were exported.

This observed system is not equivalent to current local source. To avoid modifying unknown-use resources or downgrading its identity tier, prepare a completely separate test stack. [Read-only evidence](evidence/aws-predeployment-readonly.json). Lambda account concurrency is 10 with two existing functions; CloudFront list API is readable and currently returns no distribution. No Bedrock/model dependency exists. Availability of every create action remains unverified until approved execution.

## Code/IaC diff and data impact

Current application baseline is 80c4eef plus preserved local changes. The complete [IaC diff](evidence/iac-review.patch) includes current template changes; no general Git patch exposing deleted historical password literals is exported. Code summary: owner-bound session/library; immutable version and attempt; bounded signed POST; validation and safe error logs; retry/idempotency/partial batch; scheduled pending recovery; native frontend authentication/polling/hash download; layered tests and explicit live-test tools. Source hashes include current frontend files and runtime requirements.

This pass adds a backwards-compatible TableNamePrefix (legacy default PolicyAssistant), Retain/UpdateReplacePolicy Retain for policy table, metadata and document bucket, and an explicit worker role so SAM cannot add wildcard SQS access. Test tables become `policy-assistant-fcaj-test-Policies` and `policy-assistant-fcaj-test-DocumentMetadata`; collision checks found neither before plan creation. Existing table names remain unchanged under the legacy default, but **this approval is not permission to update the old stack**. New test table creation can add both GSIs together; no legacy two-step upgrade is needed here.

No live application data is migrated, overwritten, re-owned, deleted or imported. After approval only new test synthetic records/files/users are written. Retained resources can incur costs even after rollback/stack deletion. Frontend/code publication targets only test resources.

## IAM review

Three new Lambda execution roles; only lambda.amazonaws.com assumes them. API role can GetItem/Scan the new policy table, Get/Put/Update new metadata, Query its ByOwner index, sign/access uploads/* in the new document bucket, and send to the new queue. Worker has Get/Update new metadata, GetObjectVersion on that bucket prefix and Receive/Delete/GetQueueAttributes on the **one new queue**. Recovery has Query ByStatus, conditional metadata UpdateItem and SendMessage to that queue. Nine generated Lambda resource permissions cover API and scheduled invocation (SQS uses the event-source mapping and worker role), as represented in the processed template; service principals/source restrictions must remain as reviewed.

Removed `AWSLambdaSQSQueueExecutionRole`; processed current plan contains no such managed policy. Three roles retain AWSLambdaBasicExecutionRole for log creation/stream writes with Resource `*`; this remaining managed-logging permission is disclosed, not claimed as perfect least privilege. It does not grant document reads, SQS data access or role administration. See [detailed processed IAM evidence](evidence/aws-test-iam-review.json) and [official logging policy](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSLambdaBasicExecutionRole.html). CloudFormation execution needs CAPABILITY_IAM and caller/service execution permissions; change-set creation alone is not proof that CreateRole/PassRole/all service creates will succeed.

## Itemized cost scope

One full intended test environment under explicit assumed load, before allowances/credits/tax:

| Service group | USD/month gross |
|---|---:|
| Lambda API/worker/recovery | 0.072670 |
| HTTP API | 0.125000 |
| DynamoDB reads/writes/storage/PITR | 0.196625 |
| S3 stored versions/frontend and requests | 0.633250 |
| SQS including polling/retries | 0.120000 |
| SNS publish/email planning reserve | 0.002050 |
| CloudWatch 1 GB ingest/1 GB stock, 5 alarms, 1 dashboard | 4.230000 |
| Cognito Lite 100 MAU | 0.550000 |
| CloudFront HTTPS/5 GB Europe edge egress | 0.449000 |
| Direct Singapore internet egress 2.1 GB | 0.252000 |
| **Total** | **6.630595** |

Assumptions: 100 MAU, 100,000 API calls/month, 500 uploads of 2 MiB, 1,000 downloads, 25 GB document-version stock, 300,000 SQS requests; see [full model and official 2026-10-21 rate sources](cost-estimate.md). Model includes an SNS reserve but AlertEmail is empty, so this approval sends no email. No model/AI, VPC/NAT/EC2/RDS is provisioned. The 10x planning stress scenario is 34.7081 USD/month, not a guaranteed maximum.

**Excluded:** existing policy-assistant costs and any unrelated account usage; tax/currency/support/domain/SMS/advanced features; traffic or duration above assumptions; extra metric retrieval; any approved later resources. Existing stack still has its own dashboard/two alarms (paid-rate baseline about 3.20 USD/month before allowances, plus its other usage), so 6.63 is **not the whole account bill**. No Billing/Cost Explorer consumption or Free Tier eligibility was verified. No Calculator estimate/share URL exists. Budget USD 10 can be an owner planning target, not a hard cap; no Budget/SNS notification setup is included.

Preparation uploaded two candidate code artifacts of about 15.97 MiB each into separate new prefixes of the existing packaging bucket, plus created unexecuted change sets/REVIEW_IN_PROGRESS placeholder. Approximate combined Standard artifact stock cost is under 0.001 USD/month at Singapore list rate, plus tiny request charges, outside the base model. No new packaging bucket/bootstrap stack was created. Artifact cleanup must target only these prefixes after approval, not the shared bucket.

## Proposed execution and rollback

1. Approve **this named current candidate** and the bounded [real test plan](aws-live-test-plan.md). Recheck exact account/region/stack/candidate/fingerprint immediately before execution; changes require a new review.
2. Execute CREATE, monitor events without printing secret values. Stop on permission/quota/service failure or unexpected resource/data action. Do not broaden IAM or touch the existing stack to bypass a failure. CloudFormation may roll back newly provisioned test infrastructure on a failed CREATE; Retain protects the two new tables/document bucket. That rollback is limited to this new test environment.
3. On CREATE_COMPLETE, verify test tags, functions/GSIs/storage/mapping. Seed new synthetic policies, provision two invitation-suppressed test users, export public config and publish exactly four assets to the new frontend bucket. No existing user password or production data is changed.
4. Execute A01–A12 in the test plan: Cognito/two-user isolation, policy query, valid/oversized/tampered/invalid-byte upload, exact-version hash, async/duplicate handling, direct real mixed-batch result, actual SQS retry/DLQ, safe logs and actual metrics/alarm states. No mock/skip PASS. No temporary mapping/IAM change is included. Typical queue wait can be about 15 minutes. No application E2E has been run before approval.
5. On failed acceptance, stop publishing/declaring readiness and preserve evidence/test state. Restore only a reviewed compatible test artifact/config if appropriate; no table/state rewriting or blind queue purge. Existing stack needs no rollback because it was not updated.
6. After successful acceptance, update EN/VI Workshop and save actual public test endpoint and redacted results/screenshots. Rehearse [the 5–7 minute script](demo-script.md); student creates their own official-icon architecture with [the worksheet](architecture-self-draw.md).

## Cleanup — separate owner decision

Before deletion, approve an explicit inventory: test CloudFront/OAC/frontend bucket, API/Cognito test users/functions/roles/logs/alarm/dashboard/SNS/schedule/SQS/DLQ, retained two DynamoDB tables/document bucket/versions/PITR, and only the two review artifact prefixes/unused change sets. Preserve required evidence first. `sam delete` alone cannot be assumed to delete Retain data or nonempty buckets; version/delete-marker cleanup is destructive and is **not authorized now**. Removing infrastructure can remove synthetic users/messages, so cleanup needs scope approval. No change set or resource/data was deleted in this preparation.

## Verification and open gates

Actual local checks for this candidate: 123 unit tests passed; selected fatal Python lint passed; SAM validate --lint and SAM build passed. Existing frontend/browser evidence remains local evidence and is not AWS proof. AWS read-only/plan actions are verified, but **application deployment and A01–A12 remain NOT_RUN pending approval**. No credentials/access blocker was observed for read/packaging/change-set creation. Full execute/IAM/service-creation permissions, CloudFront provisioning and test outcomes are not yet proven. Account concurrency 10 requires low-volume operation. Student editable architecture, real attendance/publication evidence and any real account billing verification remain personal/external gates.

## Exact AWS resource actions

| Logical resource | Type | Change |
|---|---|---|
| AlertTopic | AWS::SNS::Topic | Add |
| DocumentDLQAlarm | AWS::CloudWatch::Alarm | Add |
| DocumentMetadata | AWS::DynamoDB::Table | Add |
| DocumentQueueAgeAlarm | AWS::CloudWatch::Alarm | Add |
| DocumentRecoveryLogs | AWS::Logs::LogGroup | Add |
| DocumentRecoveryRecoverPendingPermission | AWS::Lambda::Permission | Add |
| DocumentRecoveryRecoverPending | AWS::Events::Rule | Add |
| DocumentRecoveryRole | AWS::IAM::Role | Add |
| DocumentRecovery | AWS::Lambda::Function | Add |
| DocumentsBucketTlsPolicy | AWS::S3::BucketPolicy | Add |
| FrontendAccessControl | AWS::CloudFront::OriginAccessControl | Add |
| FrontendBucketPolicy | AWS::S3::BucketPolicy | Add |
| FrontendBucket | AWS::S3::Bucket | Add |
| FrontendDistribution | AWS::CloudFront::Distribution | Add |
| FrontendHeaders | AWS::CloudFront::ResponseHeadersPolicy | Add |
| PoliciesTable | AWS::DynamoDB::Table | Add |
| PolicyAssistantApiProdStage | AWS::ApiGatewayV2::Stage | Add |
| PolicyAssistantApi | AWS::ApiGatewayV2::Api | Add |
| PolicyAssistantDashboard | AWS::CloudWatch::Dashboard | Add |
| PolicyAssistantDocumentDLQ | AWS::SQS::Queue | Add |
| PolicyAssistantDocumentQueue | AWS::SQS::Queue | Add |
| PolicyAssistantDocumentsBucket | AWS::S3::Bucket | Add |
| PolicyAssistantDurationAlarm | AWS::CloudWatch::Alarm | Add |
| PolicyAssistantErrorAlarm | AWS::CloudWatch::Alarm | Add |
| PolicyAssistantFunctionDocumentDownloadPermission | AWS::Lambda::Permission | Add |
| PolicyAssistantFunctionDocumentStatusPermission | AWS::Lambda::Permission | Add |
| PolicyAssistantFunctionGetPolicyByIdPermission | AWS::Lambda::Permission | Add |
| PolicyAssistantFunctionHealthCheckPermission | AWS::Lambda::Permission | Add |
| PolicyAssistantFunctionListDocumentsPermission | AWS::Lambda::Permission | Add |
| PolicyAssistantFunctionRole | AWS::IAM::Role | Add |
| PolicyAssistantFunctionSearchPoliciesPermission | AWS::Lambda::Permission | Add |
| PolicyAssistantFunctionSubmitDocumentPermission | AWS::Lambda::Permission | Add |
| PolicyAssistantFunctionUploadSessionPermission | AWS::Lambda::Permission | Add |
| PolicyAssistantFunction | AWS::Lambda::Function | Add |
| PolicyAssistantLogGroup | AWS::Logs::LogGroup | Add |
| PolicyAssistantUserPoolClient | AWS::Cognito::UserPoolClient | Add |
| PolicyAssistantUserPool | AWS::Cognito::UserPool | Add |
| PolicyAssistantWorkerDocumentQueueEvent | AWS::Lambda::EventSourceMapping | Add |
| PolicyAssistantWorkerLogGroup | AWS::Logs::LogGroup | Add |
| PolicyAssistantWorkerRole | AWS::IAM::Role | Add |
| PolicyAssistantWorker | AWS::Lambda::Function | Add |
| RecoveryErrorAlarm | AWS::CloudWatch::Alarm | Add |

Website preparation verification: Hugo v0.167.0 built 128 EN / 127 VI outputs; 129 generated HTML pages and 12,270 internal references have zero failed targets. Three existing theme deprecation warnings remain. EN/VI deployment status is explicitly pending, not AWS integration PASS. Earlier handover ZIPs predate this candidate; use the exact named change set/fingerprints rather than treating an older ZIP as approval evidence.
