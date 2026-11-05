# Hướng dẫn sử dụng và vận hành Policy Assistant

Dành cho bản thử nghiệm một shop phụ kiện, cập nhật ngày 30/10/2026.

## Địa chỉ và mã nguồn

Website: https://djreo5eptvwk5.cloudfront.net/

Chỉ sửa và triển khai từ `C:\Users\accli\Documents\Project\policy-assistant`. Các bản làm việc tạm trước đây đã được chuyển vào thư mục sao lưu, không phải project đang triển khai.

## Dùng các chức năng

1. Chọn **Đăng nhập / Đăng ký**, tạo tài khoản bằng email của mình và xác nhận email. Quên mật khẩu thì dùng chức năng khôi phục trên trang đăng nhập.
2. Vào **Tài liệu của tôi**, tải PDF lên và chờ trạng thái **Sẵn sàng**. PDF dạng ảnh cần thêm thời gian nhận dạng chữ. Mỗi tệp tối đa 10 MiB, 100 trang có chữ hoặc 10 trang cần OCR.
3. Vào **Trợ lý chính sách**, chọn tài liệu phù hợp và đặt câu hỏi cụ thể. Khi không chọn tài liệu, hệ thống có thể tra cứu PDF gần đây của bạn cùng chính sách chung. PDF riêng chỉ thuộc tài khoản đã tải lên.
4. Đọc câu trả lời và nguồn trích dẫn. Bấm nguồn để xem chính sách hoặc tải PDF gốc; kiểm tra điều kiện và thời điểm bắt đầu tính thời hạn trước khi tư vấn khách.
5. **Chính sách chung** dùng để tìm chính sách do quản trị công bố. Không dùng nguồn DEMO làm cam kết bán hàng thật.
6. **Lịch sử hỏi đáp** lưu tối đa 30 ngày, có thể xóa từng cuộc. **Tài khoản** có chức năng xuất dữ liệu, theo dõi hạn mức và yêu cầu xóa tài khoản. Xóa tài khoản là thao tác không thể hoàn tác qua giao diện; đọc xác nhận trước khi thực hiện.
7. Quản trị dùng **Quản trị** để quản lý chính sách chung và xem nhật ký. Chính sách công bố được dùng chung trong ứng dụng, nên chỉ nhập nội dung đã duyệt cho cùng một shop. PDF riêng không trở thành chính sách chung khi tải lên.

## Hạn mức và xử lý lỗi

Mỗi tài khoản mặc định có 20 lượt hỏi/ngày UTC. Nếu hết lượt, chờ ngày tiếp theo; không tạo tài khoản để né hạn mức. Báo lỗi AI hoặc mất kết nối có thể vẫn tính một lượt vì yêu cầu đã được tiếp nhận.

Nếu PDF báo lỗi, kiểm tra tệp có mở được, có mật khẩu hay vượt giới hạn không. Nếu đang xử lý lâu bất thường, ghi lại mã tài liệu và thông báo lỗi để kiểm tra vận hành; không gửi mật khẩu hoặc mã đăng nhập. Khi sửa hướng dẫn AI, hãy hỏi lại bằng câu mới; lịch sử cũ được giữ nguyên.

Ngân sách AWS 30–50 USD/tháng là mục tiêu. Thông báo ở 25/40/50 USD không tự chặn phát sinh chi phí. Theo dõi hóa đơn, cảnh báo và lượng sử dụng thực tế; chưa có kết quả đo tải hay cam kết độ sẵn sàng.

## Trước khi mời khách thật

- Chủ shop phải duyệt chính sách thật về bán hàng, giao hàng, đổi trả, bảo hành và hỗ trợ. Hiện bộ DEMO gồm số liệu hư cấu.
- Chốt danh tính đơn vị vận hành, thông tin liên hệ, địa chỉ nhận hàng và ngày hiệu lực; hoàn thiện sáu bản nháp tại `docs/policy-drafts/` trước khi công bố.
- Kiểm tra thủ công đăng ký/xác nhận email, khôi phục mật khẩu và nhận cảnh báo thực tế. Lỗi công cụ điều khiển trình duyệt hiện khiến các bước giao diện này chưa được kiểm chứng lại tự động.
- Hệ thống tra cứu và giải thích chính sách; chưa kết nối đơn hàng, tồn kho, thanh toán hoặc hãng vận chuyển, chưa tự thực hiện hủy/hoàn tiền. Những yêu cầu đó cần nhân viên xác minh qua kênh thật của shop.
- Nếu mở cho nhiều shop, cần triển khai phân tách dữ liệu và thành viên theo shop trước; không nhập chính sách riêng của nhiều shop vào kho chung hiện tại.

Kết quả kiểm tra kỹ thuật, phạm vi đã kiểm chứng và các giới hạn nằm tại `docs/retail-pilot-verification.md`.

Quy trình soạn nháp, công bố và ngừng công bố đã có hướng dẫn riêng tại [Hướng dẫn quản trị](HUONG-DAN-QUAN-TRI.md). Kiểm tra giao diện mới đã thực hiện cục bộ bằng dữ liệu giả; quyền trình duyệt hiện vẫn chặn việc quan sát website thật.

## Support/source-scope handover — 2026-11-04

Current single-shop feature inventory: [FEATURE-STATUS.md](FEATURE-STATUS.md). Support creation, staff replies/statuses, explicit sharing consent, retention/export/purge and AI source-scope selection are implemented. Current evidence: [support-verification.md](support-verification.md); Vietnamese instructions: [HUONG-DAN-HO-TRO.md](HUONG-DAN-HO-TRO.md). Policies remain DEMO pending business approval.


Latest practical triage release (2026-11-04): 218 Python/28 frontend passes; 29 live support/API checks and successful disposable-account cleanup; no new model calls/PDF uploads. See [current verification](practical-release-verification.md). Earlier sections describe their respective historical releases.


Bản chính đã chọn ngày 04/11/2026: djreo5eptvwk5.cloudfront.net / policy-assistant. Thông tin shop có thể lưu nháp, công bố và ngừng công bố ngay trong quản trị. [Hướng dẫn cấu hình](HUONG-DAN-CAU-HINH-SHOP.md) · [Nghiệm thu hiện tại](shop-release-verification.md). Các báo cáo trên thuộc phạm vi bản phát hành tương ứng.
