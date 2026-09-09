import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import evals


class Scores(unittest.TestCase):
    def setUp(self):
        self.key = {'V1': {'language': 'zh', 'arm': 'baseline'}}
        self.doc = {'rubric_version': '1.0.0', 'judge_type': 'human', 'judge_id': 'reviewer-1', 'ratings': [{
            'label': 'V1', 'scores': {d: 4 for d in evals.RUBRIC['weights']},
            'evidence': {d: '测试断言的证据占位，不用于真实评分' for d in evals.RUBRIC['weights']},
            'hard_errors': [], 'hard_error_evidence': ''}]}

    def test_endpoints(self):
        self.assertEqual(evals.aggregate(self.doc, self.key)['results'][0]['score'], '100.00')
        self.doc['ratings'][0]['scores'] = dict.fromkeys(evals.RUBRIC['weights'], 0)
        self.assertEqual(evals.aggregate(self.doc, self.key)['results'][0]['score'], '0.00')

    def test_weight_and_hard_error_separate(self):
        r = self.doc['ratings'][0]
        r['scores']['facts'] = 2
        r['hard_errors'] = ['critical_omission']
        r['hard_error_evidence'] = '输入18行，输出缺失'
        result = evals.aggregate(self.doc, self.key)['results'][0]
        self.assertEqual(result['score'], '90.00')
        self.assertEqual(result['hard_error_rate_pct'], '100.00')

    def test_invalid_grades(self):
        for value in [None, True, -1, 5, 3.5, float('nan')]:
            with self.subTest(value=value):
                self.doc['ratings'][0]['scores']['facts'] = value
                with self.assertRaises(ValueError): evals.aggregate(self.doc, self.key)

    def test_evidence_required(self):
        self.doc['ratings'][0]['evidence']['voice'] = ''
        with self.assertRaises(ValueError): evals.aggregate(self.doc, self.key)

    def test_missing_and_duplicate(self):
        self.doc['ratings'] *= 2
        with self.assertRaises(ValueError): evals.aggregate(self.doc, self.key)
        self.doc['ratings'] = []
        with self.assertRaises(ValueError): evals.aggregate(self.doc, self.key)

    def test_dataset(self):
        data = evals.rows(evals.ROOT / 'data/cases.jsonl')
        evals.validate(data)
        self.assertEqual(len(data), 94)
        for bad in [[], [data[0], data[0]]]:
            with self.assertRaises(ValueError): evals.validate(bad)

    def test_languages_separate(self):
        self.key['V2'] = {'language': 'en', 'arm': 'baseline'}
        second = copy.deepcopy(self.doc['ratings'][0]); second['label'] = 'V2'
        self.doc['ratings'].append(second)
        self.assertEqual(len(evals.aggregate(self.doc, self.key)['results']), 2)


class Pipeline(unittest.TestCase):
    def call(self, *args):
        return subprocess.run([sys.executable, str(evals.ROOT / 'evals.py'), *map(str, args)], capture_output=True, text=True)

    def test_run_blind_score_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t) / 'base.jsonl'; blind = Path(t) / 'blind'
            args = ['run', '--arm', 'baseline', '--model', 'smoke', '--limit', '2', '--repeats', '1', '--out', base, '--command', sys.executable, evals.ROOT / 'tests/echo_adapter.py']
            self.assertEqual(self.call(*args).returncode, 0)
            self.assertNotEqual(self.call(*args).returncode, 0)
            self.assertEqual(self.call('blind', '--out', blind, base).returncode, 0)
            doc = evals.read(blind / 'ratings.json'); doc.update(judge_type='human', judge_id='smoke-reviewer')
            for r in doc['ratings']:
                r['scores'] = dict.fromkeys(evals.RUBRIC['weights'], 3)
                r['evidence'] = dict.fromkeys(evals.RUBRIC['weights'], '离线链路测试，非模型实测')
            (blind / 'ratings.json').write_text(json.dumps(doc))
            result = self.call('score', '--ratings', blind / 'ratings.json', '--key', blind / 'key.json')
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['results'][0]['score'], '75.00')
            packet = evals.read(blind / 'packet.json')
            self.assertNotIn('arm', packet[0]); self.assertNotIn('model_requested', packet[0])

    def test_timeout_invalid_output_and_exit(self):
        for code, timeout in [('import time; time.sleep(2)', '.05'), ('print("invalid")', '2'), ('raise SystemExit(2)', '2')]:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as t:
                out = Path(t) / 'failed.jsonl'
                result = self.call('run', '--arm', 'bad', '--model', 'smoke', '--limit', '1', '--repeats', '1', '--timeout', timeout, '--out', out, '--command', sys.executable, '-c', code)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(evals.rows(out)[0]['status'], 'error')
                self.assertNotEqual(self.call('blind', '--out', Path(t) / 'blind', out).returncode, 0)


if __name__ == '__main__':
    unittest.main()
