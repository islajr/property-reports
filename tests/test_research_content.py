import hashlib
import tempfile
from pathlib import Path
import unittest
from test_compute_metrics import snapshots
import compute_metrics as cm
from research_content import build_research


class ResearchTests(unittest.TestCase):
    def test_concentration_and_benchmarks_use_included_weeks_and_exact_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'snapshots.csv';frame=snapshots();frame.to_csv(path,index=False)
            df=cm.load_snapshots(path)
            data=cm.compute_all_metrics(df,'2026-09','September 2026','1mo')
            metrics={'sales':data,'rentals':None,'_source':{'csv_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}
            study=build_research(metrics,path)['sales']
            self.assertEqual(sum(city['listing_weeks'] for city in study['cities']),data['overall']['cumulative_active_listings'])
            self.assertAlmostEqual(sum(city['share'] for city in study['cities']),100,places=1)
            self.assertTrue(all(row['active']>=3 for row in study['all_comparisons']))
            path.write_text(path.read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'differs'):build_research(metrics,path)

    def test_legacy_inputs_do_not_claim_complete_research_coverage(self):
        self.assertEqual(build_research({'sales':{}},'missing.csv'),{})

    def test_excluded_weeks_and_unpriced_inventory_do_not_contaminate_comparisons(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'snapshots.csv'
            frame = snapshots()
            frame.loc[frame.neighbourhood == 'Other', 'median_price_kobo'] = float('nan')
            frame.loc[frame.snapshot_week.astype(str) == '2026-09-14', 'median_price_kobo'] = 999_000_000
            frame.to_csv(path, index=False)
            data = cm.compute_all_metrics(cm.load_snapshots(path), '2026-09', 'September 2026', '1mo')
            data['overall']['weeks'] = ['2026-09-07']
            metrics = {'sales': data, '_source': {'csv_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}}
            study = build_research(metrics, path)['sales']
            self.assertEqual(study['total_listing_weeks'], 17)
            self.assertEqual(study['report_weeks'], 1)
            self.assertTrue(all(row['price'] == 1000 for row in study['all_comparisons']))
            self.assertTrue(all(row['neighbourhood'] != 'Other' for row in study['all_comparisons']))
            self.assertEqual(study['cities'][0]['average_active'], 15)
            self.assertEqual(len(study['all_comparisons']), 2)

    def test_download_preserves_units_and_sanitizes_formula_text(self):
        from research_content import comparison_download, research_provenance
        row = dict(city='LAGOS', neighbourhood='=1+2', class_key='FLAT',
                   price=1234567.89, active=3.2, weeks=2, priced_weeks=1)
        research = {'rentals': {'all_comparisons': [row], 'report_weeks': 4}}
        exported = comparison_download(research)[0]
        self.assertEqual(exported['mean_group_median_ngn'], 1234567.89)
        self.assertEqual(exported['neighbourhood'], "'=1+2")
        self.assertEqual(exported['rental_period'], 'year_assumed')
        self.assertEqual(exported['report_weeks'], 4)
        provenance = research_provenance({'_source': {'csv_sha256': 'abc'},
                                         'rentals': {'overall': {'weeks': ['2026-09-07']}}}, research)
        self.assertEqual(provenance['source_csv_sha256'], 'abc')
