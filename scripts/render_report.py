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
    reports/2026-06/nigerian-residential-real-estate-market-report-2026-06.pdf
    (unless --no-pdf)
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import sys
import tempfile
from datetime import date
from html import escape
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from report_identity import report_key, validate_metrics_identity
from editorial import build_publication, money
from narrative_validation import metrics_digest, validate_narrative

DATA_DIR = Path(__file__).parent.parent / "data"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
FONTS_DIR = Path(__file__).parent.parent / "templates" / "fonts"
REPORTS_DIR = Path(__file__).parent.parent / "reports"

# Ordered list of (CSS font-family name, CSS weight, filename)
EMBEDDED_FONTS = [
    ("New Computer Modern", "400", "NewCM-Book.woff2"),
    ("New Computer Modern", "700", "NewCM-Bold.woff2"),
    ("Merriweather", "400", "Merriweather-Regular.woff2"),
    ("Merriweather", "700", "Merriweather-Bold.woff2"),
    ("Playfair Display", "400", "PlayfairDisplay.woff2"),
    ("Inter",            "400", "Inter_400.woff2"),
    ("Inter",            "500", "Inter_500.woff2"),
    ("Inter",            "600", "Inter_600.woff2"),
    ("Inter",            "700", "Inter_700.woff2"),
    ("JetBrains Mono",   "400", "JetBrains_Mono_400.woff2"),
    ("JetBrains Mono",   "500", "JetBrains_Mono_500.woff2"),
    ("Menlo",            "400", "Menlo_400.woff2"),
    ("Playfair Display", "700", "Playfair_Display_700.woff2"),
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
        autoescape=True,
    )
    env.filters["money"] = money
    template = env.get_template("report.html.j2")
    return template.render(**template_vars)


def render_pdf(html_path: Path, pdf_path: Path) -> None:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError("WeasyPrint is required for PDF generation. Install it or pass --no-pdf.") from exc

    print(f"Rendering PDF via WeasyPrint ...")
    HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    size_kb = pdf_path.stat().st_size / 1024
    print(f"  ✓ PDF: {pdf_path}  ({size_kb:.0f} KB)")


def get_descriptive_pdf_filename(month: str, period: str, type_str: str) -> str:
    parts = ["nigerian-residential-real-estate-market-report", month]
    if period and period != "1mo":
        parts.append(period)
    if type_str and type_str != "all":
        parts.append(type_str)
    return "-".join(parts) + ".pdf"


# ---------------------------------------------------------------------------
# Index page generation
# ---------------------------------------------------------------------------



def regenerate_index(reports_dir: Path, preview: bool = False) -> None:
    """Scan reports/ subdirectories and regenerate the index page."""
    from jinja2 import Environment

    report_entries = []
    for sub in sorted(reports_dir.iterdir(), reverse=True):
        if not sub.is_dir() or sub.name == ".gitkeep":
            continue
        html_file = sub / "index.html"
        pdf_files = list(sub.glob("*.pdf"))
        pdf_file = pdf_files[0] if pdf_files else None
        meta_file = sub / "meta.json"
        if not html_file.exists():
            continue

        meta = {}
        if meta_file.exists():
            with open(meta_file) as f:
                meta = json.load(f)
        if "pdf_filename" in meta:
            pdf_file = sub / meta["pdf_filename"] if meta["pdf_filename"] else None
            if pdf_file is not None and not pdf_file.exists():
                pdf_file = None

        month_str = sub.name
        parts = month_str.split("_")
        base_month = parts[0]

        period_suffix = meta.get("period")
        mtype_suffix = meta.get("type")

        if not period_suffix or not mtype_suffix:
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
            "period": period_suffix,
            "type": mtype_suffix,
            "published": meta.get("published_date", "—"),
            "cities": meta.get("num_cities", "—"),
            "neighbourhoods": meta.get("unique_neighbourhoods", "—"),
            "has_pdf": pdf_file is not None,
            "pdf_name": pdf_file.name if pdf_file else None,
        })

    embedded_fonts_css = build_embedded_fonts_css()
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    template = env.get_template("index.html.j2")
    html = template.render(
        reports=report_entries,
        preview=preview,
        collection_schema={"@context": "https://schema.org", "@type": "CollectionPage", "name": "PS-0 Market Reports", "url": "https://reports.akinmokun.com/", "mainEntity": {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"https://reports.akinmokun.com/{r['month']}/", "name": r["label"]} for i, r in enumerate(report_entries)]}},
        embedded_fonts_css=embedded_fonts_css,
    )

    index_path = reports_dir / "index.html"
    with open(index_path, "w") as f:
        f.write(html)
    print(f"✓ Index regenerated: {index_path} ({len(report_entries)} reports listed)")

    json_path = reports_dir / "reports.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_entries, f, indent=2)
    print(f"✓ Reports JSON exported: {json_path}")


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


