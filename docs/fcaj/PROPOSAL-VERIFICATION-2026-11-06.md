# Current proposal and worklog verification — 6 November 2026

This documentation/tooling update aligns the bilingual proposal with the deployed single-shop Policy Assistant. It does not change the AWS runtime or approve real business policies.

## Delivered

- New VI/EN `2-Proposal/CurrentSolution` pages describe users/problem, scope, architecture/data flows, decisions, risks, proposed remaining effort, COST inputs and acceptance boundaries.
- Managed notices on 20 existing pages now point to the current proposal and support release rather than presenting the earlier 251-test snapshot as the latest release. Content outside these blocks remains unchanged.
- Four technical chapters per language are defined by one synchronization map. The verifier resolves local links, encoded fragments and assets for all eight pages, rejects invalid output, and compares all three sanitized evidence exports against reviewed source reports.
- Additional regression tests cover missing pages/assets/anchors, encoded Vietnamese fragments, UTF-8 replacement characters, unrendered shortcodes, build path escapes, incomplete cleanup and mismatched deployment evidence. No browser or network is needed for these tests.

## Actual local checks

| Check | Observed result |
|---|---|
| Targeted synchronization/verification tests | 23 passed |
| Hugo extended 0.167.0 | Build passed; 140 EN pages, 139 VI pages, 102 static files per language |
| Historical preservation | 20 original files unchanged outside managed blocks |
| Technical guides | 8 pages, 856 local link/asset occurrences resolved, including fragments; 25 distinct local assets |
| Evidence | 3 allowlisted exports matched; zero synchronization drift |

Hugo still emits three pre-existing theme deprecation warnings; no build failure occurred. Generated proof is ignored under `.deployment/proposal-20261106/`; the original preservation baseline remains `.deployment/worklog-sync-20261104T110633559705Z`. Backups precede managed worklog writes.

Reproduce from the canonical application folder, after building the worklog into the specified directory:

```powershell
python -m pytest tests/unit/test_worklog_sync.py tests/unit/test_worklog_verification.py -q
python scripts/sync_fcaj_worklog.py --worklog C:/Users/accli/Documents/Project/aws-internship-worklog
python -m scripts.verify_fcaj_worklog --worklog C:/Users/accli/Documents/Project/aws-internship-worklog --build .deployment/proposal-20261106/preview --backup .deployment/worklog-sync-20261104T110633559705Z --report .deployment/proposal-20261106/verification.json
```

The verifier is invoked as a module (`python -m scripts.verify_fcaj_worklog`) so its repository imports resolve. It reads local files, not the public site. Public availability and GitHub workflow results must be checked separately after publication.

## Evidence boundaries

The 322 Python / 67 frontend / 20 HTTP figures in the proposal remain the previously recorded support-runtime snapshot; they are not reruns by this documentation update. No model, PDF/OCR, new customer-data operation, browser visual, AWS deployment, load, restore or email-delivery check was performed in this update. Existing primary runtime and historical pilot/canary state are preserved.

The proposal's USD 30–50 target, budget alerts and workload assumptions do not constitute a verified monthly estimate. Calculator total/share URL, student-designed AWS diagram, actual blog publications, attendance/event evidence, personal explanation and a recorded demo remain pending. Current business content remains DEMO.

Reviewed [workshop rules](https://hcm-rules.awsfcaj.com/3-project/) and [scoring guidance](https://hcm-rules.awsfcaj.com/5-scoring/) on 6 November 2026. These motivate a bilingual, evidence-backed proposal and student-owned architecture; no grade or eligibility is claimed. AI assistance is disclosed on both proposal pages.
