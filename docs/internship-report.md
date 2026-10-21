# Policy Assistant — Internship Report

## 1. Title and Project Summary

**Project Name:** Policy Assistant  
**Project Type:** Serverless Minimum Viable Product (MVP)  
**Primary Technology:** AWS SAM, Python 3.12, Amazon API Gateway HTTP API, AWS Lambda, Amazon DynamoDB  
**Region:** `ap-southeast-1`  
**CloudFormation Stack:** `policy-assistant`  
**API Base URL:** `https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod/`  

Policy Assistant is a serverless application for retrieving and searching organizational policies. It exposes a RESTful API over HTTP that allows users to look up policies by exact ID or search for policies by keyword. The application is designed as an MVP suitable for small policy repositories (under 100 policies) and is not intended for production-scale use without further optimization.

## 2. Background and Problem Statement

Organizations often maintain numerous policy documents (refund policies, privacy policies, terms of service, etc.) that employees and customers need to access. Without a centralized, searchable repository, users must manually search through documents or contact support staff for basic policy information.

**Problem:** Manual policy lookup is time-consuming and error-prone. There is no centralized API for programmatic policy retrieval.

**Solution:** A serverless API that provides:
- Exact-ID policy retrieval (`GET /policies/{policy_id}`)
- Case-insensitive keyword search (`GET /policies?keyword=xxx`)
- Health check endpoint (`GET /health`)

**Intended Users:** Internal staff, customers, and automated systems that need to look up policy information programmatically.

## 3. Project Objectives and Scope

### Objectives
- Build a serverless API for policy retrieval and keyword search
- Use AWS serverless services (Lambda, API Gateway, DynamoDB, CloudWatch Logs)
- Implement case-insensitive keyword search with DynamoDB Scan
- Add a per-request scan budget to bound read capacity consumption
- Strip internal metadata fields from client-facing responses
- Provide comprehensive unit test coverage with mocked DynamoDB
- Deploy to AWS and verify against the live API

### Scope (Included)
- Two API endpoints: `GET /policies/{policy_id}` and `GET /policies?keyword=xxx`
- Health check endpoint: `GET /health`
- DynamoDB table with `policy_id` partition key, on-demand billing
- Case-insensitive keyword search across title, category, content, and keywords
- Per-request scan budget (1,000 items evaluated per request)
- Optional `limit` parameter (max 100 returned items)
- Internal lowercase fields stripped from client responses
- CORS headers on all responses
- JSON error responses with appropriate HTTP status codes
- 43 unit tests with mocked DynamoDB
- 9 integration tests against the deployed API

### Scope (Excluded)
- Authentication and authorization (API is publicly accessible)
- Frontend user interface
- Policy creation, update, or deletion (read-only API)
- Cursor-based pagination (`next_token`)
- Amazon Bedrock, RAG, embeddings, or vector search
- Amazon Cognito, API keys, or Lambda authorizers
- CloudWatch Alarms, X-Ray tracing, or synthetic monitoring
- Amazon S3, Kinesis, IoT Core, Glue, Athena, QuickSight, or other AWS services
- CI/CD pipeline (deployment via `sam deploy --guided`)

## 4. Functional and Non-Functional Requirements

### Functional Requirements
| ID | Requirement | Status |
|----|-------------|--------|
| FR-01 | Retrieve a policy by exact ID via `GET /policies/{policy_id}` | Implemented, verified |
| FR-02 | Search policies by keyword via `GET /policies?keyword=xxx` | Implemented, verified |
| FR-03 | Case-insensitive keyword matching | Implemented, verified |
| FR-04 | Health check endpoint `GET /health` | Implemented, verified |
| FR-05 | Optional `limit` parameter to cap returned results (max 100) | Implemented, verified |
| FR-06 | Return `scanned_count` and `truncated` in search responses | Implemented, verified |
| FR-07 | Strip internal `*_lower` fields from client responses | Implemented, verified |
| FR-08 | Return appropriate HTTP status codes (200, 400, 404, 405, 500) | Implemented, verified |
| FR-09 | Include CORS headers on all responses | Implemented, verified |

