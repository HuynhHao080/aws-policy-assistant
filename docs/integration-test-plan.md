# Policy Assistant — Integration Test Plan

**Project:** `C:\Users\accli\Documents\Project\policy-assistant`
**Status:** Design only — not executed (requires deployed stack and live DynamoDB / Cognito).
**Prerequisites:** Deployed `policy-assistant` stack in `ap-southeast-1`; `AWS_SAM_STACK_NAME` set; valid Cognito JWT token for protected routes.

---

## How to Use This Plan

Each case includes: purpose, prerequisites, request, expected result, data-impact avoidance, and evidence to collect. Do not execute against production data without backup/approval.

---

## Authentication Tests

### IT-01: Health endpoint is public
- **Purpose:** Confirm `/health` requires no JWT.
- **Prereq:** Deployed API URL.
- **Request:** `curl -X GET "$API_URL/health"`
- **Expected:** HTTP 200, `{"status":"healthy"}`.
- **Data impact:** None.
- **Evidence:** `curl` output saved to `docs/evidence-index.md`.

### IT-02: Policy lookup requires JWT
- **Purpose:** Confirm protected route rejects missing/invalid token.
- **Prereq:** Valid JWT from Cognito User Pool.
- **Request:** `curl -H "Authorization: Bearer INVALID" "$API_URL/policies/POL-001"`
- **Expected:** HTTP 401/403 (API Gateway rejects invalid JWT).
- **Data impact:** None.
- **Evidence:** Response status and error body.

### IT-03: Policy lookup with valid JWT
- **Purpose:** Confirm authorized access returns policy.
- **Prereq:** Valid JWT.
- **Request:** `curl -H "Authorization: Bearer $VALID_JWT" "$API_URL/policies/POL-001"`
- **Expected:** HTTP 200, policy object with internal fields stripped.
- **Data impact:** Read-only.
- **Evidence:** Response JSON; compare with `sample_data/policies.json`.

---

## Policy Lookup Tests

### IT-04: Existing policy
- **Purpose:** Verify exact-ID retrieval.
- **Request:** `GET /policies/POL-001` (with JWT)
- **Expected:** 200; `policy_id`, `title`, `category`, `content`, `keywords` present; no `title_lower`.

### IT-05: Non-existent policy
- **Purpose:** Verify 404 behavior.
- **Request:** `GET /policies/POL-999` (with JWT)
- **Expected:** 404; `{"error":"Not found","message":"Policy with ID 'POL-999' not found"}`.

### IT-06: Empty policy ID
- **Purpose:** Verify 400 for empty/whitespace ID.
- **Request:** `GET /policies/` or `GET /policies/%20` (with JWT)
- **Expected:** 400; `{"error":"Bad request","message":"policy_id is required"}`.

---

## Search & Pagination Tests

### IT-07: Search with keyword
- **Purpose:** Verify keyword search returns matches.
- **Request:** `GET /policies?keyword=refund` (with JWT)
- **Expected:** 200; `policies` array non-empty; `count` matches array length; `scanned_count` ≥ `count`; `truncated` false (small dataset).

### IT-08: Case-insensitive search
- **Purpose:** Confirm lowercase matching.
- **Request:** `GET /policies?keyword=REFUND` (with JWT)
- **Expected:** 200; same results as `refund`.

### IT-09: Search with limit
- **Purpose:** Verify `limit` caps returned items.
- **Request:** `GET /policies?keyword=legal&limit=1` (with JWT)
- **Expected:** 200; `count` = 1; `policies` length = 1.

### IT-10: Search with pagination (first page)
- **Purpose:** Verify `next_token` returned when more pages exist.
- **Request:** `GET /policies?keyword=legal&limit=1` (with JWT)
- **Expected:** 200; `next_token` non-null; `count` = 1.

### IT-11: Search with pagination (second page)
- **Purpose:** Verify continuation with `next_token`.
- **Request:** `GET /policies?keyword=legal&limit=1&next_token=<token>` (with JWT)
- **Expected:** 200; `policies` contains different item(s); `next_token` null if final page.

### IT-12: Search with invalid token
- **Purpose:** Verify malformed token returns 400.
- **Request:** `GET /policies?keyword=refund&next_token=badtoken` (with JWT)
- **Expected:** 400; `{"error":"Bad request","message":"badtoken"}` (or similar; Lambda validates).

### IT-13: Search missing keyword
- **Purpose:** Verify 400 when `keyword` missing.
- **Request:** `GET /policies` (with JWT)
- **Expected:** 400; `{"error":"Bad request","message":"Query parameter 'keyword' is required"}`.

---

## Method & Endpoint Tests

### IT-14: Invalid method (POST)
- **Purpose:** Verify 405.
- **Request:** `POST /policies/POL-001` (with JWT)
- **Expected:** 405; `{"error":"Method not allowed","message":"Only GET method is supported"}`.

### IT-15: Invalid endpoint
- **Purpose:** Verify 404 for unknown path.
- **Request:** `GET /unknown` (with JWT)
- **Expected:** 404; `{"error":"Not found","message":"Invalid endpoint"}`.

---

## Data Safety & Avoidance of Production Impact

- All integration tests are **read-only** (GET only).
- No `POST`/`PUT`/`DELETE` endpoints exist; no data modification possible via API.
- To avoid affecting live data: use `limit=1` for pagination tests; do not run repeated scans at high frequency.
- If testing against production DynamoDB: use a separate test table or restore from `sample_data/policies.json` after any accidental write (not expected for read-only tests).
- Cognito JWT tokens should be obtained from a test user pool or temporary user; do not use production user credentials.

---

## Evidence Collection

For each executed test, save:
- Command executed (with `API_URL` and headers)
- HTTP status code
- Response body (redacted if contains tokens)
- Timestamp
- Whether test passed/failed

Store in `docs/evidence-index.md` under a new "Integration Test Evidence" section.

---

## References

- `tests/integration/test_api_gateway.py` — existing integration test framework
- `README.md` L289–308 — historical integration results
- `docs/aws-upgrade-roadmap.md` — CI/CD and frontend phases
- `policy_assistant/app.py` — handler contracts
