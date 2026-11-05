"""Offline checks for the managed bilingual worklog pages and built assets.

Does not start a browser or assert visual acceptance or public availability.
"""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from scripts import sync_fcaj_worklog as sync


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'img') and attrs.get('src'):
            self.assets.append(attrs['src'])
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.assets.append(attrs['href'])
        if tag == 'a' and attrs.get('href'):
            self.hrefs.append(attrs['href'])


def built_file(build: Path, url: str) -> Path:
    parts = urlsplit(url)
    if parts.netloc and parts.netloc != 'huynhhao080.github.io':
        raise ValueError('Only local worklog paths can be resolved')
    prefix = '/aws-internship-worklog/'
    path = unquote(parts.path)
    if not path.startswith(prefix):
        raise ValueError(f'Unexpected site base path: {url}')
    relative = path[len(prefix):]
    result = build / relative
    if path.endswith('/'):
        result = result / 'index.html'
    if not result.resolve().is_relative_to(build.resolve()):
        raise ValueError('URL escapes build directory')
    return result


def verify(worklog: Path, build: Path, backup: Path) -> dict:
    sync.validate_repository(worklog)
    if sync.plan(sync.ROOT, worklog):
        raise ValueError('Worklog differs from reviewed source templates/evidence')
    manifest = json.loads((backup / 'manifest.json').read_text(encoding='utf-8'))
    if Path(manifest['target']).resolve() != worklog.resolve():
        raise ValueError('Backup belongs to a different worklog')
    preserved = 0
    for record in manifest['files']:
        if record['before_sha256'] is None:
            continue
        old = (backup / record['path']).read_bytes()
        if sync.sha(old) != record['before_sha256']:
            raise ValueError('Backup checksum mismatch')
        current = (worklog / record['path']).read_bytes()
        start, end = sync.BEGIN.encode(), sync.END.encode()
        left, body = current.split(b'\n' + start, 1)
        _, right = body.split(end + b'\n', 1)
        if left + right != old:
            raise ValueError(f'Historical bytes modified: {record["path"]}')
        preserved += 1
    pages, assets = [], set()
    for language, prefix in (('en', ''), ('vi', 'vi/')):
        route = f'/aws-internship-worklog/{prefix}5-workshop/5.7-policyassistant/currentrelease/'
        page = built_file(build, route)
        html = page.read_text(encoding='utf-8')
        if '\ufffd' in html or '{{<' in html:
            raise ValueError('Encoding replacement or unrendered shortcode')
        parser = Links()
        parser.feed(html)
        for url in parser.assets:
            if urlsplit(url).scheme or url.startswith('//'):
                continue  # No network checks or claims about external availability.
            if not built_file(build, url).is_file():
                raise ValueError(f'Missing built asset: {url}')
            assets.add(urlsplit(url).path)
        evidence_url = '/aws-internship-worklog/evidence/policy-assistant-2026-11-04.json'
        if evidence_url not in parser.hrefs:
            raise ValueError('Evidence download link missing')
        if json.loads(built_file(build, evidence_url).read_text(encoding='utf-8')) != sync.evidence(sync.ROOT):
            raise ValueError('Built evidence differs from allowlisted export')
        for name in sync.PAGES:
            # Hugo default path generation lowercases directory names.
            slug = name.removesuffix('/_index')
            destination = built_file(build, '/aws-internship-worklog/' + prefix + slug.lower() + '/')
            links = Links()
            links.feed(destination.read_text(encoding='utf-8'))
            if route not in links.hrefs and 'https://huynhhao080.github.io' + route not in links.hrefs:
                raise ValueError(f'Managed release link missing in {destination}')
        pages.append({'language': language, 'path': str(page)})
    return {'historical_files_preserved_byte_for_byte': preserved,
            'managed_pages': len(sync.PAGES) * 2,
            'new_release_pages': pages, 'local_assets_resolved': len(assets),
            'evidence_export_matches': True, 'synchronization_drift': False,
            'scope': 'Offline source preservation, generated links/assets and sanitized JSON only; no browser, publication, cloud or model checks.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worklog', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.worklog.resolve(), args.build.resolve(), args.backup.resolve())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
