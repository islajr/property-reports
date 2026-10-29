import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from test_render_report import section
import editorial
import render_report as rr


class EditorialTests(unittest.TestCase):
    def test_all_chart_text_uses_bundled_menlo_without_host_fallback(self):
        import matplotlib.pyplot as plt
        from matplotlib.text import Text
        fig, ax = plt.subplots()
        ax.plot([0, 1], [10, 20])
        ax.set_title('₦ pricing benchmark')
        ax.set_xlabel('Observed week')
        editorial.enforce_chart_font(fig)
        for text in fig.findobj(match=Text):
            self.assertEqual(Path(text.get_fontproperties().get_file()), editorial.chart_font_path())
        plt.close(fig)

    def test_figures_have_accessible_names_and_matching_benchmarks(self):
        data = section()
        result = editorial.build_publication({'sales': data, 'rentals': None})
        self.assertEqual(list(result), ['sales'])
        self.assertEqual(len(result['sales']['pricing']), 2)
        for svg in result['sales']['figures'].values():
            root = ET.fromstring(svg)
            self.assertEqual(root.attrib['role'], 'img')
            self.assertTrue(root.attrib['aria-label'])

    def test_preview_cannot_write_to_publication_archive(self):
        with patch.object(sys, 'argv', ['render_report.py', '--month', '2026-09', '--preview', '--output-root', str(Path(rr.__file__).resolve().parents[1] / 'reports')]), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            rr.main()

    def test_published_issue_cannot_be_rebuilt_in_place(self):
        root = Path(rr.__file__).resolve().parents[1]
        path = root / 'reports/2026-09/index.html'
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        with patch.object(sys, 'argv', ['render_report.py', '--month', '2026-09']), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            rr.main()
        self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_catalogue_has_crawlable_links_and_independent_pdf_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue = root / '2026-09'
            issue.mkdir()
            (issue / 'index.html').write_text('Archived issue')
            (issue / 'report.pdf').write_bytes(b'%PDF-')
            (issue / 'meta.json').write_text(json.dumps({'published_date': 'October 1, 2026', 'num_cities': 10, 'unique_neighbourhoods': 297}))
            with contextlib.redirect_stdout(io.StringIO()):
                rr.regenerate_index(root)
            html = (root / 'index.html').read_text()
            self.assertTrue('href="/2026-09/report.pdf"' in html)
            self.assertTrue('href="/2026-09/"' in html)
            self.assertTrue('application/ld+json' in html)
            self.assertTrue('aria-live="polite"' in html)
            self.assertEqual((issue / 'index.html').read_text(), 'Archived issue')
