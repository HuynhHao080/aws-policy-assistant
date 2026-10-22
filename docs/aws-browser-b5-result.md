> Latest B5-R7:10/10 browser cases PASS sau API fix, không đổi kết quả lịch sử B5. [R7 result](aws-browser-b5r7-result.md). Cleanup chưa thực hiện.

# Approval B5 — Browser E2E thực tế: FAIL / STOPPED

**NO-GO nghiệm thu browser. 2 PASS / 1 FAIL / 0 BLOCKED / 7 NOT_RUN.** Đã dừng ngay tại PDF UI pipeline, không sửa source/config hoặc deploy/rerun. B4 API/SDK PASS vẫn là bằng chứng riêng; không thay thế kết quả browser này.

## Môi trường và thời gian

- Browser thật: **Microsoft Edge 155.0.4283.62**, Chromium, **headless**, Playwright; network AWS thật, không mock responses. Route interception chỉ làm allowlist/cap guard, không fulfill response giả.
- Cửa sổ browser: **2026-10-21T17:19:40.726Z – 2026-10-21T17:19:48.094Z**, khoảng **7.368 giây**; UTC+7 khoảng **00:19:40–00:19:48 ngày22/10/2026**.
- Account …0098, ap-southeast-1, stack policy-assistant-fcaj-test CREATE_COMPLETE/45 resources; frontend https://d3ataim7dfsl7t.cloudfront.net/.
- Preflight đọc STS/CF outputs+resources, frontend config và SHA app.js, pool/client binding, S3 bucket region, API endpoint, Lambda env tables/bucket/queue đúng stack test; IAM không Allow Resource `*`, không tham chiếu stack cũ. Budget20USD/ba notifications/no Actions đúng. Main0, DLQ1 là baseline giữ lại từ B4.
- Hai local PDF hash khớp manifest; chỉ TestA fixture được chọn ở UI. TestB chưa chạy. Credentials DPAPI vào subprocess stdin trong bộ nhớ, không argv/env/plaintext file. Không trace/HAR/video hoặc raw console/network dumps.

## Kết quả từng ca

| Ca | Trạng thái | Nội dung |
|---|---|---|
| real_browser_load | **PASS** | CloudFront thật, render/config đúng outputs |
| testa_login_search | **PASS** | Login TestA và tìm refund/POL-001 |
| testa_pdf_flow | **FAIL** | Upload PDF TestA qua UI |
| testa_logout | **NOT_RUN** | GlobalSignOut TestA |
| testb_login_isolation | **NOT_RUN** | Login TestB và ownership trên UI |
| testb_pdf_flow | **NOT_RUN** | Upload/download TestB |
| testb_logout | **NOT_RUN** | GlobalSignOut TestB |
| testa_reverse_isolation | **NOT_RUN** | Kiểm tra ownership ngược |
| testa_final_logout | **NOT_RUN** | Logout phiên TestA cuối |
| responsive_console | **NOT_RUN** | Hoàn tất responsive/screenshots/console acceptance |

CloudFront page render/config đúng; TestA đăng nhập qua giao diện và policy search trả đúng POL-001. Upload-session POST trả **200**, tạo metadata; ngay sau đó UI upload-result chuyển error. Không có request S3 được route observer thấy; không submit, processing hoặc download tiếp. Không có cross-user attempt hoặc thành công ngoài dự kiến vì đã dừng trước TestB.

## Số lần thực tế và guardrails

| Hoạt động | Thực tế | Cap |
|---|---:|---:|
| Login | 1 | 3 |
| GlobalSignOut | 0 | 3 |
| Upload sessions | 1 | 2 |
| S3 file uploads observed | 0 | 2 |
| S3 file downloads | 0 | 2 |
| Files delivered by browser | 0 | 2 |
| Bytes uploaded | 0 | 131072 |
| Application API requests | 2 | 80 |
| Dynamic requests gồm Cognito/API/S3 | 3 | 80 |

API requests: GET /Prod/policies200, POST /Prod/documents/upload-session200. API Gateway Count trong minute17:19UTC cũng là2; browser-internal preflight không được coi là request riêng nếu instrumentation không export. Một Cognito InitiateAuth làm dynamic requests=3. Guard không chặn request nào, không page exception, hai console error entries (không lưu text); không phát hiện pattern secret trong console đã kiểm tra. Không dùng counts thấp để coi upload PASS: chọn file trên UI không đồng nghĩa file đã rời browser.

Browser run đúng **một lần**. Trước launch, local runner IAM guard từng coi ký tự `*` trong scoped ARN string là exact Resource `*`; diagnostic read-only xác định lỗi phép membership, normalized-list self-test4cases PASS trước launch. Không thay IAM, app source, template hoặc nới giới hạn AWS. Guard correction giữ evidence riêng; không có auth/browser writes trong prelaunch bị chặn.

## Điều tra read-only sau FAIL

