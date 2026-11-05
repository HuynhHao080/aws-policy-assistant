# Phối hợp xử lý yêu cầu hỗ trợ

Tính năng dành cho những tài khoản quản trị đã được đơn vị vận hành tin cậy. Phân công là cơ chế phối hợp, không phải quyền đọc PDF riêng hoặc một vai trò nhân viên mới. Mọi quản trị viên vẫn có thể xem các yêu cầu khách đã đồng ý chia sẻ; người khác có thể nhận bàn giao với lý do được lưu. Hiện giao diện dùng “Bạn” hoặc mã tài khoản nhân viên rút gọn, chưa có danh bạ nhân sự.

## Nhận và bàn giao

1. Trong **Quản trị → Hỗ trợ**, lọc **Chưa có người nhận / Tôi phụ trách / Nhân viên khác** kết hợp trạng thái, loại, ưu tiên hoặc mã đơn. Đây là trang scan có giới hạn, không phải số tổng backlog; có thể cần Xem thêm.
2. Mở yêu cầu, chọn **Nhận phụ trách**. Server gán cho `sub` của nhân viên đang đăng nhập; không nhận mã nhân viên đích tự khai từ client. Hai người dùng cùng revision không thể cùng nhận thành công.
3. Khi người khác đang phụ trách, bạn vẫn có thể thêm ghi chú nội bộ. Muốn phản hồi khách hoặc đổi trạng thái/ưu tiên, dùng **Nhận bàn giao về tôi** với lý do10–300ký tự. Điều này hỗ trợ đổi ca hoặc nhân viên cũ không còn làm việc mà không cần sửa dữ liệu bằng tay.
4. Chỉ người đang phụ trách được **Trả về hàng đợi**. Nhận/trả/bàn giao không tự đổi trạng thái công khai, tạo tin nhắn hoặc gửi email.

Mỗi lần ghi đều dùng revision và transaction audit/guard tài khoản xóa hiện có. Nếu409hoặc không chắc request đã thành công, chọn **Tải lại yêu cầu** và xem trạng thái mới trước khi thao tác tiếp; không tự gửi lại mù. Tải lại/đóng/mở yêu cầu khác cảnh báo khi có bản nháp chưa lưu.

## Ghi chú và phản hồi là hai luồng khác nhau

- **Ghi chú nội bộ:** tối đa20ghi chú/yêu cầu,1000ký tự/ghi chú. Chỉ admin detail hiển thị nội dung; admin summary chỉ có số lượng. Không gửi cho khách, không vào export dữ liệu khách, audit text, lịch sử AI hoặc nguồn RAG.
- **Phản hồi khách:** tiếp tục dùng luồng20tin nhắn,1500ký tự/tin. Nhãn và vùng màu riêng giúp tránh gửi nhầm ghi chú vào luồng khách. Lưu ghi chú giữ bản nháp phản hồi; gửi phản hồi giữ ghi chú đang soạn.
- **Bàn giao:** giữ10sự kiện phân công gần nhất trong yêu cầu, gồm lý do bàn giao; sự kiện cũ hơn bị bỏ khỏi danh sách giới hạn này. Audit riêng giữ action/actor/resource90ngày, không chứa nội dung note hoặc lý do. Đây không phải lịch sử không giới hạn.

Không nhập mật khẩu, thông tin thanh toán hoặc dữ liệu cá nhân không cần thiết. Ghi chú không tự đính kèm PDF/hội thoại và không trở thành nguồn AI. Phân công không mở quyền đọc tài liệu cá nhân.

## Thời hạn, xóa và cập nhật

Ghi chú/phân công nằm trong cùng record yêu cầu nên dùng chung mốc hết hạn90ngày từ khi khách tạo. Thao tác nội bộ không kéo dài TTL, không tăng `message_count`, không đổi `updated_at` công khai; admin có `staff_updated_at` riêng. Revision chung vẫn đổi nên khách có thể cần tải lại khi gửi đồng thời với hoạt động nội bộ.

Khách xóa yêu cầu/tài khoản sẽ dọn record hỗ trợ bao gồm ghi chú, theo workflow hiện có; marker tài khoản đang xóa ngăn ghi phục hồi lại dữ liệu. TTL/backup có độ trễ và quy tắc riêng. Đóng yêu cầu không xóa ghi chú. Nhân viên xóa tài khoản không tự xóa đóng góp trong yêu cầu thuộc khách khác; chúng giữ theo vòng đời yêu cầu và audit. Đăng xuất/hết phiên xóa dữ liệu nội bộ khỏi UI; phản hồi đến muộn không phục hồi phiên cũ.

## Kiến trúc và nghiệm thu

Không thêm bảng/index/route/dịch vụ/IAM grant. Dùng SupportTable, transaction revision+owner-deletion guard+audit hiện có; bộ lọc vẫn scan theo quota của một shop nhỏ. Kích thước note/history được chặn; chưa có benchmark tải, SLA, realtime push, danh bạ nhân viên hoặc role support-only.

`python -m pytest tests/unit/test_support_team.py -q` kiểm quyền, claim/handover, không lộ ghi chú, race revision/xóa tài khoản, giới hạn lưu và không vào model context bằng moto/model giả. `scripts/check_support_team_live.py` là nghiệm thu riêng sau triển khai với3identity tạm không gửi thư và1yêu cầu tổng hợp có consent. Script xác minh artifact trước ghi, lưu marker attempt trước tạo user và dọn bằng workflow tài khoản; không gọi model, embedding, OCR hoặc PDF. Các counter HTTP/support/audit thông thường vẫn được sử dụng, không reset quota để che lần kiểm thử.
