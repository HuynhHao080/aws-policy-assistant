# D3-A2 — Bản xác nhận vận hành của chủ dự án

**PREPARED_PENDING_OWNER_RESPONSE. D3-A: BLOCKED_PENDING_OWNER_OPERATIONAL_CONFIRMATION.**

Ngày chuẩn bị: 2026-10-22. Chỉ dùng evidence D2, D3-A, D3-A1 đã lưu; không truy vấn lại AWS. Đối tượng duy nhất: **EXPOSED_LEGACY_IDENTITY_1**, thuộc legacy stack `policy-assistant`, account …0098, region `ap-southeast-1`, pool `ap-southeast-1_zzeu6TjQs`. Exact username/sub đã được đối chiếu trong D3-A/D3-A1; không đưa vào mẫu này. Không áp dụng cho TestA/TestB.

## Căn cứ và quy trình có thể bị gián đoạn

| Quy trình | Bằng chứng đã có / rủi ro nếu disable và sign-out | Người xác nhận |
|---|---|---|
| `get_token.py`, `verify_jwt.py` | HEAD 80c4eef dùng cùng identity/client để lấy token và chẩn đoán JWT/API; có đường ghi token local. Lần chạy tiếp theo có thể không đăng nhập được. Không khẳng định các đường này đã chạy. | Chủ dự án; người thực thi từng script chưa được gán tên trong hồ sơ đã đọc |
| `verify_search.py`, `verify_e2e.py` | Tham chiếu lịch sử cho search và upload/submit/status/download. Smoke test hoặc demo dùng identity này có thể gián đoạn. | Chủ dự án xác định operator nếu có |
| Demo/manual client gọi legacy API | Authorizer hiện dùng legacy pool/client theo snapshot D3-A1; chưa chứng minh bắt buộc dùng riêng identity này. | Chủ dự án / người phụ trách demo, chưa xác định cá nhân |
| Notebook, CLI, Task Scheduler, automation, người dùng khác ngoài GitHub | Chưa kiểm kê đầy đủ; có thể dùng credential hoặc phiên đã lưu. | Chủ dự án xác định người quản lý máy, job và client liên quan |
| CI ứng dụng và Pages worklog | Không thấy dependency trong workflow definitions đã kiểm tra; không đồng nghĩa mọi runtime job, secret hay automation bên ngoài đều đã được kiểm tra. | Chủ dự án xác định maintainer nếu khác mình |

**13 sự kiện InitiateAuth ngày 19/10/2026 khớp exact identity là bằng chứng yêu cầu xác thực trong quá khứ.** Sự kiện cuối lúc 18:06:53 UTC+7; không có errorCode được ghi nhận. Chúng **không tự chứng minh** đăng nhập hoàn tất, mật khẩu công khai đã được dùng/còn hiệu lực, hoạt động hợp pháp, hoặc dependency hiện tại. Thiếu log hay không có hoạt động mới không phải xác nhận “không còn dùng”. Các số liệu này là snapshot D3-A1, không phải kiểm tra AWS mới.

## Chủ dự án điền và xác nhận

Không gửi password, token, email hoặc exact username/sub. Dùng alias trên; có thể ghi vai trò thay tên cá nhân trong bản chia sẻ công khai.

| Câu hỏi | Chọn một / thông tin cần điền |
|---|---|
| Identity còn dùng cho demo legacy hoặc client thủ công không? | CÓ / KHÔNG / CHƯA RÕ; workflow và người phụ trách: ___ |
| Script/notebook/CLI ngoài GitHub hoặc trên máy khác còn sử dụng không? | CÓ / KHÔNG / CHƯA RÕ; vị trí theo vai trò, không chứa secrets: ___ |
| Automation, scheduled job hoặc người dùng khác còn phụ thuộc không? | CÓ / KHÔNG / CHƯA RÕ; người cần xác nhận: ___ |
| Nếu còn cần, có thể chuyển sang identity/phương thức xác thực thay thế không? | CÓ / KHÔNG / CHƯA RÕ / KHÔNG ÁP DỤNG; operator, kế hoạch, tiêu chí kiểm chứng và thời điểm dự kiến: ___ |
| Chấp nhận ngắt các phiên hiện tại của riêng identity này không? | CÓ / KHÔNG / CHƯA RÕ; khung giờ hoặc điều kiện: ___ |
| Đã lấy xác nhận từ mọi operator liên quan được biết chưa? | CÓ / CHƯA / KHÔNG ÁP DỤNG; vai trò còn thiếu: ___ |

Người chịu trách nhiệm xác nhận cuối: **chủ dự án**. Vai trò/người xác nhận: ___; thời điểm xác nhận và múi giờ: ___. Mọi ô hiện tại đều **chưa có câu trả lời**; không đánh dấu thay chủ dự án.

## Quyết định theo câu trả lời

| Trường hợp | Xử lý tiếp theo | Trạng thái D3-A |
|---|---|---|
| Không còn sử dụng, operator liên quan đã xác nhận và chấp nhận ngắt phiên | Trình xác nhận rõ ràng theo mẫu dưới để đề nghị tiếp tục đúng D3-A. Trước AWS write phải refresh account/pool/exact identity/IAM và các điều kiện preflight. | Chỉ xem xét tiếp tục sau xác nhận; D3-A2 không execute |
| Còn sử dụng | Lập bảng workflow → operator → phương thức thay thế → bước chuyển đổi → kiểm chứng → khung containment. Phương án không được dùng lại credential có khả năng lộ. Xin phê duyệt riêng cho mọi tạo identity/chỉnh cấu hình/kiểm thử; không thực hiện trong D3-A2. | BLOCKED tới khi chuyển đổi và chủ dự án xác nhận tác động |
| Chưa xác định, còn operator chưa trả lời, hoặc chưa chấp nhận ngắt phiên | Chủ dự án chỉ định người xác nhận từng workflow còn thiếu và thời hạn phản hồi. Không coi im lặng hoặc thiếu log là đồng ý. | BLOCKED |

## Mẫu phản hồi khi không còn sử dụng

> Tôi là chủ dự án và xác nhận EXPOSED_LEGACY_IDENTITY_1 không còn cần cho demo, script/notebook, automation hoặc người dùng khác trong phạm vi tôi quản lý và đã kiểm tra với các operator liên quan. Tôi chấp nhận ngắt các phiên của riêng identity này. Tôi đề nghị tiếp tục D3-A sau khi preflight được làm mới, chỉ AdminDisableUser và AdminUserGlobalSignOut trên exact legacy identity đã đối chiếu. Xác nhận này không cho phép reset password, xóa user, thay đổi identity khác, deploy, cleanup hoặc Git writes. Vai trò/người xác nhận: ___; thời điểm/múi giờ: ___.

Mẫu trên **chưa được chủ dự án điền/phê duyệt**. Không dùng mẫu này nếu còn workflow hoặc tác động chưa rõ. Cognito containment không bảo đảm mọi JWT được kiểm offline mất hiệu lực ngay; không suy ra unauthorized access đã được loại trừ.

Nguồn: [D2](d2-secret-exposure-review.md), [D3-A](d3a-containment-result.md), [D3-A1](d3a1-operational-dependency-assessment.md), [decision evidence](evidence/d3a1-dependency-summary.json).

**D3-A2: chỉ chuẩn bị tài liệu local. AWS calls 0; authentication 0; disable/sign-out/reset/create identity/deploy/cleanup/stage/commit/push/history rewrite NOT_EXECUTED. Dừng chờ xác nhận rõ ràng.**
