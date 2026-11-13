"""The final system against the base model, from saved judgments (no new runs, no new judging).

    python scripts/release/final_system_vs_base.py      # writes reports/judge/final_system_vs_base.json

The final system (dig then reason with the loop guards and evidence first, arm D of experiments/grounded/) and the base
model were judged in separate batches by the same two judges (Claude Code and Codex on gpt-6-sol) with the same
instrument (sha256 cca85a72…). Runs are paired by case and attempt; intervals as in the registered report (cases
resampled) and with whole companies resampled.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))
from aemon.evaluation.judging.report import bootstrap, episode_scores, load  # noqa: E402

JUDGES = ('claudecode_predictions.jsonl', 'codexsol_predictions.jsonl')
TESTS = {'final_test': ('experiments/grounded/final', 'reports/judge/system_final'),
         'test_set_2': ('experiments/grounded/test2', 'reports/judge/system_test2')}


def arm_scores(folder: str, arm: str) -> dict[tuple[str, int], list[float]]:
    d = REPO / folder
    key = [json.loads(line) for line in open(d / 'key.jsonl') if line.strip()]
    preds = [load(str(d / j)) for j in JUDGES]
    out = {}
    for k in key:
        if k['arm'] != arm:
            continue
        s = []
        for p in preds:
            x = p.get(k['packet_id'])
            v = episode_scores(x['judgment'])[0] if x and 'judgment' in x else None
            if v is None:
                break
            s.append(v)
        if len(s) == len(JUDGES):
            out[(k['case'], k['attempt'])] = s
    return out


def one(system_folder: str, base_folder: str) -> dict:
    system, base = arm_scores(system_folder, 'D'), arm_scores(base_folder, 'base')
    by_case, by_company, per_judge = defaultdict(list), defaultdict(list), [[] for _ in JUDGES]
    for c in sorted(set(system) & set(base)):
        d = [s - b for s, b in zip(system[c], base[c])]
        by_case[c[0]].append(statistics.mean(d))
        by_company[c[0].split('-')[0]].append(statistics.mean(d))
        for i, x in enumerate(d):
            per_judge[i].append(x)
    pairs = sorted(set(system) & set(base))
    return {'pairs': len(pairs),
            'base_mean_of_judges': round(statistics.mean(statistics.mean(base[c]) for c in pairs), 3),
            'final_system_mean_of_judges': round(statistics.mean(statistics.mean(system[c]) for c in pairs), 3),
            'difference_case_cluster': bootstrap(by_case),
            'difference_company_cluster': bootstrap(by_company),
            'difference_per_judge': {j.split('_')[0]: round(statistics.mean(v), 3) for j, v in zip(JUDGES, per_judge)},
            'companies_higher': f'{sum(statistics.mean(v) > 0 for v in by_company.values())} of {len(by_company)}'}


def main() -> None:
    out = {name: one(*folders) for name, folders in TESTS.items()}
    path = REPO / 'reports/judge/final_system_vs_base.json'
    path.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
