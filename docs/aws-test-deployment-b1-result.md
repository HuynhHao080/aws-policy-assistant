# Approval B1 — kết quả thực thi test stack

**Status: CREATED_VERIFIED. B1 đã hoàn thành; DỪNG, chưa được phép B2/B3/B4/C.**

Account **…0098**, region **ap-southeast-1**, stack **policy-assistant-fcaj-test**. Execute đúng một lần change set `fcaj-review-20261021-072124-24ba855e`, chỉ 45 Add, không Modify/Remove/Replace; không deploy lại.

## Thời gian và Events

- Preflight STS/source/processed/artifacts/Budget/cost: 21/10/2026 khoảng 09:36 UTC.
- Execute request: **2026-10-21 09:37:14.915928 UTC** (16:37:14.915928 UTC+7).
- CloudFormation Stack CREATE_IN_PROGRESS event: **09:37:14.982 UTC**.
- Quan sát stack CREATE_COMPLETE: **09:42:51 UTC** (16:42:51 UTC+7), khoảng **337 giây** từ execute request.
- Kết thúc monitor/Budget read: **09:42:54 UTC**; kiểm tra dịch vụ và deployed template tiếp tục sau đó, có thời điểm riêng trong evidence.
- **45 tài nguyên CREATE_COMPLETE; không CREATE_FAILED, không rollback.** Event CREATE_COMPLETE thứ 46 là stack parent, không phải tài nguyên Add thứ 46.

[Execution/events/resource evidence](evidence/approval-b1-execution.json), [kiểm tra dịch vụ](evidence/approval-b1-service-readiness.json), [preflight mới](evidence/approval-b-final-preflight-readonly.json), [artifact](evidence/aws-review-artifact-fingerprint.json).

Sau execute thành công, DescribeChangeSet trả ChangeSetNotFoundException. Không tạo lại hoặc execute lại. Đã đọc template Processed trực tiếp từ stack triển khai, khớp chính xác snapshot candidate đã duyệt. AWS mô tả change sets được loại bỏ sau khi áp dụng vì không còn phù hợp: [CloudFormation change sets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-changesets.html). Snapshot AVAILABLE trước execute là lịch sử, không tiếp tục ghi AVAILABLE sau triển khai.

## Kiểm tra read-only sau CREATE

| Thành phần | Kết quả |
|---|---|
| Lambda | Ba functions Active / LastUpdateStatus Successful; CodeSha256 giải mã khớp ZIP SHA-256 đã duyệt |
| IAM | Ba roles: không managed policy, không inline Allow Resource `*`; logging grants chỉ CreateLogStream/PutLogEvents ở log groups test, khớp thiết kế đã duyệt |
| S3 | Cả hai bucket versioning Enabled, AES256, bốn public-access-block bật, HTTPS Deny hiện hữu |
| DynamoDB | Hai bảng ACTIVE; ByOwner/ByStatus ACTIVE; item count snapshot 0 (không seed dữ liệu) |
| Cognito | Pool tạo xong; estimated users 0; không tạo users hay gửi invitation |
| SQS | Queue chính visibility 180 giây/maxReceiveCount 3; DLQ retention 14 ngày, byQueue chỉ queue test; không gửi message |
| Event mapping | Enabled, BatchSize 1, ReportBatchItemFailures; chưa chứng minh retry/partial failure/DLQ runtime |
| API Gateway | HTTP API và stage Prod auto-deploy tạo xong; không gọi endpoint để thử nghiệp vụ |
| CloudFront | Deployed, Enabled, redirect-to-https; frontend chưa publish |
| CloudWatch | Ba log groups retention 30 ngày, dashboard hiện hữu; năm alarms OK lúc đọc; không phải bằng chứng alarm delivery/runtime thành công |
| Stack cũ | UPDATE_COMPLETE, LastUpdatedTime vẫn 2026-10-19 11:10:29.038 UTC; không thao tác ghi stack cũ; chưa có full drift detection |

Các resource vận hành tự động đã được bật bởi template (scheduled recovery rule và queue mapping). Không có manual Lambda invoke, SQS send hoặc E2E từ agent; hoạt động tự động của hạ tầng không được tính thành AWS E2E PASS.

## Outputs đã lọc

Chỉ URL công khai của infrastructure được hiển thị dưới đây; không có signed URL, JWT, credentials, ARN/account ID đầy đủ. IDs và tên tài nguyên phục vụ vận hành được giữ trong Console/private mapping, không đưa vào báo cáo public.

