# B5-R3 — Read-only impact audit

**NO-GO EXECUTE. AWS writes: 0.**

STS xác minh account …0098, ap-southeast-1. Stack test CREATE_COMPLETE; change set `fcaj-b5r2-20261021-174854-e16c8529` CREATE_COMPLETE / AVAILABLE. Kiểm tra kết thúc 2026-10-21T17:55:48.694960+00:00 UTC, tức 00:55 ngày22/10 UTC+7; thời điểm chính xác trong evidence.

## Template, artifact và Lambda

Original deployed/candidate chỉ khác ba CodeUri. Processed chỉ khác ba Code.S3Key; cùng bucket. Snapshot deployed và candidate B5-R2 khớp AWS đọc lại. Không coi đây là kiểm tra mọi historical template version hoặc full drift detection.

GetObject đọc lại 16.731.316bytes; SHA256 `7c0228312d950a082c8efdd9ac0caeb8ba6a51c31b32d47c782e42ecea934bcd` khớp artifact B5-R2. Ba Lambda đều tham chiếu đúng object. Không upload mới.

Ba Lambda Active/LastUpdateStatus Successful, Python3.12, không layers. Non-code properties deployed/candidate bằng nhau. Runtime, handler, timeout, memory live khớp template; role/environment live khớp resolved BeforeContext; BeforeContext/AfterContext bỏ Code bằng nhau.

| Lambda | Handler | Timeout / Memory |
|---|---|---|
| PolicyAssistantFunction | app.lambda_handler |10s /128MiB |
| PolicyAssistantWorker | app.worker_handler |30s /256MiB |
| DocumentRecovery | app.recovery_handler |60s /128MiB |

Event mapping declaration không đổi. Live worker mapping Enabled, BatchSize1, ReportBatchItemFailures; hai function còn lại không SQS mapping. Không khẳng định đã đối chiếu historical runtime mapping nếu không có baseline đó.

Static IAM audit PASS, tất cả AWS::IAM resources bằng nhau; exact Allow Resource `*`=0. Không có quyền mới trong template; không phải effective-permission audit toàn account.

## Hai phản hồi DescribeChangeSet

Default view vẫn có **6 Modify,0Add/Remove**, một Replacement Conditional. `IncludePropertyValues=true` trả **3 Modify Code**, tất cả Replacement False, kèm before/after resolved contexts. Đã lưu cả hai, không chọn một phản hồi để loại bỏ rủi ro của phản hồi kia.

AWS công bố enhanced visibility resolve references có giá trị biết trước deployment. Đây là giải thích phù hợp cho việc dependency entries không xuất hiện ở detailed view; không chứng minh provider chắc chắn không gọi update hoặc recreate permission.

## Sáu ResourceChanges — default view

Mọi Action là Modify. PhysicalResourceId, Details đầy đủ và contexts nằm trong evidence JSON. ACCEPT dưới đây chỉ chấp nhận phạm vi code, không cấp phép execute.

| Logical ID / type | Replacement | ChangeSource / Evaluation | Property; RequiresRecreation | Runtime impact | Confidence / quyết định |
|---|---|---|---|---|---|
| PolicyAssistantFunction / AWS::Lambda::Function | False | DirectModification / Static | Code; Never | API handler code mới, có rủi ro lỗi runtime | HIGH scope; ACCEPT |
| PolicyAssistantWorker / AWS::Lambda::Function | False | DirectModification / Static | Code; Never | Worker code mới; mapping không đổi | HIGH scope; ACCEPT |
| DocumentRecovery / AWS::Lambda::Function | False | DirectModification / Static | Code; Never | Recovery code mới theo lịch | HIGH scope; ACCEPT |
| PolicyAssistantApi / AWS::ApiGatewayV2::Api | False | ResourceAttribute / Dynamic | Body; Never; Cause PolicyAssistantFunction.Arn | Không declaration diff; chưa chứng minh update propagation không gián đoạn | HIGH configuration; UNKNOWN runtime |
| DocumentRecoveryRecoverPending / AWS::Events::Rule | False | ResourceAttribute / Dynamic | Targets; Never; Cause DocumentRecovery.Arn | Target không đổi theo declaration; invocation continuity chưa chứng minh | HIGH configuration; UNKNOWN runtime |
| DocumentRecoveryRecoverPendingPermission / AWS::Lambda::Permission | Conditional | ResourceAttribute / Dynamic | SourceArn; Always; Cause DocumentRecoveryRecoverPending.Arn | Có thể recreate statement, invocation bị deny hoặc rollback lỗi | HIGH plan; BLOCK |

## API Gateway

Live ApiId `u02lf7tfb0` khớp stack resource và PhysicalResourceId. Tám routes: GET /health NONE, bảy routes nghiệp vụ JWT, cùng authorizer Cognito test. Tám integrations AWS_PROXY/payload2.0 cùng trỏ ARN PolicyAssistantFunction test. Stage Prod AutoDeploy=true, deployment5ie9z1. Tên Prod là stage trong test stack, không phải stack cũ.

