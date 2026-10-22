# October 2026 account baseline and Budget decision

Observed **2026-10-21 08:34:26–08:34:33 UTC** (15:34:26–15:34:33 Vietnam time). Signed STS verified account …0098. Only read operations were performed; no Budget, tag activation, deployment, user, message, commit or push. Existing candidate remained CREATE_COMPLETE/AVAILABLE and old stack UPDATE_COMPLETE.

## Comparable query basis

Cost Explorer filter: exact privately verified LINKED_ACCOUNT ending 0098 AND NOT RECORD_TYPE in Credit/Refund. Metric **UnblendedCost**, USD, all regions/services; no resource-tag filter or amortization. No new BillingView, Cost Explorer activation, resource-level granularity or paid data export was enabled.

Actual query: GetCostAndUsage DAILY, grouped SERVICE and USAGE_TYPE, **2026-10-01 inclusive to 2026-10-21 exclusive**. Thus it covers completed UTC dates 1–20 October, not unreported usage on 21 October. All returned dates have Estimated=true. “Actual” means accrued/recorded current-month estimated costs, not a finalized invoice.

Forecast query: GetCostForecast DAILY, UNBLENDED_COST, **2026-10-21 inclusive to 2026-11-01 exclusive**, same filter, prediction interval level 80. AWS returns a prediction for the remaining period, not a whole-month total. Daily prediction intervals are retained in evidence; they are not summed and presented as an 80% confidence interval for the month.

| Item | USD | Evidence interpretation |
|---|---:|---|
| Recorded October 1–20 costs | **5.4222749168** | Verified response, still Estimated |
| AWS forecast October 21–31 | **3.1167914980** | Remaining-period prediction, not guaranteed |
| Derived baseline whole October | **8.5390664148** | Recorded costs + remaining forecast; existing account behavior |
| Full 30-day test model | **6.6305950965** | Gross list-price assumptions, not billed consumption |
| Conservative planning envelope | **15.1696615113** | Baseline forecast + full test model; **not an AWS forecast** |

The test is not deployed. The AWS forecast does not explicitly model the planned new test workload. Adding a full 30-day model is a conservative planning comparison even though deployment is being considered late in October; it is not a prediction that all monthly test assumptions will be consumed this month. Do not automatically prorate all charges: active users, stock, requests and fixed features have different timing. Conversely, a full calendar month has 31 days in October while the model uses 30; modeled assumptions are not a cap. Do not add the old stack's separate gross estimate again to the account baseline and double-count existing usage.

## Existing stack and shared services: attribution limits

The query identifies service/usage types, not billing resource IDs or stack ownership. No active stack cost-allocation filter or authoritative resource-to-charge match was established. **No dollar amount is attributed to policy-assistant; this means unknown, not zero cost.** All USD5.4222749168 remain unallocated at resource/project level.

| Recorded category | USD | Attribution supported |
|---|---:|---|
| EBS gp3 volume usage | 3.8572043904 | Account usage type; volume owner/project not identified |
| EBS snapshots | .9200730810 | Account usage type; snapshot owner/project not identified |
| KMS keys, us-west-2 | .6330645060 | Account key-storage usage; specific key/project not identified |
| S3, all returned usage types | .0037095157 | Mixed account/bucket/request usage; cannot isolate shared SAM prefix from application bucket |
| DynamoDB | .0008443301 | Mixed usage types; no table/stack attribution |
| CloudWatch | .0001800000 | Nonzero GetMetricData usage; dashboard/alarm rows currently show zero billed cost, not proof of permanent free service |
| API Gateway | .0001712500 | HTTP request usage, no proven API/stage ownership |

Other small charges include Rekognition, Bedrock, AgentCore memory, Secrets Manager and EventBridge. They are account observations, not evidence that Policy Assistant implements those services. Lambda, Cognito, SNS and SQS cost rows show zero in this period; zero billed dollars does not imply zero activity or future cost.

EBS and KMS account for approximately USD5.41034 of the total. The old CloudFormation resource inventory has no EC2/EBS or KMS key resource; this prevents attributing those as its directly managed resources, but does not prove another project's ownership or rule out external dependencies. Do not delete/alter any volume, snapshot or key based on this review. Further ownership analysis would be read-only and separate.

