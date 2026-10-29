"""Build an unpublished sample from a completed month's CSV, without API calls."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from narrative_validation import metrics_digest
from editorial import money

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--month', default='2026-09')
    parser.add_argument('--output-root', type=Path, default=ROOT / 'scratch/editorial-preview')
    args = parser.parse_args()
    output = args.output_root.resolve()
    archive = ROOT / 'reports'
    if output == archive or archive in output.parents:
        parser.error('Preview output must be outside reports/.')
    inputs = output / '_inputs'
    inputs.mkdir(parents=True, exist_ok=True)
    metrics_path, narrative_path = inputs / 'metrics.json', inputs / 'narrative.json'
    subprocess.run([sys.executable, str(ROOT / 'scripts/compute_metrics.py'), '--month', args.month, '--out', str(metrics_path)], check=True)
    metrics = json.loads(metrics_path.read_text())
    narrative = {}
    for market in ('sales', 'rentals'):
        data = metrics.get(market)
        if not data:
            narrative[market] = None
            continue
        ov = data['overall']
        top = data['inventory_ranking'][0] if data['inventory_ranking'] else None
        inventory = f"PS-0 observed a weekly peak of {ov['peak_active_listings']:,} active {market} listings across {ov['num_cities']} cities. The period includes {ov['num_weeks']} snapshot starts."
        if top:
            inventory += f" {top['neighbourhood']} in {top['city'].title()} led the area ranking with {top['avg_weekly_active_listings']:,.1f} average observed active listings per week."
        pricing = 'Asking prices differ by property class and location. The benchmarks below compare eligible areas within each class, using means of observed group medians. Each panel has its own scale; the table identifies the areas behind the points.'
        reductions = f"The source recorded {ov['total_price_reductions']:,} price-reduction events in the {market} market. The city comparison shows event counts, which should be read alongside market size rather than as rates of discounting."
        narrative[market] = dict(executive_summary=inventory, inventory_narrative=inventory, pricing_narrative=pricing,
            lagos_narrative='City coverage is included in the evidence tables.', abuja_narrative=None, other_cities_narrative=None,
            price_reduction_narrative=reductions, outlook='Interpretation is limited to the observations in this period.',
            key_takeaways=[f"Peak observed {market} inventory: {ov['peak_active_listings']:,} active listings.",
                           f"{ov['total_new_listings']:,} listings first discovered during the included weeks.",
                           f"{ov['total_price_reductions']:,} asking-price reduction events recorded."])
    narrative['_provenance'] = {'metrics_sha256': metrics_digest(metrics), 'mode': 'evidence-preview', 'model': None}
    narrative_path.write_text(json.dumps(narrative, indent=2))
    subprocess.run([sys.executable, str(ROOT / 'scripts/render_report.py'), '--month', args.month,
                    '--metrics', str(metrics_path), '--narrative', str(narrative_path), '--preview', '--output-root', str(output)], check=True)


if __name__ == '__main__':
    main()
