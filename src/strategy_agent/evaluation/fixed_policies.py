"""Scripted policies, run through the paired cases as negative controls. No model and no training.

A policy that always answers the same way ignores the evidence, so anything that only rewards it is
measuring nothing. The theories here are filler written to touch appearance and comfort. Only the
response to new evidence varies, and a pass here shows what the guards cannot see.

Usage: python -m strategy.fixed_policies
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from strategy_agent.env.dossier import Record

import json
from typing import TYPE_CHECKING

from strategy_agent.agent.runner import record_of
from strategy_agent.common.paths import RUNS  # noqa: E402
from strategy_agent.common.types import Json
from strategy_agent.env.cases import load_cases
from strategy_agent.env.checks import guards_cleared
from strategy_agent.env.tools import Investigation

if TYPE_CHECKING:
    from strategy_agent.env.tools import Case

OUT = RUNS / 'fixed_policies.json'
POLICIES = {'always_keep': 'kept', 'always_revise': 'revised', 'always_reject': 'rejected'}
FILLER = (
    {
        'claim': 'Appearance decides whether people wear protection, because looks carry stigma',
        'why': 'stigma falls when it looks good',
        'prediction': 'Wear is higher for the styled version than the plain one',
    },
    {
        'claim': 'Comfort decides whether people wear protection, because pain ends use',
        'why': 'discomfort makes people remove it',
        'prediction': 'Removal is lower for the soft version than the standard one',
    },
)
QUERIES = ('earplugs comfort', 'earplugs appearance', 'hearing protection wear')


def theory(item: dict[str, str]) -> Json:
    return {
        'claim': item['claim'],
        'who_benefits': 'wearers',
        'why_behaviour_changes': item['why'],
        'how_value_is_captured': 'a higher price',
        'assumptions': ['the group exists'],
        'predictions': [item['prediction']],
    }


def quote(record: Record) -> str:
    return ' '.join(record.excerpt.split()[:12])


def scripted(case: Case, status: str) -> Investigation:
    run = Investigation(case, staged=True)
    run.call('read_brief', {})
    run.call(
        'frame_problem', {'objective': 'Decide whether to go further', 'constraints': ['Small budget'], 'alternatives': ['Enter', 'Partner', 'Do not enter']}
    )
    for query in QUERIES:
        for hit in run.call('search_evidence', {'query': query}).get('results', [])[:2]:
            run.call('read_source', {'id': hit['id']})
    for item in FILLER:
        run.call('add_theory', theory(item))
    source = sorted(run.read)[0]
    for key in run.theories:
        run.call(
            'assess_evidence',
            {
                'theory_id': key,
                'evidence_id': source,
                'direction': 'neutral',
                'quote': quote(run._source(source)),
                'evidence_kind': 'market_fact',
                'does_not_show': 'It says nothing about what buyers would do',
            },
        )
    for hit in run.call('challenge_theory', {'theory_id': 'T1', 'query': 'earplugs discomfort stopped using'}).get('results', [])[:1]:
        run.call('read_source', {'id': hit['id']})
    run.call(
        'propose_test',
        {
            'name': 'Two-arm trial',
            'theories': ['T1', 'T2'],
            'method': 'Give each group one version',
            'sample': '100 adults',
            'measure': 'Wear over 2 weeks',
            'prediction_by_theory': {'T1': 'Styled version worn most', 'T2': 'Soft version worn most'},
            'decision_rule': 'Pursue a version worn at least 20 percent more',
            'cost_eur': 1000,
            'weeks': 2,
        },
    )
    run.call('state_position', {'favoured_theory': 'T1', 'recommendation': 'Run the trial first', 'beliefs': {k: 'uncertain' for k in run.theories}})
    if case.shock:
        run.call('read_source', {'id': case.shock.id})
        from strategy_agent.env.checks import _affected

        target = (_affected(run) or ['T1'])[0]
        run.call(
            'revise_theory',
            {
                'theory_id': target,
                'status': status,
                'reason': 'This policy answers the same way every time',
                'new_claim': 'A narrower claim' if status == 'revised' else 'none',
                'evidence_ids': [case.shock.id],
            },
        )
    favoured = next((k for k, t in run.theories.items() if t['status'] != 'rejected'), 'T1')
    run.call(
        'finish',
        {
            'recommendation': 'Run the trial before investing',
            'target_customer': 'Adults who wear protection',
            'value_proposition': 'Protection people keep wearing',
            'favoured_theory': favoured,
            'next_action': 'Commission the trial',
            'uncertainty': 'Demand is unknown',
            'would_change_if': ['The trial shows no difference'],
            'evidence_ids': sorted(i for i in run.read if run._source(i).type != 'synthetic')[:2],
            'beliefs': {k: 'uncertain' for k in run.theories},
        },
    )
    return run


def main() -> None:
    import sys
    split = 'heldout' if '--heldout' in sys.argv else 'development'
    rows = {}
    for name, status in POLICIES.items():
        for case in load_cases(split=split):
            if case.shock is None:
                continue
            run = scripted(case, status)
            record = record_of(run)
            cell = rows.setdefault(name, {}).setdefault(case.shock_direction, {'cases': 0, 'revision_passed': 0, 'finished': 0, 'guards_cleared': 0})
            cell['cases'] += 1
            cell['revision_passed'] += record['checks']['revision']['passed'] is True
            cell['finished'] += run.final is not None
            cell['guards_cleared'] += guards_cleared(record['checks'])
    (OUT.with_name('fixed_policies_heldout.json') if split == 'heldout' else OUT).write_text(
        json.dumps({'trained': False, 'note': 'Scripted negative controls, with no model. A pass shows what the guards cannot see.', 'results': rows}, indent=1)
    )
    print(json.dumps(rows, indent=1))


if __name__ == '__main__':
    main()
