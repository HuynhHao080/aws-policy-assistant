# Approval B — đề nghị triển khai test và E2E có giới hạn

## Trạng thái hiện hành — B5 browser FAIL, đã dừng

B5 chạy Edge thật lúc00:19:40–00:19:48 ngày22/10/2026 UTC+7: **2 PASS /1 FAIL /7 NOT_RUN**. Login/search TestA PASS; UI upload lỗi sau session200, chưa có S3 upload/download. Một metadata uploading còn lại; không rerun/fix/deploy/cleanup. Nguyên nhân khả dĩ CSP regional-only không khớp global S3 hostname của signer, chưa capture exact violation. [Báo cáo B5](aws-browser-b5-result.md), [phương án sửa chưa áp dụng](browser-b5-remediation-proposal.md).

**NO-GO browser acceptance.** B4 backend PASS là lịch sử riêng; không ghi browser PASS. Main queue0/QueueAge OK, DLQ1/ALARM, ba alarms Lambda OK. Mọi sửa/triển khai/rerun/cleanup cần duyệt riêng.

## Preparation B5 — read-only sau B4

00:07 ngày22/10/2026 UTC+7: main queue0, queue-age alarm tự OK; DLQ approx1 và DLQ ALARM, ba Lambda alarms OK. Không đọc lại message body, không nhận/xóa message hoặc test writes. [Hồ sơ B5](aws-browser-b5-approval.md) / [read-only evidence](evidence/approval-b5-readonly-review.json). Browser B5 NOT_RUN, chờ duyệt riêng; B4 dưới đây giữ như lịch sử.

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

## Preflight READ-ONLY mới nhất — 21/10/2026

**GO để trình duyệt; NO-GO thực thi vì Approval B chưa được cấp.** Cửa sổ API: **09:32:20–09:33:33 UTC** (16:32:20–16:33:33 Việt Nam). [Evidence preflight](evidence/approval-b-final-preflight-readonly.json).

| Hạng mục | Kết quả mới |
|---|---|
| STS / region | VERIFIED account …0098, ap-southeast-1 |
| Stack cũ | VERIFIED UPDATE_COMPLETE; LastUpdatedTime vẫn 19/10/2026 11:10:29.038 UTC |
| Giới hạn kiểm tra stack cũ | Không phát hiện thay đổi metadata; chưa chứng minh không có resource drift ngoài CloudFormation; không khởi chạy drift detection |
| Stack test | REVIEW_IN_PROGRESS — placeholder chưa deploy; khác với trạng thái change set |
| Exact change set | VERIFIED CREATE_COMPLETE / AVAILABLE; 45 Add, 0 Modify/Remove/Replace |
| Source | VERIFIED fingerprint candidate và 8 file manifest không thay đổi |
| Template | VERIFIED Original khớp package, Processed trực tiếp khớp snapshot và audit IAM/SQS/S3 |
| Lambda artifact | VERIFIED tải lại một ZIP dùng chung, full SHA-256 và 2.199 member khớp từng build của ba Lambda; hash không đổi |
| Budget | VERIFIED COST/MONTHLY/fixed 20 USD, UnblendedCost, loại Credit/Refund, toàn account; đúng ba notifications, không Actions |
| Email | Active (legacy), verification 0/1 theo xác nhận Console trước; không kiểm tra lại trạng thái email; DELIVERY_NOT_VERIFIED |
| AWS E2E / deploy | NOT_RUN / NOT_EXECUTED |
| BLOCKED | Không lỗi API trong vòng này; quyền thực thi chưa được cấp |

### Chi phí mới, không dùng lại snapshot cũ làm số liệu realtime

CE được gọi lại lúc **09:33:08 UTC**: chi phí 01–20/10 **5,4222749168 USD**, UnblendedCost loại Credit/Refund, Estimated=true; loại ngày UTC hiện tại và có độ trễ Billing. Forecast DAILY mới **09:33:32 UTC** cho 21–31/10: **3,1167914980 USD**, kiểm tra đủ 11 ngày và tổng DAILY khớp Total. Baseline cả tháng tính từ actual + remaining forecast: **8,5390664148 USD**. Cộng mô hình test đủ tháng **6,6305950965 USD** thành kịch bản **15,1696615113 USD**, không phải AWS forecast chính thức cho workload mới.