def generate_regional_bar_chart(city_breakdown: dict) -> str:
    # Filter cities with valid median price
    cities_data = []
    for city, stats in city_breakdown.items():
        price = stats.get("median_price_ngn")
        if price:
            cities_data.append((city, price))
    
    # Sort cities by price descending
    cities_data = sorted(cities_data, key=lambda x: x[1], reverse=True)
    if not cities_data:
        return ""
    
    # SVG Dimensions
    width = 600
    row_height = 30
    padding_top = 40
    padding_bottom = 20
    left_margin = 120
    right_margin = 80
    chart_width = width - left_margin - right_margin
    height = len(cities_data) * row_height + padding_top + padding_bottom
    
    max_price = max(c[1] for c in cities_data)
    
    svg = []
    svg.append(f'<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background:var(--bg-card); border: 1px solid var(--border); border-radius: 8px; font-family: var(--font-sans); margin-top: 1.5rem; margin-bottom: 1.5rem;">')
    
    # Add title/header
    svg.append(f'<text x="20" y="25" fill="var(--text-primary)" font-size="12" font-weight="600" letter-spacing="0.5">MEDIAN PRICE COMPARISON BY REGION (NGN)</text>')
    
    y = padding_top
    for city, price in cities_data:
        # Scale bar width
        bar_width = int((price / max_price) * chart_width) if max_price > 0 else 0
        bar_width = max(5, bar_width) # Min 5px width
        
        # Price formatting
        if price >= 1_000_000_000:
            price_str = f"₦{price / 1_000_000_000:.1f}B"
        elif price >= 1_000_000:
            price_str = f"₦{price / 1_000_000:.1f}M"
        else:
            price_str = f"₦{price / 1_000:.0f}k"
            
        # Draw label
        svg.append(f'<text x="{left_margin - 15}" y="{y + 16}" fill="var(--text-secondary)" font-size="11" font-weight="600" text-anchor="end">{escape(city)}</text>')
        
        # Draw bar track
        svg.append(f'<rect x="{left_margin}" y="{y + 4}" width="{chart_width}" height="16" rx="3" fill="var(--border)" opacity="0.3"/>')
        
        # Draw bar fill
        svg.append(f'<rect x="{left_margin}" y="{y + 4}" width="{bar_width}" height="16" rx="3" fill="var(--gold-light)"/>')
        
        # Draw value label
        svg.append(f'<text x="{left_margin + bar_width + 8}" y="{y + 16}" fill="var(--gold-light)" font-size="11" font-weight="600">{price_str}</text>')
        
        y += row_height
        
    svg.append('</svg>')
    return '\n'.join(svg)


