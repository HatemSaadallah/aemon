"""V1 against V1-r (novelty-first search) on the same development runs: the measures of docs/RETRIEVAL_PROPOSAL.md,
written before the results. Read-only replay; the blind judge scores are added by judge_report.

    PYTHONPATH=src python scripts/oneoff/v1r_report.py experiments/verify/ver1_control_adapter.json experiments/verify/v1r_novelty_adapter.json \
        --output experiments/verify/report_v1r.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aemon.agent.experimental import novelty
from aemon.agent.experimental.novelty import ranked
from aemon.environment.dossier import Dossier, words
from aemon.environment.cases import load_cases
from aemon.environment.checks import guards_cleared
from aemon.environment.tools import Investigation
from aemon.evaluation.diagnostics import grounding_v2 as g


def per_run(record: dict, cases: dict, novel: bool = False) -> dict:
    """novel: replay with novelty-first search, as the run was played, so every read it made is accepted again."""
    if novel:
        saved = Dossier.search, Investigation._run_search
        Dossier.search, Investigation._run_search = novelty.search, novelty.run_search
        try:
            return per_run(record, cases)
        finally:
            Dossier.search, Investigation._run_search = saved
    case = cases[record['case']]
    run = Investigation(case, **{k: v for k, v in (record.get('settings') or {}).items() if k != 'recovery'})
    shares = []
    for call in record['calls']:
        result = run.call(call['name'], call['arguments'])
        if bool('error' in result) == bool(call['accepted']):
            raise SystemExit(f"replay diverged at {record['case']} #{record['attempt']}: {call['name']}")
        if call['name'] in ('search_evidence', 'challenge_theory') and 'results' in result:
            order = ranked(case.dossier, call['arguments'].get('query', ''))
            wanted = set(words(call['arguments']['query']))
            score = {i: sum(case.dossier._idf[t] for t in set(case.dossier._terms[i]) & wanted) for i in order}
            top = max(score.values(), default=0) or 1
            shares += [score.get(r['id'], 0) / top for r in result['results']]
    relevant = {i for i, r in case.dossier.records.items() if r.bears_on} | set(case.premise_records or ())
    checks = record['checks']
    verdict = lambda k: (checks.get(k) or {}).get('passed') if (checks.get(k) or {}).get('status') not in ('not reached', 'not applicable') else None  # noqa: E731
    return {
        'finished': bool(run.final),
        'validated': guards_cleared(checks),
        'stop': record['stop_reason'],
        'calls': len(record['calls']),
        'repeat_refusals': sum(1 for c in record['calls'] if not c['accepted'] and c['name'] == 'search_evidence' and c.get('category') == 'repeat'),
        'contradicting_weighing': any(a['direction'] == 'contradicts' for a in run.assessments),
        'disconfirmation': verdict('disconfirmation'),
        'existing_offering': verdict('existing_offering'),
        'numbers_cited': g.numbers_cited(run)[0],
        'follows_evidence': g.follows_evidence(run)[0],
        'surfaced': len(run.surfaced), 'read': len(run.read), 'weighed': len({a['evidence_id'] for a in run.assessments}),
        'relevant_weighed': len({a['evidence_id'] for a in run.assessments} & relevant),
        'hit_shares': shares,
    }


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    passed = lambda k: f"{sum(r[k] is True for r in rows)}/{sum(r[k] is not None for r in rows)}"  # noqa: E731
    shares = [s for r in rows for s in r['hit_shares']]
    return {
        'runs': n, 'finished': sum(r['finished'] for r in rows), 'validated_completion': sum(r['validated'] for r in rows),
        'stopped_repeated_errors': sum(r['stop'] == 'repeated errors' for r in rows),
        'repeat_query_refusals': sum(r['repeat_refusals'] for r in rows),
        'runs_with_contradicting_weighing': sum(r['contradicting_weighing'] for r in rows),
        'disconfirmation (passed/reached)': passed('disconfirmation'), 'existing_offering (passed/reached)': passed('existing_offering'),
        'numbers_cited failures': sum(r['numbers_cited'] is False for r in rows), 'follows_evidence failures': sum(r['follows_evidence'] is False for r in rows),
        'mean calls': round(sum(r['calls'] for r in rows) / n, 1),
        'per run: surfaced / read / weighed / decision-relevant weighed': [round(sum(r[k] for r in rows) / n, 1) for k in ('surfaced', 'read', 'weighed', 'relevant_weighed')],
        'hit relevance: mean share of top score': round(sum(shares) / len(shares), 3) if shares else None,
        'hit relevance: share of hits below half the top score': round(sum(s < 0.5 for s in shares) / len(shares), 3) if shares else None,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('control')
    p.add_argument('treatment')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    cases = {c.id: c for c in load_cases()}
    out = {name: summarise([per_run(r, cases, novel) for r in json.loads(Path(path).read_text())['records']])
           for name, path, novel in (('v1', a.control, False), ('v1_r', a.treatment, True))}
    Path(a.output).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
