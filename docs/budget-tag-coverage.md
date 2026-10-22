# Tag and billing coverage — exact 45 Add resources

Reviewed 2026-10-21. Candidate `fcaj-review-20261021-072124-24ba855e`; public CFN specification 268.0.0. Fresh AWS processed template matched the saved candidate. No template edits or AWS mutations were made.

**28 taggable resources; 17 without a CFN tag property; 0 explicitly declare both Environment/Project in the processed template.** Correct tags are requested at stack level. Propagation and actual billing line coverage are NOT_RUN, not proven by that stack request.

Taggable does not mean every service charge is allocatable. No separate fee means no duplicate resource fee in the current model, not that the surrounding service is free. Service charges can appear in Bills/Cost Explorer without being selectable by these two tags. Retain is not a billing exclusion.

| Logical ID | Type | Tag property | Explicit Env/Project | Billing category | Deletion / Replacement |
|---|---|---|---|---|---|
| AlertTopic | SNS::Topic | Tags | None | DOCUMENTED_COST_ALLOCATION | Delete (default) / Delete (default) |
| DocumentDLQAlarm | CloudWatch::Alarm | Tags | None | TAGGABLE_BILLING_COVERAGE_UNCONFIRMED | Delete (default) / Delete (default) |
| DocumentMetadata | DynamoDB::Table | Tags | None | DOCUMENTED_COST_ALLOCATION | Retain / Retain |
| DocumentQueueAgeAlarm | CloudWatch::Alarm | Tags | None | TAGGABLE_BILLING_COVERAGE_UNCONFIRMED | Delete (default) / Delete (default) |
| DocumentRecovery | Lambda::Function | Tags | None | FUNCTION_USAGE | Delete (default) / Delete (default) |
| DocumentRecoveryLogWritePolicy | IAM::Policy | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| DocumentRecoveryLogs | Logs::LogGroup | Tags | None | DOCUMENTED_COST_ALLOCATION | Delete (default) / Delete (default) |
| DocumentRecoveryRecoverPending | Events::Rule | Tags | None | NO_SEPARATE_MODELED_RULE_FEE | Delete (default) / Delete (default) |
| DocumentRecoveryRecoverPendingPermission | Lambda::Permission | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| DocumentRecoveryRole | IAM::Role | Tags | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| DocumentsBucketTlsPolicy | S3::BucketPolicy | None | None | NO_INDEPENDENT_FEE | Retain / Retain |
| FrontendAccessControl | CloudFront::OriginAccessControl | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| FrontendBucket | S3::Bucket | Tags | None | BUCKET_LEVEL_ALLOCATION | Delete (default) / Delete (default) |
| FrontendBucketPolicy | S3::BucketPolicy | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| FrontendDistribution | CloudFront::Distribution | Tags | None | DOCUMENTED_COST_ALLOCATION_GLOBAL | Delete (default) / Delete (default) |
| FrontendHeaders | CloudFront::ResponseHeadersPolicy | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| PoliciesTable | DynamoDB::Table | Tags | None | DOCUMENTED_COST_ALLOCATION | Retain / Retain |
| PolicyAssistantApi | ApiGatewayV2::Api | Tags | None | RELATED_API_STAGE_COST | Delete (default) / Delete (default) |
| PolicyAssistantApiProdStage | ApiGatewayV2::Stage | Tags | None | STAGE_COST_ALLOCATION_TARGET | Delete (default) / Delete (default) |
| PolicyAssistantDashboard | CloudWatch::Dashboard | Tags | None | TAGGABLE_BILLING_COVERAGE_UNCONFIRMED | Delete (default) / Delete (default) |
| PolicyAssistantDocumentDLQ | SQS::Queue | Tags | None | QUEUE_LEVEL_ALLOCATION | Delete (default) / Delete (default) |
| PolicyAssistantDocumentQueue | SQS::Queue | Tags | None | QUEUE_LEVEL_ALLOCATION | Delete (default) / Delete (default) |
| PolicyAssistantDocumentsBucket | S3::Bucket | Tags | None | BUCKET_LEVEL_ALLOCATION | Retain / Retain |
| PolicyAssistantDurationAlarm | CloudWatch::Alarm | Tags | None | TAGGABLE_BILLING_COVERAGE_UNCONFIRMED | Delete (default) / Delete (default) |
| PolicyAssistantErrorAlarm | CloudWatch::Alarm | Tags | None | TAGGABLE_BILLING_COVERAGE_UNCONFIRMED | Delete (default) / Delete (default) |
| PolicyAssistantFunction | Lambda::Function | Tags | None | FUNCTION_USAGE | Delete (default) / Delete (default) |
| PolicyAssistantFunctionDocumentDownloadPermission | Lambda::Permission | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| PolicyAssistantFunctionDocumentStatusPermission | Lambda::Permission | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| PolicyAssistantFunctionGetPolicyByIdPermission | Lambda::Permission | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| PolicyAssistantFunctionHealthCheckPermission | Lambda::Permission | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| PolicyAssistantFunctionListDocumentsPermission | Lambda::Permission | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| PolicyAssistantFunctionLogWritePolicy | IAM::Policy | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| PolicyAssistantFunctionRole | IAM::Role | Tags | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| PolicyAssistantFunctionSearchPoliciesPermission | Lambda::Permission | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| PolicyAssistantFunctionSubmitDocumentPermission | Lambda::Permission | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| PolicyAssistantFunctionUploadSessionPermission | Lambda::Permission | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| PolicyAssistantLogGroup | Logs::LogGroup | Tags | None | DOCUMENTED_COST_ALLOCATION | Delete (default) / Delete (default) |
| PolicyAssistantUserPool | Cognito::UserPool | UserPoolTags | None | DOCUMENTED_COST_ALLOCATION | Delete (default) / Delete (default) |
| PolicyAssistantUserPoolClient | Cognito::UserPoolClient | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| PolicyAssistantWorker | Lambda::Function | Tags | None | FUNCTION_USAGE | Delete (default) / Delete (default) |
| PolicyAssistantWorkerDocumentQueueEvent | Lambda::EventSourceMapping | Tags | None | NO_SEPARATE_MODELED_MAPPING_FEE | Delete (default) / Delete (default) |
| PolicyAssistantWorkerLogGroup | Logs::LogGroup | Tags | None | DOCUMENTED_COST_ALLOCATION | Delete (default) / Delete (default) |
| PolicyAssistantWorkerLogWritePolicy | IAM::Policy | None | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| PolicyAssistantWorkerRole | IAM::Role | Tags | None | NO_INDEPENDENT_FEE | Delete (default) / Delete (default) |
| RecoveryErrorAlarm | CloudWatch::Alarm | Tags | None | TAGGABLE_BILLING_COVERAGE_UNCONFIRMED | Delete (default) / Delete (default) |

