from datetime import date
import tempfile
from pathlib import Path
import unittest
from test_compute_metrics import snapshots
import compute_metrics as cm
from report_identity import require_closed_month


class ReadinessTests(unittest.TestCase):
    def test_requires_closed_calendar_month(self):
        require_closed_month('2026-09', date(2026,10,29))
        for month in ('2026-10', '2026-11'):
            with self.assertRaises(ValueError): require_closed_month(month, date(2026,10,29))
        require_closed_month('2026-10', date(2026,11,1))

    def test_missing_and_excluded_weeks_are_distinct(self):
        df=snapshots()
        selected=df[df.snapshot_week==date(2026,9,7)]
        quality=cm.period_quality(df,selected,date(2026,9,1),date(2026,9,30))
        self.assertEqual(quality['excluded_week_starts'],['2026-09-14'])
        self.assertEqual(quality['missing_week_starts'],['2026-09-21','2026-09-28'])

    def test_rejects_double_counts_and_invalid_inventory(self):
        import pandas as pd
        cases=[pd.concat([snapshots(),snapshots().iloc[:1]]),snapshots().assign(active_listing_count=-1),snapshots().assign(new_listings_count=float('nan')),snapshots().assign(price_type='UNKNOWN')]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'input.csv'
            for frame in cases:
                frame.to_csv(path,index=False)
                with self.assertRaises(ValueError): cm.load_snapshots(path)