- FrontendUrl: `https://d3ataim7dfsl7t.cloudfront.net` — infrastructure output, chưa là demo đã kiểm chứng.
- PolicyAssistantApiUrl: `https://u02lf7tfb0.execute-api.ap-southeast-1.amazonaws.com/Prod/` — infrastructure output, chưa là demo đã kiểm chứng.

Outputs khác gồm Cognito pool/client, buckets, distribution ID, SNS topic, function/role ARN và PoliciesTableName: **REDACTED**, xem Console được cấp quyền. Không truy cập frontend để giả định app đã hoạt động.

## Budget và chi phí

Đọc lại sau CREATE: COST/MONTHLY/fixed **20 USD**, UnblendedCost, loại Credit/Refund, không filter region/service/tag; đúng ACTUAL 80%, ACTUAL 100%, FORECASTED 100%, states OK; không Budget Actions. AWS hiện có thể bỏ ThresholdType khỏi DescribeNotifications; bằng chứng CloudTrail trước đó xác nhận PERCENTAGE. Không sửa Budget hay Billing. Recipient vẫn theo xác nhận người dùng Active (legacy), verification 0/1; DELIVERY_NOT_VERIFIED.

CE vừa đọc trước execute khoảng **09:36:36–09:36:37 UTC**: actual 01–20/10 **5,4222749168 USD**, remaining DAILY forecast 21–31/10 **3,1167914980 USD**; baseline cả tháng **8,5390664148 USD**. Snapshot Budget sau CREATE hiển thị actual **5,422 USD**, forecast **8,539 USD**. Đây không phải chi phí đo được của stack vừa tạo, không bao gồm ngày hiện tại hoàn chỉnh và chịu độ trễ Billing. Không query lại CE ngay sau vài phút để giả định có số đo mới.

Mô hình test đủ tháng **6,6305950965 USD**, combined planning **15,1696615113 USD**, không phải AWS forecast workload test. Budget không hard cap; tax/support/điều chỉnh, dịch vụ chung và dữ liệu Retain cần theo dõi. Số tháng thực tế phụ thuộc thời gian tồn tại và usage, không hứa chính xác 6,63 USD.

## Retain, rollback và rủi ro

Đã đọc deployed template xác nhận DeletionPolicy/UpdateReplacePolicy Retain trên **PoliciesTable, DocumentMetadata, PolicyAssistantDocumentsBucket, DocumentsBucketTlsPolicy**. Không thử xóa stack/bucket để chứng minh. Nếu cleanup sau này, bảo vệ HTTPS phải còn cùng bucket; lưu trữ có thể tiếp tục tính phí. Shared artifacts nằm ngoài stack. Frontend bucket versioned sau publish cần kế hoạch xử lý versions/delete markers được duyệt riêng.

Không xảy ra rollback trong B1. Nếu bước app tiếp theo lỗi, không có automatic CloudFormation rollback cho lỗi E2E; dừng và chuẩn bị sửa đổi/test-only plan cần duyệt, không sửa IAM/production hoặc tự xóa. [Quy trình cleanup](cleanup-retained-data.md).

## Quyết định cho bước kế tiếp

**GO để người dùng xem xét B2; NO-GO thực thi B2 cho đến khi có phê duyệt riêng.** Infrastructure/control-plane đủ điều kiện chuẩn bị frontend. B2 chỉ publish đúng bốn assets `index.html`, `app.js`, `styles.css`, `config.json` vào FrontendBucket mới, bind public API/client configuration từ outputs test và invalidate đúng assets đó; kiểm tra target và asset diff trước write. Không đưa password/JWT vào config, không chỉnh backend hoặc stack.

- **B2: PENDING_USER_APPROVAL** — frontend chưa publish.
- **B3: PENDING_USER_APPROVAL** — hai Cognito test users chưa tạo.
- **B4: PENDING_USER_APPROVAL / NOT_RUN** — synthetic policies, uploads/API và retry/DLQ chưa chạy.
- **Cleanup/Retain deletion: NOT_AUTHORIZED** — cần Approval C riêng.
- Không commit/push, không gửi test messages, không upload test data.

## Danh sách tài nguyên đã tạo

