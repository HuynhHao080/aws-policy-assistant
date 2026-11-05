# Practical support release — 2026-11-04

Target: existing single-shop `policy-assistant` stack, Singapore, account629380420098. Canonical source: `C:\Users\accli\Documents\Project\policy-assistant`. No new application, stack or database was created.

## Delivered behavior

Customers explicitly share a support category, optional unverified order reference, subject and message. Staff filter by status/category/priority/exact order reference and update priority with the loaded revision. Customer priority/metadata changes are rejected server-side. Staff changes retain atomic metadata-only audit and expiry, without exposing private PDFs/history or copying order references into audit logs. Legacy requests retain general/normal defaults. UI handoff clears any previous order reference/consent before prefilling a new question.

Daily support limits come from the profile API; monthly support/request usage is shown in administration. The privacy notice explains the shared fields and actual Japan model route. A read-only operational script supports AWS CLI transport and checks admin role, alarm state, queues and TTL/PITR without reading customer messages/PDFs.

## Evidence

- Python3.12: **218 passed, 11 opt-in live tests skipped**. Frontend: **28 passed**, build succeeded.
- SAM lint/validation and cached build succeeded. Source-template comparison: exactly six immutable CodeUri S3 keys changed; IAM, model/quota parameters, data resources and routes unchanged. See [template review](triage-template-review.json).
- Release `public-final-1793779926`; Lambda zip SHA256 `50394b37921b811819965f3998f8727184998999bedd0c6ee8aece11b86d978b`; template SHA256 `2e52257c5009a3d43691ae0ccd4e8e266eaefe89b3251a82115998551f928eb6`.
- **29 deployed API/support/account-cleanup checks passed** using two disposable identities and synthetic messages/order reference. Both identities and support partitions were cleaned. No PDF upload, successful AI question, model invocation, owner-account change, real-policy edit or email send was performed by this run. See [live report](triage-live-acceptance.json). `pdf_versions_purged:null` means PDF purge was not exercised in this scope.
- Fresh operational snapshot: stack UPDATE_COMPLETE, CloudFront Deployed, selected owner verified and actually in administrators group, confirmed SNS email subscription, nine alarm states OK/actions enabled, three queue snapshots empty, support TTL expires_at and PITR ENABLED. See [snapshot](operational-status-2026-11-04.json). Approximate queue counts are not a workload benchmark; confirmed subscription is not proof of delivery.
- Publication verified: all 16 production frontend files match local content bytes, six deployed Lambda hashes match this release, and CloudFront invalidation `I1JC7P9K0YP60CAG10Z4TVXLTY` is Completed. See [artifact verification](triage-artifact-verification.json).

## Review limits

Browser access to the isolated localhost fixture was declined this turn; it was stopped without another surface/proxy. UI syntax, client behavior, production asset references, unique form IDs and label targets passed automated checks, but no new browser interaction or visual acceptance is claimed. Earlier local screenshots are historical. Earlier PDF/AI/OCR tests remain evidence of their recorded release, not new model acceptance for this release. No load benchmark, real recovery-email delivery, alert delivery test or restore drill was performed.

Policies remain fictional DEMO until the operator approves real business terms/contact details. This is a small single-shop policy assistant/support portal, not a payment, order-fulfilment or multi-tenant system.

User/staff procedure: [Hỗ trợ khách hàng](HUONG-DAN-HO-TRO.md). Full scope/remaining business gates: [Feature status](FEATURE-STATUS.md).
