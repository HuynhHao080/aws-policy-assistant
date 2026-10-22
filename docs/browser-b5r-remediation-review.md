> B5-R2 mới nhất: artifact VERIFIED; change set AVAILABLE nhưng **NO-GO**, actual6 Modify gồm một Conditional replacement. Chưa deploy. Xem [review B5-R2](browser-b5r2-deployment-approval.md). Các mục NOT_CREATED bên dưới là lịch sử B5-R.

# B5-R — diagnosis và bản sửa local

**LOCAL_FIX_VERIFIED_NOT_DEPLOYED. GO review bản sửa; NO-GO deploy/execute/rerun khi chưa duyệt riêng.**

## Bằng chứng và độ tin cậy

| Mức | Kết luận |
|---|---|
| CONFIRMED | CSP live CloudFront khớp source IaC, chỉ cho S3 regional; CORS bucket cho đúng origin test GET/POST |
| CONFIRMED | Helper cũ với SDK1.43.116 như deployed build sinh global hostname cho cả presigned POST/GET; thử bằng signing credentials giả, không gọi AWS |
| CONFIRMED | Edge local với CSP đó phát sinh securitypolicyviolation `connect-src`, blocked host `fcaj-local-fixture.s3.amazonaws.com`, UI error trước S3 request |
| CONFIRMED | Một dòng virtual addressing làm actual helper sinh regional POST/GET, browser fixture hoàn thành và hash khớp, không violation |
| LIKELY | Cùng mismatch gây B5 AWS FAIL, phù hợp session200/no S3 request/hai console errors |
| UNKNOWN | Exact violation/signed response B5 gốc không được giữ; fix chưa chạy trên AWS |

Không ghi lại B5 AWS thành PASS từ fixture local. Frontend thực tế dùng presigned **POST**, không PUT. Chỉ giữ directive/hostname, không query/signature/credential. Mock API/S3 đều được fulfill local, **0 unmocked external requests**; không tạo dữ liệu AWS.

Đọc [live configuration](evidence/b5r-live-config-readonly.json), [red trước sửa](evidence/b5r-prepatch-csp-browser.json), [green sau sửa](evidence/b5r-local-csp-browser.json). Live configuration đã STS-verify …0098/ap-southeast-1, stack test CREATE_COMPLETE; stack cũ chỉ đọc, metadata không đổi.

## So sánh và lựa chọn

| Phương án | Ưu điểm | Tradeoff |
|---|---|---|
| **Chọn: presigner virtual regional** | Một dòng, sửa POST/GET, không mở thêm CSP source; SDK tự resolve region/suffix | Cần artifact Lambda mới và AWS acceptance sau duyệt |
| Thêm exact global DocumentsBucket host vào CSP | Có thể giữ runtime cũ, không wildcard toàn S3 | Đổi IaC/CloudFront trust surface, giữ legacy endpoint/khả năng redirect; không cần khi có fix runtime nhỏ |

Cấu hình explicit endpoint_url đơn thuần đã được thử local nhưng tạo path-style host khác wildcard bucket-regional CSP. Chọn `Config(signature_version="s3v4", s3={"addressing_style": "virtual"})`, không hard-code endpoint, không thêm *.amazonaws.com hoặc *.s3.amazonaws.com. Không nới IAM, S3 public access hoặc CORS.

