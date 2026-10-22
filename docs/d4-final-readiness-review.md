# D4 — Final project readiness, local only

Ngày: 22/10/2026. **Hồ sơ local sẵn sàng để trình duyệt chọn file commit; public push NO-GO; AWS cleanup NO-GO.** D3-A vẫn **BLOCKED_PENDING_OWNER_OPERATIONAL_CONFIRMATION**. Không gọi AWS/GitHub, không authentication/E2E, không stage/commit/push. Các trạng thái AWS bên dưới là evidence lịch sử, không phải health check mới.

## Sản phẩm và mức độ hoàn thành

Policy Assistant phục vụ tra cứu policy theo ID/keyword và quản lý PDF riêng theo người dùng. Frontend qua CloudFront/private S3; Cognito xác thực; HTTP API kiểm JWT; API Lambda kiểm ownership theo sub; DynamoDB lưu policy/metadata; signed S3 POST giới hạn key/MIME/size; SQS chuyển việc cho Worker kiểm version/header/size và SHA-256; EventBridge/Recovery xử lý khoảng trống metadata→queue; retry/partial response/DLQ và CloudWatch hỗ trợ vận hành.

Không có Bedrock, RAG, OCR, full-text engine, trích nội dung PDF hay quét malware được nghiệm thu. `processed` chỉ phản ánh hợp đồng kiểm byte/version/hash hiện có. Download trả đúng frozen version đã kiểm; không phải output PDF đã biến đổi.

| Mốc | Kết quả được giữ nguyên | Giới hạn |
|---|---|---|
| B4 AWS API/SDK | **19 PASS, 0 FAIL/BLOCKED, 1 NOT_RUN** | Browser chưa chạy tại B4; direct mixed invocation không đồng nghĩa queue BatchSize 1 tự giao mixed batch |
| B5 ban đầu | **FAIL browser upload** | Giữ nguyên lịch sử lỗi, không đổi thành PASS |
| B5-R6 | API-only fix được deploy theo phê duyệt | Virtual S3 addressing, không nới IAM/CSP/CORS; Worker/Recovery giữ ZIP cũ |
| B5-R7 | **10/10 browser PASS** | Hai identities tổng hợp; không phải load test hay chứng nhận production |
| C0 | Inventory hoàn tất, **chưa cleanup** | 45 resources/4 Retain theo snapshot; inventory cần refresh trước delete |
| D2 / D3-A / D3-A2 | Exposure CONFIRMED / **BLOCKED** / mẫu xác nhận đã chuẩn bị | Không có containment/rotation evidence; không tự coi thiếu log là hết sử dụng |

Kết luận: chức năng test demo đã có bằng chứng AWS API và browser; hồ sơ được chuẩn bị local. Không tuyên bố production-ready hoặc demo live hiện đang healthy. Ngày kết thúc duy trì môi trường **chưa được chủ dự án chốt**.

## Git readiness và kiểm tra local

Hai repo được rà soát riêng: `policy-assistant-github` HEAD `80c4eef`; `aws-internship-worklog` HEAD `846d2ff`. D4 không đọc remote và không khẳng định trạng thái remote hôm nay. Manifest đầy đủ, status, hashes, scan scope và kết quả kiểm tra nằm ở [evidence D4](evidence/d4-local-readiness.json); số lượng trong manifest được cập nhật sau khi hoàn tất tài liệu.

D4 đọc working-tree tracked + untracked nonignored của cả hai repo, danh sách tracked, diff/status và ignore probes. Không xuất raw diff vì removed lines có thể chứa secret lịch sử. Git index phải vẫn rỗng. Source/API/Worker/Recovery, frontend, SAM, tests và runbooks được đối chiếu với báo cáo D1; D4 chỉ sửa docs. Không rerun các suite đã PASS khi không có thay đổi runtime.

