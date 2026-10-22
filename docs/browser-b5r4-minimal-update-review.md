# B5-R4 — minimal Lambda update strategy

**GO chuẩn bị local phương án B; NO-GO AWS writes/execute.** Candidate B5-R2 không bị thay thế. AWS Browser B5 vẫn FAIL, fix chưa deploy/rerun.

## Phạm vi thực sự của presigner

`policy_assistant/app.py` chỉ import standard library, boto3/botocore; không có dynamic import/eval/exec hoặc presigner hook khi import. Module initialization tạo DynamoDB resource/table handles, không tạo URL. Call graph AST direct-name được đối chiếu source và handler dispatch:

| Handler | S3 operations reachable | Cần fix để browser hoạt động? |
|---|---|---|
| lambda_handler | _document_upload_session→_s3().generate_presigned_post; _document_download→_s3().generate_presigned_url; submit→head_object | **Có: PolicyAssistantFunction** |
| worker_handler | _process_document_record→_s3().get_object với VersionId | Không tạo presigned URL; không cần code mới cho lỗi browser |
| recovery_handler | DynamoDB query/update; SQS send_message | Không dùng _s3 hoặc presigner; không cần code mới |

Worker dùng chung helper nhưng default SDK client cũ đã đọc object qua SDK trong B4. Giữ worker cũ không loại bỏ validation/version/hash/ownership/retry/partial-failure logic. Không suy ra worker “không dùng S3”. Recovery không cần cập nhật. Các handler cùng app.py và dependencies là lựa chọn packaging, không phải yêu cầu cùng version triển khai đồng thời.

Bản API mới chỉ thêm `s3={"addressing_style":"virtual"}`; không đổi metadata schema, SQS body doc_id/submission_id, version binding hoặc response schema. Mỗi Lambda chạy package/process riêng nên cùng module name không yêu cầu cùng ZIP. API mới vẫn tạo dữ liệu theo contract cũ; mixed-artifact test xác nhận bằng moto, không thay thế AWS E2E.

## Phương án A/B/C

| Tiêu chí | A: shared artifact, set hiện có | B: API-only CodeUri — khuyến nghị | C: tách presigner helper riêng nhưng vẫn update shared artifact |
|---|---|---|---|
| Source/template | Không đổi thêm;3 CodeUri mới | Không cần sửa runtime nữa; local proposal từ deployed Original chỉ đổi API CodeUri; Worker/Recovery giữ nguyên toàn resource | Refactor helper và2 signer call sites; chưa thực hiện |
| Artifact | ZIP B5-R2 đã upload | Có thể **dùng lại chính ZIP đã xác minh B5-R2**, không cần ZIP/upload mới nếu hash/config vẫn đúng | Cần ZIP mới và kiểm thử thêm; không làm trong R4 |
| Actual/predicted plan | Actual default6Modify, detailed3Code | Chỉ1 direct CodeUri diff được chứng minh local; actual AWS plan **UNKNOWN** | Vẫn3 CodeUri nếu shared packaging; không chứng minh giảm dependency |
| Dynamic chain | API Body; Recovery→Rule→Permission Conditional đã quan sát | Recovery không đổi nên dự kiến giảm chain đó; API Body dynamic vẫn có thể xuất hiện; không bảo đảm hết Conditional/other changes | Cùng reference graph như A, có thể vẫn6entries |
| Runtime risk | API/worker/recovery code rollout, permission recreation chưa loại trừ | Chỉ API code rollout; API propagation vẫn cần review; old worker/recovery giữ nguyên | Worker SDK behavior giữ như cũ trong source mới nhưng3Lambda vẫn roll code; không giảm plan bằng chứng |
| Rollback |3Code refs về artifact cũ qua plan riêng; dependency risk tồn tại | API CodeUri về old artifact qua change set được duyệt riêng; API dependency vẫn cần audit | Rollback3Code như A; thêm refactor regression risk |
| Tests | Local hiện có; AWS B5 chưa pass | Mixed newAPI/oldWorker/oldRecovery và existing tests PASS local | Chưa triển khai/test phương án C; không ghi PASS |
| Cost/resources | Không thêm service; có sẵn review ZIP; update/calls vẫn có phí | Reuse ZIP => không cần thêm storage artifact; change-set/read requests có thể tính phí; không hứa0 | Có thể thêm ZIP/storage và test/update requests; không thêm service |

C là phương án source refinement có cơ sở ở helper dùng chung, nhưng không nhỏ hơn B và không giải quyết reference graph. Không chọn pin ARN cứng, xóa permission, nới CSP/CORS/IAM, tách stack hoặc direct Lambda update để né change set.

## Thử nghiệm B local — không sửa candidate hiện có

Trong thư mục Gitignored `.aws-sam/test-review/b5r4-local/`:

- `api-only-original.json`: clone Original deployed đọc trực tiếp AWS; chỉ API CodeUri trỏ **object B5-R2 đã tồn tại**. Không upload template này.
- Worker/Recovery toàn resource bằng deployed Original, gồm CodeUri. Không dùng output `sam package` mặc định vì có thể đổi cả ba functions do cùng local CodeUri.
- SHA256 old ZIP cho Worker/Recovery: `8ef709aa27ab22094b83071591f9cce1b546f78aebc3b5fd00b1ec257ab6d591`.
- SHA256 API ZIP: `7c0228312d950a082c8efdd9ac0caeb8ba6a51c31b32d47c782e42ecea934bcd`.
- Cả hai ZIP local2.199members, chỉ app.py khác; dependency member hashes bằng nhau. Old URI lấy từ deployed template, không đoán key; old bytes là cache đã kiểm AWS ở B5-R, không bịa fresh S3 hash R4.
- SAM validate --lint PASS. SAM build packaged template PASS và giữ nguyên3 S3 CodeUris. **SAM bỏ build cả ba functions vì remote CodeUri**: không ghi nhận đây là fresh dependency rebuild. Source build đã có bằng chứng B5-R; R4 chỉ xác minh package/template và byte fingerprints.