### Non-Functional Requirements
| ID | Requirement | Status |
|----|-------------|--------|
| NFR-01 | Serverless architecture (no EC2, no long-running servers) | Implemented |
| NFR-02 | Pay-per-request billing (DynamoDB on-demand, Lambda, API Gateway HTTP API) | Implemented |
| NFR-03 | Per-request scan budget of 1,000 evaluated items | Implemented |
| NFR-04 | Least-privilege IAM permissions (GetItem, Scan only) | Implemented |
| NFR-05 | CloudWatch Logs with JSON format and 30-day retention | Implemented |
| NFR-06 | Unit tests with mocked DynamoDB (no AWS credentials required) | Implemented, 43 tests pass |
| NFR-07 | Integration tests against deployed API | Implemented, 9 tests pass |

## 5. System Architecture

### Request Flow

```
Client (curl, browser, script)
    │
    │ HTTPS GET
    ▼
Amazon API Gateway HTTP API (v2)
    Stage: Prod
    CORS: localhost:3000, 127.0.0.1:3000
    │
    │ AWS_PROXY integration
    ▼
AWS Lambda (Python 3.12, 10s timeout)
    Handler: app.lambda_handler
    │
    ├─ GetItem → DynamoDB Table: PolicyAssistantPolicies
    │    Partition Key: policy_id (String)
    │    Billing: PAY_PER_REQUEST
    │
    └─ Scan with FilterExpression → DynamoDB Table: PolicyAssistantPolicies
         Filter: contains() on lowercase fields
         Limit: bounded by MAX_SCAN_ITEMS (1,000)
    │
    ▼
CloudWatch Logs (JSON format, 30-day retention)
    Log Group: /aws/lambda/PolicyAssistantFunction-...
```

### Components

| Component | Responsibility |
|-----------|---------------|
| API Gateway HTTP API | Entry point, routes requests to Lambda, handles CORS, stage management |
| Lambda Function | Request routing, input validation, DynamoDB interaction, response formatting |
| DynamoDB Table | Policy storage, GetItem for exact-ID lookup, Scan for keyword search |
| CloudWatch Logs | Lambda execution logs, JSON format, 30-day retention |
| IAM Role | Least-privilege execution role for Lambda (GetItem, Scan only) |

## 6. AWS Services and Responsibilities

| Service | Purpose | Configuration |
|---------|---------|---------------|
| Amazon API Gateway HTTP API | RESTful API endpoint, request routing, CORS | Stage: Prod, CORS origins: localhost:3000, 127.0.0.1:3000 |
| AWS Lambda | Compute, request handling, business logic | Runtime: Python 3.12, Timeout: 10s, Memory: 128 MB, Architecture: x86_64 |
| Amazon DynamoDB | Policy data storage | Table: PolicyAssistantPolicies, PK: policy_id (String), Billing: PAY_PER_REQUEST |
| Amazon CloudWatch Logs | Application logging | Log group: /aws/lambda/PolicyAssistantFunction-..., Retention: 30 days, Format: JSON |
| AWS IAM | Execution role permissions | dynamodb:GetItem, dynamodb:Scan on table ARN only |

## 7. Application Design and API Workflow

### API Endpoints

#### GET /policies/{policy_id}
Retrieve a single policy by its exact ID.

**Request:**
```
GET /policies/POL-001
```

**Response (200):**
```json
{
  "policy_id": "POL-001",
  "title": "Customer Refund Policy",
  "category": "Customer Service",
  "content": "Customers may request a full refund within 30 days...",
  "keywords": ["refund", "return", "customer", "money back", "30 days", "defective", "damaged"]
}
```

**Response (404):**
```json
{
  "error": "Not found",
  "message": "Policy with ID 'POL-999' not found"
}
```

#### GET /policies?keyword=xxx
Case-insensitive keyword search across title, category, content, and keywords.

**Request:**
```
GET /policies?keyword=refund
```

**Response (200):**
```json
{
  "policies": [...],
  "count": 1,
  "scanned_count": 3,
  "truncated": false
}
```

**Query Parameters:**
- `keyword` (required): Search term, case-insensitive
- `limit` (optional): Maximum number of results (1-100)

**Response Fields:**
- `policies`: List of matching policy objects (internal `*_lower` fields stripped)
- `count`: Number of policies returned
- `scanned_count`: Total items DynamoDB evaluated across all Scan pages
- `truncated`: `true` if scan budget was exhausted before all matches found

#### GET /health
Lightweight liveness check. Verifies Lambda handler availability only; does NOT verify DynamoDB connectivity.

