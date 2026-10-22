> Latest B5-R6: API-only set B5-R5 đã execute sau approval riêng; UPDATE_COMPLETE. Shared B5-R2 set không execute. [Deployment result](browser-b5r6-deployment-result.md).

> B5-R5: API-only set mới AVAILABLE; default2Modify gồm API Body nên NO-GO theo strict scope. Set cũ vẫn AVAILABLE. [Review mới](browser-b5r5-change-set-review.md).

> B5-R4: khuyến nghị API-only CodeUri ở mức chuẩn bị candidate; current set vẫn NO-GO execute. [Strategy review](browser-b5r4-minimal-update-review.md).

> B5-R3: NO-GO giữ nguyên. Xem [impact audit](browser-b5r3-impact-audit.md): default6/detailed3, chưa loại trừ permission lifecycle risk.

# B5-R2 — artifact và UPDATE change set review

**NO-GO execute: actual plan vượt phạm vi đã duyệt. Change set CREATED_NOT_EXECUTED.**

## Xác minh

Thời gian UTC: 2026-10-21T17:48:50.055474+00:00 → 2026-10-21T17:49:49.669013+00:00 (00:48–00:49 ngày 22/10/2026 UTC+7).
STS xác minh account …0098; tất cả client dùng ap-southeast-1. Stack test policy-assistant-fcaj-test CREATE_COMPLETE trước/sau, không deploy. Stack cũ policy-assistant UPDATE_COMPLETE, LastUpdatedTime vẫn 2026-10-19 11:10:29.038000+00:00. Chỉ đối chiếu metadata/template, không chạy drift detection hoặc khẳng định đã kiểm tra mọi runtime property.

Git working tree chứa nhiều thay đổi từ các giai đoạn trước; đã giữ nguyên. Incremental runtime diff so với ZIP deployed chỉ một dòng Config thêm virtual addressing. Source-pair SHA-256 `e16c8529fdc8fe2fde6d20714699a19ce5ff8af5c962fd8e68021f2e7e34fbea` khớp bản đã kiểm thử, template source không đổi. Build cả ba Lambda có 2.199 members, chỉ app.py khác artifact cũ; dependencies giữ nguyên. Original template AWS khớp packaged snapshot; processed deployed khớp snapshot.

## Artifact mới

Deployment bucket được lấy từ Code của processed template đang deploy, khớp cấu hình review thực tế; kiểm tra owner và region. Không suy đoán bucket. Key được HeadObject xác nhận chưa tồn tại; PutObject đúng một lần với IfNoneMatch=* và checksum SHA256. Không ghi đè artifact cũ.

Object key:
`policy-assistant-fcaj-test/reviews/fcaj-b5r2-20261021-174854-e16c8529/lambda-7c0228312d950a082c8efdd9ac0caeb8ba6a51c31b32d47c782e42ecea934bcd.zip`

SHA-256 nội dung ZIP tải lại:
`7c0228312d950a082c8efdd9ac0caeb8ba6a51c31b32d47c782e42ecea934bcd`

Kích thước: 16,731,316 bytes. Toàn bộ member hashes đọc lại khớp cả ba build. Bucket/full account và full change-set ARN giữ trong state local Gitignored, không cần đưa vào tài liệu public.

## Change set thực tế

Tên: `fcaj-b5r2-20261021-174854-e16c8529`

ID đã che account: `arn:aws:cloudformation:ap-southeast-1:********0098:changeSet/fcaj-b5r2-20261021-174854-e16c8529/17bb1e79-6bf3-49c9-accf-98dedf77273f`

Type UPDATE; CREATE_COMPLETE / AVAILABLE. Đã gọi CreateChangeSet đúng một lần. Không tạo set thứ hai, không execute hoặc xóa set này.

| Logical ID | Action / property | Replacement / evaluation |
|---|---|---|
| PolicyAssistantFunction | Modify Code | False / Static |
| PolicyAssistantWorker | Modify Code | False / Static |
| DocumentRecovery | Modify Code | False / Static |
| PolicyAssistantApi | Modify Body | False / Dynamic, Function.Arn |
| DocumentRecoveryRecoverPending | Modify Targets | False / Dynamic, Recovery.Arn |
| DocumentRecoveryRecoverPendingPermission | Modify SourceArn | **Conditional / Dynamic**, Rule.Arn, RequiresRecreation Always |

**0 Add, 6 Modify, 0 Remove; 0 Replacement True nhưng 1 Conditional.** Không được ghi thành “không replacement” hoặc “chỉ ba Modify”. CloudFormation liệt kê dependency evaluation; chưa execute nên không thể khẳng định các dynamic entries sẽ no-op.

