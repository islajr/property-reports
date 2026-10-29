import copy
import unittest
from test_render_report import section
from report_evidence import evidence_narrative
from narrative_validation import validate_narrative
from generate_narrative import build_prompt


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.metrics = {'sales': section(), 'rentals': None}
        self.narrative = evidence_narrative(self.metrics)

    def test_evidence_draft_is_valid(self):
        validate_narrative(self.narrative, self.metrics)

    def test_rejects_invented_numbers_unrelated_refs_and_long_text(self):
        for edit in ('number', 'reference', 'length', 'takeaway', 'topic'):
            draft = copy.deepcopy(self.narrative)
            block = draft['sales']
            if edit == 'number': block['inventory_narrative'] += ' Inventory reached 999999.'
            if edit == 'reference': block['evidence_refs']['pricing_narrative'] = ['inventory.peak']
            if edit == 'length': block['pricing_narrative'] = 'observed ' * 81
            if edit == 'takeaway': block['key_takeaways'][0] = 'Invented claim'
            if edit == 'topic': block['inventory_narrative'] += ' Interest rates caused this.'
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                validate_narrative(draft, self.metrics)

    def test_rejects_repeated_sentences(self):
        draft = copy.deepcopy(self.narrative)
        sentence = 'These observations have limited coverage of advertised properties.'
        draft['sales']['inventory_narrative'] = sentence
        draft['sales']['pricing_narrative'] = sentence
        with self.assertRaisesRegex(ValueError, 'repeated'):
            validate_narrative(draft, self.metrics)

    def test_prompt_contains_selected_facts_and_omits_unused_dom_data(self):
        prompt = build_prompt(self.metrics)
        self.assertIn('pricing.area.0', prompt)
        self.assertNotIn('avg_days_on_market', prompt)
        self.assertNotIn('executive_summary (', prompt)
