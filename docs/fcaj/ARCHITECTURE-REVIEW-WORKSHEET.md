# Student architecture review worksheet / Phiếu tự rà soát kiến trúc

This is a review brief, not the final diagram. Use [official AWS icons](https://aws.amazon.com/architecture/icons/) and design/draw the final artifact yourself. Cross-check every component with template.yaml and the exact deployed release.

| Review question | Evidence to inspect |
|---|---|
| Why is S3 private while the CloudFront frontend is public? How does OAC differ from a VPC endpoint? | FrontendBucketPolicy, FrontendDistribution |
| Which identity is trusted, and why cannot a bearer string supplied to direct Lambda establish it? | HTTP API authorizers, app.lambda_handler |
| How are private PDFs separated from globally published policies? Can an administrator read customer PDFs? | Service.owned, assistant.retrieve, two-account tests |
| Why persist work before SQS dispatch? What makes duplicate deliveries/recovery safe? | pipeline.py, metadata stream, dispatcher, worker leases/DLQs |
| What can the PDF parser access? Why is source-version pinning important? | PdfParser policies, pdf_parser.py, versioned extraction tests |
| Which retrieved data leaves Singapore, and where does generation occur? | BedrockModelId, generation region/IAM destinations, privacy notice |
| How do account-deletion markers prevent a late answer/feedback from resurrecting private data? | quality.account_guard, history transaction, pipeline purge |
| How do feedback revisions, deltas and idempotent persistence retries prevent double counting? | quality.feedback/commit and retry tests |
| Why are the dashboard metrics not a measurement of factual correctness? | Quality DTO/captions, refusal/citation definitions |
| What are the scale/cost limitations of a monthly rollup key and bounded S3 vector retrieval? | Quotas, reserved concurrency, conflict retry cap, cost worksheet |

On your own diagram mark: actor/trust boundaries; authenticated API; private versus shared storage; upload/processing/retrieval/feedback/deletion flows; synchronous versus queued calls; DLQs/recovery; cross-region excerpts; metrics/alerts. Do not add services/subnets that are absent merely to decorate the diagram.

For each arrow write one sentence explaining payload, authorization and failure handling. Record changes you personally made and questions you can answer without a script. Keep this worksheet separate from the final student-designed diagram.
