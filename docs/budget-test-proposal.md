# Cost-control proposal — account-wide first, test tags later

## Cập nhật hiện hành — Console do người dùng xác nhận

**Cấu hình Budget: VERIFIED.** Người dùng xác nhận COST / MONTHLY / 20 USD, Healthy, bắt đầu 2026-10-01; Actual 5,42 USD (27,11%), Forecast 8,54 USD (42,70%). Đúng ba alerts: ACTUAL 80%, ACTUAL 100%, FORECASTED 100%, đều Not exceeded; không Budget Actions. Metric UnblendedCost, loại Credit/Refund và phạm vi toàn account đã được xác minh trong snapshot API trước đó.

**Recipient: Active (legacy), theo Console người dùng kiểm tra. Email verification: 0/1 verified; email delivery: DELIVERY_NOT_VERIFIED.** Không đánh đồng trạng thái legacy với email đã xác minh hoặc đã nhận thành công. Không gửi verification, không sửa Budget/notification. Thời điểm quan sát Console không được cung cấp; evidence chỉ ghi thời điểm tiếp nhận. [Evidence mới](evidence/budget-20usd-user-console-confirmation.json) bổ sung snapshot API lịch sử, không thay thế nguồn gốc của snapshot đó. Sáu Budget cũ khớp fingerprint ở lần kiểm tra trước; không kiểm tra lại AWS trong cập nhật local này.

Hồ sơ [Approval B](aws-test-deployment-approval-b.md) đã chuẩn bị, **chưa được phê duyệt**. CloudFormation deployment: NOT_EXECUTED. AWS E2E: NOT_RUN. Các trạng thái PARTIAL/unconfirmed bên dưới mô tả thời điểm API lịch sử trước xác nhận Console này.

**Live state after owner creation:** Budget USD20 now exists and its configuration/three PERCENTAGE alerts/no Actions are verified read-only. Six old configuration fingerprints match. Recipient is CONFIGURED but activation/subscription confirmation and actual delivery are unverified by available API evidence. Do not create again or interpret the public sample as an outstanding create instruction. [Current verification report](budget-20usd-verification.md). Candidate remains AVAILABLE/45 Add as of 2026-10-21 09:18:37 UTC; separate Approval B is still required. The test-tag USD10 Budget remains pending.

**Approval A update:** user conditionally authorized the single USD20 account Budget and the three approved alerts, but explicitly requires recipient confirmation inside AWS before any create. Current status **BLOCKED_PENDING_RECIPIENT**; no Budget/notification has been created, no subscriber address queried/exported. Six existing configurations and the USD5 notification baseline match preparation fingerprints. [Current approval state](budget-20usd-approval.md), [fresh preflight](evidence/budget-20usd-approval-a-preflight.json). No deployment/E2E authorization is granted; earlier no-approval wording below is historical.

**Preparation-only packet:** [phiếu duyệt Budget 20 USD](budget-20usd-approval.md), [Budget API fragment](budget/account-monthly-20usd-proposal.json), [ba Notification](budget/account-monthly-20usd-notifications.json), [manifest pending fields](budget/account-monthly-20usd-preparation.json), [Console guide](budget/account-monthly-20usd-console.md). Trạng thái PREPARED_NOT_CREATED, recipient PENDING_USER_CONFIRMATION, creation NOT_EXECUTED. Read-only 2026-10-21 08:44:22–08:44:25 UTC: exact account verified, name available, six existing Budgets. Các fragment public không phải request CreateBudget hoàn chỉnh và không cấp quyền thao tác.

## Latest amount recommendation — observed October baseline

Read-only AWS queries at **2026-10-21 08:34:26–08:34:33 UTC** recorded **5.4223 USD for October 1–20** and forecast **3.1168 USD for October 21–31**, using exact-account UnblendedCost excluding Credit/Refund. Current-month actuals are still Estimated. Derived baseline October total: **8.5391 USD**. Adding the full gross 30-day test model **6.6306 USD** gives a conservative planning envelope **15.1697 USD**, not an AWS forecast of the new workload.

