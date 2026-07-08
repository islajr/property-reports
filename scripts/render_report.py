"""
scripts/render_report.py

Combines computed metrics + LLM narrative into the Jinja2 HTML template,
renders the report HTML, and optionally produces a PDF via WeasyPrint.

Usage:
    python scripts/render_report.py --month 2026-06
    python scripts/render_report.py --month 2026-06 --no-pdf
    python scripts/render_report.py --month 2026-06 --issue 1

Output:
    reports/2026-06/index.html
    reports/2026-06/report.pdf  (unless --no-pdf)
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

DATA_DIR = Path(__file__).parent.parent / "data"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
FONTS_DIR = Path(__file__).parent.parent / "templates" / "fonts"
REPORTS_DIR = Path(__file__).parent.parent / "reports"

# Ordered list of (CSS font-family name, CSS weight, filename)
EMBEDDED_FONTS = [
    ("Inter",          "400", "Inter_400.woff2"),
    ("Inter",          "500", "Inter_500.woff2"),
    ("Inter",          "600", "Inter_600.woff2"),
    ("Inter",          "700", "Inter_700.woff2"),
    ("JetBrains Mono", "400", "JetBrains_Mono_400.woff2"),
    ("JetBrains Mono", "500", "JetBrains_Mono_500.woff2"),
]


def build_embedded_fonts_css() -> str:
    """
    Read each woff2 file from templates/fonts/, base64-encode it,
    and return a CSS string of @font-face declarations.
    If font files are missing, returns an empty string and warns.
    """
    blocks = ["/* === EMBEDDED FONTS (Inter + JetBrains Mono, latin subset) === */"]
    missing = []
    for family, weight, filename in EMBEDDED_FONTS:
        path = FONTS_DIR / filename
        if not path.exists():
            missing.append(filename)
            continue
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        blocks.append(
            f"@font-face {{\n"
            f"  font-family: '{family}';\n"
            f"  font-style: normal;\n"
            f"  font-weight: {weight};\n"
            f"  font-display: swap;\n"
            f"  src: url('data:font/woff2;base64,{b64}') format('woff2');\n"
            f"}}"
        )
    if missing:
        print(
            f"  ⚠  Font files not found in templates/fonts/: {missing}\n"
            f"     Run: python scripts/download_fonts.py to fetch them.\n"
            f"     Report will fall back to system fonts.",
            file=sys.stderr,
        )
    return "\n".join(blocks)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path, label: str) -> dict:
    if not path.exists():
        print(f"ERROR: {label} not found at {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def render_html(template_vars: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html.j2")
    return template.render(**template_vars)


def render_pdf(html_path: Path, pdf_path: Path) -> None:
    try:
        from weasyprint import HTML
    except ImportError:
        print("WeasyPrint not installed — skipping PDF generation.", file=sys.stderr)
        print("Install with: pip install weasyprint", file=sys.stderr)
        return

    print(f"Rendering PDF via WeasyPrint ...")
    HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    size_kb = pdf_path.stat().st_size / 1024
    print(f"  ✓ PDF: {pdf_path}  ({size_kb:.0f} KB)")


# ---------------------------------------------------------------------------
# Index page generation
# ---------------------------------------------------------------------------

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Nigerian Real Estate Market Reports — reports.akinmokun.com</title>
  <meta name="description" content="Monthly market intelligence reports on the Nigerian residential real estate market by Isaac Akinmokun, powered by PS-0 PropertyScraper." />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="https://reports.akinmokun.com/" />

  <!-- Favicons / Icons -->
  <link rel="icon" href="/favicon.ico" type="image/x-icon" sizes="16x16" />
  <link rel="icon" href="/isaac-akinmokun-favicon-16x16.png" sizes="16x16" type="image/png" />
  <link rel="icon" href="/isaac-akinmokun-favicon-32x32.png" sizes="32x32" type="image/png" />
  <link rel="apple-touch-icon" href="/isaac-akinmokun-apple-touch-icon.png" sizes="180x180" type="image/png" />

  <!-- Open Graph -->
  <meta property="og:title" content="Nigerian Real Estate Market Reports — reports.akinmokun.com" />
  <meta property="og:description" content="Monthly market intelligence reports on the Nigerian residential real estate market by Isaac Akinmokun, powered by PS-0 PropertyScraper." />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://reports.akinmokun.com/" />
  <meta property="og:site_name" content="Isaac Akinmokun" />
  <meta property="og:locale" content="en_US" />

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="Nigerian Real Estate Market Reports — reports.akinmokun.com" />
  <meta name="twitter:description" content="Monthly market intelligence reports on the Nigerian residential real estate market by Isaac Akinmokun, powered by PS-0 PropertyScraper." />

  <!-- Structured Data JSON-LD -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Person",
        "@id": "https://akinmokun.com/#person",
        "name": "Isaac Akinmokun",
        "givenName": "Isaac",
        "familyName": "Akinmokun",
        "gender": "http://schema.org/Male",
        "jobTitle": "Backend Engineer & Quantitative PropTech Builder",
        "url": "https://akinmokun.com",
        "sameAs": [
          "https://github.com/islajr",
          "https://linkedin.com/in/akinmokun",
          "https://x.com/islajrn",
          "https://instagram.com/islajrn",
          "https://instagram.com/ioakin"
        ]
      },
      {
        "@type": "CollectionPage",
        "@id": "https://reports.akinmokun.com/#webpage",
        "url": "https://reports.akinmokun.com/",
        "name": "Nigerian Real Estate Market Reports",
        "description": "Monthly market intelligence reports on the Nigerian residential real estate market by Isaac Akinmokun, powered by PS-0 PropertyScraper.",
        "publisher": {
          "@id": "https://akinmokun.com/#person"
        }
      }
    ]
  }
  </script>

  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    :root {
      --bg: #0d1117; --bg-card: #161b22; --border: #21262d;
      --gold: #c9a84c; --gold-light: #e0c070;
      --text: #e6edf3; --text2: #8b949e; --text3: #6e7681;
      --radius: 8px;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; -webkit-font-smoothing: antialiased; }
    .wrap { max-width: 820px; margin: 0 auto; padding: 0 1.5rem 5rem; }
    .global-header { display: flex; justify-content: space-between; align-items: center; padding: 1.5rem 0; border-bottom: 1px solid var(--border); margin-bottom: 2.5rem; }
    .global-header .logo-link { display: inline-flex; align-items: center; transition: opacity 0.15s ease; }
    .global-header .logo-link:hover { opacity: 0.55; }
    .global-header .logo-img { border-radius: 3px; }
    .global-header .nav-links { display: flex; flex-wrap: wrap; gap: 0.5rem 1.25rem; align-items: center; }
    .global-header .nav-links a { font-size: 0.85rem; color: var(--text2); text-decoration: none; transition: color 0.15s ease; }
    .global-header .nav-links a:hover, .global-header .nav-links a.active { color: var(--text); }
    .reports-header { margin-top: 3rem; margin-bottom: 3rem; }
    .label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text3); margin-bottom: 0.75rem; }
    h1 { font-size: 1.8rem; font-weight: 700; background: linear-gradient(135deg, var(--text) 60%, var(--gold-light)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 0.5rem; }
    .sub { color: var(--text2); font-size: 1rem; }
    .reports-grid { display: flex; flex-direction: column; gap: 0.75rem; margin-top: 2rem; }
    .report-card { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 1.5rem; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); text-decoration: none; transition: border-color 0.15s, background 0.15s; }
    .report-card:hover { border-color: var(--gold); background: rgba(201,168,76,0.04); }
    .report-card .info {}
    .report-card .month { font-size: 1rem; font-weight: 600; color: var(--text); }
    .report-card .meta { font-size: 0.8rem; color: var(--text3); margin-top: 0.15rem; }
    .report-card .links { display: flex; gap: 0.75rem; align-items: center; }
    .btn { font-size: 0.78rem; padding: 0.35rem 0.8rem; border-radius: 4px; font-weight: 500; text-decoration: none; }
    .btn-html { background: rgba(201,168,76,0.12); color: var(--gold-light); border: 1px solid rgba(201,168,76,0.3); }
    .btn-pdf { background: rgba(255,255,255,0.06); color: var(--text2); border: 1px solid var(--border); }
    footer { margin-top: 4rem; padding-top: 1.5rem; border-top: 1px solid var(--border); font-size: 0.82rem; color: var(--text3); display: flex; justify-content: space-between; flex-wrap: wrap; gap: 1rem; }
    footer a { color: var(--text2); text-decoration: none; }
    footer a:hover { color: var(--gold-light); }
    @media print { :root { --bg:#fff; --bg-card:#f8f9fa; --border:#d0d7de; --text:#1a1f2e; --text2:#4a5568; --text3:#718096; --gold:#7a5f20; --gold-light:#7a5f20; } h1 { -webkit-text-fill-color: var(--text); } }
  </style>
</head>
<body>
<div class="wrap">
  <header class="global-header">
    <a class="logo-link" href="https://akinmokun.com/">
      <img alt="Isaac Akinmokun Logo" src="/isaac-akinmokun-apple-touch-icon.png" width="32" height="32" class="logo-img" />
    </a>
    <nav class="nav-links">
      <a href="https://akinmokun.com/">Home</a>
      <a href="https://akinmokun.com/about/">About</a>
      <a href="https://akinmokun.com/now/">Now</a>
      <a href="https://akinmokun.com/blog/">Blog ↗</a>
      <a href="/" class="active">Reports</a>
    </nav>
  </header>

  <header class="reports-header">
    <div class="label">akinmokun.com · Market Intelligence</div>
    <h1>Nigerian Residential Real Estate<br>Market Reports</h1>
    <p class="sub">Monthly data intelligence on Nigeria's property market, powered by PS-0 PropertyScraper.</p>
  </header>

  <div class="reports-grid">
    {% for report in reports %}
    <a class="report-card" href="/{{ report.month }}/" id="report-{{ report.month }}">
      <div class="info">
        <div class="month">{{ report.label }}</div>
        <div class="meta">Published {{ report.published }} · {{ report.cities }} cities · {{ report.neighbourhoods }} neighbourhoods</div>
      </div>
      <div class="links">
        <span class="btn btn-html">View Report</span>
        {% if report.has_pdf %}<span class="btn btn-pdf">PDF</span>{% endif %}
      </div>
    </a>
    {% endfor %}
  </div>

  <footer>
    <span>© Isaac Akinmokun — reports.akinmokun.com</span>
    <div>
      <a href="https://akinmokun.com/">akinmokun.com</a> ·
      <a href="https://github.com/islajr">GitHub</a>
    </div>
  </footer>
</div>
</body>
</html>
"""


