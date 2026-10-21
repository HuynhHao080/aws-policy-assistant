# AI Policy Assistant MVP

A serverless application for policy retrieval and keyword search, built with AWS SAM, Python 3.12, API Gateway HTTP API, and DynamoDB.

## Architecture

- **Region**: `ap-southeast-1`
- **Runtime**: Python 3.12
- **API**: API Gateway HTTP API (v2)
- **Database**: DynamoDB (`PolicyAssistantPolicies` table, on-demand billing)
- **Compute**: AWS Lambda
- **Logging**: CloudWatch Logs (JSON format)
- **Frontend**: None (API-only; no frontend files in repository)
- **Authentication**: Cognito User Pool + API Gateway JWT Authorizer configured in `template.yaml` (not deployed)

## Features

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/policies/{policy_id}` | GET | Retrieve a policy by exact ID |
| `/policies` | GET | Case-insensitive keyword search across title, category, content, and keywords |
| `/policies?keyword=xxx&limit=N` | GET | Case-insensitive keyword search with optional result limit (max 100) and per-request scan budget |
| `/policies?keyword=xxx&limit=N&next_token=xxx` | GET | Case-insensitive keyword search with cursor-based pagination using `next_token` from previous page |
| `/health` | GET | Lightweight liveness check (Lambda availability only; does not verify DynamoDB connectivity) | Authentication: Public

### Response Format

**Success (200):**
```json
// GET /policies/POL-001
{
  "policy_id": "POL-001",
  "title": "Customer Refund Policy",
  "category": "Customer Service",
  "content": "...",
  "keywords": ["refund", "return", "customer", ...]
}

// GET /policies?keyword=refund
{
  "policies": [...],
  "count": 1,
  "scanned_count": 3,
  "truncated": false
}

// GET /policies?keyword=legal&limit=1
{
  "policies": [...],
  "count": 1,
  "scanned_count": 3,
  "truncated": false
}

// Budget exhausted before enough matches found
{
  "policies": [...],
  "count": 5,
  "scanned_count": 1000,
  "truncated": true
}

// GET /health
{
  "status": "healthy"
}
```

**Response fields:**
- `policies`: List of matching policy objects (internal `*_lower` fields stripped)
- `count`: Number of policies returned in this response
- `scanned_count`: Total number of items DynamoDB evaluated across all Scan pages
- `truncated`: `true` if the per-request scan budget was exhausted before all matching items were found; results may be incomplete

**Error Responses:**
- `400 Bad Request` - Missing or invalid parameters (including invalid `limit`)
- `404 Not Found` - Policy not found or invalid endpoint
- `405 Method Not Allowed` - Only GET supported
- `500 Internal Server Error` - Unexpected errors or DynamoDB failures

## Project Structure

```
policy-assistant/
├── template.yaml              # SAM template (infrastructure)
├── samconfig.toml             # SAM CLI configuration
├── policy_assistant/
│   ├── app.py                 # Lambda handler
│   └── requirements.txt       # Python dependencies
├── sample_data/
│   └── policies.json          # Sample policy records (3 policies)
├── tests/
│   ├── requirements.txt       # Test dependencies
│   ├── unit/
│   │   └── test_handler.py    # Unit tests (mocked DynamoDB)
│   └── integration/
│       └── test_api_gateway.py # Integration tests (requires deployment)
└── README.md                  # This file

> Architecture diagrams are in `architecture.mmd` and `architecture.png`.
> Additional documentation is available in the `docs/` directory:
> - `docs/internship-report.md` — Full internship report
> - `docs/evidence-index.md` — Evidence index and verification status
```

## Documentation

Architecture diagrams are available as:
- `architecture.mmd` — Mermaid flowchart source
- `architecture.png` — Rendered diagram

## Prerequisites

- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) >= 1.100
- [Python 3.12](https://www.python.org/downloads/)
- [Docker](https://www.docker.com/) (for `sam build --use-container` and `sam local`)
- AWS CLI configured (for deployment)

## Local Development

### 1. Install Dependencies

```bash
# Lambda dependencies
cd policy-assistant/policy_assistant
pip install -r requirements.txt -t .

