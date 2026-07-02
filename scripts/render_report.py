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
import json
import sys
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

DATA_DIR = Path(__file__).parent.parent / "data"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
REPORTS_DIR = Path(__file__).parent.parent / "reports"


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
  <meta name="description" content="Monthly market intelligence reports on the Nigerian residential real estate market by Isaac Akinmokun." />
  <style>
    :root {
      --bg: #0d1117; --bg-card: #161b22; --border: #21262d;
      --gold: #c9a84c; --gold-light: #e0c070;
      --text: #e6edf3; --text2: #8b949e; --text3: #6e7681;
      --radius: 8px;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI Variable', 'Segoe UI', Ubuntu, Cantarell, Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; -webkit-font-smoothing: antialiased; }
    .wrap { max-width: 820px; margin: 0 auto; padding: 3rem 1.5rem 5rem; }
    header { margin-bottom: 3rem; }
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
  <header>
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
        try:
            dt = date.fromisoformat(f"{month_str}-01")
            label = dt.strftime("%B %Y")
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


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Render monthly report HTML (and PDF).")
    parser.add_argument("--month", required=True, help="Reporting month in YYYY-MM format.")
    parser.add_argument("--metrics", default=None, help="Override metrics JSON path.")
    parser.add_argument("--narrative", default=None, help="Override narrative JSON path.")
    parser.add_argument("--issue", type=int, default=None, help="Issue number (e.g. 1 for first report).")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation.")
    args = parser.parse_args()

    metrics_path = Path(args.metrics) if args.metrics else DATA_DIR / f"metrics_{args.month}.json"
    narrative_path = Path(args.narrative) if args.narrative else DATA_DIR / f"narrative_{args.month}.json"

    metrics = load_json(metrics_path, "metrics")
    narrative = load_json(narrative_path, "narrative")

    out_dir = REPORTS_DIR / args.month
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine issue number
    issue_number = args.issue
    if issue_number is None:
        existing = [d for d in REPORTS_DIR.iterdir() if d.is_dir() and d.name != ".gitkeep"]
        issue_number = len(existing)

    published_date = date.today().strftime("%B %d, %Y").replace(" 0", " ")

    template_vars = {
        "overall": metrics["overall"],
        "weekly_aggregates": metrics["weekly_aggregates"],
        "inventory_ranking": metrics["inventory_ranking"],
        "pricing_tiers": metrics["pricing_tiers"],
        "city_breakdown": metrics["city_breakdown"],
        "price_reduction_analysis": metrics["price_reduction_analysis"],
        "narrative": narrative,
        "issue_number": issue_number,
        "published_date": published_date,
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
        "num_cities": metrics["overall"]["num_cities"],
        "unique_neighbourhoods": metrics["overall"]["unique_neighbourhoods"],
        "peak_active_listings": metrics["overall"]["peak_active_listings"],
    }
    with open(out_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Render PDF
    if not args.no_pdf:
        pdf_path = out_dir / "report.pdf"
        render_pdf(html_path, pdf_path)

    # Regenerate reports index
    regenerate_index(REPORTS_DIR)

    print(f"\n✓ Report complete: reports/{args.month}/")
    print(f"  Open: file://{html_path.resolve()}")


if __name__ == "__main__":
    main()
