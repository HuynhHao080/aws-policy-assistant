# Policy Assistant — AWS Upgrade Roadmap

This document outlines a prioritized, incremental upgrade path for the Policy Assistant serverless MVP, based on the AWS Cloud Journey learning materials (https://cloudjourney.awsstudygroup.com/). Every proposed change addresses a real requirement, integrates with the existing application, includes tests, and is documented.

## Current Baseline (Verified)

| Component | Technology | Status |
|-----------|------------|--------|
| Compute | AWS Lambda (Python 3.12) | Deployed |
| API | Amazon API Gateway HTTP API (v2), Stage: Prod | Deployed |
| Database | Amazon DynamoDB, table `PolicyAssistantPolicies`, PK: `policy_id`, PAY_PER_REQUEST | Deployed |
| Logging | Amazon CloudWatch Logs, JSON format, 30-day retention | Deployed |
| IAM | Lambda execution role: `dynamodb:GetItem`, `dynamodb:Scan` on table ARN only | Deployed |
| CORS | `http://localhost:3000`, `http://127.0.0.1:3000` | Deployed |
| IaC | AWS SAM (`template.yaml`, `samconfig.toml`) | Defined locally |
| Tests | 43 unit tests (moto), 9 integration tests (live API) | Verified |
| Frontend | None (API-only) | Not implemented |
| Authentication | None (public API) | Not implemented |
| CI/CD | None (manual `sam deploy`) | Not implemented |
| Monitoring | CloudWatch Logs only; no alarms, no dashboard, no X-Ray | Not implemented |
| AI/ML | None (keyword search only) | Not implemented |

## Roadmap Ranking

The roadmap is ranked into four tiers:

1. **Tier 1 — Essential Security and Reliability** (highest priority, lowest risk)
2. **Tier 2 — Core Application Features**
3. **Tier 3 — DevOps and Frontend**
4. **Tier 4 — Optional AI and Advanced Architecture**

---

## Tier 1 — Essential Security and Reliability

These changes address the most critical gaps: lack of authentication, lack of monitoring/alarms, and lack of automated deployment safety.

### 1.1 — Amazon Cognito User Pool + API Gateway JWT Authorizer

**Cloud Journey Reference:** https://cloudjourney.awsstudygroup.com/vi/1-explore/ (IAM, authentication)

**Purpose:** The API is currently public with no authentication. Any caller can read all policies. Adding Cognito provides user identity and access control.

**AWS Services:**
- Amazon Cognito User Pool
- Amazon API Gateway JWT Authorizer
- AWS IAM (existing role, may need update)

**Architecture:**
```
Client --> Cognito (sign-in, get JWT) --> API Gateway (JWT Authorizer validates) --> Lambda --> DynamoDB
```

**Files to Change:**
- `template.yaml` — Add Cognito User Pool, User Pool Client, API Gateway Authorizer, update Lambda event to include authorizer
- `policy_assistant/app.py` — Validate JWT claims, extract user context
- `tests/unit/test_handler.py` — Add tests for authenticated vs unauthenticated requests
- `README.md` — Document authentication flow

**Security Implications:**
- API no longer publicly accessible without a valid JWT
- IAM role remains least-privilege (DynamoDB only)
- Cognito handles user storage and password policies

**Estimated Cost Drivers:**
- Amazon Cognito: First 50,000 MAU free, then ~$0.0055 per MAU
- No additional Lambda or API Gateway cost

**Test Strategy:**
- Unit tests: Verify JWT validation, missing token returns 401, invalid token returns 401
- Integration tests: Sign-in flow, authenticated request, unauthenticated request

**Rollback Strategy:**
- Remove Authorizer from API Gateway routes, remove Cognito resources from template

**Dependencies:** None (standalone)

**Acceptance Criteria:**
- Unauthenticated requests return 401
- Authenticated requests with valid JWT return 200
- Cognito User Pool created in `ap-southeast-1`

---

### 1.2 — CloudWatch Alarms and Dashboard

**Cloud Journey Reference:** https://cloudjourney.awsstudygroup.com/vi/3-optimize/ (observability, monitoring)

**Purpose:** Currently only CloudWatch Logs exists. No alarms or dashboard means no visibility into errors, latency, or throttling.

**AWS Services:**
- Amazon CloudWatch Alarms
- Amazon CloudWatch Dashboard

**Architecture:**
```
Lambda --> CloudWatch Logs --> CloudWatch Metrics --> CloudWatch Alarms --> SNS (optional)
Lambda --> CloudWatch Dashboard
```

**Files to Change:**
- `template.yaml` — Add CloudWatch Alarm resources, CloudWatch Dashboard resource, SNS topic (optional)
- `README.md` — Document alarm thresholds and dashboard

**Security Implications:**
- None (read-only monitoring)

**Estimated Cost Drivers:**
- CloudWatch Alarms: ~$0.10 per alarm per month
- CloudWatch Dashboard: ~$3.00 per dashboard per month
- CloudWatch Logs: Existing, no change

**Test Strategy:**
- Unit tests: Verify alarm thresholds are defined in template
- No live testing required (alarms are passive)

**Rollback Strategy:**
- Delete CloudWatch Alarm and Dashboard resources from template

**Dependencies:** None

**Acceptance Criteria:**
- Alarm on Lambda Errors > 0 for 5 minutes
- Alarm on Lambda Duration > 5 seconds for 5 minutes
- Dashboard displays Lambda invocations, errors, duration

---

### 1.3 — AWS X-Ray Tracing

**Cloud Journey Reference:** https://cloudjourney.awsstudygroup.com/vi/4-modernize/ (observability)

**Purpose:** Add distributed tracing to identify latency issues in the Lambda → DynamoDB path.

**AWS Services:**
- AWS X-Ray

**Files to Change:**
- `template.yaml` — Add X-Ray tracing to Lambda function
- `policy_assistant/app.py` — Add X-Ray SDK instrumentation (optional, for sub-segments)

**Security Implications:**
- None

**Estimated Cost Drivers:**
- AWS X-Ray: First 100,000 traces free, then ~$5.00 per 1 million traces

**Test Strategy:**
- Unit tests: Verify X-Ray header propagation (if implemented)
- No live testing required

**Rollback Strategy:**
- Remove TracingConfig from Lambda, remove X-Ray SDK code

**Dependencies:** None

**Acceptance Criteria:**
- Lambda has TracingConfig set to Active
- X-Ray service map shows Lambda → DynamoDB

---

## Tier 2 — Core Application Features

These changes add functionality that directly improves the policy assistant use case.

### 2.1 — DynamoDB Global Secondary Index (GSI) for Category-Based Search

**Cloud Journey Reference:** https://cloudjourney.awsstudygroup.com/vi/1-explore/ (DynamoDB)

**Purpose:** Current keyword search uses DynamoDB Scan, which reads the entire table. A GSI on `category` enables efficient category-based queries without scanning.

**AWS Services:**
- Amazon DynamoDB (GSI addition)

**Files to Change:**
- `template.yaml` — Add GSI on `category` attribute
- `policy_assistant/app.py` — Add `GET /policies?category=xxx` endpoint using Query instead of Scan
- `tests/unit/test_handler.py` — Add tests for category query
- `README.md` — Document new endpoint

**Security Implications:**
- None (read-only query)

**Estimated Cost Drivers:**
- DynamoDB: GSI storage and write capacity (on-demand: pay per write request)

**Test Strategy:**
- Unit tests: Query by category returns correct policies, empty category returns empty list
- Integration tests: Verify category query against deployed API

**Rollback Strategy:**
- Remove GSI from template, remove category endpoint from code

**Dependencies:** None

**Acceptance Criteria:**
- `GET /policies?category=Legal` returns POL-002 and POL-003
- `GET /policies?category=NonExistent` returns empty list
- GSI created and active

---

### 2.2 — Cursor-Based Pagination (`next_token`)

**Cloud Journey Reference:** https://cloudjourney.awsstudygroup.com/vi/1-explore/ (DynamoDB)

**Purpose:** Current `limit` parameter caps results but provides no way to fetch the next page. Adding `LastEvaluatedKey` passthrough enables cursor-based pagination.

**AWS Services:**
- Amazon DynamoDB (existing, no new resources)

**Files to Change:**
- `policy_assistant/app.py` — Accept `next_token` parameter, pass `ExclusiveStartKey`, return `next_token` in response
- `tests/unit/test_handler.py` — Add tests for pagination
- `README.md` — Document pagination

**Security Implications:**
- None

**Estimated Cost Drivers:**
- None (uses existing DynamoDB Scan)

**Test Strategy:**
- Unit tests: Verify next_token returned when more items exist, verify next page returns remaining items

**Rollback Strategy:**
- Remove next_token logic from code

**Dependencies:** None

**Acceptance Criteria:**
- Search with limit=1 returns next_token
- Search with next_token returns remaining items
- Search with next_token=null returns first page

---

## Tier 3 — DevOps and Frontend

These changes improve deployment automation and add a user interface.

### 3.1 — CI/CD Pipeline (GitHub Actions or AWS CodePipeline)

**Cloud Journey Reference:** https://cloudjourney.awsstudygroup.com/vi/4-modernize/ (CI/CD)

**Purpose:** Current deployment is manual (`sam deploy --guided`). A CI/CD pipeline automates testing and deployment with safeguards.

**AWS Services:**
- AWS CodePipeline, AWS CodeBuild, AWS CodeDeploy (AWS-native)
- OR GitHub Actions (if GitHub repository)

**Files to Change:**
- `.github/workflows/deploy.yml` (if GitHub Actions) OR `buildspec.yml` + `template.yaml` additions (if CodePipeline)
- `template.yaml` — May need IAM role for CodeBuild/CodeDeploy

**Security Implications:**
- CI/CD requires AWS credentials; must use secure secret storage (GitHub Secrets or AWS Secrets Manager)
- Never hardcode credentials

**Estimated Cost Drivers:**
- CodeBuild: ~$0.005 per build minute
- CodePipeline: $1.00 per active pipeline per month
- GitHub Actions: Free for public repos, limited free minutes for private

**Test Strategy:**
- Unit tests run in pipeline before deploy
- Integration tests run against deployed stack after deploy

**Rollback Strategy:**
- CodePipeline automatic rollback on failure
- Manual `sam delete` if needed

**Dependencies:** GitHub repository (for GitHub Actions) or AWS account (for CodePipeline)

**Acceptance Criteria:**
- Pipeline runs unit tests on every push
- Pipeline deploys to staging on merge to main
- Pipeline deploys to production on tag/release

---

### 3.2 — Static Frontend (S3 + CloudFront)

**Cloud Journey Reference:** https://cloudjourney.awsstudygroup.com/vi/4-modernize/ (serverless frontend)

**Purpose:** Currently API-only. A simple web UI makes the assistant usable by non-technical users.

**AWS Services:**
- Amazon S3 (static website hosting)
- Amazon CloudFront (CDN, SSL, origin access control)
- Amazon Cognito (if authentication added)

**Architecture:**
```
User --> CloudFront --> S3 (static website) --> API Gateway --> Lambda --> DynamoDB
```

**Files to Change:**
- New `frontend/` directory with HTML/CSS/JS
- `template.yaml` — Add S3 bucket, CloudFront distribution, Origin Access Control
- `README.md` — Document frontend deployment

**Security Implications:**
- S3 bucket must NOT be publicly readable; use CloudFront Origin Access Control
- CORS must be updated to include production frontend domain

**Estimated Cost Drivers:**
- S3: Negligible for static site
- CloudFront: First 1 TB free, then ~$0.085 per GB

**Test Strategy:**
- Unit tests: None (frontend is static)
- Manual testing: Verify frontend loads and calls API

**Rollback Strategy:**
- Delete S3 bucket and CloudFront distribution

**Dependencies:** Cognito (if authentication added), production domain (optional)

**Acceptance Criteria:**
- Frontend loads and displays policy list
- Frontend can search policies via API
- S3 bucket is not publicly readable

---

## Tier 4 — Optional AI and Advanced Architecture

These are optional enhancements that should only be implemented if a clear business need exists.

### 4.1 — Amazon Bedrock / RAG for AI-Assisted Question Answering

**Cloud Journey Reference:** https://cloudjourney.awsstudygroup.com/vi/7-aimlservice/ (AI/ML)

**Purpose:** Allow users to ask natural-language questions about policies and receive answers with source citations.

**AWS Services:**
- Amazon Bedrock (foundation models)
- Amazon S3 (document storage)
- Amazon OpenSearch Serverless (vector index, optional)

**Architecture:**
```
User Question --> Lambda --> Bedrock (embedding) --> OpenSearch (vector search) --> Bedrock (generation with citations) --> User
```

**Files to Change:**
- `policy_assistant/app.py` — Add `/ask` endpoint
- `template.yaml` — Add Bedrock permissions, S3 bucket, OpenSearch (optional)
- `tests/unit/test_handler.py` — Add tests for question answering

**Security Implications:**
- **CRITICAL:** Do not send sensitive policy content to Bedrock without explicit approval
- Model invocation costs can be significant
- Vector embeddings of policy content stored in OpenSearch

**Estimated Cost Drivers:**
- Amazon Bedrock: Per 1,000 input tokens and per 1,000 output tokens (varies by model)
- Amazon S3: Negligible for document storage
- Amazon OpenSearch Serverless: ~$0.18 per OCU per hour (minimum 1 OCU = ~$130/month)

**Test Strategy:**
- Unit tests: Mock Bedrock responses, verify answer format
- Integration tests: NOT recommended (incurs Bedrock costs)

**Rollback Strategy:**
- Remove `/ask` endpoint, remove Bedrock permissions, delete S3 bucket/OpenSearch

**Dependencies:** None (standalone)

**Acceptance Criteria:**
- User asks natural-language question, receives answer with source citations
- Unsupported questions return polite refusal
- No sensitive data sent to Bedrock without explicit approval

---

### 4.2 — Advanced Services (Evaluate Only if Required)

The following services should **only** be added if a measurable requirement justifies them:

| Service | When to Consider | Why Not Now |
|---------|-----------------|-------------|
| Amazon S3 | Policy document storage (PDFs, etc.) | Current policies are small JSON; no need |
| Amazon Kinesis/SQS | High-volume event processing | Current volume is low; no async workload |
| AWS Step Functions | Multi-step workflows | No complex workflow exists |
| Amazon RDS | Relational data needs | DynamoDB is sufficient for key-value lookups |
| Amazon ElastiCache | High-frequency read caching | DynamoDB on-demand is sufficient for MVP |
| Amazon ECS/EKS | Containerized workloads | Lambda is sufficient |
| AWS Glue/Athena | Data analytics | No analytics requirement |
| Amazon VPC | Network isolation | Lambda + API Gateway is serverless; VPC adds complexity |

---

## Implementation Order (Recommended)

| Phase | Item | Estimated Effort | Dependencies |
|-------|------|-----------------|--------------|
| 1 | CloudWatch Alarms + Dashboard | Low | None |
| 2 | AWS X-Ray Tracing | Low | None |
| 3 | Amazon Cognito + JWT Authorizer | Medium | None |
| 4 | DynamoDB GSI + Category Query | Low | None |
| 5 | Cursor-Based Pagination | Low | None |
| 6 | CI/CD Pipeline | Medium | GitHub repository or AWS account |
| 7 | Static Frontend (S3 + CloudFront) | Medium | Cognito (optional), production domain (optional) |
| 8 | Amazon Bedrock / RAG | High | Explicit approval for AI costs |

## Acceptance Criteria Summary

| Tier | Item | Acceptance Criteria |
|------|------|-------------------|
| 1 | CloudWatch Alarms | Alarm on Lambda Errors > 0, Alarm on Duration > 5s |
| 1 | X-Ray | TracingConfig active, service map shows Lambda → DynamoDB |
| 1 | Cognito + JWT | Unauthenticated returns 401, authenticated returns 200 |
| 2 | DynamoDB GSI | Category query returns correct policies |
| 2 | Pagination | next_token returned when more items exist |
| 3 | CI/CD | Pipeline runs tests on push, deploys on tag |
| 3 | Frontend | S3 bucket not public, CloudFront serves UI |
| 4 | Bedrock RAG | Answers with citations, refuses unsupported questions |

---

## Files to Create/Modify

| File | Change |
|------|--------|
| `docs/aws-upgrade-roadmap.md` | **Create** — This document |
| `docs/architecture-decisions.md` | Create — Record ADRs for each tier |
| `architecture.mmd` | Update — Add Cognito, X-Ray, CloudWatch, GSI, optional Bedrock |
| `README.md` | Update — Document new endpoints, authentication, CI/CD, frontend |
| `template.yaml` | Update — Add Cognito, GSI, CloudWatch, X-Ray, optional Bedrock |
| `policy_assistant/app.py` | Update — Add Cognito validation, category query, pagination, optional Bedrock |
| `tests/unit/test_handler.py` | Update — Add tests for new features |
| `tests/integration/test_api_gateway.py` | Update — Add tests for new endpoints |

---

## Approval Required Before Deployment

The following changes require explicit user approval before any AWS resources are created or modified:

1. **Amazon Cognito** — Incurs monthly cost after free tier
2. **CloudWatch Alarms** — Incurs monthly cost
3. **AWS X-Ray** — Incurs per-trace cost
4. **Amazon S3 + CloudFront** — Incurs storage and data transfer costs
5. **Amazon Bedrock** — Incurs per-token inference costs
6. **CI/CD Pipeline** — CodePipeline incurs $1.00/month per pipeline

**No deployment will be performed without explicit user approval.**

---

## References

- AWS Cloud Journey: https://cloudjourney.awsstudygroup.com/
- AWS SAM Documentation: https://docs.aws.amazon.com/serverless-application-model/
- Amazon Cognito: https://docs.aws.amazon.com/cognito/
- Amazon DynamoDB: https://docs.aws.amazon.com/dynamodb/
- Amazon API Gateway: https://docs.aws.amazon.com/apigateway/
- AWS Lambda: https://docs.aws.amazon.com/lambda/
- Amazon CloudWatch: https://docs.aws.amazon.com/cloudwatch/
- AWS X-Ray: https://docs.aws.amazon.com/xray/
- Amazon Bedrock: https://docs.aws.amazon.com/bedrock/