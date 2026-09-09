"""本地改写评测：固定输入、匿名评审、分语言加权汇总。"""
import argparse
import hashlib
import json
import math
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUBRIC = json.loads((ROOT / 'rubric/v1.json').read_text())


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def validate(cases):
    if not cases:
        raise ValueError('案例不能为空')
    seen = set()
    for c in cases:
        if not isinstance(c.get('id'), str) or not c['id'] or c['id'] in seen:
            raise ValueError('案例ID为空或重复')
        seen.add(c['id'])
        for name in ['text', 'task', 'language', 'category', 'source', 'split']:
            if not isinstance(c.get(name), str) or not c[name].strip():
                raise ValueError('案例缺少有效字段：' + name)
        for name in ['must_preserve', 'literal_hints', 'term_hints']:
            if not isinstance(c.get(name), list) or not all(isinstance(x, str) for x in c[name]):
                raise ValueError('无效列表：' + name)
    if sum(RUBRIC['weights'].values()) != 100:
        raise ValueError('权重必须合计100')


def run(args):
    cases = rows(args.cases)
    validate(cases)
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError('limit必须为正数')
        cases = cases[:args.limit]
    if args.repeats < 1 or args.repeats > 100 or not math.isfinite(args.timeout) or args.timeout <= 0:
        raise ValueError('repeats须为1—100，timeout须为正有限数')
    if not args.original and not args.command:
        raise ValueError('需要--command或--original')
    if not args.arm.strip() or not args.model.strip():
        raise ValueError('arm和model不能为空')
    skill = Path(args.skill).read_text() if args.skill else ''
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    with out.open('x') as f:
        for c in cases:
            for repeat in range(1, args.repeats + 1):
                payload = {k: c.get(k, '') for k in ['id', 'text', 'task', 'material', 'voice', 'language']}
                payload['skill'] = skill
                record = {'case_id': c['id'], 'case': c, 'repeat': repeat, 'arm': args.arm,
                          'model_requested': args.model, 'rubric_version': RUBRIC['version'],
                          'skill_sha256': digest(skill.encode()), 'input_sha256': digest(json.dumps(payload, sort_keys=True).encode()),
                          'command': args.command, 'original': args.original}
                start = time.monotonic()
                try:
                    if args.original:
                        result = {'text': c['text']}
                    else:
                        proc = subprocess.run(args.command, input=json.dumps(payload, ensure_ascii=False),
                                              capture_output=True, text=True, timeout=args.timeout, check=True)
                        result = json.loads(proc.stdout)
                    if not isinstance(result, dict) or not isinstance(result.get('text'), str) or not result['text'].strip():
                        raise ValueError('适配器须返回非空text')
                    record.update(status='ok', text=result['text'], usage=result.get('usage'))
                except (subprocess.SubprocessError, OSError, ValueError) as exc:
                    # 不保存stderr或异常正文，避免供应商错误消息带出凭证。
                    record.update(status='error', error=type(exc).__name__)
                    failures += 1
                record['seconds'] = round(time.monotonic() - start, 4)
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                f.flush()
    print(json.dumps({'records': len(cases) * args.repeats, 'failures': failures}))
    return 1 if failures else 0


def blind(args):
    entries = [r for path in args.files for r in rows(path)]
    if not entries or any(r['status'] != 'ok' for r in entries):
        raise ValueError('记录为空或含失败；不可静默丢弃失败记录')
    signatures, seen, cases = {}, set(), {}
    for r in entries:
        token = (r['arm'], r['case_id'], r['repeat'])
        if token in seen:
            raise ValueError('条件/案例/轮次重复')
        seen.add(token)
        signatures.setdefault(r['arm'], set()).add((r['case_id'], r['repeat']))
        if r['rubric_version'] != RUBRIC['version']:
            raise ValueError('评分版本不一致')
        old = cases.setdefault(r['case_id'], r['case'])
        if old != r['case']:
            raise ValueError('同ID案例内容不一致')
    first = next(iter(signatures.values()))
    if any(s != first for s in signatures.values()):
        raise ValueError('各条件的案例和轮次不齐')
    random.Random(args.seed).shuffle(entries)
    packet, key, ratings = [], {}, []
    for i, r in enumerate(entries):
        label = 'V' + str(i + 1).zfill(5)
        key[label] = {k: r[k] for k in ['case_id', 'repeat', 'arm', 'model_requested']}
        key[label]['language'] = r['case']['language']
        case = {k: v for k, v in r['case'].items() if k not in ['source', 'notes']}
        packet.append({'label': label, 'case': case, 'candidate': r['text']})
        ratings.append({'label': label, 'scores': {k: None for k in RUBRIC['weights']},
                        'evidence': {k: '' for k in RUBRIC['weights']}, 'hard_errors': [], 'hard_error_evidence': ''})
    target = Path(args.out)
    target.mkdir(parents=True, exist_ok=False)
    write_new(target / 'packet.json', packet)
    write_new(target / 'key.json', key)
    write_new(target / 'ratings.json', {'rubric_version': RUBRIC['version'], 'judge_type': '', 'judge_id': '', 'ratings': ratings})
    print('匿名记录：' + str(len(packet)) + '；key.json不得交给评审')


