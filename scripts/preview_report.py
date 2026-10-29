"""Build an unpublished sample from a completed month's CSV, without API calls."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from narrative_validation import metrics_digest
from report_evidence import evidence_narrative

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
    narrative = evidence_narrative(metrics)
    narrative['_provenance'] = {'metrics_sha256': metrics_digest(metrics), 'mode': 'evidence-preview', 'model': None}
    narrative_path.write_text(json.dumps(narrative, indent=2))
    subprocess.run([sys.executable, str(ROOT / 'scripts/render_report.py'), '--month', args.month,
                    '--metrics', str(metrics_path), '--narrative', str(narrative_path), '--preview', '--output-root', str(output)], check=True)


if __name__ == '__main__':
    main()
