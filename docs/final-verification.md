# Verification — 2026-10-30

Current handover reviewed 2026-11-04: [current shop profile release](shop-release-verification.md). The live results below describe their respective historical releases.

## Completed evidence

- Full offline suite on Python 3.12: **231 passed, 11 opt-in live tests skipped**.
- Frontend API/upload/editor/build suite: **33 passed**.
- Frontend production build: succeeded, including self-hosted Vietnamese fonts and OIDC dependency.
- Runtime dependency audit for frontend: 0 reported vulnerabilities at the time checked.
- SAM validation: valid template. SAM build: succeeded for API, worker, isolated PDF parser, dispatcher, recovery and signup guard.
- Live model probes using synthetic text: Cohere multilingual int8 embedding returned 1,024 dimensions; APAC Nova Micro inference succeeded.
- Local browser: page rendered, connection-not-configured state and Vietnamese typography inspected. This preview is not a live authentication or backend workflow test.

## Deployed application and live acceptance

- Public HTTPS URL: https://djreo5eptvwk5.cloudfront.net/
- Stack `policy-assistant`, account `629380420098`, Singapore: **UPDATE_COMPLETE**. CloudFront: **Deployed**. Both metadata indexes are active, recovery is enabled, and frontend assets/config were published after migration. The Cognito pool/client and existing data resources were preserved.
- Previous language-fix change set: `public-final-1793331454`. Lambda zip SHA-256: `e7ab4b0584e8e98075d49b19d9e99b88dfef18caf22b3b9342da1f24c6fd1c19`. Template SHA-256: `678282aa6c2a24ecea9bb8ff24546a03e124088a3ae67c28147cb499db450c35`.
- **Live acceptance passed: 39 checks**, including OCR, using two disposable Cognito users: actual JWT authorization, upload/CORS, durable dispatch, isolated text extraction, original download byte hash, Vietnamese answers sourced to an English PDF/page, cross-account denials, private history, customer/admin role separation, policy publication/deletion/audit, scanned-PDF OCR and sourced answers, renaming, PDF deletion and all-version S3 purge. The synthetic users and their private data were then deleted successfully. Machine-readable evidence: `live-acceptance-2026-10-30.json`.
- The initial run found a missing API UsageTable PutItem permission for the account-deletion marker. The template was fixed, a regression check added, and the complete live run passed after deployment. The earlier run's disposable users/data were also cleaned. Missing S3 objects can return 403 to a scoped presigned caller; version purge is additionally verified with operator listing permissions, requiring both Versions and DeleteMarkers to be empty.
- Public-site automated browser navigation was declined by the origin approval gate and was not retried through another surface. Hosted-login interaction and public visual acceptance have not been claimed as browser-tested. The 11 skipped integration tests are not counted as live passes.

## Owner confirmation and remaining checks

The owner registered and confirmed administrator access. The SNS subscription was confirmed. Actual alert delivery and password recovery have not been newly acceptance-tested. The AWS budget is USD 50 with notifications at USD 25/40/50; it is not a hard billing cap.

No load benchmark or availability SLA is claimed. This is a bounded small public launch; quotas and retrieval limits are documented in the runbook and API contract.

Offline coverage includes ownership and cursor isolation, atomic quotas, immutable S3 versions, version purge, document/worker retries, multilingual retrieval, model citation validation/refusal, private history, admin/audit transactions, signup limits, OCR polling/cost limits, blocked account access and identity/data cleanup.


## Vietnamese response regression fix

A Vietnamese warranty-shipping question was correctly grounded but answered in English. The generation instructions now explicitly default to Vietnamese with diacritics and require direct, customer-facing wording. A different output language is allowed only when explicitly requested. Source validation, retrieval, quota and history behavior are unchanged.

The full Python 3.12 suite passed again: 150 passed, 11 opt-in live tests skipped. SAM build succeeded. Four live retrieval/model probes passed using public DEMO policies and isolated in-memory history/quota handling, including the reported question twice, missing phone-case warranty information, and the charger warranty duration. These are not browser tests. The deployment completed and the API function CodeSha256 matches the reviewed artifact. See language-fix-verification.md for details. Existing conversation entries are not rewritten; submit a new question to test the new wording.

## Previous retail follow-up

That answer-refinement release was `public-final-1793345584`, Lambda SHA-256 `2dbb212f3e9663a4682fd6f16a157d7aa8dcb120f5ee9c61fa990a1c38395a31`, template SHA-256 `7bc25d4540b5980f6838394ef1fce0ac5bb8fc34628fcf57bd7f6a01e8c15f37`. It preserves policy qualifiers, avoids invented customer status and uses structured answer serialization with server-side citation validation. Final evidence: 169 offline tests passed (11 opt-in live skipped), 30 public-policy questions completed without request errors (all core outcomes acceptable; three secondary notes), nine authenticated HTTP questions passed, and the disposable account was cleaned. See [retail verification](retail-pilot-verification.md) for exact scope, evidence and limitations. The earlier 39-check acceptance run is historical, not a complete workflow rerun of this release. Browser control remains unavailable.

## Previous administrator release

Previous release: `public-final-1793347694`, Lambda SHA-256 `b3971f78369dac2aab0675dbb7973f7abbae158a2fe8021381a19fdf9eceaed6`, template SHA-256 `1edce0cce2308d72b097850671f80bd2001844cfb6b8d140958f81d8f3b493ad`. Backend and frontend publication completed; CloudFront invalidation completed and the published entry/config/assets matched local bytes. Evidence: **187 Python tests**, **18 frontend tests**, **16 live administrator HTTP checks**, and **four real AI HTTP questions** passed; both disposable identities and the synthetic policy were cleaned. Local browser UI used synthetic authentication/data only; saved permission blocks the live website's browser origin. This is not a live-browser or full upload/OCR rerun. See [admin verification](admin-verification.md) for scope and [operator guide](HUONG-DAN-QUAN-TRI.md).

Previous support release: `public-final-1793350855`; 209 Python/26 frontend passes, 28 deployed support/source-scope checks and complete synthetic cleanup. See support-verification.md for exact hashes and browser limitations.
