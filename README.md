# Nigerian Real Estate Market Reports

Monthly market intelligence reports for the Nigerian residential real estate market, powered by
**PS-0 PropertyScraper** — an autonomous data pipeline tracking active listings across Lagos,
Abuja, and six other cities.

Published at [reports.akinmokun.com](https://reports.akinmokun.com).

---

## Methodology

Data is collected weekly via PropertyScraper from the four major Nigerian listing portals.
Neighbourhood-level snapshots record weekly active listing counts, new listing inflows,
price reduction events, and price distribution percentiles (median, P25, P75, P90).

Prices are stored internally in **kobo** (integer arithmetic) and converted to NGN for display.
All conversion is exact (÷ 100).

Reports are generated on the first of each month covering the prior calendar month.

## Pipeline

```
Supabase (PostgreSQL) → scripts/export_data.py
        ↓
scripts/compute_metrics.py  → data/metrics_{month}.json
        ↓
scripts/generate_narrative.py (Gemini API) → data/narrative_{month}.json
        ↓
templates/report.html.j2  → reports/{YYYY-MM}/index.html
templates/report.tex.j2   → reports/{YYYY-MM}/report.pdf
        ↓
Cloudflare Pages (reports.akinmokun.com)
```

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your Supabase credentials and Gemini API key.

## Generating a Report Manually

```bash
# 1. Export data from Supabase (or place CSV in data/ manually)
python scripts/export_data.py --month 2026-07

# 2. Compute metrics
python scripts/compute_metrics.py --month 2026-07

# 3. Generate narrative (requires GEMINI_API_KEY in .env)
python scripts/generate_narrative.py --month 2026-07

# 4. Render HTML + PDF
python scripts/render_report.py --month 2026-07
```

## Commit Convention

This repo follows [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` new feature or report section
- `fix:` data correction or pipeline bug
- `chore:` tooling, deps, CI config
- `docs:` README, methodology notes
- `report:` a published report output (`report: add 2026-07 market report`)
- `style:` template/CSS changes only

## License

Report content © Isla Akinmokun. Code is MIT licensed.
