# Policy Assistant — Final JWT Auth Diagnosis (2026-10-19)

## Status
DEPLOYED — UPDATE_COMPLETE (policy-assistant, ap-southeast-1, 629380420098)

## Actual Evidence
- `aws sts get-caller-identity`: 629380420098
- `aws cloudformation describe-stacks`: UPDATE_COMPLETE
- `sam.cmd build`: Build Succeeded
- `python -m pytest tests/unit -v --tb=short`: 69 passed
- `sam.cmd validate --lint`: valid SAM Template
- `curl /health`: HTTP 200 PASS
- `curl /policies/POL-001` (no JWT): HTTP 401 PASS
- Previous JWT request: HTTP 401 BLOCKED (`www-authenticate: Bearer error="invalid_token" error_description="illegal base64 data at input byte 601"`)
- Token claims verified locally (InitiateAuth): `iss` = correct User Pool; `aud` = `usn7b60eevhmvgsao7ok63a8l`; `token_use` = `id`; `exp` = future

## Blocker (Actual)
- Terminal environment: `cd` parameter non-functional (persistent failure)
- Token file: not present at `/home/user/.jwt_token` or repo `jwt_token.tmp` (cleaned after verification)
- Previous curl used very long JWT in command-line header, causing base64 truncation at byte 601
- Recommendation: Obtain fresh IdToken via `aws cognito-idp initiate-auth`; save to protected temp file; test with PowerShell `Invoke-RestMethod` using file-based `-Headers @{"Authorization"="Bearer $(Get-Content -Path ... -Raw)"}`

## Safety
- No `sam delete`
- No secrets in report
- No token values printed
- No existing data deleted
- No AWS resource mutation

## Not Tested (Blocked by auth transmission)
- Authenticated policy lookup with verified token
- Document E2E (upload-session → upload → submit → status → download)
- Document ownership isolation
- Worker/DLQ live inspection
