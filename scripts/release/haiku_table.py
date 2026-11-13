"""The Claude Haiku 5.5 baseline (DECISIONS 2026-11-13), from its saved runs and blind judgments.

    python scripts/release/haiku_table.py      # writes experiments/haiku/summary.json

Per test set: how the runs ended, calls, refusals and cost (from the merged runner reports, which include the
episodes rerun after Anthropic API errors), the three registered comparisons (from experiments/haiku/*/report_both_*),
and the mean score per rubric dimension, final system against Haiku (mean of both judges; an unreached dimension 0).
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))
from aemon.evaluation.judging.report import load  # noqa: E402

H = REPO / 'experiments/haiku'


def runs(path: Path) -> dict:
    records = json.loads(path.read_text())['records']
    calls = sum(len(r['calls']) for r in records)
    refused = sum(sum(v for v in r['rejections'].values() if isinstance(v, int)) for r in records)
    finished = sum(r['stop_reason'] == 'finished' for r in records)
    usd = sum(sum(t.get('usd', 0) for t in r['model_turns']) for r in records)
    seconds = sum(sum(t.get('seconds', 0) for t in r['model_turns']) for r in records)
    return {'runs': len(records), 'finished': finished, 'calls_per_run': round(calls / len(records), 1),
            'calls_per_finished': round(calls / finished), 'refused_share': round(refused / calls, 3),
            'usd_per_investigation': round(usd / len(records), 4), 'seconds_per_investigation': round(seconds / len(records))}


def dimensions(name: str) -> dict:
    key = [json.loads(line) for line in open(H / name / 'key.jsonl')]
    preds = [load(str(H / name / f'{j}_predictions.jsonl')) for j in ('claudecode', 'codexsol')]
    out: dict = defaultdict(lambda: defaultdict(list))
    for k in key:
        for p in preds:
            x = p.get(k['packet_id'])
            if x and 'judgment' in x:
                for d, v in x['judgment']['dimensions'].items():
                    out[d][k['arm']].append(v['score'] if v['status'] == 'scored' else 0)
    return {d: {arm: round(statistics.mean(v), 2) for arm, v in arms.items()} for d, arms in out.items()}


def main() -> None:
    summary = {}
    for name in ('final', 'test2'):
        comparisons = {}
        for c in ('final_system_vs_haiku', 'v1_vs_haiku', 'haiku_vs_base'):
            m = json.loads((H / name / f'report_both_{c}.json').read_text())
            comparisons[c] = {'by_arm': m['mean_of_judges']['by_arm'], 'difference': m['mean_of_judges']['difference'],
                              'per_judge': {j: v['difference']['mean_and_95_interval'] for j, v in m['judges'].items()},
                              'missing_judgments': len(m['missing']), 'agreement': m['agreement']}
        summary[name] = {'haiku_runs': runs(H / f'{name}_merged.json'), 'comparisons': comparisons, 'dimensions': dimensions(name)}
    (H / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({n: {'runs': s['haiku_runs'], 'final_system_vs_haiku': s['comparisons']['final_system_vs_haiku']['difference']['mean_and_95_interval']} for n, s in summary.items()}, indent=1))


if __name__ == '__main__':
    main()
