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

    def test_invalid_model_response_does_not_replace_cached_commentary(self):
        import contextlib
        import io
        import json
        import os
        from pathlib import Path
        import sys
        import tempfile
        from unittest.mock import patch
        import generate_narrative as gn
        from narrative_validation import metrics_digest
        metrics=dict(self.metrics, type='all')
        cached=evidence_narrative(metrics)
        cached['_provenance']={'metrics_sha256':metrics_digest(metrics),'mode':'gemini','model':'test'}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/'metrics.json';out=root/'narrative.json'
            source.write_text(json.dumps(metrics));out.write_text(json.dumps(cached))
            before=out.read_bytes()
            invalid=copy.deepcopy(cached)
            invalid['sales']['pricing_narrative']='The price was ₦999999M.'
            args=['generate_narrative.py','--month','2026-09','--metrics',str(source),'--out',str(out),'--force']
            with patch.dict(os.environ,{'GEMINI_API_KEY':'mock-key'}), patch.object(sys,'argv',args), patch.object(gn,'call_gemini',return_value=invalid), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                gn.main()
            self.assertEqual(out.read_bytes(),before)

    def test_valid_model_output_is_saved_with_computed_takeaways_and_reused(self):
        import contextlib
        import io
        import json
        import os
        from pathlib import Path
        import sys
        import tempfile
        from unittest.mock import patch
        import generate_narrative as gn
        metrics=dict(self.metrics, type='all')
        response=evidence_narrative(metrics)
        response['sales']['key_takeaways']=['Model supplied text must be replaced']
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'metrics.json';out=root/'narrative.json'
            source.write_text(json.dumps(metrics))
            args=['generate_narrative.py','--month','2026-09','--metrics',str(source),'--out',str(out)]
            with patch.dict(os.environ,{'GEMINI_API_KEY':'mock-key'}), patch.object(sys,'argv',args), patch.object(gn,'call_gemini',return_value=response) as model, contextlib.redirect_stdout(io.StringIO()):
                gn.main()
                saved=out.read_bytes()
                gn.main()
                self.assertEqual(model.call_count,1)
                self.assertEqual(out.read_bytes(),saved)
            validate_narrative(json.loads(saved),metrics)
            self.assertEqual(json.loads(saved)['_quality_version'],2)


    def test_brand_name_is_not_treated_as_a_statistical_zero(self):
        draft = copy.deepcopy(self.narrative)
        draft['sales']['inventory_narrative'] = 'PS-0 observes the advertised properties in this coverage. '
        draft['sales']['inventory_narrative'] += self.narrative['sales']['inventory_narrative']
        validate_narrative(draft, self.metrics)
