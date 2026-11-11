"""Stage 1 report for the recovery experiment: paired effects against A, company-cluster bootstrap, strata, regressions.

    python -m aemon.evaluation.diagnostics.recovery_report --manifest experiments/recovery/benchmark_v1.json \
        --results experiments/recovery/stage1_results.jsonl --out experiments/recovery/stage1_report.json
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

METRICS = ('advanced', 'finished', 'validated')
SEED, B = 20261109, 4000


def boot(diffs: dict[str, list[float]]) -> tuple[float, float, float]:
    """Mean paired difference over checkpoints, and a 95% interval resampling companies."""
    groups = list(diffs.values())
    flat = [d for g in groups for d in g]
    rng = random.Random(SEED)
    stats = []
    for _ in range(B):
        pick = [groups[rng.randrange(len(groups))] for _ in groups]
        sample = [d for g in pick for d in g]
        stats.append(mean(sample) if sample else 0.0)
    stats.sort()
    return mean(flat), stats[int(0.025 * B)], stats[int(0.975 * B) - 1]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', required=True)
    p.add_argument('--results', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    cps = {c['id']: c for c in json.loads(Path(args.manifest).read_text())['checkpoints']}
    rows = [json.loads(x) for x in Path(args.results).read_text().splitlines() if x.strip()]
    by = defaultdict(dict)
    for r in rows:
        r['validated'] = bool(r['finished'] and r['guards_cleared'])
        by[r['checkpoint']][r['config']] = r
    configs = sorted({r['config'] for r in rows})
    report = {'n_results': len(rows), 'configs': {}, 'paired_vs_A': {}, 'by_stratum': {}, 'regressions': {}, 'exploratory_development': {}}
    for group, keep in (('primary', lambda c: not c['stratum'].startswith('exploratory')), ('exploratory_development', lambda c: c['stratum'].startswith('exploratory'))):
        ids = [i for i in by if i in cps and keep(cps[i])]
        table = {}
        for cfg in configs:
            got = [by[i][cfg] for i in ids if cfg in by[i]]
            if not got:
                continue
            table[cfg] = {
                'n': len(got), **{m: sum(r[m] for r in got) for m in METRICS},
                'mean_calls': round(mean(r['calls'] for r in got), 1), 'mean_progress_calls': round(mean(r['progress_calls'] for r in got), 2),
                'refused': sum(r['refused'] for r in got), 'rereads': sum(r['rereads'] for r in got),
                'synthetic_citation_refusals': sum(r['synthetic_citation_refusals'] for r in got),
                'mean_seconds': round(mean(r['seconds'] for r in got), 1), 'mean_prompt_tokens': round(mean(r['prompt_tokens'] for r in got)),
                'efficiency': round(sum(r['progress_calls'] for r in got) / max(1, sum(r['calls'] for r in got)), 3),
            }
        if group == 'primary':
            report['configs'] = table
            for cfg in configs:
                if cfg == 'A':
                    continue
                pair = [i for i in ids if 'A' in by[i] and cfg in by[i]]
                out = {'n_pairs': len(pair)}
                for m in METRICS:
                    diffs = defaultdict(list)
                    for i in pair:
                        diffs[cps[i]['company']].append(float(by[i][cfg][m]) - float(by[i]['A'][m]))
                    if diffs:
                        d, lo, hi = boot(diffs)
                        out[m] = {'diff': round(d, 3), 'ci95': [round(lo, 3), round(hi, 3)],
                                  'better': sum(1 for i in pair if by[i][cfg][m] and not by[i]['A'][m]),
                                  'worse': sum(1 for i in pair if by[i]['A'][m] and not by[i][cfg][m])}
                report['paired_vs_A'][cfg] = out
                report['regressions'][cfg] = [{'checkpoint': i, 'stratum': cps[i]['stratum'], 'A': by[i]['A']['stop_reason'], cfg: by[i][cfg]['stop_reason']}
                                              for i in pair if by[i]['A']['advanced'] and not by[i][cfg]['advanced']]
            for stratum in sorted({cps[i]['stratum'] for i in ids}):
                sids = [i for i in ids if cps[i]['stratum'] == stratum]
                report['by_stratum'][stratum] = {cfg: f"{sum(by[i][cfg]['advanced'] for i in sids if cfg in by[i])}/{sum(cfg in by[i] for i in sids)}" for cfg in configs}
        else:
            report['exploratory_development'] = table
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report[k] for k in ('configs', 'paired_vs_A', 'by_stratum')}, indent=1))


if __name__ == '__main__':
    main()
