"""Version 3 rows from the DeepSeek V4-Pro investigations (DECISIONS 2026-11-10 22:55, 23:05 and 23:25 UTC). NOTHING TRAINS.

The investigations become rows with the same builder as version 1's (pipeline/rows.py: provenance, replay-exact, an
accepted finish; the compact prompt version 1 was trained under). The six validation companies' DeepSeek rows go to the
validation file only. The action-mix check compares the read_source share with version 1's and refuses (exit 2) a mix
above 1.5 times it.

    PYTHONPATH=src python scripts/oneoff/v3_rows.py --folder experiments/hosted_investigations --base rows/final.jsonl --out rows/v3
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from aemon.rows.build_rows import build  # noqa: E402

VALIDATION = ('diatek', 'illumina', 'perrigo', 'resmed', 'sensirion', 'sievi')  # drawn with random.Random(20261110)
DEVELOPMENT = ('hellberg', 'neumann', 'jotun', 'tanita', 'deere', 'acr')
NAME = re.compile(r'"name":\s*"(\w+)"')


def action(row: dict) -> str:
    found = NAME.search(row['messages'][row['target_index']]['content'])
    return found.group(1) if found else '?'


def shares(rows: list[dict]) -> dict[str, float]:
    count = collections.Counter(action(r) for r in rows)
    return {k: round(v / max(len(rows), 1), 3) for k, v in count.most_common()}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--folder', required=True)
    p.add_argument('--base', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    folder = Path(a.folder)
    reports = []
    for stem in sorted({f.name.split('.')[0] for f in folder.glob('*.episodes.jsonl')}):
        done = folder / f'{stem}.json'
        reports.append(str(done if done.exists() else folder / f'{stem}.episodes.jsonl'))  # a stopped part: its episode log
    manifest = tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False)
    for f in sorted(folder.glob('provenance_*.jsonl')):
        manifest.write(f.read_text())
    manifest.close()
    rows, decisions = build(reports, manifest.name, prompt='compact', compact=True, exclude=())
    rows = [r for r in rows if not r['case'].startswith(DEVELOPMENT)]
    val = [r for r in rows if r['case'].startswith(VALIDATION)]
    train = [r for r in rows if not r['case'].startswith(VALIDATION)]
    base = [json.loads(line) for line in open(a.base)]
    v1, ds = shares(base), shares(train)
    reasons = collections.Counter(d.get('reason', 'accepted')[:80] for d in decisions)
    report = {'reports': len(reports), 'episodes': len(decisions), 'accepted': sum(d['accepted'] for d in decisions),
              'rejections': reasons.most_common(8), 'train_rows': len(train), 'validation_rows': len(val),
              'train_companies': len({r['case'].split('-')[0] for r in train}), 'v1_action_share': v1, 'deepseek_action_share': ds,
              'read_ratio': round(ds.get('read_source', 0) / max(v1.get('read_source', 1e-9), 1e-9), 2)}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Path(f'{out}_report.json').write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    if report['read_ratio'] > 1.5:
        raise SystemExit(2)
    Path(f'{out}_deepseek_train.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in train))
    Path(f'{out}_deepseek_val.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in val))


if __name__ == '__main__':
    main()
