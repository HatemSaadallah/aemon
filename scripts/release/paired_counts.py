"""Paired counts beside the mean difference: for each pair of runs (same case and attempt), is the first arm better,
worse or tied, on the mean of the two judges; and the same per case (mean over its attempts). Exact two-sided sign
test, ties left out. Uses the judge report's own scoring (aemon.evaluation.judging.report).

Usage: python scripts/release/paired_counts.py --key K --judge NAME=PRED --judge NAME=PRED --compare A,B --output OUT
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from math import comb
from pathlib import Path

from aemon.evaluation.judging.report import episode_scores, load


def sign_test(better: int, worse: int) -> float:
    n = better + worse
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(min(better, worse) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def counts(diffs: list[float]) -> dict:
    better, worse = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
    return {'n': len(diffs), 'better': better, 'worse': worse, 'tied': len(diffs) - better - worse, 'sign_test_p': float(f'{sign_test(better, worse):.3g}')}


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument('--key', required=True)
    a.add_argument('--judge', action='append', required=True)
    a.add_argument('--compare', required=True)
    a.add_argument('--output', required=True)
    args = a.parse_args()
    key = [json.loads(line) for line in Path(args.key).read_text().splitlines() if line.strip()]
    first, second = args.compare.split(',')
    per_judge = []
    for spec in args.judge:
        preds = load(spec.split('=', 1)[1])
        scores = {}
        for i, k in enumerate(key):
            p = preds.get(k['packet_id'])
            if p and 'judgment' in p:
                s, _ = episode_scores(p['judgment'])
                if s is not None:
                    scores[i] = s
        per_judge.append(scores)
    both = set.intersection(*(set(s) for s in per_judge))
    mean = {i: sum(s[i] for s in per_judge) / len(per_judge) for i in both}
    cell = defaultdict(dict)
    for i in mean:
        if key[i]['arm'] in (first, second):
            cell[(key[i]['case'], key[i]['attempt'])][key[i]['arm']] = mean[i]
    runs, by_case = [], defaultdict(list)
    for (case, _), v in cell.items():
        if first in v and second in v:
            runs.append(v[first] - v[second])
            by_case[case].append(v[first] - v[second])
    out = {'compare': f'{first} minus {second}', 'judges': [j.split('=')[0] for j in args.judge],
           'runs': counts(runs), 'cases': counts([sum(v) / len(v) for v in by_case.values()])}
    Path(args.output).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
