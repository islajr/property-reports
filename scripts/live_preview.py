"""Create an isolated, unpublished live-data preview; regular pipeline inputs stay untouched."""
import argparse
from datetime import datetime, date, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from report_identity import report_key

ROOT = Path(__file__).resolve().parents[1]


def protected_hashes():
    paths = list((ROOT / 'reports').rglob('*')) + list((ROOT / 'data').glob('*'))
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths if path.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--month', required=True)
    parser.add_argument('--output-root', type=Path)
    parser.add_argument('--evidence-only', action='store_true', help='Use computed commentary without sending data to Gemini.')
    args = parser.parse_args()
    key = report_key(args.month)
    now = datetime.now(timezone.utc)
    cutoff = now.astimezone(ZoneInfo('Africa/Lagos')).date()
    output = (args.output_root or ROOT / 'scratch' / f'live-{key}-{now.strftime("%Y%m%dT%H%M%SZ")}').resolve()
    scratch = (ROOT / 'scratch').resolve()
    if scratch not in output.parents:
        parser.error('Live preview must use a dedicated directory under scratch/.')
    if output.exists():
        parser.error('Use a new output directory; live preview caches must remain separate.')
    load_dotenv(ROOT / '.env')
    if not os.getenv('SUPABASE_DB_URL') or (not args.evidence_only and not os.getenv('GEMINI_API_KEY')):
        parser.error('SUPABASE_DB_URL and GEMINI_API_KEY are required for a real-data/Gemini preview.')
    before = protected_hashes()
    inputs = output / '_inputs'
    inputs.mkdir(parents=True)
    csv_path, metrics_path, narrative_path = [inputs / name for name in ('snapshots.csv', 'metrics.json', 'narrative.json')]
    try:
        # Export query is SELECT-only. Enforce a read-only session as well.
        import psycopg2
        import csv
        from export_data import EXPORT_QUERY
        with psycopg2.connect(os.environ['SUPABASE_DB_URL'], connect_timeout=20,
                              options='-c default_transaction_read_only=on -c statement_timeout=180000') as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT NOW(), MAX(last_seen_at) FROM raw_data.scraped_listings')
                db_time, latest_seen = cursor.fetchone()
                cursor.execute(EXPORT_QUERY)
                names = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                with csv_path.open('w', newline='') as stream:
                    writer = csv.writer(stream); writer.writerow(names); writer.writerows(rows)
        subprocess.run([sys.executable, str(ROOT / 'scripts/compute_metrics.py'), '--month', key,
                        '--csv', str(csv_path), '--out', str(metrics_path)], check=True)
        metrics = json.loads(metrics_path.read_text())
        metrics['quality']['as_of_date'] = cutoff.isoformat()
        metrics['quality']['partial_week_starts'] = [week for week in metrics['quality']['included_week_starts']
            if date.fromisoformat(week) + timedelta(days=6) >= cutoff]
        metrics_path.write_text(json.dumps(metrics, indent=2, allow_nan=False))
        manifest = {'status': 'unpublished-draft', 'month': key, 'as_of_date': cutoff.isoformat(),
                    'generated_at_utc': now.isoformat(), 'database_export_at': str(db_time),
                    'latest_source_last_seen_at': str(latest_seen), 'regular_inputs_unchanged': False, 'protected_sha256': before,
                    'commentary_mode': 'evidence-only' if args.evidence_only else 'gemini'}
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        if args.evidence_only:
            from report_evidence import evidence_narrative
            from narrative_validation import metrics_digest, validate_narrative
            narrative = evidence_narrative(metrics)
            narrative['_provenance'] = {'metrics_sha256': metrics_digest(metrics), 'mode': 'evidence-preview', 'model': None}
            validate_narrative(narrative, metrics)
            narrative_path.write_text(json.dumps(narrative, indent=2))
        else:
            subprocess.run([sys.executable, str(ROOT / 'scripts/generate_narrative.py'), '--month', key,
                            '--metrics', str(metrics_path), '--out', str(narrative_path)], check=True)
        subprocess.run([sys.executable, str(ROOT / 'scripts/render_report.py'), '--month', key,
                        '--metrics', str(metrics_path), '--narrative', str(narrative_path),
                        '--preview', '--as-of', cutoff.isoformat(), '--source-last-seen', str(latest_seen)[:10], '--output-root', str(output / 'site')], check=True)
        print('Private preview:', output / 'site' / key)
    finally:
        if before != protected_hashes():
            raise RuntimeError('Regular reports or data changed during preview. Inspect before publishing anything.')
        manifest_path = output / 'manifest.json'
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            manifest['regular_inputs_unchanged'] = True
            manifest_path.write_text(json.dumps(manifest, indent=2))
        print('Verified: regular report assets and data caches are unchanged.')


if __name__ == '__main__':
    main()
