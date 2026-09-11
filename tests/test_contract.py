import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import evals


class Contract(unittest.TestCase):
    def test_visible_requirements_and_private_hints(self):
        case = {'id': 'c', 'text': '原文', 'must_preserve': ['否定条件'], 'literal_hints': ['私有提示']}
        payload = evals.generation_payload(case, '', 'explicit')
        self.assertEqual(payload['must_preserve'], ['否定条件'])
        self.assertNotIn('literal_hints', payload)
        self.assertNotIn('must_preserve', evals.generation_payload(case, '', 'legacy'))
        case['must_preserve'] = []
        self.assertEqual(evals.generation_payload(case, '', 'explicit')['must_preserve'], [])

    def test_actual_adapter_receives_contract_and_run_records_model(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / 'out.jsonl'
            code = 'import json,sys; p=json.load(sys.stdin); assert "must_preserve" in p; print(json.dumps({"text":p["text"]}))'
            result = subprocess.run([sys.executable, str(evals.ROOT / 'evals.py'), 'run', '--arm', 'a', '--model', 'gpt-6-astra', '--reasoning-effort', 'medium', '--limit', '1', '--repeats', '1', '--out', str(out), '--command', sys.executable, '-c', code], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            r = evals.rows(out)[0]
            self.assertEqual(r['reasoning_effort_requested'], 'medium')
            self.assertEqual(r['contract_mode'], 'explicit')
            self.assertEqual(r['model_requested'], 'gpt-6-astra')

    def test_blind_rejects_mixed_visibility(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'records.jsonl'
            case = evals.rows(evals.ROOT / 'data/cases.jsonl')[0]
            records = [dict(status='ok', arm=arm, case_id=case['id'], repeat=1, case=case, rubric_version=evals.RUBRIC['version'], model_requested='smoke', text=case['text'], contract_mode=mode) for arm, mode in [('a','explicit'),('b','legacy')]]
            path.write_text(''.join(json.dumps(r)+'\n' for r in records))
            with self.assertRaisesRegex(ValueError, '可见'):
                evals.blind(argparse.Namespace(files=[path], seed=1, out=Path(t)/'blind'))

    def test_legacy_judge_hints_are_not_user_instructions(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'records.jsonl'
            case = evals.rows(evals.ROOT / 'data/cases.jsonl')[0]
            r = dict(status='ok', arm='a', case_id=case['id'], repeat=1, case=case, rubric_version=evals.RUBRIC['version'], model_requested='smoke', text=case['text'])
            path.write_text(json.dumps(r)+'\n')
            evals.blind(argparse.Namespace(files=[path], seed=1, out=Path(t)/'blind'))
            p = evals.read(Path(t)/'blind/packet.json')[0]
            self.assertNotIn('must_preserve', p['case'])
            self.assertEqual(p['review_reference']['must_preserve'], case['must_preserve'])
            self.assertEqual(p['requirements_visibility'], 'judge_only')
