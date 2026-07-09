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
    .reports-grid { display: flex; flex-direction: column; gap: 0.75rem; margin-top: 1rem; }
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

    @media (max-width: 600px) {
      .wrap { padding: 0 1.25rem 3rem; }
      .global-header { padding: 1rem 0; margin-bottom: 1.5rem; flex-direction: column; gap: 1rem; align-items: center; text-align: center; }
      .global-header .nav-links { gap: 0.5rem 1rem; justify-content: center; }
      .reports-header { margin-top: 1.5rem; margin-bottom: 2rem; text-align: center; }
      h1 { font-size: 1.5rem; }
      .sub { font-size: 0.9rem; }
      .controls { padding: 1.25rem 1rem; gap: 1rem; align-items: center; }
      .search-box { width: 100%; }
      .filters { flex-direction: column; align-items: center; gap: 1rem; width: 100%; }
      .filter-group { flex-direction: column; align-items: center; gap: 0.5rem; width: 100%; }
      .pills { flex-wrap: wrap; justify-content: center; gap: 0.35rem; width: 100%; }
      .pill { font-size: 0.74rem; padding: 0.28rem 0.65rem; }
      .report-card { flex-direction: column; align-items: flex-start; gap: 1rem; padding: 1.25rem; }
      .report-card .links { width: 100%; justify-content: flex-start; }
      .report-card .btn { flex: 1; text-align: center; font-size: 0.75rem; }
    }

    /* Search & Filter Bar Styling */
    .controls { display: flex; flex-direction: column; gap: 1rem; margin-top: 2rem; margin-bottom: 2rem; background: var(--bg-card); border: 1px solid var(--border); padding: 1.25rem 1.5rem; border-radius: var(--radius); }
    .search-box { position: relative; }
    .search-box input { width: 100%; padding: 0.75rem 1rem; border-radius: var(--radius); background: var(--bg); border: 1px solid var(--border); color: var(--text); font-family: inherit; font-size: 0.9rem; transition: border-color 0.15s; }
    .search-box input:focus { border-color: var(--gold); outline: none; }
    .filters { display: flex; flex-wrap: wrap; gap: 1.25rem; align-items: center; }
    .filter-group { display: flex; align-items: center; gap: 0.5rem; }
    .filter-label { font-size: 0.78rem; text-transform: uppercase; color: var(--text3); font-weight: 600; letter-spacing: 0.5px; }
    .pills { display: flex; gap: 0.35rem; }
    .pill { font-size: 0.76rem; padding: 0.3rem 0.75rem; border-radius: 20px; background: rgba(255,255,255,0.06); border: 1px solid var(--border); color: var(--text2); cursor: pointer; transition: all 0.15s; font-weight: 500; }
    .pill:hover { border-color: var(--text3); color: var(--text); }
    .pill.active { background: rgba(201,168,76,0.15); border-color: var(--gold); color: var(--gold-light); }

    /* Badges */
    .badge { font-size: 0.68rem; padding: 0.15rem 0.5rem; border-radius: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; display: inline-flex; align-items: center; }
    .badge-monthly { background: rgba(201,168,76,0.12); color: var(--gold-light); border: 1px solid rgba(201,168,76,0.3); }
    .badge-quarterly { background: rgba(98,125,152,0.15); color: #9fb3c8; border: 1px solid rgba(98,125,152,0.3); }
    .badge-biannual { background: rgba(200,122,83,0.15); color: #e2947a; border: 1px solid rgba(200,122,83,0.3); }
    .badge-yearly { background: rgba(212,175,55,0.15); color: #f3e5ab; border: 1px solid rgba(212,175,55,0.3); }
    .badge-sale { background: rgba(49,130,206,0.15); color: #63b3ed; border: 1px solid rgba(49,130,206,0.3); }
    .badge-rent { background: rgba(56,161,105,0.15); color: #68d391; border: 1px solid rgba(56,161,105,0.3); }
    .badge-combined { background: rgba(255,255,255,0.06); color: var(--text2); border: 1px solid var(--border); }

    .report-card .meta-row { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; margin-top: 0.45rem; }
    .report-card .stats-text { font-size: 0.78rem; color: var(--text3); }
    .no-results { text-align: center; padding: 3rem 0; color: var(--text3); font-size: 0.95rem; }
    .show-more-wrap { display: flex; justify-content: center; margin-top: 2rem; }
    .btn-show-more { background: rgba(255,255,255,0.06); color: var(--text); border: 1px solid var(--border); padding: 0.5rem 1.5rem; border-radius: var(--radius); cursor: pointer; font-size: 0.85rem; font-weight: 500; transition: border-color 0.15s, background 0.15s; }
    .btn-show-more:hover { border-color: var(--gold); background: rgba(201,168,76,0.04); }
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

  <!-- Controls Section (Search & Filter) -->
  <div class="controls" id="dashboard-controls" style="display: none;">
    <div class="search-box">
      <input type="text" id="search-input" placeholder="Search reports by month or year (e.g. June, 2026)..." />
    </div>
    <div class="filters">
      <div class="filter-group">
        <span class="filter-label">Market:</span>
        <div class="pills" id="type-pills">
          <button class="pill active" data-type="all">All</button>
          <button class="pill" data-type="sale">Sales</button>
          <button class="pill" data-type="rent">Rentals</button>
        </div>
      </div>
      <div class="filter-group">
        <span class="filter-label">Frequency:</span>
        <div class="pills" id="period-pills">
          <button class="pill active" data-period="all">All</button>
          <button class="pill" data-period="1mo">Monthly</button>
          <button class="pill" data-period="3mo">Quarterly</button>
          <button class="pill" data-period="6mo">Bi-Annual</button>
          <button class="pill" data-period="12mo">Yearly</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Featured Publications (Recent Reports) -->
  <div id="featured-section" style="display: none; margin-bottom: 2.5rem;">
    <h2 style="font-size: 1.1rem; text-transform: uppercase; color: var(--text3); font-weight: 600; letter-spacing: 0.5px; margin-bottom: 1rem;">Featured Publication</h2>
    <div id="featured-grid"></div>
  </div>

  <!-- Dynamic Grid Container -->
  <div id="reports-dynamic-container" style="display: none;">
    <h2 style="font-size: 1.1rem; text-transform: uppercase; color: var(--text3); font-weight: 600; letter-spacing: 0.5px; margin-bottom: 1rem;" id="grid-header">All Publications</h2>
    <div class="reports-grid" id="dynamic-grid"></div>
    <div class="show-more-wrap" id="show-more-wrap" style="display: none;">
      <button class="btn-show-more" id="btn-show-more">Show More</button>
    </div>
  </div>

  <!-- SEO Fallback Container (for crawlers without JS) -->
  <div id="reports-fallback">
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
  </div>

  <footer>
    <span>© Isaac Akinmokun — reports.akinmokun.com</span>
    <div>
      <a href="https://akinmokun.com/">akinmokun.com</a> ·
      <a href="https://github.com/islajr">GitHub</a>
    </div>
  </footer>
</div>

<script id="reports-data" type="application/json">
  {{ reports_json | safe }}
</script>

<script>
  (function() {
    // 1. Load data
    const reports = JSON.parse(document.getElementById('reports-data').textContent);
    if (!reports || reports.length === 0) return;

    // 2. Hide fallback, show dynamic container & controls
    document.getElementById('reports-fallback').style.display = 'none';
    document.getElementById('dashboard-controls').style.display = 'flex';
    document.getElementById('reports-dynamic-container').style.display = 'block';

    // 3. UI references
    const searchInput = document.getElementById('search-input');
    const typePills = document.querySelectorAll('#type-pills .pill');
    const periodPills = document.querySelectorAll('#period-pills .pill');
    const dynamicGrid = document.getElementById('dynamic-grid');
    const featuredSection = document.getElementById('featured-section');
    const featuredGrid = document.getElementById('featured-grid');
    const showMoreWrap = document.getElementById('show-more-wrap');
    const btnShowMore = document.getElementById('btn-show-more');
    const gridHeader = document.getElementById('grid-header');

    // State
    let filterType = 'all';
    let filterPeriod = 'all';
    let searchQuery = '';
    let pageSize = 6;
    let visibleCount = pageSize;

    // Badges builder helper
    function getPeriodBadge(period) {
      if (period === '3mo') return '<span class="badge badge-quarterly">Quarterly</span>';
      if (period === '6mo') return '<span class="badge badge-biannual">Bi-Annual</span>';
      if (period === '12mo') return '<span class="badge badge-yearly">Yearly</span>';
      return '<span class="badge badge-monthly">Monthly</span>';
    }

    function getTypeBadge(type) {
      if (type === 'sale') return '<span class="badge badge-sale">Sales</span>';
      if (type === 'rent') return '<span class="badge badge-rent">Rentals</span>';
      return '<span class="badge badge-combined">Combined</span>';
    }

    // Render a single report card HTML
    function renderCard(report) {
      const pdfBtn = report.has_pdf ? `<span class="btn btn-pdf" style="margin-left:0.5rem">PDF</span>` : '';
      return `
        <a class="report-card" href="/${report.month}/" id="card-${report.month}">
          <div class="info">
            <div class="month">${report.label}</div>
            <div class="meta-row">
              ${getPeriodBadge(report.period)}
              ${getTypeBadge(report.type)}
              <span class="stats-text">• Published ${report.published} • ${report.cities} cities • ${report.neighbourhoods} hoods</span>
            </div>
          </div>
          <div class="links">
            <span class="btn btn-html">View Report</span>
            ${pdfBtn}
          </div>
        </a>
      `;
    }

    // Render Dashboard
    function render() {
      // Filter
      const filtered = reports.filter(r => {
        // Type filter
        if (filterType !== 'all' && r.type !== filterType) return false;
        // Period filter
        if (filterPeriod !== 'all' && r.period !== filterPeriod) return false;
        // Search query
        if (searchQuery) {
          const query = searchQuery.toLowerCase();
          return r.label.toLowerCase().includes(query) || r.month.toLowerCase().includes(query);
        }
        return true;
      });

      // Set up Featured Publications (only show the top 1 if no filtering is active, else hide)
      if (filterType === 'all' && filterPeriod === 'all' && !searchQuery && filtered.length > 0) {
        featuredSection.style.display = 'block';
        featuredGrid.innerHTML = renderCard(reports[0]);
        // Filter out the featured report from all reports list so we don't repeat
        const remaining = filtered.slice(1);
        gridHeader.textContent = 'All Publications';
        renderGrid(remaining);
      } else {
        featuredSection.style.display = 'none';
        gridHeader.textContent = 'Search Results';
        renderGrid(filtered);
      }
    }

    function renderGrid(list) {
      if (list.length === 0) {
        dynamicGrid.innerHTML = '<div class="no-results">No reports found matching selected criteria.</div>';
        showMoreWrap.style.display = 'none';
        return;
      }

      const sliced = list.slice(0, visibleCount);
      dynamicGrid.innerHTML = sliced.map(renderCard).join('');

      if (list.length > visibleCount) {
        showMoreWrap.style.display = 'flex';
      } else {
        showMoreWrap.style.display = 'none';
      }
    }

    // Event Listeners
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value;
      visibleCount = pageSize; // Reset pagination
      render();
    });

    // Type pills toggle
    document.getElementById('type-pills').addEventListener('click', (e) => {
      const btn = e.target.closest('.pill');
      if (!btn) return;
      typePills.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      filterType = btn.dataset.type;
      visibleCount = pageSize;
      render();
    });

    // Period pills toggle
    document.getElementById('period-pills').addEventListener('click', (e) => {
      const btn = e.target.closest('.pill');
      if (!btn) return;
      periodPills.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      filterPeriod = btn.dataset.period;
      visibleCount = pageSize;
      render();
    });

    // Pagination
    btnShowMore.addEventListener('click', () => {
      visibleCount += pageSize;
      render();
    });

    // Init
    render();
  })();
</script>
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
        pdf_files = list(sub.glob("*.pdf"))
        pdf_file = pdf_files[0] if pdf_files else None
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

    env = Environment(autoescape=select_autoescape(["html"]))
    template = env.from_string(INDEX_TEMPLATE)
    html = template.render(
        reports=report_entries,
        reports_json=json.dumps(report_entries)
    )

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
        existing = sorted([d.name for d in REPORTS_DIR.iterdir() if d.is_dir() and (d / "meta.json").exists()])
        try:
            issue_number = existing.index(folder_name) + 1
        except ValueError:
            issue_number = len(existing) + 1

    published_date = date.today().strftime("%B %d, %Y").replace(" 0", " ")
    published_date_iso = date.today().isoformat()

    print("Embedding fonts ...")
    embedded_fonts_css = build_embedded_fonts_css()

    primary = metrics["sales"] if metrics.get("sales") else metrics["rentals"]
    if not primary:
        print("ERROR: No metrics data found (neither sales nor rentals)", file=sys.stderr)
        sys.exit(1)

    # Determine descriptive PDF filename
    pdf_filename = get_descriptive_pdf_filename(args.month, args.period, metrics.get("type", "all"))

    # Prepare Jinja template context
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
        "pdf_filename": pdf_filename,
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
        "period": args.period,
        "type": metrics.get("type", "all"),
        "issue_number": issue_number,
        "published_date": published_date,
        "num_cities": primary["overall"]["num_cities"],
        "unique_neighbourhoods": primary["overall"]["unique_neighbourhoods"],
        "peak_active_listings": primary["overall"]["peak_active_listings"],
    }
    with open(out_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Render PDF
    if not args.no_pdf:
        pdf_path = out_dir / pdf_filename
        render_pdf(html_path, pdf_path)

    # Regenerate reports index
    regenerate_index(REPORTS_DIR)

    # Regenerate sitemap.xml and robots.txt
    generate_sitemap_and_robots(REPORTS_DIR)

    print(f"\n✓ Report complete: reports/{args.month}/")
    print(f"  Open: file://{html_path.resolve()}")


if __name__ == "__main__":
    main()
