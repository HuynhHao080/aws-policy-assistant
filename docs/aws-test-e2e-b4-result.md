# Approval B4 — kết quả AWS E2E có kiểm soát

**19 PASS / 0 FAIL / 0 BLOCKED / 1 NOT_RUN.** Backend API/SDK E2E trên AWS thật đạt; không đồng nhất với browser E2E đầy đủ. **DỪNG: không tự cleanup, sửa code/IAM, deploy hoặc commit/push.**

## Thời gian, môi trường và phương pháp

- Bắt đầu: **2026-10-21T16:47:11.696488+00:00**; kết thúc runner: **2026-10-21T16:57:34.897615+00:00**. Follow-up alarms: **2026-10-21T16:59:27.702859+00:00**. Các thời điểm đều UTC (UTC+7 tương ứng khoảng 23:47–23:59 ngày 21/10/2026).
- Account …0098; region ap-southeast-1; stack policy-assistant-fcaj-test CREATE_COMPLETE; frontend https://d3ataim7dfsl7t.cloudfront.net/.
- STS và outputs/resources được đối chiếu với pool/client/API/buckets/queues test. CloudFront config khớp. Lambda Active, queue mapping Enabled, IAM không Allow Resource `*`, log grants test-only; queue/DLQ rỗng trước phép thử. Budget đúng 20 USD/ba notifications/không Actions.
- Chỉ dùng hai users tổng hợp B3, DPAPI được giải mã trong bộ nhớ; không in hoặc lưu password, JWT, refresh token, signed URLs/fields. Không thay đổi email_verified=false.
- Runner dùng boto3/requests trực tiếp với AWS; không mock, skip hoặc gọi handler local thay Lambda. Native S3 upload hiện tại là **presigned POST có điều kiện**, không phải PUT. Không đổi implementation để khớp wording bàn giao.
- Script chạy **một lần**; khi phiên chat gián đoạn, tiến trình tiếp tục và được đọc lại, không rerun hoặc gửi poison thứ hai.

Lệnh tái hiện trong môi trường được cấp quyền: `.venv/Scripts/python.exe .aws-sam/test-review/b4_controlled_e2e.py`. **Không chạy lại** để xem báo cáo: runner có writes và guard preflight queue/data sẽ khác; chỉ đọc evidence. Runner hash được lưu trong JSON. Credentials DPAPI chỉ dành cho Windows user được cấp quyền, không phải artefact để publish.

## Bảng kết quả

| Ca | Trạng thái | Phạm vi |
|---|---|---|
| preflight | **PASS** | Môi trường, targets, IAM, Budget, credentials |
| authentication_valid | **PASS** | Đăng nhập TestA/TestB, sub khác nhau |
| authentication_wrong_password | **PASS** | Mật khẩu sai |
| jwt_missing_invalid | **PASS** | Thiếu/sai JWT |
| health | **PASS** | API health |
| policy_search | **PASS** | Ba policy tổng hợp, lookup/search/not-found |
| policy_pagination_validation | **PASS** | Pagination và input/cursor lỗi |
| cors | **PASS** | Preflight từ CloudFront origin test |
| pdf_A | **PASS** | PDF TestA: upload/worker/download/hash |
| pdf_B | **PASS** | PDF TestB: upload/worker/download/hash |
| authorization_both_directions | **PASS** | Ownership hai chiều |
| upload_size_boundary | **PASS** | 10 MiB / 10 MiB + 1 byte |
| upload_mime_key_tamper | **PASS** | Sửa MIME / signed key |
| invalid_pdf_bytes | **PASS** | Plain text gắn PDF |
| frozen_version_idempotency | **PASS** | Frozen version / submit lặp |
| partial_batch_direct | **PASS** | Direct Lambda partial-batch semantics |
| retry_dlq | **PASS** | SQS retry/redrive thật |
| observability_logs | **PASS** | Quét logs có giới hạn |
| observability_metrics_alarms | **PASS** | Metrics / năm alarms |
| frontend_browser | **NOT_RUN** | Browser đăng nhập/nghiệp vụ trên CloudFront |

## Authentication, API và phân quyền

