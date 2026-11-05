"""Fetch self-hosted Vietnamese serif fonts from Google Fonts, retaining OFL."""
import re
from pathlib import Path
import requests

target = Path(__file__).resolve().parents[1] / "frontend" / "src" / "fonts"
target.mkdir(exist_ok=True)
url = "https://fonts.googleapis.com/css2?family=Noto+Serif:ital,wght@0,400;1,400&display=swap"
response = requests.get(url, headers={"User-Agent": "Mozilla/5.0 Chrome/130.0.0.0 Safari/537.36"}, timeout=20)
response.raise_for_status()
blocks = re.findall(r"(@font-face\s*\{.*?\})", response.text, re.S)
css = []
for block in blocks:
    source = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", block)
    if not source:
        raise RuntimeError("Google Fonts did not return an expected font URL")
    style = "italic" if "font-style: italic" in block else "normal"
    suffix = "woff2" if ".woff2" in source[1] else "ttf"
    name = f"noto-serif-{style}.{suffix}"
    font = requests.get(source[1], timeout=20)
    font.raise_for_status()
    if not font.content.startswith((b"wOF2", b"\x00\x01\x00\x00", b"OTTO")):
        raise RuntimeError("Unexpected font format")
    (target / name).write_bytes(font.content)
    css.append(block.replace(source[1], "./fonts/" + name))
if len(css) != 2:
    raise RuntimeError("Expected both styles of the full Unicode font")
(target.parent / "fonts.css").write_text("\n".join(css), encoding="utf-8")
license = requests.get("https://raw.githubusercontent.com/google/fonts/main/ofl/notoserif/OFL.txt", timeout=20)
license.raise_for_status()
(target / "OFL.txt").write_text(license.text, encoding="utf-8")
print("Downloaded 2 self-hosted Unicode fonts with OFL license")
