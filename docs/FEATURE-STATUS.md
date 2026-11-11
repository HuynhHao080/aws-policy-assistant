# Phạm vi chức năng và điều kiện sử dụng thực tế

Rà soát bàn giao: 04/11/2026. Mã nguồn duy nhất: `C:\Users\accli\Documents\Project\policy-assistant`.

Phạm vi sản phẩm là trợ lý chính sách và hỗ trợ khách hàng cho **một shop phụ kiện**, mở đăng ký công khai. Đây không phải hệ thống quản lý đơn hàng hoặc nền tảng nhiều shop.

| Nhóm | Chức năng đã có |
|---|---|
| Thông tin shop | Quản trị tự cấu hình liên hệ/giờ hỗ trợ/hướng dẫn tiếp nhận, lưu nháp/công bố/ngừng công bố, khách xem bản đã duyệt; không cần triển khai lại |
| Tài khoản | Đăng ký, xác nhận email, đăng nhập/đăng xuất, khôi phục mật khẩu qua Cognito; phân quyền khách/quản trị |
| PDF cá nhân | Tải lên, trích xuất/OCR, trạng thái xử lý, phân trang, tìm/lọc các PDF đã tải danh sách, xem, tìm trong trang, tô kết quả, sao chép và tải TXT từng trang, mở trang từ trích dẫn, đổi tên, tải bản gốc và xóa các phiên bản |
| Chất lượng AI | Đánh giá có cấu trúc, đổi/rút đánh giá, dashboard tổng hợp và xuất JSON; không lộ câu hỏi/PDF, không đồng nhất tỷ lệ nguồn với độ đúng |
| Hỏi đáp | Xếp hạng từ khóa trên văn bản có chuẩn hóa tiếng Việt, chọn phạm vi nguồn, Global Claude Haiku 5.5 trả lời tiếng Việt có trích dẫn, từ chối khi thiếu bằng chứng |
| Lịch sử | Riêng theo tài khoản, tối đa 30 ngày. Tìm và lọc trong các trang đã tải, mở từng cuộc, dùng lại câu hỏi, sao chép câu trả lời kèm nguồn, xuất JSON và xóa từng cuộc |
| Chính sách | Tìm kiếm nội dung công bố; quản trị danh mục, bản nháp, chỉnh sửa, công bố, ẩn/khôi phục, bỏ nháp, chống ghi đè và nhật ký |
| Hiệu lực chính sách | Ngày áp dụng UTC+7, lọc bản chưa/hết hiệu lực, sửa ngày hỏng, kiểm tra lại dữ kiện nguồn trước lưu câu trả lời; giới hạn point-in-time được nêu rõ |
| Hỗ trợ | Đồng ý chia sẻ, tạo/theo dõi/phản hồi/đóng/xóa yêu cầu; nhân viên xử lý theo trạng thái/ưu tiên, lọc theo loại và mã đơn khách tự cung cấp; xuất JSON; lưu tối đa 90 ngày |
| Phối hợp hỗ trợ | Tự nhận/bỏ nhận/tiếp quản có lý do; lọc người nhận; ghi chú nội bộ tách hội thoại khách; revision chung và lịch sử phân công giới hạn |
| Quyền riêng tư | Không tự chia sẻ PDF/lịch sử với nhân viên; không dùng yêu cầu hỗ trợ làm nguồn AI; xóa tài khoản kèm dọn dữ liệu |
| Vận hành | HTTPS, S3 riêng, hàng đợi và thử lại, phục hồi việc treo, DLQ/cảnh báo, quota, ngân sách AWS, quy trình triển khai và phục hồi |

## Bằng chứng

Bản phối hợp hỗ trợ đã triển khai: **322 Python đạt, 11 live bỏ qua; 67 frontend đạt; 20 kiểm tra HTTP thực tế đạt**. Ba tài khoản QA và yêu cầu thử đã dọn. 40 tệp frontend, 6 Lambda khớp artifact. [Báo cáo mới nhất](support-team-verification.md). Không gọi model/PDF/OCR hoặc gửi email trong lượt này. Các số liệu sau là snapshot lịch sử.

Mở rộng hiệu lực chính sách đã triển khai ngày05/11: **298Python đạt,11live bỏ qua;59frontend đạt;16kiểm tra API thực tế đạt và dọn fixture/tài khoản thành công**. Không gọi model/publish/OCR/PDF trong lượt nghiệm thu API này. [Báo cáo và giới hạn](policy-validity-verification.md). Các số liệu quality bên dưới là snapshot của bản trước, không thay kết quả lịch sử.

Bản chất lượng AI: **251 Python đạt, 11 bài tích hợp trực tiếp bỏ qua; 54 frontend đạt; 15 kiểm tra API/cleanup thực tế đạt**. Hai tài khoản, lịch sử và cohort giả đã dọn. Không gọi mô hình hay dùng PDF thật trong đợt này. Xem [báo cáo hiện tại](quality-release-verification.md). Kiểm thử frontend dùng DOM giả lập, không phải nghiệm thu hình ảnh trình duyệt; các kết quả mô hình/OCR trước đó giữ nguyên theo bản lịch sử.

## Trước khi nhận khách thật

- Chủ shop cần nhập/phê duyệt tên đơn vị, kênh hỗ trợ, giờ hỗ trợ và hướng dẫn tiếp nhận tại **Quản trị → Thông tin shop**, rồi công bố chính sách thật trong kho chính sách. Hiện giữ nhãn DEMO theo yêu cầu; không tự biến các mốc thử nghiệm thành cam kết kinh doanh.
- Cần thử thủ công email khôi phục mật khẩu, việc nhận cảnh báo thực tế và quy trình nhân viên trực hỗ trợ. Chủ tài khoản đã xác nhận đăng nhập/quyền quản trị và xác nhận SNS ở lượt trước.
- Chưa có kết quả kiểm thử tải hoặc SLA. Hạn mức hiện dành cho đợt chạy nhỏ, mục tiêu ngân sách 30–50 USD/tháng; AWS Budgets cảnh báo không chặn hóa đơn.

## Chưa thuộc phạm vi đã nghiệm thu

Nhiều shop/tenant, thanh toán/gói thuê bao, đồng bộ đơn hàng, chatbot kênh mạng xã hội, email phản hồi hỗ trợ tự động, lịch sử phiên bản chính sách đầy đủ và báo cáo CRM nâng cao. Chỉ bổ sung khi có nhu cầu nghiệp vụ và ngân sách rõ ràng.
