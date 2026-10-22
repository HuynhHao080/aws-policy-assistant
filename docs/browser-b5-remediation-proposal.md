# B5 remediation proposal — chưa áp dụng

## B5-R — local fix đã kiểm chứng, chưa deploy

Edge local đã thu CSP connect-src violation với global S3 host; helper virtual addressing sinh regional POST/GET và fixture pipeline/hash PASS. Không đổi template/CSP/CORS/IAM/frontend. 129 backend,17 frontend,3 browser fixture,1 full-stack local PASS; SAM lint/build PASS;9 integration skip=NOT_RUN. [Hồ sơ B5-R](browser-b5r-remediation-review.md), [evidence](evidence/b5r-local-remediation.json).

B5 AWS vẫn FAIL. Chưa tạo change set vì artifact S3 mới đang bị cấm trong B5-R; cần duyệt upload/artifact/change set chưa execute, rồi execute/rerun riêng. Trạng thái chưa sửa local ở phần dưới là lịch sử B5.

**Status: PROPOSED_NOT_IMPLEMENTED.** Browser B5 FAIL sau session200, trước S3 upload. Evidence cấu hình chỉ ra likely mismatch giữa CSP regional-only và S3 global hostname do presigner sinh; raw CSP violation chưa capture. Không có app/source/IAM/AWS fix trong B5.

## Lựa chọn ưu tiên để xem xét

Tạo local patch cho helper `_s3()` để endpoint ký POST và GET được buộc về S3 regional ap-southeast-1 (virtual-hosted), phù hợp connect-src hiện tại. Giữ SigV4, MIME/length policy, version binding và IAM least privilege; không mở CSP thành *.amazonaws.com hoặc *.s3.amazonaws.com. Giải pháp cần kiểm tra download lẫn upload, CORS/SigV4 và target-bucket binding.

Regression có ý nghĩa: dùng fake signing credentials, không network để assert cả POST URL và GET presigned host regional; policy giữ application/pdf và10MiB; existing backend/frontend/browser-local suites; SAM validate/build; SHA artifacts và processed IAM audit. Đây là kế hoạch, chưa có regression test mới hoặc PASS được chạy cho bản sửa.

CodeUri shared bởi ba Lambda có thể khiến deployment update code cả ba functions; chỉ kết luận tài nguyên Modify/Replace sau khi có actual diff/change set mới được duyệt. Không suy đoán change set mới chỉ có một resource. Cần review stack test chính xác, IAM/data impact, costs và rollback; không deploy template vào policy-assistant cũ. Không tự tạo hoặc execute change set trong nhiệm vụ B5 này.

## Phương án thay thế

Giới hạn CSP thêm **exact test DocumentsBucket global host** bên cạnh regional host, thay vì wildcard mọi S3 bucket; không đổi IAM/runtime code. Cần review ResponseHeadersPolicy/CloudFront update qua IaC và ảnh hưởng signed POST/GET/CORS, không tự bật unsafe-* hoặc tắt CSP. Có thể giảm thay đổi runtime nhưng vẫn cho phép thêm endpoint; tradeoff phải được người dùng chọn sau diff. Chưa chuẩn bị patch hoặc cập nhật policy.

## Các phê duyệt độc lập còn thiếu

1. Cho phép sửa local implementation/tests theo phương án đã chọn, giữ nguyên thay đổi người dùng.
2. Sau diff/tests/IaC review: quyền chuẩn bị change set chưa execute nếu cần, rồi quyền deploy riêng cho test stack mới; không production.
3. Sau triển khai được kiểm chứng: quyền rerun B5 với counters mới, đúng hai B3 users và hai PDFs, không poison hoặc dùng quota cũ sau FAIL.
4. Approval C riêng cho orphan metadata B5, B4 fixtures/DLQ, users hoặc Retain cleanup; không gộp xóa vào fix.

Phiên TestA B5 chưa GlobalSignOut vì stop policy. Nếu cần revoke sớm, phải nêu riêng scope Cognito session của synthetic TestA; không tự password reset/user deletion. Credentials không có trong tài liệu và không yêu cầu gửi trong chat.