Runtime source, template.yaml chuẩn, frontend và candidate B5-R2 không bị thay đổi. Không commit/push.

## Local tests R4

| Kiểm tra | Kết quả / phạm vi |
|---|---|
| pytest tests/unit + private mixed-artifact test |130 PASS =129existing +1mixed |
| npm test |17PASS |
| npm run test:browser |3PASS, fixtures offline |
| npm run test:local |1PASS, simulated AWS |
| SAM validate --lint temporary template |PASS |
| SAM build temporary packaged template |PASS; remote CodeUri functions skipped |
| ZIP hashes/dependency members/CodeUri preservation |PASS |
| AWS B4/B5 rerun |NOT_RUN |

Mixed test dùng moto và source app.py lấy từ old deployed ZIP, không tài nguyên thật: API mới tạo session/submit, old Recovery nhận pending metadata/enqueue, old Worker xử lý version/hash, API mới status/download200 và user khác404; old worker malformed-message trả partial failure. Test chạy với signing credentials giả chỉ trong child process, không đổi credentials/profile AWS thật. Không lưu/log signed URLs.

Lệnh test đầy đủ và test fixture nằm trong thư mục local riêng; evidence public lưu counts/hashes/call graph. Không sửa các tests chuẩn để cưỡng ép PASS. Lint/typecheck của unchanged runtime đã PASS B5-R; không chạy lại chúng trong R4 hoặc ghi thành fresh run.

## CloudFormation: điều đã chứng minh và điều chưa biết

Read-only R4 xác minh STS đúng account …0098, region ap-southeast-1, test stack CREATE_COMPLETE; existing set vẫn CREATE_COMPLETE/AVAILABLE. Original deployed dùng làm baseline proposal. Chi tiết sáu entries/default vs3detailed và live bindings ở [B5-R3](browser-b5r3-impact-audit.md); không nhận là đã fresh-read toàn bộ configs đó trong R4.

1. **Template proven**: current A processed chỉ3Code.S3Key diff; B local Original chỉ1API CodeUri diff. Không IAM/CSP/CORS/schema/event declarations diff.
2. **Dynamic inference**: API Body tham chiếu Function.Arn; Rule Targets tham chiếu Recovery.Arn; Permission SourceArn tham chiếu Rule.Arn. Default plan bảo thủ khi giá trị intrinsic phụ thuộc tài nguyên được update. A báo Dynamic ResourceAttribute; SourceArn RequiresRecreation Always nên Conditional.
3. **Runtime UNKNOWN**: provider có thực sự reapply/recreate, invocation gap, rollback thành công hoặc API propagation continuity. No interruption/False không bảo đảm mọi request thành công. Enhanced visibility resolve available refs giúp đánh giá chính xác hơn nhưng không phải bằng chứng zero replacement risk.

Không nhầm `Evaluation: Dynamic` với cú pháp Secrets Manager/SSM dynamic references; đây là intrinsic resource references trong Details.

## Bước tiếp theo cần phê duyệt riêng

**GO để trình duyệt chuẩn bị candidate B**, không GO execute. Đề xuất phê duyệt tương lai chỉ cho tạo **một UPDATE change set mới chưa execute** từ proposal API-only, **không upload mới nếu artifact cũ/mới vẫn xác minh đúng**. Trước write phải refresh STS/stack, candidate/templates, artifact SHA thực tế của API và old Worker/Recovery, source/build, parameters/tags và old-stack isolation.

Plan mới chỉ chấp nhận direct Code update API. Mọi dependency entries phải liệt kê/audit; nếu Conditional/True replacement hoặc tài nguyên ngoài scope, NO-GO và dừng. Không hứa trước plan chỉ1/2/3entries. Không xóa/obsolete candidate cũ trong R4; nếu việc tạo set tương lai có ảnh hưởng lifecycle các set hiện hữu, phải nêu trong approval và kiểm chứng.

Execute, browser rerun và cleanup là ba phạm vi phê duyệt riêng sau đó. Giữ old ZIP/template cho rollback qua CloudFormation, không direct update. Chưa execute nên không có runtime rollback để làm. Dữ liệu B4, orphan metadata B5, DLQ message, users và4Retain resources giữ nguyên.

## Sources và evidence

- [ResourceChange replacement semantics](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ResourceChange.html).
- [Dynamic evaluation và ChangeSource](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ResourceChangeDetail.html).
- [Enhanced visibility resolves known references](https://aws.amazon.com/about-aws/whats-new/2024/04/aws-cloudformation-changesets-enhanced-change-visibility-deployments/).

Nguồn chính thức kiểm tra ngày22/10/2026 UTC+7. [Evidence R4](evidence/b5r4-strategy.json) ghi thời điểm AWS/local verification, call graph, scope/tests/hashes và limitations.

**AWS WRITES:0. NEW CHANGE SET:NOT_CREATED. DEPLOYMENT:NOT_EXECUTED. AWS E2E:NOT_RUN. DỪNG chờ phê duyệt riêng.**
