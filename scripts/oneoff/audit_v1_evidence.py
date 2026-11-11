"""Mechanical evidence-reliability audit of version 1's teacher training data and of version 1's own runs (2026-11-10).

Read-only: every record is replayed through today's tools; nothing is rescored in place and no frozen result changes.
Frozen-test runs are audited only to characterise limitations (DECISIONS: never to tune or select).

Per investigation, on what the agent actually used (assessments and the finish):
  late_assessed / late_cited   an assessed or cited source dated after the year the case is set in (cases without a
                               year are present-day and cannot have one)
  independent_mislabel         assess_evidence labelled independent_study where the v1 annotation says otherwise
  kind_agrees                  assessments whose kind equals the v1 annotation (the evidence_kinds check's basis)
  company_as_independent       independent_study given to a source whose origin is the company itself
  invented_numbers             the original no_invented_numbers check fails
  numbers_not_cited            a claimed number is in no cited source or the brief (development measure)
  follows_evidence             the favoured theory has a supporting assessment from a cited real source

    PYTHONPATH=src python scripts/oneoff/audit_v1_evidence.py --output reports/v1_audit/mechanical.json
"""

from __future__ import annotations

import argparse
import collections
import json
import os
from pathlib import Path

from aemon.environment.cases import load_cases
from aemon.environment.checks import no_invented_numbers
from aemon.evaluation.diagnostics import grounding_v2 as g
from aemon.evaluation.diagnostics.rescore import rebuild
from aemon.data.splits import is_validation
from aemon.teacher.targeted import YEAR

BACKUP = Path(os.path.expanduser('~/lexsi-backup/cluster'))


def year(case) -> int | None:
    found = YEAR.search(f'{case.question} {case.brief}')
    return int(found.group(1)) if found else None


def late(run, source: str, y: int | None) -> bool:
    date = str(getattr(run._source(source), 'date', '') or '')
    return y is not None and date[:4].isdigit() and int(date[:4]) > y


def audit(record: dict, cases: dict) -> dict:
    case = cases[record['case']]
    settings = {k: v for k, v in (record.get('settings') or {}).items() if k != 'recovery'}
    run = rebuild({**record, 'settings': settings}, cases)
    y = year(case)
    a = run.assessments
    out = collections.Counter(investigations=1, dated_case=int(y is not None), assessments=len(a), finished=int(bool(run.final)))
    for x in a:
        src = run._source(x['evidence_id'])
        out['late_assessed'] += late(run, x['evidence_id'], y)
        if src.kind:
            out['annotated'] += 1
            out['kind_agrees'] += x['evidence_kind'] == src.kind
        if x['evidence_kind'] == 'independent_study':
            out['labelled_independent'] += 1
            out['independent_mislabel'] += bool(src.kind) and src.kind != 'independent_study'
            out['company_as_independent'] += src.type == 'company_claim'
    if run.final:
        cited = [i for i in run.final.get('evidence_ids') or [] if i in run.read]
        out['cited'] += len(cited)
        out['late_cited'] += sum(late(run, i, y) for i in cited)
        out['finish_cites_late'] += any(late(run, i, y) for i in cited)
        out['invented_numbers'] += no_invented_numbers(run)[0] is False
        out['numbers_not_cited'] += g.numbers_cited(run)[0] is False
        out['follows_evidence'] += bool(g.follows_evidence(run)[0])
    return out


def total(records: list[dict], cases: dict) -> dict:
    t = collections.Counter()
    for r in records:
        if r['case'] in cases:
            t.update(audit(r, cases))
    return dict(t)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    a = p.parse_args()
    dev_cases = {c.id: c for c in load_cases()}
    result = {}
    # 1. The teacher investigations that became version 1's rows (rows/final.decisions.json, accepted only)
    decisions = json.loads((BACKUP / 'rows' / 'final.decisions.json').read_text())
    wanted = {(Path(d['report']).name, d['episode']) for d in decisions if d['accepted']}
    teacher = []
    for name in sorted({w[0] for w in wanted}):
        for r in json.loads((BACKUP / 'teacher' / name).read_text())['records']:
            if (name, r['episode']) in wanted:
                teacher.append(r)
    result['teacher_training'] = total([r for r in teacher if not is_validation(r['case'])], dev_cases)
    result['teacher_training']['episodes_matched'] = len(teacher)
    # 2. Version 1 on development (stage 2 as-evaluated arm, 45 runs)
    stage2 = json.loads(Path('experiments/recovery/stage2/rec2b_control_adapter.json').read_text())['records']
    result['v1_development'] = total(stage2, dev_cases)
    # 3. Frozen tests, characterisation only
    for split, path in (('heldout', 'reports/judge/final/final_test_trained_adapter.json'), ('heldout2', 'reports/judge/test2/test2_trained_adapter.json')):
        cases = {c.id: c for c in load_cases(split=split)}
        result[f'v1_{split}_characterisation'] = total(json.loads(Path(path).read_text())['records'], cases)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
