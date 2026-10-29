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

    def test_obsolete_print_overrides_are_removed_without_touching_screen_or_body(self):
        from restyle_published import strip_legacy_print_styles
        original = '<head><style>p { color: green } @media print { @page { size: A4 } .kpi-card { border: 1px solid red !important } } @media screen { p { color: blue } }</style></head><body><p>Published content</p>'
        updated = strip_legacy_print_styles(original)
        self.assertNotIn('!important', updated)
        self.assertIn('@media screen', updated)
        self.assertIn('color: green', updated)
        self.assertEqual(original.split('<body>')[1], updated.split('<body>')[1])

    def test_svg_pdf_compatibility_resolves_presentation_without_changing_labels(self):
        from restyle_published import pdf_compatible_svg
        html = '<p style="color:var(--gold)">Outside chart</p><svg><text style="font-family:var(--font-sans)" fill="var(--text-primary)">₦220.0M</text></svg>'
        updated = pdf_compatible_svg(html)
        self.assertIn('₦220.0M', updated)
        self.assertIn('New Computer Modern', updated)
        self.assertIn('fill="#222c25"', updated)
        self.assertIn('<p style="color:var(--gold)">Outside chart</p>', updated)

    def test_pdf_summary_stays_in_five_columns_and_flows_after_title(self):
        from weasyprint import HTML
        css = (ROOT / 'templates/partials/published-report.css').read_text()
        html = '<html><head><style>' + css + '</style></head><body><div class="page-wrapper"><header class="report-header"><h1>Report</h1></header><div class="market-section" style="page-break-before:always"><h1>Sales</h1><div class="kpi-strip">' + ''.join('<div class="kpi-card" id="metric-'+str(i)+'"><span class="kpi-label">Metric</span><span class="kpi-value">8,026</span></div>' for i in range(5)) + '</div></div></div></body></html>'
        doc = HTML(string=html).render()
        self.assertEqual(len(doc.pages), 1)
        boxes = [box for box in doc.pages[0]._page_box.descendants() if getattr(box, 'element', None) is not None and box.element.get('id', '').startswith('metric-') and type(box).__name__ == 'TableCellBox']
        self.assertEqual(len(boxes), 5)
        self.assertEqual(len({round(box.position_y, 2) for box in boxes}), 1)

    def test_print_stays_light_when_html_theme_is_dark(self):
        from weasyprint import HTML
        css = (ROOT / 'templates/partials/published-report.css').read_text()
        html = '<html data-theme="dark"><head><style>' + css + '</style></head><body><div class="page-wrapper"><p>Published report</p></div></body></html>'
        doc = HTML(string=html).render()
        wrapper = next(box for box in doc.pages[0]._page_box.descendants() if getattr(box, 'element', None) is not None and box.element.get('class') == 'page-wrapper')
        colour = wrapper.style['background_color']
        self.assertAlmostEqual(colour.red, 1)
        self.assertGreater(colour.green, .99)
        self.assertGreater(colour.blue, .97)