Body và toàn bộ API properties deployed/candidate bằng nhau; Modify xuất phát Function.Arn dependency, không direct Body edit. Lambda Replacement False nên ARN dự kiến ổn định; không dự kiến đổi endpoint identity, routes, authorizer hoặc integration declaration. Nếu provider reapply Body, vẫn có propagation risk, nhất là AutoDeploy. Chưa có execution trace để chứng minh zero interruption hoặc IDs không đổi xuyên update. **UNKNOWN phần gián đoạn**, không khẳng định có outage.

## EventBridge Rule

Physical rule `policy-assistant-fcaj-tes-DocumentRecoveryRecoverPe-wZYhuInXzabX`; default bus, rate(2 minutes), ENABLED. Một target Id DocumentRecoveryRecoverPendingLambdaTarget, live ARN đúng DocumentRecovery test. Không RoleArn/Input/RetryPolicy/DeadLetterConfig được trả cho target; không ghi nhận đã cấu hình retry/DLQ riêng của EventBridge.

Schedule/state/target declaration bằng nhau trước/sau; dynamic Cause Recovery.Arn. Lambda không replacement nên target ARN dự kiến ổn định. Không chứng minh được zero missed/denied invocation quanh update bằng current configuration. Không invoke để thử.

## Lambda Permission

PhysicalResourceId/Statement Sid:
`policy-assistant-fcaj-test-DocumentRecoveryRecoverPendingPermission-2vtk9ji5k3ZS`.

GetPolicy tìm duy nhất Sid này trên DocumentRecovery. Effect Allow, Principal events.amazonaws.com, Action lambda:InvokeFunction; Resource đúng function test. Condition ArnLike AWS:SourceArn bằng live rule ARN. Template FunctionName Ref DocumentRecovery. **SourceAccount vắng mặt trong template lẫn live statement**; exact SourceArn đã chứa account/region, không phải permission mở cho mọi rule. Không sửa policy trong audit.

SourceArn declaration trước/sau giống nhau. Nhưng default plan vẫn Dynamic + RequiresRecreation Always => Conditional replacement. AWS resource spec quy định thay đổi SourceArn cần replacement. Nếu recreate, chưa biết thứ tự add/remove hoặc khoảng trống quyền; invocation có thể AccessDenied, recovery trễ; không bảo đảm service retries khắc phục. Add permission hoặc rollback cũng có thể thất bại. Resource-based permission lifecycle risk này khác execution-role expansion và không được coi là an toàn mặc định.

## So sánh phương án

| Phương án | Lợi ích / bằng chứng | Giới hạn / quyết định |
|---|---|---|
| A: giữ set và xin duyệt sáu entries | Template chỉ Code; bindings live đúng; enhanced view còn3Code | Chưa loại Conditional replacement hoặc chứng minh API/EventBridge continuity. **Chưa khuyến nghị A để execute** |
| B: giảm scope đóng gói | Có thể nghiên cứu API-only CodeUri, giữ worker/recovery artifact cũ để giảm chain Recovery→Rule→Permission | Cần call-graph/tests chứng minh API-only đủ; API Body dependency có thể vẫn còn. Chỉ đổi ZIP compression/key không giải quyết graph. Chưa sửa hoặc tạo artifact/set |

Đề xuất B **ở mức nghiên cứu local được phê duyệt riêng**, không tự triển khai trong R3. Không pin ARN cứng, bỏ permission hoặc direct-update Lambda để che dependency/tạo drift. Không hứa plan mới chắc chắn chỉ ba entries.

## Quyết định và rollback

**NO-GO EXECUTE** theo điều kiện hiện tại: thiếu bằng chứng đủ để loại trừ hoặc phê duyệt rõ permission lifecycle/interruption risks. Không mở rộng B5-R2 ngầm. Không tạo change set mới hoặc thực hiện phương án B.

Chưa execute nên không cần runtime rollback; giữ artifact/set. Sau approval execute tương lai, CloudFormation rollback vẫn có thể lỗi permission/dependency. Giữ old artifact để lập rollback plan riêng; không direct Lambda update. Không đổi schema/Retain; metadata uploading/DLQ/dữ liệu cũ giữ nguyên. R3 không đọc lại Budget/Billing; không dùng số liệu cũ làm snapshot hiện tại.

## Sources và evidence

- [Enhanced visibility resolves references](https://aws.amazon.com/about-aws/whats-new/2024/04/aws-cloudformation-changesets-enhanced-change-visibility-deployments/).
- [ResourceChange Conditional semantics](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ResourceChange.html).
- [DescribeChangeSet](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeChangeSet.html).
- [Lambda Permission replacement](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-lambda-permission.html).

Nguồn chính thức đọc ngày22/10/2026 UTC+7. [Evidence đã che account](evidence/b5r3-impact-audit.json) lưu physical IDs, đủ ResourceChanges/default và detailed, live configurations, hash và giới hạn kết luận.

DEPLOYMENT: NOT_EXECUTED. BROWSER E2E: NOT_RUN. AWS WRITES:0. Không commit/push. DỪNG.
