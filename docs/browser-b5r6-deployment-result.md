> Latest B5-R7:10/10 browser cases PASS sau API fix, không đổi kết quả lịch sử B5. [R7 result](aws-browser-b5r7-result.md). Cleanup chưa thực hiện.

# B5-R6 — API-only execution result

**UPDATE_COMPLETE_VERIFIED. GO để xin approval Browser E2E rerun riêng; chưa nghiệm thu browser.**

## Identity và change set

Account STS …0098; region ap-southeast-1; stack policy-assistant-fcaj-test.
Name `fcaj-b5r5-api-20261021-182458-e16c8529`.
Exact ID được đối chiếu full ARN trong private state trước execute; bản public che account:
`arn:aws:cloudformation:ap-southeast-1:********0098:changeSet/fcaj-b5r5-api-20261021-182458-e16c8529/c202f831-b371-4326-8167-cc5f9fcac9c0`.
Suffix `c202f831-b371-4326-8167-cc5f9fcac9c0`. Full ARN giữ ở `.aws-sam/test-review/b5r5-pending-change-set.json` Gitignored và trong AWS Console được cấp quyền; không public full account.

Preflight khớp CREATE_COMPLETE/AVAILABLE, đúng StackId/account/region; hai view ResourceChanges và Details khớp B5-R5. Default chỉ2entries: Function.Code Static/False và API.Body Dynamic/False; detailed chỉ1Function.Code. Không Add/Remove/Conditional/True replacement hoặc resource khác. Source fingerprint khớp, processed candidate khớp snapshot, deployed/candidate chỉ API Code khác. SHA256 GetObject thực tế của API ZIP khớp `7c0228312d950a082c8efdd9ac0caeb8ba6a51c31b32d47c782e42ecea934bcd`.

## Timeline và CloudFormation events

| Mốc | UTC21/10/2026 | UTC+7 ngày22/10 |
|---|---|---|
| Preflight bắt đầu |18:28:43.653550 |01:28:43 |
| Execute requested |18:28:50.136088 |01:28:50 |
| Function UPDATE_IN_PROGRESS |18:28:54.712 |01:28:54 |
| Function UPDATE_COMPLETE |18:29:02.648 |01:29:02 |
| Stack UPDATE_COMPLETE_CLEANUP_IN_PROGRESS |18:29:07.585 |01:29:07 |
| Stack UPDATE_COMPLETE |18:29:08.445 |01:29:08 |
| Postflight kết thúc |18:29:15.974253 |01:29:15 |

Execute API accepted; **execute_attempt_count=1**, không retry/deploy khác. Stack đạt UPDATE_COMPLETE sau khoảng18giây tính từ request, được quan sát18:29:11UTC. Không thấy FAILED/ROLLBACK trong update window thu thập. Events kể từ execute response/local timestamp: chỉ API Lambda có resource update events; không có API Gateway event trong window. Không suy ra provider chắc chắn không gọi API Gateway chỉ vì không có event. API cấu hình/IDs trước-sau bằng nhau; không đo continuity bằng traffic nghiệp vụ nên không tuyên bố zero downtime.

Tên trạng thái CloudFormation CLEANUP_IN_PROGRESS là bước nội bộ CloudFormation; không có thao tác cleanup thủ công/data deletion do agent thực hiện.

## Code trước/sau

| Function | Trước | Sau |
|---|---|---|
| PolicyAssistantFunction | review fcaj-review-20261021-072124-24ba855e, key259348981e60d7d9a0fbbf28bc58643e | review fcaj-b5r2-20261021-174854-e16c8529, lambda-7c0228312d950a082c8efdd9ac0caeb8ba6a51c31b32d47c782e42ecea934bcd.zip |
| PolicyAssistantWorker | Old reference | **Chính xác old reference, không đổi** |
| DocumentRecovery | Old reference | **Chính xác old reference, không đổi** |

