# B5-R7 — controlled AWS Browser E2E rerun result

**PASS:10, FAIL:0, BLOCKED:0, NOT_RUN:0 trong browser test plan đã duyệt.** GO nghiệm thu luồng browser giới hạn; GO demo test với các mục vận hành còn mở. Không phải production readiness/exhaustive security certification.

## Môi trường và thời gian

Account STS …0098, ap-southeast-1; policy-assistant-fcaj-test UPDATE_COMPLETE. Frontend https://d3ataim7dfsl7t.cloudfront.net/. Preflight xác minh API hash mới, stack outputs/frontend config/API/Cognito/S3/CloudFront cùng tài nguyên test; IAM runtime policies không exact Allow Resource *, không attached managed policies trên API/worker đã kiểm. Rule/security không bị chỉnh sửa.

Browser **Microsoft Edge155.0.4283.62, Chromium/Playwright headless trên Windows**, real HTTPS, không mocks/SDK thay UI. 2026-10-21T18:33:51.309Z → 2026-10-21T18:34:09.011Z, tức01:33:51–01:34:09 ngày22/10/2026 UTC+7,17.702giây. Postflight kết thúc 2026-10-21T18:35:29.753295+00:00 (01:35:29 UTC+7). Cả preflight/browser/postflight trong15phút. Browser chạy đúng một lần, không retry toàn lượt.

Chỉ hai TestA/TestB đã có; hai PDF synthetic đã chuẩn bị,609bytes/file và hash khớp. DPAPI decrypt current-user vào memory, truyền qua anonymous stdin pipe, không argv/env/plaintext-file. Không logs/traces/HAR/signed URLs. Screenshot mask username/password/auth/JWT fields; đã xem cả hai ảnh. Một lỗi namespace trong helper postflight local được sửa rồi chỉ đọc lại postflight; không chạy lại browser, không tạo thêm dữ liệu vì lỗi đó.

## Cases

| Case | Status |
|---|---|
| real_browser_load | PASS |
| testa_login_search | PASS |
| testa_pdf_flow | PASS |
| testa_logout | PASS |
| testb_login_isolation | PASS |
| testb_pdf_flow | PASS |
| testb_logout | PASS |
| testa_reverse_isolation | PASS |
| testa_final_logout | PASS |
| responsive_console | PASS |

TestA login→policy search tìm POL-001→upload→processed→download→GlobalSignOut. TestB login→library không hiện docA, nhập docA qua UI status/download đều404→upload/processed/download docB→GlobalSignOut. TestA login lần3→library không hiện docB và status/download404→GlobalSignOut. UI báo lỗi404, không false success; logout trảHTTP200, JWT field cleared, thao tác protected bị chặn local không thêm network. Mobile390x844 không horizontal overflow; page errors0.

Không chỉ suy luận ownership từ library: bốn foreign-document status/download requests qua UI thực sự bị API404 hai chiều. Có4console error entries trong lượt có4HTTP404 cố ý; không giữ raw console, không khẳng định mapping từng console entry vì chưa capture raw. CSP violations0, console sensitive matches0, guard blocks0. Không thực hiện wrong-password/retry/DLQ tests lần nữa.

## Limits và request accounting

| Hạng mục | Thực tế | Giới hạn |
|---|---:|---:|
| Login |3|3|
| Cognito GlobalSignOut |3|3|
| Upload sessions |2|2|
| S3 POST uploads |2|2|
| S3 GET downloads / browser files |2 /2|2|
| PDF bytes upload |1.218|131.072|
| Application requests động, gồm Cognito/S3/API/polling |27|80|
| API Gateway requests trong số trên |17|80 tổng|
| Browser duration |17,702s|900s trừ preflight time|

Request route guard và browser request observer đều27. Counts là browser application traffic; AWS control-plane reads pre/postflight không phải application API requests. Static CloudFront assets không tính vào27. Không có extra login/refresh/poison hoặc DLQ operations. Không tăng quota/rerun sau lỗi.

## Regional S3 và integrity

Hostname đã che account:
`policy-assistant-fcaj-test-documents-********0098.s3.ap-southeast-1.amazonaws.com`.

Runner chỉ allow đúng regional hostname của bucket test; browser nhận POST201 và GET200 cho cả hai file,0CSPviolation. Đây là evidence thực tế sau fix, khác fixture local trước đây. Không giữ query/signature/credential. B5 FAIL cũ không bị sửa thành PASS; R7 là bằng chứng mới khắc phục browser flow.

