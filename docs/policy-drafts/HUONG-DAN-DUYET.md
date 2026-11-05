# Hướng dẫn duyệt và đưa vào sử dụng

Ngày soạn: 30/10/2026. Trạng thái: dự thảo, chưa công bố.

## 1. Bốn trường phải điền

| Ký hiệu | Cần cung cấp |
| --- | --- |
| [TEN_DON_VI_VAN_HANH] | Tên cá nhân/tổ chức chịu trách nhiệm, không suy ra tên pháp lý từ email. |
| [DIA_CHI_LIEN_HE] | Địa chỉ phù hợp để công bố và tiếp nhận liên hệ. |
| [EMAIL_HO_TRO] | Địa chỉ được đồng ý công khai và có người tiếp nhận. |
| [NGAY_HIEU_LUC] | Ngày chính thức sau khi duyệt, không tự dùng ngày soạn. |

## 2. Quyết định và kiểm tra trước ban hành

- Rà soát pháp lý theo đối tượng khách hàng và nơi cung cấp dịch vụ, đặc biệt dữ liệu cá nhân và xử lý ngoài Việt Nam. Luật 91/2025/QH15 có hiệu lực từ 01/01/2026; bộ này không chứng nhận tuân thủ.
- Xác định vai trò các bên, căn cứ xử lý, cơ chế thông báo/đồng ý và rút lại đồng ý. Không suy ra đồng ý mọi mục đích chỉ từ đăng nhập. Chốt phạm vi dữ liệu nhạy cảm, trẻ em và dữ liệu của bên thứ ba cùng quy trình cần thiết.
- Phê duyệt đầu mối tiếp nhận, cách xác minh yêu cầu, quy trình sự cố và các thời hạn pháp luật áp dụng. Chỉ bổ sung cam kết phản hồi khi có người phụ trách thực hiện.
- Kiểm kê log/bản sao lưu tồn tại, kể cả log lịch sử trước phiên bản mới; đối chiếu thời hạn nhóm log quản lý 14–30 ngày và cửa sổ khôi phục DynamoDB. Không hứa xóa PDF tự xóa luôn mọi đoạn trích đã lưu trong lịch sử.
- Đối chiếu hạn mức với cấu hình triển khai ngay trước ngày ban hành. Bản này dựa trên mã nguồn, không khẳng định tham số AWS không thể được thay đổi về sau.
- Chốt việc thu phí. Chưa có biểu giá/hoàn tiền được duyệt; không dùng chính sách DEMO hoàn tiền 30 ngày hoặc ngân sách AWS 30–50 USD làm điều kiện bán hàng.
- Chốt nơi lưu nội dung phiên bản và hồ sơ duyệt. Nhật ký quản trị chỉ ghi thao tác, không phải kho phiên bản đầy đủ.

## 3. Cách đưa lên sau khi duyệt

1. Điền các trường còn trống, duyệt nội dung và ngày áp dụng. Chỉ bỏ chữ DỰ THẢO khi đã phê duyệt; có thể đổi mã DRAFT-PA-... thành PA-... cho bản chính thức. Giữ bản nháp và bản duyệt riêng.
2. Vào Quản trị → Xuất bản hoặc cập nhật chính sách. Sao chép Mã chính sách, Nhóm, Tiêu đề, Từ khóa và phần Nội dung của từng tệp. Không đưa toàn bộ tài liệu hướng dẫn vào một chính sách.
3. Kiểm tra rồi bấm Lưu chính sách. Đây là công bố ngay, không phải lưu nháp riêng. Chỉ thực hiện sau khi duyệt.
4. Tìm lại trong Chính sách chung, hỏi thử và đối chiếu nguồn.
5. Đồng bộ bản đã duyệt vào trang Quyền riêng tư, Điều khoản, thông báo đăng ký/tải lên và cơ chế ghi nhận chấp thuận cần thiết. Lưu trong Quản trị không tự sửa những trang đó.
6. Khi thay dữ liệu DEMO, chỉ xử lý đúng các bản thử đã nhận diện; không ghi đè hoặc xóa chính sách thật. Xóa PDF không tự xóa cuộc hỏi đáp và đoạn trích trong lịch sử.

JSON đi kèm lưu sáu bộ trường để sao chép hoặc phục vụ tích hợp về sau. Giao diện chưa có nút nhập hàng loạt JSON. Bộ tài liệu không chứa script tự đăng hoặc sửa dữ liệu AWS.

## 4. Câu hỏi kiểm tra sau khi ban hành

| Câu hỏi | Điểm cần có trong câu trả lời kèm nguồn |
| --- | --- |
| PDF tối đa bao nhiêu MiB/trang? | 10 MiB; 100 trang văn bản hoặc 10 trang scan. |
| Mỗi ngày được tải/hỏi bao nhiêu lượt? | 5 lượt tải; 20 câu hỏi; hạn mức chung có thể hết trước. |
| Ngày mới tính hạn mức theo giờ Việt Nam bắt đầu khi nào? | 07:00, do bộ đếm dùng UTC. |
| Chọn PDF riêng có loại chính sách chung khỏi tìm kiếm không? | Không. |
| Xóa PDF có tự xóa đoạn trích trong lịch sử không? | Không; xóa lịch sử riêng, chờ hết hạn hoặc xóa tài khoản. |
| Dữ liệu có chỉ xử lý ở Việt Nam không? | Không; Singapore và suy luận APAC có thể xử lý ngoài Việt Nam. |
| AI có bảo đảm đúng tuyệt đối không? | Không; phải đối chiếu nguồn. |
| Liên hệ hỗ trợ ở đâu? | Email đã duyệt, không còn ký hiệu [EMAIL_HO_TRO]. |

## 5. Căn cứ và phạm vi rà soát

Đã đọc mã nguồn ngày 30/10/2026: frontend/privacy.html, frontend/terms.html, policy_assistant/service.py, policy_assistant/pipeline.py, policy_assistant/assistant.py, template.yaml và docs/production-runbook.md của project policy-assistant.

- Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15, hiệu lực 01/01/2026: https://chinhphu.vn/?classid=1&docid=214590&orggroupid=1&pageid=27160
- Bộ Công an, quyền của chủ thể dữ liệu theo Luật 91/2025/QH15: https://bocongan.gov.vn/chinh-sach-phap-luat/bai-viet/luat-bao-ve-du-lieu-ca-nhan-chinh-thuc-co-hieu-luc-thi-hanh-tu-ngay-01-01-2026-1767186124
- AWS, bảo vệ dữ liệu Bedrock và trách nhiệm cấu hình của khách hàng: https://docs.aws.amazon.com/bedrock/latest/userguide/data-protection.html

Chưa thực hiện đánh giá pháp lý đầy đủ, hồ sơ chuyển dữ liệu xuyên biên giới, thỏa thuận xử lý dữ liệu, đánh giá tác động hoặc chứng nhận tuân thủ cho đơn vị vận hành. Cần hoàn tất những phần áp dụng trước khi công bố chính thức.