**Recommend 20 USD/month instead of the earlier provisional 15 USD.** ACTUAL >80%=16 USD, ACTUAL >100%=20 USD, FORECASTED >100%=20 USD, no Budget Actions. The exact account-wide scope, unchanged existing USD5 Budget and private recipient confirmation in AWS remain as stated below. No amount or creation is approved.

| Monthly amount | ACTUAL 80% / 100% | FORECASTED 100% | Headroom against 15.1697 USD planning envelope | Decision guidance |
|---|---|---|---:|---|
| 10 USD | >8 / >10 USD | >10 USD | -5.1697 USD | Too low for combined planned use |
| 15 USD | >12 / >15 USD | >15 USD | -.1697 USD | Very tight, expected threshold crossings possible |
| **20 USD** | **>16 / >20 USD** | **>20 USD** | **+4.8303 USD** | **Recommended for owner approval**, not a hard cap |

EBS volume/snapshot costs **4.7773 USD** and KMS keys **.6331 USD** dominate the recorded baseline. No reliable resource/stack attribution was established; do not charge those amounts to Policy Assistant. S3/shared artifacts and old-stack services also cannot be split from service-level billing alone. The full **5.4223 USD** is unallocated by resource/project, not zero stack cost. Existing unfiltered Budget zero-spend snapshots are not comparable to the strict Credit/Refund exclusion query.

Method, service/usage breakdown, timing/forecast limitations and API-query overhead: [October baseline decision](budget-baseline-2026-10.md), [sanitized AWS evidence](evidence/aws-october-account-cost.json), [decimal comparison](evidence/aws-october-budget-comparison.json). Two CE requests were used; approximately .02 USD planning overhead at the documented standard API rate is not yet a measured charge. This section supersedes the older provisional amount below. Budget test USD10 remains pending; no activation/deployment is included.

## Current decision packet — 2026-10-21 08:22 UTC

**Neither Budget nor deployment is approved.** The current recommendation is a new account-wide **20 USD/month** alert Budget first, preserving the existing USD5 Budget unchanged; add **10 USD/month** test-tag attribution only after tagging and Billing prerequisites are verified. The latest observed-baseline review above replaces the earlier provisional USD15 amount. Neither is a hard spending cap.

| Choice | Exact scope | ACTUAL / FORECASTED | Approval needed |
|---|---|---|---|
| policy-assistant-account-monthly, 20 USD | Exact account …0098, all services/regions including global, old stack, test, shared artifacts and retained charges; no resource tag filter | ACTUAL >80%=16 USD and >100%=20 USD; FORECASTED >100%=20 USD | New Budget/configuration and recipient confirmed privately inside authorized AWS |
| policy-assistant-fcaj-test-monthly, 10 USD | Same exact account; Environment=fcaj-test AND Project=PolicyAssistant billing lines; all regions/services | ACTUAL >80%=8 USD and >100%=10 USD; FORECASTED >100%=10 USD | New Budget/configuration plus separately authorized tag implementation/activation and coverage checks |

Both use UnblendedCost excluding Credit/Refund, no automatic Budget Actions and no existing-Budget edits. Explicitly restrict LINKED_ACCOUNT to the verified exact account under consolidated billing. Proposed October start is 2026-10-01 00:00 UTC, recurring monthly; re-review if later. Owner enters/confirms recipients only in the authorized AWS console; no address is requested or stored in public files/chat/logs.

Fresh read-only verification found correct stack-level tags, **28 taggable resources / 17 without tag properties / zero explicitly declaring both values in the processed template**. Stack propagation and deployed billing coverage remain NOT_RUN. Billing returned no Environment/Project allocation keys. These findings do not imply that implicit stack propagation always fails. Current AWS documentation supports dashboard tagging; prior descriptions of inherently untaggable dashboards are corrected. CloudFront supports cost allocation; Retain is not an allocation exclusion. Shared artifact prefixes cannot be isolated by bucket-level tags.

The existing USD5 Budget has two ACTUAL thresholds, 50 and 80, with ThresholdType omitted; do not infer percentages/dollar amounts or claim delivery. No FORECASTED notification was returned. No subscriber addresses were queried.

