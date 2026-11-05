# Isolated source reproduction — 5 November 2026

## Result and scope

The existing canonical application was exported, integrity-checked and extracted into a new local folder. A new Python3.12 virtual environment installed dependencies from the extracted requirements; frontend dependencies were installed with `npm ci --ignore-scripts` from the extracted lockfile. The application working directory, installed frontend dependencies and earlier Python dependency folder were not reused for execution. System Python/Node/SAM tools and package download caches remain shared; this was not a new computer, container or AWS account.

- **273 Python tests passed;11 opt-in live tests skipped**,226.93seconds. PYTHONPATH and live-test stack/token variables were cleared; AWS credential variables in the test subprocess used synthetic values. Unit/mocked tests ran; no new model/PDF/AWS acceptance is claimed.
- **54 frontend tests passed**,0failed/0skipped. Synthetic DOM checks are not real-browser visual acceptance. Frontend build produced `app-IAHPVWYA.js` and `app-FD2HQBVT.css`, with intentionally unconfigured example connection settings.
- **SAM build passed for all six functions**, followed by `sam validate --lint --region ap-southeast-1` passing. The first build failed because PATH selected Python3.13; prepending the actual Python3.12 directory fixed runtime discovery. No template/runtime requirement was weakened.
- New source-bundle safeguards passed12tests, included in the273 total: deterministic output, excluded authentication/build artifacts, no overwrites, checksum tampering, source allowlist and path/device-name checks before extraction. Windows ZIP normalization required validating the original central-directory filename as well as its normalized filename.
- Frontend dependency installation audited41packages and reported0vulnerabilities at execution time. This narrow npm result is not a full code/dependency/security audit.

Tools: Python3.12, Node26.3.0, SAM CLI1.168.0. Exact installed Python versions are in [the dated snapshot](requirements-verified-2026-11-05.txt), with the caveat that it is not hash-locked or verified on every OS. [Instructions](README.md) document correct runtime selection and local-only verification.

## Provenance

Tested immutable source archive: `.deployment/source-handover-20261104/review-02.zip`.

SHA256: `65cd56b3de7dfd1405890104cce33462e8f8faa9ad2ae9723bf91f5c076d5f63`;196source files. Extracted into the sibling `fresh-02` folder; Python environment `venv-02` was created separately. Logs under the same ignored directory: `pip-install.log`, `python-tests.log`, `sam-build.log` (initial failure), `sam-build-python312.log` (successful rebuild), and `fresh-02/frontend-test.log`.

The final handover additionally includes these reproduction notes, the dependency snapshot and a CI integrity-check step. Packaging its updated documentation does not rerun the273tests; compare source code with the tested archive and retain the final bundle's external SHA256/manifest. No public source update, GitHub CI run, public worklog publication, hosted-login/visual acceptance, fresh-account deployment, backup restore, load test or new model call occurred in this verification.

Historical deployed quality evidence remains251Python/54frontend/15live checks with its original scope/date/artifact. The273count is a separate local reproduction including22new sync/export safeguards, not a newer cloud deployment or a sum of unrelated live results. Personal blog/event/attendance/diagram/Calculator evidence remains pending.
