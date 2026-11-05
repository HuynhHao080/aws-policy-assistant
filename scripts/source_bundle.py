"""Create/verify an offline source handover without Git, AWS or publication.

Only explicit source directories/files are eligible. Archives have normalized
metadata and a per-file SHA256 manifest. Pattern checks supplement manual review;
they are not a complete secret audit or a public-release approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = ('README.md', '.gitignore', 'template.yaml', 'pytest.ini')
DIRECTORIES = ('policy_assistant', 'frontend', 'tests', 'scripts', 'docs')
SKIP = {'node_modules', 'dist', '__pycache__', '.pytest_cache', '.git', '.aws', '.aws-sam', '.deployment'}
EXTENSIONS = {'.py', '.md', '.json', '.csv', '.txt', '.html', '.js', '.mjs', '.cjs', '.css', '.woff2', '.ttf'}
REQUIRED = {'README.md', 'template.yaml', 'pytest.ini', '.github/workflows/ci.yml',
            'policy_assistant/app.py', 'policy_assistant/requirements.txt',
            'tests/requirements.txt', 'frontend/package-lock.json',
            'frontend/build.mjs', 'frontend/config.example.json'}
MANIFEST = 'SOURCE-MANIFEST.json'
MAX_BYTES = 50 * 1024 * 1024
PATTERNS = {
    'aws_access_key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'jwt': re.compile(r'\beyJ[A-Za-z0-9_-]{17,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b'),
    'signed_url': re.compile(r'(?:X-Amz-Signature|X-Amz-Security-Token)=[A-Za-z0-9%+/]{32,}', re.I),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scan(name: str, data: bytes) -> None:
    if Path(name).suffix in {'.woff2', '.ttf'}:
        return
    text = data.decode('utf-8')
    for label, pattern in PATTERNS.items():
        if pattern.search(text):
            # Never print the match or surrounding potentially sensitive text.
            raise ValueError(f'Secret-pattern review required: {name} ({label})')


def safe_name(name: str) -> None:
    path = PurePosixPath(name)
    devices = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{prefix}{n}' for prefix in ('COM', 'LPT') for n in range(1, 10)}
    if (not name or '\\' in name or ':' in name or '\x00' in name or path.is_absolute()
            or any(part in {'', '.', '..'} or part.endswith(('.', ' '))
                   or part.split('.')[0].upper() in devices for part in name.split('/'))):
        raise ValueError('Unsafe archive path')


def eligible(name: str) -> bool:
    safe_name(name)
    if name in ROOT_FILES or name == '.github/workflows/ci.yml':
        return True
    path = PurePosixPath(name)
    return (path.parts[0] in DIRECTORIES and len(path.parts) > 1
            and not any(p in SKIP or p.startswith('.env') for p in path.parts)
            and path.suffix.lower() in EXTENSIONS
            and name != 'frontend/config.json')


def collect(root: Path) -> dict[str, bytes]:
    root = root.resolve()
    result = {}

    def add(path: Path):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Linked source files are not eligible')
        name = path.relative_to(root).as_posix()
        if not eligible(name):
            return
        data = path.read_bytes()
        scan(name, data)
        result[name] = data

    for name in ROOT_FILES + ('.github/workflows/ci.yml',):
        path = root / name
        if path.is_file():
            add(path)
    for directory in DIRECTORIES:
        start = root / directory
        if start.is_symlink():
            raise ValueError('Linked source directories are not eligible')
        for parent, dirs, names in os.walk(start, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in SKIP)
            if any((Path(parent) / d).is_symlink() for d in dirs):
                raise ValueError('Linked source directories are not eligible')
            for name in sorted(names):
                path = Path(parent) / name
                if name.startswith('.env') or path.suffix.lower() not in EXTENSIONS:
                    continue
                if directory == 'frontend' and name == 'config.json':
                    continue
                add(path)
    missing = REQUIRED - result.keys()
    if missing:
        raise ValueError('Required source files missing: ' + ', '.join(sorted(missing)))
    if sum(map(len, result.values())) > MAX_BYTES:
        raise ValueError('Source handover exceeds size limit')
    # Fail closed on case collisions, especially when extracted on Windows.
    if len({name.casefold() for name in result}) != len(result):
        raise ValueError('Case-colliding source paths')
    return dict(sorted(result.items()))


def create(root: Path, output: Path) -> dict:
    root, output = root.resolve(), output.resolve()
    if not output.is_relative_to(root / '.deployment'):
        raise ValueError('Write source bundles only below the repository .deployment directory')
    if output.exists():
        raise ValueError('Refusing to overwrite an existing handover')
    files = collect(root)
    manifest = {
        'schema_version': 1,
        'scope': 'Local source snapshot; not Git/Pages publication, live acceptance or final secret audit.',
        'files': [{'path': name, 'bytes': len(data), 'sha256': digest(data)} for name, data in files.items()],
        'exclusions': ['Git history, generated builds, dependencies, deployment state, real frontend config, root authentication/URL/PDF artifacts, reference submodule and separate worklog'],
    }
    files[MANIFEST] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
    return {'archive': str(output), 'sha256': digest(output.read_bytes()), 'source_files': len(manifest['files']), 'bytes': output.stat().st_size}


def verify(archive_path: Path, extract_to: Path | None = None) -> dict:
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        if len({e.filename.casefold() for e in entries}) != len(entries):
            raise ValueError('Duplicate/case-colliding archive paths')
        if sum(e.file_size for e in entries) > MAX_BYTES:
            raise ValueError('Archive exceeds uncompressed size limit')
        for entry in entries:
            # ZipInfo normalizes backslashes on Windows and truncates NULs;
            # validate the original central-directory name as well.
            safe_name(entry.orig_filename)
            safe_name(entry.filename)
            if entry.is_dir() or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Directory/link entries are not allowed')
        manifest = json.loads(archive.read(MANIFEST))
        if manifest.get('schema_version') != 1:
            raise ValueError('Unknown manifest schema')
        records = manifest['files']
        paths = [r['path'] for r in records]
        if len(set(paths)) != len(paths) or set(paths) | {MANIFEST} != {e.filename for e in entries}:
            raise ValueError('Manifest/archive file set mismatch')
        if REQUIRED - set(paths):
            raise ValueError('Required source files missing from archive')
        files = {}
        for record in records:
            name = record['path']
            if not eligible(name):
                raise ValueError('Archive contains a file outside the source allowlist')
            data = archive.read(name)
            if len(data) != record['bytes'] or digest(data) != record['sha256']:
                raise ValueError('Source checksum mismatch: ' + name)
            scan(name, data)
            files[name] = data
        if extract_to is not None:
            extract_to = extract_to.resolve()
            extract_to.mkdir(parents=True, exist_ok=False)
            for name, data in files.items():
                destination = extract_to / name
                if not destination.resolve().is_relative_to(extract_to):
                    raise ValueError('Extraction path escaped target')
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
            (extract_to / MANIFEST).write_bytes(archive.read(MANIFEST))
    return {'sha256': digest(archive_path.read_bytes()), 'source_files': len(files), 'checksums_verified': True,
            'extracted_to': str(extract_to) if extract_to else None,
            'scope': 'Offline archive integrity/pattern checks only; not proof of production readiness or absence of all secrets.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('create')
    build.add_argument('--output', type=Path, required=True)
    check = commands.add_parser('verify')
    check.add_argument('--archive', type=Path, required=True)
    check.add_argument('--extract-to', type=Path)
    args = parser.parse_args()
    result = create(ROOT, args.output) if args.command == 'create' else verify(args.archive, args.extract_to)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
