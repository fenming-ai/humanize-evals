"""验证中文案例的原始来源、保护点、分区与重复情况；不替代人工语义评审。"""
import argparse
import collections
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def grams(text):
    text = re.sub(r'\W+', '', text)
    return set(text[i:i + 5] for i in range(len(text) - 4))


def audit(data, root=ROOT, near_duplicates=True):
    if not data:
        raise ValueError('空数据集')
    source_cache, ids, groups, normalized, shingles = {}, set(), {}, set(), []
    for case in data:
        if case['id'] in ids:
            raise ValueError('重复ID')
        ids.add(case['id'])
        if case['review_status'] != 'model_accepted':
            raise ValueError('含尚未通过模型标注验收的案例')
        source = case['provenance']
        path = (root / source['file']).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('来源路径越界')
        if path not in source_cache:
            with path.open(encoding='utf-8-sig') as f:
                source_cache[path] = list(csv.DictReader(f))
        row = source_cache[path][source['csv_record'] - 1]
        text = row['text'].strip()
        if row['id'] != source['id'] or text != case['text'] or sha(text) != source['text_sha256']:
            raise ValueError('来源正文不一致：' + case['id'])
        if not case['checks'] or any(not p['quote'] or p['quote'] not in text or not p['requirement'] for p in case['checks']):
            raise ValueError('保护点引用不成立：' + case['id'])
        if not case['voice_quote'] or case['voice_quote'] not in text:
            raise ValueError('声音证据不成立：' + case['id'])
        if len(case['failure_conditions']) < 2 or not case['allowed_changes'] or not case['audience']:
            raise ValueError('验收条件不足')
        group = case['group_id']
        if group in groups:
            raise ValueError('同源主题重复或跨分区泄漏')
        groups[group] = case['split']
        norm = sha(re.sub(r'\s+', '', text))
        if norm in normalized:
            raise ValueError('精确重复正文')
        normalized.add(norm)
        shingles.append(grams(text))
    similar = []
    if near_duplicates:
        for i in range(len(data)):
            for j in range(i):
                score = len(shingles[i] & shingles[j]) / max(1, len(shingles[i] | shingles[j]))
                if score > .3:
                    similar.append({'a': data[i]['id'], 'b': data[j]['id'], 'jaccard': round(score, 4)})
    return {'cases': len(data), 'categories': dict(collections.Counter(c['category'] for c in data)),
            'splits': dict(collections.Counter(c['split'] for c in data)),
            'source_domains': dict(collections.Counter(c['provenance']['domain'] for c in data)),
            'source_generators': dict(collections.Counter(c['provenance']['generator'] for c in data)),
            'min_characters': min(len(c['text']) for c in data), 'max_characters': max(len(c['text']) for c in data),
            'unique_source_groups': len(groups), 'similar_pairs': similar,
            'review': '模型辅助标注与程序核验；非独立人工金标准，未运行参赛改写排名'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('file')
    args = p.parse_args()
    try:
        cases = [json.loads(s) for s in Path(args.file).read_text().splitlines() if s.strip()]
        result = audit(cases)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1 if result['similar_pairs'] else 0)
    except (ValueError, KeyError, IndexError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
