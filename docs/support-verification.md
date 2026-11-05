# Support and source-scope release verification

Historical support release. Latest scope and evidence: [practical triage verification](practical-release-verification.md).

Handover review date: 2026-11-04. Raw execution timestamps are retained in the evidence JSON; they are not rewritten to the handover date.

- Existing stack: `policy-assistant`, Singapore, account `629380420098`.
- Change set: `public-final-1793350855`.
- Lambda artifact SHA-256: `34358298ca99b859430600d21a01efac12dc0872ca74a391a99053e10e823500`.
- Template SHA-256: `3fb19ef3066ab2fa614cf23b4905b98529819dd497ca4fd6a304ac6d8e3ca4e4`.
- Adds one encrypted, on-demand SupportTable with PITR, TTL and retention protection; eight Cognito-authorized support routes; scoped API/worker access and the account-deletion transaction condition. Existing identity/storage resources are preserved.

## Verification

- Current Python 3.12 suite rerun: **209 passed, 11 opt-in live tests skipped**.
- Current frontend suite/build rerun: **26 passed**, production assets `app-KQGCZQB5.js` / `app-MLQO6QVJ.css`. Legal pages use the fingerprinted stylesheet too; the production build excludes local QA authentication.
- SAM validation/build succeeded before the reviewed deployment.
- **28 deployed HTTP/data/model checks passed**, see [machine-readable report](support-live-acceptance.json). Two disposable identities and one private synthetic PDF exercised JWT boundaries, real selected-PDF versus policy-only generation, consent, absence of automatic attachments, cross-customer denials, administrator/PDF separation, queue pagination, staff replies, revision conflicts, reopening/closing/deletion, blocked deleting accounts, complete support purge and S3 all-version purge.
- Cleanup flags `identities_cleaned`, `support_purged` and `pdf_versions_purged` are all true. No owner account, customer PDF or real policy was modified; no support email was sent.
- Local UI fixture exercised create, customer follow-up, staff reply/resolved state and customer readback. It used fake authentication, moto storage and synthetic messages only; it is not evidence of hosted Cognito browser login or real AI generation.
- Fresh AWS control-plane verification confirmed all six deployed Lambda code hashes match the reviewed artifact and the stack is UPDATE_COMPLETE.
- Frontend publication invalidation: `I8M5R7G09H957925OWIEM6MHOR`. Artifact verification is recorded separately in [frontend report](support-frontend-verification.json).

## Limits

The live website's browser origin access was declined and was not retried through another browser/proxy. Browser verification therefore applies to the isolated local fixture only; deployed backend verification uses synthetic authenticated API calls. The earlier retail/OCR/admin reports remain historical. No load benchmark, new alert-email delivery or password recovery acceptance is claimed. Policies remain DEMO until the shop approves real content.

Operator guide: [Hướng dẫn hỗ trợ](HUONG-DAN-HO-TRO.md). Product scope: [Feature status](FEATURE-STATUS.md).
