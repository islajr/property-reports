import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from test_render_report import section
import live_preview as lp


class LivePreviewTests(unittest.TestCase):
    def test_rejects_regular_pipeline_paths_before_connecting(self):
        for path in (lp.ROOT/'reports', lp.ROOT/'data', lp.ROOT/'templates'):
            with self.subTest(path=path), patch.object(sys,'argv',['live_preview.py','--month','2026-10','--output-root',str(path)]), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                lp.main()

    def test_local_preview_routes_every_input_to_scratch_and_uses_readonly_connection(self):
        import os
        scratch=lp.ROOT/'scratch'
        scratch.mkdir(exist_ok=True)
        data={'type':'all','sales':section(),'rentals':None,'quality':{'included_week_starts':['2026-09-07']}}
        connection=MagicMock()
        cursor=connection.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value=('export time','last observation')
        cursor.description=[('city',)]
        cursor.fetchall.return_value=[('LAGOS',)]
        commands=[]
        def run(command,check):
            commands.append(command)
            if 'compute_metrics.py' in command[1]:
                Path(command[command.index('--out')+1]).write_text(json.dumps(data))
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            output=Path(tmp)/'draft'
            args=['live_preview.py','--month','2026-09','--evidence-only','--output-root',str(output)]
            with patch.dict(os.environ,{'SUPABASE_DB_URL':'test-only','GEMINI_API_KEY':''}), patch.object(sys,'argv',args), patch('psycopg2.connect',return_value=connection) as connect, patch.object(lp.subprocess,'run',side_effect=run), contextlib.redirect_stdout(io.StringIO()):
                lp.main()
            self.assertIn('default_transaction_read_only=on',connect.call_args.kwargs['options'])
            self.assertEqual(len(commands),2)
            self.assertTrue(all('generate_narrative.py' not in command[1] for command in commands))
            self.assertIn('--preview',commands[-1])
            self.assertEqual(Path(commands[-1][commands[-1].index('--research-csv')+1]), output/'_inputs/snapshots.csv')
            self.assertEqual(Path(commands[-1][-1]),output/'site')
            manifest=json.loads((output/'manifest.json').read_text())
            self.assertTrue(manifest['regular_inputs_unchanged'])
            self.assertEqual(manifest['status'],'unpublished-draft')
