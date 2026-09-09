import collections
import hashlib
import json
import unittest
from pathlib import Path
import evals
from tools.curation_audit import audit


class CuratedRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = evals.rows(evals.ROOT / 'data/curated/zh-v1.jsonl')
        cls.manifest = evals.read(evals.ROOT / 'data/curated/manifest.json')

    def test_frozen_counts_and_split(self):
        self.assertEqual(len(self.data), 500)
        self.assertEqual(collections.Counter(c['split'] for c in self.data), {'development': 300, 'holdout': 200})
        self.assertEqual(dict(collections.Counter(c['category'] for c in self.data)), self.manifest['categories'])
        self.assertEqual(len(evals.rows(evals.ROOT / 'data/benchmark-v1.jsonl')), 588)
        self.assertEqual(len(evals.rows(evals.ROOT / 'data/cases.jsonl')), 94)
        self.assertTrue(all(len(c['text']) >= 1200 for c in self.data if c['category'] == 'long_form'))

    def test_manifest_bytes(self):
        for name, expected in self.manifest['files'].items():
            self.assertEqual(hashlib.sha256((evals.ROOT / name).read_bytes()).hexdigest(), expected, name)

    def test_source_quotes_and_no_leakage(self):
        result = audit(self.data)
        self.assertEqual(result['unique_source_groups'], 500)
        self.assertEqual(result['similar_pairs'], [])

    def test_review_records_support_every_case(self):
        cache = {}
        def load(relative):
            if relative not in cache:
                obj = evals.read(evals.ROOT / 'data/curation' / relative)
                cache[relative] = {r['id']: r for r in obj['cases']}
            return cache[relative]
        for c in self.data:
            ref = c['review_provenance']
            annotation = load('annotations/' + ref['annotation'])[c['id']]
            self.assertTrue(annotation['suitable'], c['id'])
            self.assertEqual(c['checks'], annotation['must_preserve'])
            self.assertEqual(c['voice_quote'], annotation['voice_quote'])
            self.assertTrue(ref['reviews'])
            for path in ref['reviews']:
                self.assertTrue(load(path)[c['id']]['approve'], (c['id'], path))
            self.assertFalse(ref['human_reviewed'])
            if c['category'] == 'punctuation':
                self.assertIn('允许等效标点形式', c['task'])
                self.assertTrue(all(s.startswith('仅当造成实际') for s in c['failure_conditions']))
