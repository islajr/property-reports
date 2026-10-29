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
import generate_narrative as gn
import render_report as rr


def section():
    df = pd.DataFrame([
        dict(city="LAGOS", neighbourhood="Ikeja", snapshot_week=date(2026, 9, day),
             active_listing_count=10, new_listings_count=2, price_reduced_count=1,
             median_price_kobo=100_000_000, avg_days_on_market=20)
        for day in (7, 14)
    ])
    result = cm.compute_all_metrics(df, "2026-09", "September 2026", "1mo")
    result["classes"] = {"DETACHED_HOUSE": cm.compute_all_metrics(df, "2026-09", "September 2026", "1mo")}
    return result


class RenderTests(unittest.TestCase):
    def test_combined_and_single_market_reports_render(self):
        for market_type in ("all", "sale", "rent"):
            with self.subTest(market_type=market_type), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                metrics = {"type": market_type, "sales": None, "rentals": None}
                narrative = {"sales": None, "rentals": None}
                for key, selected in (("sales", "sale"), ("rentals", "rent")):
                    if market_type in ("all", selected):
                        metrics[key] = section()
                        narrative[key] = gn.PLACEHOLDER_NARRATIVE_SUB
                metrics_path = root / "metrics.json"
                narrative_path = root / "narrative.json"
                metrics_path.write_text(json.dumps(metrics))
                narrative_path.write_text(json.dumps(narrative))
                argv = ["render_report.py", "--month", "2026-09", "--no-pdf",
                        "--metrics", str(metrics_path), "--narrative", str(narrative_path)]
                with patch.object(rr, "REPORTS_DIR", root / "reports"), patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                    rr.main()
                folder = "2026-09" + ("" if market_type == "all" else "_" + market_type)
                html = (root / "reports" / folder / "index.html").read_text()
                self.assertEqual("Sales Market Analysis" in html, market_type in ("all", "sale"))
                self.assertEqual("Rentals Market Analysis" in html, market_type in ("all", "rent"))
                self.assertTrue((root / "reports/reports.json").exists())


if __name__ == "__main__":
    unittest.main()
