# AWS test deployment approval — read-only VERIFIED, NOT EXECUTED

## Trạng thái hiện hành — B4 API/SDK E2E hoàn tất

**19 PASS, 0 FAIL/BLOCKED, 1 NOT_RUN (browser thực tế)**. Authentication, hai chiều ownership, PDF/hash/10 MiB/MIME, worker và retry/DLQ thật đã kiểm chứng ngày 21/10/2026 16:47–16:57 UTC. Một poison, ba lần nhận ở queue chính (hai lần retry), DLQ còn 1; follow-up 16:59 UTC ghi DLQ/queue-age ALARM, ba alarms còn lại OK. Không reset/xóa để ép OK. [Báo cáo B4](aws-test-e2e-b4-result.md), [evidence](evidence/approval-b4-e2e.json).

**DỪNG: không tự cleanup, sửa/deploy hoặc commit/push. Browser E2E và email delivery chưa được chứng minh.** Các trạng thái AWS NOT_RUN ở lịch sử dưới đây đã được thay thế theo từng ca bởi báo cáo B4; không thay thế bằng blanket PASS.

## Trạng thái hiện hành — B3 hoàn thành

**B3: CREATED_VERIFIED**, hai users tổng hợp TestA/TestB ở pool test, Enabled / CONFIRMED, `sub` khác nhau, email_verified=false; invitation SUPPRESS. Credentials DPAPI current-user + NTFS ACL giới hạn, Git-ignored; không xuất passwords. [Báo cáo B3](aws-test-cognito-b3-result.md), [evidence](evidence/approval-b3-users.json).

**DỪNG: B4 login/token/API/upload/retry/DLQ chưa được duyệt và NOT_RUN.** Không tạo thêm users hoặc cleanup. Các đoạn ghi users chưa tạo trong lịch sử bên dưới đã được thay thế bởi trạng thái B3 này.

## Trạng thái hiện hành — B2 hoàn thành

**B2: PUBLISHED_STATIC_VERIFIED**, 21/10/2026 khoảng 16:28–16:29 UTC. Đã publish đúng bốn assets test, SHA-256 đọc lại S3/CloudFront khớp; invalidation Completed, HTTP 301 sang HTTPS, static HTTPS 200. Không overwrite/delete. [Báo cáo B2 và checksum](aws-test-frontend-b2-result.md), [evidence](evidence/approval-b2-result.json).

**DỪNG: B3 users, B4 AWS E2E và cleanup chưa được duyệt.** Các đoạn nói frontend chưa publish ở lịch sử bên dưới đã được thay thế bởi trạng thái B2 này. Không tạo users, gọi API nghiệp vụ, gửi SQS, upload DocumentsBucket hoặc commit/push.

## Trạng thái hiện hành — B1 đã hoàn thành

**B1: CREATED_VERIFIED**, stack test CREATE_COMPLETE ngày 21/10/2026 khoảng 09:42:51 UTC; execute đúng một lần candidate `fcaj-review-20261021-072124-24ba855e`, 45/45 tài nguyên CREATE_COMPLETE, không lỗi/rollback. [Báo cáo B1 và danh sách đầy đủ](aws-test-deployment-b1-result.md), [execution evidence](evidence/approval-b1-execution.json), [service read-only checks](evidence/approval-b1-service-readiness.json).

**DỪNG: B2 frontend, B3 users, B4 E2E vẫn chưa được duyệt; cleanup riêng.** Các trạng thái NOT_EXECUTED/AVAILABLE/chưa duyệt B1 ở phần dưới là lịch sử trước B1, không phải trạng thái hiện tại. Không tạo users, upload dữ liệu, gửi message, chạy E2E hoặc commit/push trong B1.

Cập nhật preflight 21/10/2026 09:32–09:33 UTC: AWS read-only thành công; candidate 45 Add AVAILABLE, Budget 20 USD/ba alerts không Actions. [Approval B mới nhất](aws-test-deployment-approval-b.md) và [evidence](evidence/approval-b-final-preflight-readonly.json). Email legacy/0-of-1 vẫn theo xác nhận Console trước, delivery chưa xác minh. Không ghi AWS, không deploy/E2E.

## Cập nhật hiện hành — Console do người dùng xác nhận

**Cấu hình Budget: VERIFIED.** Người dùng xác nhận COST / MONTHLY / 20 USD, Healthy, bắt đầu 2026-10-01; Actual 5,42 USD (27,11%), Forecast 8,54 USD (42,70%). Đúng ba alerts: ACTUAL 80%, ACTUAL 100%, FORECASTED 100%, đều Not exceeded; không Budget Actions. Metric UnblendedCost, loại Credit/Refund và phạm vi toàn account đã được xác minh trong snapshot API trước đó.

