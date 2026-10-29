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
                metrics["coverage"] = dict(section()["overall"], num_cities=2, unique_neighbourhoods=3)
                narrative = {"sales": None, "rentals": None}
                for key, selected in (("sales", "sale"), ("rentals", "rent")):
                    if market_type in ("all", selected):
                        metrics[key] = section()
                        narrative[key] = gn.PLACEHOLDER_NARRATIVE_SUB
                metrics_path = root / "metrics.json"
                narrative_path = root / "narrative.json"
                metrics_path.write_text(json.dumps(metrics))
                narrative_path.write_text(json.dumps(narrative))
                folder = "2026-09" + ("" if market_type == "all" else "_" + market_type)
                report_dir = root / "reports" / folder
                report_dir.mkdir(parents=True)
                (report_dir / "meta.json").write_text(json.dumps({"issue_number": 17, "published_date": "October 1, 2026"}))
                argv = ["render_report.py", "--month", "2026-09", "--type", market_type, "--no-pdf",
                        "--metrics", str(metrics_path), "--narrative", str(narrative_path)]
                with patch.object(rr, "REPORTS_DIR", root / "reports"), patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                    rr.main()
                html = (root / "reports" / folder / "index.html").read_text()
                self.assertEqual("Sales Market Analysis" in html, market_type in ("all", "sale"))
                self.assertEqual("Rentals Market Analysis" in html, market_type in ("all", "rent"))
                self.assertTrue((root / "reports/reports.json").exists())
                self.assertIn(f'href="https://reports.akinmokun.com/{folder}/"', html)
                self.assertIn('content="[PLACEHOLDER] Set GEMINI_API_KEY', html)
                meta = json.loads((report_dir / "meta.json").read_text())
                self.assertEqual(meta["issue_number"], 17)
                self.assertEqual(meta["published_date_iso"], "2026-10-01")
                self.assertEqual(meta["num_cities"], 2)
                self.assertEqual(meta["unique_neighbourhoods"], 3)


if __name__ == "__main__":
    unittest.main()
