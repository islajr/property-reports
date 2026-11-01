"""Exercise the same Git staging used by the publication workflow."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PublicationAssetsTests(unittest.TestCase):
    def test_report_comparisons_are_committed_but_raw_csvs_remain_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(ROOT / '.gitignore', root / '.gitignore')
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            paths = ('reports/2026-10/comparisons.csv', 'reports/2026-10/index.html',
                     'reports/2026-10/source.csv', 'data/neighbourhood_snapshots.csv',
                     'scratch/preview/comparisons.csv')
            for name in paths:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture')
            subprocess.run(['git', '-C', tmp, 'add', 'reports/'], check=True)
            staged = subprocess.check_output(['git', '-C', tmp, 'diff', '--cached', '--name-only'], text=True).splitlines()
            self.assertEqual(set(staged), set(paths[:2]))
            for name in paths[2:]:
                result = subprocess.run(['git', '-C', tmp, 'check-ignore', '-q', name])
                self.assertEqual(result.returncode, 0, name)
