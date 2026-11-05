# Policy Assistant

A public, self-service AWS application for private PDF libraries, multilingual semantic retrieval, source-cited AI answers, conversation history, and administration of shared policies. The interface is in Vietnamese. Runtime: Python 3.12; deployment: AWS SAM; browser authentication: Cognito authorization code + PKCE.

Published application: [Policy Assistant](https://djreo5eptvwk5.cloudfront.net/). Deployment and acceptance evidence: [verification report](docs/final-verification.md). The owner has confirmed registration and administrator access; the SNS subscription was confirmed.

Current handover: [feature inventory](docs/FEATURE-STATUS.md), [support guide](docs/HUONG-DAN-HO-TRO.md) and [current quality extension verification](docs/quality-release-verification.md). Support is consented and in-app; administrators cannot access private customer PDFs. AI questions can use shared policies, selected PDFs or both.

Policy validity: inclusive Vietnam business dates, administrator filters and final cited-source revalidation prevent scheduled/expired/changed policy snapshots from being saved as current answers. [Operator guide and reproducible demo](docs/HUONG-DAN-HIEU-LUC-CHINH-SACH.md). No scheduler or additional AWS service is required.

- Practical support triage: customer category/order reference, staff-only priority, combined exact filters, revision checks and monthly usage. References are unverified input; no automatic refund/order integration.

- Shop contact configuration: separate administrator drafts, explicit publication/withdrawal, customer contact page and revision/audit protection. [Operator guide](docs/HUONG-DAN-CAU-HINH-SHOP.md).

V1 handover and operating boundaries: [RELEASE-V1.md](docs/RELEASE-V1.md). Administrator tabs: overview, policies, support, shop information, quality and audit.

New quality extension: structured private feedback, aggregate-only quality dashboard and JSON report. [FCAJ readiness and actual worklog handoff](docs/fcaj/READINESS.md).

The separate internship worklog now has a dated bilingual primary-release guide, demo plan, cost inputs and sanitized evidence. [Local synchronization and build verification](docs/fcaj/WORKLOG-VERIFICATION.md). These updates preserve historical results and do not establish personal attendance, published blogs or FCAJ eligibility.

## Functional scope

- Cognito self-registration, email confirmation, sign-in, password recovery and sign-out through hosted login. The frontend never asks users to paste JWTs.
- Owner-scoped document upload, pagination, renaming, processing status, download and permanent deletion of all source/extraction versions.
- PDF text extraction, with asynchronous Textract OCR for scanned PDFs. Limits: 10 MiB, 100 text pages or 10 scanned pages per file; encrypted and malformed PDFs fail explicitly.
- Multilingual semantic retrieval using Cohere Embed Multilingual v3; compact int8 vectors live in S3, avoiding an always-running vector database. Selected document IDs are re-authorized before content is read.
- Nova 2 Lite (Japan profile, low reasoning) answers only from retrieved excerpts, returning server-validated source IDs, document/page references and excerpts. Unsupported questions can return insufficient evidence. AI answers still require human verification.
- Owner-scoped history with 30-day expiry, per-entry deletion and JSON export.
- Confirmed account deletion blocks access first, purges private object versions/history/support requests, then removes the Cognito identity asynchronously.
- An `administrators` Cognito group controls shared-policy publication/deletion and a transactionally recorded audit log. The admin UI does not expose customer PDF contents.
- PDF parsing runs in an isolated Lambda with logging-only IAM permissions; it receives a short-lived URL to the current input and returns a validated bounded text result.
- Durable processing: a DynamoDB stream dispatches persisted work to SQS; duplicate delivery is safe; worker failures retry; scheduled recovery repairs stalled work; dead-letter and HTTP 5xx alarms are configured.
- Private S3 origins, CloudFront HTTPS hosting, content security headers, versioned documents, DynamoDB recovery, bounded log retention, usage quotas and a monthly AWS budget notification.

The deployed generation profile is `jp.amazon.nova-2-lite-v1:0` with low reasoning. Its Japan destinations may process retrieved excerpts in Tokyo/Osaka. Cohere embedding and Textract calls use Singapore. See the published privacy notice before uploading sensitive material.

## Budget and limits

The requested operating budget is USD 30–50/month. Defaults intentionally target a small public launch:

| Operation | Per account | Whole application |
|---|---|---|
| Support request creation | 5/day | 200/month |
| PDF upload attempts | 5/day | 300/month |
| AI question attempts | 20/day | 2,000/month |
| Authenticated application requests | 1,000/day | 100,000/month |
| Public registration attempts | — | 100/month, 1,000 lifetime |

Reservations are atomic. Retries and failed attempts may consume a reservation. Daily/monthly periods use UTC; signup lifetime counters do not expire. These limits are starting settings, not paid subscription tiers. Administrators can inspect monthly totals; changing limits is an operator deployment decision.

AWS Budgets notifications fire at 50%, 80% and 100% of USD 50. The budget covers the AWS account, not only this stack. SNS email subscriptions require confirmation. Alerts are not an automatic billing cap: traffic, stored data, other account resources, tax and regional pricing can still affect the bill. Consult [AWS Bedrock pricing](https://aws.amazon.com/bedrock/pricing/), [Textract pricing](https://aws.amazon.com/textract/pricing/) and [Cognito pricing](https://aws.amazon.com/cognito/pricing/).

## Development and verification

For a clean source review ZIP and Windows Python3.12/SAM setup, see [source handover and local reproduction](docs/reproducibility/README.md). The export excludes actual frontend configuration, authentication artifacts, generated dependencies and Git history.

```powershell
python -m pip install -r policy_assistant/requirements.txt -r tests/requirements.txt
npm ci --prefix frontend --ignore-scripts
npm run build --prefix frontend
npm test --prefix frontend
python -m pytest tests -q
sam validate --lint --region ap-southeast-1
sam build
python -m http.server 8080 --bind 127.0.0.1 --directory frontend/dist
```

Use Python 3.12 for the Lambda-runtime test pass. Tests use mocked AWS services; deployed integration tests skip unless `AWS_SAM_STACK_NAME` is explicitly set. Protected policy tests also require `POLICY_ASSISTANT_ID_TOKEN` to be set privately. Data-specific read-only tests use explicit `POLICY_ASSISTANT_TEST_POLICY_ID` and `POLICY_ASSISTANT_TEST_KEYWORD`; production does not auto-publish demo samples. Run `scripts/smoke_live.py --ocr` for disposable full acceptance. A skipped live test is not deployment evidence.

The compiled frontend reads public configuration from `config.json`; `frontend/config.example.json` is deliberately unconfigured. An unconfigured preview shows a connection notice and disables sign-in. Real authentication requires a deployed user pool and a registered callback URL. Local callback: `http://localhost:8080/`, not a nested source path.

`frontend/package-lock.json` locks browser dependencies. Fonts are self-hosted with their OFL license. The production browser has no CDN script or remote-font dependency. Tokens are held in browser session storage by oidc-client-ts and sent only to the configured API; a strict CSP and plain-text rendering reduce injection exposure. Do not add untrusted scripts to this origin.

## Update the existing AWS project

The current stack is `policy-assistant` in `ap-southeast-1`. Review `docs/production-runbook.md` before executing a release. Build before preparing a change set.

```powershell
python scripts/deploy_release.py prepare --notification-email YOUR_ALERT_EMAIL
python scripts/deploy_release.py inspect
# Execute only the reviewed immutable change set:
python scripts/deploy_release.py execute
python scripts/deploy_release.py status
```

When the existing metadata table has neither new index, preparation generates an `index-migration` phase adding only `OwnerCreatedAt`, with recovery scheduling disabled. After it completes, prepare/inspect/execute again: the `final` phase adds `StatusUpdatedAt` and enables recovery. DynamoDB permits one GSI addition per table update. Only publish the frontend after both indexes are active:

```powershell
python scripts/deploy_release.py publish
```

The release helper packages the verified build, rejects stale runtime modules, records artifact hashes and refuses removal/replacement of data-bearing tables, buckets, user pools or queues. It assumes this project's existing SAM managed artifact bucket. A fresh environment can use `sam deploy --guided`; existing fixed table names assume one copy per account/region. Do not execute a fresh stack against those names without reviewing conflicts.

The rollout does not guess owners for historical metadata. Existing objects under `uploads/` are retained; only the new `quarantine/` prefix has two-day temporary cleanup. Old metadata without a verifiable owner stays inaccessible. Legacy policy rows are hidden until an administrator explicitly publishes actual customer content. Do not present the original sample policies as real business rules.

## First administrator

Register and confirm the chosen owner email on the deployed website. Then an AWS operator runs:

```powershell
python scripts/bootstrap_admin.py --email OWNER_EMAIL
```

The helper refuses absent, disabled or unconfirmed accounts. Sign out and in again after the group grant. The public API never lets a customer grant themselves an administrative role.

## Main files

- `policy_assistant/app.py`: gateway routing and existing policy search.
- `service.py`, `pipeline.py`, `pdf_parser.py`, `assistant.py`, `embeddings.py`, `signup.py` inside `policy_assistant/`: application, processing, grounded generation, vectors, signup limits.
- `frontend/src/`: production interface and authenticated API client.
- `template.yaml`: AWS infrastructure and role permissions.
- `scripts/deploy_release.py`, `scripts/bootstrap_admin.py`: repeatable release and owner setup.
- `docs/api-contract.md`, `docs/production-runbook.md`, `docs/final-verification.md`: current behavior, operations and actual evidence.

Older internship reports and roadmaps describe historical snapshots. The current verification report is authoritative for what has actually been tested; it does not equate a local test pass with successful public operation.

Canonical working repository: `C:\Users\accli\Documents\Project\policy-assistant`. See [working location](docs/WORKING-LOCATION.md) and [latest retail verification and limitations](docs/retail-pilot-verification.md). Vietnamese usage guide: [Hướng dẫn vận hành](docs/HUONG-DAN-VAN-HANH.md).

Administrator workflow: [Vietnamese guide](docs/HUONG-DAN-QUAN-TRI.md), [current release evidence](docs/admin-verification.md). Drafts are separate from published policies; publication is explicit, archive is reversible, and revision checks prevent stale writes. Production frontend builds use fingerprinted assets to keep previous HTML compatible during deployment.
