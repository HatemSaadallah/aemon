"""The final-test freeze. NOTHING HERE TRAINS.

The held-out companies are fixed before more teacher data is made, and the digest below covers their
cases and every evidence record in their scopes. tests/test_strategy.py fails if either changes, if a
development case can see their evidence, or if a development company shares a name with one of them.
Changing the final test therefore needs a deliberate new freeze, recorded in docs/DECISIONS.md.

Usage: python -m strategy.freeze   prints the current digest
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from strategy_agent.common.paths import DOSSIER as HERE
from strategy_agent.common.paths import FREEZE as FROZEN  # noqa: F401  where the digest is kept, read by the frozen-test check
from strategy_agent.common.types import Json


def held_out() -> tuple[Any, list[Any], list[Any | Any]]:
    cases = json.loads((HERE / 'cases_heldout.json').read_text())['cases']
    scopes = sorted({c['scope'] for c in cases})
    evidence = json.loads((HERE / 'evidence.json').read_text())
    records = evidence['records'] if isinstance(evidence, dict) else evidence
    return cases, scopes, sorted((r for r in records if r['scope'] in scopes), key=lambda r: r['id'])


def digest() -> Json:
    cases, scopes, records = held_out()
    blob = json.dumps({'cases': sorted(cases, key=lambda c: c['id']), 'records': records}, sort_keys=True, ensure_ascii=False)
    return {
        'digest': hashlib.sha256(blob.encode()).hexdigest(),
        'companies': sorted({c['company'] for c in cases}),
        'scopes': scopes,
        'cases': sorted(c['id'] for c in cases),
        'records': len(records),
    }


if __name__ == '__main__':
    print(json.dumps(digest(), indent=1, ensure_ascii=False))