**Recipient: Active (legacy), theo Console người dùng kiểm tra. Email verification: 0/1 verified; email delivery: DELIVERY_NOT_VERIFIED.** Không đánh đồng trạng thái legacy với email đã xác minh hoặc đã nhận thành công. Không gửi verification, không sửa Budget/notification. Thời điểm quan sát Console không được cung cấp; evidence chỉ ghi thời điểm tiếp nhận. [Evidence mới](evidence/budget-20usd-user-console-confirmation.json) bổ sung snapshot API lịch sử, không thay thế nguồn gốc của snapshot đó. Sáu Budget cũ khớp fingerprint ở lần kiểm tra trước; không kiểm tra lại AWS trong cập nhật local này.

Hồ sơ [Approval B](aws-test-deployment-approval-b.md) đã chuẩn bị, **chưa được phê duyệt**. CloudFormation deployment: NOT_EXECUTED. AWS E2E: NOT_RUN. Các trạng thái PARTIAL/unconfirmed bên dưới mô tả thời điểm API lịch sử trước xác nhận Console này.

## Budget owner-created — latest read-only verification

Budget `policy-assistant-account-monthly` now exists: COST/MONTHLY/fixed USD20/UnblendedCost, Credit/Refund excluded, standalone exact account …0098, all services/regions, no Budget Actions. CloudTrail successful CreateBudget at **2026-10-21 09:11:39 UTC** explicitly records the three PERCENTAGE alerts (ACTUAL 80, ACTUAL 100, FORECASTED 100). Current reads at 09:16 UTC and typed subscriber lookups agree. Seven Budgets now exist; six prior configuration fingerprints and the USD5 notification baseline match. No agent AWS writes occurred.

One common email recipient is CONFIGURED; Budgets API does not expose its verification status and Contacts returned no matching record. **SUBSCRIPTION_CONFIRMATION_UNVERIFIED / DELIVERY_NOT_VERIFIED**, not a conclusion that the recipient is inactive. Owner should inspect Active/Active (legacy) privately in AWS before relying on delivery. Overall Budget operational status PARTIAL, configuration VERIFIED. [Current Budget report](budget-20usd-verification.md).

Candidate read at **09:18:37 UTC**: same exact test candidate AVAILABLE, 45 Add, no replacement, source hash unchanged. **Ready to present separate deployment Approval B**, with recipient verification check pending; no application write authority is inferred. CloudFormation deployment NOT_EXECUTED; AWS E2E NOT_RUN. Do not recreate Budget or repair notifications under this read-only request. [Budget evidence](evidence/budget-20usd-created-readonly-verification.json), [CloudTrail evidence](evidence/budget-20usd-cloudtrail-readonly.json), [candidate evidence](evidence/aws-candidate-after-budget-readonly.json). Older pending-recipient/preparation statements below are historical.

## Approval A received — Budget only, recipient gate still blocked

Owner conditionally authorized creation of exactly one USD20 account-wide Budget with the three reviewed notifications, **only after explicit private recipient confirmation in AWS Console**. No CloudFormation execution/E2E authorization is granted. Read-only preflight at 2026-10-21 08:56:35–08:56:38 UTC verified account, available name, and unchanged six Budget configurations including the USD5 notification baseline. IAM simulation allowed relevant Budget actions; no writes were used to test permissions.

**Current status: BLOCKED_PENDING_RECIPIENT. Budget creation: NOT_EXECUTED. CloudFormation deployment: NOT_EXECUTED. AWS E2E: NOT_RUN. Existing Budgets: UNCHANGED.** The official AWS Sign-In tab was handed to the owner; no recipient has been observed or confirmed, and no email address was queried/exported. See [current Budget approval state](budget-20usd-approval.md) and [preflight evidence](evidence/budget-20usd-approval-a-preflight.json). Older statements below saying no Budget approval are superseded only by this conditional Budget authorization; application write restrictions are unchanged.

## Budget preparation only — no execution approval

2026-10-21: [Budget 20 USD approval packet](budget-20usd-approval.md) is **PREPARED_NOT_CREATED**, recipient **PENDING_USER_CONFIRMATION**. Fresh Budget read-only check verified exact account …0098 and available target name among six existing Budgets; configuration fingerprints preserve a comparison baseline. Offline Budget/Notification shapes and thresholds passed, but private account binding, recipient/date confirmation and explicit owner approval remain pending. No server dry-run or create permission test was attempted.

