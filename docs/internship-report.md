# D1 — hiện trạng nghiệm thu ngày22/10/2026

B4 AWS API/SDK19PASS; B5 browserFAIL lịch sử; B5-R6 API-only UPDATE_COMPLETE; B5-R7 browser10PASS. C0:45resources/4Retain, GO demo test, NO-GO production. SNS0subscriptions; DLQ diagnostic1/ALARM; Budget20USD email delivery chưa xác minh. Chưa cleanup/commit/push; chủ dự án chưa chốt ngày kết thúc môi trường.

Local129backend/17frontend/3browserfixtures/1fullstack và1mixed-version private case R4 không thay bằng chứng AWS. Presigner virtual regional khắc phục browser upload, không mở IAM/CSP/CORS. Deployed API dùng ZIP mới, Worker/Recovery ZIP cũ. [D1 review](d1-handover-review.md), [R7](aws-browser-b5r7-result.md), [C0](cleanup-c0-inventory-and-acceptance.md).

Báo cáo cũ dưới đây là snapshot local ngày21/10, bao gồm các dòng chưa deploy/chưa live acceptance nay đã được supersede. Giữ để đối chiếu lịch sử; sử dụng bảng hiện trạng bên trên cho nghiệm thu. Student tự bổ sung minh chứng worklog/events/office và tự vẽ/giải thích architecture bằng icon chính thức.

## Snapshot kỹ thuật trước AWS acceptance

# Policy Assistant — báo cáo kỹ thuật thực tập FCAJ

Ngày cập nhật: 21/10/2026. Báo cáo này phản ánh mã nguồn local sau mốc bàn giao `80c4eef`; chưa push hoặc triển khai các thay đổi mới.

## 1. Bài toán và mục tiêu

Xây dựng MVP để tra cứu chính sách tổ chức, tìm kiếm theo từ khóa và tiếp nhận tài liệu PDF theo từng người dùng. Mục tiêu thực tập là thực hành serverless, Infrastructure as Code, phân quyền, xử lý bất đồng bộ và kiểm thử có minh chứng.

## 2. Phạm vi đã triển khai trong mã nguồn

- API tra cứu ID và tìm kiếm từ khóa trên dữ liệu chính sách mẫu.
- Cognito JWT Authorizer ở API Gateway, health endpoint công khai.
- Upload session gắn với người dùng; submit/status/download kiểm tra chủ sở hữu.
- S3 private/versioned; submit chốt version; SQS worker xác minh PDF và SHA-256; tải về đúng phiên bản.
- Frontend có đăng nhập Cognito, đổi mật khẩu lần đầu/MFA challenge, gia hạn và đăng xuất; token chỉ nằm trong bộ nhớ. Tài khoản do quản trị viên cấp, self-signup bị tắt trong template.
- Thư viện tài liệu theo owner với phân trang và tên file; polling, trạng thái lỗi và kiểm tra hash trước khi lưu PDF.
- Recovery Lambda theo lịch truy vấn pending index để bù khoảng trống ghi metadata/gửi queue; trạng thái failed phân biệt lỗi PDF và lỗi dịch vụ.
- Hosting private S3/CloudFront HTTPS, OAC, security headers và SNS alarm được định nghĩa trong SAM nhưng chưa triển khai.
- SAM template, CI tests/build, CloudWatch log/alarm/dashboard.

Chưa có AI/RAG, OCR, semantic search hoặc trích xuất nội dung chính sách. `processed` chỉ thể hiện xác minh byte/metadata, không đánh giá tính đúng đắn của nội dung PDF.

## 3. Kiến trúc và luồng xử lý

Frontend gửi JWT tới HTTP API. API Gateway xác thực JWT rồi truyền claims cho Lambda. Lambda dùng `sub` để gắn và kiểm tra owner. Chính sách nằm trong DynamoDB Policies; trạng thái tài liệu nằm trong Document Metadata.

Lambda tạo S3 key và signed POST policy theo session. Sau upload, submit kiểm tra object, size/content type rồi ghi version ID và timestamp UTC. Message SQS chứa document ID và submission_id; worker đọc metadata làm nguồn tin cậy, tải đúng version, kiểm tra PDF header/size và tính SHA-256. Khi xử lý thành công, API cấp presigned GET theo version đó. Frontend so file gốc, hash worker và file tải về trước khi lưu.

Worker để lỗi propagate cho SQS retry; message thành công lặp lại không reset dữ liệu. Nếu gửi queue thất bại, API trả 503; người dùng có thể submit lại cùng ID và giữ nguyên version. Xem sơ đồ `architecture.mmd`.