Full decision detail, per-cost gaps and permissions: [two-option review](budget-options-review.md). All 45 resources: [tag/billing matrix](budget-tag-coverage.md), [JSON evidence](evidence/aws-test-tag-coverage-matrix.json). Latest Billing/API evidence: [read-only review](evidence/aws-budget-tag-coverage-readonly.json).

**Choose and approve the Budget scope first; any tag implementation/activation and application execution/E2E are separate approvals.** No AWS changes, source-template changes, new candidate, commit or push were made. The earlier USD10 draft below is supporting detail only; this current decision packet and linked review supersede older coverage and recipient instructions.

Reviewed 2026-10-21. **No Budget, subscriber or cost-allocation-tag activation was created or changed.** Budget creation and deployment require independent approvals.

## Current read-only evidence

Signed STS verified account ending **0098**. At **08:12:48–08:12:52 UTC** (15:12:48–15:12:52 Vietnam time), DescribeBudgets returned six existing budgets. Proposed name `policy-assistant-fcaj-test-monthly` does not exist. An existing USD5 COST budget has no CostFilters or FilterExpression; it remains unchanged. No recipient addresses were exported or reused. This review did not retest delivery or Budget Actions.

ListCostAllocationTags for **Environment** and **Project** returned **no records**, with no next page. Their activation is therefore not verified; this does not establish that resource tags are absent. Evidence: [read-only review](evidence/aws-budget-readonly-review.json).

## Exact configuration for approval

| Setting | Proposal |
|---|---|
| Account | STS-verified account ending 0098 |
| Name | policy-assistant-fcaj-test-monthly |
| Type / period | COST / fixed MONTHLY / USD; no auto adjustment |
| Limit | 10.00 USD per calendar month, not a balance or hard cap |
| Start | 2026-10-01 00:00 UTC if approved/created in October 2026, recurring monthly; re-review if creation moves to another month |
| Metric | UnblendedCost, excluding Credit and Refund line items; not net-unblended or amortized |
| Filter | Environment equals fcaj-test **AND** Project equals PolicyAssistant, exact tag values |
| Region/service filters | None; includes matching global-service and other-region charges |
| ACTUAL | GREATER_THAN 80 PERCENTAGE and 100 PERCENTAGE: month-to-date cost >8 USD and >10 USD |
| FORECASTED | GREATER_THAN 100 PERCENTAGE: forecast month-end cost >10 USD |
| Recipient | Owner confirms privately inside authorized AWS; no address collection in public report/chat |
| Budget Actions | None: no deny, stop, shutdown, deletion or IAM changes |
| SNS / reports | No SNS subscription or scheduled Budget Report proposed |
| Existing Budgets | No modifications, deletion, threshold increase or subscriber changes |

The [JSON draft](budget-test-proposal.json) uses explicit AND FilterExpression and Metrics. It is **not an executable CreateBudget request**: recipient is unset. Two tag filters must not be flattened into a list with OR semantics. Tags on the Budget resource itself are access-management metadata, not workload allocation. [Budget API](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_Budget.html), [Expression API](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_Expression.html).

## Separation from the existing stack

The candidate carries stack tags Project=PolicyAssistant, Environment=fcaj-test and Purpose=FCAJ-demo-review. The Budget selects **billing line items with both matching cost-allocation tags**, not stack names, resource-name prefixes or a CloudFormation boundary. Existing policy-assistant charges without both tags are excluded. Accidental reuse of both values on old/unrelated resources includes their matching charges. Verify tag propagation to supported test resources after approved creation; do not modify production tags to force a match.

Do not apply an ap-southeast-1-only region filter: it can omit global CloudFront charges. This proposal covers matching charges in the account across regions, so accidentally matching resources elsewhere would count too.

Keep the existing account-wide USD5 Budget unchanged as a complementary warning. Reconcile tagged costs against Bills by service. No account-wide USD10 Budget is silently substituted. No paid Cost Explorer cost query, cost-category/billing-view change, resource tag write or historical backfill was performed.

Coverage gaps:

- Stack tags do not prove every service/line item receives usable billing tags. No deployed test-resource coverage is verified yet.
- Untagged/unsupported charges, including the modeled USD3/month CloudWatch dashboard, may be omitted. Do not claim coverage of all USD6.6306 of the gross model.
- Review artifacts share an existing SAM bucket. Bucket-level tags cannot isolate a prefix; do not label the entire shared bucket as test.
- Tax/support are not deliberately excluded by charge type, but count **only if their line items match both tags**. Untagged account fees can be missed; this is not full-account tax/support protection.
- Retained tables/document bucket can keep costing money after deletion. They count only where matching allocation tags remain available. Budget does not delete retained data.

## Tag prerequisites and order

**The tag Budget cannot yet be accepted as operational test coverage.** Both keys were absent from the Billing allocation inventory. Even if AWS accepts a filter before tagged charges appear, a zero value does not mean free usage or working protection.

After explicit scope approval: use the intended keys if available, or wait until approved test resources introduce them to Billing; activate only Environment and Project once available, confirm Active, then verify resource/value/line-item coverage. Activation changes allocation for **all values of those keys in the account**, although it does not change production resource configuration. No production-resource tag changes are proposed or authorized.

AWS says tag-key appearance can take up to 24 hours after tagging, and activation can take another 24 hours. Do not retry indefinitely, silently broaden scope or authorize historical backfill. [AWS tag activation](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html).

If the owner requires a functioning test-only Budget **before any deployment**, keep execution NO-GO until verified coverage can be established; the sequence may need revisiting. Any temporary account-wide Budget or allocation scheme is a different proposal requiring separate approval. Existing account-wide warnings/manual Bills checks do not prove test-tag coverage is ready.

## Recipient and limitations

Owner enters and confirms the recipient only inside the authorized AWS console and completes account-specific verification there if required. Do not request/display addresses in public reports, chat, JSON, logs or screenshots. Saving can trigger verification mail; check Active there, without copying the address into evidence. No subscriber address was queried or exported. Direct Budgets email is separate from application AlertEmail/SNS. [AWS verification](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-email-recipients.html).

Budget is **not a hard spending cap**: it reserves no funds, stops no resources and rolls back no deployments. AWS reports updates up to three times daily, typically 8–12 hours apart, with additional billing/notification delay possible. Costs can pass thresholds before an alert arrives. [AWS Budgets behavior](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html).

AWS guidance requires approximately five weeks of usage history for forecasts; a new tagged segment may not produce usable forecasts for a short demo. Actual alerts occur once per threshold per period, not as recurring reminders. No artificial spending is proposed to test delivery. [AWS best practices](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-best-practices.html).

USD10 gives about USD3.37 planning headroom over the **USD6.6306/month gross list-rate model**, whose 10x scenario is USD34.7081. Budget tracks billed UnblendedCost, not that model: Free Tier, pricing tiers, applicable discounts and incomplete tags change observed costs. Excluding Credit/Refund does not reconstruct every pre-discount cost. The existing account-wide USD5 alert may fire earlier; do not raise it automatically.

## Two independent approvals — neither granted

**A — Budget selection and creation.** Confirm the selected option in the current decision packet, start date and recipient privately inside authorized AWS. Tag implementation/activation needs separate scope approval; it is not implicit in account-wide Budget approval. No Budget Actions, existing Budget edits, production tag changes or hidden fallback. Owner completes recipient verification. Stop/report if prerequisites fail. A grants no deployment authority.

**B — Execute candidate and bounded E2E.** Separately approve `fcaj-review-20261021-072124-24ba855e`, test stack `policy-assistant-fcaj-test`, account …0098, region ap-southeast-1, **45 Add / 0 Modify / 0 Remove / 0 Replace**, and [the E2E plan](aws-live-test-plan.md): three synthetic policies, four frontend assets/invalidation, two invitation-suppressed test users, sequential real tests, at most one poison SQS probe and a direct mixed worker event. Recheck identity/candidate/source/artifact before execution. No load test, old-stack mutation, IAM weakening, queue purge or destructive cleanup is included. B grants no Budget write authority. If active Budget coverage is required first, B is gated on that readiness.

Both are unapproved. Runtime AWS E2E remains NOT_RUN. Teardown/retained-data deletion needs separate inventory approval.
