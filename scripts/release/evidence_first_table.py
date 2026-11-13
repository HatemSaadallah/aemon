"""Numbers for the evidence-first write-up, read from the report files (nothing typed by hand).

    python scripts/release/evidence_first_table.py
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))
from aemon.environment.checks import _numbers  # noqa: E402

SETS = {  # name: (folder, report, control arm, treated arm)
    'Development (45 runs per arm)': ('experiments/grounded/screen2', 'report_both_D_vs_A.json', 'A', 'D'),
    'Test set 2 (72)': ('experiments/grounded/test2', 'report_both_D_vs_default.json', 'default', 'D'),
    'Final test (48)': ('experiments/grounded/final', 'report_both_D_vs_default.json', 'default', 'D'),
}


def dims(folder: Path, control: str, treated: str, dim: str) -> dict:
    key = {json.loads(l)['packet_id']: json.loads(l)['arm'] for l in open(folder / 'key.jsonl')}
    sc = collections.defaultdict(list)
    for j in ('claudecode', 'codexsol'):
        for l in open(folder / f'{j}_predictions.jsonl'):
            p = json.loads(l)
            try:
                d = json.loads(p['response']['text'])['dimensions']
            except Exception:
                continue
            v = d.get(dim, {})
            if v.get('status') == 'scored' and key.get(p['packet_id']) in (control, treated):
                sc[(j, key[p['packet_id']])].append(v['score'])
    return {k: sum(v) / len(v) for k, v in sc.items()}


def unsourced(report: dict) -> tuple[int, int]:
    fail = nowhere = 0
    for r in report['records']:
        c = r['checks'].get('no_invented_numbers', {})
        if c.get('passed') is not False:
            continue
        fail += 1
        tn = _numbers(json.dumps(r.get('tests')))
        nowhere += any(n not in tn for n in re.findall(r"'([^']*)'", c['detail']))
    return fail, nowhere


rows = []
for name, (folder, rep, control, treated) in SETS.items():
    f = REPO / folder
    if not (f / rep).exists():
        print(f'| {name} | not judged yet |')
        continue
    r = json.load(open(f / rep))
    assert not r['missing'], (name, r['missing'])
    m = r['mean_of_judges']
    by, (d, lo, hi) = m['by_arm'], m['difference']['mean_and_95_interval']
    cc = r['judges']['claudecode']['difference']['mean_and_95_interval']
    sol = r['judges']['codexsol']['difference']['mean_and_95_interval']
    ev = dims(f, control, treated, 'evidence_judgement')
    rec = dims(f, control, treated, 'recommendation')
    runs = {a: json.load(open(f / f'{a}.json')) for a in (control, treated)}
    fin = {a: runs[a]['summary']['finished'] for a in runs}
    un = {a: unsourced(runs[a]) for a in runs}
    rows.append((name, by[control], by[treated], d, lo, hi, cc, sol, ev, control, treated, fin, un, m['difference']['by_company']))
    print(f'| {name} | {by[control]:.2f} → {by[treated]:.2f} | **{d:+.2f} [{lo:.2f}, {hi:.2f}]** | {cc[0]:+.2f} [{cc[1]:.2f}, {cc[2]:.2f}] | '
          f'{sol[0]:+.2f} [{sol[1]:.2f}, {sol[2]:.2f}] | {ev[("claudecode", control)]:.2f} → {ev[("claudecode", treated)]:.2f} / '
          f'{ev[("codexsol", control)]:.2f} → {ev[("codexsol", treated)]:.2f} | '
          f'{rec[("claudecode", control)]:.2f} → {rec[("claudecode", treated)]:.2f} / '
          f'{rec[("codexsol", control)]:.2f} → {rec[("codexsol", treated)]:.2f} | {fin[control]} → {fin[treated]} | '
          f'{un[control][1]} → {un[treated][1]} ({un[control][0]} → {un[treated][0]}) |')
    print('   by company', json.dumps(m['difference']['by_company']), 'spearman', r['agreement']['spearman_episode_scores'])
