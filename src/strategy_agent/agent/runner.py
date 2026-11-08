"""Whole investigations on the real model. NO TRAINING. Case content is labelled by class.

Assumes llama-server on --url. Each episode is written to disk before the next starts.

Usage: python -m strategy.run --prompt strong --cases all --output PATH
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import json
import os
import subprocess
import threading
import traceback
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from strategy_agent.agent.claude_backend import MODEL as CLAUDE_MODEL
from strategy_agent.agent.claude_backend import Claude
from strategy_agent.common.constants.prompts import (  # noqa: F401
    ASSISTED_SEARCHES,
    COMPACT,
    COMPACT_NOTE,
    FORMAT,
    PLAIN,
    PROMPTS,
    REASON_FIRST,
    REASONED,
    STAGED,
    STRONG,
    STRUCTURED,
    TEACHER,
)
from strategy_agent.common.model_client import chat, headers, parse_call
from strategy_agent.common.types import Json, Message, Respond, Schema
from strategy_agent.env.cases import load_cases
from strategy_agent.env.checks import coverage, guards_cleared, rejected_categories, run_checks
from strategy_agent.env.stages import MIN_THEORIES, current_stage
from strategy_agent.env.tools import BELIEFS, Investigation
from strategy_agent.pipeline.provenance import PROVENANCE, record_provenance

if TYPE_CHECKING:
    from strategy_agent.env.tools import Case

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
_BY_NAME = {tool['properties']['name']['const']: tool for tool in [*TOOL_SCHEMA['anyOf'], POSITION_TOOL, DECLINE_TOOL]}


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
        must_read_new = current_stage(run).name in ('evidence', 'challenge_reading')  # rereading cannot meet a minimum
        choices = unread if must_read_new else run.surfaced  # elsewhere rereading stays open and costs no search
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
        fields['evidence_ids']['items'] = _only(read)
        fields['beliefs'] = beliefs
        tool['properties']['arguments']['required'] = sorted(fields)
    return tool


def schema_for(run: Investigation, reasoned: bool = False) -> dict[str, list[Json]]:
    """The server can only produce calls to tools that are open, naming ids that exist. Content stays the model's."""
    tools = [tool for name in current_stage(run).tools if (tool := _narrow(name, run))]
    if not tools:  # nothing can succeed: offer the stage's tools as they are, and let the tools refuse on the record
        tools = [copy.deepcopy(_BY_NAME[name]) for name in current_stage(run).tools]
    if reasoned:  # first in the object, so the reasoning is written before the call it leads to
        tools = [
            {**t, 'required': ['analysis', *t['required']], 'properties': {'analysis': {'type': 'string', 'maxLength': 400}, **t['properties']}} for t in tools
        ]
    return {'anyOf': tools}


SOURCES_NOTE = 'Each excerpt in sources_read is everything the dossier holds for that source: reading it again returns the same text.'


def state_of(run: Investigation, last_result: Json) -> str:
    """The whole investigation as it stands. Mechanical: it copies what is on record and interprets nothing."""
    case = run.case
    sources = [{'id': i, 'class': run._source(i).type, 'title': run._source(i).title, 'excerpt': run._source(i).excerpt} for i in sorted(run.read)]
    # Reads are listed too: a reread looked like progress to the student and the teacher alike (2026-11-05, DECISIONS)
    tried = [
        {'tool': c['name'], 'arguments': c['arguments']}
        for c in run.calls
        if not c['accepted'] or c['name'] in ('search_evidence', 'challenge_theory', 'read_source')
    ][-12:]
    state = {
        'question': case.question,
        'budgets': {**searches(run), 'test_budget_eur': case.test_budget, 'max_test_weeks': case.max_test_weeks},
        'frame': run.frame,
        'unread_results': sorted(i for i in run.surfaced if i not in run.read),
        'sources_read': sources,
        'sources_note': SOURCES_NOTE,
        # Everything a later step may need to justify itself is kept in full, so a conclusion never rests on reasoning it cannot see.
        'theories': {k: {f: v for f, v in t.items() if f != 'first_claim'} for k, t in run.theories.items()},
        'assessed': [{f: a[f] for f in ('theory_id', 'evidence_id', 'direction', 'quote', 'evidence_kind', 'does_not_show')} for a in run.assessments],
        'challenged': [s['theory_id'] for s in run.challenge_searches],
        'tests': run.tests,
        'test_declined': run.test_declined,
        'position': run.position,
        'revisions': run.revisions,
        'already_tried': tried,
    }
    if run.calls and not run.calls[-1]['accepted']:  # otherwise the context after a refusal is the one before it, and the call repeats
        state['your_last_call_was_refused'] = {'tool': run.calls[-1]['name'], 'arguments': run.calls[-1]['arguments']}
    if not case.brief or run.brief_read:
        state['brief'] = case.brief
    return 'Current state: ' + json.dumps(state) + '\nLatest tool result: ' + json.dumps(last_result)


