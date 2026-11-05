# Bộ demo shop phụ kiện — Policy Assistant

DỮ LIỆU DEMO HƯ CẤU — CHỈ ĐỂ KIỂM THỬ, KHÔNG ÁP DỤNG CHO GIAO DỊCH THẬT. Các thời hạn và mức phí dưới đây là giả định kiểm thử, chưa được shop nào phê duyệt.

Ngày soạn: 30/10/2026. Tên bối cảnh: Shop phụ kiện mẫu (hư cấu). Chưa đăng lên website.

Chính sách chung hiện dùng cho toàn ứng dụng. Chỉ dùng bộ này trong pilot một shop và báo rõ đây là môi trường demo. Trước khi phục vụ shop thật phải thay bằng nội dung do chủ shop duyệt. Bộ này không thay thế 6 chính sách vận hành website đã soạn trước đó.


---

## 1. DEMO — Đặt hàng và hủy đơn

**Mã:** `DEMO-SHOP-ORDER-001`

**Nhóm:** DEMO — Shop phụ kiện mẫu

**Từ khóa:** đặt hàng, hủy đơn, thanh toán

### Nội dung

DỮ LIỆU DEMO HƯ CẤU — CHỈ ĐỂ KIỂM THỬ, KHÔNG ÁP DỤNG CHO GIAO DỊCH THẬT. Các thời hạn và mức phí dưới đây là giả định kiểm thử, chưa được shop nào phê duyệt.

1. Trong tình huống mẫu, cửa hàng bán cáp sạc, củ sạc, ốp điện thoại và tai nghe. Đây là cửa hàng hư cấu, không nhận đơn hoặc thanh toán thực tế.
2. Đơn hàng chỉ được coi là xác nhận sau khi nhân viên kiểm tra tồn kho và gửi xác nhận cho khách.
3. Khách có thể đề nghị hủy khi đơn chưa bàn giao cho đơn vị vận chuyển. Đơn đã bàn giao được xử lý theo chính sách đổi trả, không tự động được hủy.
4. Trong kịch bản mẫu, khách có thể chọn chuyển khoản hoặc thanh toán khi nhận hàng. Không có số tài khoản thanh toán thật trong bộ dữ liệu.
5. Không có dữ liệu giá bán, tồn kho trực tiếp, mã giảm giá hoặc trạng thái đơn hàng trong bộ chính sách. Khi được hỏi các thông tin đó, cần báo chưa có dữ liệu và đề nghị liên hệ nhân viên. Không tự suy đoán sản phẩm còn hàng hoặc giá hiện tại.


---

## 2. DEMO — Giao hàng và phí vận chuyển

**Mã:** `DEMO-SHOP-SHIPPING-001`

**Nhóm:** DEMO — Shop phụ kiện mẫu

**Từ khóa:** giao hàng, vận chuyển, phí ship, chậm giao

### Nội dung

DỮ LIỆU DEMO HƯ CẤU — CHỈ ĐỂ KIỂM THỬ, KHÔNG ÁP DỤNG CHO GIAO DỊCH THẬT. Các thời hạn và mức phí dưới đây là giả định kiểm thử, chưa được shop nào phê duyệt.

1. Trong kịch bản mẫu, cửa hàng giao trong lãnh thổ Việt Nam; chưa hỗ trợ giao quốc tế.
2. Dự kiến bàn giao đơn cho đơn vị vận chuyển trong 1–2 ngày làm việc kể từ khi xác nhận đơn. Thời gian vận chuyển dự kiến sau bàn giao là 2–5 ngày làm việc. Đây là hai giai đoạn khác nhau, không cam kết giao trong 1–2 ngày.
3. Ngày làm việc trong bộ DEMO là thứ Hai đến thứ Sáu, không tính ngày lễ.
4. Phí giao mẫu là 25.000 đồng mỗi đơn. Đơn có giá trị hàng hóa từ 500.000 đồng được miễn phí giao tiêu chuẩn. Chưa quy định phụ phí vùng xa hoặc dịch vụ hỏa tốc.
5. Chưa có dịch vụ giao hẹn giờ hay giao trong ngày. Nếu quá khoảng dự kiến, khách cung cấp mã đơn hàng cho nhân viên kiểm tra; hệ thống hỏi đáp không tra cứu trực tiếp hãng vận chuyển.
6. Khách nên kiểm tra tình trạng bao gói khi nhận và báo nhân viên khi thấy dấu hiệu bất thường.


---

## 3. DEMO — Đổi trả và hoàn tiền

**Mã:** `DEMO-SHOP-RETURNS-001`

**Nhóm:** DEMO — Shop phụ kiện mẫu

**Từ khóa:** đổi trả, hoàn tiền, mở hộp, giao sai, lỗi sản phẩm

### Nội dung

DỮ LIỆU DEMO HƯ CẤU — CHỈ ĐỂ KIỂM THỬ, KHÔNG ÁP DỤNG CHO GIAO DỊCH THẬT. Các thời hạn và mức phí dưới đây là giả định kiểm thử, chưa được shop nào phê duyệt.

