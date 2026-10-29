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

    def test_zero_prices_are_flagged_and_excluded_without_losing_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'input.csv'
            snapshots().assign(median_price_kobo=0).to_csv(path,index=False)
            df=cm.load_snapshots(path)
            self.assertTrue(df.median_price_kobo.isna().all())
            self.assertEqual(len(df),len(snapshots()))
            self.assertEqual(df.active_listing_count.sum(),snapshots().active_listing_count.sum())
            self.assertEqual(int(df['_invalid_price'].sum()),len(df))

    def test_pricing_coverage_distinguishes_missing_price_weeks(self):
        frame=snapshots()
        frame.loc[frame.snapshot_week==date(2026,9,14),'median_price_kobo']=float('nan')
        rows=cm.compute_pricing_tiers(frame)['most_expensive']
        self.assertTrue(rows)
        self.assertTrue(all(row['num_weeks_observed']==2 and row['num_price_weeks_observed']==1 for row in rows))