## 4. Bảo mật

Quyền truy cập tài liệu được kiểm tra ở backend, không dựa vào giao diện hoặc độ khó đoán của ID. Người dùng khác và record cũ không có owner nhận 404. Key do server lưu không bị client tự thay thế. S3 chặn public access, có mã hóa và versioning; worker có quyền đọc version cần thiết. Token chỉ giữ trong bộ nhớ frontend; script nhập mật khẩu không echo và không in token/URL.

Các mật khẩu từng bị commit cần được đổi. Xóa literal trong working tree không xóa lịch sử hoặc vô hiệu hóa bí mật cũ. Đợt này không thay đổi tài khoản AWS hoặc lịch sử Git.

## 5. Kiểm thử và kết quả

Kết quả chi tiết nằm trong `final-verification.md`: 120 unit tests pass trên Python 3.12.10; 17 frontend tests pass; 2 kịch bản browser pass trên Edge headless với API/S3 giả lập. Tests mới kiểm tra truy cập chéo user, version cố định, retry/idempotency, không bỏ sót trang và lỗi/hash frontend. 9 live integration tests skip theo cơ chế opt-in.

Ảnh full-stack desktop/mobile trong `evidence/` là minh chứng trình duyệt đi qua backend thật của ứng dụng với AWS/auth local giả lập. Có thêm kịch bản kiểm lỗi bằng fixture HTTP độc lập. Chưa tái kiểm chứng stack, IAM/JWT/CORS hoặc DLQ trên AWS cho thay đổi mới; không dùng kết quả mock để tuyên bố live E2E thành công.

## 6. Giới hạn và vận hành

DynamoDB Scan phù hợp dataset nhỏ, tối đa 1.000 item được đánh giá mỗi request; không đảm bảo snapshot khi dữ liệu thay đổi giữa các trang. Metadata/queue không có transaction chung; retry và recovery index theo lịch đảm bảo tiếp tục xử lý khi dịch vụ hồi phục, không phải transaction phân tán. Worker ghi failed khi PDF không hợp lệ hoặc hết lượt retry; trong sự cố metadata vẫn cần operator điều tra DLQ. Signed POST ràng buộc key/MIME/size tại S3; cần kiểm chứng enforcement trên AWS thật. Alarm nối SNS topic và hỗ trợ email tùy chọn cần chủ sở hữu xác nhận. Hosting HTTPS/CORS có cấu hình CloudFront nhưng chưa test live; S3 current/noncurrent expiry lần lượt 365 ngày; version có thể còn khoảng 730 ngày.

Đã có dự toán tải giả định có đơn giá AWS ngày 21/10/2026: 6,6306 USD/tháng trước ưu đãi, stress 10× khoảng 34,7081 USD/tháng. Xem `cost-estimate.md` cho từng dịch vụ và Calculator input; chưa tạo estimate URL hoặc đo hóa đơn thực tế.

## 7. Kế hoạch nghiệm thu

1. Xử lý credential đã lộ và review các thay đổi local/change set.
2. Sau khi được phép triển khai: test JWT, hai user, S3 CORS, worker/DLQ và đối chiếu SHA-256 trên AWS.
3. Lưu evidence có commit/ngày/môi trường, che bí mật, rồi cập nhật kết luận theo kết quả thực tế.
4. Đối soát nhật ký IoT, workshop độc lập, blog trùng nội dung và phần tự đánh giá theo trải nghiệm thật.
5. Trình bày theo `demo-script.md`, nêu cả kết quả và giới hạn.

Kỹ năng có thể chứng minh qua artifact: thiết kế SAM, xử lý AWS SDK, kiểm tra chủ sở hữu, phân trang, retry và kiểm thử nhiều lớp. Mức độ tham gia cá nhân, đánh giá mentor và kết quả hành chính cần sinh viên xác nhận riêng.

## 8. Bàn giao sản phẩm

Chạy `python -m scripts.demo_server` để dùng toàn bộ ứng dụng offline, `python -m scripts.verify` để chạy bộ nghiệm thu và `python -m scripts.build_release` để tạo ZIP source/frontend có manifest SHA-256. Cấu hình public có thể xuất từ stack bằng `scripts.export_frontend_config` sau khi được phép truy cập AWS. Không đóng gói credential/session/lịch sử Git. Mã triển khai hiện có hai GSI; nâng cấp bảng cũ cần hai bước theo `operations.md` để tránh giới hạn một GSI mới mỗi lần cập nhật.