def next_step(run: Investigation) -> str:
    """Workflow guidance in each tool result. It names the step, never the answer."""
    if run.frame is None:
        return 'Next: read_brief if you have not, then frame_problem.'
    unread = [i for i in run.surfaced if i not in run.read]
    if len(run.read) < 3 and unread:
        return f'Next: read_source. Unread results: {sorted(unread)[:3]}'
    if len(run.read) < 3:
        return 'Next: search_evidence for something specific and different.'
    if len(run.theories) < MIN_THEORIES:
        return 'Next: add_theory, with a different causal explanation.'
    unassessed = [k for k in run.theories if not any(a['theory_id'] == k for a in run.assessments)]
    if unassessed:
        return f'Next: assess_evidence for {unassessed[0]}, quoting exact words from a source you read.'
    if not run.challenge_searches:
        return 'Next: challenge_theory, to look for evidence that could prove your favoured theory wrong.'
    if not run.tests:
        return 'Next: propose_test.'
    shock = run.case.shock
    if run.shock_delivered and shock is not None and shock.id not in run.read:
        return f'Next: read_source {shock.id}.'
    if run.shock_delivered and shock is not None and not any(shock.id in r['evidence_ids'] for r in run.revisions):
        return 'You have new evidence. Decide what it means for each theory.'
    return 'Next: finish, or investigate further if you still need to.'


def searches(run: Investigation) -> dict[str, int]:
    """Searches the model may still spend on evidence, with the one held back for challenge_theory counted apart.
    The raw tool result counts the held-back search too, which led teacher and student to search into a refusal."""
    left = max(run.case.search_budget - len(run.searches), 0)
    held = 1 if left and not run.challenge_searches else 0
    return {'searches_left': left - held, 'kept_for_challenge': held}


def lora_route(spec: str, loaded: int = 0) -> Callable[[str], list[dict[str, float]]]:
    """'default=0,test=1' applies adapter 0 everywhere except the test stage, which gets adapter 1. 'none' applies none.
    Every loaded adapter is named in each request, so one left over from the turn before is always switched off.
    loaded is how many adapters the server holds, so 'default=none' also switches off adapters the route never names."""
    table = dict(part.split('=') for part in spec.split(','))
    if 'default' not in table:
        raise ValueError('a route needs a default')
    ids = [int(v) for v in table.values() if v != 'none']
    count = max(loaded, 1 + max(ids) if ids else 0)

    def route(stage: str) -> list[dict[str, float]]:
        chosen = table.get(stage, table['default'])
        return [{'id': i, 'scale': 1.0 if str(i) == chosen else 0.0} for i in range(count)]

    return route


