# Latest hardened test approval

The current candidate, scope, source fingerprint and actual verification are in [aws-test-deployment-approval.md](aws-test-deployment-approval.md). It supersedes the earlier a9a40304 candidate. Technical preparation is authorized; execution/Budget/users/frontend/messages/deletion/push remain unapproved. The material below is historical context, not the current candidate ID or execution approval.

# AWS deployment review — MVP v1

**Latest status 2026-10-21 06:42 UTC:** real AWS inspection and an unexecuted isolated test CREATE change set are now complete. Read [the exact approval packet](aws-test-deployment-approval.md) before any execution. Existing `policy-assistant` was not updated; new candidate `policy-assistant-fcaj-test` awaits owner approval.

## Historical local preparation (before the AWS inspection below)

The original text below describes the earlier local-only stage; its statements that no AWS reads/change sets exist are superseded by the packet above.

Current source changes have not been pushed or deployed. The complete checklist, state recovery model, host configuration, SNS/email behavior and two-phase legacy DynamoDB index upgrade are maintained in [operations.md](operations.md).

Before approval, inspect the current SAM template and local acceptance results, rotate previously exposed credentials, confirm account/region and budget inputs, and preserve existing tables/buckets. No cleanup/deletion, account changes or email notifications were performed here.

New resources to review include private frontend hosting S3/CloudFront/OAC/security headers, a pending-recovery Lambda/schedule, SNS topic/optional email recipient, alarms and two document-table indexes. Existing document versioning, IAM changes, lifecycle, Cognito admin-only onboarding/password policy and all CORS origins also require review.

Live acceptance must cover native Cognito login/challenges/refresh/logout, rejected tokens, two-user library/API isolation, immutable PDF integrity, scheduled recovery, failed/new-attempt behavior, SQS/DLQ, CloudFront security headers and S3/API CORS. Local tests and browser screenshots are not substitutes for these live checks.

## Concrete local IaC review, 2026-10-21

The reviewable diff is [evidence/iac-review.patch](evidence/iac-review.patch), comparing current local template to baseline 80c4eef; it includes existing local work and this pass. This is **not** a CloudFormation change set and does not prove deployed drift/replacement behavior. No AWS inventory/change-set call or write was executed. Review the actual account state before approving a deployment.

| Resource area | Current intended change | Operational/cost effect |
|---|---|---|
| Existing document API/worker | Owner/session/version/attempt handling; POST policy; per-record SQS response | Coordinate code, CORS and mapping; no new service for these fixes |
| SQS mapping/queues | ReportBatchItemFailures, explicit SQS-managed SSE, 180 s visibility, 3 receives/DLQ | Backlog/partial errors need queue metrics, not Errors alone |
| Existing buckets | TLS-only deny, BPA/encryption/versioning, POST/GET document CORS | Review lifecycle and all retained versions; do not delete data |
| Frontend delivery | Private S3/OAC/CloudFront/security headers and public config | Cache rollout/publication needs authorization |
| Metadata/GSI/recovery | ByStatus/ByOwner, bounded scheduled recovery every 2 minutes | Legacy one-GSI-per-update constraint; fixed idle invocation cost |
| Cognito | Admin-only onboarding/password policy, explicit LITE tier | Verify existing tier/features before applying; do not silently downgrade a live feature requirement |
| Operations | Three 30-day log groups, dashboard queue/worker widgets, five alarms, optional SNS email | Gross modeled fixed monitoring cost; recipient action required |

Gross small-load planning estimate: **6.6306 USD/month**, before allowances/credits/tax; 10× scenario **34.7081 USD/month**. Full quantities and official 2026-10-21 sources: [cost-estimate.md](cost-estimate.md). This is total intended-system planning cost, **not an incremental delta from a verified deployed baseline**. Real current bill/deployed resources remain unknown. No VPC/NAT/AI addition is planned. Calculator estimate URL and measured load are absent.

## Authorized rollout and rollback sequence

1. Owner confirms account/region, credential rotation, retained data inventory/backups, optional recipient and budget. Save prior deployed code/template/frontend/config separately; a Git baseline alone may not match deployment.
2. Prepare `sam build`, then an **authorized** `sam deploy --guided --stack-name policy-assistant --region ap-southeast-1 --no-execute-changeset`. It uploads artifacts/creates a change set, so do not run it merely as a local preview. Inspect actual Add/Modify/Remove/Replacement and IAM changes before approval to execute.
3. For a live worker upgrade from whole-invocation failures, pause its SQS event-source mapping during the reviewed maintenance window before updating worker code and ReportBatchItemFailures together. A new handler returning partial failures under an old mapping could otherwise acknowledge failed work. Preserve backlog; pause is not purge. Check mapping configuration before re-enabling. Schedule recovery can create duplicate pending deliveries during maintenance; existing attempt checks protect state, and queue storage/age still grows.
4. For legacy metadata without indexes, apply false → wait ByStatus ACTIVE → reviewed true → wait ByOwner ACTIVE. Never remove an existing ByOwner index or replace the table for convenience. Delay library acceptance until the final phase.
5. Roll out API signed POST, document S3 POST CORS and four frontend files together; invalidate named assets. Drain/reload cached old PUT clients. Preserve old frontend assets and their compatible backend/CORS policy for a coherent rollback.
6. Run the live matrix and record actual results. A failing acceptance stops shared demo rollout. Restore the previously reviewed compatible function/mapping/frontend configuration if needed, with mapping paused while changing response protocol. Resume mapping only after inspection; do not ACK/purge backlog to make metrics look healthy.
7. Rollback does not delete new indexes, buckets, tables, versions or documents. Do not roll back data by rewriting owners or state en masse. Inspect CloudFormation rollback events and retained resources; operator review is needed if GSI creation is still in progress. Data migration or resource deletion needs separate explicit approval.

## Cleanup checklist, no deletion performed

Inventory the actual stack and retained tables/buckets/versions/backups/log groups/CloudFront/SNS, export required evidence with owner permission, identify data owners and obtain deletion scope. Review `DeletionPolicy` and `UpdateReplacePolicy`. A future `sam delete` may leave retained/nonempty resources; never assume it erases all data or costs. Record remaining resources and check Billing after approved teardown. Do not shorten the existing version lifecycle without consent.
