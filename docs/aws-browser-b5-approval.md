# Preparation B5 — Browser E2E & observability review

## B5-R — local fix đã kiểm chứng, chưa deploy

Edge local đã thu CSP connect-src violation với global S3 host; helper virtual addressing sinh regional POST/GET và fixture pipeline/hash PASS. Không đổi template/CSP/CORS/IAM/frontend. 129 backend,17 frontend,3 browser fixture,1 full-stack local PASS; SAM lint/build PASS;9 integration skip=NOT_RUN. [Hồ sơ B5-R](browser-b5r-remediation-review.md), [evidence](evidence/b5r-local-remediation.json).

B5 AWS vẫn FAIL. Chưa tạo change set vì artifact S3 mới đang bị cấm trong B5-R; cần duyệt upload/artifact/change set chưa execute, rồi execute/rerun riêng. Trạng thái chưa sửa local ở phần dưới là lịch sử B5.

## Trạng thái hiện hành — B5 browser FAIL, đã dừng

B5 chạy Edge thật lúc00:19:40–00:19:48 ngày22/10/2026 UTC+7: **2 PASS /1 FAIL /7 NOT_RUN**. Login/search TestA PASS; UI upload lỗi sau session200, chưa có S3 upload/download. Một metadata uploading còn lại; không rerun/fix/deploy/cleanup. Nguyên nhân khả dĩ CSP regional-only không khớp global S3 hostname của signer, chưa capture exact violation. [Báo cáo B5](aws-browser-b5-result.md), [phương án sửa chưa áp dụng](browser-b5-remediation-proposal.md).

**NO-GO browser acceptance.** B4 backend PASS là lịch sử riêng; không ghi browser PASS. Main queue0/QueueAge OK, DLQ1/ALARM, ba alarms Lambda OK. Mọi sửa/triển khai/rerun/cleanup cần duyệt riêng.

**READINESS: PREPARED. GO để trình Approval B5; NO-GO thực thi cho đến khi người dùng duyệt riêng.** Không đăng nhập, gọi API nghiệp vụ, tạo session/upload hoặc nhận/xóa message trong vòng chuẩn bị này.

## Bằng chứng đã đọc

B4 `docs/aws-test-e2e-b4-result.md`, `docs/evidence/approval-b4-e2e.json` và `docs/aws-live-test-plan.md`: 19 PASS, 0 FAIL/BLOCKED, browser NOT_RUN. Không chạy lại B4, không seed thêm hoặc gửi poison. Các kết quả B4 được giữ như snapshot lịch sử, không sửa thành browser PASS.

## Read-only AWS hiện tại

Cửa sổ xác minh **2026-10-21T17:07:16.654101+00:00 – 2026-10-21T17:07:22.257679+00:00**, tương ứng **00:07 ngày 22/10/2026 UTC+7**. STS exact account …0098; region ap-southeast-1; stack policy-assistant-fcaj-test CREATE_COMPLETE, 45 tài nguyên. Ba Lambda Active/Successful; SQS mapping Enabled/BatchSize1/ReportBatchItemFailures.

| Hạng mục | Quan sát |
|---|---|
| Main queue | Visible=0, inflight=0, delayed=0; đã quiescent |
| Main queue age | Datapoint mới nhất 17:05 UTC =0 giây |
| Queue-age alarm | **OK**, tự chuyển về lúc 17:03:20 UTC; không reset thủ công |
| DLQ | Approx visible=1, inflight=0, delayed=0; metric visible=1 lúc 17:05 UTC |
| DLQ alarm | **ALARM**, phù hợp visible>0; không lỗi mới được chứng minh chỉ từ ALARM này |
| Lambda Duration/Errors/Recovery alarms | Ba alarms **OK** |
| Budget | COST/MONTHLY/20 USD/UnblendedCost, loại Credit/Refund, toàn account; ba notifications, không Actions |
| Budget snapshot vừa đọc | Actual5,479/Forecast8,539 USD; Billing last update 10:05:01 UTC, có độ trễ; không là fresh CE/invoice/test-only cost |
| Email Budget | Delivery NOT_VERIFIED; Active(legacy)/0-of-1 theo Console trước, không kiểm tra lại recipient |
| Stack cũ | UPDATE_COMPLETE, LastUpdatedTime 2026-10-19 11:10:29.038 UTC; metadata read only |

Queue-age alarm đo Maximum ApproximateAgeOfOldestMessage >300 giây trong một period300; poison B4 từng lưu lại lâu nên ALARM, sau redrive/period evaluation đã tự OK. DLQ alarm đo Maximum ApproximateNumberOfMessagesVisible >0 trong period300 nên còn ALARM khi diagnostic message được giữ. Không chỉnh TreatMissingData hoặc ép alarm OK.