- Live CSP `connect-src` cho phép S3 `https://*.s3.ap-southeast-1.amazonaws.com`.
- S3 CORS cho phép chính xác frontend test, methods GET/POST.
- Tái hiện signer local dùng **credentials giả, không gọi AWS hoặc tạo capability thật**: cùng boto3 version1.43.116 với saved Lambda build, sinh endpoint dạng **`[test-bucket].s3.amazonaws.com`**. Host dạng này không khớp allowlist regional CSP.
- Kết hợp upload-session200, không S3 network request, hai console errors và cấu hình mismatch: **LIKELY_CSP_S3_ENDPOINT_MISMATCH**.
- **Giới hạn:** raw console CSP text và signed response thực tế không được giữ để bảo vệ dữ liệu; không khẳng định đã capture exact CSP violation/hostname từ Lambda response này. Không gọi thêm signed-session API hoặc đăng nhập lại để cố chứng minh. Đây là nguyên nhân khả dĩ có bằng chứng cấu hình, chưa là packet-level confirmation.

Không sửa CSP hoặc SDK endpoint trong B5. [Phương án sửa cần phê duyệt riêng](browser-b5-remediation-proposal.md).

## Observability, Budget và tài nguyên cũ

Post-read khoảng **17:21UTC ngày21/10**: main queue visible/inflight/delayed=0; DLQ vẫn visible1/inflight0. Không nhận/xóa/redrive/purge DLQ; không poison mới. QueueAge **OK**, DLQ **ALARM** theo baseline B4, ba Lambda alarms **OK**. Không reset alarm.

API Lambda có2 invocations, Errors0/Throttles0 trong minute17:19; worker series rỗng trong cửa sổ (không dùng empty series để chứng minh zero). Recovery tiếp tục lịch tự động; không manual invoke. Post log scan có12 events ở pages đầu, không thấy exact passwords/JWT/signed-field patterns; còn pagination tokens nên **scan không toàn diện**, không tuyên bố tất cả logs không có secrets. Không export raw messages. Billing snapshot read-back: Budget20USD, Actual5,479USD/Forecast8,539USD; last update10:05UTC, không phải chi phí riêng B5 hoặc invoice realtime. Email delivery vẫn NOT_VERIFIED.

Stack cũ metadata UPDATE_COMPLETE/LastUpdatedTime2026-10-19 11:10:29.038UTC không đổi, không production write target; không full drift scan.

## Dữ liệu còn lại và credentials

- Metadata `doc-0dfd6bcb45f347ecab0a7ae5f4b636d1` thuộc TestA tổng hợp: **uploading**; S3 HeadObject404 xác nhận chưa có object tại session key lúc đọc. Không tự xóa metadata.
- Ba policy fixtures, bốn document sessions/S3 versions và một DLQ poison từ B4 còn là inventory riêng; B3 vẫn đúng hai users. Không thêm dữ liệu TestB trong B5.
- **GlobalSignOut chưa chạy** do dừng ngay khi lỗi. Browser/context đã đóng, credentials/tokens không persist trong reports/storage; không tuyên bố đã revoke phiên server. Không tự revoke/reset hoặc xóa users sau fail; cần phạm vi tiếp theo được duyệt.
- **Screenshots=0**: runner chỉ chụp sau PDF success, nên không có ảnh browser đã làm xong upload/download. Không tạo ảnh giả từ fixtures.

## Quyết định

**NO-GO browser acceptance; không dùng B4 backend PASS để ghi B5 PASS.** Cần duyệt riêng phương án sửa local/regression, review bản triển khai test mới và quyền deploy, rồi một browser rerun mới có cap riêng. Không tự tận dụng quota B5 còn lại để thử tiếp sau FAIL. Cleanup/DLQ deletion/Retain/user removal thuộc Approval C tách riêng.

B5 không deploy, sửa IAM/CloudFormation/Lambda/frontend/Budget, tạo users, gửi poison, nhận/xóa DLQ hoặc commit/push. Chỉ một authorized Cognito login và một upload-session metadata write đã xảy ra qua UI trước dừng.

## Evidence

- [Preflight AWS](evidence/approval-b5-execution-preflight.json)
- [Prelaunch guard diagnostic](evidence/approval-b5-prelaunch-guard-diagnostic.json)
- [Controller / credential-handoff scan](evidence/approval-b5-execution-controller.json)
- [Browser cases/counters](evidence/approval-b5-browser.json)
- [Post-failure investigation](evidence/approval-b5-post-readonly.json)
- [Summary](evidence/approval-b5-result.json)

## Kiểm chứng tài liệu local

JSON/counters và kiểm tra credential/account redaction PASS; fingerprint app/template và frontend JS không đổi so với candidate/B2. Workshop Việt/Anh đã ghi B5 FAIL, không publish; Hugo build PASS với ba cảnh báo theme có sẵn; 131 HTML/12.582 references/0 broken links. Các kiểm tra tài liệu này không thay đổi B5 FAIL. [Validation](evidence/approval-b5-local-validation.json).
