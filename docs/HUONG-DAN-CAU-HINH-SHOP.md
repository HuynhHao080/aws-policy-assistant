# Cấu hình thông tin shop ngay trên website

Bản chính đã chọn: https://djreo5eptvwk5.cloudfront.net/ — stack `policy-assistant`.

## Quản trị viên

1. Đăng nhập tài khoản quản trị, mở **Quản trị → Thông tin shop**.
2. Chọn **DEMO** nếu đang thử, hoặc **Thông tin vận hành thật** khi đã có dữ liệu được phép công bố.
3. Điền tên shop/đơn vị, email hoặc số điện thoại hỗ trợ, giờ hỗ trợ kèm múi giờ, hướng dẫn tiếp nhận đổi trả và lời nhắn. Chỉ nhập thông tin liên hệ/địa chỉ được phép chia sẻ cho khách; hệ thống không tự lấy email quản trị làm email hỗ trợ.
4. Bấm **Lưu nháp thông tin shop**. Khách vẫn thấy bản đã công bố trước đó; bản nháp chỉ quản trị viên xem được.
5. Kiểm tra bản nháp đã lưu, chọn ô xác nhận thông tin được phép hiển thị, rồi bấm **Công bố thông tin shop** và xác nhận. Khi chọn thông tin thật, tên shop, một kênh liên hệ hợp lệ, giờ hỗ trợ và hướng dẫn tiếp nhận đổi trả là bắt buộc. Hệ thống kiểm tra định dạng, không xác minh hộp thư/số điện thoại có hoạt động hay không.
6. Mở **Thông tin shop** để xem nội dung khách thấy. Thay đổi có hiệu lực ở lần tải/làm mới tiếp theo; không cần triển khai mã nguồn.

Nút **Ngừng công bố thông tin shop** ẩn bản đang công bố. **Bỏ nháp thông tin shop** bỏ phần soạn riêng, không thay bản đang công bố. **Tải lại thông tin shop** đọc bản mới nhất và hỏi trước nếu đang có nội dung chưa lưu. Nếu gặp xung đột, nội dung đang nhập vẫn giữ nguyên; đối chiếu rồi tải lại trước khi gửi lại.

Có thể lưu bản nháp chưa đầy đủ. Sau khi chỉnh bất kỳ trường nào, cần lưu lại trước khi công bố. Không tự chuyển DEMO thành thật khi chưa kiểm tra thông tin kinh doanh.

## Khách hàng

Đăng nhập và chọn **Thông tin shop** để xem tên đơn vị, kênh hỗ trợ, giờ hỗ trợ và hướng dẫn tiếp nhận đổi trả. Nếu chưa công bố, ứng dụng thông báo chưa có thông tin vận hành; vẫn có thể gửi yêu cầu hỗ trợ trong ứng dụng.

Thông tin shop là phần liên hệ vận hành, không thay thế các chính sách đã công bố và không tự trở thành nguồn AI. Tài liệu gắn nhãn DEMO vẫn chỉ để thử dù shop đã cập nhật kênh liên hệ thật. Nhân viên vẫn cần xác minh đơn hàng/chứng từ qua hệ thống bán hàng riêng.

## Dữ liệu và quyền

Chỉ quản trị được sửa/công bố. Khách không xem được bản nháp, revision hoặc danh tính người sửa. Mỗi cập nhật có kiểm tra phiên bản và ghi nhật ký hành động trong cùng giao dịch; nhật ký không chép nội dung liên hệ. Thông tin dùng chung của shop tồn tại độc lập với tài khoản quản trị, được giữ tới khi cập nhật/bỏ nháp/ngừng công bố, không bị xóa khi một quản trị xóa tài khoản. Các bản sao lưu vẫn theo thời hạn khôi phục vận hành đã công bố.