def regenerate_index(reports_dir: Path) -> None:
    """Scan reports/ subdirectories and regenerate the index page."""
    from jinja2 import Environment

    report_entries = []
    for sub in sorted(reports_dir.iterdir(), reverse=True):
        if not sub.is_dir() or sub.name == ".gitkeep":
            continue
        html_file = sub / "index.html"
        pdf_file = sub / "report.pdf"
        meta_file = sub / "meta.json"
        if not html_file.exists():
            continue

        meta = {}
        if meta_file.exists():
            with open(meta_file) as f:
                meta = json.load(f)

        month_str = sub.name
        parts = month_str.split("_")
        base_month = parts[0]

        period_suffix = "1mo"
        mtype_suffix = "all"
        for p in parts[1:]:
            if p in ("3mo", "6mo", "12mo"):
                period_suffix = p
            elif p in ("sale", "rent"):
                mtype_suffix = p

        try:
            dt = date.fromisoformat(f"{base_month}-01")
            label = dt.strftime("%B %Y")
            if period_suffix == "3mo":
                label += " (3-Month)"
            elif period_suffix == "6mo":
                label += " (6-Month)"
            elif period_suffix == "12mo":
                label += " (Yearly)"

            if mtype_suffix == "sale":
                label += " - Sales"
            elif mtype_suffix == "rent":
                label += " - Rentals"
        except ValueError:
            label = month_str

        report_entries.append({
            "month": month_str,
            "label": label,
            "published": meta.get("published_date", "—"),
            "cities": meta.get("num_cities", "—"),
            "neighbourhoods": meta.get("unique_neighbourhoods", "—"),
            "has_pdf": pdf_file.exists(),
        })

    env = Environment(autoescape=select_autoescape(["html"]))
    template = env.from_string(INDEX_TEMPLATE)
    html = template.render(reports=report_entries)

    index_path = reports_dir / "index.html"
    with open(index_path, "w") as f:
        f.write(html)
    print(f"✓ Index regenerated: {index_path} ({len(report_entries)} reports listed)")


