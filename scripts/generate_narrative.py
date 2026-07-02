"""
scripts/generate_narrative.py

Reads the metrics JSON for a reporting period, sends a structured prompt to
the Gemini API (free tier), and writes the narrative paragraphs to a JSON file.

The narrative JSON is then consumed by render_report.py to fill in the Jinja2
report template alongside the raw computed metrics.

Usage:
    python scripts/generate_narrative.py --month 2026-06

Output:
    data/narrative_2026-06.json

Environment:
    GEMINI_API_KEY — from .env or environment (get one free at aistudio.google.com)

Offline / no-key mode:
    If GEMINI_API_KEY is not set, the script writes placeholder narrative strings
    so you can still render and inspect the report template layout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTION = """You are a senior real estate market analyst writing a monthly intelligence
report on the Nigerian residential property market. Your style is data-driven, precise, and
professional — similar to a Knight Frank or Stears Business report. You write for an audience of
real estate investors, developers, and financial analysts, not the general public.

You must:
- Ground every claim in the provided metrics. Do not invent statistics.
- Use NGN amounts as formatted (e.g. ₦254.1M, not ₦254,166,666.67).
- Be direct. No filler phrases like "It is worth noting that...".
- Use British English spelling (e.g. "analysed", "centre", "recognised").
- Return only valid JSON matching the schema requested. No markdown fences."""

NARRATIVE_SCHEMA = {
    "executive_summary": "string (2-3 paragraphs synthesising the period's key developments)",
    "inventory_narrative": "string (1-2 paragraphs on listing volume distribution and what it signals)",
    "pricing_narrative": "string (1-2 paragraphs on price tiers, luxury ceiling, and affordable end)",
    "lagos_narrative": "string (1 paragraph Lagos market commentary)",
    "abuja_narrative": "string (1 paragraph Abuja market commentary, if Abuja data present, else null)",
    "other_cities_narrative": "string (1 paragraph on remaining cities, if data present, else null)",
    "price_reduction_narrative": "string (1 paragraph interpreting price reduction events as a market signal)",
    "outlook": "string (1 paragraph forward-looking commentary based on observed trends)",
    "key_takeaways": "array of 3-5 short bullet strings (each under 25 words)",
}


def build_prompt(metrics: dict) -> str:
    ov = metrics["overall"]
    weekly = metrics["weekly_aggregates"]
    inv = metrics["inventory_ranking"]
    pricing = metrics["pricing_tiers"]
    city_bkd = metrics["city_breakdown"]
    reductions = metrics["price_reduction_analysis"]

    # Format weekly table for the prompt
    weekly_lines = []
    for w in weekly:
        ngn = f"₦{w['median_price_ngn'] / 1_000_000:.1f}M" if w.get("median_price_ngn") else "N/A"
        weekly_lines.append(
            f"  {w['week']}: active={w['active_listing_count']:,}  "
            f"new={w['new_listings_count']:,}  reductions={w['price_reduced_count']}  "
            f"median={ngn}"
        )

    # Format top inventory
    inv_lines = [
        f"  {r['rank']}. {r['neighbourhood']} ({r['city']}): "
        f"avg {r['avg_weekly_active_listings']} active/week"
        for r in inv
    ]

    # Format expensive
    exp_lines = [
        f"  {r['rank']}. {r['neighbourhood']} ({r['city']}): "
        f"₦{r['avg_median_price_ngn']/1_000_000:.1f}M  DOM:{r['avg_days_on_market']}d"
        for r in pricing["most_expensive"]
        if r["avg_median_price_ngn"] is not None
    ]

    # Format affordable
    aff_lines = [
        f"  {r['rank']}. {r['neighbourhood']} ({r['city']}): "
        f"₦{r['avg_median_price_ngn']/1_000:,.0f}k  DOM:{r['avg_days_on_market']}d"
        for r in pricing["most_affordable"]
        if r["avg_median_price_ngn"] is not None
    ]

    city_lines = [
        f"  {city}: {data['num_neighbourhoods']} neighbourhoods  "
        f"top area={data['top_neighbourhood_by_activity']}  "
        f"median=₦{data['median_price_ngn']/1_000_000:.1f}M"
        for city, data in city_bkd.items()
        if data.get("median_price_ngn")
    ]

    prompt = f"""Generate a professional market report narrative for the following data.
Return ONLY valid JSON matching this schema exactly:
{json.dumps(NARRATIVE_SCHEMA, indent=2)}

--- METRICS ---

PERIOD: {ov['report_period_label']} ({ov['date_range']['start']} to {ov['date_range']['end']})
WEEKS COVERED: {ov['num_weeks']}
CITIES: {', '.join(ov['cities'])}
UNIQUE NEIGHBOURHOODS: {ov['unique_neighbourhoods']}
TOTAL SNAPSHOT RECORDS: {ov['total_snapshot_records']:,}