**Request:**
```
GET /health
```

**Response (200):**
```json
{
  "status": "healthy"
}
```

### Error Responses

| Status Code | Condition | Response Body |
|-------------|-----------|---------------|
| 400 | Missing or invalid `keyword` or `limit` parameter | `{"error": "Bad request", "message": "..."}` |
| 404 | Policy not found or invalid endpoint | `{"error": "Not found", "message": "..."}` |
| 405 | Unsupported HTTP method | `{"error": "Method not allowed", "message": "Only GET method is supported"}` |
| 500 | DynamoDB error or unexpected exception | `{"error": "Internal server error", "message": "..."}` |

## 8. DynamoDB Data Model

### Table: PolicyAssistantPolicies

| Property | Value |
|----------|-------|
| Table Name | `PolicyAssistantPolicies` |
| Partition Key | `policy_id` (String, HASH) |
| Billing Mode | PAY_PER_REQUEST |
| GSIs / LSIs | None |
| Item Count | 3 sample policies |

### Policy Item Schema

| Attribute | Type | Description | Returned to Client |
|-----------|------|-------------|-------------------|
| `policy_id` | String | Unique policy identifier | Yes |
| `title` | String | Policy title | Yes |
| `category` | String | Policy category | Yes |
| `content` | String | Full policy text | Yes |
| `keywords` | List[String] | Search keywords | Yes |
| `title_lower` | String | Lowercase copy of title | No (stripped) |
| `category_lower` | String | Lowercase copy of category | No (stripped) |
| `content_lower` | String | Lowercase copy of content | No (stripped) |
| `keywords_lower` | List[String] | Lowercase copy of keywords | No (stripped) |

### Sample Policies

| ID | Title | Category |
|----|-------|----------|
| POL-001 | Customer Refund Policy | Customer Service |
| POL-002 | Privacy Policy | Legal |
| POL-003 | Terms of Service | Legal |

### Search Access Pattern

Keyword search uses DynamoDB `Scan` with a `FilterExpression` containing `contains()` on four lowercase fields (`title_lower`, `category_lower`, `content_lower`, `keywords_lower`). Each Scan request passes DynamoDB's `Limit` parameter bounded by the remaining scan budget. A per-request scan budget of 1,000 evaluated items bounds read capacity consumption. When the budget is exhausted, scanning stops and `truncated` is set to `true` if more items may remain unprocessed.

**Important:** The `limit` parameter caps returned items but does NOT bound scanned items. The scan budget (1,000 items) bounds read capacity consumption per request.

## 9. Implementation Details

### Lambda Handler (`policy_assistant/app.py`)

The Lambda handler is a single Python file (`app.py`) containing:

- **`lambda_handler`**: Main entry point, routes requests to appropriate handler based on path and method
- **`_strip_stage_prefix`**: Strips API Gateway stage prefix from request path (e.g., `/Prod/policies` → `/policies`)
- **`_get_policy_by_id`**: Retrieves a policy by exact ID using DynamoDB `GetItem`
- **`_search_policies`**: Searches policies by keyword using DynamoDB `Scan` with `FilterExpression`
- **`_strip_internal_fields`**: Removes internal `*_lower` fields from client responses
- **`_cors_headers`**: Returns CORS headers for all responses
- **`_success_response`**: Creates a successful HTTP response with JSON body and CORS headers
- **`_error_response`**: Creates an error HTTP response with JSON body and CORS headers

### Error Handling

- `ClientError` (DynamoDB): Returns 500 with "Database error occurred"
- `Exception` (unexpected): Returns 500 with "An unexpected error occurred" (no stack trace leaked)
- Missing/empty `keyword`: Returns 400
- Invalid `limit`: Returns 400 (must be positive integer, max 100)
- Missing `policy_id`: Returns 400
- Policy not found: Returns 404
- Unsupported HTTP method: Returns 405
- Invalid endpoint: Returns 404

## 10. Security and IAM Design

### IAM Permissions

The Lambda execution role (`PolicyAssistantFunctionRole`) grants least-privilege permissions:

- `dynamodb:GetItem` on `PolicyAssistantPolicies` table ARN
- `dynamodb:Scan` on `PolicyAssistantPolicies` table ARN

No other AWS service permissions are granted.

### Authentication and Authorization

**Not implemented.** The API is publicly accessible. No Amazon Cognito, API keys, or Lambda authorizers are configured.

