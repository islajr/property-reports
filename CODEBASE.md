# Codebase reference

This document describes the implementation in this repository. Upstream scraper
and database behaviour must be verified in `property-intel`; no Java sources or
Flyway migrations are maintained here.

## Entry points and files

| File | Responsibility |
| --- | --- |
| `run.sh` | Validate options, optionally export, then compute, narrate, and render |
| `scripts/report_identity.py` | Canonical `YYYY-MM[_period][_type]` identifiers |
| `scripts/export_data.py` | Reconstruct weekly aggregates from Supabase |
| `scripts/compute_metrics.py` | Produce sales/rentals metrics and property-class breakdowns |
| `scripts/generate_narrative.py` | Build prompts, call Gemini, or create explicit draft commentary |
| `scripts/narrative_validation.py` | Validate narrative fields and metrics fingerprints |
| `scripts/render_report.py` | Render HTML/PDFs, charts, metadata, catalogue, and discovery files |
| `scripts/download_fonts.py` | Download six Inter/JetBrains Mono WOFF2 assets |
| `templates/report.html.j2` | Shared HTML/print report layout |
| `tests/` | Offline regression checks using synthetic data and temporary directories |
| `.github/workflows/monthly_report.yml` | Monthly generation, output commits, and input archives |
| `.github/workflows/tests.yml` | PR and branch regression checks |
| `wrangler.jsonc` | Cloudflare static asset configuration for `reports/` |

The catalogue template is `templates/index.html.j2`.
Edit the source templates and scripts for future builds. Files under `reports/`
are generated publications, not template sources.

## Export contract

The exporter uses `SUPABASE_DB_URL` loaded from `.env` or the environment. It
queries `raw_data.scraped_listings`, `raw_data.listing_history`, and
`market.classify_property(title, property_type, bedrooms)`. It does **not** export
`market.neighbourhood_snapshots` directly.

`EXPORT_QUERY` generates Monday-start weeks from 2026-04-06 through the current
week. A listing contributes when first seen by the week's final day and either
currently active or last seen on/after the week's start. Consequently, current
active status can preserve old inventory even without a fresh observation.
Current asking price and property classification are reused across its historical
weeks; price-change history is used to count reductions, not to reconstruct prices.

Rows are grouped by city, neighbourhood, week, price type, and property class.
The output includes these dimensions and:

- `id`: an MD5 of the concatenated dimensions; the analytics code uses dimensions,
  not this identifier, for grouping.
- `active_listing_count`, `new_listings_count`, `price_reduced_count`.
- `median_price_kobo`, `p25`, `p75`, `p90`.
- `avg_days_on_market`, `computed_at`.

The query counts multiple price-reduction events separately. DOM averages elapsed
days from first observation to the earlier of last observation and the week's
exclusive end, with a floor of one day. No outage annotation or explicit weekly
carry-forward algorithm exists in this pipeline.

The CSV is replaced at `data/neighbourhood_snapshots.csv` unless `--out` is supplied.
A manually exported CSV must match this contract, including `property_class`.

## Metrics contract

`load_snapshots` normalises dimensions, validates required columns, converts dates
and numeric fields, and excludes `FOR_SHORT_LET`. `get_period_dates` calculates
calendar windows; `filter_to_period` selects by snapshot start date and may exclude
a trailing week whose inventory is less than 30% of preceding weeks' median.

The result is `data/metrics_{key}.json`:

```text
{
  type: all | sale | rent,
  sales: market metrics | null,
  rentals: market metrics | null,
  coverage: report-wide cities, neighbourhoods, weeks, and date range,
  _source: { report_key, csv_sha256 }
}
```

Each populated market contains:

- `overall`: peak and cumulative active inventory, new listings, reduction events,
  first-to-last inventory growth, geography coverage, and summary prices.
- `weekly_aggregates`: summed counts and unweighted median of source group medians.
- `inventory_ranking`: neighbourhood totals summed over property classes within
  each week, then averaged over observed weeks.
- `pricing_tiers`: most expensive/affordable areas by unweighted mean of observed
  group medians. Average weekly inventory thresholds are 5/3 respectively.
- `city_breakdown`: city totals, median of group medians, and top active area.
- `price_reduction_analysis`: total events, peak week, and city concentrations.
- `classes`: the same metric groups for each property class, without recursion.

Low-volume class rows remain in metrics and tables. Pricing thresholds apply to
rank eligibility, not to deleting class inventory. Additive class totals reconcile
with their market totals; peaks and growth percentages are not additive.

Neighbourhood identity is `(city, neighbourhood)`. Report-wide coverage uses both
markets for combined reports. Pricing summaries do not pool raw listings or weight
by group inventory; exact listing medians cannot be recovered from group medians.
Prices use kobo internally and divide by 100 for NGN display. Null summary prices
are emitted as JSON null; pricing rankings omit areas with no usable price.

## Narrative contract

`generate_narrative.py` uses `google-generativeai`, with `GEMINI_API_KEY` and an
optional `GEMINI_MODEL` override (default string: `gemini-3.5-flash`). No live model
availability check is part of offline tests. Python 3.12+ is required by the prompt
syntax used in this codebase.

`build_prompt_section` supplies overall metrics, weekly figures, area rankings,
city breakdowns, and reductions. It does not send each class's entire metrics
object. Prompts explain that asking prices, reconstructed history, and cumulative
listing-weeks must not be treated as transaction prices or unique listings.

The response is parsed as JSON and checked by `validate_narrative`; there is no
Pydantic dependency or response schema enforced by that library. Legacy narrative blocks require executive summary, inventory, pricing, Lagos, Abuja,
other-city, reduction, outlook, and takeaway fields. New version-2 blocks require
only inventory/pricing/reduction paragraphs, evidence references and computed takeaways. Abuja and other-city text may be null.
Field validation cannot establish the factual correctness of generated prose.

