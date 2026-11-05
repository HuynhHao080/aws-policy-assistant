# Final V1 UI verification — 2026-11-04

Historical V1 snapshot before the quality extension. Current evidence: [quality release](quality-release-verification.md).

Primary frontend only: djreo5eptvwk5.cloudfront.net / existing policy-assistant stack. No Lambda source/template/model/identity/database change was made in this pass.

## Changes and regression coverage

Administrator workspaces are separate persistent tab panels with ARIA references/selection and keyboard navigation. Guest forms are inert and the destructive account panel is hidden. Notices support dismissal and appear inside the active support modal rather than behind it. Policy sources use a plaintext modal without inserting HTML. Navigation creates real fragment history, redirects unauthorized administrator routes and protects unsaved editors/logout. Invalid source selection is rejected before clearing the previous answer or sending an AI request.

Bounded PDF polling reports readiness/failure/continued processing distinctly, releases controls after validation failure, and stops reading/writing after the session changes. Latest-response guards protect document/policy/history/audit lists. Session clearing resets search/order filters, counts, pagination and private content. Typography, touch targets, small-screen grids/dialogs and table scrolling are refined; motion respects prefers-reduced-motion.

## Actual results

- **48 frontend tests passed** with Node26.3.0, production build succeeded.
- Existing API/editor/build tests plus3 new lifecycle tests and12 isolated DOM interaction tests. DOM tests execute the actual main entry using esbuild and jsdom, synthetic auth/fetch and no network egress. A minimal dialog shim is used, so these are not browser/visual/rendering tests.
- Production assets: app-OFZZGQ2R.js and app-FYHZGEMM.css. The build excludes local/unit authentication markers and legal pages reference the fingerprinted CSS.
- Runtime and full npm dependency audit reported0 vulnerabilities at execution time. jsdom30.1.3 is a development dependency only; no new runtime dependency or third-party analytics was added.
- Static HTML checks passed: unique element IDs, valid label/ARIA target references, five administrator tab panels. Primary muted text #58695c on paper #f7f5ed measures5.36:1; this is one verified color pair, not a complete WCAG certification.
- Deployment bytes, six unchanged backend hashes, CloudFront invalidation and operational metadata are recorded in [artifact report](v1-ui-artifact-verification.json) and [operations snapshot](v1-operational-status.json).

## Limits

The previously declined browser-origin authority was respected. No real-browser screenshot, mobile viewport rendering, hosted Cognito flow, live AI/PDF roundtrip, load test or email delivery test was run in this UI-only pass. Earlier reports retain their own scope. The unchanged backend's last full suite is231 passed/11 opt-in skipped; its14 live shop checks are historical for that same immutable backend artifact, not rerun here.

Refer to [V1 handover](RELEASE-V1.md) for the fixed product scope and human business-content review gates.