Tổng cộng **3 truy vấn CE**: một actual, một MONTHLY forecast probe, một DAILY forecast kiểm tra thêm. MONTHLY trả số giống forecast cả tháng nên không dùng nó làm forecast phần còn lại; kết quả probe được giữ trong evidence. Không phân bổ chi phí theo stack khi chưa có bằng chứng; không query group-by/resource thêm. Budget vẫn không phải hard cap; alert/delivery chưa được kiểm chứng thực tế.

### Các quyết định phê duyệt độc lập đề nghị

| Mã | Phạm vi cần người dùng phê duyệt | Hiện trạng |
|---|---|---|
| B1 | Execute đúng một change set `fcaj-review-20261021-072124-24ba855e`, stack test, account …0098, ap-southeast-1; 45 Add; automatic CREATE rollback theo cấu hình mặc định | CHƯA PHÊ DUYỆT |
| B2 | Publish đúng bốn assets frontend/config vào bucket test và invalidate các assets đó, sau stack readiness | CHƯA PHÊ DUYỆT |
| B3 | Tạo đúng hai Cognito test users ở pool mới, SUPPRESS invitation, không email/SMS, mật khẩu riêng không xuất evidence | CHƯA PHÊ DUYỆT |
| B4 | E2E dữ liệu tổng hợp: seed ba policies, login/ownership/upload/status/download, tối đa một poison message queue test, direct mixed-batch worker invoke, quan sát log/metric/alarms; tải tuần tự thấp | CHƯA PHÊ DUYỆT |
| C | Cleanup/DeleteStack, xóa dữ liệu/users/versions/artifacts hoặc bốn tài nguyên Retain | NGOÀI PHẠM VI B; cần hồ sơ/phê duyệt độc lập |

B4 phụ thuộc B1 và B3; browser E2E trên frontend CloudFront phụ thuộc thêm B2. Phê duyệt riêng B1 không cấp B2/B3/B4. Không ReceiveMessage DLQ, purge/redrive, fault production, IAM/concurrency/visibility change. Retry giữ visibility 180s/maxReceiveCount 3 và có thể chờ khoảng 15 phút; partial-batch direct invoke khác với SQS tự nhiên BatchSize=1.

Điều kiện dừng: account/candidate/hash/action mismatch, source thay đổi, quyền thiếu, timeout, throttling bất thường, lỗi ownership/chức năng chính; không tự mở rộng IAM hoặc sửa stack cũ. Khi CREATE thất bại chỉ quan sát automatic rollback; khi E2E lỗi sau CREATE_COMPLETE, dừng/giữ bằng chứng, không tự xóa. Bốn Retain: **PoliciesTable, DocumentMetadata, PolicyAssistantDocumentsBucket, DocumentsBucketTlsPolicy**; policy HTTPS phải còn cùng bucket. Shared artifacts ngoài stack tiếp tục tồn tại; lưu trữ có thể tiếp tục tính phí. Không xóa để thử Retain.

Các phần dưới giữ chi tiết thiết kế và lịch sử snapshot. Preflight này thay thế snapshot 09:18 cho trạng thái candidate; không cấp quyền triển khai. Nếu chờ lâu hoặc cấu hình thay đổi, kiểm tra lại identity/candidate/hash trước thao tác đã được duyệt.

**PREPARED_NOT_APPROVED — NO-GO thực thi cho đến khi người dùng phê duyệt riêng.**

## Candidate và bằng chứng

- Account …0098; region ap-southeast-1; chỉ stack `policy-assistant-fcaj-test`.
- Change set duy nhất đề nghị: `fcaj-review-20261021-072124-24ba855e`.
- Snapshot API gần nhất: **2026-10-21 09:18:37 UTC**, CREATE_COMPLETE / AVAILABLE, **45 Add, 0 Modify/Remove/Replace**. Không gọi lại AWS trong lần cập nhật tài liệu này; không coi snapshot là trạng thái thời gian thực.
- Fingerprint SHA-256 của template.yaml + policy_assistant/app.py được kiểm tra lại local, vẫn `24ba855eb69ff2f6ff251ac21c0202684f2c558a6753965d431ca9dce873e9f1`.
- Ba Lambda: ZIP thực tế đã được kiểm tra 08:07–08:09 UTC, SHA-256 `8ef709aa27ab22094b83071591f9cce1b546f78aebc3b5fd00b1ec257ab6d591`, 16.746.794 bytes; 2.199 member khớp từng build. Không thay ETag cho SHA-256; đây là bằng chứng chuẩn bị, không phải runtime.
- [Manifest B và 45 tài nguyên](evidence/approval-b-preparation.json), [snapshot candidate](evidence/aws-candidate-after-budget-readonly.json), [kiểm tra IAM](evidence/aws-test-iam-review.json), [artifact](evidence/aws-review-artifact-fingerprint.json).

