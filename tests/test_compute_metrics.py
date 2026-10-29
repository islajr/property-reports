import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import compute_metrics as cm


def snapshots():
    return pd.DataFrame([
        dict(city=city, neighbourhood=hood, snapshot_week=date(2026, 9, day),
             price_type="FOR_SALE", property_class=prop_class, active_listing_count=count,
             new_listings_count=1, price_reduced_count=0, median_price_kobo=100_000,
             avg_days_on_market=10)
        for day in (7, 14)
        for city, hood, prop_class, count in (
            ("LAGOS", "Shared", "DETACHED_HOUSE", 4),
            ("LAGOS", "Shared", "TERRACED_HOUSE", 4),
            ("LAGOS", "Other", "DETACHED_HOUSE", 7),
            ("ABUJA", "Shared", "DETACHED_HOUSE", 2),
        )
    ])


class MetricsTests(unittest.TestCase):
    def test_inventory_sums_classes_before_averaging_weeks(self):
        df = snapshots()
        ranking = cm.compute_inventory_ranking(df)
        self.assertEqual(ranking[0]["neighbourhood"], "Shared")
        self.assertEqual(ranking[0]["avg_weekly_active_listings"], 8)
        self.assertEqual(cm.compute_city_breakdown(df)["LAGOS"]["top_neighbourhood_by_activity"], "Shared")
        expensive = cm.compute_pricing_tiers(df)["most_expensive"]
        self.assertIn(("LAGOS", "Shared"), [(r["city"], r["neighbourhood"]) for r in expensive])
        self.assertEqual(cm.compute_overall(df, "2026-09", "September 2026", "1mo")["unique_neighbourhoods"], 3)

    def test_class_totals_reconcile_with_market_totals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path, out_path = root / "snapshots.csv", root / "metrics.json"
            snapshots().to_csv(csv_path, index=False)
            argv = ["compute_metrics.py", "--month", "2026-09", "--csv", str(csv_path), "--out", str(out_path)]
            with patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                cm.main()
            metrics = json.loads(out_path.read_text())["sales"]
            for field in ("cumulative_active_listings", "total_new_listings", "total_price_reductions"):
                self.assertEqual(metrics["overall"][field], sum(c["overall"][field] for c in metrics["classes"].values()))
            self.assertEqual(metrics["classes"]["DETACHED_HOUSE"]["overall"]["num_cities"], 2)

    def test_null_prices_are_json_null_and_not_ranked(self):
        df = snapshots()
        df["median_price_kobo"] = float("nan")
        metrics = cm.compute_all_metrics(df, "2026-09", "September 2026", "1mo")
        json.dumps(metrics, allow_nan=False)
        self.assertEqual(metrics["pricing_tiers"]["most_expensive"], [])

    def test_required_downstream_columns_are_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshots.csv"
            for column in ("price_type", "avg_days_on_market"):
                snapshots().drop(columns=[column]).to_csv(path, index=False)
                with self.subTest(column=column), self.assertRaisesRegex(ValueError, column):
                    cm.load_snapshots(path)
