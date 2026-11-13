"""Robustness of the two frozen test results, from the saved judgments (no new runs, no new judging).

    python scripts/release/robustness.py      # writes reports/judge/robustness.json

1. Company-clustered intervals. The registered interval resamples cases; cases of one company share the company and its
   question, so they are not independent. Here whole companies are resampled (percentile bootstrap), and a
   cluster-robust t interval with (companies - 1) degrees of freedom is given as well (4 companies on the final test, so
   any interval there is rough).
2. Reached-only comparison. A run's score counts every dimension it never reached as 0, and 25 of 48 base runs on the
   final test stop at the context limit (the base reads the full transcript, the fine-tuned arm the compact state). Here
   each pair is compared only on the dimensions both runs were scored on, per judge, then averaged over the judges.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))
from aemon.evaluation.judging.report import bootstrap, episode_scores, load  # noqa: E402

TESTS = {
    'final_test': ('reports/judge/final', ('claude_predictions.jsonl', 'codex_predictions.jsonl'),
                   'final_test_base_base.json'),
    'test_set_2': ('reports/judge/test2', ('claude_test2/predictions.jsonl', 'codex_predictions.jsonl'),
                   'test2_base_base.json'),
}
T975 = {3: 3.182, 11: 2.201}  # Student t, 97.5th percentile


def cluster_t(groups: dict[str, list[float]]) -> list[float]:
    xs = [x for v in groups.values() for x in v]
    mu, n, g = statistics.mean(xs), len(xs), len(groups)
    se = math.sqrt(sum((sum(v) - len(v) * mu) ** 2 for v in groups.values()) * g / (g - 1)) / n
    return [round(mu, 3), round(mu - T975[g - 1] * se, 3), round(mu + T975[g - 1] * se, 3)]


def one(folder: str, judges: tuple[str, str], base_report: str) -> dict:
    d = REPO / folder
    key = [json.loads(line) for line in open(d / 'key.jsonl') if line.strip()]
    preds = [load(str(d / j)) for j in judges]

    def judged(i: int) -> list[dict] | None:
        out = []
        for p in preds:
            x = p.get(key[i]['packet_id'])
            if not x or 'judgment' not in x:
                return None
            out.append(x['judgment'])
        return out

    cell: dict[tuple, dict[str, int]] = defaultdict(dict)
    for i, k in enumerate(key):
        cell[(k['case'], k['attempt'])][k['arm']] = i
    by_case, by_company, reached, shared = defaultdict(list), defaultdict(list), defaultdict(list), []
    for (case, _), arms in cell.items():
        if 'trained' not in arms or 'base' not in arms:
            continue
        t, b = judged(arms['trained']), judged(arms['base'])
        if not t or not b:
            continue
        scores = [(episode_scores(jt)[0], episode_scores(jb)[0]) for jt, jb in zip(t, b)]
        if any(st is None or sb is None for st, sb in scores):
            continue
        full = [st - sb for st, sb in scores if st is not None and sb is not None]
        by_case[case].append(sum(full) / 2)
        by_company[case.split('-')[0]].append(sum(full) / 2)
        diffs = []
        for jt, jb in zip(t, b):
            st = {n: v['score'] for n, v in jt['dimensions'].items() if v['status'] == 'scored'}
            sb = {n: v['score'] for n, v in jb['dimensions'].items() if v['status'] == 'scored'}
            common = set(st) & set(sb)
            if common:
                diffs.append(statistics.mean(st[n] - sb[n] for n in common))
                shared.append(len(common))
        if len(diffs) == 2:
            reached[case].append(sum(diffs) / 2)
    stops = Counter(r['stop_reason'] for r in json.load(open(d / base_report))['records'])
    return {
        'pairs': sum(map(len, by_case.values())), 'cases': len(by_case), 'companies': len(by_company),
        'registered_case_cluster_bootstrap': bootstrap(by_case),
        'company_cluster_bootstrap': bootstrap(by_company),
        'company_cluster_t': cluster_t(by_company),
        'by_company': {c: round(statistics.mean(v), 3) for c, v in sorted(by_company.items())},
        'reached_only': {'mean_and_95_interval_case_cluster': bootstrap(reached),
                         'mean_and_95_interval_company_cluster': bootstrap({c: [x for k, v in reached.items() if k.split('-')[0] == c for x in v]
                                                                            for c in by_company}),
                         'pairs': sum(map(len, reached.values())),
                         'mean_dimensions_scored_in_both': round(statistics.mean(shared), 2)},
        'base_stop_reasons': dict(stops),
    }


def main() -> None:
    out = {name: one(*args) for name, args in TESTS.items()}
    path = REPO / 'reports/judge/robustness.json'
    path.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
