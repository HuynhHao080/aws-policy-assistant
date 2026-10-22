# Cost-control options — decision packet, not authorization

**Amount update after observed baseline:** [October cost review](budget-baseline-2026-10.md) records USD5.4223 accrued October 1–20 and USD3.1168 remaining AWS forecast, giving USD8.5391 baseline; adding the full USD6.6306 test model yields a USD15.1697 conservative envelope. Recommend **USD20**, superseding provisional USD15, with Actual >16/>20 and Forecasted >20. No approval or AWS change occurred. All resource-attribution limitations remain; do not infer old-stack costs from service totals.

Reviewed 2026-10-21. No AWS writes, template edits, activation, deployment or new candidate was performed. Existing Budget recipients were not queried. No address belongs in the public report, chat, repository, evidence logs or screenshots; the owner confirms the recipient only in the authorized AWS console and completes AWS verification there if required.

## Current evidence

08:22:20–08:22:32 UTC: STS verified account …0098; candidate `fcaj-review-20261021-072124-24ba855e` remained CREATE_COMPLETE/AVAILABLE with 45 Add and correct stack tags. Fresh processed template matched the saved AWS template. Billing returned no Environment/Project allocation keys and no next page. Six existing budgets remain; neither proposed new name exists. [AWS read-only evidence](evidence/aws-budget-tag-coverage-readonly.json).

The existing USD5 whole-account Budget has UnblendedCost, no CostFilters/FilterExpression and two ACTUAL notifications (thresholds 50 and 80). ThresholdType is omitted: do not infer percentages or dollar amounts. The complete notification list has no FORECASTED alert. No delivery or subscriber verification was performed. Keep it unchanged; normalizing that Budget would be a different modification requiring an exact separate approval.

## Two choices

| Setting | 1 — Account-wide monitoring | 2 — Test-tag attribution |
|---|---|---|
| Proposed new name | policy-assistant-account-monthly | policy-assistant-fcaj-test-monthly |
| Fixed monthly limit | **20 USD**, recommended after observed baseline + full test planning envelope of 15.1697 USD | **10 USD**, planning allowance for the 6.6306 USD gross test model |
| Scope | All services/regions/global charges attributable to the exact account ending 0098, including old stack/test/shared artifacts/retained data | Exact same account, only cost lines with Environment=fcaj-test AND Project=PolicyAssistant, all regions/services |
| Metric | UnblendedCost excluding Credit/Refund; no resource-tag filter | UnblendedCost excluding Credit/Refund; both resource cost-allocation tags required |
| ACTUAL alerts | GREATER_THAN 80%=16 USD and 100%=20 USD | GREATER_THAN 80%=8 USD and 100%=10 USD |
| FORECASTED alert | GREATER_THAN 100%=20 USD | GREATER_THAN 100%=10 USD |
| Benefit | Warns on untagged/shared usage before test tags exist | Distinguishes eligible test spend from old-stack costs |
| Limits | Cannot tell which environment caused the alert; unrelated or prior usage can trigger it immediately | Can omit charges or show a misleading zero; not ready until propagation/activation/line-item coverage is verified |
| Required approval | Exact new name, amount, metric, start and private recipient confirmation; create only three direct-email notifications | Same, plus separate authorization for explicit tag implementation and activation of the two keys |

Under consolidated billing, explicitly restrict LINKED_ACCOUNT to the exact privately verified account ending 0098, rather than silently monitoring all linked accounts. The account creating a Budget does not by itself prove its financial scope. No BillingView or CostCategory creation is proposed. Tax/support are included under option 1 where attributable to that account; under option 2 they count only if both tags match. Credits/refunds are excluded from both, but Free Tier/pricing discounts still mean the view is not the gross list-price model.

Both options start at 2026-10-01 00:00 UTC only if approved/created in October, recurring monthly; re-review if later. Neither changes the existing USD5 Budget, has Budget Actions, changes IAM or automatically stops anything. Recipient values are confirmed only inside the authorized AWS console. No fallback filter is allowed if the selected scope fails.

## Tag declarations and cost coverage

