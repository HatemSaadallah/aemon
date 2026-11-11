"""Where each failed guard of a finished recovery continuation came from: the checkpoint prefix or the continuation.

    PYTHONPATH=src python experiments/recovery/invalid_finishes.py CONFIG [RESULTS.jsonl] > out.json
Reads stage results; trains nothing.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from aemon.agent.backends.llama_client import parse_call

ROOT = Path(__file__).resolve().parent
TOOLS = {'experiment': ('propose_test', 'decline_test'), 'evidence_kinds': ('assess_evidence',), 'evidence_classes': ('assess_evidence', 'add_theory', 'revise_theory'),
         'testable_predictions': ('add_theory', 'revise_theory'), 'existing_offering': ('read_source',), 'tool_use': None}


def calls_of(cp, row):
    before = []
    for t in cp['prefix']:
        call, _ = parse_call(t['text'], True)
        if call:
            before.append({'name': call['name'], 'arguments': call['arguments'], 'accepted': 'error' not in t['tool_result'], 'where': 'prefix'})
    after = [{'name': c['name'], 'arguments': c.get('arguments') or {}, 'accepted': c['accepted'], 'where': 'continuation'} for c in row['record']['calls']]
    return before + after


def origin(check, detail, calls):
    if check == 'no_invented_numbers':
        nums = re.findall(r"'([\d.,]+)'", detail)
        out = {}
        for n in nums:
            hits = [c for c in calls if c['accepted'] and re.search(r'(?<![\d.])' + re.escape(n) + r'(?![\d])', json.dumps(c['arguments']))]
            out[n] = [f"{c['where']}:{c['name']}" for c in hits] or ['not found in calls']
        return out
    names = TOOLS.get(check)
    if not names:
        return None
    hits = [f"{c['where']}:{c['name']}" for c in calls if c['accepted'] and c['name'] in names]
    return hits


def main():
    config = sys.argv[1]
    results = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'stage1_results.jsonl'
    cps = {c['id']: c for c in json.loads((ROOT / 'benchmark_v1.json').read_text())['checkpoints']}
    rows = [json.loads(x) for x in results.read_text().splitlines() if x.strip()]
    report, tally = [], Counter()
    for row in rows:
        if row['config'] != config or not row['finished'] or row['checkpoint'] not in cps:
            continue
        cp, checks = cps[row['checkpoint']], row['record']['checks']
        calls = calls_of(cp, row)
        failures = []
        for k in row['checks_failed']:
            o = origin(k, checks[k]['detail'], calls)
            flat = [x for v in (o.values() if isinstance(o, dict) else (o or [])) for x in (v if isinstance(v, list) else [v])]
            where = 'continuation' if flat and all(x.startswith('continuation') for x in flat) else 'prefix' if flat and all(x.startswith('prefix') for x in flat) else 'both' if flat else 'unlocated'
            tally[(k, where)] += 1
            failures.append({'check': k, 'detail': checks[k]['detail'], 'origin': where, 'calls': o})
        cont = [c['name'] for c in calls if c['where'] == 'continuation' and c['accepted']]
        report.append({'checkpoint': cp['id'], 'case': cp['case'], 'stratum': cp['stratum'], 'turns_left': cp['turns_left'], 'continuation_accepted': cont, 'failures': failures,
                       'test_call': next(({'name': c['name'], 'arguments': c['arguments'], 'where': c['where']} for c in reversed(calls) if c['accepted'] and c['name'] in ('propose_test', 'decline_test')), None)})
    print(json.dumps({'config': config, 'finished': len(report), 'by_check_and_origin': {f'{k} / {w}': n for (k, w), n in sorted(tally.items())}, 'runs': report}, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
