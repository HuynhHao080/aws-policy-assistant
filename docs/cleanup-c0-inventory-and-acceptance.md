# Approval C0 — cleanup inventory và final test acceptance

**READ_ONLY_INVENTORY_VERIFIED. CLEANUP NOT_EXECUTED.** GO demo test có thời hạn, kèm manual monitoring và các hạn chế dưới đây. NO-GO production. Không có approval xóa/thay đổi AWS trong C0.

## Phạm vi bằng chứng

STS account …0098, ap-southeast-1; stack test UPDATE_COMPLETE. Inventory chính: 2026-10-21T18:41:20.382036+00:00 → 2026-10-21T18:41:35.758237+00:00; supplemental SNS/metrics: 2026-10-21T18:42:37.763586+00:00 (khoảng01:41–01:43 ngày22/10/2026 UTC+7). Stack cũ policy-assistant metadata không đổi qua vòng inventory chính, không có write target tới stack cũ. Không full drift detection/account-wide discovery.

Đã đọc reports/evidence B1/B2/B3/B4/B5/B5-R6/B5-R7, lưu statuses và hashes trong JSON. API chỉ đọc metadata/configuration/key projections; không đọc PDF bodies/policy text, email usernames/passwords/JWT hoặc DLQ messages. S3 versions và DynamoDB scan có pagination; không phải cross-service atomic snapshot. C0 không rerun E2E.

## Resource inventory và ownership

**45 stack resources =41stack-managed Delete(default) +4Retain**. Full logical/type/physical IDs, policies và statuses trong [inventory JSON](evidence/approval-c0-inventory.json); account được che. Không dùng prefix hoặc tag làm bằng chứng duy nhất cho ownership: chính CloudFormation resources/template xác định stack membership.

-3Lambda,3IAMroles+3IAMpolicies,9LambdaPermissions,1EventBridgeRule,1SQS event mapping.
-2DynamoDBtables,2S3buckets+2bucket policies,2SQSqueues,1CognitoPool+1Client.
-1HTTPAPI+1stage,1CloudFrontdistribution+1OAC+1responseheaderspolicy.
-3loggroups,5alarms,1dashboard,1SNS topic.

### Retain — tồn tại sau stack deletion thành công

| Logical ID | Retain / UpdateReplacePolicy | Chi phí/tác động |
|---|---|---|
| PoliciesTable |Retain /Retain|Data/index storage và PITR tiếp tục có thể tính phí; không còn CFN quản lý sau delete |
| DocumentMetadata |Retain /Retain|Records/GSIs/PITR vẫn tồn tại; TTL hiện DISABLED |
| PolicyAssistantDocumentsBucket |Retain /Retain|Mọi current/noncurrent versions tiếp tục lưu/tính phí theo lifecycle |
| DocumentsBucketTlsPolicy |Retain /Retain|Không có storage fee riêng cho policy; bắt buộc giữ HTTPS Deny cùng retained bucket |

Retain không phải backup/khóa chống privileged deletion. Không xóa TLS policy khi giữ bucket. [AWS Retain](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-deletionpolicy.html) và [bucket policy retention](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-s3-bucketpolicy.html).

### External hoặc service-managed state

- Deployment bucket dùng chung `aws-sam-cli-managed-default-samclisourcebucket-efw1spucsorg`, owner stack theo tag là **aws-sam-cli-managed-default**, không phải test stack. Chỉ list prefix `policy-assistant-fcaj-test/`, không quét/xóa toàn bucket hoặc owner stack.
- Prefix có4ZIP/4versions,0delete markers, **66.971.698bytes**. B1ZIP đang dùng Worker/Recovery và là rollback artifact API; B5-R2ZIP đang dùng API. **Giữ cả hai** khi demo/rollback cần thiết.
- Hai ZIP prefixes fcaj-review-20261021-063231-1f5cb969 và064014-a9a40304 khớp hồ sơ historical superseded reviews. Không live Code refs trong stack test nhưng không đủ để tự xóa: chưa full cross-stack/reference audit hoặc rehash contents trong C0. Chỉ candidate cleanup sau exact key/version approval.
- ListChangeSets hiện **0**. B5-R5 đã execute; không dùng các snapshot AVAILABLE cũ làm hiện trạng. Không xóa change set trong C0 và không suy đoán nguyên nhân chi tiết của mọi set biến mất.
- Budget account20USD và các Budget khác là external/account-wide: **giữ nguyên**, kể cả khi teardown test. Bucket dùng chung có thể chứa production artifacts ngoài prefix, hoàn toàn ngoài cleanup scope.
- CloudFront caches/invalidations, Cognito sessions, CloudWatch native metric history, backups/PITR recovery points và evidence local có lifecycle riêng; không mặc định stack deletion xóa mọi lịch sử/service state. Không quét mọi external backup/account resource trong C0.

