"""Synchronize reviewed, dated technical notes; never publish or edit personal logs.

Default is a read-only drift check. --apply backs up every changed destination
under the application .deployment directory before updating the worklog.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
BEGIN = '<!-- policy-assistant-managed:begin -->'
END = '<!-- policy-assistant-managed:end -->'
PAGES = (
    '8-PolicyAssistant/_index', '2-Proposal/_index', '0-Audit/_index',
    '0-Audit/student-evidence', '5-Workshop/5.7-PolicyAssistant/_index',
    '5-Workshop/5.7-PolicyAssistant/Demo/_index',
    '5-Workshop/5.7-PolicyAssistant/Cost/_index',
    '3-BlogsPosted/3.4-Ownership/_index',
    '3-BlogsPosted/3.5-SignedUploads/_index',
    '3-BlogsPosted/3.6-QueueFailures/_index',
)
GUIDES = {
    'current': '5-Workshop/5.7-PolicyAssistant/CurrentRelease',
    'validity': '5-Workshop/5.7-PolicyAssistant/PolicyValidity',
    'support': '5-Workshop/5.7-PolicyAssistant/SupportTeam',
    'proposal': '2-Proposal/CurrentSolution',
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def overlay(original: str, body: str) -> str:
    """Replace only our block or insert after front matter, preserving history."""
    block = f'{BEGIN}\n{body.strip()}\n{END}'
    if original.count(BEGIN) != original.count(END) or original.count(BEGIN) > 1:
        raise ValueError('Malformed or duplicate managed markers')
    if BEGIN in original:
        start, end = original.index(BEGIN), original.index(END)
        if end < start:
            raise ValueError('Reversed managed markers')
        return original[:start] + block + original[end + len(END):]
    front = re.match(r'\A---\r?\n.*?\r?\n---(?:\r?\n|$)', original, re.S)
    if not front:
        raise ValueError('Expected YAML front matter; refusing to rewrite page')
    pos = front.end()
    return original[:pos] + '\n' + block + '\n' + original[pos:]


def evidence(source: Path) -> dict:
    """Explicit allowlist, rather than copying operator reports to a public site."""
    live_path = source / 'docs/quality-live-acceptance.json'
    artifact_path = source / 'docs/quality-artifact-verification.json'
    live = json.loads(live_path.read_text(encoding='utf-8'))
    artifact = json.loads(artifact_path.read_text(encoding='utf-8'))
    if live['release'] != artifact['release']:
        raise ValueError('Acceptance and artifact reports describe different releases')
    required = ('http_passed', 'accounts_cleaned', 'fixture_cleaned', 'history_purged')
    if not all(live.get(key) is True for key in required):
        raise ValueError('Live acceptance or cleanup is incomplete')
    functions = artifact['deployed_functions']
    release_sha = live['release']['code_sha256']
    if len(functions) != 6 or any(f['code_sha256'] != release_sha or f['update_status'] != 'Successful' for f in functions):
        raise ValueError('Lambda artifact evidence is incomplete')
    if artifact['stack_status'] != 'UPDATE_COMPLETE' or artifact['invalidation_status'] != 'Completed':
        raise ValueError('Release publication evidence is incomplete')
    return {
        'schema_version': 1,
        'acceptance_checked_at': live['checked_at'],
        'artifact_checked_at': artifact['checked_at'],
        'primary_url': 'https://djreo5eptvwk5.cloudfront.net/',
        'stack': live['release']['stack'],
        'code_sha256': release_sha,
        'template_sha256': live['release']['template_sha256'],
        'live_checks': live['checks'],
        'cleanup': {key: live[key] for key in required},
        'verified_lambda_artifacts': len(functions),
        'verified_frontend_files': len(artifact['files']),
        'scope': live['scope'],
        'method': artifact['method'],
        'source_reports': {str(p.relative_to(source)).replace('\\', '/'): sha(p.read_bytes()) for p in (live_path, artifact_path)},
        'limits': ['Historical acceptance, not a new live run or CI result.',
                   'No new model, visual browser, load, restore or alert-delivery acceptance.',
                   'No customer IDs, questions, answers, JWTs or operator credentials exported.',
                   'Academic evidence and student authorship remain pending.'],
    }


def validity_evidence(source: Path) -> dict:
    paths = [source / ('docs/policy-validity-' + kind + '.json') for kind in ('live-acceptance', 'artifact-verification')]
    live, artifact = [json.loads(path.read_text(encoding='utf-8')) for path in paths]
    if live['release'] != artifact['release']:
        raise ValueError('Validity reports describe different releases')
    flags = ('http_passed', 'accounts_cleaned', 'policies_cleaned')
    if not all(live.get(key) is True for key in flags):
        raise ValueError('Validity acceptance or cleanup is incomplete')
    if (artifact['stack_status'] != 'UPDATE_COMPLETE' or artifact['invalidation_status'] != 'Completed'
            or len(artifact['deployed_functions']) != 6
            or any(f['code_sha256'] != live['release']['code_sha256'] or f['update_status'] != 'Successful' for f in artifact['deployed_functions'])):
        raise ValueError('Validity artifact verification is incomplete')
    return {'schema_version': 1, 'checked_at': live['checked_at'], 'scope': live['scope'],
            'code_sha256': live['release']['code_sha256'], 'template_sha256': live['release']['template_sha256'],
            'checks': live['checks'], 'cleanup': {key: live[key] for key in flags},
            'verified_frontend_files': len(artifact['files']), 'verified_lambda_artifacts': 6,
            'cloudfront_invalidation': artifact['invalidation_status'],
            'source_report_hash_format': 'SHA256 of UTF-8 canonical JSON: sorted keys, ensure_ascii=False, separators comma/colon, no trailing newline',
            'source_reports': {p.relative_to(source).as_posix(): json_report_sha(p) for p in paths},
            'limits': ['Operator-seeded inactive policies and draft/read APIs only, not model or publication acceptance.',
                       'No new browser visual, load, restore or AI accuracy result.']}


def support_evidence(source: Path) -> dict:
    paths = [source / ('docs/support-team-' + kind + '.json') for kind in ('live-acceptance', 'artifact-verification')]
    live, artifact = [json.loads(path.read_text(encoding='utf-8')) for path in paths]
    if live['release'] != artifact['release']:
        raise ValueError('Support reports describe different releases')
    flags = ('http_passed', 'accounts_cleaned', 'support_purged')
    if not all(live.get(key) is True for key in flags):
        raise ValueError('Support acceptance or cleanup is incomplete')
    if (artifact['stack_status'] != 'UPDATE_COMPLETE' or artifact['invalidation_status'] != 'Completed'
            or len(artifact['deployed_functions']) != 6
            or any(f['code_sha256'] != live['release']['code_sha256'] or f['update_status'] != 'Successful' for f in artifact['deployed_functions'])):
        raise ValueError('Support artifact verification is incomplete')
    return {'schema_version': 1, 'checked_at': live['checked_at'], 'scope': live['scope'],
            'code_sha256': live['release']['code_sha256'], 'template_sha256': live['release']['template_sha256'],
            'checks': live['checks'], 'cleanup': {key: live[key] for key in flags},
            'verified_frontend_files': len(artifact['files']), 'verified_lambda_artifacts': 6,
            'cloudfront_invalidation': artifact['invalidation_status'],
            'source_report_hash_format': 'SHA256 of UTF-8 canonical JSON: sorted keys, ensure_ascii=False, separators comma/colon, no trailing newline',
            'source_reports': {p.relative_to(source).as_posix(): json_report_sha(p) for p in paths},
            'limits': ['Synthetic support HTTP acceptance; no model, PDF/OCR, email delivery or real customer processing.',
                       'No new visual browser, load, restore, SLA or student authorship acceptance.']}


def json_report_sha(path: Path) -> str:
    # Git normalizes line endings; evidence hashes must survive publication.
    data = json.loads(path.read_text(encoding='utf-8'))
    return sha(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


def target_file(target: Path, relative: str) -> Path:
    path = target / relative
    # Existing directory links must not redirect an authorized write elsewhere.
    if not path.resolve().is_relative_to(target.resolve()):
        raise ValueError(f'Destination escapes worklog: {relative}')
    return path


def plan(source: Path, target: Path) -> dict[Path, bytes]:
    result = {}
    template_root = source / 'docs/fcaj/worklog'
    for lang, suffix in (('en', '.md'), ('vi', '.vi.md')):
        notice = (template_root / f'notice.{lang}.md').read_text(encoding='utf-8')
        for page in PAGES:
            path = target_file(target, f'content/{page}{suffix}')
            original = path.read_bytes().decode('utf-8')
            result[path] = overlay(original, notice).encode('utf-8')
        for name, page in GUIDES.items():
            path = target_file(target, f'content/{page}/_index{suffix}')
            result[path] = (template_root / f'{name}.{lang}.md').read_bytes()
    result[target_file(target, 'static/evidence/policy-assistant-2026-11-04.json')] = (json.dumps(evidence(source), ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    result[target_file(target, 'static/evidence/policy-validity-2026-11-05.json')] = (json.dumps(validity_evidence(source), ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    result[target_file(target, 'static/evidence/support-team.json')] = (json.dumps(support_evidence(source), ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    return {p: data for p, data in result.items() if not p.exists() or p.read_bytes() != data}


def validate_repository(target: Path) -> None:
    remote = subprocess.run(['git', '-C', str(target), 'remote', 'get-url', 'origin'], check=True, capture_output=True, text=True).stdout.strip()
    allowed = ('https://github.com/HuynhHao080/aws-internship-worklog.git',
               'git@github.com:HuynhHao080/aws-internship-worklog.git')
    if remote not in allowed or not (target / 'config.toml').is_file():
        raise ValueError('Expected the authoritative aws-internship-worklog repository')


def apply(changes: dict[Path, bytes], target: Path, backup_root: Path) -> Path:
    backup_root.mkdir(parents=True, exist_ok=False)
    records = []
    # Back up the complete plan before the first destination mutation.
    for path, data in changes.items():
        relative = path.relative_to(target)
        old = path.read_bytes() if path.exists() else None
        if old is not None:
            backup = backup_root / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(old)
        records.append({'path': relative.as_posix(), 'before_sha256': sha(old) if old is not None else None, 'after_sha256': sha(data)})
    manifest = backup_root / 'manifest.json'
    manifest.write_text(json.dumps({'target': str(target), 'files': records}, indent=2) + '\n', encoding='utf-8')
    for path, data in changes.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worklog', type=Path, required=True)
    parser.add_argument('--apply', action='store_true', help='Apply the reviewed plan with local backups; no Git/cloud publication')
    args = parser.parse_args()
    target = args.worklog.resolve()
    validate_repository(target)
    changes = plan(ROOT, target)
    print(json.dumps({'mode': 'apply' if args.apply else 'check', 'changed_files': [p.relative_to(target).as_posix() for p in changes]}, ensure_ascii=False, indent=2))
    if args.apply and changes:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        print('Backup manifest:', apply(changes, target, ROOT / '.deployment' / f'worklog-sync-{stamp}'))
    return 0 if args.apply or not changes else 1


if __name__ == '__main__':
    raise SystemExit(main())