**Giới hạn xác minh DLQ:** GetQueueAttributes là số đếm xấp xỉ; kết quả1 phù hợp message marker/ID đã xác minh trong B4. Không ReceiveMessage trong B5 prep, nên không tuyên bố vừa đọc lại hoặc chứng minh lại identity/body chính xác. B4 là nguồn bằng chứng marker; B5 là nguồn trạng thái/count mới. Không có poison mới, delete, purge, redrive hoặc visibility change.

[Read-only evidence và metric timestamps](evidence/approval-b5-readonly-review.json).

## Quy trình browser đề nghị — chưa chạy

Chỉ frontend https://d3ataim7dfsl7t.cloudfront.net/; real browser/Edge, clean contexts, không mock/intercept trả response giả. Theo dõi actual responses với metadata đã lọc, không persist headers/bodies nhạy cảm. App hiện tại dùng presigned **S3 POST**, không PUT.

| Bước | Thao tác UI sau khi được duyệt | Kết quả cần chứng minh |
|---|---|---|
| 0 | Read-only preflight, config/targets/DPAPI/guard review; baseline DLQ1/main0 | Chỉ tài nguyên test, không đòi DLQ=0 vì giữ fault B4 |
| 1 | Login TestA (phiên1), lookup POL-001 và keyword refund | UI xác thực/hiển thị đúng; không lộ password/token |
| 2 | Chọn PDF TestA local → upload → xử lý → download | Một upload session, S3 POST201, submit/status thật; UI chỉ success sau worker processed + SHA-256 file gốc/worker/download bằng nhau |
| 3 | Logout TestA | UI xóa session/password/token; GlobalSignOut của đúng synthetic user thành công; thao tác protected sau logout bị UI chặn |
| 4 | Context sạch, login TestB (phiên2), refresh library; nhập docA vào status/download | Tài liệu A không có trong list; status/download trả404 và UI hiển thị lỗi, không false success |
| 5 | TestB upload PDF local và download, rồi logout | Session thứ2, hash khớp; không tạo user hoặc policy mới |
| 6 | Context sạch, login TestA lần2 (phiên3), list/status/download docB để kiểm tra ngược, logout | Không lộ tài liệu B,404/error UI. Không download body trái phép |
| 7 | Kiểm tra desktop/mobile layout, console/page errors; screenshot sau masking | Không PII/credentials/JWT/signed URLs; không screenshot DevTools/Network/console raw |
| 8 | Read-only logs/metrics/alarms và artifact/evidence checks | Main về0; DLQ giữ baseline1, không poison mới; so sánh before/after theo timestamps |

**Logout là thao tác AWS cần duyệt:** source gọi `GlobalSignOut` với access token; tối đa3 lần cho đúng hai users test, có thể revoke phiên cũ của chính hai identities này. Không gọi vào user thật/pool cũ. Kiểm chứng local state + response GlobalSignOut, không hứa JWT API Gateway bị từ chối ngay sau logout hoặc kiểm thử reuse token ngoài phạm vi UI.

Không gọi SDK/API để vượt qua một UI lỗi rồi coi browser PASS. Nếu UI chỉ copy hidden backend result không phản ánh đúng success/failure, ghi FAIL và dừng; không sửa/redeploy trong B5.

## Giới hạn đề nghị

- Tối đa **3 login sessions / 3 GlobalSignOut**, chỉ TestA/TestB; không test sai password lại, không reset/đổi thuộc tính/email verification hoặc tạo users.
- Tối đa **2 upload sessions, 2 S3 POST, 2 successful downloads**; hai PDFs tổng hợp ≤64 KiB/file, tổng ≤128 KiB. Không overwrite hoặc duplicate-click/resubmit để thử vô hạn.
- Tối đa **80 application requests** gồm polling/CORS preflight; tối đa2 policy-search pages. UI refresh/list dùng trong mức này. Nếu near-cap, dừng thay vì tự mở rộng cap.
- Tổng tối đa **15 phút**; mỗi document chờ worker tối đa90 giây, poll cách5 giây. Không auto-retry write/login/upload sau timeout; đọc trạng thái và đánh dấu PARTIAL/BLOCKED.
- **0 poison / 0 direct worker invoke / 0 DLQ Receive/Delete/Redrive/Purge / 0 deploy/config change**. Queue processing tự nhiên của document mới vẫn xảy ra qua mapping hiện có.
- Đề nghị soft allowance **0,10 USD/lần** để vận hành; đây là khoản dự phòng do người thực hiện đề xuất, **không phải báo giá AWS, số đo hoặc hard spending cap**. Không lập claim có thể dừng đúng0,10USD vì Billing trễ. Giới hạn requests/bytes/thời gian là guardrails có thể kiểm soát; không load test/AI/dịch vụ mới.
- Trước run dừng nếu Budget Actual≥16USD hoặc Forecasted≥20USD, cấu hình Budget khác, hoặc chi phí bất thường chưa giải thích. Không sửa Budget. Fixed monthly model6,6306USD/test từ tài liệu cũ không là estimate cho một browser run.

