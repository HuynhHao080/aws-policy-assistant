## 5. Dự thảo — Hạn mức sử dụng và vận hành dịch vụ

**Mã chính sách:** `DRAFT-PA-LIMITS-001`

**Nhóm:** Dự thảo — Hạn mức

**Tiêu đề:** Dự thảo — Hạn mức sử dụng và vận hành dịch vụ

**Từ khóa:** hạn mức, lượt tải, câu hỏi, UTC, vận hành, ngân sách

### Nội dung

DỰ THẢO — CHƯA BAN HÀNH
Phiên bản 0.1 · Ngày soạn 30/10/2026
Đơn vị vận hành: [TEN_DON_VI_VAN_HANH]
Địa chỉ liên hệ: [DIA_CHI_LIEN_HE]
Email hỗ trợ công khai: [EMAIL_HO_TRO]
Ngày có hiệu lực: [NGAY_HIEU_LUC]
Nội dung cần được chủ dự án duyệt trước khi có hiệu lực.

1. Hạn mức cấu hình hiện tại
Mỗi tài khoản tối đa 5 lượt tải PDF và 20 lượt hỏi đáp mỗi ngày. Toàn hệ thống tối đa 300 lượt tải PDF và 2.000 lượt hỏi đáp mỗi tháng. Các thao tác ứng dụng còn chịu giới hạn 1.000 yêu cầu mỗi tài khoản/ngày và 100.000 yêu cầu toàn hệ thống/tháng. Đối chiếu các con số với cấu hình triển khai trước ngày chính sách có hiệu lực.

2. Cách tính lượt
Lượt được đặt tại bước kiểm tra hạn mức, không chỉ khi yêu cầu hoàn tất thành công. Yêu cầu đã nhận xử lý có thể vẫn tính lượt khi lỗi ở bước sau; không tự động hoàn lại mọi lượt lỗi. Tránh gửi lặp liên tục khi chưa biết kết quả lượt trước.

3. Thời điểm đặt lại
Bộ đếm ngày và tháng dùng UTC. Tại Việt Nam, ngày mới bắt đầu lúc 07:00; tháng mới bắt đầu lúc 07:00 ngày đầu tháng theo giờ Việt Nam. Đây là ngày/tháng lịch, không phải cửa sổ trượt 24 giờ hoặc 30 ngày.

4. Hạn mức chung và đăng ký
Nếu toàn hệ thống đã hết hạn mức tháng, yêu cầu có thể bị từ chối dù tài khoản còn lượt riêng. Giới hạn đăng ký và bảo vệ vận hành cũng có thể làm đăng ký mới bị từ chối. Không tạo nhiều tài khoản để né giới hạn.

5. Tác vụ nền và khả dụng
Tải lên, OCR và xóa dữ liệu có thể cần xử lý nền hoặc thử lại. Bấm gửi không đồng nghĩa tác vụ đã xong; theo dõi trạng thái và liên hệ hỗ trợ nếu lỗi kéo dài. Chưa có SLA, cam kết hỗ trợ 24/7 hoặc thời gian xử lý cố định.

6. Phí và ngân sách
Hạn mức không tự tạo thành gói trả phí. Ngân sách AWS nội bộ và email cảnh báo không phải biểu giá khách hàng, bảo đảm chi phí tối đa hay cơ chế tự ngắt mọi khoản chi. Chính sách thu phí/hoàn tiền, nếu có, phải được công bố riêng trước khi áp dụng.

7. Thay đổi hạn mức
Khi thay đổi, đơn vị vận hành cần đồng bộ cấu hình, tài liệu và thông báo liên quan. Không dùng số liệu từ phiên bản cũ để khẳng định hạn mức hiện tại sau khi chính sách đã thay thế.
