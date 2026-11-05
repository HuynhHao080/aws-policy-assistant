"""Protect historical evidence and prevent cross-repository writes."""
import json
from pathlib import Path
import subprocess

import pytest

from scripts import sync_fcaj_worklog as sync


def test_overlay_preserves_original_frontmatter_and_history():
    original = '---\r\ntitle: history\r\n---\r\n\r\nB5 FAIL\r\nB5-R7 PASS\r\n'
    updated = sync.overlay(original, 'current evidence')
    assert updated.startswith('---\r\ntitle: history\r\n---\r\n')
    assert updated.endswith('\r\nB5 FAIL\r\nB5-R7 PASS\r\n')
    assert sync.overlay(updated, 'current evidence') == updated
    assert sync.overlay(updated, 'new evidence').count(sync.BEGIN) == 1


@pytest.mark.parametrize('bad', [
    'no front matter',
    f'---\ntitle: x\n---\n{sync.BEGIN}',
    f'---\ntitle: x\n---\n{sync.END}{sync.BEGIN}',
    f'---\ntitle: x\n---\n{sync.BEGIN}{sync.END}{sync.BEGIN}{sync.END}',
])
def test_overlay_refuses_malformed_documents(bad):
    with pytest.raises(ValueError):
        sync.overlay(bad, 'new')


def test_only_expected_remote_is_allowed(tmp_path, monkeypatch):
    (tmp_path / 'config.toml').write_text('baseURL="example"')
    monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: subprocess.CompletedProcess(a, 0, stdout='https://github.com/someone/reference.git\n'))
    with pytest.raises(ValueError, match='authoritative'):
        sync.validate_repository(tmp_path)


def test_target_cannot_escape_authorized_root(tmp_path):
    with pytest.raises(ValueError, match='escapes'):
        sync.target_file(tmp_path, '../outside.md')


def test_backup_records_exact_old_bytes_and_new_files(tmp_path):
    target = tmp_path / 'worklog'
    target.mkdir()
    old = target / 'old.md'
    new = target / 'new.md'
    old.write_bytes(b'B5 FAIL\r\n')
    backup = tmp_path / 'backup'
    manifest = sync.apply({old: b'new\nB5 FAIL\r\n', new: b'guide'}, target, backup)
    assert (backup / 'old.md').read_bytes() == b'B5 FAIL\r\n'
    records = json.loads(manifest.read_text())['files']
    assert records[0]['before_sha256'] == sync.sha(b'B5 FAIL\r\n')
    assert records[1]['before_sha256'] is None
    assert new.read_bytes() == b'guide'


def test_export_contains_no_operator_identifiers_or_private_text(tmp_path):
    exported = sync.evidence(sync.ROOT)
    assert len(exported['live_checks']) == 15
    assert exported['verified_lambda_artifacts'] == 6
    validity = sync.validity_evidence(sync.ROOT)
    assert len(validity['checks']) == 16 and validity['cleanup']['policies_cleaned']
    support = sync.support_evidence(sync.ROOT)
    assert len(support['checks']) == 20 and support['cleanup']['support_purged']
    for result in (exported, validity, support):
        serialized = json.dumps(result)
        for forbidden in ('change_set_id', 'arn:aws:', '629380420098', 'huynhhao080@', 'conversation_id', 'owner_id', 'validity-qa-', 'support-team-qa-'):
            assert forbidden not in serialized
    first, second = tmp_path / 'windows.json', tmp_path / 'github.json'
    first.write_bytes(b'{\r\n  "a": 1, "b": 2\r\n}\r\n')
    second.write_bytes(b'{"b":2,"a":1}\n')
    assert sync.json_report_sha(first) == sync.json_report_sha(second)


def test_mismatched_or_incomplete_evidence_stops_export(tmp_path):
    docs = tmp_path / 'docs'
    docs.mkdir()
    for name in ('quality-live-acceptance.json', 'quality-artifact-verification.json'):
        (docs / name).write_bytes((sync.ROOT / 'docs' / name).read_bytes())
    live_path = docs / 'quality-live-acceptance.json'
    live = json.loads(live_path.read_text())
    live['accounts_cleaned'] = False
    live_path.write_text(json.dumps(live))
    with pytest.raises(ValueError, match='cleanup'):
        sync.evidence(tmp_path)
    live['accounts_cleaned'] = True
    live['release']['code_sha256'] = 'different release'
    live_path.write_text(json.dumps(live))
    with pytest.raises(ValueError, match='different releases'):
        sync.evidence(tmp_path)
