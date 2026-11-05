# Hướng dẫn quản trị chính sách

Giao diện V1 chia quản trị thành sáu mục: **Tổng quan, Chính sách, Hỗ trợ, Thông tin shop, Chất lượng AI, Nhật ký**. Chọn đúng mục trước khi làm theo các bước bên dưới. Có thể dùng phím trái/phải hoặc Home/End để chuyển mục; chuyển mục nội bộ vẫn giữ nội dung đang soạn.

Cập nhật ngày 30/10/2026. Website: https://djreo5eptvwk5.cloudfront.net/#admin

## Soạn và công bố

1. Đăng nhập tài khoản quản trị, vào **Quản trị**. Nếu đang mở trang cũ, tải lại trang để nhận giao diện mới.
2. Ở **Kho chính sách**, tìm theo mã, tiêu đề hoặc nhóm; chọn **Mở để sửa**. Muốn tạo chính sách khác, chọn **+ Soạn mới**. Mã chỉ gồm chữ, số, dấu gạch ngang hoặc gạch dưới, tối đa 80 ký tự; mã không đổi khi đang sửa.
3. Nhập nhóm, tiêu đề, nội dung và từ khóa. Giới hạn: tiêu đề 180 ký tự, nhóm 80 ký tự, nội dung 20.000 ký tự, tối đa 30 từ khóa — mỗi từ khóa 80 ký tự.
4. Chọn **Lưu bản nháp**. Khách hàng và AI chưa sử dụng phần thay đổi này. Nếu chính sách đã công bố, bản đang công bố vẫn được giữ nguyên. Mở **Xem bản đang công bố** phía dưới để đối chiếu.
5. Đọc lại bản nháp, kiểm tra các điều kiện, thời hạn, mức phí, ngày hiệu lực và thông tin liên hệ. Khi đã duyệt nội dung, chọn **Công bố bản nháp**, rồi xác nhận. Mỗi lần công bố mới tạo lại chỉ mục tìm kiếm AI.

Nút công bố chỉ hoạt động sau khi bản nháp đã lưu. Nếu sửa tiếp, hãy lưu nháp lần nữa. Lưu nháp không gọi AI tạo chỉ mục; khi dịch vụ AI lỗi, bạn vẫn có thể soạn nháp và công bố lại sau.

## Ngừng công bố và bỏ bản nháp

- **Ngừng công bố** làm chính sách ngừng xuất hiện trong kho chung và truy xuất AI; nội dung vẫn được giữ. Lịch sử hỏi đáp đã có không bị viết lại.
- Nếu không có bản nháp, **Công bố lại bản đã lưu** khôi phục chính sách đã ngừng công bố. Nếu có bản nháp, nút **Công bố bản nháp** sẽ công bố phần đã chỉnh sửa, nên kiểm tra kỹ trước khi chọn.
- **Bỏ bản nháp** chỉ bỏ phần nháp đã lưu; bản đang công bố được giữ nguyên. Nội dung nháp đã bỏ không có chức năng khôi phục. Nếu chưa từng công bố, mục chính sách chuyển sang trạng thái ngừng công bố và có thể mở lại để soạn tiếp.
- Giao diện mới ưu tiên ngừng công bố có thể khôi phục, không đặt nút xóa vĩnh viễn cạnh nút lưu.

## Khi có xung đột hoặc lỗi

Nếu chính sách được sửa ở phiên khác, hệ thống từ chối ghi đè và giữ nội dung đang gõ trên màn hình. Sao chép phần cần giữ trước khi **Mở để sửa** lại bản mới nhất, đối chiếu rồi lưu. Không bấm công bố nhiều lần để bỏ qua thông báo xung đột.

Thay đổi đang gõ chưa được lưu tự động. Trang cảnh báo khi rời trang có nội dung chưa lưu. Khi mất kết nối hoặc công bố báo lỗi, mở lại chính sách để xem trạng thái thực tế trước khi thử tiếp. Nhật ký quản trị ghi thao tác và người thực hiện, nhưng không chứa bản sao nội dung để khôi phục mọi phiên bản cũ.

## Phạm vi quản trị

Quản trị quản lý chính sách chung và mức sử dụng, không mở PDF riêng của khách hàng. Chính sách chung hiện được dùng cho toàn ứng dụng của một shop; không nhập chính sách riêng của nhiều shop vào cùng kho này.

Giữ nguyên nhãn DEMO khi dùng dữ liệu mẫu. Chỉ thay bằng chính sách thực tế khi chủ shop đã duyệt nội dung và cung cấp kênh hỗ trợ thật. Việc công bố trên website không tự tạo quyền hủy đơn, phê duyệt bảo hành hoặc thực hiện hoàn tiền; nhân viên vẫn xử lý các giao dịch thật.

Mã nguồn duy nhất đang sử dụng: `C:\Users\accli\Documents\Project\policy-assistant`.

## Hỗ trợ khách hàng

Trang quản trị hiện có hàng đợi yêu cầu, bộ lọc trạng thái, hội thoại phản hồi và kiểm tra xung đột cập nhật. Chỉ xem nội dung khách chủ động đồng ý gửi; không truy cập PDF riêng. Xem [hướng dẫn từng bước](HUONG-DAN-HO-TRO.md).


Bản chính đã chọn ngày 04/11/2026: djreo5eptvwk5.cloudfront.net / policy-assistant. Thông tin shop có thể lưu nháp, công bố và ngừng công bố ngay trong quản trị. [Hướng dẫn cấu hình](HUONG-DAN-CAU-HINH-SHOP.md) · [Nghiệm thu hiện tại](shop-release-verification.md). Các báo cáo trên thuộc phạm vi bản phát hành tương ứng.


Dashboard **Chất lượng AI** và xuất báo cáo: [hướng dẫn](HUONG-DAN-CHAT-LUONG-AI.md). Chỉ trả số liệu tổng hợp; không dùng làm chứng nhận câu trả lời đúng.
