"""The tools as JSON schemas, and the per-turn schema the server is constrained to.

TOOL_SCHEMA lists the ten tools every run has; state_position and decline_test (staged runs) and company_status
(status-check runs) are kept apart, so a run that does not use them is never offered them. Each turn, schema_for
offers only the tools the stage controller has open, narrowed to ids that exist: which tool and what content stay the
model's choice.
"""

from __future__ import annotations

import copy
from collections.abc import Iterable
from typing import TYPE_CHECKING

from aemon.agent import recovery
from aemon.agent.state_view import searches
from aemon.common.types import Json
from aemon.environment.stages import current_stage
from aemon.environment.tools import BELIEFS

if TYPE_CHECKING:
    from aemon.environment.tools import Investigation

_TEXT = {'type': 'string', 'maxLength': 240}
_LONG = {'type': 'string', 'maxLength': 420}
_LIST = {'type': 'array', 'items': _TEXT, 'maxItems': 6}
# Test designs need room: at 240 characters constrained generation cut most decision rules mid-sentence (DECISIONS, 2026-11-08)
_RULE = {'type': 'string', 'maxLength': 900}
_DESIGN = {'type': 'string', 'maxLength': 500}
_IDS = {'type': 'array', 'items': {'type': 'string', 'maxLength': 40}, 'minItems': 1, 'maxItems': 8}


def _tool(name: str, arguments: Json | None = None) -> Json:
    return {
        'type': 'object',
        'additionalProperties': False,
        'required': ['name', 'arguments'],
        'properties': {
            'name': {'const': name},
            'arguments': {'type': 'object', 'additionalProperties': False, 'required': sorted(arguments or {}), 'properties': arguments or {}},
        },
    }


TOOL_SCHEMA = {
    'anyOf': [
        _tool('read_brief'),
        _tool('frame_problem', {'objective': _LONG, 'constraints': _LIST, 'alternatives': _LIST}),
        _tool('search_evidence', {'query': {'type': 'string', 'maxLength': 120}}),
        _tool('challenge_theory', {'theory_id': {'type': 'string', 'maxLength': 4}, 'query': {'type': 'string', 'maxLength': 120}}),
        _tool('read_source', {'id': {'type': 'string', 'maxLength': 40}}),
        _tool(
            'add_theory',
            {'claim': _LONG, 'who_benefits': _TEXT, 'why_behaviour_changes': _TEXT, 'how_value_is_captured': _TEXT, 'assumptions': _LIST, 'predictions': _LIST},
        ),
        _tool(
            'assess_evidence',
            {
                'theory_id': {'type': 'string', 'maxLength': 4},
                'evidence_id': {'type': 'string', 'maxLength': 40},
                'direction': {'enum': ['supports', 'contradicts', 'neutral']},
                'quote': _LONG,
                'evidence_kind': {'enum': ['company_assertion', 'customer_observation', 'independent_study', 'regulation', 'analogy', 'market_fact']},
                'does_not_show': _TEXT,
            },
        ),
        _tool(
            'propose_test',
            {
                'name': _TEXT,
                'theories': {'type': 'array', 'items': {'type': 'string', 'maxLength': 4}, 'maxItems': 5},
                'method': _RULE,
                'sample': _DESIGN,
                'measure': _DESIGN,
                'prediction_by_theory': {'type': 'object', 'additionalProperties': {'type': 'string', 'maxLength': 600}},
                'decision_rule': _RULE,
                'cost_eur': {'type': 'number'},
                'weeks': {'type': 'number'},
            },
        ),
        _tool(
            'revise_theory',
            {
                'theory_id': {'type': 'string', 'maxLength': 4},
                'status': {'enum': ['kept', 'revised', 'rejected']},
                'reason': _LONG,
                'new_claim': _LONG,
                'evidence_ids': _IDS,
            },
        ),
        _tool(
            'finish',
            {
                'recommendation': _LONG,
                'target_customer': _TEXT,
                'value_proposition': _TEXT,
                'favoured_theory': {'type': 'string', 'maxLength': 4},
                'next_action': _TEXT,
                'uncertainty': _TEXT,
                'would_change_if': _LIST,
                'evidence_ids': _IDS,
            },
        ),
    ]
}
POSITION_TOOL = _tool('state_position', {'favoured_theory': {'type': 'string', 'maxLength': 4}, 'recommendation': _LONG, 'beliefs': {'type': 'object'}})
DECLINE_TOOL = _tool('decline_test', {'reason': _LONG})
STATUS_TOOL = _tool('company_status')  # status-check runs only; kept out of TOOL_SCHEMA so other runs see no new tool
_BY_NAME = {tool['properties']['name']['const']: tool for tool in [*TOOL_SCHEMA['anyOf'], POSITION_TOOL, DECLINE_TOOL, STATUS_TOOL]}