Processed template so với live chỉ khác đúng ba Code S3 references. Tất cả phần khác bằng nhau, gồm IAM, resource-based Lambda permission declaration, S3 policies, SQS, DynamoDB, Cognito, CloudFront, parameters/outputs. Điều đó không loại bỏ actual plan Conditional replacement. Không có đổi CSP/CORS/public access/frontend/schema. Budget không nằm trong template và không có Budgets write.

## IAM và security

Static processed audit PASS; runtime Allow Resource exact `*`: **0**. Logging vẫn exact log-group Arn với CreateLogStream/PutLogEvents. Scoped wildcards giữ nguyên: streams trong log group, S3 uploads/*, routes trong API tương ứng. HTTPS Deny Principal */s3:* chỉ trên bucket được chỉ định; đây không phải Allow mở rộng. DLQ byQueue và bốn Retain/UpdateReplacePolicy Retain giữ nguyên.

Không mô phỏng effective permissions; không coi audit template là IAM runtime test. Lambda Permission Conditional trong plan vẫn là blocker phạm vi phê duyệt.

## Tests và giới hạn bằng chứng

Kế thừa lần verify local gần nhất 2026-10-21 17:42 UTC vì source/build fingerprint không đổi: 129 backend unit PASS; 17 frontend unit PASS; 3 browser fixture PASS; 1 full-stack local browser PASS; lint/typecheck/JS syntax, SAM validate --lint/build PASS. Chín live integration SKIPPED = NOT_RUN. Không chạy lại toàn bộ suite trong R2; fresh checks xác minh source, build-member hashes, uploaded bytes và AWS templates/plan.

B5 AWS vẫn FAIL; fix trên AWS UNKNOWN. Không đăng nhập, phát hành token, gọi API nghiệp vụ, upload PDF, gửi/nhận/xóa SQS hoặc reset alarm. Tên evidence approval-b5-e2e.json được yêu cầu không có trong checkout; dùng các evidence B5 hiện có, không tự tạo lại bằng chứng cũ.

## Cost, rollback và dữ liệu

Chưa thực thi nên chưa có code runtime mới; phát sinh một ZIP khoảng16 MiB và S3 PUT/GET/read requests, không hứa chi phí0. Không thêm infrastructure đang chạy. Budget20USD không hard cap; không sửa hoặc xác minh lại Billing trong vòng artifact preparation này.

Nếu dừng tại đây: giữ change set và artifact để review, không có runtime rollback cần thực hiện. Không xóa chúng nếu chưa duyệt. Nếu tương lai được duyệt execute, CloudFormation rollback theo kết quả update; không bảo đảm tự rollback khắc phục mọi lỗi runtime. Giữ old ZIP SHA2568ef709aa27ab22094b83071591f9cce1b546f78aebc3b5fd00b1ec257ab6d591 và template để chuẩn bị code rollback qua change set được duyệt riêng. Không rollback bằng direct Lambda update. Old code vẫn có browser endpoint mismatch.

PoliciesTable, DocumentMetadata, DocumentsBucket và DocumentsBucketTlsPolicy đều Retain: không xóa stack/retained data/policy. Metadata uploading B5, DLQ message B4 và dữ liệu test cũ giữ nguyên.

## Quyết định và bước cần duyệt riêng

**NO-GO execute theo B5-R2 hiện tại**: plan vượt tối đa ba Lambda Code và có Conditional replacement. Đề nghị review riêng ba dependency entries và rủi ro permission; không tự mở rộng approval hoặc đổi template để né guardrail. Mọi chuẩn bị change set khác cần phê duyệt mới; mọi execute cần approval riêng xác định actual six-resource plan nếu được chấp nhận.

Browser rerun sau deploy cũng cần approval riêng: hai users/hai PDF đã có, tối đa3login/3GlobalSignOut/2sessions/2uploads/2downloads, tổng128KiB,80requests,15phút; thu CSP hostname đã lọc, stop ngay cross-user/leak/sai scope. Không poison hoặc cleanup. Approval C riêng cho dữ liệu/DLQ/Retain.

ARTIFACT UPLOAD: VERIFIED

CHANGE SET: CREATED_NOT_EXECUTED

DEPLOYMENT: NOT_EXECUTED

BROWSER E2E RERUN: NOT_RUN

Không commit/push. DỪNG chờ phê duyệt riêng.

[Evidence JSON](evidence/b5r2-preparation.json).
