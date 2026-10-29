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
    Pass --placeholder explicitly to create an offline draft. Missing API keys
    otherwise fail generation. Use --force to replace existing commentary.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from report_identity import report_key, validate_metrics_identity
from narrative_validation import metrics_digest, validate_narrative
from report_evidence import evidence_for_market, takeaways

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTION = """You are a senior real estate market analyst writing a monthly intelligence
report on observed advertised Nigerian property. Your style is data-driven, precise, and
professional — similar to a Knight Frank or Stears Business report. You write for an audience of
real estate investors, developers, and financial analysts, not the general public.

You must:
- Frame all findings as observations of online listings visible through the PS-0 PropertyScraper lens, rather than generalising them as the entire physical property market.
- Ground every claim in the provided metrics. Do not invent statistics.
- Use NGN amounts as formatted (e.g. ₦254.1M, not ₦254,166,666.67).
- Be direct. No filler phrases like "It is worth noting that...".
- Use British English spelling (e.g. "analysed", "centre", "recognised").
- Do not discuss DOM in the main findings. Its observation limits are covered in methodology.
- Give each section a distinct purpose. Avoid repeating takeaway statistics in prose.
- Do not attribute changes to interest rates, policy, demand, or buyer sentiment without supplied evidence.
- Return only valid JSON matching the schema requested. No markdown fences."""

def build_prompt(metrics: dict) -> str:
    evidence = {market: {key: value for key, value in evidence_for_market(data, market).items() if key not in ('inventory.peak', 'inventory.new', 'reductions.total')} for market in ('sales', 'rentals') if (data := metrics.get(market))}
    return """Write concise analysis of observed advertised property listings using ONLY these named facts.
Return a JSON object with one block per populated market. Each block has exactly:
inventory_narrative (at most 80 words), pricing_narrative (at most 80 words),
price_reduction_narrative (at most 70 words), and evidence_refs mapping each field
to a non-empty list of the fact IDs used in it.
Use inventory.* facts for inventory, pricing.* for pricing, reductions.* for reductions.
Use the formatted numbers exactly as supplied, including units. Do not introduce numbers
or calculations absent from cited facts. Do not repeat sentences between sections.
There is no need to restate a full executive summary or produce takeaways: those are
computed separately. Explain the observations, not speculative causes. Do not discuss DOM,
macroeconomic policy, demand, realised returns, transaction prices or historical appreciation.
Independent pricing scales are class-specific; reductions are event counts, not rates.
Unpopulated markets should be null. Return valid JSON without Markdown fences.
EVIDENCE:\n""" + json.dumps(evidence, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Placeholder narrative (no API key mode)
# ---------------------------------------------------------------------------

PLACEHOLDER_NARRATIVE_SUB = {
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

def call_gemini(prompt: str, api_key: str, model_name: str) -> dict:
    try:
        import google.generativeai as genai
    except ImportError:
        print("ERROR: google-generativeai not installed. Run: pip install google-generativeai", file=sys.stderr)
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_INSTRUCTION,
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,    # Lower temperature for factual, consistent output
            response_mime_type="application/json",
        ),
    )
    print(f"Calling Gemini API ({model_name}) ...")
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
    parser.add_argument("--type", default="all", choices=["all", "sale", "rent"])
    parser.add_argument("--force", action="store_true", help="Replace an existing narrative using the current metrics.")
    parser.add_argument(
        "--period",
        default="1mo",
        choices=["1mo", "3mo", "6mo", "12mo"],
        help="Reporting period window length (default: 1mo)",
    )
    parser.add_argument(
        "--metrics",
        default=None,
        help="Path to metrics JSON. Defaults to data/metrics_YYYY-MM[_period].json.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output narrative JSON path. Defaults to data/narrative_YYYY-MM[_period].json.",
    )
    parser.add_argument(
        "--placeholder",
        action="store_true",
        help="Skip API call and write placeholder narrative (for template testing).",
    )
    args = parser.parse_args()

    key = report_key(args.month, args.period, args.type)
    metrics_path = Path(args.metrics) if args.metrics else DATA_DIR / f"metrics_{key}.json"
    out_path = Path(args.out) if args.out else DATA_DIR / f"narrative_{key}.json"

    if not metrics_path.exists():
        print(f"ERROR: Metrics file not found: {metrics_path}", file=sys.stderr)
        print(f"Run scripts/compute_metrics.py --month {args.month} first.", file=sys.stderr)
        sys.exit(1)

    with open(metrics_path) as f:
        metrics = json.load(f)
    try:
        validate_metrics_identity(metrics, args.month, args.period, args.type)
    except ValueError as exc:
        parser.error(str(exc))

    api_key = os.getenv("GEMINI_API_KEY")
    use_placeholder = args.placeholder
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

    if out_path.exists() and not args.force:
        with open(out_path) as f:
            narrative = json.load(f)
        try:
            validate_narrative(narrative, metrics)
        except ValueError as exc:
            parser.error(str(exc))
        if not narrative.get("_provenance"):
            parser.error("Existing narrative has no metrics provenance. Preserve a copy if needed, then use --force to regenerate.")
        if not use_placeholder and narrative.get('_quality_version') != 2:
            parser.error('Cached commentary predates evidence validation. Use --force to regenerate.')
        if not use_placeholder and narrative["_provenance"].get("mode") == "placeholder":
            parser.error("Existing narrative is a placeholder. Use --force with GEMINI_API_KEY to generate commentary.")
        print(f"✓ Reusing narrative with matching metrics: {out_path}")
    else:
        if use_placeholder:
            # Construct placeholder narrative based on what types are present in metrics
            narrative = {}
            if metrics.get("sales") is not None:
                narrative["sales"] = PLACEHOLDER_NARRATIVE_SUB
            else:
                narrative["sales"] = None
                
            if metrics.get("rentals") is not None:
                narrative["rentals"] = PLACEHOLDER_NARRATIVE_SUB
            else:
                narrative["rentals"] = None
        else:
            if not api_key:
                parser.error("GEMINI_API_KEY is required. Use --placeholder explicitly for an offline draft.")
            prompt = build_prompt(metrics)
            narrative = call_gemini(prompt, api_key, model_name)
            if not isinstance(narrative, dict):
                parser.error('Narrative response must be an object.')
            narrative['_quality_version'] = 2
            for market in ('sales', 'rentals'):
                if metrics.get(market) and isinstance(narrative.get(market), dict):
                    narrative[market]['key_takeaways'] = takeaways(metrics[market], market)

        try:
            validate_narrative(narrative, metrics)
        except ValueError as exc:
            parser.error(str(exc))
        narrative["_provenance"] = {
            "metrics_sha256": metrics_digest(metrics),
            "mode": "placeholder" if use_placeholder else "gemini",
            "model": None if use_placeholder else model_name,
        }

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