## Credentials, tokens và minh chứng

DPAPI B3 được dùng dưới đúng Windows user; sau phê duyệt, runner được review giải mã trực tiếp trong bộ nhớ để điền UI, không yêu cầu gửi password vào chat, không đặt trong CLI args/env hoặc test source. Nếu không có cơ chế điền UI không lộ tool arguments/log, **BLOCKED**, không xuất plaintext để thử tiện hơn. Không bật Playwright trace/HAR/video/request dump vì có thể chứa auth/signed fields; không in raw errors. Secret values không trở thành fixture.

Chỉ capture screenshot sau khi password/new-password/JWT/MFA inputs rỗng hoặc masked; mask username/auth-status nếu chứa identity, advanced config closed. Không chứng minh email delivery bằng screenshot cấu hình. SHA-256 và status/time là bằng chứng, không lưu signed URLs. Sau run đóng context, không tự rotate credentials hoặc thay users. Browser/tool credential injection là **thiết kế chưa chạy**, không ghi VERIFIED automation chỉ vì B2 local browser tests từng PASS.

## Quan sát và điều kiện dừng

Ghi thời điểm UTC và run ID, counts và SHA-256; đọc logs ba functions trong đúng time window, scan exact secrets/patterns trong bộ nhớ rồi chỉ xuất aggregates. Đọc metric samples với timestamp và năm alarms literal states; cho publication lag, không gọi missing datapoint là zero. DLQ ALARM baseline1 được chấp nhận, nhưng DLQ tăng>1, main backlog tăng không khớp hai docs, worker fail bất thường hoặc throttling là điều kiện dừng.

Dừng ngay nếu account/pool/client/API/bucket/queue/domain mismatch, IAM rộng nghiêm trọng, foreign document thành công/PII leak, UI success khi backend chưa xác nhận, checksum mismatch, email challenge/verification mới, permission/service blocker, credential/log leak, timeout hoặc vượt cap/chi phí. Chỉ điều tra read-only; không sửa IAM/code/config, deploy, login lại hoặc tạo session mới để bypass lỗi. Các cases chưa chạy giữ NOT_RUN, không biến skip/mock thành PASS.

## Cleanup phải tách Approval C

B5 có thể để lại tối đa2 metadata records,2 S3 uploaded versions (và partial/uncertain records nếu lỗi),2 local synthetic downloads và screenshots đã lọc. Inventory theo run ID/doc IDs/object versions và trạng thái thực tế; không tự xóa để quay lại baseline. Chính sách fixture trong local không chứa credential hoặc PII.

B4 còn ba policy fixtures/bốn document sessions/S3 versions/một DLQ poison; B3 hai users; bốn Retain resources và shared artifacts là các đối tượng riêng. Approval B5 **không cho phép** xóa bất kỳ mục nào trong số này. Approval C phải nêu cụ thể DeleteMessage/DeleteObjectVersion/DynamoDB items/users hoặc DeleteStack/Retain destruction, backup và giữ HTTPS policy cùng DocumentsBucket; không xin quyền cleanup chung chung trong B5.

## Đề nghị người dùng phê duyệt

> Chỉ thực hiện browser E2E trên stack policy-assistant-fcaj-test/account …0098/ap-southeast-1 và domain test đã nêu, với đúng hai B3 users, tối đa3 login/3 GlobalSignOut,2 upload sessions/2 uploads/2 downloads,80 application requests,128KiB upload và15 phút. Chấp nhận đọc observability; không poison/deploy/config/cleanup hoặc commit-push. Gặp bất thường dừng và báo lại. Cleanup/DLQ deletion cần Approval C riêng.

**Hiện tại: PREPARED_NOT_AUTHORIZED. Browser execution: NOT_RUN. AWS writes trong preparation:0.** Cần phê duyệt riêng và refresh preflight/guard review ngay trước run, không tự chuyển sang thực thi.

[Proposal machine-readable](evidence/approval-b5-proposal.json).

## Local fixtures đã chuẩn bị

| Identity | File | Bytes | SHA-256 |
|---|---|---:|---|
| TestA | `docs/fixtures/browser-b5/synthetic-testa.pdf` | 609 | `ec60bdc781a7584ace672151908a04640bf4e5217d3562c4bbb374a753c4029a` |
| TestB | `docs/fixtures/browser-b5/synthetic-testb.pdf` | 609 | `44467808b22c3c0c303f911341a58a2ae7fad69c10c9df1c0d2fa2b9373a4dae` |