| Logical ID | Loại | Trạng thái |
|---|---|---|
| AlertTopic | AWS::SNS::Topic | CREATE_COMPLETE |
| DocumentDLQAlarm | AWS::CloudWatch::Alarm | CREATE_COMPLETE |
| DocumentMetadata | AWS::DynamoDB::Table | CREATE_COMPLETE |
| DocumentQueueAgeAlarm | AWS::CloudWatch::Alarm | CREATE_COMPLETE |
| DocumentRecovery | AWS::Lambda::Function | CREATE_COMPLETE |
| DocumentRecoveryLogWritePolicy | AWS::IAM::Policy | CREATE_COMPLETE |
| DocumentRecoveryLogs | AWS::Logs::LogGroup | CREATE_COMPLETE |
| DocumentRecoveryRecoverPending | AWS::Events::Rule | CREATE_COMPLETE |
| DocumentRecoveryRecoverPendingPermission | AWS::Lambda::Permission | CREATE_COMPLETE |
| DocumentRecoveryRole | AWS::IAM::Role | CREATE_COMPLETE |
| DocumentsBucketTlsPolicy | AWS::S3::BucketPolicy | CREATE_COMPLETE |
| FrontendAccessControl | AWS::CloudFront::OriginAccessControl | CREATE_COMPLETE |
| FrontendBucket | AWS::S3::Bucket | CREATE_COMPLETE |
| FrontendBucketPolicy | AWS::S3::BucketPolicy | CREATE_COMPLETE |
| FrontendDistribution | AWS::CloudFront::Distribution | CREATE_COMPLETE |
| FrontendHeaders | AWS::CloudFront::ResponseHeadersPolicy | CREATE_COMPLETE |
| PoliciesTable | AWS::DynamoDB::Table | CREATE_COMPLETE |
| PolicyAssistantApi | AWS::ApiGatewayV2::Api | CREATE_COMPLETE |
| PolicyAssistantApiProdStage | AWS::ApiGatewayV2::Stage | CREATE_COMPLETE |
| PolicyAssistantDashboard | AWS::CloudWatch::Dashboard | CREATE_COMPLETE |
| PolicyAssistantDocumentDLQ | AWS::SQS::Queue | CREATE_COMPLETE |
| PolicyAssistantDocumentQueue | AWS::SQS::Queue | CREATE_COMPLETE |
| PolicyAssistantDocumentsBucket | AWS::S3::Bucket | CREATE_COMPLETE |
| PolicyAssistantDurationAlarm | AWS::CloudWatch::Alarm | CREATE_COMPLETE |
| PolicyAssistantErrorAlarm | AWS::CloudWatch::Alarm | CREATE_COMPLETE |
| PolicyAssistantFunction | AWS::Lambda::Function | CREATE_COMPLETE |
| PolicyAssistantFunctionDocumentDownloadPermission | AWS::Lambda::Permission | CREATE_COMPLETE |
| PolicyAssistantFunctionDocumentStatusPermission | AWS::Lambda::Permission | CREATE_COMPLETE |
| PolicyAssistantFunctionGetPolicyByIdPermission | AWS::Lambda::Permission | CREATE_COMPLETE |
| PolicyAssistantFunctionHealthCheckPermission | AWS::Lambda::Permission | CREATE_COMPLETE |
| PolicyAssistantFunctionListDocumentsPermission | AWS::Lambda::Permission | CREATE_COMPLETE |
| PolicyAssistantFunctionLogWritePolicy | AWS::IAM::Policy | CREATE_COMPLETE |
| PolicyAssistantFunctionRole | AWS::IAM::Role | CREATE_COMPLETE |
| PolicyAssistantFunctionSearchPoliciesPermission | AWS::Lambda::Permission | CREATE_COMPLETE |
| PolicyAssistantFunctionSubmitDocumentPermission | AWS::Lambda::Permission | CREATE_COMPLETE |
| PolicyAssistantFunctionUploadSessionPermission | AWS::Lambda::Permission | CREATE_COMPLETE |
| PolicyAssistantLogGroup | AWS::Logs::LogGroup | CREATE_COMPLETE |
| PolicyAssistantUserPool | AWS::Cognito::UserPool | CREATE_COMPLETE |
| PolicyAssistantUserPoolClient | AWS::Cognito::UserPoolClient | CREATE_COMPLETE |
| PolicyAssistantWorker | AWS::Lambda::Function | CREATE_COMPLETE |
| PolicyAssistantWorkerDocumentQueueEvent | AWS::Lambda::EventSourceMapping | CREATE_COMPLETE |
| PolicyAssistantWorkerLogGroup | AWS::Logs::LogGroup | CREATE_COMPLETE |
| PolicyAssistantWorkerLogWritePolicy | AWS::IAM::Policy | CREATE_COMPLETE |
| PolicyAssistantWorkerRole | AWS::IAM::Role | CREATE_COMPLETE |
| RecoveryErrorAlarm | AWS::CloudWatch::Alarm | CREATE_COMPLETE |