Cả TestA và TestB nhận token qua Cognito client test, issuer/audience đúng pool/client và subjects khác nhau. Email unverified không chặn flow này; không sửa thuộc tính. Một lần mật khẩu sai bị NotAuthorizedException; thiếu/sai JWT vào protected endpoint trả 401. Health 200; seed đúng ba policy fixture bằng conditional put, không overwrite; lookup/search/pagination và invalid input đúng hợp đồng. CORS OPTIONS từ frontend test trả 204 và exact origin.

TestA và TestB không đọc/status/download/submit tài liệu của nhau: sáu thao tác cross-user trả **404**, thư viện riêng không lộ tài liệu user còn lại. Chỉ kiểm tra hai identities được duyệt, không enumerating production IDs.

## PDF và tính toàn vẹn

Hai PDF nhỏ được tạo theo cấu trúc PDF/xref tổng hợp, không PII; signed POST **201**, submit pending, worker processed với processed_at và SHA-256. Hash của file gốc, worker và bản tải về khớp:

- pdf_A: `cddd003cb1498313425bced900b3b954194173455476680174d3f3ac489f5b38`.
- pdf_B: `79f8f210c2b2abf72804a59830203153f2efcf382091acd609d6f2b4402206d1`.

- File **10.485.760 bytes** được upload và worker xử lý; **10.485.761 bytes** bị S3 từ chối. Không bỏ qua giới hạn để tạo kết quả PASS.
- Tampered Content-Type hoặc key bị S3 từ chối; plain text mang MIME PDF upload được nhưng worker xác định **INVALID_PDF**, download và resubmit trả **409**.
- Upload một phiên bản mới của TestA sau submit không thay frozen download hash; submit lại terminal document vẫn processed.
- Chức năng hiện tại kiểm tra MIME/size/header và hash, **không có full PDF parsing, malware scan, OCR hoặc AI/RAG**. PDF fixture có cấu trúc hợp lệ không chứng minh sản phẩm kiểm tra mọi cấu trúc PDF độc hại.

## Worker, partial batch và retry/DLQ

Worker thực sự xử lý documents qua SQS. Một direct Lambda invoke dùng mixed event với dependencies AWS thật: record JSON lỗi được trả trong batchItemFailures, record khỏe được acknowledge. **Record khỏe là document đã processed**, nên phép thử direct xác minh idempotent acknowledgement và partial-failure contract; không chứng minh fresh processing trong mixed event. Fresh processing đã được chứng minh riêng qua SQS. Mapping vẫn BatchSize=1; không tuyên bố natural two-record batch delivery.

Poison được gửi **một lần** lúc 2026-10-21T16:47:57.986406+00:00, redrive được quan sát 2026-10-21T16:57:30.689943+00:00; khoảng 9 phút 33 giây. Không có doc_id nên lỗi KeyError trước document lookup. Main queue về 0, DLQ có đúng 1. Một ReceiveMessage chẩn đoán với VisibilityTimeout=0 xác nhận body marker và message ID khớp, ApproximateReceiveCount **4** (ba lần nhận main + lần đọc DLQ). Không DeleteMessage, purge, redrive hoặc đổi visibility config. Message còn nguyên để cleanup riêng.

## Observability và Budget

Quét **158 log events** của ba log groups trong cửa sổ test, complete theo giới hạn ba pages/group. Không phát hiện exact password/token hoặc pattern JWT/signed capability/access key trong phạm vi đã đọc; **không phải chứng minh tất cả logs/tương lai không có secret**. Chỉ xuất counts/error classes, không raw log messages. Worker có **JSONDecodeError=1** từ direct batch và **KeyError=3** từ retry poison.

Metrics thực đọc: API Lambda Invocations=37, worker=8, recovery=6 trong cửa sổ queried; Errors/Throttles đã xuất hiện đều 0. Main queue NumberOfMessagesReceived=7, NumberOfMessagesDeleted=4. API HTTP calls tổng 40 gồm requests bị JWT chặn ở Gateway và CORS, nên không bắt buộc bằng Lambda Invocations. Lambda Errors=0 không có nghĩa không retry: partial failures được ghi qua response/logs/SQS. CloudWatch có publication lag; DLQ gauges ở snapshot metrics đầu còn 0 trong khi GetQueueAttributes đã báo 1, không dùng series trễ để phủ nhận redrive.

Alarms trước test: cả năm OK. Ngay sau test queue-age ALARM, DLQ alarm còn OK; một follow-up read-only sau đó ghi:

| Alarm | Trạng thái follow-up |
|---|---|
| policy-assistant-fcaj-test-DocumentDLQAlarm-b1DKU337nh8A | **ALARM** |
| policy-assistant-fcaj-test-DocumentQueueAgeAlarm-oIF96hZ3Zegg | **ALARM** |
| policy-assistant-fcaj-test-Duration | **OK** |
| policy-assistant-fcaj-test-Errors | **OK** |
| policy-assistant-fcaj-test-RecoveryErrorAlarm-uGYsYmQ0uObI | **OK** |

Hai ALARM là hệ quả đã dự kiến của fault injection; không sửa/xóa để ép OK. DLQ alarm có thể tiếp tục ALARM khi message được giữ lại; queue-age state có thể còn trễ sau khi main queue rỗng. Không chứng minh SNS email delivery; AlertEmail ứng dụng đang rỗng. Budget email recipient theo Console trước Active (legacy), verification 0/1, **delivery NOT_VERIFIED**.

Budget preflight: COST/MONTHLY/20 USD/UnblendedCost, loại Credit/Refund, toàn account; đúng Actual80/Actual100/Forecasted100, không Actions. Sau test Budget đọc lại amount20; **Actual 5,479 USD**, Forecasted8,539 USD. Đây là Billing snapshot có độ trễ, không phải số đo riêng chi phí B4 hoặc invoice cuối tháng; không gán delta account cost cho test. Budget không hard cap.

## Guardrails và dữ liệu để lại

| Hoạt động | Thực tế | Giới hạn |
|---|---:|---:|
| api | 40 | 160 |
| sessions | 4 | 5 |
| s3_requests | 11 | 12 |
| upload_bytes_attempted | 20974553 | 25165824 |
| policy_items_created | 3 | 3 |
| direct_worker_invocations | 1 | 1 |
| poison_send_attempts | 1 | 1 |
| dlq_receive_calls | 1 | 1 |

Ba Cognito auth attempts (hai đúng, một sai). Không thêm users, không sửa pool/IAM/Lambda/CloudFormation/frontend/Budget/tags. Bốn metadata sessions, các S3 versions tổng hợp, ba policy fixtures và một DLQ message được giữ; không cleanup. Bucket/tables/policy Retain vẫn có thể tính phí; không tháo HTTPS policy. Stack cũ metadata không đổi: UPDATE_COMPLETE, LastUpdatedTime 2026-10-19 11:10:29.038 UTC. Không có production write target; đây không là full drift scan.

## GO/NO-GO tiếp theo

**GO để nghiệm thu kỹ thuật backend/API-SDK trên AWS bằng evidence hiện có.** **Chưa đủ bằng chứng để đánh dấu browser/frontend E2E hoàn chỉnh PASS**: authenticated browser flow, browser upload/download, responsive behavior và screenshots trên CloudFront thực tế **NOT_RUN**. Local browser suites trước B2 không thay thế chúng. Chưa chứng minh email delivery hoặc mọi tình huống recovery/availability/load; không hứa đầy đủ FCAJ evidence/chuyên cần/diagram do sinh viên tự vẽ.

Sau báo cáo này **DỪNG**. Browser acceptance bổ sung hoặc bất kỳ thay đổi/sửa lỗi tiếp theo cần phạm vi được duyệt riêng; cleanup/users/retained data cần Approval C. Không tự redrive/purge/reset alarms, deploy hay commit/push.

## Evidence

- [B4 cases, operations, limits và metrics/log aggregates](evidence/approval-b4-e2e.json)
- [Service preflight read-only](evidence/approval-b4-service-preflight.json)
- [Alarm follow-up](evidence/approval-b4-alarm-followup.json)

## Đồng bộ tài liệu và kiểm tra local

Workshop Việt/Anh đã có chương AWSValidation và cập nhật trạng thái AWSReadiness/B1–B4 theo evidence; không bịa worklog quá khứ, ảnh hoặc thông tin sinh viên. Hugo v0.167.0 build PASS (EN130/VI129; ba theme deprecation warnings có sẵn). Link checker: 131 HTML, 12.582 references, 0 failures. Không publish website. JSON consistency và scan credentials riêng trên các file evidence mới PASS. [Local validation](evidence/approval-b4-local-validation.json).