## Data inventory

| Thành phần | Số lượng được đọc hiện tại | Phân loại |
|---|---|---|
| DocumentsBucket |6current keys,7versions,0delete markers;10.488.812bytes tổng versions |B4:5versions/4keys; R7:2versions/2keys |
| FrontendBucket |4assets/4versions,0delete markers;33.913bytes |Expected B2 keys index.html/app.js/styles.css/config.json; không rehash body C0 |
| DocumentMetadata |7records, scan keys/status strongly consistent |B4:4; B5:1; R7:2 |
| PoliciesTable |3records |POL-001/002/003, B4 seed IDs khớp seed implementation và evidence |
| Cognito |2users Enabled/CONFIRMED |TestA/TestB liên kết với B3 qua owner_sub của synthetic docs; không lưu username/email |
| Main queue |visible0/not-visible0/delayed0 |Không Receive/Purge/Delete |
| DLQ |visible khoảng1,not-visible0/delayed0 |Phù hợp diagnostic B4; **identity/body chưa đọc C0, chưa xác minh chính xác** |

Document provenance dựa exact doc IDs trong evidence; S3 version provenance dựa key/session và lịch sử test, không kiểm lại content hash từng version C0. Unknown records/users/object keys trong phạm vi scan:0; **không suy ra toàn account không có unknown data**. DLQ message identity và cross-stack references của superseded artifacts chưa chắc chắn, không đưa vào automatic deletion.

### Metadata records

| Document | Nguồn / identity | Trạng thái |
|---|---|---|
|doc-0ca388ce767943bdb439afb9852730ef|B5-R7 / TestA|processed|
|doc-e2eb1a7c9c654ccfa8ad264839b01373|B4 / TestB|failed|
|doc-695099d7ed66418cb55fc0ed6a4abce7|B4 / TestB|processed|
|doc-1d861bcda8b647a4aedea51ef55c5717|B5-R7 / TestB|processed|
|doc-153ed4349ac1424ca0e822749885b625|B4 / TestA|processed|
|doc-0dfd6bcb45f347ecab0a7ae5f4b636d1|B5 / TestA|uploading|
|doc-15dd319de1224b4f9df1375fce17bb09|B4 / TestA|processed|

B5 orphan uploading vẫn không có object; không sửa/xóa. B4 có một INVALID_PDF failed record và một10MiB size-boundary object. Một B4 doc có2versions do controlled overwrite, metadata frozen version không nhất thiết là latest; không coi latest mismatch là corruption. R7 cả hai processed/609bytes, integrity có evidence riêng.

### DocumentsBucket versions — metadata only

| Key | Bytes | Nguồn theo session | Latest |
|---|---:|---|---|
|uploads/doc-0ca388ce767943bdb439afb9852730ef/document|609|B5-R7|True|
|uploads/doc-153ed4349ac1424ca0e822749885b625/document|10485760|B4|True|
|uploads/doc-15dd319de1224b4f9df1375fce17bb09/document|606|B4|True|
|uploads/doc-15dd319de1224b4f9df1375fce17bb09/document|594|B4|False|
|uploads/doc-1d861bcda8b647a4aedea51ef55c5717/document|609|B5-R7|True|
|uploads/doc-695099d7ed66418cb55fc0ed6a4abce7/document|594|B4|True|
|uploads/doc-e2eb1a7c9c654ccfa8ad264839b01373/document|40|B4|True|

Đầy đủ VersionIds trong evidence để trình exact deletion manifest tương lai; VersionId không phải presigned capability. Không gọi DeleteObject trong C0. Xóa version vĩnh viễn không thể khôi phục chỉ nhờ versioning nếu không có bản sao khác.