Public CloudFormation specification 268.0.0 and the actual candidate show **28 taggable resources / 17 without a tagging property / zero resources explicitly declaring both target tags**. The two values are correctly requested at stack level. CloudFormation propagation varies by resource type: this is not proof every deployed resource will lack tags, but propagation and billing coverage remain NOT_RUN. [Exact 45-row matrix](budget-tag-coverage.md), [JSON](evidence/aws-test-tag-coverage-matrix.json), [CloudFormation propagation guidance](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-resource-tags.html).

| Cost area | Precise classification |
|---|---|
| CloudWatch dashboard / five alarms | Taggable in current AWS documentation, correcting earlier claims of inherent dashboard non-taggability. Cost allocation of their charge lines remains unconfirmed; reconcile DashboardsUsageHour and AlarmMonitorUsage rather than assuming complete tag coverage. The model's 3 USD dashboard + .50 USD alarms are allocation risk, not proven universally unallocatable. [Dashboard specification](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-cloudwatch-dashboard.html). |
| CloudFront | Distribution supports tags AND cost allocation. Not inherently excluded. Verify actual distribution tags and Billing activation; do not restrict to Singapore and omit global charges. OAC/headers have no separate modeled fee/tag property. [AWS CloudFront tagging](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/tagging.html). |
| API Gateway | API/stage are taggable; stage is the recommended billing target. ABAC inheritance does not establish billing tags. Source SAM HttpApi does not set PropagateTags. [AWS API Gateway tagging](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-tagging-supported-resources.html). |
| Lambda / log groups / SQS / SNS / Cognito / DynamoDB / S3 | Tag-capable paid-service resources; eligible charges may be allocated after tags/activation. No actual test billing lines exist yet. Separately check transfer, PITR/backups and other auxiliary costs. Do not allocate Lambda spend merely by tagging its IAM role. |
| Retained document bucket / two tables | Retain is not exclusion from billing or allocation. Bytes/PITR can continue costing after stack deletion; eligible charges still match if tags remain. Verify future tag preservation and auxiliary backup line attribution. Retained bucket policy itself has no separate fee. |
| Shared SAM artifact bucket/prefix | Outside the 45 resources. Bucket-level tags cannot isolate a prefix. Do not retag the shared bucket as test; account-wide monitoring captures attributable shared bucket charges. |
| Untagged account/metric/API/transfer/tax/support lines | Account-wide view covers them within account/metric scope; a both-tag filter omits nonmatching lines. No claim of 100% per-line coverage. |

Future explicit tagging is a proposed fix only: add deployment-specific Environment/Project values to supported properties, use UserPoolTags for Cognito and verify the generated stage via SAM HttpApi Tags/PropagateTags. Explicit roles/log groups/queues need their own declaration. No unsupported Tags on inline IAM policies, Lambda permissions, bucket policies or CloudFront configuration resources. Any source change requires a new candidate/fingerprint review; do not imply it is included in 24ba855e. No production tag change or tagging service is proposed.

Billing key appearance/activation can each take up to 24 hours. Activation affects all values of those keys in the account, and requires separate approval; no backfill is included. [AWS activation guidance](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html).

## Recommendation and approval gates

**Choose account-wide monitoring first, with recommended 20 USD if approved.** It addresses the predeployment tagging dependency and includes charges the tag filter could miss. Keep the existing USD5 warning unchanged. Add the USD10 test-tag Budget later for attribution after declaration/propagation/activation and cost-line verification. The October estimated baseline is now observed; the combined full-test envelope remains a planning scenario, not a promise that account usage stays below the selected amount.

Budget warns, not protects by hard cap: usage continues after thresholds, billing/alerts lag and forecasts require enough history (AWS guidance approximately five weeks). A successful recipient configuration does not prove email delivery. [AWS Budget behavior](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html), [forecast guidance](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-best-practices.html).

Independent gates: (A) choose/approve the exact Budget configuration and confirm recipient privately in AWS; (B) separately authorize any local tagging implementation/new reviewed candidate and Billing-key activation; (C) separately approve the exact application change set and bounded E2E scope. User has not granted any of these. Deployment stays NO-GO. No existing-stack mutations, destructive cleanup, commit or push is included.
