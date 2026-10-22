# AWS Policy Assistant — test demo handover

Policy lookup/search and owner-isolated PDF byte/hash verification. Cognito, HTTP API, Lambda, DynamoDB, S3/CloudFront, SQS/DLQ, EventBridge and CloudWatch/SNS; no AI/RAG/OCR.

B4 API/SDK19PASS; original B5 browserFAIL retained; B5-R6 API-only UPDATE_COMPLETE; B5-R7 browser10PASS. C0 inventories45resources/4Retain. GO bounded test demo, NO-GO production. D1 is local review, not a fresh AWS health check.

Open: DLQ approximately1/ALARM; SNS0subscriptions; Budget20USD account alerts/email delivery unverified; old Git HEAD password literals with rotation not evidenced; cleanup/commit/push not authorized. Environment end date not set by owner.

Local baseline129backend/17frontend/3browserfixtures/1fullstack; R4 added one private mixed-version case (130in that run). Local results do not replace AWS proof. Current source SAM shares CodeUri; deployed API has new ZIP, Worker/Recovery old ZIP. Generic deploy may broaden updates.

See README.md, docs/d1-handover-review.md, docs/demo-script.md. Offline: python -m scripts.demo_server. No live scripts authorized in D1.
