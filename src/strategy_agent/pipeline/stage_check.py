"""A gate between teacher stages: stop the job early instead of spending hours on a broken setup.

Usage: python -m strategy.stage_check REPORT.json MANIFEST.jsonl
Exits non-zero, with the reasons, if the stage should not be followed by another.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from typing import TYPE_CHECKING

from strategy_agent.common.types import Json
from strategy_agent.pipeline.rows import build

if TYPE_CHECKING:
    from pathlib import Path


def check(report_path: str | Path, manifest: str | Path) -> Json:
    report = json.load(open(report_path))
    records = report['records']
    finished = [r for r in records if r['final'] is not None]
    stops = Counter(r['stop_reason'] for r in records)
    rows, decisions = build([report_path], manifest)
    refused = [d for d in decisions if not d['accepted'] and d['reason'] != 'replay did not reach an accepted finish']
    problems = []
    if report['harness_errors']:
        problems.append(f'{len(report["harness_errors"])} harness errors')
    if not records:
        problems.append('no episodes')
    elif len(finished) < len(records) / 2:
        problems.append(f'only {len(finished)} of {len(records)} finished')
    if stops.get('context limit', 0) * 2 > max(len(records), 1):  # more than half: a few long investigations are data, not a broken setup
        problems.append(f'{stops["context limit"]} context-limit stops')
    if refused:
        problems.append(f'{len(refused)} finished episodes refused as rows: {refused[0]["reason"]}')
    return {
        'episodes': len(records),
        'finished': len(finished),
        'stops': dict(stops),
        'rows': len(rows),
        'mean_calls': round(sum(len(r['calls']) for r in records) / max(len(records), 1), 1),
        'problems': problems,
    }


def main() -> None:
    result = check(sys.argv[1], sys.argv[2])
    print(json.dumps(result), flush=True)
    if result['problems']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
