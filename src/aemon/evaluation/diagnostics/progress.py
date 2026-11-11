"""How far an investigation got, as explicit counts instead of "it got further". NOTHING HERE TRAINS.

For each run: the highest stage completed (left for the next one) in the controller's order, calls, refused calls,
repeated calls (refused as repeats, or an accepted call identical to an earlier one), sources read, and sources used
(read and then cited in an assessment, revision or the finish). These are mechanical progress measures, not quality:
a run can complete every stage with poor theories. Quality comes from the blind judges.

Usage: python -m strategy.progress REPORT.json [REPORT.json ...]
"""

from __future__ import annotations

import json
import sys
from collections import Counter

from aemon.common.types import Json
from aemon.environment.stages import WORKFLOW

ORDER = [w['stage'] for w in WORKFLOW]


def progress(record: Json) -> Json:
    calls = record['calls']
    seen = [c.get('stage') for c in calls if c.get('stage') in ORDER]
    completed = None
    for earlier, later in zip(seen, seen[1:], strict=False):
        if ORDER.index(later) > ORDER.index(earlier):
            completed = earlier if completed is None or ORDER.index(earlier) > ORDER.index(completed) else completed
    if record.get('final') is not None and seen:
        completed = 'conclude'
    signatures, repeated = set(), 0
    for c in calls:
        key = (c['name'], json.dumps(c['arguments'], sort_keys=True))
        refused_repeat = not c['accepted'] and 'already' in str(c.get('result', {}).get('error', ''))
        if refused_repeat or (c['accepted'] and key in signatures):
            repeated += 1
        signatures.add(key)
    read = [c['arguments'].get('id') for c in calls if c['name'] == 'read_source' and c['accepted']]
    cited = set()
    for c in calls:
        if not c['accepted']:
            continue
        args = c['arguments']
        if c['name'] == 'assess_evidence':
            cited.add(args.get('evidence_id'))
        if c['name'] in ('revise_theory', 'finish'):
            cited.update(args.get('evidence_ids') or [])
    return {
        'highest_stage_completed': completed,
        'stage_rank': ORDER.index(completed) + 1 if completed else 0,
        'finished': record.get('final') is not None,
        'calls': len(calls),
        'refused': sum(not c['accepted'] for c in calls),
        'repeated': repeated,
        'sources_read': len(set(read)),
        'sources_used': len(set(read) & cited),
    }


def summarize(records: list[Json]) -> Json:
    rows = [progress(r) for r in records]
    n = max(len(rows), 1)
    return {
        'runs': len(rows),
        'finished': sum(r['finished'] for r in rows),
        'highest_stage_completed': dict(Counter(r['highest_stage_completed'] for r in rows)),
        'median_stage_rank': sorted(r['stage_rank'] for r in rows)[len(rows) // 2] if rows else 0,
        'stages_in_order': ORDER,
        **{f'mean_{k}': round(sum(r[k] for r in rows) / n, 1) for k in ('calls', 'refused', 'repeated', 'sources_read', 'sources_used')},
    }


def main() -> None:
    for path in sys.argv[1:]:
        print(path, json.dumps(summarize(json.load(open(path))['records'])))


if __name__ == '__main__':
    main()
