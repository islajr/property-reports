# Nigerian Real Estate Market Reports

Python pipeline for the PS-0 PropertyScraper market reports, published at
[reports.akinmokun.com](https://reports.akinmokun.com).

The repository builds static HTML reports, PDFs, and a searchable report catalogue.
The scraper, database schema, and `market.classify_property` function live upstream
in `property-intel`; this repository does not implement ingestion or migrations.

## How it works

```text
Supabase listing records + price-change history
  → export_data.py → data/neighbourhood_snapshots.csv
  → compute_metrics.py → data/metrics_{key}.json
  → generate_narrative.py → data/narrative_{key}.json
  → render_report.py → reports/{key}/{index.html, meta.json, descriptive-name.pdf}
                    → reports/{index.html, reports.json, sitemap.xml, robots.txt}
```

A report key is `YYYY-MM[_period][_type]`. Monthly combined reports retain the
plain month (`2026-09`); examples of other keys are `2026-09_3mo` and
`2026-09_3mo_sale`. Periods are `1mo`, `3mo`, `6mo`, or `12mo`; types are `all`,
`sale`, or `rent`. All stages use the same key, including intermediate files.

## Setup

Use Python **3.12 or newer**. PDF generation also requires WeasyPrint's native
libraries (Pango, HarfBuzz, and fontconfig); CI installs these on Ubuntu 24.04.
Keep the `pydyf==0.10.0` pin with WeasyPrint 62.3: newer pydyf versions remove
the stream API this renderer uses.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-pipeline.txt
cp .env.example .env
```

Configure `SUPABASE_DB_URL` for database export and `GEMINI_API_KEY` for narrative
generation. `GEMINI_MODEL` optionally overrides the code's default model name,
`gemini-3.5-flash`. Model access must be verified with your own Gemini account;
the offline checks do not call the service.

Fonts are already committed in `templates/fonts/` and embedded in generated
pages. `scripts/download_fonts.py` can refresh the six Inter and JetBrains Mono
files; it does not download the bundled Menlo or Playfair Display files.

## Build reports

```bash
# Use the local CSV and explicit offline draft commentary; render HTML only.
./run.sh --month 2026-09 --placeholder --no-pdf

# Export fresh data and build a quarterly sales report with Gemini and a PDF.
./run.sh --month 2026-09 --period 3mo --type sale --export

# Replace an existing narrative after its metrics change.
./run.sh --month 2026-09 --force

./run.sh --help
```

`--export` replaces the local CSV. Without it, the cached CSV must already exist.
Metrics are recomputed on each run. `--issue NUMBER` overrides the assigned issue;
otherwise existing issue numbers and publication dates are preserved.

Narrative generation requires an API key unless `--placeholder` is explicit.
Existing commentary is reused only when its metrics fingerprint matches. A stale
narrative, a legacy narrative without provenance, or a placeholder being reused
for a production build causes an error. Preserve any hand-edited commentary
before using `--force`, which replaces the narrative. Gemini responses are checked
for required fields and types; this does not verify the factual accuracy of prose.

The renderer can still open structurally valid legacy narrative JSON, with a
warning that its metrics cannot be verified. It rejects a fingerprint mismatch.

PDF errors fail the build before existing HTML and metadata are replaced. Use
`--no-pdf` for HTML-only output; the report and catalogue will omit PDF links.
An older PDF already on disk is retained but is no longer advertised by that build.

## Run individual stages

Pass the same month, period, and type to every stage:

```bash
python scripts/export_data.py
python scripts/compute_metrics.py --month 2026-09 --period 3mo --type sale
python scripts/generate_narrative.py --month 2026-09 --period 3mo --type sale --placeholder
python scripts/render_report.py --month 2026-09 --period 3mo --type sale --no-pdf
```

The exporter accepts `--out`; metrics accept `--csv` and `--out`; narrative
accepts `--metrics` and `--out`; rendering accepts `--metrics` and `--narrative`.
Run a script with `--help` for its options. Paths default to this repository's
`data/`, `templates/`, and `reports/` directories; there is no `DATA_DIR`
environment override.

## Data interpretation

- Source rows group listings by city, neighbourhood, week, market type, and
  property class. Sales and rentals are separate; short lets are excluded.
  The dataset includes land and commercial classes alongside residential classes.
- Inventory rankings sum classes within a neighbourhood-week before averaging
  observed weeks. Class tables retain small groups so additive totals reconcile.
- Peak inventory is the highest weekly total. Cumulative active inventory counts
  listing-weeks, so a listing can contribute more than once. Growth compares the
  first and last included weeks.
- Weekly, city, and overall prices are unweighted medians of source group medians.
  Pricing tiers use means of observed group medians, with average weekly inventory
  thresholds of five listings for expensive areas and three for affordable areas.
  These summaries are not exact medians of individual listings.
- Reports select weeks by their start date. A final week can extend past month-end.
  A trailing week below 30% of the previous weeks' median active volume is excluded
  as a possible partial export; the heuristic can also remove a real decline.
- The exporter reconstructs history using current listing status, prices, and
  classification. It does not restore historical prices or explicitly mark outages
  and carry forward weekly totals. Historical pricing is not an immutable time series.
- DOM uses first observation through the earlier of last observation and the
  end-of-week boundary, with a one-day floor. It cannot recover the actual listing
  date for properties already online before discovery.

See [CODEBASE.md](CODEBASE.md) for implementation details.

## Validation and preview

```bash
python -m unittest discover -s tests -v
bash -n run.sh
python -m http.server --directory reports 8000
```

Visit `http://localhost:8000/` for the catalogue. The tests use synthetic input and
temporary output directories; they do not call Supabase or Gemini or overwrite
published reports. They include a real PDF smoke test and require the native PDF
libraries above. The regression workflow runs on PRs and pushes to `dev` and
`master`.

## Publishing and reproducibility

`.github/workflows/monthly_report.yml` runs at 05:00 UTC (06:00 WAT) on the first
of each month, or manually. It exports data, builds the preceding month's combined
report, and commits `reports/` back to the checked-out branch. Required repository
secrets are `SUPABASE_DB_URL` and `GEMINI_API_KEY`.

Generated metrics record the source CSV hash, narratives record their metrics
hash, and report metadata records the metrics, narrative, and CSV hashes. Monthly
workflow runs archive the CSV, metrics, narrative, metadata, and dependency pins
as GitHub Actions artifacts for **90 days**. Download these before expiry when
long-term reproducibility is required; the Git commit identifies the pipeline code.
A fresh export can revise historical results as upstream records change.

`data/` and `.env` remain ignored by Git. There is no database export or API key
in the public static assets. Published HTML/PDFs and their metadata are committed.

`wrangler.jsonc` configures Cloudflare Workers static assets from `reports/`.
The monthly workflow does **not** deploy to Cloudflare; any deployment integration
must be configured separately.

## Contribution conventions

Use incremental Conventional Commits: `fix:`, `feat:`, `chore:`, `docs:`, `style:`,
or `report:`. Keep pipeline changes separate from regenerated publications so
reviewers can distinguish behaviour changes from historical report revisions.

Report data and narratives © Isaac Akinmokun.

## Editorial edition and unpublished previews

Future reports use New Computer Modern for the publication, a concise brief,
class-specific asking-price benchmarks, and eight accessible SVG figures for a
combined issue. The screen edition includes expandable weekly evidence tables;
the PDF contains the core publication. DOM is discussed once in methodology.
Chart counts and prices come from computed metrics; narrative instructions require
distinct, concise findings and include the class benchmarks behind the figures.

The archive uses shared editorial colours and fonts drawn from the personal and
PS-0 sites, with a site directory, light/dark themes, search and independent PDF
links. `templates/partials/` contains the shared header, footer, tokens and theme
behaviour. This repository adapts those components for Jinja; it does not require
React or a runtime server. Font licenses and origins are bundled in
`templates/fonts/`. The social preview image is `reports/social-card.png`.

Refresh just the archive without touching published issues:

```bash
python scripts/build_dashboard.py
```

Build an **unpublished** September design sample using the cached CSV:

```bash
python scripts/preview_report.py --month 2026-09
python -m http.server --directory scratch/editorial-preview 8000
```

The preview includes evidence-derived commentary without a Gemini call. Its report
HTML and PDF are in `scratch/editorial-preview/2026-09/`. It is explicitly marked
as a design preview and uses `noindex` metadata and a disallowing robots file.
`scratch/` is ignored and is outside the deployed static assets.

`render_report.py --preview --output-root PATH` also accepts custom metrics and
narrative inputs. Preview output inside `reports/` is rejected. Rendering an
already-published issue into the real archive is rejected; use an isolated output
root for review. Publication of a future issue remains an explicit normal build.
This redesign does not create an October issue or rewrite historical reports.

Validate with `python -m unittest discover -s tests -v`. The checks cover the
publication archive's independent reading/download links, accessible figure names,
all report variants, and preservation of existing issues.

For a presentation-only review of a published issue, preserving all original
report prose, table markup, section order, methodology, issue number and dates:

```bash
python scripts/restyle_published.py --issue 2026-09 --output-root scratch/review
```

This creates a restyled HTML/PDF copy outside the archive. The script checks that
the original report body is byte-for-byte unchanged after excluding the site navbar;
only font/layout CSS, theme behaviour and shared navigation are added. Publication
metadata is copied exactly. September remains the issue published October 1, 2026.
The more substantial editorial structure is reserved for October's future issue.

The published-report presentation preview replaces obsolete print-only rules with
print-safe layouts matching the web edition: a five-column KPI strip, inline
publication details, the same reading hierarchy and table styling, repeating table
headers, and controlled page breaks. The PDF omits site navigation/download controls
and adds page numbers. SVG colours/font variables are resolved for WeasyPrint without
changing chart labels or values. A4 line wrapping will differ from a wide browser.