**Budget creation: NOT_EXECUTED. CloudFormation deployment: NOT_EXECUTED.** No changes to existing Budgets, IAM/Billing settings, allocation tags, application resources or credentials; no user/message/cleanup/commit/push. Application change-set verification below is previously recorded evidence, not a new deployment authorization. Do not transition automatically from Budget preparation to deployment/E2E.

## Latest Budget amount decision — October actual/forecast review

Signed read-only CE/Budgets queries at 2026-10-21 08:34:26–08:34:33 UTC verified accrued October 1–20 **5.4222749168 USD** and October 21–31 forecast **3.1167914980 USD**, exact account …0098, UnblendedCost excluding Credit/Refund. Both time periods have exclusive end dates and no overlap. Whole-month baseline is derived **8.5390664148 USD**; plus a full gross 30-day test model gives a **15.1696615113 USD planning envelope**, not an AWS prediction of deployment.

Current recommendation: new whole-account **20 USD/month**, ACTUAL >16 and >20, FORECASTED >20, replacing provisional 15 USD **only as a proposal**. Compare 10/15/20 and scope/limits in [baseline decision table](budget-baseline-2026-10.md). Existing USD5 and test-tag USD10 plans remain unchanged. All current-month costs are estimated, no stack-level attribution is proven, and newly incurred/late/API-query fees may be absent. No Budget creation/modification, activation or execution was performed. Technical candidate verification remains GO; all writes remain NO-GO pending separate owner approval and private recipient confirmation in AWS.

## Earlier cost-control review — 2026-10-21 08:22 UTC

User has withheld Budget and execution approval. Fresh read-only checks confirm correct candidate stack tags and AVAILABLE/45 Add; processed template matches the previously verified candidate. Billing returned no Environment/Project allocation keys. Public CloudFormation specification 268.0.0 supports tagging for 28 of 45 resources; 17 have no tag property. None of the 28 explicitly declare both keys. Stack propagation remains unverified, not proven to fail. No template or AWS resource was changed.

Current documentation supports CloudWatch dashboard Tags; earlier statements describing dashboards as inherently untaggable are corrected. Billing attribution is still unconfirmed. CloudFront supports distribution cost allocation; Retain does not exclude table/bucket charges from billing; shared artifact-prefix allocation cannot be isolated using bucket tags.

Choose between new account-wide USD15 monitoring (ACTUAL >12/>15; FORECASTED >15, provisional amount) and test-tag USD10 attribution (ACTUAL >8/>10; FORECASTED >10, prerequisites pending), or approve neither. Keep existing USD5 Budget unchanged. Recipient confirmation occurs only in authorized AWS, never in public reports/chat. See [exact options](budget-options-review.md), [main proposal](budget-test-proposal.md), [45-resource matrix](budget-tag-coverage.md) and [fresh read-only evidence](evidence/aws-budget-tag-coverage-readonly.json).

Recommendation: account-wide alerts first, test-tag attribution after declaration/propagation/activation and billing-line verification. Neither is a hard cap. Tag implementation/new candidate, Billing activation and application execution/E2E each require explicit separate authorization. Technical predeployment IAM/artifact verification remains GO for the existing candidate; cost-control writes and deployment remain NO-GO pending owner decisions.

Prepared 2026-10-21. The owner approved technical preparation/change-set creation only. **Deployment, Budget writes, frontend publication, user creation, SQS tests and deletion remain unapproved.**

## Current decision — 4G verification succeeded

**Technical predeployment verification: GO / VERIFIED. Execution: NO-GO until separate owner approval.** This section supersedes older connectivity blockers recorded below; those observations remain historical.