Đầy đủ S3Bucket/S3Key trước/sau trong evidence. API live Lambda CodeSha256 decode bằng SHA256 ZIP đã duyệt. Worker/Recovery live CodeSha256 và LastModified giữ nguyên; cả ba State Active/LastUpdateStatus Successful. Processed deployed sau update bằng candidate đã duyệt, không chỉ kiểm hash Lambda riêng lẻ.

## Postflight API, schedule và isolation

- API endpoint vẫn `https://u02lf7tfb0.execute-api.ap-southeast-1.amazonaws.com`; ApiId, routes, authorizer và integrations full snapshots bằng nhau trước/sau. Cùng Lambda test/Cognito test. Không gọi endpoint nghiệp vụ hoặc login.
- EventBridge rule schedule/state/targets, rule ARN và exact Lambda permission statement Sid/Principal/Action/Resource/Condition bằng nhau trước/sau. Không recreate permission quan sát được qua statement/config; không khẳng định đã audit toàn bộ service API execution history.
- Worker/Recovery resources và Code refs không đổi. Stack cũ policy-assistant LastUpdatedTime vẫn2026-10-19 11:10:29.038000+00:00, metadata trước/sau khớp; không phải full production drift audit.
- Không execute set B5-R2 cũ, không tạo set mới/upload thêm hoặc thay frontend. Không phát hành tokens, uploadPDF, gửi/receive/deleteSQS, Cognito/Budget/IAM writes hay commit/push.

## Observability và Budget

Main queue: visible0/not-visible0/delayed0. DLQ: visible1/not-visible0/delayed0. SQS counters approximate; không ReceiveMessage nên không chứng minh identity/body của message trong R6. Phù hợp baseline một diagnostic message B4; không xóa.

Alarms: DLQ **ALARM**, queue-age **OK**, Duration **OK**, Errors **OK**, RecoveryError **OK**. DLQ reason vẫn datapoint1 vượt0. Một số OK do missing data treated non-breaching, không coi là đã đo workload mới thành công. Không reset alarms.

Budget policy-assistant-account-monthly COST/MONTHLY **20USD**, ba notifications ACTUAL80/ACTUAL100/FORECASTED100, trạng thái OK. Snapshot AWS trả actual5.479USD, forecast8.539USD; Billing có độ trễ, không phải chi phí riêng update và không chứng minh không phát sinh phí mới. API response này không trả CostTypes/CostFilters; không suy đoán full metric/filter verification từ trường null. Không sửa Budget hoặc đọc recipients. Email verification không kiểm lại; **delivery NOT_VERIFIED**. Budget không hard spending cap.

## Decision, residual risks và quyền tiếp theo

**GO để xin phê duyệt một Browser E2E rerun có giới hạn**, không tự chạy và không ghi B5 PASS. Backend deployment/code hash VERIFIED; fix tạo presigned regional URLs trên browser AWS vẫn UNKNOWN tới rerun. B5 FAIL lịch sử giữ nguyên.

Đề xuất rerun riêng: tối đa3login/3GlobalSignOut,2sessions/2uploads/2downloads,128KiB tổng,80application requests,15phút; chỉ hai users và PDF tổng hợp hiện có, guard account/config, DPAPI secrets trong memory, không signed URL/HAR/JWT log. Stop khi cross-user/leak/sai scope/limit/IAM errors. Không poison message. Giữ baseline DLQ1/ALARM, không nhầm là fault mới nếu không có bằng chứng. Cleanup/Retain tiếp tục approval C riêng.

Nếu runtime/browser vẫn lỗi, dừng và trình phương án riêng; không tự sửa/redeploy/rollback. Giữ old artifact cho rollback CodeUri qua plan/approval độc lập, API dependency có thể xuất hiện lại. Không migration/schema/Retain changes; orphan metadata và dữ liệu B4/B5 giữ nguyên.

DEPLOYMENT: UPDATE_COMPLETE_VERIFIED.

BROWSER E2E RERUN: NOT_RUN.

CLEANUP: NOT_EXECUTED.

COMMIT/PUSH: NOT_EXECUTED.

[Evidence JSON đã che account](evidence/b5r6-execution.json). DỪNG chờ approval riêng.
