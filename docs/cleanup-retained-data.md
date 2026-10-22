> C0 hiện tại: read-only inventory VERIFIED;45resources/4Retain, browserR7PASS; SNS0subscriptions, DLQALARM. Chưa cleanup. Xem [C0 inventory và acceptance](cleanup-c0-inventory-and-acceptance.md). Các mốc cũ bên dưới là lịch sử.

# Test rollback and retained-data cleanup

No deletion is authorized by technical preparation or change-set creation. This document is a future operator procedure requiring an approved inventory. Existing `policy-assistant` is always outside the test write scope.

## Protection design

The candidate retains **PoliciesTable, DocumentMetadata, PolicyAssistantDocumentsBucket and DocumentsBucketTlsPolicy** on stack deletion and resource replacement. The policy is a TLS-only Deny bound to the retained document bucket/objects, not a public Allow or a reference to a function/role that disappears with the stack. Keeping policy and bucket together prevents normal stack deletion from removing the explicit HTTPS restriction. S3 public-access block, SSE-S3 and versioning remain bucket properties.

[AWS explicitly supports Retain on bucket policies](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-s3-bucketpolicy.html). This protects against normal CloudFormation delete/replacement; it does not prevent a privileged administrator separately changing/deleting a policy or bypassing intended procedures. Retain is not Object Lock or a backup, and does not suspend the existing lifecycle. Current expiry is 365 days; noncurrent expiry 365 days from becoming noncurrent. Do not promise indefinite data preservation or total removal at day 365.

## CREATE rollback versus failed application acceptance

If approved CREATE fails, CloudFormation can roll back newly provisioned infrastructure. Inspect events and the actual retained-resource inventory; only successfully created resources may remain. Do not recreate named retained tables/buckets without checking for collisions/import requirements. A failed E2E after CREATE_COMPLETE does not automatically roll back CloudFormation. Stop sharing/publishing readiness, preserve evidence and choose a separately reviewed test-only corrective change. Do not roll back by deploying the legacy app/template blindly or modifying production owners/state.

The three exact-group logging IAM policies are separate resources to avoid role/function/log-group dependency cycles. They are normally deleted with the test roles/groups, while the retained S3 policy remains. New functions can exist briefly before their log policy is attached during CREATE; begin acceptance only after the entire stack is CREATE_COMPLETE and exact log-group/policy readiness is checked. No log CreateLogGroup permission is needed because CloudFormation creates all three groups.

## Expected leftovers after successful stack deletion

| Retained/outside-stack component | What persists / cost |
|---|---|
| Test PoliciesTable | Items and table/PITR state; storage/PITR charges and any later reads/writes |
| Test DocumentMetadata | Metadata and GSIs/PITR; storage/PITR and any later activity |
| Test documents bucket | Objects, versions/delete markers, lifecycle, BPA/encryption/versioning; storage/requests/egress |
| DocumentsBucketTlsPolicy | Explicit HTTPS Deny remains; no separate policy fee |
| Review artifacts | Isolated prefixes in the existing packaging bucket are outside the application stack; storage/requests continue |
| Separately approved Budget | Separate billing configuration is not part of this stack and would need its own lifecycle decision |

Other resources default to Delete, including queues/messages, users/pool, logs, API, functions, roles/policies, monitoring, schedule and CloudFront. This is intended behavior, not proof that a delete will succeed. The versioned frontend bucket must be inventoried: a nonempty bucket can cause DELETE_FAILED. Export wanted logs/screenshots before removing their groups. Confirm CloudFront teardown and any failed resources from actual events.

## Owner-approved cleanup sequence

1. Confirm exact account/region/test stack and physical IDs; list every target, retained version/delete marker, table/index/backup, queue/DLQ and review prefix. Obtain separate explicit permission for data destruction, pool/user removal and retained tables/bucket.
2. Export required synthetic evidence and keep sanitized source/fingerprints. Stop new test activity through a reviewed procedure; do not purge messages or remove policies just to clear alarms.
3. Delete test infrastructure only within the approved scope. Inspect DeletionPolicy/UpdateReplacePolicy before the operation and verify all four retained entries afterward.
4. Verify the retained bucket still has TLS-only Deny, BPA and encryption after stack deletion. **Do not remove its policy first to empty the bucket.** An approved cleaner can list/delete authorized versions over HTTPS while the Deny remains. Emptying a bucket is destructive and must explicitly include versions/delete markers.
5. Only after export/retention approval, remove the specifically authorized retained tables/backups and bucket. Keep the HTTPS policy in place until the bucket's final authorized deletion. If the bucket remains, the policy must remain. Removing it for a remaining bucket requires a separate equivalent-protection design and approval.
6. Delete only the known review artifact prefixes/unused change sets after approval, never the shared packaging bucket or unrelated artifacts. Record objects/versions removed and residual resources without secrets.
7. Recheck retained/failed resources, Budget coverage and Billing after propagation. Retain stock at the model's assumed volumes is roughly 0.6649 USD/month before allowances plus requests/egress; this is not measured test stock. Keep the cost monitor until residuals are understood.