def loaded_adapters(url: str) -> int:
    """How many LoRA adapters the server holds, 0 if it reports none."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url + '/lora-adapters', headers=headers()), timeout=10) as response:
            return len(json.load(response))
    except (urllib.error.URLError, OSError, ValueError):
        return 0


def guidance(run: Investigation) -> Json:
    """Added to each tool result shown to the model, never to the recorded result, so recordings still replay."""
    stage = current_stage(run)
    return {'next': stage.instruction, 'open_tools': list(stage.tools), **searches(run)}


def play(
    case: Case,
    respond: Respond,
    system: str,
    max_turns: int,
    max_errors: int,
    max_tokens: int,
    guided: bool,
    schema: Schema | None,
    assist: bool = False,
    complete_workflow: bool = False,
    staged: bool = False,
    on_turn: Callable[[Investigation], None] | None = None,
    temperature: float = 0,
    attempt: int = 0,
    reasoned: bool = False,
    compact: bool = False,
    route: Callable[[str], list[dict[str, float]]] | None = None,
    prefix: Sequence[Json] = (),
    stop_when: Callable[[Investigation], bool] | None = None,
    quote_marks: bool = True,
    reread_limit: int | None = None,
) -> tuple[Investigation, Json]:
    """respond(messages, seed, max_tokens, schema, temperature) returns a reply. Everything else is fixed by the arm.
    route, if given, maps the current stage to the adapters the server applies, and is passed to respond as lora.
    prefix replays recorded turns first, each of which must return its recorded result, and marks their calls, so the model
    takes over mid-investigation from exactly the state a live run would show. stop_when(run) ends the run early."""
    run = Investigation(case, complete_workflow, staged, quote_marks, reread_limit)
    seed = sum(map(ord, case.id)) + 1000 * attempt
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': 'A new investigation is ready. Call read_brief.'}]
    turns, errors, stop = [], 0, 'turn limit'  # errors counts in a row, so one mistake does not end a run

    def shown_to_model(result: Json) -> Json:
        return {**result, **guidance(run)} if staged else dict(result, next=next_step(run)) if guided else result

    def advance(messages: list[Message], shown: Json) -> list[Message]:
        if compact:  # the model sees the state, not a transcript it could copy
            return [messages[0], {'role': 'user', 'content': state_of(run, shown)}]
        return messages + [{'role': 'user', 'content': 'Tool result: ' + json.dumps(shown)}]

    for index, turn in enumerate(prefix):
        call, problem = parse_call(turn['text'], schema is not None or staged)
        before = len(run.calls)
        result = run.call(call['name'], call['arguments']) if call is not None else {'error': problem}
        if json.dumps(result, sort_keys=True) != json.dumps(turn['tool_result'], sort_keys=True):
            raise ValueError(f'prefix turn {index + 1} returned something else on replay')
        for entry in run.calls[before:]:
            entry['prefix'] = True  # recorded, not this model's
        messages = advance(messages + [{'role': 'assistant', 'content': turn['text']}], shown_to_model(result))
    for _ in range(max_turns):
        if stop_when and stop_when(run):
            stop = 'left the stage'
            break
        try:
            extra = {'lora': route(current_stage(run).name)} if route else {}
            reply = respond(messages, seed + errors, max_tokens, schema_for(run, reasoned) if staged else schema, 0.4 if errors else temperature, **extra)
        except urllib.error.HTTPError as error:
            body = error.read().decode('utf8', 'replace')
            stop = 'context limit' if 'exceeds the available context' in body else f'server refused: {error.code}'  # a limit, not a fault
            break
        raw = reply.pop('raw', None)  # a backend's own form of the reply, returned to it unchanged
        turns.append(reply)
        messages.append({'role': 'assistant', 'content': reply['text'], **({'raw': raw} if raw else {})})
        call, problem = parse_call(reply['text'], schema is not None or staged)
        result = run.call(call['name'], call['arguments']) if call is not None else {'error': problem}
        errors = errors + 1 if 'error' in result else 0
        reply['tool_result'] = result
        if on_turn:
            on_turn(run)
        if run.final is not None:
            stop = 'finished'
            break
        if errors >= max_errors:
            stop = 'repeated errors'
            break
        found = None
        if assist and call and call['name'] == 'frame_problem' and 'error' not in result:
            found = [hit for query in ASSISTED_SEARCHES for hit in run.call('search_evidence', {'query': query})['results']]
            for entry in run.calls[-len(ASSISTED_SEARCHES) :]:
                entry['harness'] = True  # the harness made these, not the model
        shown = shown_to_model(result)
        if found:
            shown['evidence_found_for_you'] = found
        messages = advance(messages, shown)
    else:
        if stop_when and stop_when(run):
            stop = 'left the stage'
    return run, {'turns': turns, 'stop_reason': stop, 'prefix_turns': len(prefix)}


STAGES = (
    'read_brief',
    'frame_problem',
    'search_evidence',
    'read_source',
    'add_theory',
    'assess_evidence',
    'challenge_theory',
    'propose_test',
    'decline_test',
    'state_position',
    'revise_theory',
    'finish',
)


def recovered_after_refusal(run: Investigation) -> int:
    """Refused, then the model got the same tool right on its next call. The harness repaired nothing."""
    return sum(not a['accepted'] and b['accepted'] and a['name'] == b['name'] for a, b in zip(run.calls, run.calls[1:], strict=False))


def stopping_point(run: Investigation) -> Json:
    done = [c['name'] for c in run.calls if c['accepted']]
    rejected = rejected_categories(run)
    return {
        'furthest_stage': max(done, key=STAGES.index) if done else None,
        'calls': len(run.calls),
        'most_common_rejection': max(rejected, key=lambda category: rejected[category]) if rejected else None,
        'stage_at_stop': current_stage(run).name if run.staged else None,
        'rejected_finishes': sum(c['name'] == 'finish' and not c['accepted'] for c in run.calls),
        'harness_actions': sum(bool(c.get('harness')) for c in run.calls),
        'refused': sum(not c['accepted'] for c in run.calls),
        'recovered_after_refusal': recovered_after_refusal(run),
    }


def record_of(run: Investigation, info: Json | None = None) -> Json:
    return {
        'stopping_point': stopping_point(run),
        'challenge_searches': run.challenge_searches,
        'case': run.case.id,
        'company': run.case.company,
        'simulated_case': run.case.simulated,
        'checks': run_checks(run),
        'rejections': rejected_categories(run),
        'settings': {'complete_workflow': run.complete_workflow, 'staged': run.staged, 'quote_marks': run.quote_marks}
        | ({'reread_limit': run.reread_limit} if run.reread_limit is not None else {}),
        'coverage': coverage(run),
        'position': run.position,
        'test_declined': run.test_declined,
        'frame': run.frame,
        'theories': run.theories,
        'assessments': run.assessments,
        'tests': run.tests,
        'revisions': run.revisions,
        'final': run.final,
        'searches': run.searches,
        'read': sorted(run.read),
        'calls': run.calls,
        'stop_reason': (info or {}).get('stop_reason'),
        'model_turns': (info or {}).get('turns', []),
    }


def summary(records: list[Json]) -> Json:
    names = list(records[0]['checks']) if records else []
    table = {}
    for name in names:
        reached = [r for r in records if r['checks'][name]['status'] in ('passed', 'failed')]
        table[name] = {
            'passed': sum(r['checks'][name]['status'] == 'passed' for r in reached),
            'reached': len(reached),
            'applied': sum(r['checks'][name]['status'] != 'not_applicable' for r in records),
            'of_all': len(records),
        }
    whole = [guards_cleared(r['checks']) for r in records]
    shocked = [r['coverage']['shock'] for r in records if r['coverage']['shock']]
    shock = {
        'cases': len(shocked),
        'delivered': sum(s['delivered'] for s in shocked),
        'read': sum(s['read'] for s in shocked),
        'held_affected_theory': sum(bool(s['affected_theories']) for s in shocked),
        'addressed_an_affected_theory': sum(bool(s['affected_addressed']) for s in shocked),
        'bore_on_favoured': sum(s['bears_on_favoured'] for s in shocked),
        'cited_in_revision': sum(s['cited_in_revision'] for s in shocked),
        'favoured_changed': sum(s['favoured_changed'] for s in shocked),
    }
    stops, furthest = {}, {}
    for record in records:
        stops[record['stop_reason']] = stops.get(record['stop_reason'], 0) + 1
        place = record['stopping_point']['furthest_stage']
        furthest[place] = furthest.get(place, 0) + 1
    rejections = {}
    for record in records:
        for key, value in record['rejections'].items():
            rejections[key] = rejections.get(key, 0) + value
    return {
        'episodes': len(records),
        'finished': sum(r['final'] is not None for r in records),
        'end_to_end_success': sum(whole),
        'stop_reasons': stops,
        'furthest_stage': furthest,
        'checks': table,
        'rejections': rejections,
        'shock_coverage': shock,
        'supporting_evidence_attempted': sum(r['coverage']['supporting_evidence_assessed'] > 0 for r in records),
        'rejected_finishes': sum(r['stopping_point']['rejected_finishes'] for r in records),
        'harness_actions': sum(r['stopping_point']['harness_actions'] for r in records),
        'refused_calls': sum(r['stopping_point']['refused'] for r in records),
        'recovered_after_refusal': sum(r['stopping_point']['recovered_after_refusal'] for r in records),
        'harness_corrections': 0,
        'resources': {
            key: round(sum(t.get(key, 0) for r in records for t in r['model_turns']), 3) for key in ('prompt_tokens', 'completion_tokens', 'seconds', 'usd')
        },
        'mean_calls': sum(len(r['calls']) for r in records) / (len(records) or 1),
    }


def _digest(data: object) -> str:
    return hashlib.sha256(data if type(data) is bytes else json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]


def protocol_of(system: str, generation: Json) -> Json:
    """Code, prompt and generation settings. A base and a fine-tuned arm must share this."""
    from strategy_agent.common.paths import DOSSIER

    package = Path(__file__).resolve().parents[1]
    files = {
        'controller': package / 'env/stages.py',
        'tools': package / 'env/tools.py',
        'checks': package / 'env/checks.py',
        'runner': package / 'agent/runner.py',
        'constants': package / 'common/constants/env.py',
        'prompts': package / 'common/constants/prompts.py',
        'evidence': DOSSIER / 'evidence.json',
        'cases': DOSSIER / 'cases.json',
    }
    parts = {name: _digest(path.read_bytes()) for name, path in files.items()}
    parts.update(chat=_digest((package / 'common/model_client.py').read_bytes()), system_prompt=_digest(system), generation=_digest(generation))
    return {'id': _digest(parts), 'parts': parts, 'generation': generation}


def suite_of(cases: Sequence[Case], attempts: int) -> Json:
    """The ordered cases and attempts, so two runs on different cases can never look matched."""
    items = [[c.id, _digest([c.question, c.brief, c.shock.excerpt if c.shock else None, c.shock_direction, c.test_warranted])] for c in cases]
    return {'id': _digest([items, attempts]), 'cases': [c.id for c in cases], 'attempts': attempts}


def model_of(backend: str, name: str, weights_sha256: str | None = None, props: Json | None = None, generation: Json | None = None) -> Json:
    """What actually ran. A label alone proves nothing, so the weights hash, server details and the generation settings
    the server was started with (reasoning budget, context, slots, which the server does not report) go in."""
    props = props or {}
    info = {
        'backend': backend,
        'name': name,
        'weights_sha256': weights_sha256,
        'build': props.get('build_info'),
        'template': _digest(str(props.get('chat_template', ''))),
        'file': Path(str(props.get('model_path', ''))).name,
        'slots': props.get('total_slots'),
        'generation': generation or {},
    }
    return {**info, 'id': _digest(info)}


def matched(a: Json, b: Json) -> Any:
    """Only runs that share a protocol and suite, on different models, may be compared as an effect of the model."""
    return a['protocol']['id'] == b['protocol']['id'] and a['suite']['id'] == b['suite']['id'] and a['model']['id'] != b['model']['id']


def server_props(url: str) -> Any:
    with urllib.request.urlopen(urllib.request.Request(url + '/props', headers=headers()), timeout=30) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8091')
    parser.add_argument('--prompt', choices=sorted(PROMPTS), default='strong')
    parser.add_argument('--cases', default='all')
    parser.add_argument('--split', choices=('development', 'heldout'), default='development', help='heldout only for the final test')
    parser.add_argument('--max-turns', type=int, default=45)
    parser.add_argument('--max-errors', type=int, default=4, help='errors in a row before stopping')
    parser.add_argument('--reread-limit', type=int, help='refuse reading one source more than this many times (off by default, as evaluated)')
    parser.add_argument('--max-tokens', type=int, default=520)
    parser.add_argument('--context', type=int, default=12288, help='the server context size, recorded with the run')
    parser.add_argument('--output', required=True)
    parser.add_argument('--backend', choices=('llama', 'claude'), default='llama', help='claude is a positive control and never training data')
    parser.add_argument('--model-label', default='tiny-aya-global-q4_k_m.gguf a602ea7', help='what llama-server is serving, recorded with the run')
    parser.add_argument('--weights-sha256', help='the hash of the served weights, which decides whether a run can be a teacher')
    parser.add_argument('--manifest', default=str(PROVENANCE), help='the append-only record of where each episode came from')
    parser.add_argument('--temperature', type=float, default=0, help='the baselines stay at 0, and only teacher attempts vary')
    parser.add_argument('--attempts', type=int, default=1, help='runs per case, each with its own seed')
    parser.add_argument('--workers', type=int, default=1, help='episodes run at once, which needs the same number of server slots')
    parser.add_argument('--first-attempt', type=int, default=0, help='so a later stage gets new seeds rather than repeating an earlier one')
    parser.add_argument('--server-settings', help='JSON of how the server was started, such as {"reasoning_budget": 512}; recorded in every manifest entry')
    parser.add_argument('--lora-route', help="stage to adapter id, such as 'default=0,test=1', for adapters loaded on the server; staged prompts only")
    parser.add_argument('--effort', default='medium', help='claude backend only')
    parser.add_argument('--run-cap-usd', type=float, default=5.0, help='claude backend only')
    args = parser.parse_args()
    if args.backend == 'claude':
        respond = Claude(f'control {args.prompt}', args.run_cap_usd, args.effort)
        model, runtime = CLAUDE_MODEL, f'Anthropic API, effort {args.effort}, no seed or temperature, so runs do not repeat exactly'
        model_id = model_of('claude', model)
    else:
        respond = lambda messages, seed, max_tokens, schema, temperature, lora=None: chat(args.url, messages, seed, max_tokens, schema, temperature, lora=lora)  # noqa: E731
        model, runtime = args.model_label, 'llama.cpp b12032, temperature 0, 0.4 only on a retry straight after a rejected call'
        model_id = model_of('llama', model, args.weights_sha256, server_props(args.url), json.loads(args.server_settings) if args.server_settings else None)
    cases = load_cases(args.cases, split=args.split)
    system = PROMPTS[args.prompt]
    revision = (
        os.environ.get('CODE_REVISION') or subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, check=False).stdout.strip()
    )
    dirty = bool(subprocess.run(['git', 'status', '--porcelain', '--', 'src', 'data'], capture_output=True, text=True, check=False).stdout.strip())
    config = {
        'inference_only': True,
        'trained': False,
        'code_revision': revision,
        'uncommitted_changes': dirty,
        'arguments': vars(args),
        'system_prompt': system,
        'tool_schema': TOOL_SCHEMA,
        'guidance_in_tool_results': args.prompt != 'plain',
        'finish_needs_every_stage': args.prompt == 'workflow',
        'stage_controller': args.prompt in STRUCTURED,
        'server_context': args.context,
        'model': model,
        'runtime': runtime,
        'protocol': protocol_of(
            system,
            {
                'prompt': args.prompt,
                'split': args.split,
                'max_turns': args.max_turns,
                'consecutive_errors': args.max_errors,
                'max_tokens': args.max_tokens,
                'context': args.context,
                'temperature': args.temperature,
                'retry_temperature': 0.4,
            },
        ),
        'suite': suite_of(cases, args.attempts) | {'first_attempt': args.first_attempt},
        'model_identity': model_id,
    }
    output = Path(args.output)
    if output.exists() or output.with_suffix('.episodes.jsonl').exists():
        parser.error(f'{output} already exists, and results are never overwritten')
    output.parent.mkdir(parents=True, exist_ok=True)
    records, errors, lock = [], [], threading.Lock()
    jobs = [(c, a) for c in cases for a in range(args.first_attempt, args.first_attempt + args.attempts)]

    def one(job: tuple[Case, int]) -> None:
        """One episode. Each has its own seed and investigation, so episodes never share state."""
        case, attempt = job
        try:
            run, info = play(
                case,
                respond,
                system,
                args.max_turns,
                args.max_errors,
                args.max_tokens,
                args.prompt != 'plain',
                TOOL_SCHEMA,
                args.prompt == 'assisted',
                args.prompt == 'workflow',
                args.prompt in STRUCTURED,
                temperature=args.temperature,
                attempt=attempt,
                reasoned=args.prompt in REASONED,
                compact=args.prompt in COMPACT,
                route=lora_route(args.lora_route, loaded_adapters(args.url)) if args.lora_route else None,
                reread_limit=args.reread_limit,
            )
            record = dict(record_of(run, info), attempt=attempt)
            with lock:
                record['episode'] = record_provenance(info['turns'], case, model_id, config['protocol']['id'], args.manifest)
        except Exception:  # noqa: BLE001  one bad episode must not lose the rest
            with lock:
                errors.append({'case': case.id, 'attempt': attempt, 'error': traceback.format_exc(limit=3)})
                log.write(json.dumps({'harness_error': errors[-1]}) + '\n')
                log.flush()
            return
        with lock:
            records.append(record)
            log.write(json.dumps(record) + '\n')
            log.flush()
            os.fsync(log.fileno())
            print(
                json.dumps(
                    {
                        'case': case.id,
                        'attempt': attempt,
                        'stop': info['stop_reason'],
                        'turns': len(info['turns']),
                        'passed': sum(bool(c['passed']) for c in record['checks'].values()),
                        'failed': [k for k, c in record['checks'].items() if c['passed'] is False],
                    }
                ),
                flush=True,
            )

    with open(output.with_suffix('.episodes.jsonl'), 'w') as log:
        log.write(json.dumps({'config': config}) + '\n')
        log.flush()
        if args.workers > 1:  # the server batches concurrent episodes, which is much faster for a large model
            with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
                list(pool.map(one, jobs))
        else:
            for job in jobs:
                one(job)
    order = {(c.id, a): i for i, (c, a) in enumerate(jobs)}
    records.sort(key=lambda r: order[(r['case'], r['attempt'])])
    report = dict(config, prompt=args.prompt, summary=summary(records), harness_errors=errors, records=records)
    try:
        from strategy_agent.evaluation.audit import audit

        report['auditkit'] = audit(records, cases)
    except ImportError as error:
        report['auditkit'] = {'skipped': str(error)}
    output.write_text(json.dumps(report, indent=1))
    print(json.dumps({'summary': report['summary'], 'auditkit': report['auditkit']}, indent=1))
    refused = [r['case'] for r in records if str(r['stop_reason']).startswith('server refused')]
    if errors or refused or not records:  # a server fault must never read as model behaviour
        raise SystemExit(f'{len(errors)} episodes failed in the harness, and the server refused {refused}')


if __name__ == '__main__':
    main()
