import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_render_report import section
import generate_narrative as gn
from narrative_validation import metrics_digest, validate_narrative


class NarrativeTests(unittest.TestCase):
    def test_rejects_missing_fields_and_stale_metrics(self):
        metrics = {"sales": section(), "rentals": None}
        with self.assertRaises(ValueError):
            validate_narrative({"sales": {"executive_summary": "Only one field"}}, metrics)
        narrative = {"sales": gn.PLACEHOLDER_NARRATIVE_SUB.copy(), "rentals": None,
                     "_provenance": {"metrics_sha256": metrics_digest(metrics)}}
        validate_narrative(narrative, metrics)
        metrics["sales"]["overall"]["total_new_listings"] += 1
        with self.assertRaisesRegex(ValueError, "changed"):
            validate_narrative(narrative, metrics)

    def test_explicit_placeholder_cache_and_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metrics_path, narrative_path = root / "metrics.json", root / "narrative.json"
            metrics = {"type": "all", "sales": section(), "rentals": None}
            metrics_path.write_text(json.dumps(metrics))
            argv = ["generate_narrative.py", "--month", "2026-09", "--metrics", str(metrics_path), "--out", str(narrative_path)]
            with patch.dict(os.environ, {"GEMINI_API_KEY": ""}), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with patch.object(sys, "argv", argv), self.assertRaises(SystemExit):
                    gn.main()
                self.assertFalse(narrative_path.exists())
                with patch.object(sys, "argv", argv + ["--placeholder"]):
                    gn.main()
                    before = narrative_path.read_bytes()
                    gn.main()
                self.assertEqual(before, narrative_path.read_bytes())
                metrics["sales"]["overall"]["total_new_listings"] += 1
                metrics_path.write_text(json.dumps(metrics))
                with patch.object(sys, "argv", argv + ["--placeholder"]), self.assertRaises(SystemExit):
                    gn.main()
                self.assertEqual(before, narrative_path.read_bytes())
                with patch.object(sys, "argv", argv + ["--placeholder", "--force"]):
                    gn.main()
                self.assertNotEqual(before, narrative_path.read_bytes())
                with patch.object(sys, "argv", argv), self.assertRaises(SystemExit):
                    gn.main()