Kiểm tra đã chạy trong D4: 41 source/config/test/tooling entries có hash trong manifest D1 giữ nguyên; 11 execution evidence/screenshots B1–R7 cũng giữ nguyên byte-for-byte so với D1. [Integrity evidence](evidence/d4-source-evidence-integrity.json). Hugo 0.167.0 build PASS (EN130/VI129), ba theme deprecation warnings; [link audit](evidence/d4-workshop-links.json): 131 HTML/12.604 references/0 failures. JSON dữ liệu và Python AST parse không lỗi trong phạm vi scan; Go template exception nêu dưới. `git diff --check` PASS ở hai repo. Không chuyển kết quả local thành AWS PASS mới.

Quét exact legacy username/password trong bộ nhớ, access-key/JWT/signed-query/private-key patterns, account/ARN patterns, JSON/Python syntax và tracked private paths. Không tìm thấy known username/password hoặc matched secret patterns trong các text candidates đã kiểm tra. Các cảnh báo chuỗi 12 chữ số là price range, số thập phân chi phí, đoạn SHA-256, hai synthetic account fixtures và hằng số của Mermaid theme; không trùng account thực đã lưu. Không đồng nghĩa mọi secret dạng encoded/novel đều bị phát hiện. History vẫn chứa credential-candidate đã public theo D2.

File `themes/hugo-theme-learn/layouts/index.json` là **Go template**, không phải JSON dữ liệu; lỗi parse JSON thô không phải lỗi website. Kiểm chứng bằng Hugo build/link check riêng. Binary/ảnh được inventory+hash; D4 không OCR hay chứng nhận lại toàn bộ ảnh. Giữ kết quả visual review D1 và yêu cầu review lại binary mới trước publication.

`.gitignore` app chặn .aws-sam, DPAPI, .env, credentials, session/token URLs, HAR/auth-state, dependencies và outputs. Worklog chặn public/resources, .env và key files; không dùng worklog để chứa DPAPI/HAR/vault. Không thấy private-path candidate đã tracked trong phạm vi kiểm tra. Ignore không làm sạch history hoặc tự loại file đã tracked.

## Phạm vi file có thể trình duyệt commit

Manifest là **danh sách ứng viên**, không phải cho phép public hoặc chỉ dẫn `git add .`. Chỉ chọn explicit paths, xem selected diff bằng công cụ không xuất secrets và scan lại đúng selection sau khi có phê duyệt.

| Nhóm | Ứng viên | Commit message đề xuất |
|---|---|---|
| Runtime + tests | `policy_assistant/`, `tests/unit/`, requirements, auth wrappers đã bỏ literals | `fix: secure owner-bound document processing and auth helpers` |
| IaC + guard tests | `template.yaml`, tests cấu hình/deployment liên quan | `infra: scope test permissions and retained-resource safeguards` |
| UI + kiểm tra offline | `frontend/`, npm manifests, `tests/frontend/`, `scripts/` mà CI cần, app CI | `feat: verify browser document workflow and integrity` |
| Handover + evidence | README, PROJECT_SUMMARY, .gitignore, docs, sanitized JSON, ảnh đã review, synthetic fixtures | `docs: record test acceptance and unresolved security gates` |
| Worklog riêng | VI/EN content, Hugo config và workflow đã review | `docs: align internship workshop with verified AWS results` |

Các commit runtime/IaC/UI có dependency; chọn nhóm cùng nhau nếu tách làm CI hỏng. Không cam kết mọi intermediate commit đã được test. Trước khi commit phải duyệt exact file list/diff, scan selection, xem deployment default và CI effects. Local commit giữ ancestor có exposure; nó không containment hoặc làm sạch history.

**Không public:** .aws-sam/private state/raw diff/vault, DPAPI, .env/credentials, session/token/presigned URLs, Lambda ZIP/deployment artifacts, HAR/raw trace/raw cloud logs, recipient email. `packaged.yaml` bị ignore. Binary mang thông tin chưa được review để riêng. Public Cognito IDs/API URL/CloudFront URL không phải secrets; chỉ giữ cấu hình cần thiết, mask account/ARN và không coi việc che ID là authorization.

## Việc bắt buộc và thứ tự ưu tiên

