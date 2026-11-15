"""Sample the retention-check items: 500 MMLU test questions (every subject, evenly) and 300 ARC-Challenge test
questions, written as one JSONL with a fixed order. Run once; the sample is committed with its sha256 so the check
can be repeated on the same items.

Usage: python scripts/bench/prepare_retention.py --out DIR
"""

import argparse
import hashlib
import json
import random
from pathlib import Path

from datasets import load_dataset

SEED = 7
LETTERS = 'ABCD'


def mmlu(n: int) -> list[dict]:
    rows = load_dataset('cais/mmlu', 'all', split='test')
    by_subject: dict[str, list] = {}
    for r in rows:
        by_subject.setdefault(r['subject'], []).append(r)
    rng = random.Random(SEED)
    subjects = sorted(by_subject)
    out: list[dict] = []
    per = n // len(subjects)
    extra = n - per * len(subjects)
    for i, s in enumerate(subjects):
        pool = by_subject[s][:]
        rng.shuffle(pool)
        k = per + (1 if i < extra else 0)
        for r in pool[:k]:
            out.append({'bench': 'mmlu', 'subject': s, 'question': r['question'], 'choices': r['choices'],
                        'answer': LETTERS[r['answer']]})
    rng.shuffle(out)
    return out


def arc(n: int) -> list[dict]:
    rows = load_dataset('allenai/ai2_arc', 'ARC-Challenge', split='test')
    rng = random.Random(SEED)
    pool = [r for r in rows if len(r['choices']['text']) == 4 and r['answerKey'] in LETTERS]
    rng.shuffle(pool)
    return [{'bench': 'arc_challenge', 'subject': 'science', 'question': r['question'], 'choices': r['choices']['text'],
             'answer': r['answerKey']} for r in pool[:n]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--mmlu', type=int, default=500)
    ap.add_argument('--arc', type=int, default=300)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    items = mmlu(a.mmlu) + arc(a.arc)
    for i, it in enumerate(items):
        it['id'] = i
    path = out / 'retention_items.jsonl'
    path.write_text(''.join(json.dumps(it, ensure_ascii=False) + '\n' for it in items))
    print(len(items), 'items', hashlib.sha256(path.read_bytes()).hexdigest()[:16], path)


if __name__ == '__main__':
    main()