Nguồn: [Botocore Config](https://docs.aws.amazon.com/botocore/latest/reference/config.html) và [AWS regional virtual-hosted URLs/legacy endpoints](https://docs.aws.amazon.com/AmazonS3/latest/userguide/VirtualHosting.html). Host của SDK hiện dùng được đo local, không chỉ suy ra từ tài liệu chung.

## Các file local thay đổi trong B5-R

- `policy_assistant/app.py`: đúng một dòng logic `_s3()` thêm virtual addressing; giữ SigV4, region và credentials chain.
- `tests/unit/test_presigner_endpoints.py`: POST/GET regional host, version binding, expiry300, SigV4, MIME PDF/10MiB policy.
- `tests/frontend/csp.e2e.cjs`: Edge enforce CSP, legacy-global block, actual-helper success pipeline/hash; chỉ fixtures local.
- `package.json`: đưa CSP regression vào `test:browser` để quy trình verify/CI hiện có chạy tự động.
- Docs/evidence liên quan. **Không đổi template.yaml, frontend source, CSP/CORS/IAM/BPA**. Giữ nguyên các thay đổi của người dùng trước B5-R.

[Runtime patch incremental so với deployed code](evidence/b5r-runtime.patch), chuẩn hóa line endings để so sánh một dòng logic. Không dùng toàn bộ dirty diff từ Git HEAD làm diff B5-R.

## Tests đã chạy

Lệnh `.venv/Scripts/python.exe -m scripts.verify`:

| Kiểm tra | Kết quả |
|---|---|
| Backend unit | **129 PASS** |
| Frontend unit | **17 PASS** |
| Browser fixtures: existing +2 CSP cases | **3 PASS** |
| Full-stack local browser | **1 PASS** |
| Ruff E9/F63/F7/F82, mypy app.py, JS syntax | **PASS** |
| SAM validate --lint / SAM build | **PASS / PASS** |
| Live integration | **9 SKIPPED = NOT_RUN**, không phải AWS proof |
| B4/B5 AWS rerun sau sửa | **NOT_RUN** |

Mypy là backend typecheck; frontend plain JS không có TypeScript build. SAM build chỉ ghi local .aws-sam/build, không package/upload/deploy. Regression trước fix đỏ và sau fix xanh được giữ riêng; legacy-global vẫn bị CSP chặn đúng thiết kế.

## Build và phạm vi AWS dự kiến

Deployed processed template vẫn khớp snapshot B1; template source không đổi. Old S3 ZIP đọc lại có SHA-2568ef709aa27ab22094b83071591f9cce1b546f78aebc3b5fd00b1ec257ab6d591. Ba builds đều2.199 files; member hashes cho thấy **chỉ app.py đổi**, dependencies không đổi.

New source-pair SHA-256: `e16c8529fdc8fe2fde6d20714699a19ce5ff8af5c962fd8e68021f2e7e34fbea`.

Shared CodeUri khiến dự kiến Code của **PolicyAssistantFunction, PolicyAssistantWorker, DocumentRecovery** thay đổi khi triển khai. Đây chưa phải actual CloudFormation plan; exact Modify/Replace chỉ xác minh sau change set thật. Không đổi data/schema/pool/queue/bucket/IAM/frontend theo local diff. Không apply template vào `policy-assistant` cũ. [Build-vs-deployed evidence](evidence/b5r-build-vs-deployed.json).

## Vì sao chưa có change set

**Change set: NOT_CREATED / NOT_EXECUTED.** Local IaC không đổi. Code deployment cần ZIP mới lên S3; user B5-R cấm **“Không tạo upload sessions, S3 objects hoặc SQS messages.”** Không `sam package` hoặc upload ZIP; cũng không tạo change set trỏ ZIP cũ/key chưa tồn tại rồi coi là candidate hợp lệ.

Cần phê duyệt riêng **upload một artifact vào review prefix test và tạo change set chưa execute**, sau STS/region/stack guard. Tiếp đó review actual resource actions, replacements, IAM/parameters, ZIP/member hashes và old stack trước khi xin execute riêng. Nếu plan có dữ liệu/IAM/replacement hoặc Modify ngoài code scope dự kiến, dừng review, không tự mở rộng phê duyệt.

## Rollback, cost và dữ liệu

Giữ old artifact/package cho rollback Code qua plan được duyệt riêng; code cũ có B4 API/SDK evidence nhưng cũng có browser mismatch, không coi rollback là fix. Không migration, cleanup hoặc đổi Retain/HTTPS policy. Shared artifact bucket chỉ dùng review prefix đã duyệt; không xóa/tag cả bucket.

Không thêm dịch vụ/recurring infrastructure theo diff. Artifact storage/requests và deployment/runtime có thể tính phí; chưa có estimate/Calculator mới cho patch, không hứa chi phí0. Budget20USD không hard cap. Orphan metadata B5, dữ liệu B4/DLQ1/users/Retain giữ nguyên. Không reset alarms hoặc sửa Cognito/Budget/Billing.

## Browser rerun sau deployment — cần duyệt riêng

Refresh STS/config/code SHA/Budget, main0/DLQ baseline1. Chỉ hai B3 users/hai PDF local; tối đa3 login/3 GlobalSignOut,2 sessions/2uploads/2downloads,128KiB,80 requests và15 phút. Không poison, direct worker invoke, DLQ Receive/Delete, deploy hoặc cleanup. Không dùng lại quota B5 sau FAIL.

Runner phải thu CSP violation/error state đã lọc hostname ngay khi lỗi, không full signed URL/HAR/token logs. Kiểm chứng UI chỉ success sau processed và hash đúng, ownership hai chiều, logout thật. Credentials DPAPI vào bộ nhớ; nếu có leak, timeout hoặc sai scope, dừng và chỉ điều tra read-only, không bypass UI bằng SDK để ghi browser PASS.

## Quyết định và quyền còn thiếu

1. **GO review bản sửa local**: cơ chế lỗi CONFIRMED local, patch nhỏ, tests/build PASS, không nới security.
2. **NO-GO deploy ngay**: cần duyệt artifact upload + unexecuted change-set preparation, rồi review/duyệt execute riêng.
3. **NO-GO nghiệm thu browser hiện tại**: code fix chưa deploy, B5 AWS vẫn FAIL; cần rerun riêng sau deploy.
4. **Approval C riêng** cho orphan metadata, DLQ/users/Retain cleanup. Phiên TestA B5 chưa GlobalSignOut; không tự revoke/reset trong B5-R.

**AWS writes0; deploy NOT_EXECUTED; AWS E2E NOT_RUN; cleanup/commit/push NOT_EXECUTED. DỪNG chờ phê duyệt riêng.**

[Local checks/evidence manifest](evidence/b5r-local-remediation.json).

## Final local validation

Source/build/JSON consistency và account redaction PASS. Workshop Việt/Anh đã phân biệt local fix với AWS B5 FAIL; Hugo build PASS, ba theme deprecation warnings có sẵn;131 HTML/12.582 links/0 failures. Không publish. [Final validation](evidence/b5r-final-validation.json).