1. Mọi nội dung sau là giả định kiểm thử, không phải quy định pháp luật hay cam kết của shop thật.
2. Với hàng giao sai hoặc sản phẩm có lỗi khi nhận, khách liên hệ trong 7 ngày lịch tính từ ngày nhận, cung cấp mã đơn và mô tả/ảnh lỗi để nhân viên kiểm tra. Đủ điều kiện sau kiểm tra thì đổi hàng hoặc hoàn tiền theo lựa chọn được hai bên xác nhận.
3. Với lý do đổi ý, chỉ tiếp nhận đề nghị trong 3 ngày lịch từ ngày nhận khi hàng chưa mở, chưa dùng, còn nguyên tem và bao bì. Không áp dụng điều kiện đổi ý này cho hàng đã mở hộp; trường hợp lỗi hoặc giao sai vẫn được xem xét theo mục 2.
4. Nếu xác nhận lỗi sản phẩm hoặc giao sai, cửa hàng chịu phí vận chuyển đổi trả tiêu chuẩn. Nếu đổi ý và đủ điều kiện, khách chịu phí gửi trả. Chưa quy định số tiền phí gửi trả cụ thể.
5. Hoàn tiền được xử lý trong 5 ngày làm việc từ khi nhân viên xác nhận đã nhận đủ hàng trả và chấp thuận hoàn tiền. Không tính thời hạn này từ ngày khách vừa gửi yêu cầu. Thời gian tiền hiển thị còn phụ thuộc bên thanh toán.
6. Không có quyền tự động duyệt yêu cầu, hoàn tiền hoặc quyết định tranh chấp trong chatbot. Nhân viên kiểm tra điều kiện và xác nhận kết quả.


---

## 4. DEMO — Bảo hành phụ kiện

**Mã:** `DEMO-SHOP-WARRANTY-001`

**Nhóm:** DEMO — Shop phụ kiện mẫu

**Từ khóa:** bảo hành, tai nghe, củ sạc, cáp sạc, rơi vỡ

### Nội dung

DỮ LIỆU DEMO HƯ CẤU — CHỈ ĐỂ KIỂM THỬ, KHÔNG ÁP DỤNG CHO GIAO DỊCH THẬT. Các thời hạn và mức phí dưới đây là giả định kiểm thử, chưa được shop nào phê duyệt.

1. Thời hạn bảo hành giả định, tính từ ngày nhận hàng: củ sạc 12 tháng, tai nghe 6 tháng, cáp sạc 3 tháng. Bộ dữ liệu chưa quy định bảo hành cho ốp điện thoại; không được suy ra là có hoặc không có bảo hành.
2. Khách cung cấp mã đơn hoặc chứng từ mua để nhân viên xác minh sản phẩm và thời hạn.
3. Lỗi kỹ thuật do sản xuất được tiếp nhận kiểm tra bảo hành. Hư hỏng do rơi vỡ, vào nước hoặc tự tháo sửa không thuộc phạm vi bảo hành mẫu. Nhân viên cần kiểm tra nguyên nhân, chatbot không tự kết luận lỗi thực tế.
4. Thời gian kiểm tra/sửa chữa dự kiến là 7–15 ngày làm việc sau khi bộ phận bảo hành nhận sản phẩm, không phải sau khi khách vừa hỏi. Chưa có cam kết sản phẩm thay thế tạm trong thời gian chờ.
5. Bộ DEMO chưa quy định phí vận chuyển bảo hành. Nếu được hỏi ai chịu phí gửi bảo hành, cần báo chưa có quy định và chuyển nhân viên; không lấy quy định phí đổi trả để tự áp dụng.
6. Quy trình đổi trả hàng mới nhận và bảo hành sau mua là hai quy trình khác nhau.


---

## 5. DEMO — Hỗ trợ khách hàng và giới hạn của trợ lý

**Mã:** `DEMO-SHOP-SUPPORT-001`

**Nhóm:** DEMO — Shop phụ kiện mẫu

**Từ khóa:** hỗ trợ, giờ làm việc, nhân viên, khiếu nại, dữ liệu

### Nội dung

DỮ LIỆU DEMO HƯ CẤU — CHỈ ĐỂ KIỂM THỬ, KHÔNG ÁP DỤNG CHO GIAO DỊCH THẬT. Các thời hạn và mức phí dưới đây là giả định kiểm thử, chưa được shop nào phê duyệt.

1. Trong kịch bản mẫu, nhân viên hỗ trợ từ 09:00 đến 17:00, thứ Hai đến thứ Sáu, trừ ngày lễ. Mục tiêu phản hồi ban đầu là trong 1 ngày làm việc; không đồng nghĩa xử lý xong yêu cầu trong 1 ngày.
2. Kịch bản chưa có số điện thoại, email hoặc địa chỉ nhận hàng trả thật. Khi cần các thông tin này, trợ lý phải nói chưa được cung cấp, không tự tạo thông tin liên hệ.
3. Trợ lý giải thích chính sách từ các nguồn đã công bố và nêu nguồn tham khảo. Trợ lý không truy cập trạng thái đơn trực tiếp, không tự hủy đơn, thu tiền, duyệt hoàn tiền hoặc quyết định quyền lợi trong trường hợp tranh chấp.
4. Với trường hợp ngoài quy định hoặc nguồn mâu thuẫn, chuyển nhân viên kiểm tra. Không coi dữ liệu DEMO là chính sách chính thức hoặc quy định pháp luật áp dụng.
5. Khách không nên gửi mật khẩu, OTP, thông tin thẻ hoặc ảnh giấy tờ cá nhân vào câu hỏi. Chỉ cung cấp mã đơn và thông tin tối thiểu khi trao đổi với nhân viên qua kênh chính thức đã được xác minh.
6. Nội dung về giờ hỗ trợ, thời hạn và quyền lợi của shop mẫu chỉ phục vụ kiểm thử. Các điều khoản về vận hành website Policy Assistant là bộ tài liệu riêng, không tự trở thành chính sách của shop.
