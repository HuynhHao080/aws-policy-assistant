# D3-A — containment preflight, chưa thực thi

D3-A1 read-only follow-up: [operational dependency assessment](d3a1-operational-dependency-assessment.md). Historical exact-identity authentication requests were found; current operational need remains UNKNOWN. **BLOCKED_PENDING_OWNER_OPERATIONAL_CONFIRMATION remains in effect; no containment calls executed.**

**BLOCKED_PENDING_OWNER_OPERATIONAL_CONFIRMATION. AWS writes0.**

Preflight UTC 2026-10-22T08:07:17.277263+00:00 → 2026-10-22T08:07:21.619867+00:00, account …0098, ap-southeast-1. Exact pool ap-southeast-1_zzeu6TjQs thuộc legacy policy-assistant. Source username từ commit80c4eef khớp cả4scripts; AdminGetUser theo username rồi reverse lookup bằng sub trả cùng canonical user/sub. Không in username/sub/PII/password; binding hashes chỉ lưu Gitignored local, không phải password hashes. Không dùng/test old password.

Identity alias EXPOSED_LEGACY_IDENTITY_1 Enabled=true/UserStatus CONFIRMED. Creation/modified metadata khớp D2. Test pool/client khác;2test users Enabled/CONFIRMED được lưu baseline metadata/hash để đối chiếu nếu sau này được execute. Hai stack UPDATE_COMPLETE, không operation đang chạy.

IAM SimulatePrincipalPolicy trả allowed, không MissingContextValues cho cognito-idp:AdminDisableUser và cognito-idp:AdminUserGlobalSignOut trên đúng pool ARN. Không sửa IAM. Simulation không bảo đảm mọi runtime SCP/session/condition; vẫn phải dừng nếu service từ chối.

## Điều kiện chưa đạt

Preflight điều5 của user yêu cầu xác minh disable không ngắt luồng vận hành còn được chủ dự án yêu cầu. Hiện **chưa có xác nhận này**. D3-A là conditional approval nên không tự suy diễn “không còn dùng” chỉ từ user Enabled hoặc sự khác nhau giữa legacy/test pools.

Đã gửi câu hỏi riêng cho chủ dự án, không yêu cầu username/password. Chỉ khi owner xác nhận không còn required workflow và chấp nhận ngắt phiên thì mới được tiếp tục. Nếu identity vẫn cần hoạt động hoặc chưa rõ, giữ BLOCKED và không disable/sign-out. Nếu trả lời tới sau, refresh relevant preflight trước write, không coi elapsed time là đồng ý.

## Trạng thái thao tác

| Mục | Kết quả |
|---|---|
| Account/pool/source username/sub guard |PASS |
| Enabled/CONFIRMED và test isolation |PASS |
| IAM two-action simulation |PASS với giới hạn nêu trên |
| Required-workflow/owner-impact confirmation |PENDING |
| AdminDisableUser |NOT_EXECUTED |
| AdminUserGlobalSignOut |NOT_EXECUTED |
| Postflight Enabled=false |NOT_RUN; before=true |
| CloudTrail write event IDs |NOT_APPLICABLE_NO_WRITE |
| Authentication/password change |NOT_RUN / NOT_EXECUTED |

Nếu tiếp tục sau confirmation, chỉ1disable rồi1admin-global-sign-out, SDKretryoff, lưu attempt trước call; uncertain/failure phải read-only kiểm tra rồi dừng, không repeat hoặc tự D3-B. Postflight kiểm Enabled=false, kết quả sign-out,2testusers unchanged,2stack metadata unchanged, CloudTrail IDs nếu có và độ trễ/coverage thực tế. Không tuyên bố mọi offline JWT hết hiệu lực hoặc loại trừ unauthorized access.

**NO-GO execution tại thời điểm snapshot này** vì còn condition5; không phải lỗi AWS/quyền hoặc sai identity. D3-B/history writes vẫn cần approval riêng. COMMIT/PUSH/REWRITE/CLEANUP/DEPLOY NOT_EXECUTED.

[Filtered preflight evidence](evidence/d3a-preflight.json). Hồ sơ này là snapshot pending, không phải kết quả containment thành công.
