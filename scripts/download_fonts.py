"""
scripts/download_fonts.py

Downloads Inter and JetBrains Mono woff2 Latin subset files from Google Fonts
and saves them to templates/fonts/. Run this once after cloning the repo,
or any time you want to refresh the font files.

The downloaded files are committed to the repo so CI/CD doesn't need network
access at render time — but this script lets you re-fetch them if needed.

Usage:
    python scripts/download_fonts.py
"""

from __future__ import annotations

import sys
import urllib.request
import re
from pathlib import Path

FONTS_DIR = Path(__file__).parent.parent / "templates" / "fonts"

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:wght@400;500;600;700"
    "&family=JetBrains+Mono:wght@400;500"
    "&display=swap"
)

CHROME_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Expected output files: (font-family, CSS weight, filename)
FONT_SPEC = [
    ("Inter",          "400", "Inter_400.woff2"),
    ("Inter",          "500", "Inter_500.woff2"),
    ("Inter",          "600", "Inter_600.woff2"),
    ("Inter",          "700", "Inter_700.woff2"),
    ("JetBrains Mono", "400", "JetBrains_Mono_400.woff2"),
    ("JetBrains Mono", "500", "JetBrains_Mono_500.woff2"),
]


def fetch_css() -> str:
    req = urllib.request.Request(GOOGLE_FONTS_URL, headers={"User-Agent": CHROME_UA})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode()


def parse_latin_urls(css: str) -> dict[tuple[str, str], str]:
    """
    Returns a dict mapping (family, weight) → woff2 URL for Latin-only blocks.
    Latin-only blocks are @font-face entries with no unicode-range restriction.
    """
    face_re = re.compile(
        r"/\* ([\w-]+) \*/\s*@font-face\s*\{([^}]+)\}",
        re.DOTALL,
    )
    results = {}
    for m in face_re.finditer(css):
        block_type = m.group(1)
        block_body = m.group(2)
        if block_type != "latin":
            continue
        fam_m = re.search(r"font-family:\s*'([^']+)'", block_body)
        wgt_m = re.search(r"font-weight:\s*(\d+)", block_body)
        url_m = re.search(
            r"url\((https://fonts\.gstatic\.com/[^\s)]+\.woff2)\)", block_body
        )
        if fam_m and wgt_m and url_m:
            results[(fam_m.group(1), wgt_m.group(1))] = url_m.group(1)
    return results


def download_woff2(url: str, out_path: Path) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": CHROME_UA})
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
    with open(out_path, "wb") as f:
        f.write(data)
    return len(data)


def main() -> None:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching font CSS from Google Fonts ...")
    css = fetch_css()
    url_map = parse_latin_urls(css)
    print(f"  Found {len(url_map)} latin font variants.")

    ok = 0
    for family, weight, filename in FONT_SPEC:
        key = (family, weight)
        url = url_map.get(key)
        if not url:
            print(f"  ✗  Not found in CSS: {family} w{weight}", file=sys.stderr)
            continue
        out_path = FONTS_DIR / filename
        size = download_woff2(url, out_path)
        size_kb = size / 1024
        print(f"  ✓  {filename}  ({size_kb:.1f} KB)")
        ok += 1

    print(f"\nDownloaded {ok}/{len(FONT_SPEC)} font files to {FONTS_DIR}/")
    if ok < len(FONT_SPEC):
        print("WARNING: Some fonts missing. Reports may fall back to system fonts.")
        sys.exit(1)
    else:
        print("All fonts ready. Re-render reports to embed updated fonts.")


if __name__ == "__main__":
    main()
