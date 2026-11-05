# Administrator workflow verification — 2026-10-30

Source: `C:\Users\accli\Documents\Project\policy-assistant`. This follow-up updates the existing website and stack; no second project or stack was created.

## Release

Change set `public-final-1793347694` completed with UPDATE_COMPLETE. Lambda ZIP SHA-256: `b3971f78369dac2aab0675dbb7973f7abbae158a2fe8021381a19fdf9eceaed6`. Template SHA-256: `1edce0cce2308d72b097850671f80bd2001844cfb6b8d140958f81d8f3b493ad`. Existing resources were preserved. Source-template review found three additional authenticated admin routes plus immutable code references; all previous routes, IAM data-access statements, Cognito configuration, quotas, budget and model routing were unchanged. API invoke permissions were added for the new routes. The data replacement/removal guard passed.

Frontend publication completed. Content-fingerprinted JS/CSS filenames keep previous HTML compatible during rollout: old hosted bundles are retained and the entry HTML changes after assets are uploaded. S3 HEAD byte lengths and single-part ETags matched local bytes for HTML/config/JS/CSS; JS/CSS MIME types were correct. CloudFront invalidation `I9F110KZ2VUJ8H3784ZXOCWHRC` completed. Evidence: `.deployment/admin-frontend-verification.json`.

## Features

- Administrator catalogue with bounded pagination and search by ID/title/category; summaries omit content, vectors and edit tokens.
- Load an existing policy into the editor; save a separate draft while the full published snapshot remains unchanged.
- Explicit publication, reversible archive/republish and draft discard. A never-published draft cannot become a customer source by saving it.
- Opaque revision tokens and conditional policy/audit transactions reject stale edits, including a race after the initial read. Failed writes do not create a success audit record.
- Customers cannot read admin drafts; public responses strip draft/edit metadata, and retrieval projects only published source content. Strongly consistent exact-ID reads and retrieval scans reduce stale visibility after archive.
- Editor prevents publishing unsaved changes, preserves unsaved state on conflicts, clears on sign-out, ignores late responses from an old session and uses Vietnamese action labels. No permanent-delete control is presented in the new editor; the legacy API remains available to operators.

Existing published policies need no migration: an older updated-at token is accepted for their first edit, then mutations use generated revisions. The legacy PUT route still supports direct creation, but updating an existing policy now requires the expected revision. See api-contract.md.

## Evidence

- **187 Python 3.12 tests passed; 11 opt-in live tests skipped.** SAM validation/lint and fresh build succeeded.
- **18 frontend tests passed**, including editor workflow/concurrency/session checks and a production-build check for fingerprinted assets and exclusion of local QA credentials. Production build succeeded.
- **16 live administrator HTTP checks passed**: gateway JWT requirement; customer denial for list/detail/draft writes; admin metadata/pagination; private draft/search exclusion; stale revision conflict; real publication/embedding; preservation of the full published snapshot during edits; old customer JWT denial after group refresh; discard, archive, republish and audit. One invitation-suppressed synthetic user was temporarily granted administrator membership for this test only. One uniquely named, clearly marked test policy was briefly published, then archived/deleted. Both the test policy and identity were cleaned; account deletion blocked further admin access while its purge ran. No owner identity, owner PDF or existing policy was modified. Evidence: `.deployment/admin-live-acceptance.json`, `.deployment/admin-test-cleanup.json`.
- **Four real AI HTTP questions passed** on this release (shipping geography, refund trigger, warranty cause verification, unspecified warranty shipping fees), with grounded Vietnamese answers and DEMO sources; history and disposable-account cleanup passed. Case 26 still uses internal instructional wording, a non-blocking style note. Evidence: `.deployment/admin-ai-regression.json`.
- **Local browser UI verified** with a synthetic identity, fake data and moto-backed tables: opening/creating/editing drafts, publication, archive, republish and side-by-side draft/published preview. The local fixture never copied a browser session or proxied AWS. Production bundle checks exclude the mock authentication. The temporary tab and server were closed after testing. Screenshot: `C:\Users\accli\Documents\ChatGPT\AWS Intern\artifacts\admin-draft-local.jpg`.

The live website's browser origin is blocked by a saved browser permission, so live browser navigation/visual acceptance is not claimed. It was not retried through a proxy, another browser or session extraction. Local UI evidence and live authenticated HTTP evidence have different scopes. The earlier 30-question AI run and 39-check upload/OCR acceptance run are historical, not full reruns on this release. Summary: `.deployment/admin-release-verification.json`.

## Remaining practical limits

One working draft and the latest published snapshot are kept per policy, not a full version-history/dual-approver system. Policies remain global for one shop; multi-shop access isolation is not implemented. Policies and service terms remain fictional DEMO/drafts until the operator approves real content and contact details. No order/inventory/payment/carrier integration, load benchmark, SLA or newly verified password-recovery/alert-delivery claim is made. The existing budget is a notification threshold, not a hard spending cap.

Operator instructions: [Hướng dẫn quản trị](HUONG-DAN-QUAN-TRI.md).

This administrator report describes the previous b3971f release. The later support/source-scope release and current acceptance scope are documented in [support-verification.md](support-verification.md).
