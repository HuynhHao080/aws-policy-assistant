---
title: "Chính sách có thời hạn — kiểm soát nguồn AI"
date: 2026-11-05
weight: 4
---

# Nguồn có liên quan chưa chắc còn được áp dụng

Một trợ lý shop có thể tìm đúng đoạn văn nhưng đoạn đó đã hết hạn hoặc chưa tới ngày hiệu lực. Bản mở rộng này bổ sung điều kiện nghiệp vụ trước truy hồi và kiểm tra lại nguồn trước lưu câu trả lời. Nội dung có AI hỗ trợ; sinh viên cần tự đọc, chạy và giải thích khi bảo vệ.

## Tính năng thực tế

Quản trị nhập **Có hiệu lực từ / Đến hết ngày**, cả hai mốc đều bao gồm ngày chọn, theo **Việt Nam UTC+7**. Để trống nếu không giới hạn; ngày không tồn tại hoặc kết thúc trước bắt đầu bị từ chối. Các bản cũ không có trường ngày vẫn dùng như trước. Thời hạn này kiểm soát nguồn chính sách hiện hành, không thay “bảo hành12tháng từ ngày nhận hàng” thành ngày hết hạn tuyệt đối và không tự quyết định quyền lợi của đơn hàng quá khứ.

Lưu nháp không đổi thời hạn bản đã công bố. Công bố bản bắt đầu trong tương lai không tự làm nó hiệu lực ngay. Danh mục có bộ lọc đang hiệu lực, chưa tới ngày, hết hạn và ngày hỏng; các bản ngày hỏng bị loại khỏi tra cứu nhưng vẫn mở được trong quản trị để sửa. Ngày bắt đầu/kết thúc và cảnh báo bản hiện hành được hiển thị riêng trong editor. Hạn mức tài khoản vẫn tính theo UTC, độc lập với ngày chính sách.

## Luồng và ranh giới AWS

1. Admin đã được xác thực lưu draft cùng ngày; revision và transaction audit bảo vệ thay đổi. Publish là thao tác riêng.
2. API lấy theo mã, tìm kiếm và RAG loại nguồn chưa/không còn hiệu lực hoặc ngày hỏng. Search vẫn giữ scan budget và cursor; một trang rỗng không đồng nghĩa hết kết quả.
3. RAG chỉ đưa nguồn hợp lệ vào context. Trước lưu kết quả, API consistent-read từng policy được trích dẫn, kiểm nội dung/ngày/trạng thái công bố. Thay đổi phát hiện tại lần kiểm này trả409, không lưu answer và không tự gọi model lại.
4. Fingerprint chỉ dựa trên dữ kiện công bố, nên một draft riêng không làm câu trả lời dùng bản công bố không đổi bị hủy. Fingerprint nội bộ không vào prompt/history/response/export; trích dẫn mới có thể giữ metadata ngày.

Không thêm dịch vụ, cron, bảng/index, endpoint hoặc execution IAM grant. Template gốc và template processed chỉ khác sáu code keys; các mục phụ thuộc CloudFormation liệt kê vẫn có cấu hình giống trước. Tối đa5logical consistent GetItem được bổ sung cho các policy ID khác nhau ở lần kiểm cuối. Không có tác vụ hay model call tự chạy khi đồng hồ qua ngày.

Đây là **kiểm tra tại thời điểm đọc**, không phải khóa tới khi khách xem kết quả hoặc transaction chung giữa policy và history. Chính sách vẫn có thể thay đổi ngay sau lần kiểm cuối. Lịch sử là snapshot; không tự viết lại câu trả lời cũ. Không hạ runtime về bản chưa kiểm ngày sau khi đã có chính sách công bố kèm ngày.

## Bằng chứng đã thực hiện

| Phạm vi | Kết quả và giới hạn |
|---|---|
| Local Python |298PASS,11liveSKIP;25ca mới về ngày, draft, cursor và thay nguồn giữa generation |
| Frontend |59PASS;5ca mới gồm validation và DOM editor/filter/khắc phục ngày hỏng; không phải kiểm hình ảnh browser thật |
| GitHub CI |[Commit5498d92 đã chạy đạt](https://github.com/HuynhHao080/aws-policy-assistant/actions/runs/42056109331): build, tests, SAM lint và source integrity |
| AWS thực |16kiểm tra API quyền/đọc/lưu nháp PASS; một identity không gửi thư và ba record chưa tới ngày/hết hạn/ngày hỏng do operator seed |
| Cleanup |Identity và ba record tạm đã dọn; không gọi `/ask`, publish, embedding, OCR hoặc PDF trong đợt API này |
| Artifact |37frontend files,6Lambda hashes khớp; stackUPDATE_COMPLETE, CloudFront invalidation hoàn tất |

[Bằng chứng đã lọc và hash nguồn](/aws-internship-worklog/evidence/policy-validity-2026-11-05.json). Hash report dùng canonical JSON để không thay khi Git đổi CRLF/LF; công thức được ghi trong JSON. Live fixture không phải đầu ra model, live publish hoặc phép đo factual accuracy. Các kết quả quality/CI/browser cũ vẫn giữ ngày và phạm vi riêng. Không có benchmark tải hoặc restore mới.

## Demo đề xuất 4 phút

1. Giải thích một policy mẫu có cửa sổ ngày, tách thời hạn tài liệu khỏi thời hạn bảo hành tính từ giao dịch. Dùng dữ liệu hư cấu rõ nhãn.
2. Mở editor, lưu nháp ngày tương lai và chỉ ra bản đã công bố không đổi. Dùng bản nháp hư cấu khi minh họa công bố và tìm kiếm từ khóa.
3. Chạy `python -m pytest tests/unit/test_policy_validity.py -q`: chỉ rõ moto/model giả, biên ngàyUTC+7, filter/cursor và tình huống nguồn bị thay trước lần kiểm cuối dẫn tới409không lưu lịch sử.
4. Đối chiếu evidence API thật với unit mô phỏng; giải thích vì sao không cần cron, vì sao consistent read không phải một khóa, giới hạn rollback và nguồn lịch sử.

Đây là kịch bản để sinh viên tự thực hiện, không phải video/demo đã quay. Không đổi giờ hệ thống hoặc chỉnh chính sách thật để giả lập. Tự thiết kế sơ đồ, kiểm tra Calculator và hoàn thành minh chứng blog/chuyên cần thực tế; tính năng này không tự bảo đảm điểm FCAJ.
