"""The version 2 continuation set: every approved corrective row a fixed number of times, mixed with a seeded sample of
version 1's own rows so the corrective rows are a stated share of supervised target tokens. NOTHING HERE TRAINS.

Why not --extra-rows with 150 steps (docs/V2_CORRECTIVE_PLAN.md section 7): the trainer only caps extra rows, never
repeats them, and 150 steps x 4 rows = 600 presentations drawn from about 3,900 base rows, so each corrective row would
be seen about 0.15 times on average.

Refuses (exit 2) a row from a development, final-test or test-set-2 case, a row without an approval key, and duplicate
targets (same case, context length and target call): the first is kept. The low-priority revise family is capped at
--revise-cap of the corrective rows. Base rows from the six development companies are all kept, for validation only
(train.py separates them by --validation-cases). Contexts and target_index are copied unchanged, so the masking is
exactly version 1's.

    PYTHONPATH=src python scripts/oneoff/v2_training_set.py --corrective approved_rows.jsonl --base rows/final.jsonl \
        --output rows/v2_mix.jsonl [--share 0.2 --corrective-epochs 2 --seed 7]
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
from pathlib import Path

from aemon.environment.cases import load_cases
from aemon.data.splits import is_validation

DEVELOPMENT = ('hellberg', 'neumann', 'jotun', 'tanita', 'deere', 'acr')


def size(row: dict) -> int:
    return len(row['messages'][row['target_index']]['content'])


def sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--corrective', required=True)
    p.add_argument('--base', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--share', type=float, default=0.2)
    p.add_argument('--corrective-epochs', type=int, default=2)
    p.add_argument('--revise-cap', type=float, default=0.1)
    p.add_argument('--seed', type=int, default=7)
    a = p.parse_args()
    frozen = {c.id for c in load_cases(split='heldout')} | {c.id for c in load_cases(split='heldout2')}
    corrective, seen, dropped = [], set(), collections.Counter()
    for row in map(json.loads, open(a.corrective)):
        case = row['case']
        if case in frozen or is_validation(case) or case.startswith(DEVELOPMENT):
            raise SystemExit(f'2: {case} is not a training case; nothing is written')
        key = (case, row['target_index'], row['messages'][row['target_index']]['content'])
        if key in seen:
            dropped['duplicate'] += 1
            continue
        seen.add(key)
        corrective.append(row)
    rng = random.Random(a.seed)
    revise = [r for r in corrective if r.get('skill') == 'revise']
    allowed = int(a.revise_cap * len(corrective))
    if len(revise) > allowed:
        rng.shuffle(revise)
        cut = {id(r) for r in revise[allowed:]}
        dropped['revise over its cap'] = len(cut)
        corrective = [r for r in corrective if id(r) not in cut]
    base = [json.loads(line) for line in open(a.base)]
    held = [r for r in base if r['case'].startswith(DEVELOPMENT)]
    pool = [r for r in base if not r['case'].startswith(DEVELOPMENT)]
    corrective_chars = a.corrective_epochs * sum(map(size, corrective))
    target = corrective_chars * (1 - a.share) / a.share
    rng.shuffle(pool)
    replay, total = [], 0
    for r in pool:
        if total >= target:
            break
        replay.append(r)
        total += size(r)
    mixed = [dict(r, source=r.get('source', 'correction')) for r in corrective for _ in range(a.corrective_epochs)] + replay
    rng.shuffle(mixed)
    Path(a.output).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in mixed + held))
    report = {
        'inputs': {'corrective': a.corrective, 'corrective_sha256': sha(a.corrective), 'base': a.base, 'base_sha256': sha(a.base)},
        'settings': {k: getattr(a, k) for k in ('share', 'corrective_epochs', 'revise_cap', 'seed')},
        'corrective_rows': len(corrective), 'dropped': dict(dropped),
        'by_family': dict(collections.Counter(r.get('skill', '?') for r in corrective)),
        'by_call': dict(collections.Counter(json.loads(r['messages'][r['target_index']]['content'])['name'] for r in corrective)),
        'replayed_base_rows': len(replay), 'validation_rows': len(held),
        'training_presentations': len(mixed),
        'corrective_share_of_target_chars': round(corrective_chars / (corrective_chars + total), 3) if corrective else 0,
        'output_sha256': sha(a.output),
    }
    Path(a.output).with_suffix('.manifest.json').write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
