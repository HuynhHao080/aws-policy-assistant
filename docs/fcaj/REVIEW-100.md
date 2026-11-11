# Đối chiếu hệ thống với 100 câu luyện bảo vệ FCAJ

Bảng dùng số thứ tự của bộ câu hỏi người dùng cung cấp. Các nhóm bao phủ từ câu 1 đến 100. Khi trình bày, đối chiếu bản chạy với mã và bằng chứng trong cột tương ứng.

| Câu | Phần có thể chứng minh | Việc cần diễn giải hoặc xác minh thêm |
|---|---|---|
| 1–10 | Shop phụ kiện DEMO, đăng ký, PDF riêng, hỏi đáp có nguồn, chính sách có hiệu lực, hỗ trợ có phân công. [Danh mục chức năng](../FEATURE-STATUS.md) | Trình bày đóng góp cá nhân ở câu 9. Nêu rõ phạm vi một shop và chính sách DEMO. |
| 11–20 | CloudFront/S3, Cognito, HTTP API/Lambda, DynamoDB, SQS, S3 private, Textract, Bedrock. [AWS SAM](../../template.yaml) | Tự vẽ luồng upload và hỏi đáp. Câu 20 là thiết kế mở rộng giả định, cần số đo tải để quyết định thay đổi. |
| 21–30 | Global Claude Haiku 5.5 là model duy nhất. Backend kiểm cấu trúc và ID nguồn trả về. [Mã truy hồi và trả lời](../../policy_assistant/assistant.py) | Giải thích Converse, giới hạn đầu ra 900 token và cách đo chi phí, chất lượng, thời gian trả lời. |
| 31–40 | PDF text/OCR, chia đoạn, xếp hạng từ khóa, trích dẫn trang, lọc hiệu lực. [Kiểm nguồn](../policy-validity-verification.md) | Nêu phạm vi, ngày và điều kiện nếu nguồn mâu thuẫn. Đo riêng chất lượng trên model thật. |
| 41–50 | Python 3.12, presigned upload, chốt phiên bản S3, trạng thái DynamoDB, SQS, worker, retry có giới hạn và DLQ. [Hợp đồng API](../api-contract.md) | Thử ca gián đoạn sau upload rồi chọn Gửi xử lý trên cùng tài liệu. Các trạng thái lỗi PDF/OCR có chỉ dẫn riêng. |
| 51–60 | Cognito JWT, quyền sở hữu theo sub, S3 private, IAM parser riêng, kiểm kích thước, từ chối PDF tương tác, kiểm ID nguồn. [Vận hành](../production-runbook.md) | Chuẩn bị demo hai tài khoản. Giải thích phạm vi kiểm tra PDF, prompt injection và quy trình thu hồi credential trong sự cố. |
| 61–70 | GitHub Actions kiểm thử, AWS SAM/CloudFormation Change Set, mã Lambda và frontend fingerprint. [CI](../../.github/workflows/ci.yml) · [Runbook](../production-runbook.md) | Câu 62 và 64 nói CDK. Đối chiếu bằng `sam validate`, `sam build` và quy trình Change Set của repo này. |
| 71–80 | Python, DOM giả lập, API AWS có fixture, CloudWatch, đối chiếu artifact. [Báo cáo API hỗ trợ](../support-team-verification.md) | Đo độ đúng bằng chấm từng câu theo nội dung và nguồn kỳ vọng. Theo dõi lỗi, tỷ lệ thiếu nguồn và latency riêng. Kết quả DOM không đo các chỉ số này. |
| 81–90 | Quota, truy hồi giới hạn, mục tiêu ngân sách và giả định theo token/OCR/lưu trữ. [Đầu vào dự toán](COST-ASSUMPTIONS.md) | Tổng chi phí tháng và giả định Free Tier cần bản Calculator theo region, lượng dùng và đơn giá tại thời điểm lập. Câu 86 là kịch bản dự toán tải cao. |
| 91–100 | Demo **Tài liệu của tôi → Hỏi từ PDF này → Gửi câu hỏi → mở nguồn và số trang**. Tạo một PDF thử chứa một quy định hư cấu rõ ràng để đối chiếu. [Kịch bản trình bày](DEMO-PLAN.md) | Ghi hình bằng tài khoản thử. Tự mô tả quá trình làm ở câu 96 và 100. Xác định giới hạn và ưu tiên dựa trên kết quả đo. |

## Ca kiểm tra trước buổi bảo vệ

1. Tải PDF có văn bản. Khi trạng thái là **Sẵn sàng**, chọn **Hỏi từ PDF này**. Kiểm tra phạm vi **Chỉ PDF đã chọn (1)** và đọc số trang ở nguồn.
2. Với câu hỏi có nhiều trích dẫn, chọn **Đối chiếu nguồn**. So sánh mốc thời gian và điều kiện, sau đó kiểm tra chính sách đang công bố nếu cần.
3. Với tài liệu đang chờ sau một lần gửi xử lý gián đoạn, làm mới thư viện và chọn **Gửi xử lý**. Đối chiếu cùng hàng tài liệu cho tới trạng thái cuối.
4. Dùng dữ liệu giả khi quay demo. Lưu thời điểm, URL, commit và kết quả quan sát thực tế. Các mục đo tải, khôi phục, độ đúng AI và Calculator cần bằng chứng riêng.