## Runtime, observability và cost exposure

- API/Lambda/CloudFront/Rule live cấu hình nằm trong inventory.3Lambda Active/Successful. API hash mới; worker/recovery old hash. Frontenddistribution Deployed/Enabled; origin đúng bucket test. Recovery rule ENABLED rate(2minutes), tiếp tục invoke dù không demo.
- Dashboard1,4metricwidgets;5alarms. DLQ ALARM,4othersOK. SNS topic là alarm action của cả5 nhưng **0confirmed/0pending subscriptions**: alarm state có bằng chứng; chưa có SNS receiver/delivery. Không tự thêm recipient/subscription/publish test.
-3Lambda log groups stack-managed, retention30days. StoredBytes service trả0, không chứng minh không có ingestion/storage phí hoặc không có log; R7 từng quét65events. Không tải raw log bodies C0.
- Metric descriptors thấy Lambda Invocations/Duration/Errors/Throttles/Concurrency, API Count/4xx/5xx/Latency, SQS backlog/age/send/receive. Listing không chứng minh workload hiện tại healthy; metric history có thể thiếu inactive series.
-2DynamoDB on-demand tables; PITR **ENABLED35days**, TTL DISABLED. TableSizeBytes/ItemCount trong DescribeTable có độ trễ; dùng paginated key scan để đếm3/7records. PITR có recovery-point lag và restore tạo table mới, không phải undo tại chỗ; phải kiểm restore point/data coverage và IAM/cutover trong approval riêng.
- Documents lifecycle current365days/noncurrent365days; có thể tạo delete marker rồi giữ noncurrent thêm thời gian, **không bảo đảm mọi bytes biến mất sau365days**. Frontendbucket versioning ENABLED, không lifecycle. Không tự sửa retention.
- Chi phí tiếp tục gồm dashboard/alarms, Recovery invocations/logs, PITR/table/index storage, S3 versions/artifacts/requests, API/Lambda/Cognito/SQS/SNS/CloudFront theo sử dụng/traffic. Tiền nhỏ không đồng nghĩa0; giữ hạ tầng không dùng vẫn có các thành phần nền.
- Model6.6306USD/tháng tại assumptions100MAU/100krequests/25GB stock trong cost-estimate.md là mô hình gross ngày21/10, **không phải idle demo cost hoặc AWS forecast**. Không tạo estimate mới/sửa Budget trong C0.
- Budget hiện COST/MONTHLY20USD,3alerts ACTUAL80/100+FORECASTED100. Snapshot actual5.479USD/forecast8.539USD có Billing lag, toàn account gồm stack cũ/shared resources. Email verification không kiểm lại, email delivery **NOT_VERIFIED**; SNS0subscriptions là vấn đề độc lập với Budget email. Không in/yêu cầu email trong báo cáo. Budget không hard cap.

## Phương án A/B/C

| Tiêu chí | A — giữ để demo | B — xóa dữ liệu test, giữ hạ tầng | C — teardown stack và Retain theo approval riêng |
|---|---|---|---|
| Giữ |45resources,users,frontend,policies/docs/evidence/artifacts; Budget |45resources,frontend,users/artifacts; chọn giữ3policies để demo nếu user duyệt subset |4Retain và external shared bucket/Budget/evidence mặc định vẫn giữ; xóa retained chỉ ở approval riêng |
| Xóa dự kiến |Không |Chỉ exact records/versions được duyệt; DLQ thao tác riêng |41nonretained resources theo CFN, gồm users/queues/logs/API/CloudFront/frontend; frontend phải empty versions trước |
| Mất dữ liệu |Không do cleanup; lifecycle/SQS retention vẫn hoạt động |Permanent version deletes, metadata gone; evidence không thay backup |Mất users/sub identities, logs/queues/config live, downtime/demo unavailable; Retain data vẫn còn |
| Chi phí |Toàn bộ nền và usage còn |Tiết kiệm data stock nhỏ; dashboard/alarms/PITR/Recovery vẫn còn |Giảm test runtime nền sau delete thành công; Retain/PITR/artifacts/historical metrics/backups có thể còn phí; stack cũ vẫn tính phí |
| Khôi phục |Chưa thay gì; giữ rollback ZIP |Chỉ từ approved backup/version chưa xóa/PITR có coverage; không hứa undo |Redeploy có thể đổi IDs/endpoints/usersubs; cần import/restore/cutover riêng, không bấm deploy lại là khôi phục toàn bộ |
| Quyền tiếp |Chốt thời hạn và manual monitoring; mọi đổiconfig cần approval |Exact data delete/write manifest, optional bounded DLQ receive/delete, backup/export riêng |Approved disable/drain, frontend versions delete, DeleteStack và retained-data deletion tách biệt |

