import unittest
import subprocess
import tempfile
import sys
import json
from pathlib import Path
import evals

class Selection(unittest.TestCase):
    def test_stratified_independent_groups(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'selection'
            r=subprocess.run([sys.executable,str(evals.ROOT/'tools/select_candidates.py'),'--out',str(out)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            selected=json.loads((out/'selected.json').read_text())
            self.assertEqual(len(selected),500)
            self.assertEqual(len({c['group_id'] for c in selected}),500)
            self.assertEqual(sum(c['split']=='development' for c in selected),300)
            self.assertEqual(sum(c['split']=='holdout' for c in selected),200)
            self.assertEqual(sum(c['category']=='long_form' for c in selected),40)
            self.assertTrue(all(len(c['text'])>=1200 for c in selected if c['category']=='long_form'))
            self.assertTrue(all(c['selection_status']=='candidate' for c in selected))
            again=subprocess.run([sys.executable,str(evals.ROOT/'tools/select_candidates.py'),'--out',str(out)],capture_output=True)
            self.assertNotEqual(again.returncode,0)
