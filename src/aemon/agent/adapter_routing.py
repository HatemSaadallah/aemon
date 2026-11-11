"""Which LoRA adapter writes each turn, when the server holds several (runner --lora-route).

The route sees only the stage and the count of refusals in a row the loop already keeps, never a judge or the case.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from aemon.agent.backends.llama_client import headers


def lora_route(spec: str, loaded: int = 0) -> Callable[..., list[dict[str, float]]]:
    """'default=0,test=1' applies adapter 0 everywhere except the test stage, which gets adapter 1. 'none' applies none.
    Every loaded adapter is named in each request, so one left over from the turn before is always switched off.
    loaded is how many adapters the server holds, so 'default=none' also switches off adapters the route never names.
    'stuck=1' switches to adapter 1 once the run has stuck_after refusals in a row (default 2), whatever the stage, and
    back to the stage's adapter after the next accepted call: 'default=1,stuck=0' runs version 3 and hands a stuck turn
    to version 1. The route sees only the refusal count the runner already keeps, never a judge or the case."""
    table = dict(part.split('=') for part in spec.split(','))
    if 'default' not in table:
        raise ValueError('a route needs a default')
    after = int(table.pop('stuck_after', 2))
    ids = [int(v) for v in table.values() if v != 'none']
    count = max(loaded, 1 + max(ids) if ids else 0)

    def route(stage: str, errors: int = 0) -> list[dict[str, float]]:
        chosen = table['stuck'] if 'stuck' in table and errors >= after else table.get(stage, table['default'])
        return [{'id': i, 'scale': 1.0 if str(i) == chosen else 0.0} for i in range(count)]

    return route


def loaded_adapters(url: str) -> int:
    """How many LoRA adapters the server holds, 0 if it reports none."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url + '/lora-adapters', headers=headers()), timeout=10) as response:
            return len(json.load(response))
    except (urllib.error.URLError, OSError, ValueError):
        return 0
