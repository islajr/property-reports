import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RunnerTests(unittest.TestCase):
    def test_invalid_options_fail_before_pipeline_starts(self):
        cases = [[], ["--unknown"], ["--month"], ["--month", "--export"],
                 ["--month", "2026-13", "--export"],
                 ["--month", "2026-09", "--type", "shortlet", "--export"],
                 ["--month", "2026-09", "--period", "2mo", "--export"],
                 ["--month", "2026-09", "--issue", "0", "--export"]]
        for args in cases:
            with self.subTest(args=args):
                result = subprocess.run(["bash", str(ROOT / "run.sh"), *args], capture_output=True, text=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Step 1", result.stdout)
                self.assertNotIn("Step 2", result.stdout)
        result = subprocess.run(["bash", str(ROOT / "run.sh"), "--help"], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0)