### Thứ tự nếu A

Giữ nguyên hiện trạng; chốt ngày demo/expiry và người theo dõi Budget/alarms thủ công; review daily trong giai đoạn demo. Không auto-schedule cleanup. Sau demo trình inventory refresh và chọn B/C. Nếu muốn SNS alerts hoạt động, cần approval notification config/recipient riêng trong AWS Console; không ghép với quyền cleanup.

### Thứ tự nếu B — chỉ kế hoạch

1. Refresh identity/ownership, stop nếu UNKNOWN hoặc data/versions khác manifest; chốt có giữ3policies/two users để demo hay không. Export/backup evidence/data cần thiết chỉ khi được duyệt, kiểm hash/restore feasibility.
2. Bảo đảm không có upload/pending work hoặc in-flightqueue; đóng cửa sổ thao tác demo. Nếu cần pause producers/Recovery/event mapping, đó là **configuration write cần approval riêng**, không tự làm.
3. Xóa đúng approved metadata và **mọi approved versions/delete markers** của keys liên quan trong cửa sổ quiescent; không broad prefix/recursive bucket wipe. Chọn thứ tự theo manifest để worker không tạo orphan/race; nếu không bảo đảm quiescence thì dừng, không xóa.
4. DLQ không thể DeleteMessage chỉ bằng MessageId; phải approve một bounded ReceiveMessage để kiểm expected B4 diagnostic identity/hash rồi delete đúng receipt handle. **C0 chưa đọc được identity**, nếu mismatch/unknown giữ message, không PurgeQueue và không redrive/poison. Receipt không lưu public.
5. Sau cleanup được duyệt: read-only scan exactkeys/records/versions/counts, queues0 nếu đúng scope; alarm tự reevaluate theo metrics/missing-data, không hứa OK ngay hoặc tự reset. Lưu before/after và Billing delayed snapshot.

B không nhất thiết tiết kiệm đáng kể khi sample PDFs khoảng10MiB; ưu tiên giữ bằng chứng demo thay vì xóa sớm chỉ để giảm storage rất nhỏ.

### Thứ tự nếu C — chỉ kế hoạch

1. Chốt demo kết thúc, exact resource/data manifest, downtime và khả năng mất Cognito identities/logs/queues; export cần thiết/restore coverage được duyệt. UNKNOWN trong bất kỳ nonretained resource thì dừng teardown.
2. Approve cụ thể việc quiesce producers/disable distribution/đợi propagation nếu runbook cần; mọi update ngoài DeleteStack cần nêu rõ. Không tự invalidate/deploy/sửa stack để teardown.
3. Frontendbucket đang versioned/nonempty: approved delete đúng4versions (và refresh any markers mới), kiểm bucket empty. [S3 nonempty bucket khiến stack deletion thất bại](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-s3-bucket.html). Không empty DocumentsBucket vì nó Retain, trừ approval độc lập.
4. DeleteStack đúng test stack sau phê duyệt; monitor events. Không force-delete/retry/update nếu DELETE_FAILED ngoài approval; chỉ read-only investigation. Không chạm policy-assistant hoặc aws-sam-cli-managed-default.
5. Xác minh41default-delete resources đã removed,4Retain còn đúng TLS policy/publicblock/encryption. Native metric history/external artifacts/Budget/backups có lifecycle riêng. CFN deletion success không chứng minh mọi account cost đã dừng.
6. Retain cleanup là **approval riêng** theo bảng ARN/bucket/key/version và snapshot backup: xóa retained table/data/PITR artifacts hoặc bucket versions chỉ khi được duyệt. Giữ HTTPS policy trong suốt thời gian bucket còn giữ dữ liệu; không xóa policy trước để làm dễ cleanup. Không mặc định delete4Retain.
7. External review artifacts chỉ exact approved keys/versions sau dependency audit; giữ active/rollback ZIP cho tới hết nhu cầu recovery. Không delete shared bucket. Kiểm Cost Explorer/Bills sau độ trễ, không dựa Budget để chứng minh zero charges.