## Phạm vi đề nghị người dùng phê duyệt

1. Execute đúng change set trên, chờ CREATE_COMPLETE; chấp nhận cơ chế automatic CREATE rollback của CloudFormation nếu tạo thất bại. Không áp dụng template cho stack `policy-assistant`.
2. Sau readiness: seed đúng ba policy tổng hợp vào bảng mới; publish đúng bốn frontend/config assets vào bucket frontend test và invalidate các assets đó. Không đưa credentials/token vào frontend.
3. Tạo hai Cognito test users trong pool mới, invitation SUPPRESS, mật khẩu sinh riêng không ghi báo cáo; không gửi email/SMS.
4. Chạy E2E thật tuần tự, tải thấp: đăng nhập hai người; policy search/pagination; upload PDF hợp lệ; kiểm tra ownership; quá kích thước, sai định dạng/chữ ký, token thiếu/sai; xử lý bất đồng bộ, status/download và SHA-256; frozen version và submit lặp lại.
5. Retry/DLQ: gửi **tối đa một** poison message vào queue chính test, lỗi trước thao tác dữ liệu; quan sát retry tự nhiên (visibility 180 giây, maxReceiveCount 3), chờ khoảng 15 phút và độ trễ metric để xác nhận DLQ. Không purge/redrive, không thay IAM/visibility/concurrency. Chỉ đọc DLQ attributes; ReceiveMessage có ảnh hưởng visibility không nằm trong phạm vi đề nghị này.
6. Gọi trực tiếp worker test với một mixed batch tổng hợp gồm record hợp lệ và lỗi để kiểm tra partial batch response bằng Lambda/dependencies thật. Phân biệt với SQS mapping thực tế BatchSize=1; không tuyên bố đã chứng minh batch nhiều record tự nhiên.
7. Đọc log/metric/dashboard/alarms test và kiểm tra browser/CORS/security headers. Queue message hợp lệ được Lambda acknowledge bình thường. Không chạy load test hoặc tác động stack cũ.

Chi tiết thao tác/kết quả mong đợi A01–A12: [kế hoạch E2E](aws-live-test-plan.md). Mọi test AWS hiện **NOT_RUN**; skip/mock/local pass không được tính AWS pass.

## Kiến trúc, IAM và cách ly

Ba Lambda + ba role + ba logging policy riêng; runtime Allow Resource `*`: **0** trong processed template đã kiểm tra. Wildcard còn lại giới hạn log streams của đúng group, object prefix đúng bucket và routes/stages đúng API; S3 Principal `*`/s3:* là HTTPS Deny, không phải Allow.

DLQ chỉ cho phép ARN queue chính test qua RedriveAllowPolicy byQueue. Bucket tài liệu cùng HTTPS Deny policy đều Retain. IAM hiệu lực và hoạt động runtime vẫn cần E2E sau duyệt. Không có cập nhật dữ liệu/tài nguyên stack cũ trong kế hoạch; account, billing và concurrency vẫn dùng chung. Giới hạn Lambda account lần gần nhất là 10: chạy tuần tự, dừng khi có throttling ngoài dự kiến.

## Chi phí và cảnh báo

Budget toàn account **20 USD/tháng VERIFIED**; Actual 80%=16 USD, Actual 100%=20 USD, Forecasted 100%=20 USD; không Actions. Recipient **Active (legacy)** theo Console người dùng; email verification **0/1**, delivery chưa có bằng chứng. Không gửi verification hoặc sửa notification. Budget 5 USD giữ nguyên; Budget tag 10 USD vẫn chờ.

Baseline tháng dự kiến 8,5391 USD, mô hình test đủ tháng 6,6306 USD; tổng kịch bản 15,1697 USD là phép lập kế hoạch, **không phải forecast AWS cho workload mới**. Test model chưa bao gồm chi phí stack cũ/dịch vụ dùng chung; cần xét riêng tax/support/điều chỉnh, lưu trữ Retain và artifact. Budget không là hard cap, không tự dừng tài nguyên; Billing/alerts có độ trễ và forecast thay đổi. [Cơ sở chi phí](budget-baseline-2026-10.md).

