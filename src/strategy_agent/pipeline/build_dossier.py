"""Builds strategy/dossier/evidence.json from raw research. Only records whose quotes passed
verify_sources get in, so an unverified quote cannot reach an agent.

The researcher's own summary of a record (`claim`) stays in raw/ and never reaches the agent, which
reads only the title and the quoted excerpt. `bears_on` is an analyst label for later study, and
no tool returns it.
"""

from __future__ import annotations

import json
from typing import Any

from strategy_agent.common.paths import DOSSIER as HERE
from strategy_agent.common.types import Json

FINALISTS = {'Moldex-Metric': 'moldex', 'Cotral Lab': 'cotral', 'Hellberg Safety': 'hellberg'}


def key_of(name: str) -> str:
    return next((key for prefix, key in FINALISTS.items() if name.startswith(prefix)), 'market')


def passed(name: str) -> set[Any]:
    results = json.loads((HERE / 'raw' / f'{name}_verification.json').read_text())['results']
    return {r['id'] for r in results if r['status'] == 'verified'}


def entry(record: Json, scope: str, topic: str) -> Json:
    return {
        'id': record['id'],
        'type': record['type'],
        'title': record.get('source_title') or record['id'],
        'url': record['url'],
        'date': str(record.get('source_date', 'unknown')),
        'excerpt': record['excerpt'],
        'access_limitation': record.get('access_limitation', 'none'),
        'topic': topic,
        'scope': scope,
        'bears_on': record.get('bears_on', []),
    }


def main() -> None:
    records, dropped = [], []
    good = passed('candidates')
    for company in json.loads((HERE / 'raw' / 'candidates.json').read_text())['companies']:
        for record in company['records']:
            if record['id'] in good:
                records.append(entry(record, key_of(company['name']), company['name']))
            else:
                dropped.append(record['id'])
    addendum = HERE / 'raw' / 'moldex_addendum.json'
    good = passed('moldex_addendum')
    for record in json.loads(addendum.read_text())['records']:
        if record['id'] in good:
            records.append(entry(record, 'moldex', 'Moldex-Metric products and packaging'))
        else:
            dropped.append(record['id'])
    market = HERE / 'raw' / 'market.json'
    if market.exists():
        good = passed('market')
        for record in json.loads(market.read_text())['records']:
            if record['id'] in good:
                records.append(entry(record, 'market', record.get('topic', '')))
            else:
                dropped.append(record['id'])
    notes = HERE / 'raw' / 'annotations.json'
    if notes.exists():  # the agent sees geography and date, while kind and limits stay evaluator-side
        annotations = json.loads(notes.read_text())['annotations']
        for record in records:
            record.update(annotations.get(record['id'], {}))
    (HERE / 'evidence.json').write_text(
        json.dumps(
            {
                'note': 'Every excerpt was checked against its live source on the access date. Quoted material belongs to its publishers.',
                'accessed': '2026-11-01',
                'records': records,
            },
            indent=1,
            ensure_ascii=False,
        )
    )
    print(json.dumps({'records': len(records), 'dropped': dropped}))


if __name__ == '__main__':
    main()
