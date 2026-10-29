import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from restyle_published import restyle, ROOT


class PublishedPresentationTests(unittest.TestCase):
    def test_restyling_preserves_report_markup_date_and_source(self):
        source = ROOT / 'reports/2026-09'
        original = (source / 'index.html').read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            target = restyle(source, Path(tmp) / '2026-09', pdf=False)
            html = target.read_text()
            self.assertTrue('publication-presentation' in html)
            self.assertTrue('New Computer Modern' in html)
            self.assertTrue('October 1, 2026' in html)
            self.assertTrue('class="app-switcher"' in html)
            self.assertEqual((target.parent / 'meta.json').read_bytes(), (source / 'meta.json').read_bytes())
        self.assertEqual((source / 'index.html').read_bytes(), original)

    def test_presentation_review_rejects_published_archive_destination(self):
        with self.assertRaises(ValueError):
            restyle(ROOT / 'reports/2026-09', ROOT / 'reports/2026-09', pdf=False)
