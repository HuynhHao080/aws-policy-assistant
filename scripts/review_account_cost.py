"""Read-only, bounded account-cost queries; never enable billing features or modify AWS."""
import datetime
from decimal import Decimal
import json
import os
from pathlib import Path

import boto3
from botocore.config import Config

ROOT = Path(__file__).resolve().parents[1]


def error_summary(error):
    code = getattr(error, 'response', {}).get('Error', {}).get('Code')
    return {'status': 'NOT_AVAILABLE' if code == 'DataUnavailableException' else 'BLOCKED',
            'error_type': type(error).__name__, 'aws_error_code': code}


def main():
    os.environ['AWS_EC2_METADATA_DISABLED'] = 'true'
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    assert today.year == 2026 and today.month == 10, 'Re-review the requested October scope if date changes'
    start, cutoff, end = '2026-10-01', today.isoformat(), '2026-11-01'
    report = {'observed_at_utc': now.isoformat(), 'scope': 'Read-only October cost baseline, not an invoice or deployment',
              'account_masked': '********0098', 'metric': 'UnblendedCost', 'currency': 'USD',
              'actual_period': {'Start': start, 'End': cutoff, 'end_exclusive': True},
              'forecast_period': {'Start': cutoff, 'End': end, 'end_exclusive': True},
              'excluded_record_types': ['Credit', 'Refund'], 'ce_requests_attempted': 0,
              'resource_level_attribution': 'NOT_VERIFIED; service/usage-type data does not identify stack ownership'}
    config = Config(connect_timeout=5, read_timeout=20, retries={'max_attempts': 0})
    session = boto3.Session(region_name='ap-southeast-1')
    try:
        state = json.loads((ROOT / '.aws-sam/test-review/pending-change-set.json').read_text())
        account = session.client('sts', config=config).get_caller_identity()['Account']
        assert account == state['account'] and account.endswith('0098')
        report['identity'] = 'VERIFIED'
    except Exception as error:
        report['identity'] = error_summary(error)
        account = None
    if account:
        cost_filter = {'And': [
            {'Dimensions': {'Key': 'LINKED_ACCOUNT', 'Values': [account]}},
            {'Not': {'Dimensions': {'Key': 'RECORD_TYPE', 'Values': ['Credit', 'Refund']}}}]}
        report['filter'] = json.loads(json.dumps(cost_filter).replace(account, '[VERIFIED_ACCOUNT]'))
        ce = session.client('ce', region_name='us-east-1', config=config)
        try:
            periods, token = {}, None
            for _ in range(4):
                args = {'TimePeriod': {'Start': start, 'End': cutoff}, 'Granularity': 'DAILY',
                        'Metrics': ['UnblendedCost'], 'Filter': cost_filter,
                        'GroupBy': [{'Type': 'DIMENSION', 'Key': 'SERVICE'}, {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}]}
                if token:
                    args['NextPageToken'] = token
                report['ce_requests_attempted'] += 1
                data = ce.get_cost_and_usage(**args)
                for period in data['ResultsByTime']:
                    day = period['TimePeriod']['Start']
                    existing = periods.setdefault(day, {'period': period['TimePeriod'], 'estimated': False, 'groups': []})
                    existing['estimated'] |= period.get('Estimated', False)
                    existing['groups'].extend(period['Groups'])
                token = data.get('NextPageToken')
                if not token:
                    break
            assert not token, 'More than four pages; stop instead of unbounded queries'
            daily, services = [], {}
            total = Decimal('0')
            for day, period in sorted(periods.items()):
                amount = Decimal('0')
                for group in period['groups']:
                    metric = group['Metrics']['UnblendedCost']
                    assert metric['Unit'] == 'USD'
                    cost = Decimal(metric['Amount'])
                    service, usage = group['Keys']
                    services.setdefault(service, {'total': Decimal('0'), 'usage_types': {}})
                    services[service]['total'] += cost
                    services[service]['usage_types'][usage] = services[service]['usage_types'].get(usage, Decimal('0')) + cost
                    amount += cost
                total += amount
                daily.append({'date': day, 'amount_usd': str(amount), 'estimated': period['estimated']})
            report['actual'] = {'status': 'VERIFIED', 'amount_usd': str(total), 'days_returned': len(daily), 'daily': daily,
                                'services': {key: {'amount_usd': str(value['total']),
                                    'usage_types_usd': {k: str(v) for k, v in value['usage_types'].items()}}
                                    for key, value in services.items()},
                                'note': 'Accrued costs through completed UTC dates; current day excluded and billing can lag'}
        except Exception as error:
            report['actual'] = error_summary(error)
        try:
            report['ce_requests_attempted'] += 1
            forecast = ce.get_cost_forecast(TimePeriod={'Start': cutoff, 'End': end}, Metric='UNBLENDED_COST',
                                          Granularity='DAILY', Filter=cost_filter, PredictionIntervalLevel=80)
            report['forecast'] = {'status': 'VERIFIED', 'prediction_interval_level': 80,
                                  'remaining_period_total': forecast['Total'], 'daily': forecast['ForecastResultsByTime'],
                                  'note': 'AWS prediction for remaining period, not whole-month total and not a guarantee'}
        except Exception as error:
            report['forecast'] = error_summary(error)
        try:
            budgets = session.client('budgets', region_name='us-east-1', config=config).describe_budgets(AccountId=account, MaxResults=100)
            report['budget_snapshots'] = [{'type': item['BudgetType'], 'limit': item.get('BudgetLimit'),
                'metric': item.get('Metrics'), 'has_filters': bool(item.get('FilterExpression') or item.get('CostFilters')),
                'calculated_spend': item.get('CalculatedSpend'), 'time_unit': item['TimeUnit'],
                'note': 'Not a substitute for the exact CE Credit/Refund exclusion filter'}
                for item in budgets['Budgets'] if item['BudgetType'] == 'COST']
            report['budgets_pagination_complete'] = not bool(budgets.get('NextToken'))
        except Exception as error:
            report['budgets_read'] = error_summary(error)
        try:
            cf = session.client('cloudformation', config=config)
            stack = cf.describe_stacks(StackName='policy-assistant')['Stacks'][0]
            resources = cf.list_stack_resources(StackName='policy-assistant')
            report['existing_stack'] = {'status': stack['StackStatus'], 'last_updated': str(stack.get('LastUpdatedTime')),
                'resource_types': [item['ResourceType'] for item in resources['StackResourceSummaries']],
                'resource_inventory_complete': not bool(resources.get('NextToken')),
                'attribution': 'Inventory correlation only; no billing resource IDs or active stack cost tag proven'}
            plan = cf.describe_change_set(StackName=state['stack'], ChangeSetName=state['change_set_name'])
            assert plan['ChangeSetId'] == state['change_set_id']
            report['test_candidate'] = {'name': state['change_set_name'], 'status': plan['Status'],
                'execution_status': plan['ExecutionStatus'], 'executed_by_this_script': False}
        except Exception as error:
            report['stack_reads'] = error_summary(error)
    report['completed_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report['aws_writes_performed'] = False
    destination = ROOT / 'docs/evidence/aws-october-account-cost.json'
    destination.write_text(json.dumps(report, indent=2, default=str) + '\n', encoding='utf-8')
    summary = {key: value for key, value in report.items() if key not in ['budget_snapshots', 'actual', 'forecast', 'existing_stack']}
    summary['actual'] = {key: value for key, value in report.get('actual', {}).items() if key not in ['daily', 'services']}
    summary['services'] = {key: value['amount_usd'] for key, value in report.get('actual', {}).get('services', {}).items()}
    summary['forecast'] = {key: value for key, value in report.get('forecast', {}).items() if key != 'daily'}
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
