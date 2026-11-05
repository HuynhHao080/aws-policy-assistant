"""Inclusive business dates in Vietnam (UTC+07), independent of Lambda timezone."""
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import re

DATE_FIELDS = ('effective_from', 'effective_until')


def today():
    return datetime.now(timezone(timedelta(hours=7))).date().isoformat()


def bounds(data, previous=None):
    result = {}
    for field in DATE_FIELDS:
        value = data[field] if field in data else (previous or {}).get(field)
        if value is None or value == '':
            continue
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError('Policy dates must use YYYY-MM-DD')
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError('Policy dates must be real calendar dates') from None
        result[field] = value
    if result.get('effective_from', '') > result.get('effective_until', '9999-12-31'):
        raise ValueError('Policy end date must not precede its start date')
    return result


def state(item, day=None):
    try:
        window = bounds(item)
    except ValueError:
        return 'invalid'
    day = today() if day is None else day
    if window.get('effective_from', '') > day:
        return 'upcoming'
    if window.get('effective_until', '9999-12-31') < day:
        return 'expired'
    return 'active'


def active(item):
    return state(item) == 'active'


def signature(item):
    # Published facts only: editing/discarding an isolated draft must not
    # invalidate an unchanged public snapshot. Also covers legacy rows.
    fields = ('policy_id', 'title', 'content', *DATE_FIELDS)
    raw = json.dumps({k: item[k] for k in fields if k in item}, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()
