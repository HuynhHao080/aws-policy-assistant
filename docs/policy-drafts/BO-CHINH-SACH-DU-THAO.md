# Bộ chính sách dự thảo — Policy Assistant

Phiên bản 0.1 · Soạn ngày 30/10/2026 · CHƯA BAN HÀNH

Bộ này dành cho chính website Policy Assistant, đối chiếu mã nguồn hiện tại. Chưa công bố lên website và chưa thay thế phê duyệt hoặc rà soát pháp lý. Đọc HUONG-DAN-DUYET.md trước khi dùng.

Cần chốt bốn trường: [TEN_DON_VI_VAN_HANH], [DIA_CHI_LIEN_HE], [EMAIL_HO_TRO], [NGAY_HIEU_LUC]. Không tự dùng email nhận cảnh báo AWS làm địa chỉ hỗ trợ công khai.

Mỗi mục có đủ các ô tương ứng biểu mẫu Quản trị. Nút Lưu chính sách công bố ngay cho các tài khoản sử dụng; chưa có chức năng lưu nháp/phê duyệt nhiều bước.


---

## 1. Dự thảo — Điều khoản sử dụng và tài khoản Policy Assistant

**Mã chính sách:** `DRAFT-PA-TERMS-001`

**Nhóm:** Dự thảo — Sử dụng dịch vụ

**Tiêu đề:** Dự thảo — Điều khoản sử dụng và tài khoản Policy Assistant

**Từ khóa:** điều khoản, tài khoản, đăng ký, mật khẩu, phí dịch vụ

### Nội dung

DỰ THẢO — CHƯA BAN HÀNH
Phiên bản 0.1 · Ngày soạn 30/10/2026
Đơn vị vận hành: [TEN_DON_VI_VAN_HANH]
Địa chỉ liên hệ: [DIA_CHI_LIEN_HE]
Email hỗ trợ công khai: [EMAIL_HO_TRO]
Ngày có hiệu lực: [NGAY_HIEU_LUC]
Nội dung cần được chủ dự án duyệt trước khi có hiệu lực.

1. Phạm vi dịch vụ
Policy Assistant hỗ trợ quản lý PDF riêng, tìm kiếm chính sách chung và hỏi đáp AI có nguồn tham khảo. Người dùng cần kiểm tra tài liệu gốc trước khi sử dụng kết quả cho quyết định quan trọng.

2. Tài khoản
Đăng ký bằng email có quyền sử dụng và hoàn tất xác nhận email. Giữ bí mật mật khẩu, không chia sẻ phiên đăng nhập, đăng xuất khi dùng thiết bị chung. Khi nghi ngờ truy cập trái phép, thực hiện khôi phục mật khẩu và liên hệ bộ phận hỗ trợ.

3. Sử dụng có trách nhiệm
Chỉ cung cấp nội dung mà bạn có quyền cho phép dịch vụ và các bên xử lý liên quan sử dụng. Không tải mã độc, mật khẩu, khóa truy cập hoặc nội dung xâm phạm quyền của người khác. Không thử truy cập dữ liệu không thuộc quyền của mình, gây gián đoạn hoặc dùng nhiều tài khoản để né hạn mức.

4. Dữ liệu riêng và chính sách chung
PDF và lịch sử hỏi đáp được phân quyền theo tài khoản. Chính sách chung do quản trị viên công bố được cung cấp cho các tài khoản sử dụng và có thể được dùng làm nguồn trả lời. Không đưa dữ liệu khách hàng hoặc tài liệu cần bảo mật vào chính sách chung.

5. Giới hạn dịch vụ
Chất lượng và thời gian xử lý phụ thuộc tài liệu, kết nối, hạn mức và hạ tầng. Chưa có cam kết hoạt động liên tục, thời gian xử lý cố định hoặc độ chính xác tuyệt đối. Thay đổi ảnh hưởng đến cách sử dụng cần được công bố cùng phiên bản và ngày áp dụng.

6. Phí và quyền của người dùng
Bản nháp chưa thiết lập giá bán, gói trả phí hoặc điều kiện hoàn tiền. Ngân sách AWS của đơn vị vận hành không phải giá bán cho khách hàng. Trước khi thu phí phải có chính sách giá, thanh toán và hoàn tiền được duyệt. Nội dung này không loại trừ quyền hoặc trách nhiệm bắt buộc theo pháp luật áp dụng.