### CORS

Configured for `http://localhost:3000` and `http://127.0.0.1:3000` only. All responses include:
- `Access-Control-Allow-Origin`
- `Access-Control-Allow-Headers`
- `Access-Control-Allow-Methods`

### Data Sensitivity

No sensitive data is stored in the sample policies. The sample data contains fictional policy content for demonstration purposes only.

## 11. Testing Methodology and Results

### Unit Tests

**File:** `tests/unit/test_handler.py`  
**Framework:** pytest with moto (mocked DynamoDB)  
**Count:** 43 tests  
**Result:** All 43 passed  
**AWS Credentials:** Not required (moto mocks DynamoDB)

Test classes:
- `TestGetPolicyById` (4 tests): Policy lookup by ID, not found, empty ID, whitespace ID
- `TestSearchPolicies` (9 tests): Keyword search success, case-insensitive, partial match, keywords field, no matches, missing/empty/whitespace keyword
- `TestErrorHandling` (5 tests): Invalid POST/PUT, invalid endpoint, CORS headers
- `TestHealthCheck` (2 tests): Health check success, trailing slash
- `TestSearchLimit` (5 tests): Valid limit, zero limit, negative limit, above max, invalid limit
- `TestScanBudget` (6 tests): Truncated field, DynamoDB Limit parameter, budget exhaustion, no further scans, zero-match page, limit respects budget, exact budget no more pages, exact budget with more pages, result limit before budget
- `TestInternalFieldStripping` (2 tests): Get by ID strips fields, search strips fields
- `TestDynamoDBErrors` (2 tests): GetItem ClientError, Scan ClientError
- `TestStagePrefixRouting` (1 test): Policy ID matching stage name
- `TestUnexpectedException` (1 test): Unexpected exception returns 500 without stack trace
- `TestResponseFormat` (3 tests): JSON content type for success/error, search response structure

### Integration Tests

**File:** `tests/integration/test_api_gateway.py`  
**Framework:** pytest with requests  
**Count:** 9 tests  
**Result:** All 9 passed against deployed API  
**AWS Credentials:** Required (calls live API)

Integration tests require:
- `AWS_SAM_STACK_NAME` environment variable (default: `policy-assistant`)
- `AWS_DEFAULT_REGION` environment variable (default: `ap-southeast-1`)
- Deployed CloudFormation stack

Integration tests are read-only (GET/OPTIONS only) and do not modify any data.

### Testing Gaps

- No cursor-based pagination tests (not implemented)
- No frontend tests (no frontend exists)
- No security/penetration tests (no authentication implemented)
- No load/performance tests
- No chaos engineering tests

## 12. Deployment Procedure and Previously Reported Deployment Evidence

### Deployment Procedure

The application is deployed using AWS SAM (Serverless Application Model):

```bash
# Validate template
sam validate --lint

# Build application
sam build

# Deploy to AWS
sam deploy --guided
```

Deployment prompts:
- Stack Name: `policy-assistant`
- AWS Region: `ap-southeast-1`
- Confirm changes: `y`
- Allow SAM CLI IAM role creation: `y`
- Save to samconfig.toml: `y`

### Previously Reported Deployment Evidence

The following deployment results were reported from a previous deployment session (Phase L, October 2026):

**Stack Status:** `UPDATE_COMPLETE`  
**Region:** `ap-southeast-1`  
**Account:** `629380420098`  
**API URL:** `https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod/`

**Change Set Changes:**
1. Modify `PolicyAssistantApi` (AWS::ApiGatewayV2::Api) — no replacement
2. Add `PolicyAssistantFunctionHealthCheckPermission` (AWS::Lambda::Permission)
3. Modify `PolicyAssistantFunction` (AWS::Lambda::Function) — no replacement

**DynamoDB Table:** Not in change set — no replacement or data loss.

**Post-Deployment API Verification:**

| Test | Request | HTTP Status | Result |
|------|---------|-------------|--------|
| Health check | `GET /health` | 200 | `{"status": "healthy"}` |
| Policy lookup | `GET /policies/POL-001` | 200 | Policy object, internal fields stripped |
| Missing policy | `GET /policies/POL-999` | 404 | `{"error": "Not found", ...}` |
| Keyword search | `GET /policies?keyword=refund` | 200 | `{"policies": [...], "count": 1, "scanned_count": 3, "truncated": false}` |

