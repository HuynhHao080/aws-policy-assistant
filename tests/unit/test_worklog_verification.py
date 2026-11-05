"""Reject broken generated guides without using a browser or network."""
from pathlib import Path

import pytest

from scripts import verify_fcaj_worklog as verify


ROUTE = '/aws-internship-worklog/guide/'


def page(build: Path, relative: str, html: str):
    target = build / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding='utf-8')
    return target


def test_relative_assets_fragments_and_external_links(tmp_path):
    page(tmp_path, 'guide/index.html', '<h1 id="tiếng-việt">Guide</h1>'
         '<a href="#ti%E1%BA%BFng-vi%E1%BB%87t">local</a>'
         '<a href="../other/#section">other</a><a href="https://example.org/no-network">external</a>'
         '<a href="mailto:help@example.org">mail</a><script src="../app.js"></script>')
    page(tmp_path, 'other/index.html', '<h2 id="section">Other</h2>')
    page(tmp_path, 'app.js', '/* asset */')
    assets = set()
    result = verify.verify_guide(tmp_path, ROUTE, assets)
    assert result['local_links_checked'] == 3
    assert assets == {'/aws-internship-worklog/app.js'}


@pytest.mark.parametrize('html, expected', [
    ('<a href="../missing/">gone</a>', 'Missing local link'),
    ('<img src="../missing.png">', 'Missing local link'),
    ('<a href="#missing">gone</a>', 'Missing local anchor'),
    ('<p>bad\ufffd</p>', 'Encoding replacement'),
    ('<p>{{< relref "missing" >}}</p>', 'unrendered shortcode'),
])
def test_generated_guide_fails_on_broken_content(tmp_path, html, expected):
    page(tmp_path, 'guide/index.html', html)
    with pytest.raises(ValueError, match=expected):
        verify.verify_guide(tmp_path, ROUTE, set())


@pytest.mark.parametrize('url', [
    '/aws-internship-worklog/%2e%2e/private',
    '/another-site/index.html',
    'https://different.example/aws-internship-worklog/',
])
def test_build_path_cannot_escape_or_select_another_host(tmp_path, url):
    with pytest.raises(ValueError):
        verify.built_file(tmp_path, url)