| Identity | Document | Fixture/worker/download SHA256 |
|---|---|---|
| TestA |doc-0ca388ce767943bdb439afb9852730ef|ec60bdc781a7584ace672151908a04640bf4e5217d3562c4bbb374a753c4029a|
| TestB |doc-1d861bcda8b647a4aedea51ef55c5717|44467808b22c3c0c303f911341a58a2ae7fad69c10c9df1c0d2fa2b9373a4dae|

Current implementation **kiểm PDF/size/version, tính hash, rồi download cùng frozen S3 version**, không OCR/AI hoặc transform PDF. Vì contract này, byte-for-byte equality input/worker/S3-response/browser download là tiêu chí đúng. Không áp dụng giả định ấy cho một pipeline output biến đổi khác. UI chỉ success sau processed/download/hash check; postflight cả hai metadata processed, object609bytes, version metadata bằng current version.

## Postflight observability và cost

- Stack UPDATE_COMPLETE; cả ba Lambda Active/Successful; API CodeSha256 đúng B5-R6; old stack metadata không đổi trong phạm vi đọc.
- Main queue visible/not-visible/delayed0; DLQ visible khoảng1, hai counters khác0. Không ReceiveMessage: không xác minh body/message identity trong R7; chỉ phù hợp baseline.
- DLQ ALARM, QueueAge/Duration/Errors/RecoveryError OK. Không reset alarm. Một số OK do missing data treated nonbreaching, không coi đó là workload proof.
- CloudWatch3Lambda groups: **65events** trong bounded window, sensitive-pattern/known-secret findings0. Không lưu raw logs. Scan không bảo đảm tất cả future/delayed logs hoặc mọi loại secret đều sạch.
- Budget20USD COST/MONTHLY, đúng3notifications ACTUAL80/100 và FORECASTED100, trạng tháiOK. Snapshot actual5.479USD/forecast8.539USD, có Billing lag, không phải incremental test cost. Email verification chưa recheck; delivery NOT_VERIFIED. Budget không hard cap.

## Inventory chờ Approval C

**R7 tạo2metadata records và2S3object versions**, tổng1.218bytes PDF, IDs trong bảng. Browser downloaded2files vào context tạm; chỉ SHA được lưu, không tạo output object riêng. Có processing/SQS transient work đã drain; không còn main backlog theo counters.

Known two-user inventory có **7metadata records,7object versions/6keys,0delete markers**:

- R7:2records processed/2versions.
- B4:4records (3processed,1failed INVALID_PDF),5versions; có file10MiB và một doc có2versions do controlled overwrite test B4.
- B5 cũ: doc-0dfd6bcb45f347ecab0a7ae5f4b636d1 vẫn uploading,0object versions. Không dùng lại hoặc sửa/xóa.

Flag `version_bound=false` trên một B4 record trong inventory chỉ nghĩa latest HeadObject version khác metadata frozen version; phù hợp overwrite fixture trước đó, không chứng minh corruption/mất frozen version. Không GET lại PDF cũ trong R7.

Ngoài inventory document còn3synthetic policies B4 theo hồ sơ trước,2Cognito users,1DLQmessage baseline,artifacts/change sets/logs và4Retain resources. R7 không quét lại policies toàn bảng hoặc lập account-wide inventory, không ghi chúng là fresh verified counts. Tài nguyên Retain gồm2DynamoDBtables/DocumentsBucket/HTTPS policy; cleanup phải giữ TLS protection phù hợp, có approval riêng. Không purge/delete tài nguyên hay dữ liệu.

## Decision

**GO browser acceptance trong scope đã chạy. GO demo test hiện tại**, với DLQALARM do diagnostic message còn lại, email delivery chưa chứng minh, cleanup/retention cost và giới hạn browser coverage cần ghi rõ. Không tuyên bố mọi FCAJ evidence hoàn tất, production release hoặc đa trình duyệt PASS.

Không cần tự rerun để tăng bằng chứng. Approval C riêng cho mọi cleanup và thay đổi khác; không có deployment/commit/push trong R7. DỪNG.

## Evidence

- [Browser cases, network status và hashes](evidence/approval-b5r7-browser.json).
- [Preflight/controller/counters](evidence/approval-b5r7-controller.json).
- [Read-only postflight/inventory/log scan](evidence/approval-b5r7-postflight.json).
- [Summary và file fingerprints](evidence/approval-b5r7-result.json).
- [Desktop TestA screenshot đã mask](evidence/b5r7-testa-desktop.png).
- [Mobile logged-out screenshot đã mask](evidence/b5r7-mobile-loggedout.png).