A narrative has `sales` and `rentals` blocks plus `_provenance`, which records a
canonical SHA-256 of its metrics, generation mode, and model name. Matching cached
narratives are reused. Stale or unverified caches fail generation without changing
the file; `--force` explicitly replaces them. `--placeholder` is required for draft
creation and a production invocation cannot silently reuse a draft cache.

The renderer validates structure and any existing fingerprint before writing. It
allows legacy files without provenance with a warning, enabling old publications
to be rendered without forcing a new paid API call.

## Rendering and catalogue

`render_html` enables HTML escaping. Narrative paragraphs are rendered as text;
only internally built font CSS and SVG charts are marked safe. Fonts are embedded
as base64 WOFF2. SVG trajectory charts preserve gaps in missing prices and still
show inventory; regional SVG labels are escaped.

Reports share one Jinja loop for populated sales and rental sections. Each section
contains KPIs, commentary, property-class inventory/pricing tables, regional
figures, weekly tables, reductions, and outlook. Common methodology and disclaimer
sections follow. Period and market classes supply CSS themes; print media rules
control A4 output and pagination.

Canonical URLs use the full report key. Social descriptions use the selected
market's takeaways. Combined headers use report-wide coverage; legacy metrics
without `coverage` retain the previous primary-market fallback.

Existing issue numbers and publication dates are preserved. New issue numbers
follow the largest stored number, rather than the report folder's sorted index.
Legacy human-readable publication dates supply the ISO date when absent.

HTML, requested PDF, and metadata are prepared in a temporary directory before
replacing publication files. A PDF failure stops the build before existing files
are replaced. This is not a transaction across all output files. Metadata records
the publication identity, coverage, PDF filename (or null for HTML-only output),
and SHA-256 fingerprints of inputs. HTML-only rebuilds retain an older PDF file on
disk but omit its download link and catalogue badge.

`regenerate_index` scans report folders containing HTML and uses `meta.json` when
available, with legacy filename/PDF discovery fallbacks. It creates `reports.json`
and embeds the same catalogue data for client-side search, market/period filters,
featured publication, and pagination in batches of six. Static links remain as a
no-JavaScript fallback. Sitemap and robots generation use the configured domain,
`reports.akinmokun.com`, which is currently hard-coded in the templates/scripts.

## Operations and boundaries

The monthly workflow runs at 05:00 UTC on the first day of each month or via manual
dispatch. It builds monthly combined reports and commits static assets. CI input
archives retain the exact CSV, metrics, commentary, metadata, and dependency pins
for 90 days. Metrics/narrative hashes allow archived inputs to be checked against
publication metadata. Inputs from older publications are not retroactively archived.

`data/` and `.env` are ignored; report HTML, PDFs, metadata, fonts, and static brand
assets are tracked. Run tests with `python -m unittest discover -s tests -v`.
Offline tests exercise rendering, identity, caching, aggregation, CLI failures,
and real PDF compilation/failure preservation without contacting external services.
WeasyPrint 62.3 requires the pinned pydyf 0.10.0 stream API; newer pydyf releases
can install successfully but fail at PDF generation.

Cloudflare serving is configured in Wrangler. No Cloudflare deployment action is
included here. No runtime API server, client build framework, or database
migrations are part of this repository.

## Editorial publication update

`INDEX_TEMPLATE` has moved to `templates/index.html.j2`; the dashboard and report
share partials under `templates/partials/`. `build_embedded_fonts_css` selects a
smaller font set for the dashboard. New Computer Modern is bundled for the report
body, headings and PDF; original font licenses and source notes accompany assets.

`scripts/editorial.py` builds deterministic selections of area benchmarks and
Matplotlib SVG figures for inventory, property composition, class-specific prices,
and city reduction events. Each SVG has an accessible name and a caption. Pricing
panels have independent scales and use the same area selections as the adjacent
table. Charts do not present reconstructed asking prices as appreciation history.

The main PDF uses a cover, brief, three pages per populated market and methodology.
The full combined September sample is nine pages. The HTML appendix retains class
weekly evidence; it is excluded from print to preserve the core reading sequence.

`scripts/build_dashboard.py` regenerates the archive only. `scripts/preview_report.py`
computes a historical sample into ignored scratch space and creates concise,
evidence-derived sample commentary. `render_report.py --output-root` supports
isolated builds; `--preview` requires such a root outside `reports/`, adds a visible
preview banner and noindex metadata, and prevents a public sitemap. Existing
published issues cannot be overwritten in the real publication directory.


## Evidence contract and readiness

`report_evidence.py` owns deterministic class/area selection and fact IDs shared
by figures, tables, model prompts and narrative checks. New model responses use
`_quality_version: 2`; paragraph references must belong to that paragraph's section,
numeric tokens must be present in cited facts, and word/repetition/topic checks
run before a response is saved. Takeaways are computed rather than model-authored.
These checks do not establish all semantic or causal correctness.

Metrics include `quality` with expected/included/missing/excluded week starts and
missing/invalid price group counts. Price benchmarks expose observed and priced
weeks plus average weekly inventory. Zero/non-finite prices become missing prices
without deleting inventory; the export query excludes non-positive asking prices
from percentile calculations. Input validation rejects duplicate snapshot keys and
invalid counts/dimensions/dates. The existing tail-week heuristic is unchanged.

`require_closed_month` is called by both the normal shell pipeline and direct
publication renderer; previews remain possible outside the public assets. The
October-quality study uses September source data in ignored scratch space. No
archived reports or October publication assets are generated by this change.
