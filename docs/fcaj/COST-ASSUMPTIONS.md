# COST input worksheet — not a completed estimate

Use [AWS Pricing Calculator](https://calculator.aws/) and current official service pricing. Supply the dated share link/export and the selected regions. No dollar-rate totals or Calculator artifact are fabricated here.

| Item | Planning input / evidence |
|---|---|
| Geography | Stack, storage and OCR in Singapore. Global Claude Haiku 5.5 called from Singapore. |
| Upload attempts |300/month global,5/day/user;10MiB/file, bounded text/OCR pages |
| AI attempts | 2,000/month globally, 20/day per user. Measure input and output tokens for Haiku 5.5. |
| Support |200 creates/month; bounded messages/retention; measure actual active records |
| Feedback |5000 mutation reservations/month,50/day/user; aggregate updates are transactional |
| Lambda/API | Request volume, durations, memory/concurrency per function from template/CloudWatch; include failed/duplicate work |
| DynamoDB | Metadata/history/support/audit/quota/quality storage, transactional RCU/WCU, indexes, PITR and TTL delay |
| S3/CloudFront | Sources, versions, quarantine, extracted text, frontend/fonts, PUT/GET and download/edge transfer |
| OCR | Count actual scanned pages and jobs. |
| Observability/identity | CloudWatch logs/alarms/dashboard, SNS, Cognito active users/email behavior, budget notifications |

## Proposed scenario for student review — not measured or approved usage

| Input | Proposed quantity and interpretation |
|---|---|
| Active users |50 MAU |
| Documents |100 PDFs/month,2MiB each,10pages each |
| OCR fraction |20% of pages →200pages/month |
| Generation |1000attempts/month;8000input and2500output/reasoning tokens/attempt as planning headroom |
| Quota sensitivity |Repeat at2000AIattempts and300uploads/month with variable OCR fraction |
| Storage |Accumulate retained source/extraction versions; monthly ingress is not retained total |
| Other dimensions |Measure or explicitly assume API traffic/durations, transfer, logs, transactional capacity and retained support/audit data in Calculator |

Haiku 5.5 requests cap output at 900 tokens. Use Singapore source-region Global profile rates when creating an estimate. Include OCR, storage/PITR, requests, logs and taxes as applicable.

The30–50 USD target and50 USD account budget are planning/alerts, not a hard cap or proof of actual cost. Cost optimization choices include bounded retrieval, local keyword ranking, narrow parser role, lifecycle/retention and no automatic generation retries. Monthly aggregate contention is bounded/retried separately from generation. Revisit these choices after real workload measurements.

Calculator link/export: **not yet supplied**. Fresh-account cost validation: **not yet performed**. Student review is required before describing COST as complete in the workshop.
