# Thời hạn hiệu lực chính sách

Chức năng dành cho một shop quản lý chính sách hiện hành. Mục tiêu là tránh dùng nguồn chưa tới ngày áp dụng, đã hết hạn hoặc vừa thay đổi trong khi xử lý câu hỏi. Đây là thời hạn sử dụng nguồn của ứng dụng; không tự xác định chính sách nào áp dụng cho giao dịch quá khứ hoặc kết luận quyền lợi pháp lý của khách.

## Quản trị

1. Mở **Quản trị → Chính sách**, chọn bản cần sửa hoặc soạn mới.
2. Nhập **Có hiệu lực từ** và **Đến hết ngày**. Hai mốc đều bao gồm ngày được chọn, tính theo Việt Nam **UTC+7**, không theo giờ trình duyệt hay múi giờ Lambda. Để trống mốc nào nếu không giới hạn mốc đó.
3. Lưu nháp và kiểm tra bản xem trước. Khách vẫn dùng bản đã công bố trước đó theo thời hạn của bản đó; lưu nháp không đổi nguồn AI.
4. Công bố rõ ràng sau khi xem lại xác nhận thời hạn. Bản được công bố nhưng chưa tới ngày vẫn có trạng thái **Chưa tới ngày hiệu lực**; công bố không tự làm nó có hiệu lực ngay.
5. Dùng bộ lọc **Đang có hiệu lực / Chưa tới ngày áp dụng / Đã hết hiệu lực / Cần kiểm tra ngày** để rà soát. Bộ lọc áp dụng cho bản đã công bố, không lấy ngày của bản nháp làm ngày của bản khách đang thấy. Danh sách vẫn phân trang có giới hạn; một trang rỗng có thể còn trang kế tiếp.

Ví dụ: từ05/11 đến10/11 nghĩa dùng được từ00:00ngày05 đến trước00:00ngày11 theo UTC+7. Mốc bắt đầu có thể bằng mốc kết thúc. Ngày không tồn tại hoặc ngày kết thúc trước ngày bắt đầu bị từ chối. Các bản cũ không có hai trường ngày tiếp tục hoạt động không giới hạn thời hạn.

Client cũ không gửi trường ngày sẽ giữ thời hạn hiện có. Muốn bỏ giới hạn, gửi chuỗi rỗng rõ ràng ở trường tương ứng rồi lưu/công bố; publish loại trường đã xóa khỏi bản đã công bố. Bản legacy có ngày hỏng bị loại khỏi tra cứu, vẫn hiện trong quản trị để sửa.

## Tra cứu, AI và lịch sử

- GET theo mã và tìm kiếm không trả nguồn chưa/không còn hiệu lực. Truy hồi AI cũng kiểm ngày trước khi đưa nguồn vào prompt; không có nguồn phù hợp thì trả thiếu bằng chứng, không gọi generation.
- Trước khi lưu/trả một kết quả có trích dẫn chính sách, backend đọc lại mỗi chính sách được trích dẫn bằng consistent read và kiểm ngày, trạng thái công bố cùng fingerprint nội dung công khai. Nếu nguồn thay đổi/ẩn/hết hạn/bị xóa, trả409 và không lưu câu trả lời đó. Không tự gọi model lại; lượt hỏi có thể vẫn tính quota.
- Chỉnh nháp riêng không làm một nguồn công bố không đổi bị coi là thay đổi. Fingerprint nội bộ không được gửi vào prompt, response, lịch sử hoặc export.
- Metadata ngày được giữ trong trích dẫn mới để giải thích bối cảnh. Lịch sử cũ là snapshot tại lúc trả lời, không bị viết lại khi chính sách hết hạn. Mở nguồn hiện tại từ lịch sử có thể trả không tìm thấy nếu bản đã ẩn/hết hạn.
- Việc kiểm tra diễn ra tại thời điểm đọc/kiểm cuối, không khóa chính sách hoặc thời gian cho tới khi khách đọc kết quả. Đây không phải giải pháp tự suy luận xung đột giữa nhiều chính sách hoặc kho phiên bản pháp lý.

## Kiến trúc và chi phí

Không thêm cron, queue, bảng/index, endpoint, dịch vụ hay IAM grant. Trạng thái ngày được tính khi đọc; hết hạn không xóa dữ liệu hoặc tạo thêm audit event. Admin writes vẫn dùng revision và transaction audit hiện có. Các trích dẫn chính sách thêm tối đa5consistent GetItem (một lần/ID khác nhau) trước lưu; lookup theo mã cũng dùng consistent read. Search vẫn giữ scan budget/cursor. Việc công bố dùng pipeline embedding hiện có; không có cuộc gọi model tự động khi đồng hồ qua ngày hiệu lực.

## Demo kỹ thuật cho FCAJ

Để trình bày khả năng kiểm chứng, chạy `python -m pytest tests/unit/test_policy_validity.py -q` và giải thích: biên ngày Việt Nam, cùng ngày đầu/cuối, draft isolation, chính sách đổi giữa generation và phản hồi409 không lưu lịch sử. Các bài này dùng moto/model giả lập; không phải minh chứng độ đúng model thật. Không đổi giờ hệ thống hoặc sửa chính sách thật của shop để giả lập hết hạn.

Script `scripts/check_policy_validity_live.py` là nghiệm thu riêng sau triển khai: xác minh đúng artifact có module hiệu lực trước khi tạo fixture; một identity tạm không gửi thư và ba record luôn chưa tới ngày/đã hết hạn/ngày hỏng, không hiện cho khách. Chỉ thử API đọc/quyền/lưu nháp; không gọi `/ask`, publish, embedding, OCR hoặc PDF. Script dọn các record theo nonce và xóa tài khoản theo workflow ứng dụng; cần kiểm tra cả acceptance lẫn cleanup trước khi báo đạt. Không dùng kết quả này làm bằng chứng đã thử generation/publish trên AWS.
