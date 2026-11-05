# Working location

Canonical source: C:\Users\accli\Documents\Project\policy-assistant

All future application edits, builds and deployments are performed from this project. docs/policy-drafts contains draft policies; docs/retail-pilot contains fictional shop fixtures, test reports and operator helpers. .deployment holds ignored build/release evidence and rollback data.

The former policy-assistant-completion directory was a temporary verification copy. It is not a second hosted website or a separate AWS stack. It is no longer an editing/deployment source.


Quyết định ngày 04/11/2026: bản chính là https://djreo5eptvwk5.cloudfront.net/, stack `policy-assistant`. Người dùng đã chọn rõ địa chỉ này. Bản Zed https://d3ataim7dfsl7t.cloudfront.net/ thuộc stack `policy-assistant-fcaj-test` riêng, chỉ để tham chiếu khi có yêu cầu; không tự chuyển đích triển khai sang đó.


Nguồn worklog chính do người dùng xác nhận: `C:\Users\accli\Documents\Project\aws-internship-worklog` (HuynhHao080/aws-internship-worklog). Sau đợt kiểm tra chỉ đọc ban đầu, người dùng đã cho phép chỉnh sửa cả project và worklog; các cập nhật Việt/Anh hiện đã áp dụng local. `fcj-workshop` trong ứng dụng là bộ tham chiếu cũ, không phải worklog thật.

## Three existing folders — confirmed and synchronized 05/11/2026

| Folder under `C:\Users\accli\Documents\Project` | Role |
|---|---|
| `policy-assistant` | Canonical application working source; selected deployment remains djreo5eptvwk5.cloudfront.net / stack policy-assistant |
| `policy-assistant-github` | Separate checkout of the same aws-policy-assistant GitHub repository; application source synchronized locally from the canonical folder for review/publication preparation |
| `aws-internship-worklog` | Separate internship report/workshop repository, with bilingual primary-release documentation and historical evidence |

Do application edits in the canonical folder, review/synchronize them into the GitHub checkout, and update managed worklog templates through `scripts/sync_fcaj_worklog.py`. Local synchronization does not stage, commit, push, run GitHub CI, publish Pages or deploy AWS. Git histories and existing index changes remain separate.

The 05/11 checkout sync preserved existing private/untracked evidence and local frontend configuration; target `.gitignore` retains both sets of rules. Obsolete application/test scripts were backed up outside the target before removal from active paths. Original files and a per-file manifest are in the canonical application's ignored `.deployment/checkout-sync-*` directory. Keep that backup for review/rollback. Source equality excludes deliberately merged ignore rules and environment-specific config/build outputs.
