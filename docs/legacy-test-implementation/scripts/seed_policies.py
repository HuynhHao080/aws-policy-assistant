"""Preview bundled policy fixtures; --apply writes only missing IDs to the reviewed stack table."""
import argparse
import json
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[1]


def seed(table, items):
    created = skipped = 0
    for item in items:
        try:
            table.put_item(Item=item, ConditionExpression='attribute_not_exists(policy_id)')
            created += 1
        except ClientError as error:
            if error.response['Error']['Code'] != 'ConditionalCheckFailedException':
                raise
            skipped += 1
    return {'created': created, 'existing_preserved': skipped}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stack', default='policy-assistant')
    parser.add_argument('--region', default='ap-southeast-1')
    parser.add_argument('--apply', action='store_true', help='Requires owner authorization for these AWS writes')
    args = parser.parse_args()
    items = json.loads((ROOT / 'sample_data/policies.json').read_text(encoding='utf-8'))
    if not args.apply:
        print(f'PREVIEW: {len(items)} synthetic policy records; existing IDs will be preserved. No AWS calls made.')
        return 0
    try:
        stack = boto3.client('cloudformation', region_name=args.region).describe_stacks(StackName=args.stack)['Stacks'][0]
        outputs = {item['OutputKey']: item['OutputValue'] for item in stack['Outputs']}
        table = boto3.resource('dynamodb', region_name=args.region).Table(outputs['PoliciesTableName'])
        print(json.dumps(seed(table, items)))
        return 0
    except Exception as error:
        print(f'Seed failed ({type(error).__name__}); partial creates may exist. Re-running preserves existing IDs.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
