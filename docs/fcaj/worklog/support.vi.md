---
title: "Phối hợp hỗ trợ — phân công và ghi chú nội bộ"
weight: 5
---

# Phối hợp xử lý yêu cầu hỗ trợ

Phần này có AI hỗ trợ và cần sinh viên tự rà soát, giải thích trước khi nộp; không phải nhật ký sinh viên tự thực hiện hoặc xác nhận điểm FCAJ. [Ứng dụng bản chính](https://djreo5eptvwk5.cloudfront.net/) vẫn dùng chính sách DEMO.

## Bài toán thực tế

Hai nhân viên cùng mở một yêu cầu dễ trả lời trùng hoặc mất thông tin bàn giao. Quản trị có thể nhận việc cho chính mình, bỏ nhận hoặc tiếp quản kèm lý do. Bộ lọc “của tôi / chưa nhận / người khác” giúp phân luồng. Người đang nhận việc mới được phản hồi khách, đổi trạng thái hoặc ưu tiên; quản trị khác phải tiếp quản rõ ràng trước. Mọi quản trị vẫn đọc được ghi chú: đây là phối hợp công việc, chưa có vai trò nhân viên hạn chế quyền riêng.

Khung “Chỉ nhân viên thấy” tách ghi chú khỏi “Nội dung gửi cho khách”. Có cảnh báo bản nháp chưa lưu, tải lại yêu cầu và xử lý revision cũ bằng xung đột thay vì ghi đè. ID nhân viên được rút gọn; chưa có danh bạ, thông báo realtime, email tự động hoặc bộ đếm SLA.

## Dữ liệu và tính nhất quán

- Ghi chú tối đa 20 mục × 1.000 ký tự; lịch sử phân công giữ 10 sự kiện gần nhất. Tin nhắn công khai có giới hạn riêng 20 × 1.500 ký tự.
- Assignment chỉ lấy từ danh tính JWT đã xác thực. Tiếp quản cần lý do 10–300 ký tự. Khách không tự ghi được trường nội bộ.
- Revision dùng chung với hội thoại khách. DynamoDB transaction kiểm revision và trạng thái xóa tài khoản; ghi đồng thời thất bại thì tải lại, đọc nội dung mới rồi thao tác lại.
- API chi tiết/danh sách/xuất JSON của khách loại bỏ ghi chú, người nhận và lý do, kể cả quản trị đang dùng trang khách của mình. Ghi chú không đi vào nguồn AI.
- Ghi chú và phân công cùng vòng đời yêu cầu tối đa 90 ngày, không kéo dài hạn khi nhân viên ghi chú. Xóa tài khoản khách dọn yêu cầu; xóa tài khoản nhân viên không tự xóa đóng góp trong yêu cầu của khách. Audit chỉ lưu metadata hành động, không lưu nội dung ghi chú/lý do. TTL có thể dọn trễ, ứng dụng vẫn chặn bản hết hạn.

Không thêm table/index/route/IAM grant hoặc dịch vụ AWS. Lọc dùng scan có giới hạn và phân trang, không phải số tổng toàn bộ hàng đợi.

## Kiểm chứng đã thực hiện

| Phạm vi | Kết quả |
|---|---|
| Python 3.12 | 322 đạt, 11 live opt-in bỏ qua; unit dùng fixture/mocks, không phải gọi model thật |
| Frontend | 67 đạt bằng unit/DOM giả lập; chưa phải nghiệm thu hình ảnh trình duyệt |
| API AWS thật | 20 kiểm tra HTTP với 3 tài khoản QA không gửi thư mời và 1 yêu cầu hỗ trợ có đồng ý giả lập |
| Dọn thử nghiệm | 3 tài khoản đã xóa; partition Support của khách thử đã trống; audit metadata giữ theo vòng đời |
| Artifact | 40 tệp frontend và 6 Lambda khớp hash, stack UPDATE_COMPLETE, invalidation Completed |

Run thực tế không gọi model, embedding, PDF/OCR, email hoặc dữ liệu khách thật. Bằng chứng có timestamp UTC 05/11/2026, tương ứng 06/11 tại Việt Nam. [JSON đã lọc](/aws-internship-worklog/evidence/support-team.json) chứa danh sách kiểm tra và hash canonical JSON của báo cáo nguồn; không xuất token, ID khách hay nội dung yêu cầu.

[Báo cáo nguồn và giới hạn](https://github.com/HuynhHao080/aws-policy-assistant/blob/main/docs/support-team-verification.md). [Hướng dẫn quản trị](https://github.com/HuynhHao080/aws-policy-assistant/blob/main/docs/HUONG-DAN-PHOI-HOP-HO-TRO.md). [CI mã runtime](https://github.com/HuynhHao080/aws-policy-assistant/actions/runs/42068819957).

## Kịch bản demo 4 phút — chưa phải video đã quay

1. Khách gửi yêu cầu có đồng ý; nhân viên A nhận việc.
2. Nhân viên B ghi chú nội bộ; khách tải lại vẫn chỉ thấy hội thoại công khai.
3. B tiếp quản với lý do, A thử gửi từ revision cũ và nhận xung đột; tải lại rồi đọc lịch sử.
4. B trả lời khách; khách phản hồi và giữ nguyên dữ liệu nội bộ. Giải thích cleanup, retention và giới hạn quyền quản trị.

Không dùng số test để suy ra accuracy, SLA hoặc điểm FCAJ. Sơ đồ AWS phải do sinh viên tự vẽ/giải thích; 3 blog đăng thật, office/sự kiện, Pricing Calculator và video còn chờ minh chứng cá nhân. Không thay kết quả lịch sử B4/B5/B5-R7.
