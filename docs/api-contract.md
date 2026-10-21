# Policy Assistant — API Contract (Verified from Source)

**Project:** `C:\Users\accli\Documents\Project\policy-assistant`
**Verified:** 2026-10-19
**Source of truth:** `policy_assistant/app.py`, `template.yaml`, `tests/unit/test_handler.py`, `README.md`
**Status:** Documented from actual implementation; not invented.

---

## Base URL (Historical / Previously Reported)

`https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod/`

**Note:** This is historical deployment evidence (Phase L). Current live state is not independently verified in this audit.

---

## Authentication Model

- `GET /policies/{policy_id}`: JWT required (`PolicyAssistantApi.Auth.Authorizers.PolicyAssistantAuthorizer` via Cognito User Pool).
- `GET /policies`: JWT required (same authorizer).
- `GET /health`: Public (no `Auth` property on `HealthCheck` event).
- Authorization is enforced at API Gateway; Lambda does not verify JWT.

---

## Endpoints

### 1. `GET /health`

| Field | Value |
|---|---|
| Method | GET |
| Auth | None (public) |
| Path params | None |
| Query params | None |
| Success (200) | `{"status":"healthy"}` |
| Errors | 405 (method not allowed), 404 (invalid endpoint) |

**Verified:** `app.py` L99; `template.yaml` `HealthCheck` event (no `Auth`); `tests/unit/test_handler.py` `TestHealthCheck`.

---

### 2. `GET /policies/{policy_id}`

| Field | Value |
|---|---|
| Method | GET |
| Auth | JWT required (`Auth.Authorizer: PolicyAssistantAuthorizer`) |
| Path params | `policy_id` (String, required) |
| Query params | None |
| Success (200) | Policy object: `{"policy_id":"POL-001","title":"...","category":"...","content":"...","keywords":[...]}` (internal `*_lower` fields stripped) |
| Not found (404) | `{"error":"Not found","message":"Policy with ID 'POL-999' not found"}` |
| Bad request (400) | `{"error":"Bad request","message":"policy_id is required"}` (empty/whitespace) |
| Method not allowed (405) | `{"error":"Method not allowed","message":"Only GET method is supported"}` |

**Verified:** `app.py` L87–89, L112–130; `tests/unit/test_handler.py` `TestGetPolicyById`.

---

### 3. `GET /policies`

| Field | Value |
|---|---|
| Method | GET |
| Auth | JWT required (`Auth.Authorizer: PolicyAssistantAuthorizer`) |
| Path params | None |
| Query params | `keyword` (String, required, non-empty); `limit` (Integer, optional, 1–100); `next_token` (String, optional, base64-encoded JSON of `LastEvaluatedKey`) |
| Success (200) | `{"policies":[...],"count":N,"scanned_count":N,"truncated":bool,"next_token":"..."\|null}` |
| Bad request (400) | `{"error":"Bad request","message":"Query parameter 'keyword' is required"}` (missing/empty); `{"error":"Bad request","message":"Query parameter 'limit' must be a positive integer"}` (≤0); `{"error":"Bad request","message":"Query parameter 'limit' must not exceed 100"}` (>100); `{"error":"Bad request","message":"Query parameter 'limit' must be a valid integer"}` (non-integer); `{"error":"Bad request","message":"..."}` (invalid `next_token`) |
| Not found (404) | `{"error":"Not found","message":"Invalid endpoint"}` (only for unknown paths) |

**Pagination contract:**
- `next_token` is returned only when `LastEvaluatedKey` exists from DynamoDB Scan.
- Final page returns `next_token: null` (omitted or null — documented as `null` in code; response always includes key with `None` value when no continuation).
- `limit` bounds returned items, not evaluated items (DynamoDB `Limit` bounds evaluated items per page).
- `scanned_count` accumulates across all Scan pages within the request.
- `truncated` is `true` when `scanned_count >= MAX_SCAN_ITEMS` (1000) and more pages may exist.

**Verified:** `app.py` L132–257; `README.md` L22–23, L54–60; `tests/unit/test_handler.py` `TestSearchPagination` (6 tests), `TestScanBudget` (6 tests), `TestSearchLimit` (5 tests).

---

## Response Format Consistency

All responses use `Content-Type: application/json` with CORS headers (`Access-Control-Allow-Origin`, `Access-Control-Allow-Headers`, `Access-Control-Allow-Methods`). Error responses use the same `_error_response` helper with consistent `statusCode`, `headers`, `body` structure.

No internal lowercase fields (`title_lower`, etc.) appear in any response (`_strip_internal_fields`).

---

## Limitations & Unverified Behavior

- **No live API verification** in this audit (historical integration results from Phase L only).
- **Pagination with large datasets** not tested live; behavior inferred from mocked DynamoDB responses.
- **Cognito JWT token validation** not tested against live issuer (template-only verification via `TestCognitoAuthorization`).
- **Scan budget (`MAX_SCAN_ITEMS = 1000`)** is a code-level bound; DynamoDB `Limit` per page is `min(remaining_budget, 1000)`.
- **No request validation at gateway** for `limit` type/range (HTTP API limitation; Lambda authoritative).

---

## References

- `policy_assistant/app.py` — handler implementation
- `template.yaml` — SAM template (routes, auth, monitoring)
- `tests/unit/test_handler.py` — 64 passing tests
- `README.md` — endpoint documentation