def generate_trajectory_line_chart(weeks_data: list) -> str:
    if not weeks_data or len(weeks_data) < 2:
        return ""
    
    # Sort weeks chronologically
    weeks_data = sorted(weeks_data, key=lambda x: x["week"])
    
    # SVG Dimensions
    width = 600
    height = 240
    padding_left = 55
    padding_right = 65
    padding_top = 40
    padding_bottom = 45
    chart_width = width - padding_left - padding_right
    chart_height = height - padding_top - padding_bottom
    
    # Extract values
    weeks = [w["week"] for w in weeks_data]
    active_counts = [w["active_listing_count"] for w in weeks_data]
    median_prices = [w["median_price_ngn"] for w in weeks_data]
    
    min_active = min(active_counts)
    max_active = max(active_counts)
    valid_prices = [price for price in median_prices if price is not None and math.isfinite(price)]
    min_price = min(valid_prices, default=0)
    max_price = max(valid_prices, default=0)
    
    # Guard against flat lines
    active_range = (max_active - min_active) if max_active != min_active else 1.0
    price_range = (max_price - min_price) if max_price != min_price else 1.0
    
    # Add padding to ranges
    active_min_y = max(0, min_active - active_range * 0.1)
    active_max_y = max_active + active_range * 0.1
    active_range_padded = active_max_y - active_min_y
    
    price_min_y = max(0, min_price - price_range * 0.1)
    price_max_y = max_price + price_range * 0.1
    price_range_padded = price_max_y - price_min_y
    
    svg = []
    svg.append(f'<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background:var(--bg-card); border: 1px solid var(--border); border-radius: 8px; font-family: var(--font-sans); margin-top: 1.5rem; margin-bottom: 1.5rem;">')
    
    # Title
    svg.append('<text x="20" y="25" fill="var(--text-primary)" font-size="12" font-weight="600" letter-spacing="0.5">WEEKLY MARKET TRAJECTORY TREND</text>')
    
    # Legend
    svg.append(f'<rect x="360" y="15" width="10" height="10" fill="var(--gold-light)" rx="2"/>')
    svg.append(f'<text x="375" y="24" fill="var(--text-secondary)" font-size="10" font-weight="600">Active Listings (Left)</text>')
    if valid_prices:
        svg.append(f'<rect x="490" y="15" width="10" height="10" fill="#4B9CD3" rx="2"/>')
        svg.append(f'<text x="505" y="24" fill="var(--text-secondary)" font-size="10" font-weight="600">Median Price (Right)</text>')
    
    # X coordinates of points
    num_points = len(weeks_data)
    x_coords = []
    for i in range(num_points):
        x = padding_left + (i / (num_points - 1)) * chart_width
        x_coords.append(x)
        
    # Grid lines (horizontal)
    num_grid_lines = 4
    for i in range(num_grid_lines):
        y = padding_top + (i / (num_grid_lines - 1)) * chart_height
        svg.append(f'<line x1="{padding_left}" y1="{y}" x2="{width - padding_right}" y2="{y}" stroke="var(--border)" stroke-dasharray="4 4" opacity="0.3"/>')
        
        # Grid labels
        # Left scale: Active listings
        active_val = int(active_max_y - (i / (num_grid_lines - 1)) * active_range_padded)
        svg.append(f'<text x="{padding_left - 8}" y="{y + 4}" fill="var(--gold-light)" font-size="9" font-weight="600" text-anchor="end">{active_val}</text>')
        
        # Right scale: Price
        price_val = price_max_y - (i / (num_grid_lines - 1)) * price_range_padded
        if price_val >= 1_000_000_000:
            price_str = f"₦{price_val / 1_000_000_000:.1f}B"
        elif price_val >= 1_000_000:
            price_str = f"₦{price_val / 1_000_000:.0f}M"
        else:
            price_str = f"₦{price_val / 1_000:.0f}k"
        if valid_prices:
            svg.append(f'<text x="{width - padding_right + 8}" y="{y + 4}" fill="#4B9CD3" font-size="9" font-weight="600" text-anchor="start">{price_str}</text>')

    # Plot active listings path
    active_points = []
    for i, val in enumerate(active_counts):
        x = x_coords[i]
        y = padding_top + chart_height - ((val - active_min_y) / active_range_padded) * chart_height
        active_points.append((x, y))
        
    # Plot median price path
    price_points = []
    for i, val in enumerate(median_prices):
        if val is None or not math.isfinite(val):
            price_points.append(None)
            continue
        x = x_coords[i]
        y = padding_top + chart_height - ((val - price_min_y) / price_range_padded) * chart_height
        price_points.append((x, y))
        
    # Draw Active Listings Line & Area
    active_path_str = " ".join([f"{'M' if i==0 else 'L'} {pt[0]:.1f} {pt[1]:.1f}" for i, pt in enumerate(active_points)])
    active_area_str = f"{active_path_str} L {active_points[-1][0]:.1f} {padding_top + chart_height:.1f} L {active_points[0][0]:.1f} {padding_top + chart_height:.1f} Z"
    svg.append(f'<path d="{active_area_str}" fill="var(--gold)" opacity="0.06"/>')
    svg.append(f'<path d="{active_path_str}" fill="none" stroke="var(--gold-light)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
    
    # Start a new segment after each missing price instead of inventing values.
    price_path_str = " ".join(
        f"{'M' if i == 0 or price_points[i - 1] is None else 'L'} {pt[0]:.1f} {pt[1]:.1f}"
        for i, pt in enumerate(price_points) if pt is not None
    )
    if price_path_str:
        svg.append(f'<path d="{price_path_str}" fill="none" stroke="#4B9CD3" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
    
    # Draw markers & labels
    for i, week in enumerate(weeks):
        x = x_coords[i]
        y = padding_top + chart_height
        
        svg.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 4}" stroke="var(--border)" opacity="0.5"/>')
        
        ap = active_points[i]
        svg.append(f'<circle cx="{ap[0]:.1f}" cy="{ap[1]:.1f}" r="4" fill="var(--gold-light)" stroke="var(--bg-card)" stroke-width="1.5"/>')
        
        pp = price_points[i]
        if pp is not None:
            svg.append(f'<circle cx="{pp[0]:.1f}" cy="{pp[1]:.1f}" r="4" fill="#4B9CD3" stroke-width="1.5"/>')
        
        parts = week.split("-")
        week_lbl = f"{parts[1]}/{parts[2]}"
        svg.append(f'<text x="{x}" y="{y + 18}" fill="var(--text-secondary)" font-size="8.5" font-weight="600" text-anchor="middle">{week_lbl}</text>')
        
    svg.append('</svg>')
    return '\n'.join(svg)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Render monthly report HTML (and PDF).")
    parser.add_argument("--month", required=True, help="Reporting month in YYYY-MM format.")
    parser.add_argument("--type", default="all", choices=["all", "sale", "rent"])
    parser.add_argument(
        "--period",
        default="1mo",
        choices=["1mo", "3mo", "6mo", "12mo"],
        help="Reporting period window length (default: 1mo)",
    )
    parser.add_argument("--metrics", default=None, help="Override metrics JSON path.")
    parser.add_argument("--narrative", default=None, help="Override narrative JSON path.")
    parser.add_argument("--issue", type=int, default=None, help="Issue number (e.g. 1 for first report).")
    parser.add_argument("--output-root", type=Path, help="Render into an isolated directory instead of the publication archive.")
    parser.add_argument("--preview", action="store_true", help="Mark the isolated output as an unpublished, noindex design preview.")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation.")
    args = parser.parse_args()

    if args.preview and not args.output_root:
        parser.error("--preview requires --output-root outside reports/.")
    output_root = args.output_root.resolve() if args.output_root else REPORTS_DIR
    archive_root = Path(__file__).resolve().parents[1] / "reports"
    if args.preview and (output_root == archive_root or archive_root in output_root.parents):
        parser.error("Preview output must be outside reports/.")
    key = report_key(args.month, args.period, args.type)
    if output_root == archive_root and (output_root / key / "index.html").exists():
        parser.error("This issue is already published. Use --output-root for an isolated rebuild.")
    metrics_path = Path(args.metrics) if args.metrics else DATA_DIR / f"metrics_{key}.json"
    narrative_path = Path(args.narrative) if args.narrative else DATA_DIR / f"narrative_{key}.json"

    metrics = load_json(metrics_path, "metrics")
    narrative = load_json(narrative_path, "narrative")
    try:
        validate_metrics_identity(metrics, args.month, args.period, args.type)
        validate_narrative(narrative, metrics)
    except ValueError as exc:
        parser.error(str(exc))
    if not narrative.get("_provenance"):
        print("WARNING: Legacy narrative has no metrics provenance; its source metrics cannot be verified.", file=sys.stderr)

    folder_name = key
    out_dir = output_root / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    meta_file = out_dir / "meta.json"
    reference_meta = archive_root / folder_name / "meta.json" if args.preview and not meta_file.exists() else meta_file
    existing_meta = load_json(reference_meta, "meta.json") if reference_meta.exists() else {}

    # Preserve the assigned issue even when older reports are added later.
    issue_number = args.issue
    if issue_number is None:
        issue_number = existing_meta.get("issue_number")
    if issue_number is None:
        existing_issues = [load_json(d / "meta.json", "meta.json").get("issue_number", 0)
                           for d in output_root.iterdir() if d.is_dir() and (d / "meta.json").exists()]
        issue_number = max(existing_issues, default=0) + 1

    # Determine published date (preserve existing date from meta.json if present)
    if existing_meta:
        published_date = existing_meta.get("published_date", date.today().strftime("%B %d, %Y").replace(" 0", " "))
        published_date_iso = existing_meta.get("published_date_iso")
        if not published_date_iso:
            from datetime import datetime
            published_date_iso = datetime.strptime(published_date, "%B %d, %Y").date().isoformat()
    else:
        published_date = date.today().strftime("%B %d, %Y").replace(" 0", " ")
        published_date_iso = date.today().isoformat()

    print("Embedding fonts ...")
    embedded_fonts_css = build_embedded_fonts_css()

    primary = metrics["sales"] if metrics.get("sales") else metrics["rentals"]
    if not primary:
        print("ERROR: No metrics data found (neither sales nor rentals)", file=sys.stderr)
        sys.exit(1)
    overall = metrics.get("coverage", primary["overall"])
    primary_narrative = narrative["sales"] if metrics.get("sales") else narrative["rentals"]

    # Determine descriptive PDF filename
    pdf_filename = get_descriptive_pdf_filename(args.month, args.period, metrics.get("type", "all"))

    # Generate SVG charts
    sales_trajectory_chart = ""
    rentals_trajectory_chart = ""
    sales_regional_chart = ""
    rentals_regional_chart = ""

    if metrics.get("sales") and metrics["sales"].get("weekly_aggregates"):
        sales_trajectory_chart = generate_trajectory_line_chart(metrics["sales"]["weekly_aggregates"])
    if metrics.get("rentals") and metrics["rentals"].get("weekly_aggregates"):
        rentals_trajectory_chart = generate_trajectory_line_chart(metrics["rentals"]["weekly_aggregates"])
        
    if metrics.get("sales") and metrics["sales"].get("city_breakdown"):
        sales_regional_chart = generate_regional_bar_chart(metrics["sales"]["city_breakdown"])
    if metrics.get("rentals") and metrics["rentals"].get("city_breakdown"):
        rentals_regional_chart = generate_regional_bar_chart(metrics["rentals"]["city_breakdown"])

    # Prepare Jinja template context
    template_vars = {
        "overall": overall,
        "preview": args.preview,
        "publication": build_publication(metrics),
        "article_schema": {"@context": "https://schema.org", "@type": "Report", "headline": f"{overall['report_period_label']} — PS-0 Market Report", "datePublished": published_date_iso, "author": {"@type": "Person", "name": "Isaac Akinmokun", "url": "https://akinmokun.com/"}, "url": f"https://reports.akinmokun.com/{key}/", "inLanguage": "en-GB", "description": primary_narrative["key_takeaways"][0]},
        "report_key": key,
        "social_description": primary_narrative["key_takeaways"][0],
        "metrics": metrics,
        "narrative": narrative,
        "period": args.period,
        "type": metrics.get("type", "all"),
        "issue_number": issue_number,
        "published_date": published_date,
        "published_date_iso": published_date_iso,
        "embedded_fonts_css": embedded_fonts_css,
        "pdf_filename": pdf_filename,
        "has_pdf": not args.no_pdf,
        "sales_trajectory_chart": sales_trajectory_chart,
        "rentals_trajectory_chart": rentals_trajectory_chart,
        "sales_regional_chart": sales_regional_chart,
        "rentals_regional_chart": rentals_regional_chart,
    }

    # Render HTML
    print(f"Rendering HTML report for {args.month} ...")
    html_content = render_html(template_vars)
    html_path = out_dir / "index.html"

    # Write meta.json for index generation
    meta = {
        "month": args.month,
        "period": args.period,
        "type": metrics.get("type", "all"),
        "issue_number": issue_number,
        "published_date": published_date,
        "published_date_iso": published_date_iso,
        "num_cities": overall["num_cities"],
        "unique_neighbourhoods": overall["unique_neighbourhoods"],
        "peak_active_listings": overall["peak_active_listings"],
        "pdf_filename": None if args.no_pdf else pdf_filename,
        "metrics_sha256": metrics_digest(metrics),
        "narrative_sha256": metrics_digest(narrative),
        "source_csv_sha256": metrics.get("_source", {}).get("csv_sha256"),
    }
    # Compile every requested format before replacing an existing publication.
    with tempfile.TemporaryDirectory(prefix="property-report-") as tmp:
        staging = Path(tmp)
        staged_html = staging / "index.html"
        staged_html.write_text(html_content, encoding="utf-8")
        if not args.no_pdf:
            render_pdf(staged_html, staging / pdf_filename)
        (staging / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        # Copy across filesystems before replacing each destination atomically.
        import shutil
        for artifact in staging.iterdir():
            destination = out_dir / artifact.name
            pending = out_dir / (artifact.name + ".tmp")
            shutil.copyfile(artifact, pending)
            pending.replace(destination)
    print(f"  ✓ HTML: {html_path}  ({html_path.stat().st_size / 1024:.0f} KB)")

    # Regenerate reports index
    regenerate_index(output_root, preview=args.preview)

    # Regenerate sitemap.xml and robots.txt
    if args.preview:
        (output_root / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    else:
        generate_sitemap_and_robots(output_root)

    print(f"\n✓ Report complete: reports/{folder_name}/")
    print(f"  Open: file://{html_path.resolve()}")


if __name__ == "__main__":
    main()
