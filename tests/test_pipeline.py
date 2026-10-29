import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from test_compute_metrics import snapshots
from report_identity import report_key

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def test_all_periods_and_markets_build_without_colliding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(ROOT / "run.sh", root)
            shutil.copytree(ROOT / "scripts", root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(ROOT / "templates", root / "templates")
            if (ROOT / ".venv/bin/python").exists():
                (root / ".venv").symlink_to(ROOT / ".venv", target_is_directory=True)
            (root / "data").mkdir()
            sales = snapshots()
            rentals = sales.assign(price_type="FOR_RENT", median_price_kobo=10_000)
            pd.concat([sales, rentals]).to_csv(root / "data/neighbourhood_snapshots.csv", index=False)
            env = dict(os.environ, GEMINI_API_KEY="", PYTHONDONTWRITEBYTECODE="1")
            saved_inputs = {}
            for period in ("1mo", "3mo", "6mo", "12mo"):
                for market in ("all", "sale", "rent"):
                    with self.subTest(period=period, market=market):
                        result = subprocess.run(
                            ["bash", str(root / "run.sh"), "--month", "2026-09", "--period", period,
                             "--type", market, "--placeholder", "--no-pdf"],
                            cwd=tmp, env=env, capture_output=True, text=True, timeout=30,
                        )
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        key = report_key("2026-09", period, market)
                        report_dir = root / "reports" / key
                        self.assertTrue((report_dir / "index.html").exists())
                        meta = json.loads((report_dir / "meta.json").read_text())
                        self.assertEqual((meta["period"], meta["type"]), (period, market))
                        for prefix in ("metrics", "narrative"):
                            path = root / "data" / f"{prefix}_{key}.json"
                            self.assertTrue(path.exists())
                            saved_inputs[path] = path.read_bytes()
            self.assertEqual(len(json.loads((root / "reports/reports.json").read_text())), 12)
            self.assertEqual(len(saved_inputs), 24)
            for path, content in saved_inputs.items():
                self.assertEqual(path.read_bytes(), content)
