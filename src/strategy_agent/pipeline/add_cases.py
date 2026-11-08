"""Adds new companies to the dossier from verified research folders. NOTHING HERE TRAINS.

Only records the verifier marked `verified` get in, under the company's own scope, so one company
never sees another's evidence. Training companies go into cases.json. Held-out companies go into
cases_heldout.json, which development runs never load, so they stay unseen until the final test.
Each new company also gets an irrelevant-evidence variant, so revision is practised on new ground.

Usage: python -m strategy.add_cases --split training FOLDER ...
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from strategy_agent.common.constants.pipeline import ANNOTATIONS, CASE_KEYS  # noqa: F401
from strategy_agent.common.paths import DOSSIER as HERE
from strategy_agent.pipeline.build_dossier import entry

IRRELEVANT = {
    'id': 'SYN-D',
    'type': 'synthetic',
    'title': 'Simulated warehouse test',
    'url': 'n/a',
    'date': 'n/a',
    'excerpt': 'SIMULATED RESULT, NOT REAL DATA. In this simulated warehouse test, a new label printer reduced packing errors slightly. Nothing about wearers or buyers was measured.',
    'access_limitation': 'synthetic',
}


def load_folder(folder: str | Path) -> tuple[list[Any], Any, list[Any]]:
    folder = Path(folder)
    raw = json.loads((folder / 'raw.json').read_text())
    verified = {r['id'] for r in json.loads((folder / 'raw_verification.json').read_text())['results'] if r['status'] == 'verified'}
    cases = json.loads((folder / 'cases.json').read_text())['cases']
    scopes = {c['scope'] for c in cases}
    records, dropped = [], []
    for company in raw['companies']:
        scope = company.get('slug')
        if scope not in scopes:
            raise SystemExit(f'{folder}: company slug {scope} matches no case scope {sorted(scopes)}')
        for record in company['records']:
            if record['id'] not in verified:
                dropped.append(record['id'])
                continue
            made = entry(record, scope, company['name'])
            made.update({k: record[k] for k in ANNOTATIONS if k in record})
            records.append(made)
    return records, cases, dropped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=('training', 'heldout'), required=True)
    parser.add_argument('folders', nargs='+')
    args = parser.parse_args()
    evidence = json.loads((HERE / 'evidence.json').read_text())
    target = HERE / ('cases.json' if args.split == 'training' else 'cases_heldout.json')
    existing = (
        json.loads(target.read_text()) if target.exists() else {'note': 'Held out for the final test. Development runs never load this file.', 'cases': []}
    )
    known_ids = {r['id'] for r in evidence['records']}
    known_cases = {c['id'] for c in existing['cases']}
    added_records, added_cases, dropped = 0, [], []
    for folder in args.folders:
        records, cases, lost = load_folder(folder)
        dropped += lost
        clash = [r['id'] for r in records if r['id'] in known_ids]
        if clash:
            raise SystemExit(f'{folder}: evidence ids already in the dossier: {clash[:5]}')
        evidence['records'] += records
        known_ids |= {r['id'] for r in records}
        added_records += len(records)
        for case in cases:
            if case['id'] in known_cases:
                raise SystemExit(f'case {case["id"]} already exists')
            base = {k: case[k] for k in CASE_KEYS if k in case}
            base['split'] = args.split
            base['shared_scopes'] = []  # sees only its own evidence
            variant = dict(
                base, id=base['id'].rsplit('-base', 1)[0] + '-new-evidence-irrelevant', shock={'record': IRRELEVANT, 'targets': [], 'direction': 'irrelevant'}
            )
            existing['cases'] += [base, variant]
            added_cases += [base['id'], variant['id']]
    (HERE / 'evidence.json').write_text(json.dumps(evidence, indent=1, ensure_ascii=False))
    target.write_text(json.dumps(existing, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'records_added': added_records, 'cases_added': added_cases, 'unverified_dropped': len(dropped)}))


if __name__ == '__main__':
    main()
