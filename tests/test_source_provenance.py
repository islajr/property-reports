from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from source_provenance import read_source_metadata, write_source_metadata
import export_data


class SourceProvenanceTests(unittest.TestCase):
    def test_freshness_is_bound_to_csv_and_missing_metadata_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'snapshots.csv'
            path.write_text('aggregate export')
            self.assertEqual(read_source_metadata(path), {})
            exported = datetime(2026, 11, 1, tzinfo=timezone.utc)
            latest = datetime(2026, 10, 25, tzinfo=timezone.utc)
            write_source_metadata(path, exported, latest)
            self.assertEqual(read_source_metadata(path)['latest_source_observation'], latest.isoformat())
            path.write_text('different export')
            with self.assertRaisesRegex(ValueError, 'does not match'):
                read_source_metadata(path)

    def test_export_reads_freshness_and_data_in_one_readonly_snapshot(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (datetime(2026, 11, 1, tzinfo=timezone.utc),
                                       datetime(2026, 10, 25, tzinfo=timezone.utc))
        cursor.description = [('city',)]
        cursor.fetchall.return_value = [('LAGOS',)]
        with tempfile.TemporaryDirectory() as tmp, patch('psycopg2.connect', return_value=conn):
            path = Path(tmp) / 'export.csv'
            export_data.export_to_csv('test-only', path)
            self.assertEqual(read_source_metadata(path)['latest_source_observation'][:10], '2026-10-25')
        conn.set_session.assert_called_once_with(readonly=True, isolation_level='REPEATABLE READ')
        self.assertEqual(cursor.execute.call_count, 2)
        conn.close.assert_called_once()

    def test_disclosure_formats_known_freshness_and_marks_legacy_unknown(self):
        from jinja2 import Environment, FileSystemLoader
        from source_provenance import format_timestamp
        env = Environment(loader=FileSystemLoader(Path(__file__).resolve().parents[1] / 'templates'), autoescape=True)
        env.filters['source_time'] = format_timestamp
        template = env.get_template('partials/source_freshness.html.j2')
        known = template.render(source_freshness='2026-10-25T14:16:21+00:00', source_exported_at='2026-11-01T11:32:00+00:00')
        self.assertIn('25 October 2026, 14:16 UTC', known)
        self.assertIn('1 November 2026, 11:32 UTC', known)
        self.assertIn('not fresh collection dates', known)
        self.assertIn('not recorded', template.render(source_freshness=None))