7. Liên hệ và hiệu lực
Liên hệ [EMAIL_HO_TRO]. Cơ chế thông báo và ghi nhận chấp thuận điều khoản phải được hoàn tất trước khi ban hành. Chỉ đăng nội dung trong Chính sách chung chưa chứng minh người dùng đã chấp thuận.


---

## 2. Dự thảo — Tải lên, xử lý và quản lý tài liệu PDF

**Mã chính sách:** `DRAFT-PA-DOCUMENTS-001`

**Nhóm:** Dự thảo — Tài liệu

**Tiêu đề:** Dự thảo — Tải lên, xử lý và quản lý tài liệu PDF

**Từ khóa:** PDF, tải lên, OCR, scan, tài liệu riêng, quyền sở hữu

### Nội dung

DỰ THẢO — CHƯA BAN HÀNH
Phiên bản 0.1 · Ngày soạn 30/10/2026
Đơn vị vận hành: [TEN_DON_VI_VAN_HANH]
Địa chỉ liên hệ: [DIA_CHI_LIEN_HE]
Email hỗ trợ công khai: [EMAIL_HO_TRO]
Ngày có hiệu lực: [NGAY_HIEU_LUC]
Nội dung cần được chủ dự án duyệt trước khi có hiệu lực.

1. Tệp được hỗ trợ
Mỗi tệp là PDF không mã hóa, tối đa 10 MiB. Giới hạn là 100 trang với PDF có văn bản hoặc 10 trang với PDF cần nhận dạng chữ từ ảnh bằng OCR. Tổng văn bản trích xuất bị giới hạn ở 300.000 ký tự. Tệp hỏng, mã hóa, quá giới hạn hoặc không đọc được có thể bị từ chối.

2. Quyền đối với tài liệu
Tải lên không tự chuyển quyền sở hữu tài liệu cho đơn vị vận hành. Người tải cần có quyền cho phép lưu, trích xuất, tìm kiếm và xử lý qua các dịch vụ AWS nêu trong chính sách quyền riêng tư. Tài liệu có dữ liệu của người khác cần có căn cứ xử lý phù hợp trước khi tải.

3. Nội dung cần loại bỏ
Không tải mật khẩu, khóa API, thông tin thanh toán bí mật hoặc tài liệu không được phép đưa lên dịch vụ đám mây. Với dữ liệu nhạy cảm hoặc dữ liệu trẻ em, chỉ tải khi đơn vị vận hành đã xác nhận phạm vi và điều kiện pháp lý cần thiết. Người dùng tự kiểm tra và che dữ liệu không cần thiết; hệ thống chưa cam kết tự nhận diện hay tự che mọi dữ liệu cá nhân.

4. Xử lý và chất lượng
Sau khi bấm Tải lên và xử lý, tài liệu được đưa vào hàng đợi để trích xuất văn bản hoặc OCR và tạo dữ liệu tìm kiếm. Chỉ tài liệu xử lý xong được dùng làm nguồn trả lời. PDF scan mờ, chữ viết tay, bảng biểu và cách dàn trang phức tạp có thể được đọc thiếu hoặc sai. Kiểm tra đoạn trích với bản gốc.

5. Quản lý tài liệu
Trong Tài liệu của tôi, chủ tài khoản có thể đổi tên, tải xuống và yêu cầu xóa. PDF riêng không tự trở thành chính sách chung. Trang quản trị chính sách không cung cấp chức năng xem PDF riêng của khách hàng; quyền kỹ thuật của người vận hành hạ tầng là phạm vi riêng.

6. Xóa và lỗi xử lý
Khi tác vụ xóa thành công, các phiên bản tệp nguồn và nội dung trích xuất của tài liệu được xóa. Tác vụ đang xử lý có thể cần hoàn tất trước khi xóa. Việc xóa lịch sử và thời hạn bản sao lưu được nêu riêng trong chính sách quyền riêng tư. Nếu gặp lỗi, ghi lại thời điểm và thông báo lỗi để hỗ trợ, tránh tải lại nhiều lần liên tục.


---

## 3. Dự thảo — Quyền riêng tư, lưu giữ và xóa dữ liệu

**Mã chính sách:** `DRAFT-PA-PRIVACY-001`

**Nhóm:** Dự thảo — Quyền riêng tư

**Tiêu đề:** Dự thảo — Quyền riêng tư, lưu giữ và xóa dữ liệu

**Từ khóa:** quyền riêng tư, dữ liệu cá nhân, AWS, lưu giữ, xóa tài khoản, sao lưu

### Nội dung

