import subprocess
import sys
import tempfile
import unittest
import json
from pathlib import Path
import evals

class Filters(unittest.TestCase):
    def test_explicit_holdout_and_empty_filter(self):
        with tempfile.TemporaryDirectory() as t:
            data=evals.rows(evals.ROOT/'data/cases.jsonl')[:1]
            data[0]['split']='holdout'
            p=Path(t)/'cases.jsonl';p.write_text(json.dumps(data[0])+'\n')
            base=[sys.executable,str(evals.ROOT/'evals.py'),'run','--cases',str(p),'--arm','original','--model','none','--original','--repeats','1']
            a=subprocess.run(base+['--out',str(Path(t)/'a.jsonl')],capture_output=True)
            self.assertEqual(a.returncode,1)
            a=subprocess.run(base+['--split','holdout','--out',str(Path(t)/'b.jsonl')],capture_output=True)
            self.assertEqual(a.returncode,0)
            self.assertEqual(evals.rows(Path(t)/'b.jsonl')[0]['case']['split'],'holdout')
