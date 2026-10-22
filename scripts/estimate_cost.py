"""Reproduce a planning estimate from the dated public AWS rate snapshot (no AWS API calls)."""
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render():
    data = json.loads((ROOT / 'docs/cost/aws-rates-2026-10-21.json').read_text(encoding='utf-8'))
    lines = ['| Component | Monthly quantity | USD/unit | USD/month |', '|---|---:|---:|---:|']
    total = Decimal(0)
    for row in data['rows']:
        cost = Decimal(str(row['quantity'])) * Decimal(row['rate_usd'])
        total += cost
        lines.append(f"| {row['name']} | {row['quantity']} {row['unit']} | {row['rate_usd']} | {cost:.6f} |")
    lines.append(f'| **Total before allowances/credits/tax** | | | **{total:.4f}** |')
    (ROOT / 'docs/cost/monthly-table.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    # At 10x application traffic the scheduled recovery and monitoring baseline stay fixed.
    fixed = {'CloudWatch dashboard', 'CloudWatch standard alarms', 'SNS publish', 'SNS email notifications'}
    scaled = sum(Decimal(str(r['quantity'])) * Decimal(r['rate_usd']) * (1 if r['name'] in fixed else 10) for r in data['rows'])
    # The 270 GB-seconds / 21,600 requests for recovery are fixed, not proportional to uploads.
    scaled -= Decimal(9) * (Decimal(270) * Decimal('0.0000166667') + Decimal(21600) * Decimal('0.0000002'))
    result = {'date': data['verified_date'], 'currency': 'USD', 'base_month_usd': str(total), 'ten_times_usage_usd': str(scaled), 'actual_bill': 'NOT measured; no Free Tier or credits applied', 'calculator_estimate_url': None}
    (ROOT / 'docs/cost/estimate-result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    render()