Budget snapshots were read without recipients. Existing USD5 and unfiltered USD100 Budgets report ActualSpend=0 and ForecastedSpend=3.117; a filtered USD100 Budget reports 5.422/8.539. Those rounded snapshots have different/unverified exclusion and scope details, so they do not replace the exact CE filter. The filtered snapshot is numerically consistent, not independently proven identical. Do not infer that the account incurred no costs from a zero Budget actual; do not change existing Budgets.

## Decision table for owner approval

All choices: new `policy-assistant-account-monthly`, fixed COST/MONTHLY USD, exact account …0098, all services/regions, UnblendedCost excluding Credit/Refund; explicit PERCENTAGE and GREATER_THAN; no Budget Actions; existing USD5 unchanged. Recipient is entered/verified only in the authorized AWS console, never public chat/files. Start proposed 2026-10-01 00:00 UTC if created in October, recurring monthly; re-review if later.

An October-start Budget includes already recorded October spend; creating it on October 21 does not reset that month's costs to zero or give a fresh additional USD20 allowance.

| Monthly Budget | ACTUAL >80% / >100% | FORECASTED >100% | Headroom vs baseline + full test (15.1697) | Assessment |
|---|---|---|---:|---|
| 10 USD | 8 / 10 USD | 10 USD | **-5.1697 USD** | Baseline alone is already forecast above 80%; likely too low for combined planned use |
| 15 USD | 12 / 15 USD | 15 USD | **-.1697 USD** | Slightly below combined planning envelope; little room for late charges |
| **20 USD** | **16 / 20 USD** | **20 USD** | **+4.8303 USD** | **Recommended alert configuration**, about 24% headroom of the limit; not guaranteed spend containment |

USD20 supersedes the earlier provisional USD15 recommendation **for approval only**. Owner has approved neither amount nor creation. A larger alert threshold does not grant permission to spend that amount. For a deliberately tighter warning policy, USD15 is valid if the owner accepts expected threshold crossings; it is not a safer hard cap. Actual alerts remain based on incurred cost, not the baseline forecast compared with 80%.

Keep the test-tag USD10 Budget pending. Explicit resource tags, propagation, Billing key activation and actual cost-line coverage remain separately unapproved/unverified. Creating account-wide monitoring does not authorize any of them or execution/E2E.

## Data and cost limitations

- Current month remains Estimated and Billing may refresh later than 24 hours; October 20 is lower than prior days, which may reflect incomplete data, not a verified reduction. Current-day usage, late tax/support charges and subsequent resource changes can increase costs.
- Credit/Refund exclusions match the proposal. They do not reconstruct gross list-price costs or remove the effect of Free Tier/pricing discounts; billed usage and the gross test model differ.
- Forecast uses history and cannot guarantee future spending, incorporate the exact proposed workload or predict uncontrolled traffic, storage growth, retries or manual changes. It is not a ceiling or a stop mechanism.
- No per-resource cost attribution is claimed; shared buckets, untagged lines and retained resources are included account-wide but cannot be split reliably by project here. Allocating residual costs to the stack by subtraction would be unsupported.
- Two Cost Explorer API requests were made. At AWS's documented standard rate of USD.01 per paginated request, their planning overhead is about **USD.02**, not a measured posted charge; it falls outside the completed-day actual query and may appear later. No extra-cost data-collection feature was enabled.

Sources checked 2026-10-21: [Cost Explorer refresh and API cost](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html), [GetCostForecast period/Total semantics](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_GetCostForecast.html), [Billing vs CE timing and estimated data](https://docs.aws.amazon.com/en_en/awsaccountbilling/latest/aboutv2/differences-billing-data-cost-explorer-data.html).

Evidence: [actual/forecast AWS responses, sanitized](evidence/aws-october-account-cost.json), [decimal Budget comparison](evidence/aws-october-budget-comparison.json). Reproduce only when a fresh paid query is warranted: `.venv/Scripts/python.exe -m scripts.review_account_cost`. It is bounded, read-only and stops rather than enabling features or widening scope on errors.
