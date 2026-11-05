# Bàn giao Policy Assistant — chất lượng AI và nguồn worklog

Ứng dụng chính: https://djreo5eptvwk5.cloudfront.net/ — stack policy-assistant.

Mã ứng dụng: `C:\Users\accli\Documents\Project\policy-assistant`.
Worklog chính do người dùng xác nhận: `C:\Users\accli\Documents\Project\aws-internship-worklog` (HuynhHao080/aws-internship-worklog). Repo worklog được đọc để đối chiếu, không sửa/commit/push. Bộ fcj-workshop cũ trong ứng dụng không đại diện cho hồ sơ đó.

## Chức năng mới

Khách đánh giá câu trả lời hữu ích/chưa hữu ích kèm lý do, đổi hoặc rút đánh giá. Quản trị mở **Chất lượng AI** để xem thống kê tổng hợp theo tháng và xuất JSON. Không đưa câu hỏi, PDF hoặc định danh người đánh giá lên dashboard. Có trích dẫn/đánh giá tích cực không phải chứng nhận câu trả lời đúng.

Giữ các chức năng tài khoản, PDF/OCR, hỏi đáp có nguồn, bản nháp/công bố chính sách, hỗ trợ có đồng ý, cấu hình shop, lịch sử/xuất/xóa và vận hành đã có. Quản trị hiện có sáu mục: Tổng quan, Chính sách, Hỗ trợ, Thông tin shop, Chất lượng AI, Nhật ký.

## Kiểm chứng hiện tại

**251 kiểm thử Python đạt, 11 bài tích hợp trực tiếp bỏ qua theo cấu hình;54 frontend đạt;15 kiểm tra API/cleanup thực tế đạt.** Tài khoản, lịch sử và cohort giả đã dọn. Test trực tiếp dùng cohort2000 ẩn khỏi dashboard và không gọi mô hình AI; không ghi dữ liệu giả vào tháng thật. Frontend được đối chiếu bytes, sáu Lambda khớp artifact và CloudFront đã cập nhật.

[Báo cáo/giới hạn](quality-release-verification.md) · [Hướng dẫn sử dụng](HUONG-DAN-CHAT-LUONG-AI.md) · [Đối chiếu FCAJ](fcaj/READINESS.md) · [Handoff worklog riêng](fcaj/WORKLOG-HANDOFF.md).

Các kết quả B4/B5/B5-R7/CI ở worklog là bằng chứng riêng theo thời điểm, không bị thay hoặc cộng thành điểm số mới. Chưa có nghiệm thu trình duyệt/hình ảnh, model accuracy, tải, khôi phục backup hoặc email thực trong lượt này. Code/cloud đã được cập nhật không đồng nghĩa GitHub/worklog đã được publish lại.

Sơ đồ kiến trúc cuối, bản Calculator và minh chứng cá nhân cần được chủ dự án thực hiện/rà soát theo quy định. Mã nguồn AI hỗ trợ và bản nháp kỹ thuật không thay thế phần tự hiểu, tự thiết kế và trình bày. Giữ DEMO cho tới khi có nội dung kinh doanh được phê duyệt.