| Ưu tiên / gate | Việc còn thiếu | Phê duyệt / người thực hiện |
|---|---|---|
| P0 trước app public push | Chủ dự án trả lời [D3-A2](d3a2-owner-operational-confirmation.md); nếu còn dùng thì lập migration trước containment | Owner xác nhận rõ ràng, không suy từ 13 InitiateAuth hoặc thiếu log |
| P0 trước app public push | Thực hiện containment đúng phạm vi sau confirmation + preflight, lưu kết quả và residual JWT risk; xem xét D3-B/password safety nếu cần | Approval riêng tương ứng; D4 không disable/sign-out/reset |
| P0 trước app public push | Quyết định xử lý history/forks/caches/clones và SHA references; revoke không được thay bằng xóa history | Owner duyệt phương án Git riêng; không rewrite hiện tại |
| P1 trước commit/push | Exact selection, fresh scan/redaction, binary review, destination/branch và tác động CI | Approval commit và push riêng; không blanket stage |
| P1 trước worklog publish | Review publication content/remote-only gh-pages theo D2, contact/ảnh/quyền công khai; xác nhận main push tự publish Pages | Approval Pages riêng; không khẳng định worklog chứa cùng password |
| P1 trước cleanup | Owner chọn C A/B/C, chốt end date/demo, refresh inventory và provenance, quyền sở hữu data/external artifact, backup/retention/restore | Approval C riêng theo exact objects/versions/records/users/resources |
| P1 trước cleanup | Phân biệt 4 Retain: 2 DynamoDB tables, DocumentsBucket và HTTPS bucket policy; shared SAM deployment bucket không thuộc quyền xóa toàn bộ | Không tự xóa unknown data, retained resources hoặc shared artifact đang dùng |
| P2 trước production | Xác minh alert routing (SNS snapshot 0 subscriptions), Budget email delivery, DLQ handling/runbook, credential lifecycle, load/SLO/concurrency, restore/security review | Thiết kế và phê duyệt riêng, không chỉ tăng services |
| FCAJ trước nộp | Sơ đồ do sinh viên tự vẽ/giải thích bằng icon AWS, thông tin sinh viên, daily worklog thật, blog/event/office evidence, feedback/self-evaluation | Sinh viên cung cấp minh chứng; không bịa dates, attendance, ảnh, publish links |

Chi phí: 6.6306 USD/tháng là mô hình tải có giả định đã lưu, trước ưu đãi; không phải bill hiện tại hay AWS forecast mới. Budget 20 USD toàn account bao gồm legacy/test/shared, không hard cap; không dừng resources. Retain/logs/artifacts có thể tiếp tục tính phí; số Billing cũ không được gọi là real-time. D4 không xác minh giá mới, không sửa Budget hoặc người nhận.

## Hồ sơ bàn giao và quyết định

- [Tóm tắt đưa vào báo cáo thực tập](d4-internship-project-summary.md)
- [Kịch bản evidence-only 5–10 phút](demo-script.md): không login/upload/call AWS mới
- [Worksheet sơ đồ tự vẽ](architecture-self-draw.md), [D1 review](d1-handover-review.md), [C0 plan](cleanup-c0-inventory-and-acceptance.md)
- Workshop VI/EN: sibling repo `content/5-Workshop/5.7-PolicyAssistant/`; lab S3/VPC 5.1–5.6 là nội dung khác, không phải dependency mới của sản phẩm.

| Hành động | Quyết định D4 |
|---|---|
| Trình duyệt local commit có chọn lọc, cả hai repo | **GO chuẩn bị/đề nghị duyệt**, chưa stage/commit; fresh selection scan bắt buộc |
| App public push | **NO-GO** security containment/history gates |
| Worklog push/Pages | **NO-GO** publication approval và review còn thiếu |
| AWS cleanup/delete | **NO-GO** chưa có Approval C |
| Production | **NO-GO** |

Bước tiếp theo: chủ dự án hoàn tất xác nhận D3-A2; không cần chạy lại B4/B5-R7 để trả lời câu hỏi vận hành. Giữ nguyên mọi evidence lỗi/thành công. Dừng sau D4, không chuyển sang thao tác ghi AWS hoặc Git.
