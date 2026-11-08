"""Rescores recorded runs with the current checks, by replaying their calls through the tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from strategy_agent.agent.runner import summary
from strategy_agent.common.types import Json
from strategy_agent.env.cases import load_cases
from strategy_agent.env.checks import run_checks
from strategy_agent.env.tools import Investigation

if TYPE_CHECKING:
    from strategy_agent.env.tools import Case


def rebuild(record: Json, cases: dict[str, Case]) -> Investigation:
    run = Investigation(cases[record['case']], **record.get('settings', {}))
    for call in record['calls']:
        run.call(call['name'], call['arguments'])
    return run


def main() -> None:
    cases = {c.id: c for c in load_cases()}
    for name in sys.argv[1:]:
        path = Path(name)
        report = json.loads(path.read_text())
        for record in report['records']:
            record['checks'] = run_checks(rebuild(record, cases))
        report['summary'] = summary(report['records'])
        path.write_text(json.dumps(report, indent=1))
        print(path.name, {k: f'{v["passed"]}/{v["reached"]}' for k, v in report['summary']['checks'].items()})


if __name__ == '__main__':
    main()
