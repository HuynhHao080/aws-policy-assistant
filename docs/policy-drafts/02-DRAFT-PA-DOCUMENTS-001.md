## 2. Dự thảo — Tải lên, xử lý và quản lý tài liệu PDF

**Mã chính sách:** `DRAFT-PA-DOCUMENTS-001`

**Nhóm:** Dự thảo — Tài liệu

**Tiêu đề:** Dự thảo — Tải lên, xử lý và quản lý tài liệu PDF

**Từ khóa:** PDF, tải lên, OCR, scan, tài liệu riêng, quyền sở hữu

### Nội dung

DỰ THẢO — CHƯA BAN HÀNH
Phiên bản 0.1 · Ngày soạn 30/10/2026
Đơn vị vận hành: [TEN_DON_VI_VAN_HANH]
Địa chỉ liên hệ: [DIA_CHI_LIEN_HE]
Email hỗ trợ công khai: [EMAIL_HO_TRO]
Ngày có hiệu lực: [NGAY_HIEU_LUC]
Nội dung cần được chủ dự án duyệt trước khi có hiệu lực.

1. Tệp được hỗ trợ
Mỗi tệp là PDF không mã hóa, tối đa 10 MiB. Giới hạn là 100 trang với PDF có văn bản hoặc 10 trang với PDF cần nhận dạng chữ từ ảnh bằng OCR. Tổng văn bản trích xuất bị giới hạn ở 300.000 ký tự. Tệp hỏng, mã hóa, quá giới hạn hoặc không đọc được có thể bị từ chối.

2. Quyền đối với tài liệu
Tải lên không tự chuyển quyền sở hữu tài liệu cho đơn vị vận hành. Người tải cần có quyền cho phép lưu, trích xuất, tìm kiếm và xử lý qua các dịch vụ AWS nêu trong chính sách quyền riêng tư. Tài liệu có dữ liệu của người khác cần có căn cứ xử lý phù hợp trước khi tải.

3. Nội dung cần loại bỏ
Không tải mật khẩu, khóa API, thông tin thanh toán bí mật hoặc tài liệu không được phép đưa lên dịch vụ đám mây. Với dữ liệu nhạy cảm hoặc dữ liệu trẻ em, chỉ tải khi đơn vị vận hành đã xác nhận phạm vi và điều kiện pháp lý cần thiết. Người dùng tự kiểm tra và che dữ liệu không cần thiết; hệ thống chưa cam kết tự nhận diện hay tự che mọi dữ liệu cá nhân.

4. Xử lý và chất lượng
Sau khi bấm Tải lên và xử lý, tài liệu được đưa vào hàng đợi để trích xuất văn bản hoặc OCR và tạo dữ liệu tìm kiếm. Chỉ tài liệu xử lý xong được dùng làm nguồn trả lời. PDF scan mờ, chữ viết tay, bảng biểu và cách dàn trang phức tạp có thể được đọc thiếu hoặc sai. Kiểm tra đoạn trích với bản gốc.

5. Quản lý tài liệu
Trong Tài liệu của tôi, chủ tài khoản có thể đổi tên, tải xuống và yêu cầu xóa. PDF riêng không tự trở thành chính sách chung. Trang quản trị chính sách không cung cấp chức năng xem PDF riêng của khách hàng; quyền kỹ thuật của người vận hành hạ tầng là phạm vi riêng.

6. Xóa và lỗi xử lý
Khi tác vụ xóa thành công, các phiên bản tệp nguồn và nội dung trích xuất của tài liệu được xóa. Tác vụ đang xử lý có thể cần hoàn tất trước khi xóa. Việc xóa lịch sử và thời hạn bản sao lưu được nêu riêng trong chính sách quyền riêng tư. Nếu gặp lỗi, ghi lại thời điểm và thông báo lỗi để hỗ trợ, tránh tải lại nhiều lần liên tục.