- Successful signed SDK verification window: **2026-10-21T08:07:43.948327+00:00 → 2026-10-21T08:08:59.475170+00:00**. Independent fresh processed audit: **2026-10-21T08:09:00.589889+00:00**.
- STS verified the exact expected account, masked **…0098**. Clients explicitly used **ap-southeast-1**; returned CloudFormation candidate/stack ARN account, region and stack name matched the private expected IDs.
- Candidate **fcaj-review-20261021-072124-24ba855e** remains **CREATE_COMPLETE / AVAILABLE**, **45 Add / 0 Modify / 0 Remove / 0 Replace**. No change set was executed.
- Fresh original template equals the local packaged template; fresh processed template equals the saved AWS candidate snapshot. Local template/app source hash still matches the candidate. Fresh processed IAM/SQS/S3/dependency/isolation audit passes all checks.
- Three explicit runtime roles have no managed policies and zero Allow Resource `*`; each log policy points only to its function's exact group. DLQ byQueue accepts only the test main queue. Both tables, document bucket and its HTTPS Deny policy have Retain on deletion/replacement. Scoped stream/object/API wildcards and TLS Deny wildcards are unchanged and disclosed below.
- Authenticated S3 GetObject retrieved the shared **16,746,794-byte** ZIP; SHA-256 **8ef709aa27ab22094b83071591f9cce1b546f78aebc3b5fd00b1ec257ab6d591**. All three processed Lambda Code bindings point to that exact reviewed artifact. It was fetched once and all **2,199 member SHA-256 digests** matched each of DocumentRecovery, PolicyAssistantWorker and PolicyAssistantFunction build directories independently. This is content verification, not ETag or mock evidence.
- Existing `policy-assistant` read-only status: **UPDATE_COMPLETE**, last updated **2026-10-19 11:10:29.038 UTC**, unchanged from earlier review. This session made no AWS writes; shared account/quota/billing still apply.
- Runtime application E2E, effective deployed IAM, log delivery, alarms and retry/DLQ remain **NOT_RUN**. Cost model **6.6306 USD/month** remains an assumption, not a measured bill. Budget configuration/recipient and AlertEmail delivery remain unapproved/unverified.
- Required separate approvals: execution of this exact candidate; test frontend/users/seed/E2E scope; Budget configuration/recipient; eventual teardown and retained-data cleanup. Do not execute superseded candidates. Recheck live identity/status/source/artifact if execution occurs later.

Current evidence: [final readiness](evidence/aws-final-readiness.json), [artifact content verification](evidence/aws-review-artifact-fingerprint.json), [fresh processed IAM audit](evidence/aws-test-iam-review.json), [4G network checks](evidence/aws-4g-connectivity.json). Prior NO-GO evidence archived under `history/pre-4g-*`.

## Historical preparation and evidence boundary

- STS account ending **0098**, explicit region **ap-southeast-1**, stack **policy-assistant-fcaj-test**. Preparation verifies the exact account against ignored private context and checks suffix 0098 before uploading/creating a plan.
- CREATE change set **fcaj-review-20261021-072124-24ba855e**, observed at **2026-10-21T07:25:28.212901+00:00**: **CREATE_COMPLETE / AVAILABLE**, **45 Add / 0 Modify / 0 Remove / 0 Replace**.
- Source pair SHA-256: `24ba855eb69ff2f6ff251ac21c0202684f2c558a6753965d431ca9dce873e9f1`. Full per-file manifest: `evidence/aws-review-source-fingerprint.json`.
- Parameters: TableNamePrefix=policy-assistant-fcaj-test-, EnableOwnerIndex=true, LocalFrontendOrigin=http://localhost:8080, AlertEmail empty. Tags: Project=PolicyAssistant, Environment=fcaj-test, Purpose=FCAJ-demo-review.
- **All earlier candidates, including fcaj-review-20261021-064014-a9a40304 and fcaj-review-20261021-063231-1f5cb969, are superseded and must not be executed.** They were not deleted.
- Actual AWS processed template was retrieved and saved during this candidate's successful creation. Automated audit of that saved template passed; this is an AWS-produced template, not an invented local transform. Later fresh status/audit and ZIP download checks encountered ConnectTimeoutError. Cached audit is explicitly labelled `fresh_aws_status_verified=false`; no effective-permission simulation or deployed behavior is claimed. See `evidence/aws-test-iam-review.json` and `evidence/aws-review-artifact-fingerprint.json`.

## Resumption read-only verification — 2026-10-21

