"""Check generated HTML internal href/src targets and fragments without network access."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'a' and attrs.get('name'):
            self.ids.add(attrs['name'])
        for key in ('href', 'src'):
            if attrs.get(key):
                self.links.append(attrs[key])


def check(root, base):
    root = Path(root).resolve()
    if not (root / 'index.html').is_file():
        raise ValueError('Site root must contain index.html')
    origin = urlsplit(base)
    prefix = origin.path.rstrip('/') + '/'
    pages = {}
    for path in root.rglob('*.html'):
        parser = Links()
        parser.feed(path.read_text(encoding='utf-8'))
        pages[path] = parser
    failures = []
    checked = 0
    for path, parser in pages.items():
        page_url = urljoin(base, path.relative_to(root).as_posix())
        for value in parser.links:
            target = urlsplit(urljoin(page_url, value))
            if target.scheme not in ('http', 'https') or target.netloc != origin.netloc:
                continue
            checked += 1
            decoded = unquote(target.path)
            if not decoded.startswith(prefix):
                failures.append({'page':path.relative_to(root).as_posix(), 'target':value, 'reason':'outside configured site prefix'})
                continue
            candidate = (root / decoded[len(prefix):]).resolve()
            if not candidate.is_relative_to(root):
                failures.append({'page':path.relative_to(root).as_posix(), 'target':value, 'reason':'outside output directory'})
                continue
            if candidate.is_dir():
                candidate /= 'index.html'
            reason = None
            if not candidate.is_file():
                reason = 'missing file'
            elif target.fragment and candidate in pages and unquote(target.fragment) not in pages[candidate].ids:
                reason = 'missing fragment'
            if reason:
                failures.append({'page':path.relative_to(root).as_posix(), 'target':value, 'reason':reason})
    return {'scope':'Generated local HTML href/src and fragment targets; no external requests or publication verified',
        'html_pages':len(pages),'internal_references_checked':checked,'failures':failures,'passed':not failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-root', required=True)
    parser.add_argument('--base-url', default='https://huynhhao080.github.io/aws-internship-worklog/')
    parser.add_argument('--output', default='docs/evidence/worklog-links.json')
    args = parser.parse_args()
    result = check(args.site_root, args.base_url)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Checked {result['html_pages']} HTML pages, {result['internal_references_checked']} references; failures={len(result['failures'])}")
    for failure in result['failures'][:20]:
        print(failure)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