def _only(values: Iterable[str]) -> dict[str, list[str]]:
    return {'enum': sorted(values)}


def _narrow(name: str, run: Investigation) -> Json | None:
    """Which ids exist right now, and nothing more. Picking the right one stays the model's job, so a
    simulated result or an unchallenged theory is still offered, and the tool refuses it on the record.
    Returns None when the tool has nothing to act on."""
    tool = copy.deepcopy(_BY_NAME[name])
    fields = tool['properties']['arguments']['properties']
    theories, read = list(run.theories), sorted(run.read)
    # A search the budget would refuse is not offered: both models searched into the budget again and again
    if name == 'search_evidence' and searches(run)['searches_left'] <= 0:
        return None
    if name == 'challenge_theory' and run.case.search_budget - len(run.searches) <= 0:
        return None
    if name == 'read_source':
        unread = [i for i in run.surfaced if i not in run.read]
        stage = current_stage(run).name
        must_read_new = stage in ('evidence', 'challenge_reading')  # rereading cannot meet a minimum
        choices = unread if must_read_new else run.surfaced  # elsewhere rereading stays open and costs no search
        if stage == 'status_reading':
            choices = list(run.status_ids or [])
        elif stage == 'evidence' and getattr(run, 'status_ids', None):  # a status source does not count toward the evidence minimum
            choices = [i for i in choices if i not in run.status_ids]
        choices = recovery.read_choices(run, choices)
        if not choices:
            return None
        fields['id'] = _only(choices)
    if 'theory_id' in fields:
        if not theories:
            return None
        fields['theory_id'] = _only(theories)
    if name == 'assess_evidence':
        if not read:
            return None
        fields['evidence_id'] = _only(read)
    if name == 'revise_theory':
        fields['evidence_ids']['items'] = _only(read)
    if name == 'propose_test':
        fields['theories']['items'] = _only(theories)
    beliefs = {'type': 'object', 'additionalProperties': False, 'required': sorted(theories), 'properties': {k: {'enum': list(BELIEFS)} for k in theories}}
    if name == 'state_position':
        fields['favoured_theory'] = _only(theories)
        fields['beliefs'] = beliefs
    if name == 'finish':
        fields['favoured_theory'] = _only(theories)
        fields['evidence_ids']['items'] = _only(recovery.citable(run, read))
        fields['beliefs'] = beliefs
        if getattr(run, 'status_check', False):  # the company's current position, and how it bears on the recommendation
            fields['company_position'] = copy.deepcopy(_TEXT)
        tool['properties']['arguments']['required'] = sorted(fields)
    return tool


def schema_for(run: Investigation, reasoned: bool = False) -> dict[str, list[Json]]:
    """The server can only produce calls to tools that are open, naming ids that exist. Content stays the model's."""
    tools = [tool for name in current_stage(run).tools if not recovery.withdrawn(run, name) and (tool := _narrow(name, run))]
    if not tools:  # nothing can succeed: offer the stage's tools as they are, and let the tools refuse on the record
        tools = [copy.deepcopy(_BY_NAME[name]) for name in current_stage(run).tools]
    if reasoned:  # first in the object, so the reasoning is written before the call it leads to
        tools = [
            {**t, 'required': ['analysis', *t['required']], 'properties': {'analysis': {'type': 'string', 'maxLength': 400}, **t['properties']}} for t in tools
        ]
    return {'anyOf': tools}
