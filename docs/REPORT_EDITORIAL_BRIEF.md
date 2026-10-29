# PS-0 report: proposed decision-focused editorial brief

Status: proposal for the next unpublished edition. Published editions remain intact.

## Purpose

Help readers compare observed property markets, understand the evidence and identify
what to investigate next. The current draft overcompresses analysis into short
paragraphs and displays extremes without enough mid-market or location context.
More pages alone do not solve this. Each main section needs a reader question,
segmented evidence, interpretation, practical relevance and the limits of that use.

## Reader questions

| Readers | Decisions/questions | Useful evidence | Important boundary |
| --- | --- | --- | --- |
| Buyers and tenants | What can my budget reach? Which areas offer comparable alternatives? | Area × property-class asking-price comparisons, advertised stock by budget, annual rent units, dated sample coverage | Asking amounts exclude unverified transaction costs and do not establish negotiated prices |
| Estate surveyors and valuers | Which observations support my comparable search? How dispersed and current are they? | Dated comparables, sample provenance, robust ranges, property attributes, documented exclusions | Area group medians alone do not support an individual-property valuation |
| Fund managers and investors | Where is exposure concentrated? How do submarkets differ? | Geography/class concentration, qualified benchmarks, consistent cohorts, observed repricing | Net yields/returns need matched rent/sale evidence, vacancy, expenses and achieved prices |
| Developers | What advertised stock competes with my proposed product? At which price/bedroom bands? | Location/product mix, budget bands, observed new inventory and repricing | Sparse advertisements do not prove unmet demand or a shortage; permits and absorption need other data |
| Governments and researchers | What pressures appear in the visible formal market? Where are the blind spots? | Spatial coverage, advertised rents, composition, verified external population/income/context series | Portal data does not measure the housing deficit or represent all income groups |

## Proposed core publication

1. Executive assessment: several substantive findings with locations, classes,
   evidence strength and relevance; stable facts separated from watchlist items.
2. Coverage and freshness panel: export date, latest real observations, included
   periods, missing weeks, priced observations and exclusions.
3. Geography and product mix: city/neighbourhood inventory and class composition,
   with counts and concentration explained in market context.
4. Asking-price comparison: a usable area/class matrix covering the middle of the
   market, not only the cheapest and most expensive points. Clearly identify
   properties that are not truly comparable within broad classes.
5. City/submarket briefs: Lagos and Abuja plus other cities with sufficient
   coverage. Each brief answers a concrete comparison question.
6. Repricing and observable availability: event counts and distribution; add rates
   or reduction magnitudes only with valid listing-level denominators/history.
7. Implications and watchlist: what different readers can investigate from the
   evidence; conditional interpretation rather than unsupported buy/sell advice.
8. Reproducibility and appendix: metric definitions, source/cleaning/version notes,
   reference tables and downloadable aggregate evidence where appropriate.

Aim for a readable core of roughly 12–16 pages if evidence supports it, with a
searchable HTML appendix. Do not fill pages to meet a target. Replace rigid
one-paragraph-per-topic generation with question-led sections whose statements
retain evidence references. Keep headline repetition low without starving the
analysis of explanations or necessary supporting numbers.

## What can be done with present aggregates

- City/class/area comparisons of explicitly labelled group-median statistics.
- Inventory composition, geography concentration and available area benchmarks.
- Coverage/freshness, observed week counts and incomplete-period flags.
- Counts and city concentration of recorded price-reduction events.
- More complete, navigable comparison tables and factual city briefs.

Current aggregates cannot reconstruct a pooled listing-level interquartile range
from group quartiles or establish a transaction-price index. Reconstructed old
prices must not be charted as actual appreciation. Low observed stock must not be
labelled strong demand without demand evidence.

## Additional evidence needed before stronger claims

- Deduplicated, dated listing-level snapshots with price history and provenance.
- Bedrooms, usable floor area, tenure, location granularity and condition for
  genuinely comparable segments and price-per-square-metre measures.
- Unique listing IDs/observation exposure for defensible reduction denominators.
- Achieved lease/sale values, operating costs and vacancy for return measures.
- Primary-source income, population, planning, permits and policy series for
  affordability, development pipeline and independently sourced market context.

## Professional transparency

Use concise captions stating unit, population, sample, date and statistic. Put
relevant caveats beside the affected figure, with the full method in one appendix.
Use explicit missing-data labels rather than unsupported precision or arbitrary
confidence scores. Distinguish observations, interpretation and externally sourced
context. Maintain named authorship, editorial review, stable dates, correction and
revision notes, and a suggested citation. Explain the automation role plainly;
never imply a credential, verification or market coverage we do not possess.

## Discovery plan

- Descriptive Nigeria/month report titles; crawlable substantive HTML with a PDF
  download, rather than PDF-only content.
- Durable Lagos/Abuja/property-class pages only where genuinely useful data and
  analysis support them; link through to dated evidence. Avoid thin auto-pages.
- Appropriate Article and, for actual published data, Dataset structured metadata.
- Clear authorship/methodology/citation pages, correct dates/canonical URLs,
  social previews, internal links from PS-0 and the personal website.
- Search Console measurement of indexing, query intent and useful landing pages.
- Make original charts and aggregate tables easy to cite in professional work.

## Chart typography

Enforce the bundled Menlo face for every Matplotlib text object, including ticks,
axis labels, titles, legends and annotations. Embed SVG glyph paths so neither the
browser nor PDF renderer can silently substitute a system font. This is a
presentation change only and does not alter data or commentary.

## Reference examples

- Knight Frank Lagos research: https://www.knightfrank.com.ng/research/lagos-market-update-13035.aspx
- RICS survey/data boundaries: https://www.rics.org/news-insights/market-surveys/global-commercial-property-monitors
- Google content guidance: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- Article metadata: https://developers.google.com/search/docs/appearance/structured-data/article
- Dataset metadata: https://developers.google.com/search/docs/appearance/structured-data/dataset
