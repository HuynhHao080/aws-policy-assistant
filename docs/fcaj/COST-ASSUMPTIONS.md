# COST input worksheet — not a completed estimate

Use [AWS Pricing Calculator](https://calculator.aws/) and current official service pricing. Supply the dated share link/export and the selected regions. No dollar-rate totals or Calculator artifact are fabricated here.

| Item | Planning input / evidence |
|---|---|
| Geography | Stack/storage/embedding/OCR Singapore; Nova2 Lite generation Japan profile with Tokyo/Osaka destinations |
| Upload attempts |300/month global,5/day/user;10MiB/file, bounded text/OCR pages |
| AI attempts |2000/month global,20/day/user; measure generation input/output tokens separately from query/document embeddings |
| Support |200 creates/month; bounded messages/retention; measure actual active records |
| Feedback |5000 mutation reservations/month,50/day/user; aggregate updates are transactional |
| Lambda/API | Request volume, durations, memory/concurrency per function from template/CloudWatch; include failed/duplicate work |
| DynamoDB | Metadata/history/support/audit/quota/quality storage, transactional RCU/WCU, indexes, PITR and TTL delay |
| S3/CloudFront | Sources, versions, quarantine, extraction vectors, frontend/fonts, PUT/GET and download/edge transfer |
| OCR/embedding | Actual scanned pages and chunks; do not assume all uploaded files need OCR or every question generates a model answer |
| Observability/identity | CloudWatch logs/alarms/dashboard, SNS, Cognito active users/email behavior, budget notifications |

## Proposed scenario for student review — not measured or approved usage

| Input | Proposed quantity and interpretation |
|---|---|
| Active users |50 MAU |
| Documents |100 PDFs/month,2MiB each,10pages each |
| OCR fraction |20% of pages →200pages/month |
| Document embeddings |2000chunks/month; measure actual token volume per chunk |
| Query embeddings |1000/month, separate from generation input |
| Generation |1000attempts/month;8000input and2500output/reasoning tokens/attempt as planning headroom |
| Quota sensitivity |Repeat at2000AIattempts and300uploads/month with variable OCR fraction |
| Storage |Accumulate retained source/extraction/vector versions; monthly ingress is not retained total |
| Other dimensions |Measure or explicitly assume API traffic/durations, transfer, logs, transactional capacity and retained support/audit data in Calculator |

Nova2 maxTokens is2500 in source; input quantity is an assumption, not an enforced input limit. These inputs also appear in the worklog CurrentRelease guide. No new regional unit prices, USD total or Calculator export has been verified for this scenario. Include unavailable Calculator dimensions as supplemental official-price calculations rather than omitting them. Explain free-tier eligibility and tax/currency separately. Include continuing storage/PITR/log costs even when inference is off.

The30–50 USD target and50 USD account budget are planning/alerts, not a hard cap or proof of actual cost. Cost optimization choices include bounded retrieval, compact vectors, no always-running vector cluster, narrow parser role, lifecycle/retention and no automatic generation retries. Monthly aggregate contention is bounded/retried separately from generation. Revisit these choices after real workload measurements.

Calculator link/export: **not yet supplied**. Fresh-account cost validation: **not yet performed**. Student review is required before describing COST as complete in the workshop.
