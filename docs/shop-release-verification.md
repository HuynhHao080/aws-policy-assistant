# Primary shop profile release — 2026-11-04

User explicitly selected https://djreo5eptvwk5.cloudfront.net/ (`policy-assistant`) as primary. The Zed site (`policy-assistant-fcaj-test`) was not modified. Canonical source remains `C:\Users\accli\Documents\Project\policy-assistant`.

## Delivered

Administrators configure shop name, email/phone, support hours, return reception instructions and a customer message without redeployment. Separate drafts, explicit confirmation/publish, withdrawal, discard and conditional revisions protect the customer snapshot. Customers see published contact fields only, behind normal JWT authorization. The saved mode is demo/live; live publication requires complete contact information, not just a label toggle. Shared contacts are not AI source policies, do not approve DEMO policies and do not provide order/payment integration.

No owner email or fictional shop identity was prefilled or published. The customer page/banner clearly handles an unconfigured shop. Failure to load optional shop information does not prevent the rest of the application starting. New UI retains the Vietnamese Noto fonts.

## Release and actual checks

- Change set: `public-final-1793782175`.
- Lambda zip SHA256: `6c70b4b5b5281d16931e1f54ffdd94ae9881eaeb25517b44ccc658d6eedfb101`.
- Template SHA256: `65ad846dc07f66f366cd01ac39dc7d934ca310391c455e2b8bb5c721552ee066`.
- Final full Python3.12 run: **231 passed, 11 opt-in live skipped**. Frontend: **33 passed**; latest production build and entry/legal-page fingerprint check passed.
- SAM validation/lint and cached build succeeded. Source comparison shows only six immutable artifact keys and three route definitions added. Existing execution IAM grants, model/budget/quota parameters, identity and data resources unchanged; SAM adds three API-to-Lambda invoke permissions. The initial candidate lacked explicit route authorizers and was stopped by review before execution; the corrected candidate was deployed. An infrastructure regression now requires the JWT authorizer on each route.
- **14 live metadata/API checks passed**. Actual API Gateway route metadata confirms JWT on all three routes. A disposable customer cannot read/edit drafts; a temporary test administrator can save/discard a nonce-guarded private draft. Malformed contacts, stale revisions, missing confirmation and incomplete live publication are rejected. Customer-visible snapshot remained unchanged throughout. Metadata-only audit was confirmed.
- The synthetic draft was discarded and the disposable identity removed through the application account deletion workflow. Only revision/audit metadata remains as intended; audit retention is90days. No fake public contact information, owner account/PDF/policy changes, AI/model invocation, PDF upload or email sending occurred. See [live report](shop-live-acceptance.json).
- Publication hashes, six Lambda code hashes and CloudFront invalidation are recorded in [artifact verification](shop-artifact-verification.json). See [template review](shop-template-review.json).

## Boundaries

Full successful publish/unpublish behavior was exercised offline; live testing intentionally verified rejected publication and private draft cleanup instead of publishing fictional business information. Browser-origin permission was declined earlier and not retried, so no new browser/visual acceptance is claimed. Earlier PDF/AI/OCR/triage reports are historical evidence, not model acceptance rerun for this release. No load/SLA, email delivery, password recovery or restore drill was newly verified.

Shared profile data uses UsageTable pk app#shop-profile without TTL and survives an administrator's individual account deletion; this is documented in the privacy notice. Contacts remain until updated/unpublished/discarded, with normal backup retention. Model processing configuration and generation guard behavior are unchanged.

Operator procedure: [Cấu hình shop](HUONG-DAN-CAU-HINH-SHOP.md). Scope/remaining business work: [Feature status](FEATURE-STATUS.md).