DỰ THẢO — CHƯA BAN HÀNH
Phiên bản 0.1 · Ngày soạn 30/10/2026
Đơn vị vận hành: [TEN_DON_VI_VAN_HANH]
Địa chỉ liên hệ: [DIA_CHI_LIEN_HE]
Email hỗ trợ công khai: [EMAIL_HO_TRO]
Ngày có hiệu lực: [NGAY_HIEU_LUC]
Nội dung cần được chủ dự án duyệt trước khi có hiệu lực.

1. Đầu mối phụ trách
[TEN_DON_VI_VAN_HANH], địa chỉ [DIA_CHI_LIEN_HE], email [EMAIL_HO_TRO], tiếp nhận yêu cầu liên quan đến dữ liệu của dịch vụ. Vai trò và trách nhiệm pháp lý của đơn vị cùng các bên xử lý phải được chốt trước khi ban hành.

2. Dữ liệu và mục đích
Email, mã tài khoản và thông tin xác thực cần thiết phục vụ đăng nhập. PDF, tên tệp, văn bản trích xuất và dữ liệu tìm kiếm phục vụ quản lý tài liệu và truy xuất nguồn. Câu hỏi, câu trả lời và đoạn trích phục vụ hỏi đáp và lịch sử. Bộ đếm phục vụ hạn mức; nhật ký và bản ghi quản trị phục vụ xử lý lỗi, an toàn và kiểm tra thay đổi chính sách.

3. Nhà cung cấp và nơi xử lý
Dịch vụ sử dụng AWS: Cognito cho xác thực, S3/DynamoDB cho lưu trữ, Textract cho OCR và Bedrock cho tìm kiếm ngữ nghĩa, tạo câu trả lời. Cấu hình chính tại Singapore. Khi lập chỉ mục, văn bản được gửi tới mô hình nhúng. Khi hỏi đáp, câu hỏi và tối đa năm đoạn liên quan được gửi tới mô hình tạo câu trả lời. Suy luận APAC có thể xử lý tại các vùng AWS ngoài Singapore và ngoài Việt Nam. Không dùng dịch vụ cho tài liệu bắt buộc chỉ lưu hoặc xử lý tại Việt Nam khi chưa có phương án được duyệt. Đơn vị vận hành cần xác định căn cứ xử lý, thông báo/đồng ý và nghĩa vụ chuyển dữ liệu ra nước ngoài áp dụng cho mình trước khi ban hành.

4. Phạm vi truy cập
Ứng dụng phân quyền PDF và lịch sử theo tài khoản sở hữu. Quản trị viên ứng dụng quản lý chính sách chung, không mặc nhiên xem PDF riêng qua trang quản trị. Người vận hành hạ tầng AWS có quyền kỹ thuật theo phân quyền vận hành. Người có liên kết tải tạm có thể sử dụng trong thời gian liên kết còn hiệu lực; không chia sẻ liên kết đó.

5. Thời hạn lưu giữ
PDF đã xử lý và dữ liệu tìm kiếm được giữ tới khi yêu cầu xóa được xử lý thành công. Lịch sử hỏi đáp có thời hạn 30 ngày. Tệp tải tạm trong luồng mới được cấu hình dọn sau hai ngày. Dấu vết xóa tài liệu có thời hạn 30 ngày; bộ đếm/trạng thái phục vụ vận hành khoảng 65 ngày; nhật ký quản trị 90 ngày. Các nhóm nhật ký ứng dụng được quản lý trong cấu hình lưu 14–30 ngày tùy loại. Cơ chế dọn tự động có độ trễ; không bảo đảm mọi dữ liệu biến mất đúng thời điểm hết hạn. Nhật ký lịch sử và các hệ thống sao lưu có phạm vi riêng cần được kiểm kê trước khi ban hành.

6. Xóa PDF không tự xóa mọi đoạn trích đã lưu
Sau khi xóa PDF thành công, các phiên bản nguồn và dữ liệu trích xuất được xóa. Câu trả lời và đoạn trích đã lưu trong lịch sử có thể vẫn còn đến khi xóa cuộc hỏi đáp, hết thời hạn lưu hoặc xóa tài khoản. Bạn có thể xóa từng cuộc hỏi đáp trong Lịch sử hỏi đáp và xuất lịch sử ở mục Tài khoản. Tệp đã tải hoặc xuất ra thiết bị của bạn nằm ngoài phạm vi xóa của ứng dụng.

