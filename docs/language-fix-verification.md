# Vietnamese response regression verification — 2026-10-30

Problem: a Vietnamese question about the DEMO warranty-shipping fee produced a supported English answer. The previous prompt only asked for the user language, leaving the default implicit.

Change: only the generation system instructions changed. Vietnamese with diacritics is now explicit as the default, including when source text is English. Another language requires an explicit user request. The model must address the customer directly and must not claim to execute a handoff, cancellation or refund. Citation validation and no-evidence refusal behavior remain in place.

Validation: 150 offline tests passed on Python 3.12, 11 opt-in integration tests skipped; SAM build succeeded. Four real AWS retrieval/model cases passed. The probe used an isolated internal owner, in-memory history and no customer quota writes. It was not a browser or customer-session test.

- warranty_shipping_1: PASS. Chính sách chưa quy định nội dung về ai chịu phí gửi hàng đi bảo hành. Bạn cần liên hệ nhân viên để được xác nhận.

- warranty_shipping_2: PASS. Chính sách chưa quy định nội dung về ai chịu phí gửi hàng đi bảo hành. Bạn cần liên hệ nhân viên để được xác nhận.

- phone_case_unknown: PASS. Chính sách chưa quy định nội dung bảo hành cho ốp điện thoại. Bạn cần liên hệ nhân viên để được xác nhận.

- charger_duration: PASS. Theo chính sách DEMO — Bảo hành phụ kiện, củ sạc được bảo hành 12 tháng tính từ ngày nhận hàng. Tuy nhiên, đây là dữ liệu hư cấu, chỉ dùng để kiểm thử và không áp dụng cho giao dịch thực tế. Bạn cần liên hệ nhân viên để được xác nhận thông tin chính xác.

Deployment: UPDATE_COMPLETE; API function Active / Successful; deployed CodeSha256 matches the reviewed artifact.

Change set: `public-final-1793331454`.

Lambda zip SHA-256: `e7ab4b0584e8e98075d49b19d9e99b88dfef18caf22b3b9342da1f24c6fd1c19`.

Template SHA-256: `678282aa6c2a24ecea9bb8ff24546a03e124088a3ae67c28147cb499db450c35`.

Only six shared application-artifact keys changed in the original template; configuration and IAM statements matched. Existing history is preserved, so prior English answers remain historical entries. Ask again to obtain a new response.

This is evidence for the reported language regression and these test cases, not a guarantee that all future model outputs are error-free.
