# Nigerian Real Estate Market Reports

Monthly market intelligence reports for the Nigerian residential real estate market, powered by
**PS-0 PropertyScraper** — an autonomous data pipeline tracking active listings from major portals across Lagos, Abuja, and six other cities.

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
Supabase (PostgreSQL) -> scripts/export_data.py
        |
        v
scripts/compute_metrics.py  -> data/metrics_{month}[_{period}].json
        |
        v
scripts/generate_narrative.py (Gemini API) -> data/narrative_{month}[_{period}].json
        |
        v
templates/report.html.j2  -> reports/{month}[_{period}]/index.html
                             reports/{month}[_{period}]/report.pdf (WeasyPrint)
        |
        v
Cloudflare Pages (reports.akinmokun.com)
```

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your Supabase credentials and Gemini API key.

## Generating a Report

Use the unified orchestrator script `run.py` at the root of the project to generate reports. It automates all steps (exporting, computing metrics, narrative generation, HTML rendering, and PDF generation) with flags:

```bash
# Render a single month with placeholder narrative (skips Gemini API key requirement):
python run.py --month 2026-06 --placeholder

# Render a 3-month report ending in June 2026, pulling fresh data from Supabase first:
python run.py --month 2026-06 --period 3mo --export

# Render a 6-month report with real Gemini narratives:
python run.py --month 2026-06 --period 6mo
```

Options:
- `--month YYYY-MM`: Target reporting month (required)
- `--period [1mo|3mo|6mo|12mo]`: Window length (default: 1mo)
- `--export`: Pull fresh snapshots from Supabase database
- `--placeholder`: Bypasses Gemini API key using draft narratives
- `--no-pdf`: Skips PDF rendering via WeasyPrint
- `--issue N`: Sets a custom issue number override

## Commit Convention

This repo follows [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` new feature or report section
- `fix:` data correction or pipeline bug
- `chore:` tooling, deps, CI config
- `docs:` README, methodology notes
- `report:` a published report output (`report: add 2026-07 market report`)
- `style:` template/CSS changes only

## License

Report content © Isaac Akinmokun. Code is MIT licensed.