## Gate ngay trước thực thi sau khi được duyệt

- Xác minh lại STS exact account, region, exact stack/change set AVAILABLE và toàn bộ 45 Add; dừng nếu mismatch hoặc xuất hiện Modify/Remove/Replace.
- Đối chiếu source/build/package, processed template và artifact với bản được duyệt; kiểm tra quyền mà không tự sửa IAM. Timeout -> BLOCKED, không lặp vô hạn hoặc thực thi mù.
- Xác nhận phạm vi người dùng duyệt có đủ các thao tác E2E/frontend/users/queue ở trên; chỉ duyệt execute không tự mở rộng sang E2E.
- Đọc lại trạng thái stack cũ; không chọn nó làm target. Chờ roles/log policies/log groups, Lambda/mapping và indexes sẵn sàng trước test.
- Dừng khi permission/service blocker, bất thường ownership, lỗi cốt lõi hoặc throttling; lưu bằng chứng đã che thông tin. Không tự sửa production hoặc mở rộng IAM.

## Rollback và cleanup

CREATE thất bại: quan sát automatic CloudFormation rollback trong phạm vi test, không tự gọi DeleteStack. Khi đã CREATE_COMPLETE nhưng E2E thất bại: dừng và giữ bằng chứng; không giả định CloudFormation tự rollback lỗi ứng dụng.

**Bốn tài nguyên Retain/UpdateReplacePolicy Retain:** PoliciesTable, DocumentMetadata, PolicyAssistantDocumentsBucket, DocumentsBucketTlsPolicy. Chúng có thể tồn tại và phát sinh phí sau xóa stack; phải giữ HTTPS policy cùng bucket. Shared packaging artifacts ngoài stack cũng không tự mất. Frontend bucket có dữ liệu/version có thể làm cleanup thất bại. Mô hình retained stock khoảng 0,6649 USD/tháng là dự toán, không phải số đo sử dụng thực tế.

Cleanup/DeleteStack/xóa users, dữ liệu, object versions/delete markers, retained tables/bucket/policy hoặc artifact prefix cần **Approval C độc lập** kèm inventory/backup/phạm vi cụ thể. Không purge queue hoặc xóa để chứng minh Retain. [Hướng dẫn cleanup](cleanup-retained-data.md).

## Quyết định đề nghị

| Hạng mục | Trạng thái |
|---|---|
| Cấu hình Budget | VERIFIED; legacy Active do người dùng xác nhận |
| Email verification / delivery | 0/1; DELIVERY_NOT_VERIFIED — tiếp tục theo dõi |
| Candidate kỹ thuật | Snapshot đã xác minh; cần refresh trước execute |
| Approval B | PENDING_USER_APPROVAL — chưa có quyền execute/E2E |
| CloudFormation deployment | NOT_EXECUTED |
| AWS E2E | NOT_RUN |
| Cleanup / Budget writes / commit-push | NOT_AUTHORIZED |

Người dùng có thể phê duyệt riêng (B1) execute candidate và automatic CREATE rollback; (B2) các thao tác frontend, dữ liệu tổng hợp, hai users và E2E giới hạn ở trên. Hồ sơ này chỉ trình phạm vi để xem xét, không tự cấp cả hai quyền.

## Danh sách 45 Add và retention

