# Approval B2 — kết quả publish frontend test

**PUBLISHED_STATIC_VERIFIED. DỪNG; B3/B4/cleanup chưa được phê duyệt.**

## Target và thời gian

Account **…0098** xác minh STS; region **ap-southeast-1**; stack **policy-assistant-fcaj-test CREATE_COMPLETE**. Chỉ frontend bucket và CloudFront distribution thuộc stack test, đối chiếu Outputs + resource inventory + origin binding. Không đoán tên bucket.

- Bucket: `policy-assistant-fcaj-test-frontendbucket-icggnkicte7f`.
- CloudFront distribution: `E1LWE11YCHVIKC`.
- Frontend: https://d3ataim7dfsl7t.cloudfront.net/
- Preflight UTC: 2026-10-21T16:27:20.451505+00:00 đến 2026-10-21T16:27:26.611268+00:00.
- Upload/invalidation UTC: 2026-10-21T16:28:19.935148+00:00 đến 2026-10-21T16:28:47.184633+00:00.
- HTTP/HTTPS UTC: 2026-10-21T16:29:01.099094+00:00 đến 2026-10-21T16:29:07.628010+00:00.

Ngày thực hiện **21/10/2026**; giờ UTC+7 tương ứng khoảng **23:26–23:29**. Không sử dụng thời điểm B1 ban sáng làm thời điểm B2.

## Preflight và build

- Bucket rỗng trước upload và được kiểm tra lại ngay trước write: **0 object ghi đè, 0 object xóa**. Upload dùng IfNoneMatch `*` để tránh ghi đè nếu có object xuất hiện ngoài dự kiến.
- API URL, region, Cognito pool/client và CloudFront khớp outputs cùng stack test; client thuộc pool test, không client secret. Targets khác stack cũ; không dùng DocumentsBucket làm frontend target.
- App là HTML/CSS/JavaScript tĩnh, không bundler/TypeScript project. Build là copy ba assets nguồn và sinh riêng config.json cho test trong thư mục build ignored. Không đổi file frontend/config.json nguồn.
- App dùng apiBase/region/clientId; userPoolId và frontendUrl được giữ làm metadata đối chiếu cùng môi trường. Không có credentials/password/JWT trong config.
- **17 frontend unit tests PASS, 0 skip; hai browser suites local PASS** (một fixture, một local full-stack/mô phỏng AWS). JS syntax, Ruff phạm vi E9/F63/F7/F82 và mypy backend theo quy trình hiện có PASS. Không tuyên bố frontend có TypeScript typecheck riêng.

[Local checks](evidence/approval-b2-local-checks.json), [preflight/build manifest](evidence/approval-b2-preflight.json).

## Assets đã upload

| Key | Bytes | SHA-256 |
|---|---:|---|
| index.html | 5752 | `28182131e09dc5f0e29cba98404c1b5182f7b711fc48f8c77a425891835ff1cd` |
| app.js | 22780 | `c0b52244d1ac5f729da7819dadc585028a6ad1721e16d57c1b790643f8483222` |
| styles.css | 5096 | `aa65a893213b10a01e3c9484e8c56edb0a425fa9076e246d44938d4859f8588e` |
| config.json | 285 | `150bc0f17ac6fd19172ada9934dd2e896d472a70ec064d4a2f685c6c0c41e678` |

Tổng **4 assets, 33.913 bytes**. Checksum SHA-256 được xác minh từ nội dung GET S3 và response HTTPS CloudFront, không dùng ETag thay SHA-256. Content-Type đúng từng định dạng; config.json Cache-Control no-store, các assets còn lại no-cache. Không đặt ACL công khai hoặc đổi policy/IAM.

## CloudFront invalidation

ID `I3QP9GCKWVCDRQT8ERMMBUUOT2`; **Completed**. Paths: `/`, `/index.html`, `/app.js`, `/styles.css`, `/config.json`. `/` là alias của index.html; không wildcard, không invalidation distribution khác. Một lần CreateInvalidation.

## Kết quả HTTP/HTTPS

- HTTP `/`: **301**, Location đúng HTTPS frontend test.
- HTTPS `/`, `/index.html`, `/app.js`, `/styles.css`, `/config.json`: **200**, nội dung khớp SHA-256 build; trang root chứa Policy Assistant và tham chiếu assets đúng.
- Có HSTS, CSP, X-Content-Type-Options nosniff và Referrer-Policy no-referrer.
- **Chưa kiểm tra browser render trực tiếp trên CloudFront**, chưa đăng nhập, chưa gọi API nghiệp vụ/Cognito, chưa kiểm chứng upload/download hoặc ownership trên AWS. Không tính các browser tests local thành AWS E2E.

[HTTP/HTTPS evidence](evidence/approval-b2-static-http-verification.json), [upload/invalidation evidence](evidence/approval-b2-publish.json), [summary](evidence/approval-b2-result.json).

## Phạm vi và tài nguyên cũ

Chỉ bốn PutObject vào bucket test và một CreateInvalidation trên distribution test. Không CloudFormation/IAM/Lambda/API deployment, không DocumentsBucket writes, không tạo user, không gửi SQS message, không Budget writes, không cleanup hoặc commit/push. Stack cũ UPDATE_COMPLETE và LastUpdatedTime 2026-10-19 11:10:29.038 UTC không đổi. Không có write target production; metadata này không phải full drift scan.

## Quyết định B3

**GO để người dùng xem xét B3; NO-GO tạo users cho đến khi phê duyệt riêng.** Pool/client/API/frontend đã đối chiếu cùng môi trường test. B3 đề nghị đúng hai users tổng hợp trong pool test, invitation SUPPRESS, không email/SMS; không công khai password. Đăng nhập/nghiệp vụ/E2E thuộc B4 riêng; B3 không tự cấp quyền B4. Email Budget vẫn theo trạng thái trước: Active (legacy), verification 0/1, delivery chưa xác minh; B2 không thay đổi hoặc kiểm tra lại Billing.

Chi phí requests/lưu trữ/CloudFront phát sinh nhỏ nhưng không đo thành invoice ngay vì Billing trễ; giữ Budget 20 USD theo dõi, không coi hard cap. Cleanup và retained data cần Approval C độc lập.
