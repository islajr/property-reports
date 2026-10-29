import contextlib
import io
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
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
    def test_real_pdf_compilation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            html_path, pdf_path = root / "index.html", root / "report.pdf"
            html_path.write_text("<!doctype html><html><body><p>PDF regression check</p></body></html>")
            with contextlib.redirect_stdout(io.StringIO()):
                rr.render_pdf(html_path, pdf_path)
            self.assertTrue(pdf_path.read_bytes().startswith(b"%PDF-"))

    def test_missing_pdf_dependency_fails(self):
        with patch.dict(sys.modules, {"weasyprint": None}), self.assertRaisesRegex(RuntimeError, "--no-pdf"):
            rr.render_pdf(Path("unused.html"), Path("unused.pdf"))

    def test_pdf_failure_preserves_published_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_dir = root / "reports/2026-09"
            report_dir.mkdir(parents=True)
            (report_dir / "index.html").write_text("Original publication")
            original_meta = json.dumps({"issue_number": 2, "published_date": "October 1, 2026"})
            (report_dir / "meta.json").write_text(original_meta)
            metrics = {"type": "all", "sales": section(), "rentals": None}
            (root / "metrics.json").write_text(json.dumps(metrics))
            (root / "narrative.json").write_text(json.dumps({"sales": gn.PLACEHOLDER_NARRATIVE_SUB, "rentals": None}))
            argv = ["render_report.py", "--month", "2026-09", "--metrics", str(root / "metrics.json"), "--narrative", str(root / "narrative.json")]
            with patch.object(rr, "REPORTS_DIR", root / "reports"), patch.object(sys, "argv", argv), patch.object(rr, "render_pdf", side_effect=RuntimeError("PDF failed")), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), self.assertRaisesRegex(RuntimeError, "PDF failed"):
                rr.main()
            self.assertEqual((report_dir / "index.html").read_text(), "Original publication")
            self.assertEqual((report_dir / "meta.json").read_text(), original_meta)

    def test_charts_handle_missing_prices_and_escape_city_names(self):
        weeks = [{"week": f"2026-09-{day}", "active_listing_count": 10, "median_price_ngn": price}
                 for day, price in (("07", None), ("14", 100), ("21", None), ("28", 200))]
        svg = rr.generate_trajectory_line_chart(weeks)
        ET.fromstring(svg)
        self.assertNotIn("None", svg)
        self.assertNotIn("nan", svg)
        for week in weeks:
            week["median_price_ngn"] = None
        self.assertNotIn("Median Price (Right)", rr.generate_trajectory_line_chart(weeks))
        ET.fromstring(rr.generate_regional_bar_chart({"A & B <C>": {"median_price_ngn": 100}}))

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
                        narrative[key] = dict(gn.PLACEHOLDER_NARRATIVE_SUB,
                                              inventory_narrative='<script>alert("x")</script>\n\nSecond paragraph',
                                              abuja_narrative=None, other_cities_narrative=None)
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
                self.assertNotIn("Download PDF", html)
                self.assertFalse(json.loads((root / "reports/reports.json").read_text())[0]["has_pdf"])
                self.assertIn(f'href="https://reports.akinmokun.com/{folder}/"', html)
                self.assertTrue('name="description" content="September 2026 Nigeria property market research:' in html)
                meta = json.loads((report_dir / "meta.json").read_text())
                self.assertEqual(meta["issue_number"], 17)
                self.assertEqual(meta["published_date_iso"], "2026-10-01")
                self.assertEqual(meta["num_cities"], 2)
                self.assertEqual(meta["unique_neighbourhoods"], 3)
                self.assertIn('&lt;script&gt;alert', html)
                self.assertIn('<p>Second paragraph</p>', html)
                self.assertNotIn('<script>alert', html)
                self.assertTrue("font-family: 'New Computer Modern'" in html)
                self.assertNotIn("None", html)


if __name__ == "__main__":
    unittest.main()
