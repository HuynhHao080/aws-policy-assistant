# Evidence Index — Policy Assistant

This document lists existing evidence relevant to the Policy Assistant project. Each entry records the file path, what it supports, and whether the evidence is current or historical.

## Source Code Evidence

| File | Path | Supports | Status |
|------|------|----------|--------|
| Lambda handler | `policy_assistant/app.py` | API endpoints, search logic, scan budget, health check, error handling, CORS headers, internal field stripping | Current |
| SAM template | `template.yaml` | Infrastructure as code, IAM permissions, API Gateway routes, DynamoDB table definition, CloudWatch Logs | Current |
| SAM config | `samconfig.toml` | Stack name, region, deployment parameters | Current |
| Unit tests | `tests/unit/test_handler.py` | 68 unit tests covering endpoints, error handling, scan budget, pagination, CloudWatch monitoring, Cognito authorization, IAM least-privilege, throttling, correlation logging | Current |
| Integration tests | `tests/integration/test_api_gateway.py` | 9 integration tests against deployed API | Current |
| Sample data | `sample_data/policies.json` | 3 sample policies (POL-001, POL-002, POL-003) | Current |
| Lambda dependencies | `policy_assistant/requirements.txt` | boto3 dependency | Current |
| Test dependencies | `tests/requirements.txt` | pytest, boto3, moto dependencies | Current |

## Test Evidence

| Evidence | Path | Supports | Status |
|----------|------|----------|--------|
| Unit test results | `tests/unit/test_handler.py` | 68 tests pass (mocked DynamoDB); verified by `python -m pytest tests/unit -v --tb=short` | Current — verified during master execution |
| Cognito User Pool | `template.yaml` | JWT issuer for API Gateway authorizer | Local — defined but NOT deployed |
| Test event | `test_event.json` | Sample API Gateway HTTP API v2 event for local invocation | Current |

## Architecture Evidence

| Evidence | Path | Supports | Status |
|----------|------|----------|--------|
| Mermaid diagram | `architecture.mmd` | Client → API Gateway → Lambda → DynamoDB → CloudWatch Logs → IAM flow | Current |
| Rendered diagram | `architecture.png` | Rendered version of architecture.mmd | Current |

## CloudWatch Monitoring Evidence

| Evidence | Path | Supports | Status |
|----------|------|----------|--------|
| CloudWatch Error Alarm | `template.yaml` | Lambda Errors > 0 alarm | Local — defined but NOT deployed |
| CloudWatch Duration Alarm | `template.yaml` | Lambda Duration > 5000ms alarm | Local — defined but NOT deployed |
| CloudWatch Dashboard | `template.yaml` | Lambda metrics dashboard (Invocations, Errors, Duration, Throttles) | Local — defined but NOT deployed |

## Deployment Evidence

| Evidence | Path | Supports | Status |
|----------|------|----------|--------|
| CloudFormation stack | AWS Console / `aws cloudformation describe-stacks` | Stack `policy-assistant`, status `UPDATE_COMPLETE`, region `ap-southeast-1` | Historical — verified during Phase L deployment |
| Stack outputs | AWS Console / `aws cloudformation describe-stacks` | API URL, Lambda ARN, IAM role ARN, table name | Historical — verified during Phase L deployment |
| Stack resources | AWS Console / `aws cloudformation describe-stack-resources` | 9 resources, all CREATE_COMPLETE or UPDATE_COMPLETE | Historical — verified during Phase L deployment |
| Change set | `samcli-deploy1792151046` | 3 changes: Modify API, Add Lambda permission, Modify Lambda code | Historical — created during Phase K, executed during Phase L |

## API Response Evidence

| Evidence | Path | Supports | Status |
|----------|------|----------|--------|
| Health check response | Live API (`GET /health`) | `{"status": "healthy"}` HTTP 200 | Historical — verified during Phase L |
| Policy lookup response | Live API (`GET /policies/POL-001`) | Policy object with internal fields stripped, HTTP 200 | Historical — verified during Phase L |
| Not found response | Live API (`GET /policies/POL-999`) | `{"error": "Not found", ...}` HTTP 404 | Historical — verified during Phase L |
| Search response | Live API (`GET /policies?keyword=refund`) | `{"policies": [...], "count": 1, "scanned_count": 3, "truncated": false}` HTTP 200 | Historical — verified during Phase L |

## Missing Evidence

The following evidence does not exist in the repository:

| Evidence | Needed For | Status |
|----------|------------|--------|
| CI/CD pipeline configuration | Automated deployment verification | Missing — not implemented |
| Deployment pipeline logs | Deployment verification | Missing — not implemented |
| Frontend files | Frontend testing | Missing — not implemented |
| Screenshots | Visual documentation | Missing — not captured |
| Load/performance test results | Performance validation | Missing — not implemented |
| Security/penetration test results | Security validation | Missing — not implemented |
| Cost estimation report | Budget planning | Missing — not created |
| Disaster recovery documentation | Operational readiness | Missing — not created |

## Secrets and Credentials

No secrets, access keys, session tokens, or credentials are stored in the repository. The `.gitignore` file excludes `.env`, `.venv`, and other environment files. AWS credentials are managed externally via `~/.aws/credentials` and are not part of the repository.