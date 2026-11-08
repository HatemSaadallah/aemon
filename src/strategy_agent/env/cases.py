"""Investigation cases, built from the verified dossier. Filled in once the evidence is checked."""

from __future__ import annotations

import json
from typing import Any

from strategy_agent.common.paths import DOSSIER
from strategy_agent.env.dossier import Dossier, Record
from strategy_agent.env.tools import Case


def load_cases(selection: str = 'all', split: str = 'development') -> list[Any]:
    """Development cases by default. Held-out cases load only when asked for by name, for the final test."""
    data = json.loads((DOSSIER / ('cases_heldout.json' if split == 'heldout' else 'cases.json')).read_text())
    records = Dossier.load(DOSSIER / 'evidence.json')
    cases = []
    for item in data['cases']:
        if selection != 'all' and item['id'] not in selection.split(','):
            continue
        shock = item.get('shock')
        record = Record(**{**shock['record'], 'bears_on': ()}) if shock else None
        shared = tuple(item.get('shared_scopes', ['market']))  # the hearing-protection market evidence belongs to the original three only
        visible = Dossier([r for r in records if r.scope in (*shared, item['scope'])])
        cases.append(
            Case(
                item['id'],
                item['company'],
                item['question'],
                item['brief'],
                item['search_budget'],
                item['test_budget'],
                item['max_test_weeks'],
                visible,
                record,
                tuple(shock['targets']) if shock else (),
                shock.get('direction', 'undermines') if shock else 'undermines',
                bool(item.get('simulated')),
                tuple(item.get('premise_records', ())),
                item.get('test_warranted', True),
            )
        )
    return cases
