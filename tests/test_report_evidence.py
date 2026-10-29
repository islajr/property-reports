import unittest
from test_render_report import section
from report_evidence import evidence_for_market, evidence_narrative, pricing_benchmarks
from editorial import build_publication


class EvidenceTests(unittest.TestCase):
    def test_chart_table_and_prompt_share_exact_price_selections(self):
        data = section()
        _, rows = pricing_benchmarks(data)
        chart = build_publication({'sales': data})['sales']
        self.assertEqual(chart['pricing'], rows)
        facts = evidence_for_market(data, 'sales')
        self.assertEqual(sum(key.startswith('pricing.area.') for key in facts), len(rows))
        self.assertTrue(all(row['property_class'] in facts[f'pricing.area.{i}'] for i, row in enumerate(rows)))

    def test_evidence_draft_has_only_populated_markets_and_declares_sources(self):
        result = evidence_narrative({'sales': section(), 'rentals': None})
        self.assertIsNone(result['rentals'])
        self.assertEqual(len(result['sales']['key_takeaways']), 3)
        self.assertIn('inventory.coverage', result['sales']['evidence_refs']['inventory_narrative'])
