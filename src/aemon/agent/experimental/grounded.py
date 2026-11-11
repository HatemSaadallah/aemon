"""V1.1 candidate, experimental: an evidence-consistent position and finish, by constrained decoding (2026-11-10,
docs/V1_1_PLAN.md).

In 10 of version 1's 24 finished development runs, the favoured theory had no supporting weighing while another
theory had one, and 21 of 24 finishes cited a source never weighed. Advice does not change this, because V1 ignored the
verification layer's findings. So here the choice itself is narrowed: wherever the agent's own record supports at least
one theory, state_position and finish offer only those theories as the favoured one, and finish offers only real
sources it weighed as citations. The texts stay the model's own.
- state_position writes the favoured theory before its recommendation text, so the text follows the constrained choice.
- If nothing is supported, or nothing was weighed, the choice is left as it is.

The evaluated runner (aemon.agent.run_investigations) is not changed: this process replaces tool_schemas._narrow with a
wrapper and runs run_investigations.main.

    python -m aemon.agent.experimental.grounded [the runner's arguments]  # development split only
"""

from __future__ import annotations

import sys
from typing import Any

from aemon.agent import run_investigations, tool_schemas
from aemon.common.types import Json

VERSION = 'grounded-v1'
_NARROW = tool_schemas._narrow


def supported(run: Any) -> list[str]:
    return sorted({a['theory_id'] for a in run.assessments if a['direction'] == 'supports' and a['theory_id'] in run.theories})


def weighed(run: Any) -> list[str]:
    return sorted({a['evidence_id'] for a in run.assessments if a['evidence_id'] in run.read and run._source(a['evidence_id']).type != 'synthetic'})


def narrow(name: str, run: Any) -> Json | None:
    tool = _NARROW(name, run)
    if tool is None or name not in ('state_position', 'finish'):
        return tool
    fields = tool['properties']['arguments']['properties']
    theories = supported(run)
    if theories:
        fields['favoured_theory'] = {'enum': theories}
    if name == 'finish':
        sources = weighed(run)
        allowed = set(fields['evidence_ids']['items'].get('enum') or sources)
        if sources and set(sources) & allowed:
            fields['evidence_ids']['items'] = {'enum': sorted(set(sources) & allowed)}
    return tool


def main() -> None:
    if '--split' in sys.argv and sys.argv[sys.argv.index('--split') + 1] != 'development':
        raise SystemExit('V1.1 is experimental: development split only until it passes its evaluation')
    tool_schemas._narrow = narrow  # this process only
    run_investigations.main()


if __name__ == '__main__':
    main()
