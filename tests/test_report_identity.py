import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_identity import report_key


class IdentityTests(unittest.TestCase):
    def test_variants_have_distinct_keys_and_combined_keys_are_preserved(self):
        keys = {report_key("2026-09", period, market) for period in ("1mo", "3mo", "6mo", "12mo") for market in ("all", "sale", "rent")}
        self.assertEqual(len(keys), 12)
        self.assertIn("2026-09", keys)
        self.assertIn("2026-09_3mo", keys)
        self.assertIn("2026-09_3mo_sale", keys)

    def test_invalid_identity_is_rejected(self):
        for month in ("2026-13", "2026-9", "../2026-09"):
            with self.subTest(month=month), self.assertRaises(ValueError):
                report_key(month)
