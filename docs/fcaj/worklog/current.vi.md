---
title: "Bản chính — chức năng, kiểm chứng và bàn giao"
date: 2026-11-04
weight: 0
---

# Policy Assistant — bản chính ngày 04/11/2026

Ứng dụng: [Policy Assistant](https://djreo5eptvwk5.cloudfront.net/). Repo ứng dụng: `HuynhHao080/aws-policy-assistant`, thư mục làm việc `C:\Users\accli\Documents\Project\policy-assistant`. Repo worklog riêng: `HuynhHao080/aws-internship-worklog`. Mã local chưa push không tự xuất hiện trong source public. Hướng dẫn này có AI hỗ trợ; không phải nhật ký sinh viên đã tự thực hiện hoặc quyết định nghiệm thu của FCAJ.

Ngày 05/11, người dùng yêu cầu đồng bộ checkout `C:\Users\accli\Documents\Project\policy-assistant-github` từ mã nguồn ứng dụng chính. Đây là thư mục checkout thứ hai của cùng repo GitHub, không phải worklog hoặc đích AWS mới. Đồng bộ local không tự commit/push hay công bố site; các tài liệu lịch sử và config riêng được giữ/sao lưu theo báo cáo đồng bộ.

## Bài toán và giới hạn sản phẩm

Hỗ trợ shop nhỏ trả lời câu hỏi chính sách bằng nguồn công khai và tài liệu riêng của khách, đồng thời chuyển câu hỏi thiếu thông tin sang nhân viên qua yêu cầu hỗ trợ có đồng ý chia sẻ. Hiện là một shop dùng nội dung DEMO hư cấu; không có tích hợp đơn hàng/thanh toán, không tự hoàn tiền, không tự quyết định nguyên nhân hỏng hoặc cam kết pháp lý. Chưa có đơn vị vận hành/chính sách thật được phê duyệt.

## Chức năng đã có và cách tự kiểm tra

| Luồng | Hành vi và ranh giới cần trình bày |
|---|---|
| Tài khoản | Cognito tự đăng ký, xác nhận email, đăng nhập PKCE, quên mật khẩu; quyền quản trị kiểm ở backend |
| PDF riêng | Upload tối đa 10 MiB, 100 trang text hoặc 10 trang scan; phiên bản S3 được chốt; trạng thái lỗi rõ ràng; thư viện/đổi tên/tải/xóa theo chủ sở hữu |
| Xử lý nền | Stream metadata → dispatcher → SQS → worker; parser cô lập quyền; Textract cho scan; recovery, retry và DLQ |
| Hỏi đáp | Cohere đa ngôn ngữ/int8 trong S3; chọn chính sách chung, PDF hoặc cả hai; Nova 2 Lite có trích dẫn nguồn/trang, có thể trả thiếu bằng chứng |
| Lịch sử | Riêng từng tài khoản, tối đa 30 ngày, xuất JSON/xóa; bản ghi hết hạn bị ẩn dù TTL chưa dọn |
| Chính sách | Draft tách bản published; publish/archive/restore/discard có revision và audit; admin không vì có vai trò mà đọc được PDF khách |
| Hỗ trợ | Khách đồng ý trước khi gửi, category/mã đơn do khách nhập chưa xác minh; trao đổi trong app; nhân viên lọc, đổi trạng thái/priority; không tự gửi email hoặc đính kèm PDF/lịch sử |
| Shop | Draft/publish/withdraw/discard thông tin liên hệ; mode live yêu cầu thông tin và xác nhận; cấu hình shop không tự là nguồn AI |
| Chất lượng | Helpful/not-helpful và lý do cố định, đổi/rút đánh giá; revision, retry không đếm trùng; dashboard admin chỉ số tổng hợp/tháng hiện tại hoặc trước theo UTC, xuất JSON |
| Xóa tài khoản | Chặn truy cập trước, dọn dữ liệu và mọi phiên bản object bất đồng bộ; tổng hợp không định danh có thể còn sau khi xóa lịch sử |

Nguồn mã để đọc: `policy_assistant/app.py`, `assistant.py`, `pipeline.py`, `quality.py`, `tickets.py`, `shop.py`, `policy_admin.py`, `pdf_parser.py`, `template.yaml`, `frontend/src/`. Hợp đồng API và runbook trong `docs/api-contract.md`, `docs/production-runbook.md`. Kiểm tra tên route hiện hành trước khi viết snippet; không dùng tên endpoint tự suy đoán.

## Luồng dữ liệu để sinh viên tự vẽ kiến trúc

Frontend S3 private qua CloudFront HTTPS; Cognito cấp identity, API Gateway kiểm JWT, Lambda kiểm quyền trên từng tài nguyên. PDF vào S3 private theo owner và version; metadata lưu DynamoDB rồi dispatch xử lý nền. Parser không có quyền dịch vụ tùy ý. Nguồn text/vector được truy hồi có giới hạn trước khi gọi model; kết quả/history và bộ đếm chất lượng cập nhật bằng transaction có guard khi xóa tài khoản.

Stack, lưu trữ, embedding và OCR ở Singapore. Generation dùng `jp.amazon.nova-2-lite-v1:0`, low reasoning; trích đoạn có thể được xử lý tại Tokyo/Osaka. Cần giải thích luồng liên vùng và đọc thông báo quyền riêng tư trước khi dùng tài liệu nhạy cảm. Chỉ số có trích dẫn không chứng minh câu trả lời đúng; đánh giá người dùng là ý kiến. Thời gian xử lý server không phải độ trễ trình duyệt từ đầu đến cuối. Giữ dữ liệu tổng hợp 65 ngày sau cập nhật cuối; lịch sử riêng 30 ngày, hỗ trợ 90 ngày.

**Sơ đồ cuối cùng vẫn chưa có.** Sinh viên tự thiết kế/vẽ với [icon AWS chính thức](https://aws.amazon.com/architecture/icons/), đánh dấu trust boundary, dữ liệu riêng/chung, sync/async, retry/DLQ và liên vùng. Mỗi mũi tên cần tự giải thích payload, quyền và xử lý lỗi; không nộp worksheet AI làm sơ đồ tự thiết kế.

## Kiểm chứng đã ghi nhận — không phải chạy mới khi build worklog

[Tải bản bằng chứng đã lọc](/aws-internship-worklog/evidence/policy-assistant-2026-11-04.json). File chỉ xuất schema cho phép và hash báo cáo nguồn; không sao chép JWT, ID khách hoặc câu hỏi/câu trả lời. Thời điểm kiểm tra có trong JSON.

| Loại | Kết quả báo cáo release 04/11 | Phạm vi |
|---|---|---|
| Python 3.12 | 251 PASS, 11 SKIP | Kiểm thử local/mocked; live opt-in không bật |
| Frontend | 54 PASS và build | Node/DOM synthetic, không thay nghiệm thu hình ảnh trình duyệt |
| API chất lượng thật | 15 kiểm tra PASS | Hai identity tạm, fixture năm 2000 không hiển thị dashboard bình thường; lưu bằng helper operator và gọi feedback API thật; không gọi model/PDF/email |
| Dọn fixture | PASS trong báo cáo | Xóa hai identity, history và cohort tạm; không seed tháng thật |
| Artifact | 6 Lambda, 31 frontend files | Đối chiếu hash/metadata release; không phải screenshot, benchmark hoặc xác nhận đăng nhập mới |

Code SHA-256: `974197f606822d42a51a922694a30de95be06ac57a5a4ff30c1837089ab94273`. Không có kết quả mới cho load, khôi phục backup, email cảnh báo, độ chính xác model hoặc visual browser. Lịch sử B4/B5/B5-R7 và CI tháng 10 thuộc môi trường cũ, giữ nguyên.

## Tái lập local và đồng bộ worklog

Dùng Python 3.12, Node 26, AWS SAM CLI. Trong repo ứng dụng, thực hiện các bước README: cài `policy_assistant/requirements.txt` và `tests/requirements.txt`; `npm ci --prefix frontend --ignore-scripts`; `npm run build --prefix frontend`; `npm test --prefix frontend`; `python -m pytest tests -q`; `sam validate --lint --region ap-southeast-1`; `sam build`. Các bước unit/build không chứng minh cấu hình AWS đang deploy. Không bật biến live test hay chạy smoke/model khi chỉ cần kiểm tra local. Config mẫu không có backend thật và sẽ vô hiệu hóa đăng nhập.

```powershell
# Repo ứng dụng: kiểm tra drift, không ghi vào AWS/Git/site
python scripts/sync_fcaj_worklog.py --worklog C:/Users/accli/Documents/Project/aws-internship-worklog
# Áp dụng phần kỹ thuật có quản lý; backup trước mọi lần sửa
python scripts/sync_fcaj_worklog.py --worklog C:/Users/accli/Documents/Project/aws-internship-worklog --apply
# Repo worklog, Hugo extended đúng phiên bản CI
hugo --minify
```

Công cụ chỉ sửa block có marker trong danh sách trang được phép, hai trang hướng dẫn và JSON đã lọc. Không sửa nhật ký daily, ảnh, thông tin cá nhân hay tự đăng blog; không push/deploy. Backup/manifest nằm ở `.deployment/worklog-sync-*` trong repo ứng dụng. Dùng Hugo extended **0.167.0** theo workflow; kiểm checksum bản tải chính thức trước khi chạy.

## Demo 7 phút — sinh viên chưa quay/thực hiện bản này

| Phút | Thao tác cần tự làm và giải thích |
|---|---|
| 0–1 | Nêu bài toán shop và nhãn DEMO; tự giải thích sơ đồ |
| 1–2 | Tài khoản A upload PDF tổng hợp, theo dõi processing; chỉ nói OCR nếu thật sự dùng PDF scan |
| 2–3 | Hỏi câu có nguồn và câu thiếu quy định; mở nguồn/trang, giải thích phạm vi truy hồi |
| 3–4 | Tài khoản B không đọc được PDF/history của A; không quay token/presigned URL |
| 4–5 | Gửi hỗ trợ có đồng ý, nhân viên phản hồi; chứng minh không tự đính kèm dữ liệu riêng |
| 5–6 | Đánh giá/đổi/rút phản hồi; admin xem số tổng hợp, giải thích không đồng nghĩa accuracy |
| 6–7 | Draft/publish, audit, chi phí và giới hạn; chỉ dùng số đo đúng nguồn/ngày |

Đây là kế hoạch, không phải evidence đã PASS. Không dùng fixture API có latency giả làm đầu ra model hay kết quả đo thực. Không chạy fault/poison/load hoặc xóa tài nguyên giữa bài demo. Cleanup tài nguyên cloud cần phạm vi riêng và đối soát dữ liệu/version/retained storage trước khi thực hiện; không có cleanup mới trong lần đồng bộ này.

## COST hiện tại — đầu vào chuẩn bị, chưa có Calculator

Mục tiêu chủ dự án: 30–50 USD/tháng, budget account 50 USD và ngưỡng thông báo 25/40/50 USD theo báo cáo triển khai. Đây không phải hard cap/hóa đơn mới đọc. Giữ dự toán 21/10 cho môi trường test cũ dưới nhãn lịch sử; nó không bao gồm đầy đủ Nova2/OCR/embedding/vectors/counters mới.

Một kịch bản **đề xuất để nhập Calculator**, chưa được đo hoặc chủ dự án chốt: 50 MAU; 100 PDF/tháng × 10 trang, 20% cần OCR → 200 trang OCR; 2 MiB/PDF; 2.000 chunks embedding/tháng cộng 1.000 query embedding; 1.000 lần generation × 8.000 input tokens và 2.500 output/reasoning tokens để dự trù. Số token là giả định, không đo và không phải giới hạn input bắt buộc; maxTokens Nova2 trong code là 2.500. Thử kịch bản quota 2.000 lần/tháng; retention/version tăng theo thời gian, không lấy dung lượng upload một tháng làm tổng storage.

Trong [AWS Pricing Calculator](https://calculator.aws/) nhập từng dịch vụ theo region: generation Japan; embedding/Textract/API/Lambda/DynamoDB/S3 Singapore; CloudFront theo người dùng thực. Gồm cả parser/recovery/dispatcher/signup Lambda, request thất bại/trùng, transactional writes/index/PITR, S3 mọi phiên bản và vectors, transfer, Cognito, CloudWatch logs/alarms/dashboard, SNS. Không mặc định đủ free tier hoặc trừ credit. Dùng [giá Bedrock chính thức](https://aws.amazon.com/bedrock/pricing/) và trang pricing từng dịch vụ tại ngày lập estimate. Chưa có đơn giá mới/tổng USD được xác minh cho kịch bản này; nếu Calculator chưa hỗ trợ model/dimension, đính kèm phép tính bổ sung từ giá chính thức, không bỏ chi phí đó. Lưu share URL/export và ngày/giả định thật trước khi đánh dấu COST hoàn tất.

## Các việc cá nhân còn chờ

### Kiểm tra bàn giao bổ sung — 05/11/2026

Bản mã nguồn đã được đóng gói, kiểm manifest/checksum và giải nén vào thư mục mới. Cài dependency trong venv Python 3.12 riêng và `npm ci` theo lockfile: **273 kiểm thử Python PASS, 11 live SKIP; 54 frontend PASS; SAM build cả sáu function và validate/lint PASS**. Lần build đầu chọn nhầm Python 3.13 từ PATH đã thất bại; chọn đúng thư mục Python 3.12 rồi build lại đạt, không hạ yêu cầu runtime.

Đây là nghiệm thu local mới, gồm 22 kiểm thử công cụ đồng bộ/đóng gói bổ sung; không thay số 251/54/15 của release cloud lịch sử phía trên. Dùng toolchain hệ thống và cache tải package chung, không phải máy/container/account AWS mới. Không chạy model hoặc kiểm thử AWS trực tiếp. Mã source được đóng gói bằng `scripts/source_bundle.py`, loại config thật, credentials, build/dependency và Git history; pattern scan không phải kiểm toán bí mật đầy đủ. Hướng dẫn và báo cáo trong repo ứng dụng: `docs/reproducibility/README.md`, `VERIFICATION-2026-11-05.md`, `requirements-verified-2026-11-05.txt`. CI đã thêm bước kiểm tra archive local; chưa có lần chạy GitHub CI mới hoặc xuất bản công khai.

Ba blog 3.4–3.6 là bản nháp; cần tự rà soát kỹ thuật, bổ sung đóng góp thật, đăng rồi lưu URL/ngày. Minh chứng office/sự kiện, ngày thực tập, sơ đồ tự vẽ, Calculator và video demo phải có evidence thật. Không tạo ngày/ảnh/điểm tự đánh giá thay sinh viên. Đọc [quy định workshop](https://hcm-rules.awsfcaj.com/3-project/) và [tiêu chí chấm](https://hcm-rules.awsfcaj.com/5-scoring/) trước nộp; không suy ra điểm hoặc eligibility từ test counts.