**Note:** These deployment results are from a previously reported deployment session and were not independently re-verified during this documentation phase. The repository does not contain CI/CD pipeline output or dated deployment records.

## 13. Operational and Cost Considerations

### Operational Considerations

- **Logging:** CloudWatch Logs with JSON format, 30-day retention
- **Monitoring:** No CloudWatch Alarms or dashboards configured
- **Health Check:** `/health` endpoint verifies Lambda availability only, not DynamoDB connectivity
- **Error Handling:** All exceptions caught and returned as 500 with generic message (no stack trace leakage)
- **Retries:** Lambda retries handled by AWS Lambda service
- **Deployment:** Manual via `sam deploy --guided`; no CI/CD pipeline

### Cost Considerations

| Service | Pricing Model | Notes |
|---------|---------------|-------|
| AWS Lambda | Pay per request + GB-seconds | 1M free requests/month |
| API Gateway HTTP API | Pay per request | 1M free requests/month |
| DynamoDB | On-demand (PAY_PER_REQUEST) | 25 GB free storage, 25 WCU/RCU |
| CloudWatch Logs | Pay per GB ingested/stored | 5 GB free ingestion |

**No specific cost figures are provided.** Actual monthly costs depend on request volume, data size, and usage patterns. Use the AWS Pricing Calculator to estimate costs for your expected workload.

### Cost Optimization Notes
- DynamoDB on-demand billing: No capacity planning needed
- No NAT Gateway, EC2, RDS, or X-Ray — minimal infrastructure
- HTTP API is cheaper than REST API
- CloudWatch Logs JSON format enables efficient querying
- Search uses DynamoDB Scan (suitable for small MVP datasets only; not for production at scale)

## 14. Limitations and Lessons Learned

### Limitations

1. **Keyword Search uses DynamoDB Scan:** Scans entire table (max 1 MB per request). Suitable for MVP with small dataset (< 100 policies). Not suitable for production at scale.
2. **No Authentication/Authorization:** API is publicly accessible. Add API keys, Cognito, or Lambda authorizers for production.
3. **CORS Limited to Localhost:** Configured for `http://localhost:3000` and `http://127.0.0.1:3000`. Requires customer input for production domain.
4. **No Custom Domain/SSL:** Uses default API Gateway domain.
5. **Health Check is Liveness Only:** Does not verify DynamoDB connectivity.
6. **No AI/ML Capabilities:** No Amazon Bedrock, RAG, embeddings, or vector search.
7. **No CI/CD Pipeline:** Deployment is manual via `sam deploy --guided`.
8. **No Frontend:** API-only; no HTML/CSS/JS frontend files in repository.

### Lessons Learned

- DynamoDB Scan is simple but does not scale; consider GSI or OpenSearch for production
- Internal fields (`*_lower`) must be explicitly stripped from client responses
- Scan budget (1,000 items) provides read capacity protection but does not replace proper indexing
- Health check should not be confused with readiness check (does not verify DynamoDB)
- CORS origins must be configured for production domains before deployment

## 15. Future Improvements

| Improvement | Status | Priority |
|-------------|--------|----------|
| Authentication (Cognito or API keys) | Not implemented | High (production) |
| Frontend user interface | Not implemented | Medium |
| Cursor-based pagination (`next_token`) | Not implemented | Medium |
| GSI for category-based filtering | Not implemented | Medium |
| OpenSearch for full-text search | Not implemented | Low |
| CloudWatch Alarms and dashboards | Not implemented | Medium |
| X-Ray tracing | Not implemented | Low |
| CI/CD pipeline | Not implemented | Medium |
| Production CORS domain | Not implemented | High (production) |
| Amazon Bedrock / RAG | Not implemented | Low (future consideration) |

## 16. Conclusion

Policy Assistant is a serverless MVP for policy retrieval and keyword search. It provides a simple, cost-effective API for looking up organizational policies using AWS serverless services. The application has been tested locally (43 unit tests) and against the deployed API (9 integration tests). While suitable for MVP use with small datasets, it requires additional security, monitoring, and scaling improvements before production use.

---

**Documentation Status:** This report reflects the repository state as of the documentation phase. AWS deployment results are from a previously reported deployment session and are labeled as such. No AWS resources were created, modified, or deleted during this documentation phase.