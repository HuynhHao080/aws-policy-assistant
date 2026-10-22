# Approval B3 — Cognito test users

**CREATED_VERIFIED — B3 hoàn tất. DỪNG; B4 chưa được phê duyệt.**

## Môi trường đã xác minh

- STS account **…0098**, region **ap-southeast-1**.
- Stack `policy-assistant-fcaj-test` **CREATE_COMPLETE**.
- User Pool ID: `ap-southeast-1_EfQPshNZ7` — khớp trực tiếp CloudFormation Outputs và resource PolicyAssistantUserPool của stack test.
- App Client ID khớp resource/outputs và DescribeUserPoolClient trong cùng pool; không client secret. Không dùng pool/client của stack cũ.
- Trước tạo: **0 user**, complete list. Sau tạo: **2 users**, complete list; không tạo trùng, không xóa hoặc thay user có sẵn.

## Users và trạng thái

| Danh tính báo cáo | Enabled | UserStatus sau cấu hình | Email verified | Phone |
|---|---|---|---|---|
| TestA | true | CONFIRMED | false | Không có |
| TestB | true | CONFIRMED | false | Không có |

Hai `sub` khác nhau đã được so sánh trong bộ nhớ; không xuất sub/username/email ra evidence public. Danh tính sử dụng địa chỉ tổng hợp miền `.invalid`, không dùng người thật. Hai users ban đầu FORCE_CHANGE_PASSWORD sau AdminCreateUser, được chuyển CONFIRMED bằng AdminSetUserPassword Permanent=True; **không qua đăng nhập**. CONFIRMED là trạng thái account, không phải email đã xác minh hay authentication đã chạy thành công.

AdminCreateUser dùng MessageAction **SUPPRESS**, không Resend/verification/reset APIs. Không gắn số điện thoại, không email_verified=true. Pool auto-verified email tồn tại nhưng đường admin-create được suppress và permanent password không yêu cầu gửi mã; không thay pool policies để bỏ kiểm tra. Không có Lambda triggers hoặc MFA trong cấu hình hiện tại. [AWS xác nhận permanent password cho phép chuyển CONFIRMED không cần first sign-in](https://docs.aws.amazon.com/cognito/latest/developerguide/how-to-create-user-accounts.html).

Thời gian UTC: **2026-10-21T16:37:32.961685+00:00 – 2026-10-21T16:37:37.414305+00:00** (21/10/2026, khoảng 23:37 UTC+7). Hai AdminCreateUser + hai AdminSetUserPassword; không retry, không delete.

## Chính sách mật khẩu và bảo vệ credentials

Pool yêu cầu tối thiểu 12 ký tự, uppercase/lowercase/numbers/symbols. Mỗi user có mật khẩu ngẫu nhiên 32 ký tự; temporary khác permanent. Passwords không đặt trong shell arguments, chat, public evidence hoặc source; SDK debug logs tắt, lỗi chỉ xuất type/code.

Permanent credentials được mã hóa **Windows DPAPI current-user scope** trước AWS writes; đã kiểm tra encrypt/decrypt roundtrip trong bộ nhớ. File ciphertext `.aws-sam/test-review/b3-private/credentials.dpapi` được Git ignore; NTFS directory inheritance tắt và file ACL đã xác minh chỉ Windows user hiện hành/SYSTEM. Không có file plaintext hoặc password hash công khai; dữ liệu transient trong bộ nhớ không được coi là đã zeroize bảo đảm. Windows user/session hoặc máy bị xâm nhập vẫn là rủi ro; DPAPI không thay thế quản lý truy cập máy.

Cho B4 sau khi được duyệt, tiến trình chạy dưới đúng Windows user có thể giải mã trong bộ nhớ, lấy username/password cho test rồi không xuất log. Không phải gửi password trong ChatGPT hoặc đưa vào frontend config. Chuyển máy/Windows profile cần phương án riêng, không tự export plaintext. Nếu không giải mã được, dừng; không tự reset hoặc tạo thêm users ngoài phạm vi.

## Kiểm chứng và giới hạn

- DescribeUserPool/Client, complete ListUsers, AdminGetUser read-only xác nhận Enabled/UserStatus/attributes và hai subjects khác nhau.
- Stack cũ sau B3 vẫn UPDATE_COMPLETE, LastUpdatedTime **2026-10-19 11:10:29.038 UTC**, không là write target. Không tạo user trong pool cũ hoặc sửa stack; metadata không là full resource drift scan.
- **Login/token issuance: NOT_RUN. AWS business E2E: NOT_RUN.** Không gọi API nghiệp vụ, upload tài liệu, gửi SQS, deploy frontend/CloudFormation hoặc thay IAM/Budget/Billing.
- Không kiểm chứng email delivery, không thử password reset. Không hứa đã xác minh đăng nhập chỉ vì CONFIRMED. Admin reads/user management có thể được phản ánh trong metering Cognito; chưa đo chi phí invoice mới.

## Điều kiện cho B4

**GO để xem xét B4; NO-GO chạy E2E cho đến phê duyệt riêng.** Cần người dùng duyệt rõ: login/phát hành tokens cho hai users tổng hợp, seed ba policies, luồng API/upload/status/download/ownership, tối đa một poison message queue test, direct mixed batch worker và đọc evidence. Các dữ liệu/users/queues/buckets đều phải xác minh target test trước chạy. Giữ guardrails tải thấp, retry/DLQ tự nhiên, không purge/redrive/IAM weakening hoặc production writes. Cleanup/Retain deletion vẫn cần Approval C riêng.

B1/B2 đã hoàn tất; credentials sẵn sàng dưới DPAPI cho tiến trình B4 được cấp quyền, nhưng chưa sử dụng để đăng nhập. Budget 20 USD không hard cap, email delivery Budget vẫn chưa được chứng minh. Không commit/push.

[Preflight evidence](evidence/approval-b3-preflight.json) · [Creation/read-back evidence](evidence/approval-b3-users.json).
