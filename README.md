# Nigerian Real Estate Market Reports — Pipeline Documentation

Monthly market intelligence reports for the Nigerian residential real estate market, powered by **PS-0 PropertyScraper** — an autonomous data pipeline tracking active listings from major portals across Lagos, Abuja, and other primary cities.

Published at [reports.akinmokun.com](https://reports.akinmokun.com).

---

## Architecture Overview

The system operates as a multi-stage compilation pipeline that extracts data from a PostgreSQL database, calculates statistical snapshots, generates narrative summaries via the Gemini API, and builds a static web dashboard containing PDF download links.

```
+------------------+
| Supabase Database|  <--- Scraped listing data
+------------------+
         |
         | (export_data.py via SQL query)
         v
+-----------------------------+
| neighbourhood_snapshots.csv |  <--- Local CSV data cache
+-----------------------------+
         |
         | (compute_metrics.py --month --period --type)
         v
+-----------------------+
| metrics_2026-07.json  |  <--- Statistical JSON data structure
+-----------------------+
         |
         | (generate_narrative.py --placeholder / Gemini API)
         v
+-------------------------+
| narrative_2026-07.json  |  <--- Gemini-generated narrative blocks
+-------------------------+
         |
         | (render_report.py --no-pdf)
         +-------------------------------------+
         |                                     |
         v                                     v
+-------------------------+          +--------------------+
| reports/2026-07/        |          | reports/index.html |  <--- Dynamic Filter
|  - index.html (Theme)   |          |  - sitemap.xml     |       Dashboard & SEO
|  - report.pdf           |          |  - robots.txt      |       Index list
+-------------------------+          +--------------------+
```

---

## Installation & Setup

### 1. Prerequisites
Ensure you have the following installed on your machine:
* Python 3.10 or higher
* `pip` (Python package manager)
* `libweasyprint` (Required for PDF rendering via WeasyPrint. On Linux: `sudo apt-get install weasyprint` or `shared-mime-info`)

### 2. Virtual Environment Setup
Initialize a Python virtual environment and install the required dependencies:
```bash
# Clone the repository and navigate to its root directory
cd property-reports

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install required dependencies
pip install -r requirements-pipeline.txt
```

### 3. Configuration
Copy the sample environment file and enter your API keys and database credentials:
```bash
cp .env.example .env
```
Open `.env` in your editor and configure the variables:
```ini
# Supabase PostgreSQL Credentials (Used by export_data.py)
DB_HOST=your-supabase-db-host.supabase.co
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-secure-db-password
DB_PORT=5432

# Gemini API Credentials (Used by generate_narrative.py)
GEMINI_API_KEY=AIzaSy...
```

---

## Detailed Pipeline Execution Commands

While the root-level `run.sh` script is the standard orchestrator, you can invoke individual python scripts manually for granular control.

### Step 1: Export Snapshot Data
Pulls weekly snapshots from the Supabase `market.neighbourhood_snapshots` table and exports them to `data/neighbourhood_snapshots.csv`:
```bash
python scripts/export_data.py
```

### Step 2: Compute Market Metrics
Calculates inventory statistics, pricing percentiles, days on market (DOM) averages, price reduction records, and regional breakdowns.
```bash
# Calculate 1-Month Combined metrics for July 2026
python scripts/compute_metrics.py --month 2026-07 --period 1mo --type all

# Calculate 3-Month Sales-only metrics ending July 2026
python scripts/compute_metrics.py --month 2026-07 --period 3mo --type sale

# Calculate 6-Month Rentals-only metrics ending June 2026
python scripts/compute_metrics.py --month 2026-06 --period 6mo --type rent
```
*Outputs: `data/metrics_{month}_{period}.json`*

### Step 3: Generate Gemini Narrative Commentary
Prompts the Gemini API (`gemini-1.5-flash`) for executive summaries, inventory narratives, pricing deep-dives, regional reports, and market outlooks.
```bash
# Generate real Gemini narrative using API key
python scripts/generate_narrative.py --month 2026-07 --period 1mo

# Generate placeholder draft text (skips API key requirement)
python scripts/generate_narrative.py --month 2026-07 --period 1mo --placeholder
```
*Outputs: `data/narrative_{month}_{period}.json`*

### Step 4: Compile HTML & PDF Reports
Generates the statically styled HTML pages and compiles the print-optimized PDF documents.
```bash
# Render HTML and PDF using default configurations
python scripts/render_report.py --month 2026-07 --period 1mo

# Render HTML only (skip WeasyPrint PDF compilation)
python scripts/render_report.py --month 2026-07 --period 1mo --no-pdf

# Render report with custom issue number override (e.g. Issue #5)
python scripts/render_report.py --month 2026-07 --period 1mo --issue 5
```
*Outputs:*
* *Report Page: `reports/{month}_{period}_{type}/index.html`*
* *PDF Download: `reports/{month}_{period}_{type}/report.pdf`*
* *Directory Index: `reports/index.html`*
* *Sitemap: `reports/sitemap.xml`*
* *Robots: `reports/robots.txt`*

---

## Unified Orchestration (`run.sh`)

For convenience, use `run.sh` to run the entire pipeline end-to-end:

```bash
# Generate a standard monthly combined report with placeholders
./run.sh --month 2026-07 --placeholder

# Export fresh database data first, then compile a 3-month sales report
./run.sh --month 2026-07 --period 3mo --type sale --export

# Compile a 12-month (Yearly) combined report with real Gemini narratives
./run.sh --month 2026-07 --period 12mo
```

### Full Options List
```
Usage: ./run.sh [options]

Options:
  -m, --month YYYY-MM    Target reporting month (end month) (required)
  -p, --period PERIOD    Period window (1mo, 3mo, 6mo, 12mo; default: 1mo)
  -t, --type TYPE        Report type (all, sale, rent; default: all)
  -e, --export           Pull fresh snapshots from Supabase first
  --placeholder          Use placeholder narratives (bypasses Gemini API)
  --no-pdf               Skip PDF generation via WeasyPrint
  -i, --issue NUMBER     Set a custom issue number override
  -h, --help             Show this help message
```

---

## Troubleshooting Common Build Errors

### 1. WeasyPrint PDF Rendering Fails
* **Error**: `OSError: cannot load library 'gobject-2.0-0'` or WeasyPrint is not found.
* **Solution**: WeasyPrint requires system-level drawing libraries (`Pango`, `GObject`, and `Cairo`). Install them using your OS package manager:
  * Ubuntu/Debian: `sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info`
  * MacOS: `brew install cairo pango gdk-pixbuf libffi`

### 2. Gemini API Rate Limit / Authentication Errors
* **Error**: `google.api_core.exceptions.InvalidArgument` or `API key not found`.
* **Solution**: Check that `GEMINI_API_KEY` is exported correctly in your environment or set in your local `.env` file. If the model is not found, verify that python uses `google-generativeai>=0.8.0`.

---

## Commit Message Conventions

This project strictly follows the **Conventional Commits** standard:
* `feat:` A new feature, report template modification, or dashboard element.
* `fix:` A bug fix, layout calculation adjustments, or database queries correction.
* `chore:` Modifying configurations, dependencies, gitignore, or build scripts.
* `docs:` Updates to README, CODEBASE, or markdown documentation files.
* `report:` Adding or publishing raw report outputs (e.g. `report: add June 2026 PDF report`).
* `style:` Pure CSS or spacing overrides inside report templates.

---

## License

Report data & narratives © Isaac Akinmokun. Pipeline code is licensed under the MIT License.
