# Policy Assistant V1 — bản chốt 04/11/2026

Historical V1 snapshot before the quality extension. Current evidence: [quality release](quality-release-verification.md).

Website chính: https://djreo5eptvwk5.cloudfront.net/

Mã nguồn: `C:\Users\accli\Documents\Project\policy-assistant`. Bản Zed ở địa chỉ khác là môi trường tham chiếu riêng.

## Phạm vi V1

| Người dùng | Chức năng |
|---|---|
| Khách | Đăng ký/xác nhận email/đăng nhập/khôi phục mật khẩu; quản lý PDF riêng; tra cứu chính sách; hỏi đáp có trích dẫn; lịch sử/xuất dữ liệu; trao đổi hỗ trợ; xem thông tin shop; xóa tài khoản |
| Quản trị | Tổng quan hạn mức; danh mục/nháp/công bố/ẩn chính sách; xử lý hỗ trợ theo trạng thái/loại/ưu tiên/mã đơn khách nhập; cấu hình shop; nhật ký cập nhật |
| Vận hành | HTTPS, phân quyền, giới hạn sử dụng, xử lý nền/thử lại/khôi phục, dọn phiên bản tệp, cảnh báo, lưu giữ dữ liệu và công cụ kiểm tra triển khai |

V1 phục vụ một shop, trong hạn mức đã cấu hình. Không bổ sung tính năng mới trong lượt chốt; ưu tiên ổn định và hoàn thiện trải nghiệm của phạm vi trên.

## UI bản chốt

- Noto Sans/Noto Serif hỗ trợ tiếng Việt; tăng độ rõ của chữ phụ và vùng chạm trên điện thoại.
- Hướng dẫn cho người mới, trạng thái chưa đăng nhập rõ ràng, form riêng không tương tác khi chưa đăng nhập.
- Quản trị chia năm mục, hỗ trợ bàn phím và giữ bản nháp khi chuyển mục.
- Thông báo ngay trong cửa sổ hỗ trợ; trích dẫn chính sách mở cửa sổ nguồn trong màn hình đang dùng.
- Giữ câu hỏi khi lỗi; cảnh báo trước khi bỏ nội dung chưa gửi; Back/Forward hoạt động trong ứng dụng.
- Tải PDF có thông báo chờ/thất bại/sẵn sàng rõ ràng. Không khôi phục tên tệp/tìm kiếm riêng từ phản hồi cũ sau khi hết phiên.

## Nghiệm thu

Bộ frontend hiện tại: **48 kiểm thử đạt**, gồm logic API/editor, build và tương tác DOM cô lập. Kiểm thử DOM dùng dữ liệu giả, không kết nối AWS/browser origin hoặc gọi mô hình. Dependency audit tại thời điểm kiểm tra không báo lỗ hổng.

Máy chủ không thay đổi trong lượt UI này; bản máy chủ hiện hành đã đạt **231 bài Python, 11 bài tích hợp trực tiếp bỏ qua theo cấu hình**, và 14 kiểm tra API thông tin shop ở lượt trước. Không cộng dồn các báo cáo lịch sử thành một lượt end-to-end mới. Xem [bằng chứng UI](v1-ui-verification.md) và [bằng chứng máy chủ](shop-release-verification.md).

## Việc chủ shop cần làm trước khi nhận khách thật

1. Vào **Quản trị → Thông tin shop**, nhập và phê duyệt thông tin vận hành thật.
2. Vào **Quản trị → Chính sách**, thay bộ DEMO bằng nội dung được shop phê duyệt; không dùng số liệu giả làm cam kết thật.
3. Nghiệm thu thủ công giao diện trên thiết bị sẽ sử dụng, email khôi phục mật khẩu, nhận cảnh báo và ca trực hỗ trợ. Chưa có kiểm thử tải, cam kết SLA hoặc thử phục hồi backup.

Quyền browser-origin đã bị từ chối ở lượt trước, không được thử lại qua đường khác; vì vậy không có tuyên bố nghiệm thu hình ảnh/pixel hoặc hosted-login qua trình duyệt cho lượt chốt này. Không có dữ liệu kinh doanh thật được tự sáng tác/công bố.

[Hướng dẫn quản trị](HUONG-DAN-QUAN-TRI.md) · [Cấu hình shop](HUONG-DAN-CAU-HINH-SHOP.md) · [Xử lý hỗ trợ](HUONG-DAN-HO-TRO.md) · [Runbook](production-runbook.md).