| Logical ID | Loại | DeletionPolicy | UpdateReplacePolicy |
|---|---|---|---|
| AlertTopic | AWS::SNS::Topic | Delete (default) | Delete (default) |
| DocumentDLQAlarm | AWS::CloudWatch::Alarm | Delete (default) | Delete (default) |
| DocumentMetadata | AWS::DynamoDB::Table | Retain | Retain |
| DocumentQueueAgeAlarm | AWS::CloudWatch::Alarm | Delete (default) | Delete (default) |
| DocumentRecovery | AWS::Lambda::Function | Delete (default) | Delete (default) |
| DocumentRecoveryLogWritePolicy | AWS::IAM::Policy | Delete (default) | Delete (default) |
| DocumentRecoveryLogs | AWS::Logs::LogGroup | Delete (default) | Delete (default) |
| DocumentRecoveryRecoverPending | AWS::Events::Rule | Delete (default) | Delete (default) |
| DocumentRecoveryRecoverPendingPermission | AWS::Lambda::Permission | Delete (default) | Delete (default) |
| DocumentRecoveryRole | AWS::IAM::Role | Delete (default) | Delete (default) |
| DocumentsBucketTlsPolicy | AWS::S3::BucketPolicy | Retain | Retain |
| FrontendAccessControl | AWS::CloudFront::OriginAccessControl | Delete (default) | Delete (default) |
| FrontendBucket | AWS::S3::Bucket | Delete (default) | Delete (default) |
| FrontendBucketPolicy | AWS::S3::BucketPolicy | Delete (default) | Delete (default) |
| FrontendDistribution | AWS::CloudFront::Distribution | Delete (default) | Delete (default) |
| FrontendHeaders | AWS::CloudFront::ResponseHeadersPolicy | Delete (default) | Delete (default) |
| PoliciesTable | AWS::DynamoDB::Table | Retain | Retain |
| PolicyAssistantApi | AWS::ApiGatewayV2::Api | Delete (default) | Delete (default) |
| PolicyAssistantApiProdStage | AWS::ApiGatewayV2::Stage | Delete (default) | Delete (default) |
| PolicyAssistantDashboard | AWS::CloudWatch::Dashboard | Delete (default) | Delete (default) |
| PolicyAssistantDocumentDLQ | AWS::SQS::Queue | Delete (default) | Delete (default) |
| PolicyAssistantDocumentQueue | AWS::SQS::Queue | Delete (default) | Delete (default) |
| PolicyAssistantDocumentsBucket | AWS::S3::Bucket | Retain | Retain |
| PolicyAssistantDurationAlarm | AWS::CloudWatch::Alarm | Delete (default) | Delete (default) |
| PolicyAssistantErrorAlarm | AWS::CloudWatch::Alarm | Delete (default) | Delete (default) |
| PolicyAssistantFunction | AWS::Lambda::Function | Delete (default) | Delete (default) |
| PolicyAssistantFunctionDocumentDownloadPermission | AWS::Lambda::Permission | Delete (default) | Delete (default) |
| PolicyAssistantFunctionDocumentStatusPermission | AWS::Lambda::Permission | Delete (default) | Delete (default) |
| PolicyAssistantFunctionGetPolicyByIdPermission | AWS::Lambda::Permission | Delete (default) | Delete (default) |
| PolicyAssistantFunctionHealthCheckPermission | AWS::Lambda::Permission | Delete (default) | Delete (default) |
| PolicyAssistantFunctionListDocumentsPermission | AWS::Lambda::Permission | Delete (default) | Delete (default) |
| PolicyAssistantFunctionLogWritePolicy | AWS::IAM::Policy | Delete (default) | Delete (default) |
| PolicyAssistantFunctionRole | AWS::IAM::Role | Delete (default) | Delete (default) |
| PolicyAssistantFunctionSearchPoliciesPermission | AWS::Lambda::Permission | Delete (default) | Delete (default) |
| PolicyAssistantFunctionSubmitDocumentPermission | AWS::Lambda::Permission | Delete (default) | Delete (default) |
| PolicyAssistantFunctionUploadSessionPermission | AWS::Lambda::Permission | Delete (default) | Delete (default) |
| PolicyAssistantLogGroup | AWS::Logs::LogGroup | Delete (default) | Delete (default) |
| PolicyAssistantUserPool | AWS::Cognito::UserPool | Delete (default) | Delete (default) |
| PolicyAssistantUserPoolClient | AWS::Cognito::UserPoolClient | Delete (default) | Delete (default) |
| PolicyAssistantWorker | AWS::Lambda::Function | Delete (default) | Delete (default) |
| PolicyAssistantWorkerDocumentQueueEvent | AWS::Lambda::EventSourceMapping | Delete (default) | Delete (default) |
| PolicyAssistantWorkerLogGroup | AWS::Logs::LogGroup | Delete (default) | Delete (default) |
| PolicyAssistantWorkerLogWritePolicy | AWS::IAM::Policy | Delete (default) | Delete (default) |
| PolicyAssistantWorkerRole | AWS::IAM::Role | Delete (default) | Delete (default) |
| RecoveryErrorAlarm | AWS::CloudWatch::Alarm | Delete (default) | Delete (default) |
