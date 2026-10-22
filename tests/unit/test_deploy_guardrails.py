"""Protect a separate test deployment from shared table names and data deletion."""
from pathlib import Path
import yaml
import pytest


class CloudFormationLoader(yaml.SafeLoader):
    pass


CloudFormationLoader.add_multi_constructor('!', lambda loader, tag, node:
    loader.construct_scalar(node) if isinstance(node, yaml.ScalarNode) else
    loader.construct_sequence(node) if isinstance(node, yaml.SequenceNode) else loader.construct_mapping(node))


def test_legacy_names_stay_compatible_and_test_tables_are_isolated():
    template = yaml.load((Path(__file__).parents[2] / 'template.yaml').read_text(), Loader=CloudFormationLoader)
    default = template['Parameters']['TableNamePrefix']['Default']
    for logical_id, legacy in [('PoliciesTable','PolicyAssistantPolicies'), ('DocumentMetadata','PolicyAssistantDocumentMetadata')]:
        expression = template['Resources'][logical_id]['Properties']['TableName']
        assert expression.replace('${TableNamePrefix}', default) == legacy
        assert expression.replace('${TableNamePrefix}', 'policy-assistant-fcaj-test-') != legacy


def test_stack_rollback_or_removal_does_not_delete_document_data():
    template = yaml.load((Path(__file__).parents[2] / 'template.yaml').read_text(), Loader=CloudFormationLoader)
    for logical_id in ['PoliciesTable','DocumentMetadata','PolicyAssistantDocumentsBucket']:
        resource = template['Resources'][logical_id]
        assert resource['DeletionPolicy'] == 'Retain'
        assert resource['UpdateReplacePolicy'] == 'Retain'


def test_worker_role_scopes_queue_access_instead_of_sam_wildcard_managed_policy():
    template = yaml.load((Path(__file__).parents[2] / 'template.yaml').read_text(), Loader=CloudFormationLoader)
    resources = template['Resources']
    assert resources['PolicyAssistantWorker']['Properties']['Role'] == 'PolicyAssistantWorkerRole.Arn'
    role = resources['PolicyAssistantWorkerRole']['Properties']
    assert not any('AWSLambdaSQSQueueExecutionRole' in policy for policy in role.get('ManagedPolicyArns',[]))
    statements = role['Policies'][0]['PolicyDocument']['Statement']
    queue_rules = [rule for rule in statements if any(action.startswith('sqs:') for action in rule['Action'])]
    assert queue_rules
    assert all(rule['Resource'] == 'PolicyAssistantDocumentQueue.Arn' for rule in queue_rules)


@pytest.mark.parametrize('function,group', [
    ('PolicyAssistantFunction','PolicyAssistantLogGroup'),
    ('PolicyAssistantWorker','PolicyAssistantWorkerLogGroup'),
    ('DocumentRecovery','DocumentRecoveryLogs'),
])
def test_each_function_can_write_only_its_precreated_log_group(function, group):
    template = yaml.load((Path(__file__).parents[2] / 'template.yaml').read_text(), Loader=CloudFormationLoader)
    resources = template['Resources']
    assert resources[function]['Properties']['Role'] == function + 'Role.Arn'
    role = resources[function + 'Role']['Properties']
    assert not role.get('ManagedPolicyArns')  # SAM must not inject basic/SQS wildcard policies.
    policy = resources[function + 'LogWritePolicy']['Properties']
    assert policy['Roles'] == [function + 'Role']
    statements = policy['PolicyDocument']['Statement']
    assert all(statement['Resource'] == group + '.Arn' for statement in statements)
    assert {action for statement in statements for action in statement['Action']} == {'logs:CreateLogStream','logs:PutLogEvents'}


def test_dlq_allows_only_its_own_source_without_circular_reference():
    template = yaml.load((Path(__file__).parents[2] / 'template.yaml').read_text(), Loader=CloudFormationLoader)
    resources = template['Resources']
    rule = resources['PolicyAssistantDocumentDLQ']['Properties']['RedriveAllowPolicy']
    assert rule['redrivePermission'] == 'byQueue'
    assert rule['sourceQueueArns'] == ['arn:${AWS::Partition}:sqs:${AWS::Region}:${AWS::AccountId}:' + resources['PolicyAssistantDocumentQueue']['Properties']['QueueName']]
    assert resources['PolicyAssistantDocumentQueue']['Properties']['RedrivePolicy']['deadLetterTargetArn'] == 'PolicyAssistantDocumentDLQ.Arn'


def test_retained_document_bucket_keeps_https_deny_after_stack_deletion():
    template = yaml.load((Path(__file__).parents[2] / 'template.yaml').read_text(), Loader=CloudFormationLoader)
    policy = template['Resources']['DocumentsBucketTlsPolicy']
    assert policy['DeletionPolicy'] == 'Retain'
    assert policy['UpdateReplacePolicy'] == 'Retain'
    assert policy['Properties']['Bucket'] == 'PolicyAssistantDocumentsBucket'
    deny = policy['Properties']['PolicyDocument']['Statement'][0]
    assert deny['Effect'] == 'Deny'
    assert deny['Condition']['Bool']['aws:SecureTransport'] == 'false'