def generate_sitemap_and_robots(reports_dir: Path) -> None:
    """
    Generate sitemap.xml and robots.txt inside the reports directory.
    Ensures all published market reports are discoverable and indexed
    by search engine crawlers under the reports.akinmokun.com subdomain.
    """
    # 1. Write robots.txt
    robots_path = reports_dir / "robots.txt"
    robots_content = (
        "# robots.txt for reports.akinmokun.com\n"
        "User-agent: *\n"
        "Allow: /\n"
        "Sitemap: https://reports.akinmokun.com/sitemap.xml\n"
    )
    with open(robots_path, "w", encoding="utf-8") as f:
        f.write(robots_content)
    print(f"✓ Robots.txt generated: {robots_path}")

    # 2. Write sitemap.xml
    entries = []
    
    # Homepage entry
    entries.append(
        "  <url>\n"
        "    <loc>https://reports.akinmokun.com/</loc>\n"
        "    <changefreq>monthly</changefreq>\n"
        "    <priority>1.0</priority>\n"
        "  </url>"
    )

    # Scan for compiled report directories
    for sub in sorted(reports_dir.iterdir()):
        if not sub.is_dir():
            continue
        if sub.name in (".gitkeep", ".git", ".github", ".antigravitycli", ".venv"):
            continue
        
        # Verify index.html exists in the subfolder
        html_file = sub / "index.html"
        if not html_file.exists():
            continue

        # Extract month/period from the subfolder name
        entries.append(
            f"  <url>\n"
            f"    <loc>https://reports.akinmokun.com/{sub.name}/</loc>\n"
            f"    <changefreq>never</changefreq>\n"
            f"    <priority>0.8</priority>\n"
            f"  </url>"
        )

    # Compile the full XML payload
    sitemap_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries) + "\n"
        '</urlset>\n'
    )
    sitemap_path = reports_dir / "sitemap.xml"
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(sitemap_content)
    print(f"✓ Sitemap.xml generated: {sitemap_path} ({len(entries)} URLs listed)")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Render monthly report HTML (and PDF).")
    parser.add_argument("--month", required=True, help="Reporting month in YYYY-MM format.")
    parser.add_argument(
        "--period",
        default="1mo",
        choices=["1mo", "3mo", "6mo", "12mo"],
        help="Reporting period window length (default: 1mo)",
    )
    parser.add_argument("--metrics", default=None, help="Override metrics JSON path.")
    parser.add_argument("--narrative", default=None, help="Override narrative JSON path.")
    parser.add_argument("--issue", type=int, default=None, help="Issue number (e.g. 1 for first report).")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation.")
    args = parser.parse_args()

    suffix = "" if args.period == "1mo" else f"_{args.period}"
    metrics_path = Path(args.metrics) if args.metrics else DATA_DIR / f"metrics_{args.month}{suffix}.json"
    narrative_path = Path(args.narrative) if args.narrative else DATA_DIR / f"narrative_{args.month}{suffix}.json"

    metrics = load_json(metrics_path, "metrics")
    narrative = load_json(narrative_path, "narrative")

    folder_name = args.month if args.period == "1mo" else f"{args.month}_{args.period}"
    mtype = metrics.get("type", "all")
    if mtype != "all":
        folder_name = f"{folder_name}_{mtype}"
    out_dir = REPORTS_DIR / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine issue number
    issue_number = args.issue
    if issue_number is None:
        existing = [d for d in REPORTS_DIR.iterdir() if d.is_dir() and d.name != ".gitkeep"]
        issue_number = len(existing)

    published_date = date.today().strftime("%B %d, %Y").replace(" 0", " ")
    published_date_iso = date.today().isoformat()

    print("Embedding fonts ...")
    embedded_fonts_css = build_embedded_fonts_css()

    primary = metrics["sales"] if metrics.get("sales") else metrics["rentals"]
    if not primary:
        print("ERROR: No metrics data found (neither sales nor rentals)", file=sys.stderr)
        sys.exit(1)

    template_vars = {
        "overall": primary["overall"],
        "metrics": metrics,
        "narrative": narrative,
        "period": args.period,
        "type": metrics.get("type", "all"),
        "issue_number": issue_number,
        "published_date": published_date,
        "published_date_iso": published_date_iso,
        "embedded_fonts_css": embedded_fonts_css,
    }

    # Render HTML
    print(f"Rendering HTML report for {args.month} ...")
    html_content = render_html(template_vars)
    html_path = out_dir / "index.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    size_kb = html_path.stat().st_size / 1024
    print(f"  ✓ HTML: {html_path}  ({size_kb:.0f} KB)")

    # Write meta.json for index generation
    meta = {
        "month": args.month,
        "issue_number": issue_number,
        "published_date": published_date,
        "num_cities": primary["overall"]["num_cities"],
        "unique_neighbourhoods": primary["overall"]["unique_neighbourhoods"],
        "peak_active_listings": primary["overall"]["peak_active_listings"],
        "type": metrics.get("type", "all"),
    }
    with open(out_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Render PDF
    if not args.no_pdf:
        pdf_path = out_dir / "report.pdf"
        render_pdf(html_path, pdf_path)

    # Regenerate reports index
    regenerate_index(REPORTS_DIR)

    # Regenerate sitemap.xml and robots.txt
    generate_sitemap_and_robots(REPORTS_DIR)

    print(f"\n✓ Report complete: reports/{args.month}/")
    print(f"  Open: file://{html_path.resolve()}")


if __name__ == "__main__":
    main()
