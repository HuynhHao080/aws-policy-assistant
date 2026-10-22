# Tóm tắt AWS Policy Assistant cho báo cáo thực tập

**Bản nháp local ngày 22/10/2026; dựa trên evidence đã lưu, không phải kiểm tra AWS mới.** Thông tin sinh viên, đơn vị/người hướng dẫn, thời gian thực tập, sơ đồ và minh chứng cá nhân: **CHỜ CHỦ DỰ ÁN BỔ SUNG**.

Dự án xây dựng ứng dụng serverless phục vụ tra cứu chính sách theo mã hoặc từ khóa và quản lý PDF riêng theo người dùng. Phạm vi xử lý tài liệu là kiểm kích thước/header, cố định phiên bản S3 và tính SHA-256; chưa triển khai OCR, AI/RAG, trích nội dung hoặc quét mã độc.

Frontend được phân phối qua CloudFront với private S3 origin. Cognito và API Gateway xác thực JWT; API Lambda kiểm quyền sở hữu theo subject. DynamoDB lưu policy và metadata; S3 lưu tài liệu có versioning; SQS/Worker xử lý bất đồng bộ, EventBridge/Recovery hỗ trợ khôi phục khoảng trống enqueue. DLQ, CloudWatch logs/metrics/alarms hỗ trợ phát hiện lỗi. Lựa chọn managed services phù hợp tải nhỏ, giảm quản trị máy chủ; không thêm VPC/NAT chỉ để tăng số dịch vụ.

Luồng chính: đăng nhập → search → tạo upload session → signed S3 POST → submit → theo dõi processing → download frozen version → đối chiếu hash. Ownership được kiểm ở backend; CORS hoặc việc ẩn nút trên UI không thay thế authorization.

Nghiệm thu AWS API/SDK B4 ghi nhận **19 PASS, 1 browser NOT_RUN**. Browser B5 ban đầu **FAIL upload** vì hostname presigner không phù hợp CSP regional. Bản sửa virtual S3 addressing được triển khai API-only, không nới IAM/CSP/CORS; Worker/Recovery giữ artifact cũ đã kiểm. Browser B5-R7 sau đó đạt **10/10 PASS**, bao gồm upload/processing/download/hash và ownership hai chiều qua UI. Đây là kết quả test có giới hạn, không phải load benchmark hay chứng nhận production.

Theo snapshot C0, môi trường có 45 CloudFormation resources, 4 Retain; cleanup chưa thực hiện. DLQ còn khoảng một diagnostic message/ALARM, SNS alarm topic chưa có subscriptions, Budget 20 USD/tháng chưa có bằng chứng email delivery. Ngày kết thúc duy trì môi trường chưa được chốt. Dự toán 6.6306 USD/tháng là mô hình tải trước ưu đãi đã lưu, không phải forecast AWS mới; Budget không giới hạn cứng chi tiêu.

Một credential-candidate legacy đã được xác minh public trong Git history. Mật khẩu hiện còn hiệu lực, rotation/revocation và unauthorized access chưa được chứng minh. D3-A đang **BLOCKED_PENDING_OWNER_OPERATIONAL_CONFIRMATION**; D3-A2 cung cấp checklist để chủ dự án xác nhận dependency trước containment. Vì vậy dự án có bằng chứng đáp ứng demo test, nhưng **public push và production vẫn NO-GO**. Không đưa credentials hoặc danh tính cá nhân vào báo cáo.

Bài học kỹ thuật: phải kiểm chứng cả browser và API; xử lý retry/duplicate và ownership tại backend; phân biệt snapshot với trạng thái trực tiếp; quản lý phiên bản artifact và tránh deploy mặc định vào legacy stack; xử lý credential exposure độc lập với việc xóa literals khỏi source.

Nguồn kiểm chứng: [B4](aws-test-e2e-b4-result.md), [B5 lịch sử](aws-browser-b5-result.md), [B5-R7](aws-browser-b5r7-result.md), [C0](cleanup-c0-inventory-and-acceptance.md), [D2](d2-secret-exposure-review.md), [D3-A2](d3a2-owner-operational-confirmation.md), [D4 readiness](d4-final-readiness-review.md).

Sinh viên cần tự vẽ/kiểm tra và giải thích sơ đồ bằng icon AWS chính thức; bổ sung nhật ký/ngày làm việc thật, thông tin cá nhân, blog/publication, ảnh sự kiện và office attendance có nguồn. Không biến bản nháp này thành tuyên bố các minh chứng đó đã tồn tại.
