"""One investigation: the model and the environment take turns until the model finishes or a limit is reached.

play() is the agent loop every arm uses (base, fine-tuned, teacher, control). Each turn the backend gets the messages
and the schema of the open tools; its reply is parsed into one tool call, the environment runs it (accepting or
refusing it with a reason), and the model is shown the result, or in compact runs the whole state.
"""

from __future__ import annotations

import json
import urllib.error
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from aemon.agent import recovery
from aemon.agent.backends.llama_client import parse_call
from aemon.agent.state_view import guidance, next_step, state_of, stuck_help_text
from aemon.agent.tool_schemas import schema_for
from aemon.common.constants.prompts import ASSISTED_SEARCHES
from aemon.common.types import Json, Message, Respond, Schema
from aemon.environment.stages import current_stage
from aemon.environment.tools import Investigation

if TYPE_CHECKING:
    from aemon.environment.tools import Case


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
    source_dates: bool = False,
    stuck_help: bool = False,
    min_assessed: int = 1,
    recovery_features: Sequence[str] = (),
    errors_at_start: int = 0,
    status_check: bool = False,
) -> tuple[Investigation, Json]:
    """respond(messages, seed, max_tokens, schema, temperature) returns a reply. Everything else is fixed by the arm.
    route, if given, maps the current stage to the adapters the server applies, and is passed to respond as lora.
    prefix replays recorded turns first, each of which must return its recorded result, and marks their calls, so the model
    takes over mid-investigation from exactly the state a live run would show. stop_when(run) ends the run early."""
    run = Investigation(case, complete_workflow, staged, quote_marks, reread_limit, source_dates, min_assessed, status_check)
    run.stuck_help = stuck_help
    unknown = set(recovery_features) - set(recovery.FEATURES)
    if unknown:
        raise ValueError(f'unknown recovery features {sorted(unknown)}')
    run.recovery = frozenset(recovery_features)
    seed = sum(map(ord, case.id)) + 1000 * attempt
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': 'A new investigation is ready. Call read_brief.'}]
    turns, errors, stop = [], errors_at_start, 'turn limit'  # errors counts in a row, so one mistake does not end a run; a resumed checkpoint keeps its count
    still = 0  # calls in a row without progress (recovery controller only)
    run.model_turns = turns  # the raw turns so far, readable from on_turn (Aemon saves them to resume a run)

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
        shown = shown_to_model(result)
        if stuck_help and index == len(prefix) - 1 and 'error' in result:  # taking over a stuck run: help from the first step
            shown['help'] = stuck_help_text(run)
        messages = advance(messages + [{'role': 'assistant', 'content': turn['text']}], shown)
    for used in range(max_turns):
        run.turns_left = max_turns - used
        if stop_when and stop_when(run):
            stop = 'left the stage'
            break
        try:
            extra = {'lora': route(current_stage(run).name, errors)} if route else {}
            reply = respond(messages, seed + errors, max_tokens, schema_for(run, reasoned) if staged else schema, 0.4 if errors else temperature, **extra)
        except urllib.error.HTTPError as error:
            body = error.read().decode('utf8', 'replace')
            stop = 'context limit' if 'exceeds the available context' in body else f'server refused: {error.code}'  # a limit, not a fault
            break
        raw = reply.pop('raw', None)  # a backend's own form of the reply, returned to it unchanged
        if route:
            reply['adapters'] = [a['id'] for a in extra['lora'] if a['scale']]  # which adapter wrote this turn
        turns.append(reply)
        messages.append({'role': 'assistant', 'content': reply['text'], **({'raw': raw} if raw else {})})
        call, problem = parse_call(reply['text'], schema is not None or staged)
        before_state = recovery.signature(run)
        calls_before = len(run.calls)
        result = run.call(call['name'], call['arguments']) if call is not None else {'error': problem}
        redraws = 0
        # resample_repeats (experimental, development only): a call the environment refused as an exact repeat changed
        # nothing, so the same state is drawn again (temperature 0.8, new seed) up to 3 times before the refusal counts.
        # Every refused draw stays in run.calls, marked redrawn, so refusal counts are unchanged.
        while 'resample_repeats' in run.recovery and 'error' in result and len(run.calls) > calls_before and run.calls[-1].get('category') == 'repeat' and redraws < 3:
            run.calls[-1]['redrawn'] = True
            redraws += 1
            try:
                again = respond(messages[:-1], seed + 7919 * redraws, max_tokens, schema_for(run, reasoned) if staged else schema, 0.8, **extra)
            except urllib.error.HTTPError:
                break
            again.pop('raw', None)
            if route:
                again['adapters'] = reply.get('adapters')
            again['redraw_of'] = reply['text']
            reply = again
            turns[-1] = reply
            messages[-1] = {'role': 'assistant', 'content': reply['text']}
            call, problem = parse_call(reply['text'], schema is not None or staged)
            result = run.call(call['name'], call['arguments']) if call is not None else {'error': problem}
        if redraws:
            reply['redraws'] = redraws
        errors = errors + 1 if 'error' in result else 0
        still = 0 if recovery.signature(run) != before_state else still + 1
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
        if stuck_help and errors >= 2:  # two refusals in a row: say concretely what it can do instead
            shown['help'] = stuck_help_text(run)
        if run.recovery:
            run.turns_left = max_turns - used - 1
            upcoming = schema_for(run, reasoned) if staged else {}
            if 'progress' in run.recovery:
                if 'error' in result and len(run.calls) > calls_before:
                    shown['refusal'] = recovery.refusal_note(run, run.calls[-1], upcoming)
                if still >= recovery.NO_PROGRESS_LIMIT:
                    shown['recovery'] = recovery.recovery_note(run, [c for c in run.calls if not c.get('prefix')][-still:], upcoming)
            if 'budget' in run.recovery and recovery.tight(run):
                shown['budget'] = recovery.budget_note(run)
        messages = advance(messages, shown)
    else:
        if stop_when and stop_when(run):
            stop = 'left the stage'
    return run, {'turns': turns, 'stop_reason': stop, 'prefix_turns': len(prefix)}