# Test dependencies
cd ../tests
pip install -r requirements.txt
```

### 2. Validate Template

```bash
cd policy-assistant
sam.cmd validate --lint
```

### 3. Build Application

```bash
sam.cmd build
```

### 4. Run Unit Tests

```bash
# From policy-assistant directory
python -m pytest tests/unit -v
```

Expected output: All tests pass with mocked DynamoDB (no AWS credentials needed).

### 5. Start Local API

```bash
sam local start-api --port 3000
```

The API will be available at `http://localhost:3000`.

#### Test Endpoints Locally

```bash
# Get policy by ID
curl http://localhost:3000/policies/POL-001

# Search policies by keyword
curl "http://localhost:3000/policies?keyword=refund"
curl "http://localhost:3000/policies?keyword=privacy"
curl "http://localhost:3000/policies?keyword=legal"

# Test error cases
curl http://localhost:3000/policies/POL-999        # 404
curl "http://localhost:3000/policies?keyword="    # 400
curl -X POST http://localhost:3000/policies/POL-001 # 405
```

### 6. Invoke Lambda Directly

```bash
# Get policy by ID
sam local invoke PolicyAssistantFunction --event events/get_policy.json

# Search policies
sam local invoke PolicyAssistantFunction --event events/search_policies.json
```

Create test events in `events/` directory following the API Gateway HTTP API v2 format.

## Sample Data

Three fictional policies are included in `sample_data/policies.json`:

1. **POL-001** - Customer Refund Policy (Customer Service)
2. **POL-002** - Privacy Policy (Legal)
3. **POL-003** - Terms of Service (Legal)

### Load Sample Data into Local DynamoDB (for `sam local`)

```bash
# Start local DynamoDB
docker run -d -p 8000:8000 amazon/dynamodb-local

# Create table and load data
aws dynamodb create-table \
  --table-name PolicyAssistantPolicies \
  --attribute-definitions AttributeName=policy_id,AttributeType=S \
  --key-schema AttributeName=policy_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --endpoint-url http://localhost:8000 \
  --region ap-southeast-1

# Load sample policies
for policy in $(cat sample_data/policies.json | jq -c '.[]'); do
  aws dynamodb put-item \
    --table-name PolicyAssistantPolicies \
    --item "$policy" \
    --endpoint-url http://localhost:8000 \
    --region ap-southeast-1
done
```

Then run `sam local start-api --docker-network host` to connect to local DynamoDB.

## Deployment

### 1. Deploy to AWS

```bash
sam deploy --guided
```

Follow the prompts:
- Stack Name: `policy-assistant`
- AWS Region: `ap-southeast-1`
- Confirm changes: `y`
- Allow SAM CLI IAM role creation: `y`
- Save to samconfig.toml: `y`

### 2. Verify Deployment

```bash
# Get API URL from stack outputs
aws cloudformation describe-stacks
  --stack-name policy-assistant
  --query "Stacks[0].Outputs[?OutputKey=='PolicyAssistantApiUrl'].OutputValue"
  --output text
```

**Deployed API URL:** `https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod/`

### 3. Load Sample Data into Production DynamoDB

```bash
for policy in $(cat sample_data/policies.json | jq -c '.[]'); do
  aws dynamodb put-item
    --table-name PolicyAssistantPolicies
    --item "$policy"
    --region ap-southeast-1
done
```

Or using Python:
```bash
python -c "
import json, boto3
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
table = dynamodb.Table('PolicyAssistantPolicies')
with open('sample_data/policies.json') as f:
    for policy in json.load(f):
        table.put_item(Item=policy)
        print(f'Loaded: {policy[\"policy_id\"]}')
"
```

### 4. Test Deployed API

```bash
API_URL="https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod"

# Get policy by ID
curl "$API_URL/policies/POL-001"

# Search policies
curl "$API_URL/policies?keyword=refund"
```

## Deployed API Test Results

The Policy Assistant stack was deployed to AWS CloudFormation in region `ap-southeast-1` (stack name: `policy-assistant`, status: `UPDATE_COMPLETE`). Integration tests were executed against the live deployed API at `https://ctgt5w6emf.execute-api.ap-southeast-1.amazonaws.com/Prod/`.

