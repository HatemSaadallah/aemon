"""Judge scores per arm, company and judge, from blinded packets and their key. NOTHING HERE TRAINS.

For each run and judge, a dimension scored 0 to 3 counts as given, not_reached counts as 0 (the investigation never got
there) and not_applicable is left out; the episode score is the mean over the rest. Each judge is reported separately,
then their mean, with how well they agree. The difference between two arms is paired by case and attempt, with a 95%
interval from resampling whole cases (the case-cluster bootstrap of FINAL_EVAL_PLAN). A missing or invalid judgment is
listed, never filled in. Mechanical progress measures come from progress.py, not from here.

Usage: python -m strategy_agent.evaluation.judge_report --key key.jsonl --judge claude=results/claude/predictions.jsonl
           [--judge codex=...] [--compare trained,base] --output report.json
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

from strategy_agent.common.types import Json


def episode_scores(judgment: Json) -> tuple[float | None, dict[str, float]]:
    dims: dict[str, float] = {}
    for name, d in judgment['dimensions'].items():
        if d['status'] == 'scored':
            dims[name] = float(d['score'])
        elif d['status'] == 'not_reached':
            dims[name] = 0.0
    return (statistics.mean(dims.values()) if dims else None), dims


def load(path: str) -> dict[str, Json]:
    out = {}
    for line in Path(path).read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            out[r['packet_id']] = r
    return out


def bootstrap(pairs: dict[str, list[float]], reps: int = 4000, seed: int = 20261106) -> tuple[float, float, float] | None:
    """Mean paired difference with a 95% interval, resampling cases (each case keeps all its attempts)."""
    cases = [c for c, v in pairs.items() if v]
    if not cases:
        return None
    mean = statistics.mean(x for c in cases for x in pairs[c])
    rng, draws = random.Random(seed), []
    for _ in range(reps):
        sample = [x for c in (rng.choice(cases) for _ in cases) for x in pairs[c]]
        draws.append(statistics.mean(sample))
    draws.sort()
    return round(mean, 3), round(draws[int(0.025 * reps)], 3), round(draws[int(0.975 * reps) - 1], 3)


def spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) < 3:
        return None

    def ranks(v: list[float]) -> list[float]:
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r

    ra, rb = ranks(a), ranks(b)
    if statistics.pstdev(ra) == 0 or statistics.pstdev(rb) == 0:
        return None
    return round(statistics.correlation(ra, rb), 3)


def report(key_path: str, judges: dict[str, str], compare: tuple[str, str] | None) -> Json:
    key = [json.loads(line) for line in Path(key_path).read_text().splitlines() if line.strip()]
    out: Json = {'runs': len(key), 'arms': sorted({k['arm'] for k in key}), 'judges': {}, 'missing': []}
    per_judge_scores: dict[str, dict[int, float]] = {}
    for judge, path in judges.items():
        predictions = load(path)
        scores: dict[int, float] = {}
        by_arm: dict[str, list[float]] = defaultdict(list)
        by_arm_company: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        by_arm_dim: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for i, k in enumerate(key):
            p = predictions.get(k['packet_id'])
            if not p or 'judgment' not in p:
                out['missing'].append({'judge': judge, 'packet_id': k['packet_id'], 'arm': k['arm'], 'case': k['case'], 'error': (p or {}).get('error')})
                continue
            score, dims = episode_scores(p['judgment'])
            if score is None:
                continue
            scores[i] = score
            by_arm[k['arm']].append(score)
            by_arm_company[k['arm']][k['company']].append(score)
            for d, v in dims.items():
                by_arm_dim[k['arm']][d].append(v)
        per_judge_scores[judge] = scores
        entry: Json = {
            'by_arm': {a: {'mean': round(statistics.mean(v), 3), 'n': len(v)} for a, v in by_arm.items()},
            'by_arm_company': {a: {c: round(statistics.mean(v), 3) for c, v in sorted(cs.items())} for a, cs in by_arm_company.items()},
            'by_arm_dimension': {a: {d: round(statistics.mean(v), 3) for d, v in sorted(ds.items())} for a, ds in by_arm_dim.items()},
        }
        if compare:
            entry['difference'] = _difference(key, scores, compare)
        out['judges'][judge] = entry
    if len(per_judge_scores) == 2:
        (a, sa), (b, sb) = per_judge_scores.items()
        both = sorted(set(sa) & set(sb))
        out['agreement'] = {
            'judges': [a, b],
            'episodes_scored_by_both': len(both),
            'spearman_episode_scores': spearman([sa[i] for i in both], [sb[i] for i in both]),
            'mean_absolute_difference': round(statistics.mean(abs(sa[i] - sb[i]) for i in both), 3) if both else None,
        }
        mean_scores = {i: (sa[i] + sb[i]) / 2 for i in both}
        out['mean_of_judges'] = {
            'by_arm': {
                arm: round(statistics.mean(mean_scores[i] for i in both if key[i]['arm'] == arm), 3)
                for arm in out['arms']
                if any(key[i]['arm'] == arm for i in both)
            }
        }
        if compare:
            out['mean_of_judges']['difference'] = _difference(key, mean_scores, compare)
    return out


def _difference(key: list[Json], scores: dict[int, float], compare: tuple[str, str]) -> Json:
    """First arm minus second, paired by case and attempt; unpaired runs are counted and left out."""
    first, second = compare
    cell: dict[tuple[str, object], dict[str, float]] = defaultdict(dict)
    for i, k in enumerate(key):
        if i in scores and k['arm'] in compare:
            cell[(k['case'], k['attempt'])][k['arm']] = scores[i]
    pairs: dict[str, list[float]] = defaultdict(list)
    unpaired = 0
    for (case, _), v in cell.items():
        if first in v and second in v:
            pairs[case].append(v[first] - v[second])
        else:
            unpaired += 1
    b = bootstrap(pairs)
    by_company: dict[str, list[float]] = defaultdict(list)
    for case, v in pairs.items():
        by_company[case.split('-')[0]].extend(v)
    return {
        'arms': f'{first} minus {second}',
        'pairs': sum(len(v) for v in pairs.values()),
        'cases': len(pairs),
        'unpaired_runs': unpaired,
        'mean_and_95_interval': b,
        'by_company': {c: round(statistics.mean(v), 3) for c, v in sorted(by_company.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--key', required=True)
    parser.add_argument('--judge', action='append', required=True, help='NAME=path to predictions.jsonl')
    parser.add_argument('--compare', help='FIRST,SECOND: arms whose paired difference is reported')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    judges = dict(j.split('=', 1) for j in args.judge)
    compare = tuple(args.compare.split(',', 1)) if args.compare else None
    result = report(args.key, judges, compare)  # type: ignore[arg-type]
    Path(args.output).write_text(json.dumps(result, indent=1))
    print(json.dumps({k: result[k] for k in ('runs', 'arms')} | {'missing': len(result['missing'])}))


if __name__ == '__main__':
    main()