## Final acceptance

| Stage | Bằng chứng / kết luận |
|---|---|
| B1 |45resources CREATE_COMPLETE, stack created; lịch sử |
| B2 |Static frontend published/verified; lịch sử |
| B3 |Hai synthetic users created/confirmed; C0 read lại vẫn2 |
| B4 |19PASS,1NOT_RUN(browser); real API/SDK evidence |
| B5 |FAIL browser upload, giữ nguyên lịch sử; không sửa thành PASS |
| B5-R6 |API-only update UPDATE_COMPLETE, Code hash verified |
| B5-R7 |10browser cases PASS, bounded real headless Edge; không rerun C0 |

GO demo test: browser login/search/upload/process/download/hash/ownership/logout có evidence thật. Open items: DLQ baseline diagnostic+ALARM, SNS0subscriptions, Budget email delivery chưa chứng minh, cleanup/retention và chi phí nền. **NO-GO production** khi chưa có operational recipients/delivery proof, restore/recovery rehearsal, workload/concurrency/latency/cost tests, threat/security review đủ scope, credentials/identity lifecycle/retention và incident/runbook được owner duyệt.

Test coverage limits: một Edgeheadless/viewportmobile, không phải physical mobile/all browsers; dữ liệu synthetic nhỏ; size/MIME/invalidPDF đã B4 nhưng không stress. B4 partial-batch evidence qua direct mixed Lambda event, currentSQSBatchSize1 nên không chứng minh fresh multi-record queue workload. Không có multi-region/disaster recovery, full outage/recovery, exhaustive race/retry/security/PII/compliance audit. Metric snapshots không thay canary/SLO tests. Không tự thêm WAF/VPC/NAT hoặc dịch vụ tốn phí để lấp checklist.

FCAJ submission evidence ngoài technical acceptance (worklog thật, blog/events/office attendance/student architecture drawing) cần người dùng tự cung cấp/xác minh, không tuyên bố hoàn thành từ browser PASS.

## Khuyến nghị và Approval tiếp theo

**Chọn A có thời hạn tới buổi demo, giám sát thủ công.** Không cleanup trước khi demo/evidence đã chốt. Sau đó ưu tiên trình **C1 data-only subset** nếu vẫn cần hạ tầng demo; nếu đã kết thúc hoàn toàn, trình C2 teardown và C3Retain/external riêng để giảm nền/PITR lâu dài.

C1 cần user duyệt exact doc IDs/record keys/S3VersionIds, có giữ policies/users không, backup scope, stopconditions và bounded receive/delete diagnosticDLQ nếu muốn. Không approve blanket PurgeQueue/whole bucket/table/user deletion. Có thể tách DLQ-only thành C1a nếu chỉ muốn xử lý diagnostic alarm sau demo; recipient notification là approval độc lập.

C2 cần user duyệt exact41resource teardown scope, frontend emptying, distribution/quiesce steps nếu có, mất2users/logs/queues, rollback limitations. C3 riêng cho4Retain và exact shared-prefix artifact keys; **không delete shared bucket hoặc Budget**.

C0 không cấp bất kỳ quyền nào trong các phương án này. Không phát sinh deploy/E2E mới; CLEANUP NOT_EXECUTED, AWS WRITES0, COMMIT/PUSH NOT_EXECUTED. DỪNG.

## Appendix —45 stack resources