### Integration Test Results (Live API)

All 9 integration tests passed against the deployed API:

| Test | Endpoint | Status |
|------|----------|--------|
| Get existing policy | `GET /policies/POL-001` | 200 PASS |
| Get non-existent policy | `GET /policies/POL-999` | 404 PASS |
| Search matching keyword | `GET /policies?keyword=refund` | 200 PASS |
| Search case-insensitive | `GET /policies?keyword=REFUND` | 200 PASS |
| Search no matches | `GET /policies?keyword=nonexistentkeyword123` | 200 PASS |
| Search missing keyword | `GET /policies` | 400 PASS |
| Search empty keyword | `GET /policies?keyword=` | 400 PASS |
| CORS preflight | `OPTIONS /policies/POL-001` | 204 PASS |
| Invalid method | `POST /policies/POL-001` | 404 PASS |

Integration tests require a deployed stack and `AWS_SAM_STACK_NAME` environment variable:

```bash
export AWS_SAM_STACK_NAME=policy-assistant
export AWS_DEFAULT_REGION=ap-southeast-1
python -m pytest tests/integration -v
```

### Unit Test Results

All 43 unit tests pass (mocked DynamoDB, no AWS credentials required):

```bash
python -m pytest tests/unit -v --tb=short
```

```
============================= 43 passed ==============================
```

## Cost Considerations

| Resource | Pricing Model |
|----------|---------------|
| Lambda | Pay per request + GB-seconds |
| API Gateway HTTP API | Pay per request |
| DynamoDB | On-demand (PAY_PER_REQUEST) |
| CloudWatch Logs | Pay per GB ingested/stored |

**No specific cost figures are provided.** Actual monthly costs depend on request volume, data size, and usage patterns. Use the AWS Pricing Calculator to estimate costs for your expected workload.

### Cost Optimization Notes

- DynamoDB on-demand billing: No capacity planning needed, pay only for what you use
- No NAT Gateway, EC2, RDS, or X-Ray - minimal infrastructure
- HTTP API is cheaper than REST API
- CloudWatch Logs JSON format enables efficient querying
- Search uses DynamoDB Scan (suitable for small MVP datasets only; not for production at scale)

## Cleanup

To delete all AWS resources created by this stack:

```bash
sam delete --stack-name policy-assistant --region ap-southeast-1
```

Or via AWS Console: CloudFormation → Stacks → policy-assistant → Delete

## Known Limitations

1. **Keyword Search uses DynamoDB Scan**
   - Scans entire table (max 1 MB per request)
   - Pagination handled in code via `LastEvaluatedKey`
   - Optional `limit` parameter caps returned results (max 100)
   - Per-request scan budget of 1,000 evaluated items bounds read capacity consumption
   - When the scan budget is exhausted, `truncated` is `true` and results may be incomplete
   - Suitable for MVP with small dataset (< 100 policies)
   - **Not suitable for production at scale**
   - Production alternatives: Global Secondary Index (GSI) with `begins_with`, OpenSearch, or dedicated search service

2. **Case-Insensitive Search**
   - Implemented by storing lowercase keywords and using `contains` on lowercase fields
   - Internal lowercase fields (`title_lower`, `category_lower`, `content_lower`, `keywords_lower`) are stripped from client responses
   - For true case-insensitive search at scale, consider storing normalized (lowercase) copies of searchable fields

3. **No Authentication/Authorization**
   - Cognito User Pool and API Gateway JWT Authorizer are configured in `template.yaml` but NOT deployed. Policy routes require a valid JWT; `/health` remains public. A Cognito User Pool and client must be deployed and configured before live authentication can work.

3. **No Request Validation at API Gateway Level**
   - HTTP API (`AWS::Serverless::HttpApi`) does not support `RequestParameters` / JSON Schema request models (REST API feature); `keyword` and `limit` validation remains authoritative in Lambda.
   - Lambda validates `keyword` (required, non-empty), `limit` (positive integer ≤100), and `next_token` format.
