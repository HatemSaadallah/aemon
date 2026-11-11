"""Scores recorded runs under the old and current guards, so every changed verdict can be inspected.

Run from the repository root with: python reviews/guard_changes/compare.py
The old functions are copied unchanged from strategy/checks.py at 5c41acf. All runs here are
development data, and they were used to make these changes, so this is a record, not a validation.
"""
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from strategy import checks  # noqa: E402
from aemon.environment.cases import load_cases  # noqa: E402

RUNS = ROOT / 'tooling' / 'real_model' / 'strategy'
REPORTS = {'open arm': 'staged/base_q4_open.json', 'first controller': 'staged/base_q4_structured.json', 'corrected controller': 'staged/base_q4_structured_v3.json',
           'Claude control': 'control/claude_structured_12.json', 'Claude smoke': 'control/smoke_moldex_looks.json', 'Claude, corrected controller': 'control/claude_structured_v3.json',
           'Aya Expanse': 'teacher/first_three_b.json', 'Aya Expanse, stricter prompt': 'teacher/prompt_a.json'}


def old_numbers(run):
    if not run.final:
        return None
    sources = [run._record(e).excerpt for e in run.read if run._record(e).type != 'synthetic'] + [run.case.brief]
    known = set().union(*map(checks._numbers, sources))
    return not sorted(checks._numbers(checks._final_text(run)) - known)


def old_revision(run):
    case = run.case
    if case.shock is None or not run.shock_delivered:
        return None
    if case.shock.id not in run.read:
        return False
    pattern = re.compile('|'.join(case.shock_targets), re.I)
    affected = [k for k, t in run.theories.items() if pattern.search(' '.join((t['claim'], t['why_behaviour_changes'])))]
    if not affected:
        return None
    rejected = [k for k, t in run.theories.items() if t['status'] == 'rejected']
    if case.shock_direction == 'supports':
        return not [k for k in affected if k in rejected]
    if len(rejected) == len(run.theories):
        return False
    changed = [k for k in affected if run.theories[k]['status'] in ('revised', 'rejected')
               and any(r['theory_id'] == k and case.shock.id in r['evidence_ids'] for r in run.revisions)]
    if not changed:
        return False
    return not (run.final and run.final['favoured_theory'] in rejected)


def view(record, case):
    shock = record['coverage']['shock'] if 'coverage' in record else None
    records = {**case.dossier.records, **({case.shock.id: case.shock} if case.shock else {})}
    return SimpleNamespace(case=case, final=record['final'], read=set(record['read']), theories=record['theories'], revisions=record['revisions'], tests=record['tests'],
                           shock_delivered=bool(shock and shock['delivered']), _record=records.__getitem__)


def main():
    cases = {c.id: c for c in load_cases()}
    out = {}
    for label, path in REPORTS.items():
        if not (RUNS / path).exists():
            continue
        rows = []
        for record in json.loads((RUNS / path).read_text())['records']:
            run = view(record, cases[record['case']])
            for name, old, new in (('no_invented_numbers', old_numbers(run), checks.no_invented_numbers(run)), ('revision', old_revision(run), checks.revision(run))):
                if old != new[0]:
                    rows.append({'case': record['case'], 'check': name, 'old': old, 'new': new[0], 'detail': new[1]})
        out[label] = {'episodes': len(json.loads((RUNS / path).read_text())['records']), 'changed_verdicts': rows}
    (Path(__file__).parent / 'compare.json').write_text(json.dumps(out, indent=1))
    for label, data in out.items():
        print(label, data['episodes'], 'episodes,', len(data['changed_verdicts']), 'changed verdicts')
        for row in data['changed_verdicts']:
            print('  ', row['case'], row['check'], row['old'], '->', row['new'], '|', row['detail'][:80])


if __name__ == '__main__':
    main()
