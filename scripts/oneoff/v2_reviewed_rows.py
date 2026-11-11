"""Training rows from the examples a reviewer marked Keep on the Review page, and nothing else. NOTHING HERE TRAINS.

Each Keep decision names a student run, turn and skill; the matching saved answer is rebuilt into a row only if the
manifest holds its exact reply, today's replay rebuilds the context the teacher saw, and its gate still keeps it
(targeted.rows for the round 3 skills, corrective.rows for the corrective families). Drop and unreviewed are excluded.

    PYTHONPATH=src python scripts/oneoff/v2_reviewed_rows.py --asked A.json [B.json] --reviews R_kept_for_review.json [...] \
        --manifest M.jsonl --output rows.jsonl
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from aemon.teacher import corrective, targeted


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--asked', nargs='+', required=True)
    p.add_argument('--reviews', nargs='+', required=True)
    p.add_argument('--manifest', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    keep, decided = set(), collections.Counter()
    for path in a.reviews:
        for e in json.loads(Path(path).read_text())['examples']:
            decided['keep' if e.get('keep') is True else 'drop' if e.get('keep') is False else 'unreviewed'] += 1
            if e.get('keep') is True:
                keep.add((e['student_run'], e['student_turn'], e['skill']))
    asked = [x for path in a.asked for x in json.loads(Path(path).read_text())]
    mine = [x for x in asked if (x['state']['student_run'], x['state']['turn'], x.get('skill')) in keep]
    made = corrective.rows([x for x in mine if x['skill'] in corrective.FAMILIES], a.manifest, keep)
    made += targeted.rows([x for x in mine if x['skill'] not in corrective.FAMILIES], a.manifest)
    Path(a.output).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in made))
    print(json.dumps({'review_decisions': dict(decided), 'approved': len(keep), 'rows': len(made),
                      'by_skill': dict(collections.Counter(r['skill'] for r in made))}))
    if len(made) != len(keep):
        raise SystemExit(f'{len(keep) - len(made)} approved examples did not rebuild into rows; nothing should train until that is explained')


if __name__ == '__main__':
    main()