def aggregate(document, key):
    if document.get('rubric_version') != RUBRIC['version']:
        raise ValueError('评分版本不一致')
    if document.get('judge_type') not in ['human', 'model'] or not document.get('judge_id', '').strip():
        raise ValueError('须填写评审类型与身份代号')
    if not key or len(document['ratings']) != len(key):
        raise ValueError('评分数量不完整')
    seen, groups = set(), {}
    for r in document['ratings']:
        label = r['label']
        if label not in key or label in seen:
            raise ValueError('评分ID未知或重复')
        seen.add(label)
        scores = r['scores']
        if set(scores) != set(RUBRIC['weights']):
            raise ValueError('评分维度不完整')
        for dim, value in scores.items():
            if type(value) is not int or value not in RUBRIC['scale']:
                raise ValueError('等级须为0—4整数，不接受空值')
            if not isinstance(r.get('evidence', {}).get(dim), str) or not r['evidence'][dim].strip():
                raise ValueError('每维评分必须有证据')
        errors = r.get('hard_errors')
        if not isinstance(errors, list) or any(e not in RUBRIC['hard_errors'] for e in errors):
            raise ValueError('严重错误标签无效')
        if errors and not r.get('hard_error_evidence', '').strip():
            raise ValueError('严重错误必须有证据')
        info = key[label]
        total = sum(RUBRIC['weights'][d] * value / 4 for d, value in scores.items())
        groups.setdefault((info['language'], info['arm']), []).append((total, bool(errors), scores))
    result = []
    for (language, arm), items in sorted(groups.items()):
        totals = [v[0] for v in items]
        result.append({'language': language, 'arm': arm, 'n': len(items),
                       'score': format(statistics.mean(totals), '.2f'),
                       'stddev': format(statistics.stdev(totals) if len(totals) > 1 else 0, '.2f'),
                       'hard_error_rate_pct': format(100 * sum(v[1] for v in items) / len(items), '.2f'),
                       'dimensions': {d: format(statistics.mean(v[2][d] for v in items) * w / 4, '.2f') for d, w in RUBRIC['weights'].items()}})
    return {'rubric_version': RUBRIC['version'], 'judge_type': document['judge_type'], 'results': result,
            'note': '描述性结果，不宣称显著胜出；样本标准差不是置信区间。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('validate')
    p = sub.add_parser('run')
    p.add_argument('--cases', default=str(ROOT / 'data/cases.jsonl'))
    p.add_argument('--arm', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--skill')
    p.add_argument('--out', required=True)
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--limit', type=int)
    p.add_argument('--timeout', type=float, default=120)
    p.add_argument('--original', action='store_true')
    p.add_argument('--command', nargs=argparse.REMAINDER)
    p = sub.add_parser('blind')
    p.add_argument('files', nargs='+')
    p.add_argument('--out', required=True)
    p.add_argument('--seed', type=int, default=20260909)
    p = sub.add_parser('score')
    p.add_argument('--ratings', required=True)
    p.add_argument('--key', required=True)
    args = parser.parse_args()
    try:
        if args.action == 'validate':
            data = rows(ROOT / 'data/cases.jsonl')
            validate(data)
            source = read(ROOT / 'data/upstream/slopkit/source.json')
            assert digest((ROOT / source['path']).read_bytes()) == source['corpus_sha256'], '来源SHA256不匹配'
            assert len(rows(ROOT / source['path'])) == source['total'], '来源数量不匹配'
            print('案例有效：' + str(len(data)) + '；权重100；来源SHA256一致')
        elif args.action == 'run':
            return run(args)
        elif args.action == 'blind':
            blind(args)
        else:
            print(json.dumps(aggregate(read(args.ratings), read(args.key)), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError, AssertionError) as exc:
        print('校验失败：' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