- Git checked in the canonical app checkout (`policy-assistant-github`, HEAD 80c4eef), worklog (HEAD 846d2ff) and selected legacy checkout (HEAD fe654d2). Existing dirty/staged changes remain; no commit, push, reset or checkout was performed. Legacy session-file deletions/staged .gitignore were preserved.
- Latest attempt started **2026-10-21T07:41:02.918572+00:00**, completed **2026-10-21T07:41:13.727086+00:00**: **BLOCKED**, **ConnectTimeoutError** during **STS account identity**. Current identity, candidate availability, fresh processed template, ZIP download and old-stack status were not reverified by this attempt. The last successful AWS identity/preflight and candidate observations above remain historical, not current confirmation.
- At **2026-10-21 07:44 UTC**, source, built SAM template and packaged SAM template match after normalization of CodeUri and SAM-generated build metadata; parameters, outputs and resource IDs also match. Template+app hash remains the exact candidate hash. See `evidence/aws-local-template-consistency.json`. This local chain plus the actual saved processed AWS snapshot is useful evidence, but does not replace a fresh AWS read.
- Artifact verifier uses authenticated SDK GetObject against only the saved candidate prefix, hashes downloaded ZIP bytes, and compares every archive member digest with **all three** `.aws-sam/build/<function>` directories. It does not use or print a presigned URL; S3 ETag is not treated as SHA-256. **The download has not succeeded**, so no archive digest or integrity PASS is claimed. Command: `.venv/Scripts/python.exe -m scripts.verify_review_artifact`. Safe errors/timestamps are saved in `evidence/aws-review-artifact-fingerprint.json`.
- Current static lint rerun in the project virtual environment passed. Workshop EN/VI Hugo build passed (128 EN/127 VI pages); link check examined 129 HTML pages / 12,274 references / zero failures. Three existing theme deprecation warnings remain.
- **Final decision remains NO-GO for deployment** until fresh checks succeed and the owner separately approves the exact candidate/E2E scope. Budget recipient is still unspecified and no Budget write is approved.

## Changes versus the prior 42-resource candidate

1. All three functions now use explicit IAM roles with **no managed BasicExecution/SQS policies**. Three new AWS::IAM::Policy resources each grant only logs:CreateLogStream and logs:PutLogEvents to that function's exact precreated log group ARN. No logs:CreateLogGroup is needed; CloudFormation creates the groups. Thus 42 becomes 45 resources, with no added AWS service or separate IAM fee.
2. Log policies are attached separately after role/function/log-group creation, avoiding a dependency cycle. The processed-template dependency audit passes. Do not invoke test functions until CREATE_COMPLETE and group/policy readiness checks pass.
3. DLQ RedriveAllowPolicy is **byQueue** with exactly the same account/region/stack's main queue ARN. The deterministic ARN matches its QueueName and avoids a DLQ-to-source-to-DLQ dependency cycle.
4. DocumentsBucketTlsPolicy now has **DeletionPolicy Retain and UpdateReplacePolicy Retain**, matching the already retained bucket and two tables. Normal stack deletion/replacement retains the explicit HTTPS Deny with document bytes. It is not protection against a privileged operator manually removing the policy, nor Object Lock; the existing lifecycle still operates.

## IAM analysis and remaining wildcards

