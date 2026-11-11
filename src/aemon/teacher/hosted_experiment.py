"""Experiment answers judged by the reviewer instead of the keyword design screens (DECISIONS 2026-11-10 19:05 UTC).

The keyword screens (targeted.gate_mechanism, gate_test, gate_decline) refused sound designs. One example is a
same-price test of a poppable against a pop-less product, refused as "differs only in wording". So for the experiment
family only, an answer goes to the DeepSeek reviewer if it passes the mechanical checks:
- the call is accepted and grounded (corrections.judge);
- no field is cut off (targeted.cut_off) and none is over its limit (experiment_design.over_limits);
- it stays inside the case's period and currency (targeted.gate_case_bounds), and cites no later source
  (corrective.late_source);
- it proposes when the case warrants a test and declines when it does not (the case's own test_warranted);
- it is from a training case, every reply is in the manifest, and the composition rebuilds (experiment_design.verify).
NO TRAINING here.

    python -m aemon.teacher.hosted_experiment export --asked A.json [B.json] --manifest M.jsonl [N.jsonl] --output reviews/v2_round5/X_experiment_kept_for_review
    python -m aemon.teacher.hosted_experiment rows --asked ... --manifest ... --reviews R.json --output rows.jsonl
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any

from aemon.common.types import Json
from aemon.environment.cases import load_cases
from aemon.teacher import corrections as c
from aemon.teacher import corrective, experiment_design
from aemon.teacher import targeted as t
from aemon.data.splits import is_validation

ROOT = Path(__file__).resolve().parents[3]


def mechanical(item: Json, cases: dict[str, Any]) -> tuple[Json | None, str]:
    state = item['state']
    kept, reason = c.judge({**state, 'record': item['record']}, item['reply'])
    if kept is None:
        return None, reason
    case = cases[state['case']]
    before, _ = c._replay(item['record'], case, len(item['record']['model_turns']))
    call, args = kept['call'], kept['call'].get('arguments') or {}
    if call['name'] not in ('propose_test', 'decline_test'):
        return None, 'not a test decision'
    if call['name'] == 'propose_test' and not case.test_warranted:
        return None, 'more information is not worth a test here, so the right call declines'
    if call['name'] == 'decline_test' and case.test_warranted:
        return None, 'declined a test this case warrants'
    answer = json.loads(item['reply'])
    if experiment_design.over_limits(answer):
        return None, 'over a length limit'
    problem = ((t.cut_off(call, kept.get('justification')) or t.gate_case_bounds(before, args, kept.get('justification')))
               if call['name'] == 'propose_test' else '') or corrective.late_source(before, args)
    return (None, problem) if problem else (kept, 'passed the mechanical checks')


def _latest(paths: list[str]) -> list[Json]:
    """Experiment answers; a later file's answer to the same state (the second shortening) replaces the earlier one."""
    by: dict[tuple[str, int], Json] = {}
    for path in paths:
        for item in json.loads(Path(path).read_text()):
            if item.get('skill') == 'experiment' and 'reply' in item:
                by[(item['state']['student_run'], item['state']['turn'])] = item
    return list(by.values())


def _manifest(paths: list[str]) -> str:
    joined = tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False)
    for path in paths:
        joined.write(Path(path).read_text())
    joined.close()
    return joined.name


def candidates(asked: list[str], manifests: list[str]) -> tuple[list[Json], dict[str, int]]:
    cases = {x.id: x for x in load_cases()}
    frozen = {x.id for x in load_cases(split='heldout')} | {x.id for x in load_cases(split='heldout2')}
    manifest = _manifest(manifests)
    out, counts = [], {}
    for item in _latest(asked):
        cid = item['state']['case']
        kept, reason = mechanical(item, cases)
        if kept is not None and (cid in frozen or cid not in cases or is_validation(cid)):
            kept, reason = None, 'not a training case'
        if kept is not None and not (experiment_design.verify(item, manifest) and c.rows([dict(item, kept=kept)], manifest)):
            kept, reason = None, 'provenance or replay failed'
        counts[reason] = counts.get(reason, 0) + 1
        if kept is not None:
            out.append(dict(item, kept=kept, decision='passed the mechanical checks'))
    return out, counts


def _exporter() -> Any:
    spec = importlib.util.spec_from_file_location('v2_review_export', ROOT / 'scripts' / 'v2_review_export.py')
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def export(asked: list[str], manifests: list[str], output: str) -> None:
    items, counts = candidates(asked, manifests)
    ex = _exporter()
    cases = {x.id: x for x in load_cases()}
    entries = [ex.entry(i + 1, x, cases) for i, x in enumerate(items)]
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    calls: dict[str, int] = {}
    for e in entries:
        calls[e['call']['name']] = calls.get(e['call']['name'], 0) + 1
    data = {'counts': {'answers': sum(counts.values()), 'valid': sum(counts.values()), 'failures': 0, 'kept': len(items),
                       'by_call': ', '.join(f'{n} {k}' for k, n in calls.items()) or 'none',
                       'rejections': sorted(((k, n) for k, n in counts.items() if k != 'passed the mechanical checks'), key=lambda x: -x[1]),
                       'checks': counts, 'gate': 'mechanical checks only (DECISIONS 2026-11-10 19:05 UTC)'},
            'examples': entries}
    out.with_suffix('.json').write_text(json.dumps(data, ensure_ascii=False, indent=1))
    out.with_suffix('.md').write_text(ex.markdown(entries, data['counts']))
    print(json.dumps(data['counts']))


def rows(asked: list[str], manifests: list[str], reviews: list[str], output: str) -> None:
    """Rows for the experiment answers the reviewer kept, rebuilt from the manifest exactly as corrective.rows does,
    with the mechanical checks in place of the keyword screens."""
    approved = {(e['student_run'], e['student_turn']) for r in reviews for e in json.loads(Path(r).read_text())['examples'] if e.get('keep') is True}
    items, _ = candidates(asked, manifests)
    manifest = _manifest(manifests)
    made = []
    for item in items:
        if (item['state']['student_run'], item['state']['turn']) in approved:
            made += [dict(row, source='corrective', skill='experiment') for row in c.rows([item], manifest)]
    Path(output).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in made))
    print(json.dumps({'approved': len(approved), 'rows': len(made)}))


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='step', required=True)
    for name in ('export', 'rows'):
        s = sub.add_parser(name)
        s.add_argument('--asked', nargs='+', required=True)
        s.add_argument('--manifest', nargs='+', required=True)
        s.add_argument('--output', required=True)
        if name == 'rows':
            s.add_argument('--reviews', nargs='+', required=True)
    a = p.parse_args()
    if a.step == 'export':
        export(a.asked, a.manifest, a.output)
    else:
        rows(a.asked, a.manifest, a.reviews, a.output)


if __name__ == '__main__':
    main()
