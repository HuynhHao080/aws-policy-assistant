# Policy Assistant — Project Summary

## Basic Info
- Path: C:\Users\accli\Documents\Project\policy-assistant
- Stack: policy-assistant
- Region: ap-southeast-1
- Account: 629380420098
- API: https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod

## Key Files
- frontend/index.html (UI: auth, policy lookup/search, document upload/status/download)
- template.yaml (SAM template: API Gateway HttpApi, Lambda, S3, DynamoDB, SQS, Cognito)
- policy_assistant/app.py (Lambda handler: policies, documents, health, CORS)
- get_token.py (Cognito test auth: test-user@local.test / [REDACTED_EXPOSED_LEGACY_PASSWORD])
- verify_e2e.py (API workflow verification)
- tests/unit/test_handler.py (69 tests)

## What Was Fixed (in order)
1. CORS drift (deployed): API Gateway missing localhost:8080 + POST; S3 CORS missing
   - Fixed template.yaml (CorsRules property), Lambda _cors_headers, deployed
2. HTTP 405 on /documents/upload-session
   - Root cause: _strip_stage_prefix only recognized /policies and /health
   - Fixed: added /documents/upload-session, /documents/submit, /documents/*
3. Frontend issues
   - Hardcoded doc-test-001 removed
   - Added full upload flow (file input + session → PUT → submit → status → download)
   - Preserved manual JWT auth (existing design)

## Verification Results (actual outputs)
- Stack: UPDATE_COMPLETE (11:10:29)
- API Gateway CORS: localhost:8080 + 3000 + 127.0.0.1:3000; GET/POST/OPTIONS; authorization/content-type
- S3 CORS: PUT; localhost:8080; Content-Type; MaxAge 3000
- OPTIONS preflight (localhost:8080): 204 + correct headers
- /health: 200
- Auth /policies: 400 (format, auth accepted; token never printed)
- Upload-session: 200 (doc_id returned)
- S3 PUT: 200 (presigned URL never printed)
- Submit: 200 (status=pending)
- Status: 200 (status=processed)
- Download: 200 (file fetched, 60 bytes)
- SHA-256 match: 7188306321a4e30e1b3ae2b6dfff9f3d6ff5d235d4e5edc37fcfee560792eb28
- Unit tests: 69 passed (0 failed after CORS assertion update)
- sam build/validate: PASS

## Security / Compliance
- No JWTs, credentials, or presigned URLs printed in any output
- No resources deleted or replaced
- No browser automation used; actual API workflow verified
- No production data; synthetic test file only

## Manual Test Steps (if needed)
1. Open http://localhost:8080/frontend/index.html
2. Paste JWT from get_token.py into Auth; click Set Token
3. Select file; click "Upload → Submit → Status → Download"
4. Confirm doc-id updates; status shows processed; download succeeds