| Logical ID | Type | Class | DeletionPolicy / UpdateReplacePolicy |
|---|---|---|---|
|AlertTopic|AWS::SNS::Topic|STACK_MANAGED|Delete(default) / Delete(default)|
|DocumentDLQAlarm|AWS::CloudWatch::Alarm|STACK_MANAGED|Delete(default) / Delete(default)|
|DocumentMetadata|AWS::DynamoDB::Table|RETAIN|Retain / Retain|
|DocumentQueueAgeAlarm|AWS::CloudWatch::Alarm|STACK_MANAGED|Delete(default) / Delete(default)|
|DocumentRecovery|AWS::Lambda::Function|STACK_MANAGED|Delete(default) / Delete(default)|
|DocumentRecoveryLogWritePolicy|AWS::IAM::Policy|STACK_MANAGED|Delete(default) / Delete(default)|
|DocumentRecoveryLogs|AWS::Logs::LogGroup|STACK_MANAGED|Delete(default) / Delete(default)|
|DocumentRecoveryRecoverPending|AWS::Events::Rule|STACK_MANAGED|Delete(default) / Delete(default)|
|DocumentRecoveryRecoverPendingPermission|AWS::Lambda::Permission|STACK_MANAGED|Delete(default) / Delete(default)|
|DocumentRecoveryRole|AWS::IAM::Role|STACK_MANAGED|Delete(default) / Delete(default)|
|DocumentsBucketTlsPolicy|AWS::S3::BucketPolicy|RETAIN|Retain / Retain|
|FrontendAccessControl|AWS::CloudFront::OriginAccessControl|STACK_MANAGED|Delete(default) / Delete(default)|
|FrontendBucket|AWS::S3::Bucket|STACK_MANAGED|Delete(default) / Delete(default)|
|FrontendBucketPolicy|AWS::S3::BucketPolicy|STACK_MANAGED|Delete(default) / Delete(default)|
|FrontendDistribution|AWS::CloudFront::Distribution|STACK_MANAGED|Delete(default) / Delete(default)|
|FrontendHeaders|AWS::CloudFront::ResponseHeadersPolicy|STACK_MANAGED|Delete(default) / Delete(default)|
|PoliciesTable|AWS::DynamoDB::Table|RETAIN|Retain / Retain|
|PolicyAssistantApi|AWS::ApiGatewayV2::Api|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantApiProdStage|AWS::ApiGatewayV2::Stage|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantDashboard|AWS::CloudWatch::Dashboard|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantDocumentDLQ|AWS::SQS::Queue|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantDocumentQueue|AWS::SQS::Queue|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantDocumentsBucket|AWS::S3::Bucket|RETAIN|Retain / Retain|
|PolicyAssistantDurationAlarm|AWS::CloudWatch::Alarm|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantErrorAlarm|AWS::CloudWatch::Alarm|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantFunction|AWS::Lambda::Function|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantFunctionDocumentDownloadPermission|AWS::Lambda::Permission|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantFunctionDocumentStatusPermission|AWS::Lambda::Permission|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantFunctionGetPolicyByIdPermission|AWS::Lambda::Permission|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantFunctionHealthCheckPermission|AWS::Lambda::Permission|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantFunctionListDocumentsPermission|AWS::Lambda::Permission|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantFunctionLogWritePolicy|AWS::IAM::Policy|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantFunctionRole|AWS::IAM::Role|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantFunctionSearchPoliciesPermission|AWS::Lambda::Permission|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantFunctionSubmitDocumentPermission|AWS::Lambda::Permission|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantFunctionUploadSessionPermission|AWS::Lambda::Permission|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantLogGroup|AWS::Logs::LogGroup|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantUserPool|AWS::Cognito::UserPool|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantUserPoolClient|AWS::Cognito::UserPoolClient|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantWorker|AWS::Lambda::Function|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantWorkerDocumentQueueEvent|AWS::Lambda::EventSourceMapping|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantWorkerLogGroup|AWS::Logs::LogGroup|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantWorkerLogWritePolicy|AWS::IAM::Policy|STACK_MANAGED|Delete(default) / Delete(default)|
|PolicyAssistantWorkerRole|AWS::IAM::Role|STACK_MANAGED|Delete(default) / Delete(default)|
|RecoveryErrorAlarm|AWS::CloudWatch::Alarm|STACK_MANAGED|Delete(default) / Delete(default)|

[Full inventory](evidence/approval-c0-inventory.json) · [Summary](evidence/approval-c0-summary.json). Nguồn AWS chính thức tham khảo ngày22/10/2026 UTC+7; không tạo AWS Pricing Calculator estimate/link mới.