7. Xóa tài khoản và sao lưu
Tại mục Tài khoản, nhập DELETE rồi xác nhận xóa. Hệ thống chặn truy cập trước, xử lý xóa PDF/lịch sử rồi xóa danh tính đăng nhập. Đây là tác vụ nền, có thể cần thử lại khi lỗi; chưa cam kết xong trong số phút cố định. Không thể hoàn tác từ ứng dụng. Bản ghi vận hành còn theo thời hạn nêu trên. Sao lưu khôi phục DynamoDB có thể còn dữ liệu đã xóa trong cửa sổ tới 35 ngày; bản sao lưu không hiển thị như dữ liệu hoạt động và không phải tính năng khôi phục tài khoản cho khách hàng.

8. Yêu cầu về dữ liệu cá nhân
Bạn có thể gửi yêu cầu được biết, truy cập, chỉnh sửa, cung cấp, xóa, hạn chế hoặc phản đối xử lý dữ liệu; rút lại đồng ý khi việc xử lý dựa trên đồng ý; và phản ánh, khiếu nại theo quy định áp dụng. Gửi yêu cầu tới [EMAIL_HO_TRO]. Đơn vị vận hành có thể cần xác minh người yêu cầu bằng thông tin phù hợp; không gửi mật khẩu hoặc OTP. Thời hạn và cách giải quyết phải theo quy định áp dụng, không tự đặt một thời hạn cố định trong bản nháp.

9. Bảo mật và sự cố
Hệ thống sử dụng HTTPS, lưu trữ riêng và phân quyền tài khoản; không có bảo đảm tuyệt đối loại bỏ mọi sự cố. Nếu nghi lộ dữ liệu, bảo vệ tài khoản, ngừng chia sẻ liên kết và báo đầu mối hỗ trợ. Quy trình đánh giá, xử lý, thông báo sự cố và người chịu trách nhiệm phải được phê duyệt trước khi công bố.


---

## 4. Dự thảo — Sử dụng AI, trích dẫn và giới hạn câu trả lời

**Mã chính sách:** `DRAFT-PA-AI-001`

**Nhóm:** Dự thảo — Hỏi đáp AI

**Tiêu đề:** Dự thảo — Sử dụng AI, trích dẫn và giới hạn câu trả lời

**Từ khóa:** AI, trích dẫn, nguồn, độ chính xác, câu trả lời, tài liệu

### Nội dung

DỰ THẢO — CHƯA BAN HÀNH
Phiên bản 0.1 · Ngày soạn 30/10/2026
Đơn vị vận hành: [TEN_DON_VI_VAN_HANH]
Địa chỉ liên hệ: [DIA_CHI_LIEN_HE]
Email hỗ trợ công khai: [EMAIL_HO_TRO]
Ngày có hiệu lực: [NGAY_HIEU_LUC]
Nội dung cần được chủ dự án duyệt trước khi có hiệu lực.

1. Nguồn được sử dụng
AI tìm các đoạn liên quan trong chính sách chung đã công bố và PDF riêng mà tài khoản có quyền truy cập. Có thể chọn tối đa 10 PDF đã xử lý. Nếu không chọn, hệ thống xem xét tối đa 20 bản ghi tài liệu gần nhất của tài khoản và dùng tài liệu đủ điều kiện cùng chính sách chung. Chọn PDF riêng không loại chính sách chung khỏi tìm kiếm.

2. Phạm vi trả lời
Tối đa năm đoạn liên quan được chọn để tạo câu trả lời. Tìm kiếm có giới hạn; không bảo đảm đọc toàn bộ kho trong mỗi câu hỏi. Khi thiếu cơ sở, hệ thống có thể báo chưa đủ thông tin thay vì đưa ra kết luận.

3. Kiểm chứng nguồn
Nguồn hiển thị tên tài liệu/chính sách, đoạn trích và số trang PDF nếu có. Mở nguồn và so với bản gốc trước khi áp dụng. Có trích dẫn không bảo đảm mọi diễn giải đều đúng, đầy đủ hoặc còn hiệu lực.

4. Giới hạn của AI
AI có thể hiểu sai, bỏ sót điều kiện, nhầm phạm vi hoặc dùng đoạn OCR chưa chính xác. Không dùng câu trả lời làm căn cứ duy nhất cho quyết định pháp lý, tài chính, y tế, nhân sự hoặc quyết định ảnh hưởng lớn. Khi cần, tham khảo người có chuyên môn và văn bản có hiệu lực.

5. Nguồn mâu thuẫn và bản nháp
Khi nguồn mâu thuẫn, kiểm tra phiên bản, ngày hiệu lực và phạm vi; không coi AI là bên quyết định hiệu lực pháp lý của tài liệu. Nội dung DEMO và DỰ THẢO chỉ phục vụ thử nghiệm/rà soát, chưa phải chính sách chính thức.