4. **Least-Privilege IAM Verified**
   - Lambda IAM grants only `dynamodb:GetItem` and `dynamodb:Scan` on `!GetAtt PoliciesTable.Arn`; no wildcard actions or unnecessary DynamoDB permissions.

5. **CORS Limited to Localhost**
   - Configured for `http://localhost:3000` and `http://127.0.0.1:3000`
   - **Requires customer input**: Replace with production frontend domain in `template.yaml` before deployment

6. **No Custom Domain / SSL**
   - Uses default API Gateway domain; configure custom domain for production

7. **Health Check Scope**
   - `/health` is a lightweight liveness check that verifies Lambda handler availability only
   - Does NOT verify DynamoDB connectivity or any downstream dependency
   - CloudWatch Alarms and Dashboard are defined locally but NOT deployed
   - CloudWatch Alarms: Lambda Errors > 0 and Lambda Duration > 5000ms
   - CloudWatch Dashboard: Lambda metrics (Invocations, Errors, Duration, Throttles)

8. **No AI/ML Capabilities**
   - No Amazon Bedrock, RAG, embeddings, or vector search
   - These are evaluated as potential future enhancements only

## Extending the MVP

### Add New Policy Fields
1. Update `sample_data/policies.json`
2. No schema migration needed (DynamoDB is schemaless)
3. Update Lambda handler if new fields need special handling

### Add Pagination with Next Token
The current `limit` parameter caps results but does not support `next_token` for cursor-based pagination. Add `LastEvaluatedKey` passthrough for client-side pagination.

### Add Policy Creation/Update Endpoints
1. Add POST/PUT routes in `template.yaml`
2. Add `dynamodb:PutItem`/`UpdateItem` permissions to Lambda policy
3. Implement handlers in `app.py`

### Improve Search Performance
1. Add GSI on `category` for category-based filtering
2. Use OpenSearch for full-text search
3. Pre-compute search vectors for semantic search

### Add Authentication
1. Add Amazon Cognito user pool or API Gateway API keys
2. Add Lambda authorizer for custom auth
3. Update IAM policies accordingly

## Troubleshooting

### `sam build` fails
- Ensure Docker is running
- Check Python 3.12 is available
- Try `sam build` without `--use-container` if local Python matches

### `sam local start-api` can't connect to DynamoDB
- Use `--docker-network host` on Linux
- On Windows/Mac, use `host.docker.internal:8000` as endpoint
- Or deploy to AWS and test against real DynamoDB

### Unit tests fail with import errors
- Run from `policy-assistant` directory: `python -m pytest tests/unit -v`
- Ensure test dependencies installed: `pip install -r tests/requirements.txt`

### Deployment fails with IAM errors
- Ensure `CAPABILITY_IAM` is enabled (default in `samconfig.toml`)
- Check AWS credentials have CloudFormation/IAM/Lambda/APIGateway/DynamoDB permissions
- Replace CORS localhost origins with your production domain in `template.yaml` before deploying

## License

MIT License - Feel free to use for learning or production.

## Verification Status

| Item | Status | Evidence |
|------|--------|----------|
| Unit tests (62) | Locally tested, PASSED | `python -m pytest tests/unit -v --tb=short` |
| Integration tests (9) | Live API tested, PASSED | `python -m pytest tests/integration -v` against deployed stack |
| Cognito auth config | Template-tested, PASSED | `TestCognitoAuthorization` class in `tests/unit/test_handler.py` |
| Lambda handler | Code reviewed | `policy_assistant/app.py` |
| SAM template | Code reviewed | `template.yaml` |
| SAM CLI validation | Available as `sam.cmd` | `sam.cmd validate --lint` has a pre-existing transform error with JWT authorizer (SAM CLI 1.168.0); `sam.cmd build` succeeds |
| SAM CLI build | Available as `sam.cmd` | `sam.cmd build` succeeded |
| AWS deployment | Deployed to `ap-southeast-1` | Stack `policy-assistant`, status `UPDATE_COMPLETE` (verified 2026-10-19) |
| Production cost | Not estimated | Usage inputs unavailable |
| Production cost | Not estimated | Usage inputs unavailable |