Processed audit: **0 runtime Allow statements with Resource '*'**, **0 managed policy attachments**. API role accesses only the new policy table, metadata/ByOwner index, document uploads prefix and main queue. Worker accesses new metadata, exact document versions in uploads/* and the new main queue. Recovery accesses ByStatus, new metadata and that queue. Function environment variables point to new stack Refs, not legacy fallback table names.

Remaining wildcards are scoped: LogGroup.Arn includes :* for streams in that exact group; S3 uploads/* and frontend object ARN remain inside their named bucket; API stage/document-path wildcards remain inside the new API/account/region. S3 TLS policies use Principal '*' and Action s3:* only in **Deny**, not public Allow. Nine Lambda permissions remain eight API route permissions plus one scheduled invocation permission. No runtime PassRole, IAM administration, logs reads or cross-stack ImportValue is introduced.

IAM references/conditions and an acyclic dependency graph were checked in the actual processed snapshot. Effective IAM, log delivery, S3 enforcement and queue behavior on AWS remain untested until deployment/E2E approval.

## Existing environment and isolation

Read-only preflight at 2026-10-21 07:19 UTC verified old policy-assistant UPDATE_COMPLETE, last update **2026-10-19 11:10:29 UTC**; the new test stack remained REVIEW_IN_PROGRESS. No UpdateStack/ExecuteChangeSet/data mutation was performed on the existing environment. The only authorized cloud writes were code upload under a new review prefix in the existing packaging bucket and creation of this unexecuted CREATE candidate.

New table names: policy-assistant-fcaj-test-Policies / policy-assistant-fcaj-test-DocumentMetadata. Bucket and queue names are stack-scoped; other names are CloudFormation-generated. No old table/user/object/message is imported, migrated, overwritten or re-owned. The preparation tool is fixed to CREATE on the test target and rejects an executed/non-owned placeholder. **Applying this template to the old stack would change its configuration and is not authorized or claimed to be harmless.** Separate stacks still share the account, billing, packaging bucket and Lambda concurrency limit (last observed 10); this is not separate-account isolation. Use sequential low-volume tests.

## Cost, Budget and retained stock

The official-price assumed-load model remains **6.630595 USD/month gross**, before Free Tier/credits/tax: Lambda .072670; HTTP API .125; DynamoDB .196625; S3 .633250; SQS .12; SNS planning reserve .00205; CloudWatch 4.23; Cognito Lite .55; CloudFront .449; direct egress .252. Three added IAM policies and retained S3 policy have no separate service charge. Full rates/quantities: [cost-estimate.md](cost-estimate.md). Stress model 10x: 34.7081 USD/month, not a cap.

Assumptions: 100 MAU, 100,000 API requests, 500 2-MiB uploads, 1,000 downloads, 25 GB document versions, 300,000 SQS requests, 1 GB logs and five alarms/one dashboard. Excludes existing stack/account usage, tax/support/domain/SMS/extras, usage beyond assumptions and small packaging stock/request charges. AlertEmail is empty: no SNS recipient or delivery proof. Existing environment has separate costs. No Calculator estimate URL or actual test invoice exists. One additional review artifact upload occurred; subsequent S3 inventory/ZIP-read verification was blocked by network, so do not label post-upload ZIP verification PASS.

Retained stock at model sizes is about **.6649 USD/month** (25 GB S3 + .1 GB DynamoDB storage + .05 GB PITR, before allowances and later requests/egress); actual test stock is not measured. Policy Retain does not stop lifecycle or charges. Current expiry 365 days plus noncurrent expiry 365 after becoming noncurrent can retain versions roughly 730 days.

**Budget proposal only:** USD10/month COST, tag Environment=fcaj-test AND Project=PolicyAssistant, no region filter excluding global CloudFront, explicit ACTUAL >80%/>100% and FORECASTED >100%, no automatic actions. Recipient is awaiting owner confirmation. Tag activation/coverage/delivery need verification; a tag-only view may miss untaggable dashboard/shared artifact charges. Keep the existing account-wide USD5 Budget unchanged and reconcile Bills; a separate change to it needs approval. Budgets are delayed alerts, not a hard cap. Read [budget-test-proposal.md](budget-test-proposal.md) and [JSON draft](budget-test-proposal.json). No Budget API write, subscriber change or email was performed.

## Verification actually run

- **128 backend tests passed**, including exact per-function logging, absence of managed wildcards, DLQ source isolation, no cycle-inducing source reference and retained HTTPS policy.
- **17 frontend tests**, **1 fixture browser scenario**, **1 real-local-handler browser scenario** passed. Python fatal-category lint, app.py mypy, JS syntax, SAM validate --lint and SAM build passed. The old policy-location test was updated to follow the explicit role; the full suite was rerun after that correction.
- **9 AWS integration tests skipped** deliberately; not AWS PASS. Evidence: `evidence/offline-acceptance.json`.
- Processed AWS snapshot audit passed all checks, including new data Refs and no circular dependencies. Fresh re-audit and uploaded ZIP download were blocked by network timeout; see explicit provenance/status rather than assuming success.

## E2E, rollback and cleanup gate

All application AWS acceptance remains NOT_RUN. After a separate approval: recheck account/candidate/fingerprints/live status and artifact; execute CREATE; verify complete stack/tag/index/storage/log-policy readiness; seed synthetic policies, create two invitation-suppressed test users, publish exactly four assets and run [A01–A12](aws-live-test-plan.md). Test valid/oversized/tampered/invalid-byte PDF, Cognito/two-user isolation, frozen-version SHA-256 and async behavior. A direct real mixed Lambda event is distinct from real BatchSize1 SQS retry/DLQ. Use only one malformed synthetic queue probe; no IAM outage, visibility change, purge or unapproved redrive.

Failed CREATE can roll back newly created infrastructure; inspect actual survivors. Failed E2E after CREATE_COMPLETE does not automatically roll back CloudFormation. Stop rollout and preserve state/evidence; do not apply an old template blindly or touch production. Data deletion is separate.

After approved successful stack deletion, two test DynamoDB tables, the document bucket **and its HTTPS policy** remain. Review artifacts are outside the application stack. Other resources default Delete, but a nonempty/versioned frontend bucket can cause DELETE_FAILED. Retained bucket cleanup must use HTTPS **while its policy remains**; do not delete the policy first just to empty it. If the bucket remains, the policy must remain. Delete retained data/versions/markers/backups or shared-bucket prefixes only under a separate explicit inventory approval. See [cleanup-retained-data.md](cleanup-retained-data.md).

## GO / NO-GO

| Area | Decision |
|---|---|
| Local code/IaC checks and fresh AWS processed-template audit | GO for predeployment verification; signed AWS reads and fresh audit succeeded |
| Current live status / uploaded archive re-verification | VERIFIED after 4G switch, 08:07:43–08:09:00 UTC; candidate AVAILABLE, all three function archives match |
| Runtime effective permissions / real product behavior | NOT_RUN, no live PASS |
| Budget creation | NO-GO: exact recipient/configuration/coverage approval pending |
| Execute/publish/users/queue probe | NO-GO: owner has not authorized execution |
| Resource/data cleanup | NO-GO: separate destructive-scope approval required |

Required separate decisions: accept the new named candidate after fresh read/artifact verification; approve Budget configuration/recipient and any cost-allocation tag activation; approve deployment; approve user/seed/frontend/E2E operations; approve any extra fault-injection/mapping change; approve eventual teardown and retained-data/artifact deletion. No commit/push is performed.

## Exact 45 resource actions and retention

| Logical ID | Type | Action | DeletionPolicy / UpdateReplacePolicy |
|---|---|---|---|
| AlertTopic | AWS::SNS::Topic | Add | Delete (default) / Delete (default) |
| DocumentDLQAlarm | AWS::CloudWatch::Alarm | Add | Delete (default) / Delete (default) |
| DocumentMetadata | AWS::DynamoDB::Table | Add | Retain / Retain |
| DocumentQueueAgeAlarm | AWS::CloudWatch::Alarm | Add | Delete (default) / Delete (default) |
| DocumentRecovery | AWS::Lambda::Function | Add | Delete (default) / Delete (default) |
| DocumentRecoveryLogWritePolicy | AWS::IAM::Policy | Add | Delete (default) / Delete (default) |
| DocumentRecoveryLogs | AWS::Logs::LogGroup | Add | Delete (default) / Delete (default) |
| DocumentRecoveryRecoverPending | AWS::Events::Rule | Add | Delete (default) / Delete (default) |
| DocumentRecoveryRecoverPendingPermission | AWS::Lambda::Permission | Add | Delete (default) / Delete (default) |
| DocumentRecoveryRole | AWS::IAM::Role | Add | Delete (default) / Delete (default) |
| DocumentsBucketTlsPolicy | AWS::S3::BucketPolicy | Add | Retain / Retain |
| FrontendAccessControl | AWS::CloudFront::OriginAccessControl | Add | Delete (default) / Delete (default) |
| FrontendBucket | AWS::S3::Bucket | Add | Delete (default) / Delete (default) |
| FrontendBucketPolicy | AWS::S3::BucketPolicy | Add | Delete (default) / Delete (default) |
| FrontendDistribution | AWS::CloudFront::Distribution | Add | Delete (default) / Delete (default) |
| FrontendHeaders | AWS::CloudFront::ResponseHeadersPolicy | Add | Delete (default) / Delete (default) |
| PoliciesTable | AWS::DynamoDB::Table | Add | Retain / Retain |
| PolicyAssistantApi | AWS::ApiGatewayV2::Api | Add | Delete (default) / Delete (default) |
| PolicyAssistantApiProdStage | AWS::ApiGatewayV2::Stage | Add | Delete (default) / Delete (default) |
| PolicyAssistantDashboard | AWS::CloudWatch::Dashboard | Add | Delete (default) / Delete (default) |
| PolicyAssistantDocumentDLQ | AWS::SQS::Queue | Add | Delete (default) / Delete (default) |
| PolicyAssistantDocumentQueue | AWS::SQS::Queue | Add | Delete (default) / Delete (default) |
| PolicyAssistantDocumentsBucket | AWS::S3::Bucket | Add | Retain / Retain |
| PolicyAssistantDurationAlarm | AWS::CloudWatch::Alarm | Add | Delete (default) / Delete (default) |
| PolicyAssistantErrorAlarm | AWS::CloudWatch::Alarm | Add | Delete (default) / Delete (default) |
| PolicyAssistantFunction | AWS::Lambda::Function | Add | Delete (default) / Delete (default) |
| PolicyAssistantFunctionDocumentDownloadPermission | AWS::Lambda::Permission | Add | Delete (default) / Delete (default) |
| PolicyAssistantFunctionDocumentStatusPermission | AWS::Lambda::Permission | Add | Delete (default) / Delete (default) |
| PolicyAssistantFunctionGetPolicyByIdPermission | AWS::Lambda::Permission | Add | Delete (default) / Delete (default) |
| PolicyAssistantFunctionHealthCheckPermission | AWS::Lambda::Permission | Add | Delete (default) / Delete (default) |
| PolicyAssistantFunctionListDocumentsPermission | AWS::Lambda::Permission | Add | Delete (default) / Delete (default) |
| PolicyAssistantFunctionLogWritePolicy | AWS::IAM::Policy | Add | Delete (default) / Delete (default) |
| PolicyAssistantFunctionRole | AWS::IAM::Role | Add | Delete (default) / Delete (default) |
| PolicyAssistantFunctionSearchPoliciesPermission | AWS::Lambda::Permission | Add | Delete (default) / Delete (default) |
| PolicyAssistantFunctionSubmitDocumentPermission | AWS::Lambda::Permission | Add | Delete (default) / Delete (default) |
| PolicyAssistantFunctionUploadSessionPermission | AWS::Lambda::Permission | Add | Delete (default) / Delete (default) |
| PolicyAssistantLogGroup | AWS::Logs::LogGroup | Add | Delete (default) / Delete (default) |
| PolicyAssistantUserPool | AWS::Cognito::UserPool | Add | Delete (default) / Delete (default) |
| PolicyAssistantUserPoolClient | AWS::Cognito::UserPoolClient | Add | Delete (default) / Delete (default) |
| PolicyAssistantWorker | AWS::Lambda::Function | Add | Delete (default) / Delete (default) |
| PolicyAssistantWorkerDocumentQueueEvent | AWS::Lambda::EventSourceMapping | Add | Delete (default) / Delete (default) |
| PolicyAssistantWorkerLogGroup | AWS::Logs::LogGroup | Add | Delete (default) / Delete (default) |
| PolicyAssistantWorkerLogWritePolicy | AWS::IAM::Policy | Add | Delete (default) / Delete (default) |
| PolicyAssistantWorkerRole | AWS::IAM::Role | Add | Delete (default) / Delete (default) |
| RecoveryErrorAlarm | AWS::CloudWatch::Alarm | Add | Delete (default) / Delete (default) |


## Latest read-only connectivity round — 2026-10-21 07:47–07:49 UTC

**NO-GO remains.** STS GetCallerIdentity timed out from 07:47:58 to 07:48:10 UTC (ConnectTimeoutError). One independent DescribeChangeSet attempt, without retrying STS, also timed out from 07:49:32 to 07:49:43 UTC. It did not reach ARN/account/region validation. No further authenticated retries were made. Current identity, availability and action count are not confirmed; 07:25:28 UTC remains the historical observation.

Unsigned diagnostics at 07:48:07–07:48:28 UTC: DNS resolved STS/CloudFormation/S3; direct STS connection timed out; direct CloudFormation/S3 TCP 443 and TLS 1.3 succeeded. No proxy was detected by urllib. A TCP/TLS connection does not establish signed SDK access, valid credentials or successful AWS operations, and does not prove a specific firewall/VPN cause.

Local source hash still matches the candidate. Live processed-template audit and authenticated S3 download/member SHA-256 comparison for all three functions are **NOT_RUN due to upstream blockers**, not VERIFIED. No claim is made about newly observed IAM or artifact integrity. Evidence: `evidence/aws-sts-readonly-attempt.json`, `evidence/aws-connectivity-diagnostics.json`, `evidence/aws-review-artifact-fingerprint.json`, `evidence/aws-final-readiness.json`. Connection recovery steps: [aws-connectivity-check.md](aws-connectivity-check.md).


## Windows prerequisite check — 2026-10-21 07:53:42–07:54:04 UTC

NO-GO unchanged. AWS CLI 2.36.17 works; DNS resolves. No endpoint/proxy/CA override was detected in the inspected environment/configuration. Default region us-west-2 is not used by the explicitly Singapore-scoped project tools. STS and CloudFormation direct connections still timed out; only S3 unsigned TCP/TLS succeeded. Root cause is undetermined. No AWS API retries or configuration/credentials changes were made in this round; current account/candidate/template/artifact verification remains incomplete. See [network review](evidence/aws-windows-network-review.json) and [safe recovery instructions](aws-connectivity-check.md).


## Separate Budget decision — read-only review 2026-10-21 08:12:48–08:12:52 UTC

Proposed Budget name does not exist; six existing budgets remain unchanged. Billing returned no user-defined allocation records for Environment/Project, so test-tag coverage is not operationally verified. Budget creation, exact recipient and tag-key activation require explicit approval. A tag-only Budget cannot be claimed to cover all USD6.6306 of the gross model; untagged/shared/global charges require reconciliation with Bills/account-wide warnings. See [exact configuration and independent approval A/B](budget-test-proposal.md). Technical predeployment verification remains GO; execution is unapproved. No AWS write was performed.