6. Dữ liệu câu hỏi và phản ánh
Câu hỏi và đoạn nguồn được xử lý qua AWS như mô tả trong chính sách quyền riêng tư. Chỉ nhập dữ liệu cần thiết; không nhập mật khẩu, OTP hay khóa truy cập. Báo lỗi tới [EMAIL_HO_TRO] với câu hỏi, thời điểm, tên nguồn và điểm cần sửa. Chỉ chia sẻ nội dung được phép. Sửa chính sách chung không tự viết lại câu trả lời đã lưu trong lịch sử.


---

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


---

## 6. Dự thảo — Hỗ trợ, phản ánh và công bố chính sách

**Mã chính sách:** `DRAFT-PA-SUPPORT-001`

**Nhóm:** Dự thảo — Hỗ trợ và quản trị

**Tiêu đề:** Dự thảo — Hỗ trợ, phản ánh và công bố chính sách

**Từ khóa:** hỗ trợ, liên hệ, khiếu nại, quản trị, cập nhật, chính sách chung

### Nội dung

DỰ THẢO — CHƯA BAN HÀNH
Phiên bản 0.1 · Ngày soạn 30/10/2026
Đơn vị vận hành: [TEN_DON_VI_VAN_HANH]
Địa chỉ liên hệ: [DIA_CHI_LIEN_HE]
Email hỗ trợ công khai: [EMAIL_HO_TRO]
Ngày có hiệu lực: [NGAY_HIEU_LUC]
Nội dung cần được chủ dự án duyệt trước khi có hiệu lực.

1. Kênh tiếp nhận
Đơn vị phụ trách: [TEN_DON_VI_VAN_HANH]. Địa chỉ: [DIA_CHI_LIEN_HE]. Email: [EMAIL_HO_TRO]. Cần xác nhận đầu mối có người tiếp nhận thực tế trước khi ban hành. Chưa công bố lịch trực hay thời gian phản hồi cố định; không hiểu là hỗ trợ tức thời hoặc 24/7. Yêu cầu thuộc diện pháp luật quy định vẫn phải được giải quyết trong thời hạn áp dụng.

2. Gửi yêu cầu hỗ trợ
Nêu vấn đề, thời điểm, thao tác đã thực hiện, tên tài liệu nếu cần và thông báo lỗi. Với AI, nêu câu hỏi, nguồn và điểm cần kiểm tra. Chỉ gửi dữ liệu tối thiểu; không gửi mật khẩu, OTP, khóa AWS/API hoặc liên kết tải tài liệu còn hiệu lực.

3. Sự cố tài khoản hoặc dữ liệu
Nếu nghi tài khoản bị chiếm quyền, khôi phục mật khẩu và báo hỗ trợ. Khi báo dấu hiệu lộ dữ liệu, mô tả phạm vi đã quan sát; tránh chuyển tiếp tài liệu của người khác. Người vận hành đánh giá và xử lý theo quy trình sự cố được duyệt.

4. Công bố chính sách chung
Chỉ quản trị viên được công bố, cập nhật hoặc xóa chính sách chung. Trước khi lưu cần kiểm tra nguồn nội dung, người duyệt, phạm vi, ngày hiệu lực và dữ liệu cần che. Không dùng chính sách chung để lưu hồ sơ cá nhân hoặc tài liệu nội bộ cần giới hạn người xem.

5. Phiên bản và nhật ký
Chính sách chính thức cần có mã, phiên bản, ngày hiệu lực và người phụ trách. Nhật ký quản trị ghi thao tác, không thay thế kho lưu nội dung cũ và hồ sơ phê duyệt. Khi cập nhật, lưu bản trước đó ở nơi quản lý tài liệu riêng để đối chiếu.

6. Bản nháp và các trang thông tin
Nội dung DEMO hoặc DỰ THẢO không phải cam kết chính thức. Đăng vào kho hỏi đáp không tự sửa trang Quyền riêng tư, Điều khoản hoặc màn hình đăng ký. Khi ban hành phải đồng bộ các nơi đó và cơ chế thông báo/chấp thuận phù hợp.

7. Phản ánh và quyền người dùng
Gửi yêu cầu tới [EMAIL_HO_TRO]. Đơn vị vận hành xác minh khi cần và trả lời theo quy định áp dụng. Chính sách nội bộ không được dùng để tước bỏ quyền khiếu nại hoặc các quyền hợp pháp khác.
