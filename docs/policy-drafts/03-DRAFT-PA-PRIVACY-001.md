## 3. Dự thảo — Quyền riêng tư, lưu giữ và xóa dữ liệu

**Mã chính sách:** `DRAFT-PA-PRIVACY-001`

**Nhóm:** Dự thảo — Quyền riêng tư

**Tiêu đề:** Dự thảo — Quyền riêng tư, lưu giữ và xóa dữ liệu

**Từ khóa:** quyền riêng tư, dữ liệu cá nhân, AWS, lưu giữ, xóa tài khoản, sao lưu

### Nội dung

DỰ THẢO — CHƯA BAN HÀNH
Phiên bản 0.1 · Ngày soạn 30/10/2026
Đơn vị vận hành: [TEN_DON_VI_VAN_HANH]
Địa chỉ liên hệ: [DIA_CHI_LIEN_HE]
Email hỗ trợ công khai: [EMAIL_HO_TRO]
Ngày có hiệu lực: [NGAY_HIEU_LUC]
Nội dung cần được chủ dự án duyệt trước khi có hiệu lực.

1. Đầu mối phụ trách
[TEN_DON_VI_VAN_HANH], địa chỉ [DIA_CHI_LIEN_HE], email [EMAIL_HO_TRO], tiếp nhận yêu cầu liên quan đến dữ liệu của dịch vụ. Vai trò và trách nhiệm pháp lý của đơn vị cùng các bên xử lý phải được chốt trước khi ban hành.

2. Dữ liệu và mục đích
Email, mã tài khoản và thông tin xác thực cần thiết phục vụ đăng nhập. PDF, tên tệp, văn bản trích xuất và dữ liệu tìm kiếm phục vụ quản lý tài liệu và truy xuất nguồn. Câu hỏi, câu trả lời và đoạn trích phục vụ hỏi đáp và lịch sử. Bộ đếm phục vụ hạn mức; nhật ký và bản ghi quản trị phục vụ xử lý lỗi, an toàn và kiểm tra thay đổi chính sách.

3. Nhà cung cấp và nơi xử lý
Dịch vụ sử dụng AWS: Cognito cho xác thực, S3/DynamoDB cho lưu trữ, Textract cho OCR và Bedrock cho tìm kiếm ngữ nghĩa, tạo câu trả lời. Cấu hình chính tại Singapore. Khi lập chỉ mục, văn bản được gửi tới mô hình nhúng. Khi hỏi đáp, câu hỏi và tối đa năm đoạn liên quan được gửi tới mô hình tạo câu trả lời. Suy luận APAC có thể xử lý tại các vùng AWS ngoài Singapore và ngoài Việt Nam. Không dùng dịch vụ cho tài liệu bắt buộc chỉ lưu hoặc xử lý tại Việt Nam khi chưa có phương án được duyệt. Đơn vị vận hành cần xác định căn cứ xử lý, thông báo/đồng ý và nghĩa vụ chuyển dữ liệu ra nước ngoài áp dụng cho mình trước khi ban hành.

4. Phạm vi truy cập
Ứng dụng phân quyền PDF và lịch sử theo tài khoản sở hữu. Quản trị viên ứng dụng quản lý chính sách chung, không mặc nhiên xem PDF riêng qua trang quản trị. Người vận hành hạ tầng AWS có quyền kỹ thuật theo phân quyền vận hành. Người có liên kết tải tạm có thể sử dụng trong thời gian liên kết còn hiệu lực; không chia sẻ liên kết đó.

5. Thời hạn lưu giữ
PDF đã xử lý và dữ liệu tìm kiếm được giữ tới khi yêu cầu xóa được xử lý thành công. Lịch sử hỏi đáp có thời hạn 30 ngày. Tệp tải tạm trong luồng mới được cấu hình dọn sau hai ngày. Dấu vết xóa tài liệu có thời hạn 30 ngày; bộ đếm/trạng thái phục vụ vận hành khoảng 65 ngày; nhật ký quản trị 90 ngày. Các nhóm nhật ký ứng dụng được quản lý trong cấu hình lưu 14–30 ngày tùy loại. Cơ chế dọn tự động có độ trễ; không bảo đảm mọi dữ liệu biến mất đúng thời điểm hết hạn. Nhật ký lịch sử và các hệ thống sao lưu có phạm vi riêng cần được kiểm kê trước khi ban hành.

6. Xóa PDF không tự xóa mọi đoạn trích đã lưu
Sau khi xóa PDF thành công, các phiên bản nguồn và dữ liệu trích xuất được xóa. Câu trả lời và đoạn trích đã lưu trong lịch sử có thể vẫn còn đến khi xóa cuộc hỏi đáp, hết thời hạn lưu hoặc xóa tài khoản. Bạn có thể xóa từng cuộc hỏi đáp trong Lịch sử hỏi đáp và xuất lịch sử ở mục Tài khoản. Tệp đã tải hoặc xuất ra thiết bị của bạn nằm ngoài phạm vi xóa của ứng dụng.

7. Xóa tài khoản và sao lưu
Tại mục Tài khoản, nhập DELETE rồi xác nhận xóa. Hệ thống chặn truy cập trước, xử lý xóa PDF/lịch sử rồi xóa danh tính đăng nhập. Đây là tác vụ nền, có thể cần thử lại khi lỗi; chưa cam kết xong trong số phút cố định. Không thể hoàn tác từ ứng dụng. Bản ghi vận hành còn theo thời hạn nêu trên. Sao lưu khôi phục DynamoDB có thể còn dữ liệu đã xóa trong cửa sổ tới 35 ngày; bản sao lưu không hiển thị như dữ liệu hoạt động và không phải tính năng khôi phục tài khoản cho khách hàng.

8. Yêu cầu về dữ liệu cá nhân
Bạn có thể gửi yêu cầu được biết, truy cập, chỉnh sửa, cung cấp, xóa, hạn chế hoặc phản đối xử lý dữ liệu; rút lại đồng ý khi việc xử lý dựa trên đồng ý; và phản ánh, khiếu nại theo quy định áp dụng. Gửi yêu cầu tới [EMAIL_HO_TRO]. Đơn vị vận hành có thể cần xác minh người yêu cầu bằng thông tin phù hợp; không gửi mật khẩu hoặc OTP. Thời hạn và cách giải quyết phải theo quy định áp dụng, không tự đặt một thời hạn cố định trong bản nháp.

9. Bảo mật và sự cố
Hệ thống sử dụng HTTPS, lưu trữ riêng và phân quyền tài khoản; không có bảo đảm tuyệt đối loại bỏ mọi sự cố. Nếu nghi lộ dữ liệu, bảo vệ tài khoản, ngừng chia sẻ liên kết và báo đầu mối hỗ trợ. Quy trình đánh giá, xử lý, thông báo sự cố và người chịu trách nhiệm phải được phê duyệt trước khi công bố.
