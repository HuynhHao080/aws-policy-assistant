> D1 current state22/10/2026: AWS B4 19PASS, original B5FAIL, R7 10PASS; C0 GO bounded demo/NO-GO production. DLQ1/ALARM, SNS0subscriptions, Budget delivery unverified; end date not set. D1 authorizes no AWS actions. samconfig defaults to OLD stack; generic package/deploy can update3shared CodeUris, not the approved API-only path. See [D1 handover](d1-handover-review.md). Runbook commands below require separate scope/account/plan approval.

# Operations and deployment â€” complete MVP v1

## Boundaries

Offline acceptance is reproducible with `python -m scripts.verify`. It deliberately removes live-test opt-in variables for child processes. The demo binds only 127.0.0.1, uses moto and fake identities, and discards data on shutdown. It is never a public deployment or a substitute for Cognito validation.

Current changes are local and uncommitted. Deploy/push, account changes and real failure injection still require the user's explicit authorization. Previously committed demo passwords must be rotated by the account owner; current source changes do not revoke them.

## Run a complete local demonstration

From the application checkout:

```powershell
.venv/Scripts/python.exe -m scripts.demo_server
```

For a fresh Windows checkout, `pwsh -File scripts/start-demo.ps1` prepares missing dependencies (requires uv or an existing Python 3.12 virtual environment). Open the printed loopback URL. Sign in as `alice@demo.local` without a password; look up POL-001; upload a synthetic PDF; wait for verification/download; refresh the personal library. Sign out and use `bob@demo.local` to prove Alice's document ID returns 404. No AWS credentials or charges are required.

## AWS change review

Review `template.yaml` before creating/executing a change set. It provisions private document/hosting buckets, CloudFront with OAC/HTTPS/security headers, HTTP API, Cognito, two DynamoDB tables, API/worker/recovery functions, SQS/DLQ, a two-minute recovery schedule, SNS topic and alarms. Email subscriptions are created only if the authorized deployer supplies `AlertEmail`; the recipient must confirm the subscription. No notification has been sent by this development iteration.

### Legacy DynamoDB upgrade: two index steps

AWS permits only one GSI creation per update on an existing DynamoDB table. If the existing document table has neither index, the authorized upgrade must first deploy with `EnableOwnerIndex=false` to create `ByStatus`, wait for the index to become ACTIVE, and then deploy with `EnableOwnerIndex=true` to create `ByOwner`. Document listing is unavailable during the first transitional phase. Fresh table creation can use the default true. **Do not switch an existing ByOwner index off**: the false setting is only for the first upgrade from the no-index schema. Review each change set for unintended deletions/replacements; preserve existing tables/buckets and never auto-assign owners to legacy records.

## After an authorized deployment

1. Inspect stack outputs and resource/index readiness. Rotate exposed credentials before authenticating. Prepare two demo users using Cognito's administrative onboarding; handle required new passwords in the UI. No user creation was performed here.
2. Export only public frontend settings: `python -m scripts.export_frontend_config --stack policy-assistant --region ap-southeast-1`. This is a read-only AWS call and writes API URL/client ID/region, not credentials.
3. Upload the four frontend files (`index.html`, `app.js`, `styles.css`, `config.json`) to the `FrontendBucketName` output and invalidate the CloudFront cache. Do this only with upload/publish authorization. Do not sync the repository root or include tokens, session files, logs or credentials.
4. Open `FrontendUrl`. Verify native Cognito login, initial password challenge, logout, expiry/refresh and protected routes. The app client must be public (no client secret); current template allows USER_PASSWORD_AUTH and REFRESH_TOKEN_AUTH.
5. Verify PDF POST/GET CORS from localhost and the CloudFront URL, two-user API/list isolation, version-specific hashes, duplicate delivery, terminal failures and a controlled recovery/DLQ scenario. Record commit, date and environment in sanitized evidence.
6. Confirm the optional SNS recipient subscription and alarm delivery. Review usage/cost inputs before turning this into a shared service.

AWS references: [GSI updates](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-dynamodb-table.html), [Cognito InitiateAuth](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_InitiateAuth.html), [SQS/Lambda](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-configure.html).

## State and failure handling

| State | Meaning | User action |
|---|---|---|
| uploading | Owned session exists; not submitted | Upload and submit before URL expiry; otherwise create a new session |
| pending | Frozen S3 version awaits verification | Wait/refresh; safe to re-submit the same ID |
| processed | Exact version passed byte checks and has SHA-256 | Download; browser verifies the received bytes |
| failed / INVALID_PDF | Header/size verification failed | Upload a new valid PDF; retry cannot change the frozen version |
| failed / PROCESSING_FAILED | Third delivery failed transient processing | Inspect service health; owner may retry the same version as a new attempt |

The scheduled recovery function queries at most 20 due pending records each run, resends the same attempt and advances its deadline by two minutes. This repairs a crash between metadata update and queue send. Stale GSI records/messages are harmless: worker checks the current attempt ID and state. Recovery remains eventually consistent and bounded; sustained overload or an unavailable database requires operator action.

## DLQ and retries

Do not purge the DLQ automatically. Inspect sanitized failure logs, verify affected document/attempt IDs, fix the service issue, then choose an authorized owner retry or controlled redrive. Retrying creates a new attempt ID; older messages cannot change the newer attempt. Permanent invalid PDF input becomes failed without wasting transient retries. A metadata outage can prevent terminal-state recording, so do not rely only on the UI; inspect queue-age, DLQ and recovery-error alarms.

## Limits

PDF verification checks bytes/header/size, not full parsing, malware, OCR or policy extraction. There is no AI/RAG. Signed POST constrains key, MIME and size at S3; hosting/API/S3/IAM/Cognito must still pass live acceptance. Search uses bounded Scan and is not a stable snapshot during concurrent changes. S3 current expiry is 365 days and noncurrent expiry is another 365 days after becoming noncurrent; versioned data can remain roughly 730 days. MFA challenges are supported by the frontend but the current pool defaults to MFA OFF. Production self-registration/password reset flows are outside this administrator-provisioned MVP; do not represent them as implemented.

Partial batch failures do not necessarily increment Lambda `Errors`. Use the SQS backlog/age/DLQ widgets and alarms plus sanitized `Worker record failed` logs. The dashboard separates average duration from counters; there are no custom billed metrics. Live alarm notification delivery is still unverified.

## Handover package

`python -m scripts.build_release` creates source/static-frontend ZIPs and a SHA-256 manifest in `dist/handover/`. It never accesses AWS. Runtime/session files and ignored directories are excluded by an explicit allowlist. Export public production configuration only after reviewing the target stack. This package does not include Git history, and does not imply old credentials have been revoked.


## Hardened test preparation, 2026-10-21

All three roles are explicit, with three separate exact-group log policies and no managed logging/SQS wildcard grants. CloudFormation precreates groups; wait for CREATE_COMPLETE and policy/group readiness before acceptance. DLQ allows only its same-stack source queue by deterministic ARN. Retain covers both document bucket and HTTPS policy, as well as both tables; never remove that policy first during approved cleanup. The new candidate replaces the prior 42-resource review with 45 Adds and no existing-stack update. Budget is a separate uncreated proposal; see aws-test-deployment-approval.md, budget-test-proposal.md and cleanup-retained-data.md for current source/evidence and gates.
