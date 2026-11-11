"""V1 against V1 + verification on the same development runs (docs/VERIFY_EVAL_PLAN.md): every measure of the plan,
per arm and paired by case and attempt. Read-only; the reports are replayed, not changed.

    PYTHONPATH=src python scripts/oneoff/verify_report.py experiments/verify/ver1_control_adapter.json experiments/verify/ver1_verify_adapter.json \
        --output experiments/verify/report.json
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from aemon.agent.experimental import verify
from aemon.environment.cases import load_cases
from aemon.environment.checks import guards_cleared
from aemon.evaluation.diagnostics import grounding_v2 as g
from aemon.evaluation.diagnostics.rescore import rebuild

ORIGINAL = ('no_invented_numbers', 'evidence_kinds', 'experiment')


def verdict(check: dict | None) -> bool | None:
    if not isinstance(check, dict) or check.get('status') in ('not reached', 'not applicable'):
        return None
    return check.get('passed')


def per_run(record: dict, cases: dict) -> dict:
    run = rebuild(record, cases)
    final = run.final or {}
    reviews = [t['tool_result'] for t in record['model_turns'] if isinstance(t.get('tool_result'), dict) and 'verification' in t['tool_result']]
    dev = {k: f(run)[0] for k, f in g.MEASURES.items()}
    late = bool(final) and any(f['kind'] == 'late' for f in verify.findings(run, final))
    abstained = bool(final) and str(final.get('recommendation', '')).strip().startswith(verify.ABSTAIN)
    return {
        'key': (record['case'], record['attempt']),
        'finished': bool(final),
        'abstained': abstained,
        'validated': guards_cleared(record['checks']),
        'stop': record['stop_reason'],
        'calls': len(record['calls']),
        'reviews': len(reviews),
        'review_kinds': [k for r in reviews for k in r.get('verification_kinds', [])],
        'remaining_after_review': [f['kind'] for f in verify.findings(run, final)] if final and reviews else None,
        'late_cited': late,
        'unsupported': bool(final) and not abstained and (dev['follows_evidence'] is False or dev['numbers_cited'] is False or late),
        **{k: verdict(record['checks'].get(k)) for k in ORIGINAL},
        **dev,
    }


def arm(path: str, cases: dict) -> list[dict]:
    return [per_run(r, cases) for r in json.loads(Path(path).read_text())['records']]


def count(rows: list[dict], key: str, value=True) -> str:
    reached = [r for r in rows if r[key] is not None]
    return f'{sum(r[key] is value for r in reached)}/{len(reached)}'


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('control')
    p.add_argument('treatment')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    cases = {c.id: c for c in load_cases()}
    arms = {'v1': arm(a.control, cases), 'v1_verify': arm(a.treatment, cases)}
    out = {}
    for name, rows in arms.items():
        out[name] = {
            'runs': len(rows),
            'finished': sum(r['finished'] for r in rows),
            'abstained': sum(r['abstained'] for r in rows),
            'validated_completion': sum(r['validated'] for r in rows),
            'unsupported_recommendations': sum(r['unsupported'] for r in rows),
            'finishes_citing_late_source': sum(r['late_cited'] for r in rows),
            'stopped_repeated_errors': sum(r['stop'] == 'repeated errors' for r in rows),
            'mean_calls': round(sum(r['calls'] for r in rows) / len(rows), 1),
            'verification_reviews': sum(r['reviews'] for r in rows),
            'review_findings': dict(collections.Counter(k for r in rows for k in r['review_kinds'])),
            'findings_remaining_after_review': dict(collections.Counter(k for r in rows for k in (r['remaining_after_review'] or []))),
            **{f'{k} (failures/reached)': count(rows, k, False) for k in (*ORIGINAL, *g.MEASURES)},
        }
    by = {name: {r['key']: r for r in rows} for name, rows in arms.items()}
    same = sum(by['v1'][k]['calls'] == by['v1_verify'][k]['calls'] and by['v1'][k]['finished'] == by['v1_verify'][k]['finished'] for k in by['v1'] if k in by['v1_verify'])
    out['paired'] = {
        'pairs': len(set(by['v1']) & set(by['v1_verify'])),
        'same_length_and_outcome': same,
        'finished_only_v1': sorted(f'{c}#{t}' for (c, t) in by['v1'] if by['v1'][(c, t)]['finished'] and not by['v1_verify'][(c, t)]['finished']),
        'finished_only_verify': sorted(f'{c}#{t}' for (c, t) in by['v1'] if by['v1_verify'][(c, t)]['finished'] and not by['v1'][(c, t)]['finished']),
        'abstentions': [{'run': f'{r["key"][0]}#{r["key"][1]}', 'findings': r['review_kinds']} for r in arms['v1_verify'] if r['abstained']],
    }
    Path(a.output).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