## Per-type billing interpretation

- **AWS::ApiGatewayV2::Api** (1): API taggable; require direct stage tags, do not assume ABAC inheritance allocates usage. [Official reference](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-tagging-supported-resources.html).
- **AWS::ApiGatewayV2::Stage** (1): Stage taggable and recommended allocation target; no separate duplicate charge for a stage resource. [Official reference](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-tagging-supported-resources.html).
- **AWS::CloudFront::Distribution** (1): Distribution cost allocation supported; do not omit global charges by region; not every auxiliary line item is proven. [Official reference](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/tagging.html).
- **AWS::CloudFront::OriginAccessControl** (1): No independent modeled fee and no tagging property in public CFN specification; associated paid service resource must be classified instead. [Official reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-cloudfront-originaccesscontrol.html).
- **AWS::CloudFront::ResponseHeadersPolicy** (1): No independent modeled fee and no tagging property in public CFN specification; associated paid service resource must be classified instead. [Official reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-cloudfront-responseheaderspolicy.html).
- **AWS::CloudWatch::Alarm** (5): Alarm can be tagged; service charge exists; this review did not find proof every alarm cost line carries tags. [Official reference](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Tagging.html).
- **AWS::CloudWatch::Dashboard** (1): Current AWS supports Tags; prior untaggable claim corrected. Dashboard charge exists, cost allocation not proven. [Official reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-cloudwatch-dashboard.html).
- **AWS::Cognito::UserPool** (1): User-pool tags support cost allocation; verify actual MAU/service line items after use. [Official reference](https://docs.aws.amazon.com/cognito/latest/developerguide/tagging.html).
- **AWS::Cognito::UserPoolClient** (1): No independent modeled fee and no tagging property in public CFN specification; associated paid service resource must be classified instead. [Official reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-cognito-userpoolclient.html).
- **AWS::DynamoDB::Table** (2): Table usage/storage eligible; separately verify PITR/backups/GSI line attribution, not every related charge is proven. [Official reference](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TagResource.html).
- **AWS::Events::Rule** (1): Scheduled rule taggable; dependent Lambda is billed separately; no paid event-bus traffic modeled. [Official reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-events-rule.html).
- **AWS::IAM::Policy** (3): No independent modeled fee and no tagging property in public CFN specification; associated paid service resource must be classified instead. [Official reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-iam-policy.html).
- **AWS::IAM::Role** (3): Role can be tagged; its tags do not allocate the Lambda/service charges. [Official reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-iam-role.html).
- **AWS::Lambda::EventSourceMapping** (1): Mapping taggable; current ordinary SQS polling has no provisioned-poller charge configured; function/queue costs separate. [Official reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-lambda-eventsourcemapping.html).
- **AWS::Lambda::Function** (3): Eligible function execution charges after resource tagging/activation; deployed line items NOT_RUN. [Official reference](https://docs.aws.amazon.com/lambda/latest/dg/configuration-tags.html).
- **AWS::Lambda::Permission** (9): No independent modeled fee and no tagging property in public CFN specification; associated paid service resource must be classified instead. [Official reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-lambda-permission.html).
- **AWS::Logs::LogGroup** (3): Log ingestion/storage can be grouped by log-group allocation tags; no billing data for undeployed test. [Official reference](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html).
- **AWS::S3::Bucket** (2): Bucket storage/requests subject to service line allocation; includes retained versions when bucket tags remain; not object-prefix allocation. [Official reference](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/cost-allocation-tags.html).
- **AWS::S3::BucketPolicy** (2): No independent modeled fee and no tagging property in public CFN specification; associated paid service resource must be classified instead. [Official reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-s3-bucketpolicy.html).
- **AWS::SNS::Topic** (1): Topic usage cost eligible; no message/email delivery tested. [Official reference](https://docs.aws.amazon.com/sns/latest/dg/sns-tags.html).
- **AWS::SQS::Queue** (2): Queue request cost eligible after tags/activation; separate runtime reconciliation required. [Official reference](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-queue-tags.html).

## Future explicit tagging proposal — not applied

If separately authorized, add the two values explicitly to the 28 taggable processed resources (Tags or UserPoolTags as appropriate). Use SAM HttpApi Tags and PropagateTags=true to cover its generated stage, then review the actual transformed stage; function tags do not replace tags on explicit roles/log groups/queues. Do not add unsupported properties to inline IAM policies, permissions, bucket policies or CloudFront configuration resources. Do not hard-code test tags into a template later applied to the old stack; keep deployment-specific values. Any template change invalidates the candidate source fingerprint and needs a new reviewed candidate; the existing candidate remains untouched.

Do not tag the shared artifact bucket as test. Do not activate billing keys or perform retrospective backfill without approval. Verify after deployment: actual resource tags, both billing-key activation states, then service/usage-line attribution including untagged residuals. No runtime cost-allocation acceptance is marked PASS.