CUMULATIVE ACTIVE LISTINGS (sum across all weeks): {ov['cumulative_active_listings']:,}
TOTAL NEW LISTINGS DISCOVERED: {ov['total_new_listings']:,}
TOTAL PRICE REDUCTION EVENTS: {ov['total_price_reductions']:,}
PEAK ACTIVE LISTINGS (latest week): {ov['peak_active_listings']:,}
EARLIEST ACTIVE LISTINGS (first week): {ov['earliest_active_listings']:,}
GROWTH FIRST→LAST WEEK: {ov['active_listings_growth_pct']}%

WEEKLY AGGREGATES:
{chr(10).join(weekly_lines)}

TOP 10 NEIGHBOURHOODS BY ACTIVITY:
{chr(10).join(inv_lines)}

TOP 10 MOST EXPENSIVE (avg median price, min {pricing['filter_note']['expensive_min_listings']} avg listings):
{chr(10).join(exp_lines)}

TOP 10 MOST AFFORDABLE (avg median price, min {pricing['filter_note']['affordable_min_listings']} avg listings):
{chr(10).join(aff_lines)}

PER-CITY SUMMARY:
{chr(10).join(city_lines)}

PRICE REDUCTIONS:
  Total: {reductions['total_price_reductions']}
  Peak week: {reductions['peak_week']} ({reductions['peak_week_count']} reductions)
  By city: {json.dumps({r['city']: r['total_reductions'] for r in reductions['by_city']})}

--- END METRICS ---

Return only the JSON object. No markdown. No explanation."""

    return prompt


# ---------------------------------------------------------------------------
# Placeholder narrative (no API key mode)
# ---------------------------------------------------------------------------

PLACEHOLDER_NARRATIVE = {
    "executive_summary": (
        "[PLACEHOLDER — set GEMINI_API_KEY and re-run to generate narrative.] "
        "The market report for this period covers data collected by PS-0 PropertyScraper."
    ),
    "inventory_narrative": "[PLACEHOLDER]",
    "pricing_narrative": "[PLACEHOLDER]",
    "lagos_narrative": "[PLACEHOLDER]",
    "abuja_narrative": "[PLACEHOLDER]",
    "other_cities_narrative": "[PLACEHOLDER]",
    "price_reduction_narrative": "[PLACEHOLDER]",
    "outlook": "[PLACEHOLDER]",
    "key_takeaways": [
        "[PLACEHOLDER] Set GEMINI_API_KEY and re-run generate_narrative.py.",
    ],
}


# ---------------------------------------------------------------------------
# Gemini API call
# ---------------------------------------------------------------------------

def call_gemini(prompt: str, api_key: str) -> dict:
    try:
        import google.generativeai as genai
    except ImportError:
        print("ERROR: google-generativeai not installed. Run: pip install google-generativeai", file=sys.stderr)
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-3.5-flash",
        system_instruction=SYSTEM_INSTRUCTION,
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,    # Lower temperature for factual, consistent output
            response_mime_type="application/json",
        ),
    )
    print("Calling Gemini API (gemini-3.5-flash) ...")
    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip markdown fences if present despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Gemini returned invalid JSON: {e}", file=sys.stderr)
        print(f"Raw response (first 500 chars): {raw[:500]}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate LLM narrative for a monthly report.")
    parser.add_argument("--month", required=True, help="Reporting month in YYYY-MM format.")
    parser.add_argument(
        "--metrics",
        default=None,
        help="Path to metrics JSON. Defaults to data/metrics_YYYY-MM.json.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output narrative JSON path. Defaults to data/narrative_YYYY-MM.json.",
    )
    parser.add_argument(
        "--placeholder",
        action="store_true",
        help="Skip API call and write placeholder narrative (for template testing).",
    )
    args = parser.parse_args()

    metrics_path = Path(args.metrics) if args.metrics else DATA_DIR / f"metrics_{args.month}.json"
    out_path = Path(args.out) if args.out else DATA_DIR / f"narrative_{args.month}.json"

    if not metrics_path.exists():
        print(f"ERROR: Metrics file not found: {metrics_path}", file=sys.stderr)
        print("Run scripts/compute_metrics.py --month {args.month} first.", file=sys.stderr)
        sys.exit(1)

    with open(metrics_path) as f:
        metrics = json.load(f)

    api_key = os.getenv("GEMINI_API_KEY")

    if args.placeholder or not api_key:
        if not api_key:
            print("GEMINI_API_KEY not set — writing placeholder narrative.")
        narrative = PLACEHOLDER_NARRATIVE
    else:
        prompt = build_prompt(metrics)
        narrative = call_gemini(prompt, api_key)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(narrative, f, indent=2)

    print(f"✓ Narrative written to {out_path}")

    # Sanity check: warn if any placeholder strings remain
    raw = json.dumps(narrative)
    if "[PLACEHOLDER]" in raw:
        print("  ⚠  Narrative contains placeholder strings — set GEMINI_API_KEY and re-run.")


if __name__ == "__main__":
    main()
