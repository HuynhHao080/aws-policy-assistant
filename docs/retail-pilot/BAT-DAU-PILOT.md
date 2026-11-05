# Kế hoạch pilot một shop

Ngày soạn 30/10/2026. Bối cảnh hư cấu, chưa phải shop kinh doanh thật.

## Mục tiêu

Giúp nhân viên CSKH tra cứu điều kiện bán hàng/hậu mãi từ nguồn được duyệt. Bản đầu trả lời và dẫn nguồn, không tự hủy đơn, thu tiền hoặc duyệt hoàn tiền. Chưa tích hợp trạng thái đơn, tồn kho, thanh toán hoặc hãng vận chuyển.

## Thứ tự thao tác

1. Đọc BO-DEMO-5-CHINH-SACH.md. Các con số đều là giả định kiểm thử, không đưa thành cam kết cho khách thật.
2. Nếu chọn thử trên ứng dụng hiện tại, vào Quản trị và nhập từng mã, nhóm, tiêu đề, từ khóa, nội dung. Lưu chính sách công bố ngay cho các tài khoản. Giữ nguyên nhãn DEMO. JSON đi kèm chỉ là dữ liệu tham khảo; giao diện chưa có nút nhập hàng loạt.
3. Kiểm tra Chính sách chung tìm được các mã DEMO-SHOP. Không xóa hoặc ghi đè các bản DEMO cũ/nguồn khác một cách hàng loạt. Chúng có thể cùng được truy xuất và ảnh hưởng đáp án; ghi lại mã nguồn thực tế khi câu trả lời dùng nguồn ngoài bộ pilot.
4. Không chọn PDF không liên quan. Lưu ý khi không chọn, ứng dụng vẫn có thể dùng tài liệu gần đây của tài khoản. Để có kết quả độc lập, dùng một tài khoản thử không có PDF riêng hoặc theo dõi kỹ nguồn của từng câu. Không tự xóa PDF thật để làm sạch môi trường.
5. Hỏi lần lượt 30 câu trong tệp kiểm thử. Ghi kết quả thực tế và nguồn vào CSV. Tệp đáp án kỳ vọng không nên được công bố làm chính sách hoặc tải làm nguồn, vì sẽ làm sai mục tiêu kiểm thử.
6. Với mỗi câu sai, ghi lỗi nguồn, lỗi truy xuất hay lỗi diễn giải; sửa nguyên nhân và thử lại. Nhật ký cần phân biệt lượt chạy và phiên bản chính sách. Một lượt đầy đủ là 30 câu hỏi; tài khoản hiện bị giới hạn 20 câu/ngày UTC, nên chia hai ngày, không tạo tài khoản để né hạn mức.
7. Khi có shop thật, thay giả định bằng chính sách được chủ shop duyệt; chốt kênh hỗ trợ và cách chuyển nhân viên trước khi mời khách.

## Tiêu chí thử nghiệm đề xuất

- Ít nhất 27/30 câu đúng và có nguồn phù hợp ở một lượt đánh giá, đồng thời các câu 5, 10, 22, 26, 29 và 30 về thiếu dữ liệu/chống làm sai nguồn phải đạt; các câu 7, 18, 25 và 28 về thời hạn/cam kết cũng cần được rà soát kỹ. Không dùng tỷ lệ chung để bỏ qua câu bịa quyền lợi hoặc thông tin liên hệ.
- Mọi câu có nội dung bịa cam kết tài chính, liên hệ, giá/tồn kho hoặc tự nhận đã hủy/hoàn tiền đều cần sửa trước khi thử với khách thật, dù tổng điểm đạt mục tiêu.
- Không trả lời từ chính sách shop khác. Hỏi không rõ phải xác định điều kiện còn thiếu hoặc chuyển nhân viên.
- Đo thời gian nhân viên tìm câu trả lời theo cách cũ và khi dùng trợ lý; chỉ kết luận tiết kiệm thời gian sau khi đo.
- Theo dõi lượt sử dụng và chi phí AWS thực tế. Ngân sách 30–50 USD là mục tiêu vận hành, không phải giá bán hoặc bảo đảm chi phí.

## Trước khi phục vụ nhiều shop

Cần thêm không gian riêng theo shop, quản lý thành viên và phân quyền nguồn theo shop. Không đưa chính sách riêng của nhiều shop vào kho Chính sách chung hiện tại. Tiếp theo mới xem xét phiên bản/ngày hiệu lực, chuyển nhân viên và tích hợp kênh bán hàng.

## Bộ tệp

- BO-DEMO-5-CHINH-SACH.md: năm chính sách để đọc và sao chép theo biểu mẫu.
- 01 đến 05: từng chính sách riêng.
- 30-CAU-HOI-KIEM-THU.md và .csv: câu hỏi/đáp án kỳ vọng cùng ô ghi kết quả.
- du-lieu-demo.json: dữ liệu có cấu trúc, không tự đăng lên website.

Toàn bộ dữ liệu là hư cấu, không được dùng thay chính sách đã duyệt hoặc tư vấn pháp lý cho một cửa hàng thật.
