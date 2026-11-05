import json
from pathlib import Path
import zipfile

import pytest

from scripts import source_bundle as bundle


@pytest.fixture
def source(tmp_path):
    root = tmp_path / 'source'
    for name in bundle.REQUIRED:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('fixture\n', encoding='utf-8')
    return root


def test_archive_is_deterministic_and_excludes_local_auth_builds(source):
    ignored = ['session.json', 'upload_url.txt', 'downloaded.pdf', '.aws/credentials',
               'frontend/config.json', 'frontend/node_modules/package/index.js',
               'frontend/dist/index.html', 'docs/.env.production',
               'scripts/__pycache__/module.pyc', '.aws-sam/build/template.yaml']
    for name in ignored:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('private-or-generated')
    first = source / '.deployment/first.zip'
    second = source / '.deployment/second.zip'
    assert bundle.create(source, first)['sha256'] == bundle.create(source, second)['sha256']
    with zipfile.ZipFile(first) as archive:
        assert set(ignored).isdisjoint(archive.namelist())
        manifest = json.loads(archive.read(bundle.MANIFEST))
        assert len(manifest['files']) == len(bundle.REQUIRED)
    extracted = source.parent / 'fresh'
    assert bundle.verify(first, extracted)['checksums_verified'] is True
    assert (extracted / 'policy_assistant/app.py').read_text() == 'fixture\n'
    with pytest.raises(FileExistsError):
        bundle.verify(first, extracted)


def test_no_overwrite_or_source_directory_output(source):
    with pytest.raises(ValueError, match='only below'):
        bundle.create(source, source / 'docs/release.zip')
    output = source / '.deployment/snapshot.zip'
    bundle.create(source, output)
    before = output.read_bytes()
    with pytest.raises(ValueError, match='overwrite'):
        bundle.create(source, output)
    assert output.read_bytes() == before


def test_missing_required_file_stops_before_archive_creation(source):
    (source / 'frontend/package-lock.json').unlink()
    output = source / '.deployment/snapshot.zip'
    with pytest.raises(ValueError, match='missing'):
        bundle.create(source, output)
    assert not output.exists()


def test_secret_pattern_stops_export_without_printing_the_secret(source):
    secret = 'AK' + 'IA' + 'A' * 16
    (source / 'README.md').write_text(secret)
    output = source / '.deployment/snapshot.zip'
    with pytest.raises(ValueError) as error:
        bundle.create(source, output)
    assert secret not in str(error.value)
    assert 'aws_access_key' in str(error.value)
    assert not output.exists()


@pytest.mark.parametrize('name', ['../outside.py', '/absolute.py', 'C:/outside.py', 'docs\\outside.py', 'docs/NUL.py', 'docs/folder./x.py'])
def test_unsafe_archive_entries_cannot_be_extracted(tmp_path, name):
    archive_path = tmp_path / 'bad.zip'
    with zipfile.ZipFile(archive_path, 'w') as archive:
        entry = zipfile.ZipInfo()
        entry.filename = name  # Preserve raw backslashes; Windows' constructor normalizes them.
        archive.writestr(entry, b'unsafe')
    target = tmp_path / 'must-not-exist'
    with pytest.raises(ValueError, match='Unsafe'):
        bundle.verify(archive_path, target)
    assert not target.exists()


def test_tampered_source_is_rejected_before_extraction(source):
    good = source / '.deployment/good.zip'
    bad = source / '.deployment/tampered.zip'
    bundle.create(source, good)
    with zipfile.ZipFile(good) as original, zipfile.ZipFile(bad, 'w') as changed:
        for entry in original.infolist():
            changed.writestr(entry, b'changed' if entry.filename == 'README.md' else original.read(entry))
    target = source.parent / 'must-not-exist'
    with pytest.raises(ValueError, match='checksum'):
        bundle.verify(bad, target)
    assert not target.exists()


def test_even_a_matching_manifest_cannot_include_private_runtime_config(source):
    good = source / '.deployment/good.zip'
    bad = source / '.deployment/private.zip'
    bundle.create(source, good)
    data = b'configuration'
    with zipfile.ZipFile(good) as original, zipfile.ZipFile(bad, 'w') as changed:
        manifest = json.loads(original.read(bundle.MANIFEST))
        manifest['files'].append({'path': 'frontend/config.json', 'bytes': len(data), 'sha256': bundle.digest(data)})
        for entry in original.infolist():
            if entry.filename != bundle.MANIFEST:
                changed.writestr(entry, original.read(entry))
        changed.writestr(bundle.MANIFEST, json.dumps(manifest))
        changed.writestr('frontend/config.json', data)
    with pytest.raises(ValueError, match='allowlist'):
        bundle.verify(bad)
