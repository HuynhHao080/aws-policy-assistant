---
title: "Đề xuất hiện tại — trợ lý chính sách cho shop phụ kiện"
weight: 0
---


**Model của bản chính:** Global Claude Haiku 5.5. Ứng dụng xếp hạng từ khóa trên văn bản PDF và chính sách. Các báo cáo kiểm thử có ngày bên dưới ghi lại từng bản đã nghiệm thu. [Bằng chứng chuyển model](https://github.com/HuynhHao080/aws-policy-assistant/blob/main/docs/haiku55-migration.md).
# Policy Assistant — đề xuất giải pháp hiện tại

Rà soát tài liệu: **06/11/2026**. Đây là bản mô tả khớp mã đã công bố và bằng chứng triển khai gần nhất, có AI hỗ trợ; sinh viên phải tự rà soát, thực hành và giải thích. Không phải tuyên bố đã đủ mọi điều kiện FCAJ hoặc được phép dùng chính sách DEMO cho giao dịch thật. Các proposal tháng 10 trong trang cha được giữ làm lịch sử.

## 1. Bài toán, người dùng và giá trị

Shop phụ kiện nhỏ thường nhận lặp lại câu hỏi về bảo hành, đổi trả, giao hàng và thanh toán. Nội dung rải rác dễ dẫn tới trả lời thiếu nguồn hoặc áp dụng nhầm điều kiện. Khi chưa đủ thông tin, khách cần chuyển cho nhân viên mà vẫn kiểm soát dữ liệu chia sẻ.

Giải pháp tập trung vào **một shop**, hai nhóm người dùng: khách tự đăng ký tài khoản và quản trị viên được tin cậy. Khách tra cứu chính sách, hỏi đáp có dẫn nguồn, dùng PDF riêng và gửi yêu cầu hỗ trợ có đồng ý. Quản trị duyệt nội dung, quản lý hiệu lực, phối hợp xử lý yêu cầu và xem phản hồi tổng hợp. Đây là nền tảng hỗ trợ quyết định; nhân viên xác minh đơn hàng và nguyên nhân hỏng ngoài hệ thống.

| Mục tiêu | Cách kiểm chứng | Giới hạn |
|---|---|---|
| Câu trả lời có thể đối chiếu | Mở nguồn, trang PDF và nội dung trích dẫn | Có nguồn không đồng nghĩa mọi câu đều đúng |
| Giữ dữ liệu khách riêng | Kiểm tra hai tài khoản, DTO và kiểm quyền backend | Admin ứng dụng không phải operator AWS |
| Tránh dùng chính sách hết hạn | Ngày UTC+7, lọc hiệu lực và kiểm lại nguồn trước lưu | Kiểm tại thời điểm, không khóa giao dịch với model |
| Bàn giao có ngữ cảnh | Nhận việc, ghi chú, tiếp quản có lý do và revision conflict | Mọi admin vẫn được đọc ghi chú, chưa có role nhân viên hạn chế |
| Chi phí phù hợp thử nghiệm nhỏ | Quota, bounded retrieval, cảnh báo budget và theo dõi lượng dùng | Chưa có benchmark tải, Calculator hoàn chỉnh hay hard spending cap |

## 2. Phạm vi đã có và chưa có

Đã có đăng ký/xác minh email/PKCE/khôi phục mật khẩu; PDF riêng với phiên bản S3 chốt và pipeline text/OCR; chọn nguồn chính sách/PDF/cả hai; hỏi đáp có trích dẫn; lịch sử 30 ngày; draft/publish/archive/restore/revision/audit; thông tin shop; hỗ trợ có consent, phân công, ghi chú; đánh giá câu trả lời tổng hợp; xóa tài khoản có chặn truy cập và dọn nền.

Chưa có nhiều tenant, đồng bộ đơn hàng, thanh toán, tự hoàn tiền, mạng xã hội, email hỗ trợ tự động, bộ đếm SLA hoặc quyền support-only. Không tự kết luận điều kiện bảo hành thực tế. Chính sách vẫn **DEMO** do chưa có đơn vị vận hành phê duyệt nội dung thật. [Danh mục đầy đủ và điều kiện dùng thật](https://github.com/HuynhHao080/aws-policy-assistant/blob/main/docs/FEATURE-STATUS.md).

## 3. Kiến trúc và luồng dữ liệu để tự vẽ

Đây là mô tả đầu vào, **không thay sơ đồ AWS do sinh viên tự thiết kế**. Dùng icon AWS đúng dịch vụ, thể hiện ranh giới danh tính, dữ liệu khách riêng và nơi gọi model; đối chiếu `template.yaml` trước khi chốt.

| Luồng | Thành phần và trách nhiệm |
|---|---|
| Giao diện | CloudFront + S3; Cognito xác thực; HTTP API → Lambda Python 3.12 kiểm JWT/nhóm/quyền sở hữu |
| Upload và xử lý | S3 private versioned → metadata DynamoDB/Stream → dispatcher → SQS → worker; parser PDF cô lập IAM, Textract cho scan; recovery và DLQ |
| Hỏi đáp | Xếp hạng từ khóa trên văn bản → Global Claude Haiku 5.5 → kiểm ID nguồn và hiệu lực → lịch sử |
| Quản trị và hỗ trợ | DynamoDB lưu policy/shop/ticket; transaction revision + owner-deletion guard + audit; DTO khách loại bỏ ghi chú nội bộ |
| Vận hành | CloudWatch logs/metrics/alarms, SNS và AWS Budgets; PITR và Retain bảo vệ dữ liệu khi thao tác hạ tầng |

Ứng dụng, lưu trữ và Textract ở Singapore. Hồ sơ Global Claude Haiku 5.5 có thể xử lý câu hỏi và đoạn trích ngoài Singapore.

## 4. Quyết định kỹ thuật và rủi ro

| Rủi ro / đánh đổi | Cách xử lý và điểm còn phải đo |
|---|---|
| Model suy diễn hoặc nguồn bị đổi | Chỉ nhận IDs thuộc nguồn truy hồi, kiểm cấu trúc và kiểm lại dữ kiện công khai trước lưu; chưa có kết quả accuracy mới |
| Truy cập chéo tài khoản | Chủ sở hữu lấy từ JWT, kiểm backend, private S3, customer DTO allowlist; operator AWS vẫn có quyền hạ tầng riêng |
| Xử lý nền trùng hoặc lỗi | Version pin, trạng thái bền, retry giới hạn, partial batch failures, recovery và DLQ; cần diễn tập sự cố được duyệt |
| Hai nhân viên/khách ghi đồng thời | Revision + transaction; trả xung đột, tải lại và đọc trước khi thử lại |
| Scan và truy hồi từ khóa khi dữ liệu tăng | Truy hồi/phân trang có giới hạn; đo recall/latency/backlog trước khi tăng quota hoặc đổi storage |
| Chi phí phát sinh ngoài model | Tính cả mọi phiên bản S3, PITR, logs/alarms, OCR, transfer, request lỗi; budget chỉ cảnh báo |
| Xóa dữ liệu và phục hồi | Chặn tài khoản trước purge; retention được mô tả; backup/log theo vòng đời riêng, chưa nghiệm thu restore mới |

## 5. COST — đầu vào dự toán, còn chờ Calculator

Mục tiêu chủ dự án **30–50 USD/tháng**; cấu hình budget 50 USD với ngưỡng 25/40/50 USD là cảnh báo, không khóa hóa đơn. Không dùng dự toán test tháng 10 làm giá bản hiện tại. Bảng sau là giả định để nhập Calculator, chưa đo tải và chưa tạo estimate được chia sẻ.

| Đầu vào giả định | Cơ sở tính / dịch vụ cần nhập |
|---|---|
| 50 MAU; 100 PDF/tháng × 10 trang × 2 MiB/PDF | Cognito, API, Lambda, S3; cộng bản gốc/phiên bản/extraction và retention, không chỉ upload tháng đầu |
| 20% trang cần OCR = 200 trang/tháng | Textract Singapore + worker/poll/retry |
| 1.000 câu trả lời × 8.000 input và tối đa 900 output token | Global Claude Haiku 5.5 từ Singapore. Kịch bản 2.000 lượt/tháng dùng cho dự toán tải cao. |
| Hỗ trợ, audit, counters và vận hành | DynamoDB transactional writes/index/PITR, SQS, logs/alarms/dashboard, SNS, CloudFront/transfer và request lỗi |

Tổng tiền: **CHỜ**, chưa có đơn giá/estimate mới được xác minh; không ghi 0 USD hoặc mặc định free tier/credit. Chủ dự án cần [AWS Pricing Calculator](https://calculator.aws/) và [giá Bedrock chính thức](https://aws.amazon.com/bedrock/pricing/), lưu ngày, region, giả định và share URL/export. Nếu thiếu dimension/model thì bổ sung phép tính từ giá chính thức. [Kịch bản COST chi tiết]({{< relref "/5-Workshop/5.7-PolicyAssistant/CurrentRelease" >}}).

## 6. Kế hoạch chốt — chưa ghi thành đã thực hiện

| Giai đoạn đề xuất | Đầu ra và người xác nhận |
|---|---|
| 1–2 ngày | Chủ shop rà soát tên đơn vị, liên hệ, địa chỉ nhận hàng, chính sách thật và consent/retention |
| 1–2 ngày | Sinh viên tự vẽ/giải thích kiến trúc, nhập Calculator và chốt kịch bản tải với chủ dự án |
| 1–2 ngày | Kiểm thử browser trên thiết bị thật, nhận email/alert, quy trình nhân viên; lên kế hoạch load/restore theo phạm vi được duyệt |
| 1 ngày | Quay demo với tài khoản/dữ liệu thử, che bí mật; đối chiếu commit/artifact, nộp evidence thật |

Đây là ước lượng công việc còn lại, không phải ngày thực tập, lịch hẹn hoặc cam kết sẽ đạt trong thời gian này.

## 7. Nghiệm thu và liên kết bằng chứng

Bản runtime hỗ trợ có **322 Python PASS, 11 live SKIP; 67 frontend PASS; 20 HTTP checks PASS**. Ba tài khoản QA và ticket đã dọn; 40 tệp frontend và 6 Lambda khớp artifact. Đây là snapshot đã ghi timestamp UTC 05/11 (06/11 Việt Nam), không phải lần chạy lại khi đọc trang này. Không gọi model/PDF/OCR/email trong đợt HTTP đó. [Báo cáo](https://github.com/HuynhHao080/aws-policy-assistant/blob/main/docs/support-team-verification.md), [CI source](https://github.com/HuynhHao080/aws-policy-assistant/actions/runs/42072920395), [chương hỗ trợ]({{< relref "/5-Workshop/5.7-PolicyAssistant/SupportTeam" >}}), [chương hiệu lực]({{< relref "/5-Workshop/5.7-PolicyAssistant/PolicyValidity" >}}).

Trước khách thật cần kiểm chứng browser, độ đúng theo bộ câu hỏi shop duyệt, email, tải, restore và vận hành trực. Không đổi kết quả FAIL/PASS lịch sử. Ba blog đăng thật, minh chứng sự kiện/office, sơ đồ tự vẽ, Calculator và video vẫn chờ chủ dự án cung cấp; không tự tạo bằng chứng. [Quy định workshop](https://hcm-rules.awsfcaj.com/3-project/) yêu cầu nội dung VI/EN và proposal có phạm vi/kiến trúc/kế hoạch/COST/rủi ro; [tiêu chí chấm](https://hcm-rules.awsfcaj.com/5-scoring/) yêu cầu sinh viên tự thiết kế, giải thích kiến trúc. Đã đối chiếu các trang này ngày 06/11/2026; việc bổ sung tài liệu không tự xác lập điểm hoặc đủ điều kiện.
