"""Recovery corrections: the teacher's next call from the exact states where the student loops. docs/RECOVERY_PILOT.md.

Three steps, each recorded:
1. states: replay recorded student runs and keep the compact context shown at each turn that starts a loop: a call
   refused as a repeat, the third read of one source, or a second refusal in a row. Training companies only.
2. ask: the teacher answers each state with what has been learned, what is still uncertain, why the next action helps,
   and the call, under a schema that allows only the tools open at that stage. A correction is kept only if replaying
   it is accepted, it repeats nothing earlier in the run, and its justification names something concrete from the state
   that the call acts on. Every kept and refused correction is written with its reason, and the teacher's raw reply is
   hashed into the manifest under protocol correction-v1.
3. rows: kept corrections become rows like every other row, the student's state as context and the call as the only
   target, tagged source: correction. A row is refused unless the manifest holds that exact reply for that state.

Usage: python -m strategy.correct states --reports R.json [--stages test] --output states.json
       python -m strategy.correct ask --states states.json --url URL --weights-sha256 SHA --manifest M.jsonl --output corrections.json
       python -m strategy.correct rows --corrections corrections.json --manifest M.jsonl --output rows.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from strategy_agent.agent.runner import PROMPTS, guidance, schema_for, state_of
from strategy_agent.common.constants.pipeline import ASK, MAX_PER_RUN, PROTOCOL  # noqa: F401
from strategy_agent.common.model_client import chat, parse_call
from strategy_agent.common.types import Json
from strategy_agent.env.cases import load_cases
from strategy_agent.env.stages import current_stage
from strategy_agent.env.tools import Investigation
from strategy_agent.pipeline.freeze import held_out
from strategy_agent.pipeline.provenance import CorrectionEntry, GenerationSettings, append_entry, case_digest, read_manifest
from strategy_agent.pipeline.splits import is_validation

if TYPE_CHECKING:
    from strategy_agent.env.tools import Case

START = 'A new investigation is ready. Call read_brief.'


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _replay(record: Json, case: Case, upto: int) -> tuple[Investigation, list[dict[str, str]]]:
    """The investigation after the first upto recorded turns, and the compact context the student saw next."""
    run = Investigation(case, record['settings'].get('complete_workflow', False), True, record['settings'].get('quote_marks', False))
    shown = {}
    for turn in record['model_turns'][:upto]:
        call, problem = parse_call(turn['text'], True)
        result = run.call(call['name'], call['arguments']) if call is not None else {'error': problem}
        if json.dumps(result, sort_keys=True) != json.dumps(turn['tool_result'], sort_keys=True):
            raise ValueError('student turn returned something else on replay')
        shown = {**result, **guidance(run)}
    context = [{'role': 'system', 'content': PROMPTS['compact']}, {'role': 'user', 'content': state_of(run, shown) if upto else START}]
    return run, context


def loop_starts(record: Json) -> list[Any]:
    """Turn indexes that start a loop, from the recorded calls."""
    starts, reads, refused_in_a_row = [], {}, 0
    calls = [c for c in record['calls'] if not c.get('prefix')]
    for index, call in enumerate(calls):
        error = str(call.get('result', {}).get('error', ''))
        repeat = not call['accepted'] and 'already' in error
        if call['name'] == 'read_source' and call['accepted']:
            reads[call['arguments'].get('id')] = reads.get(call['arguments'].get('id'), 0) + 1
        third_read = call['name'] == 'read_source' and reads.get(call['arguments'].get('id'), 0) == 3
        refused_in_a_row = refused_in_a_row + 1 if not call['accepted'] else 0
        if repeat or third_read or refused_in_a_row == 2:
            starts.append(index)
    return starts


def states(reports: Sequence[str | Path], stages: Sequence[str] = (), identity: Json | None = None) -> list[Any]:
    """With stages, only loops that start in those stages are kept, to target a failure seen in the student."""
    cases = {c.id: c for c in load_cases()}
    final = set(c['id'] for c in held_out()[0])
    out = []
    for path in reports:
        report = json.loads(Path(path).read_text())
        # Which student made the run, so a correction can always be traced to the adapter and runtime it came from
        who = (
            {k: report.get(k) for k in ('model_identity', 'code_revision', 'runtime')}
            | {'protocol': (report.get('protocol') or {}).get('id')}
            | (identity or {})
        )
        for record in report['records']:
            if is_validation(record['case']) or record['case'] in final or record['case'] not in cases:
                continue  # training companies only, so validation and the final test stay unseen
            if len(record['calls']) != len(record['model_turns']):
                continue  # a turn without a call cannot be aligned exactly
            case = cases[record['case']]
            student = _digest(json.dumps([[t['text'], t['tool_result']] for t in record['model_turns']], sort_keys=True))
            starts = loop_starts(record)
            firsts = [i for n, i in enumerate(starts) if n == 0 or starts[n - 1] != i - 1]  # one state per loop, its first turn
            if stages:
                firsts = [i for i in firsts if record['calls'][i].get('stage') in stages]
            for index in firsts[:: max(len(firsts) // MAX_PER_RUN, 1)][:MAX_PER_RUN]:  # and at most a few per investigation
                _, context = _replay(record, case, index)
                out.append(
                    {
                        'case': case.id,
                        'case_digest': case_digest(case),
                        'student_run': student,
                        'student_model': report.get('model') or record.get('model') or str(path),
                        'student_identity': who,
                        'turn': index,
                        'record': {'settings': record['settings'], 'model_turns': record['model_turns'][:index]},
                        'context': context,
                        'refused_next': record['calls'][index],
                    }
                )
    return out


def _schema(run: Investigation) -> Json:
    return {
        'type': 'object',
        'additionalProperties': False,
        'required': ['learned', 'uncertain', 'why_next', 'call'],
        'properties': {
            'learned': {'type': 'string', 'maxLength': 400},
            'uncertain': {'type': 'string', 'maxLength': 300},
            'why_next': {'type': 'string', 'maxLength': 300},
            'call': schema_for(run),
        },
    }


def judge(state: Json, reply_text: str) -> tuple[Json | None, str]:
    """Kept or refused, with the reason. Mechanical: it checks the call works and is grounded, not that it is wise."""
    cases = {c.id: c for c in load_cases()}
    case = cases[state['case']]
    try:
        answer = json.loads(reply_text)
        call = answer['call']
    except (ValueError, KeyError, TypeError):
        return None, 'not the required JSON'
    run, _ = _replay(state['record'], case, len(state['record']['model_turns']))
    before = {(c['name'], json.dumps(c['arguments'], sort_keys=True)) for c in run.calls}
    if (call.get('name'), json.dumps(call.get('arguments'), sort_keys=True)) in before:
        return None, 'repeats an earlier call'
    stage = current_stage(run).name
    result = run.call(call.get('name'), call.get('arguments'))
    if 'error' in result:
        return None, f'refused by the tools: {result["error"]}'
    justification = ' '.join(str(answer.get(k, '')) for k in ('learned', 'uncertain', 'why_next'))
    concrete = set(run.read) | set(run.surfaced) | set(run.theories) | set(run.tests)
    named = {item for item in concrete if item and item in justification}
    acted_on = json.dumps(call.get('arguments'))
    if not named:
        return None, 'the justification names nothing from the state'
    if call['name'] in ('read_source', 'assess_evidence', 'challenge_theory', 'revise_theory') and not any(item in acted_on for item in named):
        return None, 'the call does not act on what the justification names'
    if stage == 'test':  # a valid new call is not enough here: the correction must move the test stage on
        args = call.get('arguments') or {}
        if call['name'] == 'propose_test':
            predictions = {k: str(v).strip().lower() for k, v in (args.get('prediction_by_theory') or {}).items() if k in run.theories}
            if len(predictions) < 2 or len(set(predictions.values())) < len(predictions):
                return None, 'the test does not give different predictions for at least two theories'
            if not any(ch.isdigit() for ch in str(args.get('decision_rule', ''))):
                return None, 'the decision rule has no threshold'
            if not any(t in str(answer.get('why_next', '')) for t in predictions):
                return None, 'why_next does not say which theories the test separates'
        elif call['name'] == 'decline_test':
            if len(str(args.get('reason', '')).split()) < 12:
                return None, 'declining a test without a reason that explains why more information is not worth it'
        else:
            return None, 'in the test stage only proposing a discriminating test or justifying declining one advances the investigation'
    return {'call': call, 'stage': stage, 'justification': {k: answer[k] for k in ('learned', 'uncertain', 'why_next')}}, 'kept'


def ask(state_items: list[Json], url: str, weights: str, manifest: str | Path, seed: int = 11, workers: int = 1, generation: Json | None = None) -> list[Json]:
    """One teacher turn per state, several at once if the server has slots. Every reply is hashed into the manifest
    before it is judged, under a lock, so the record holds every reply, kept or not."""
    import concurrent.futures
    import threading

    cases = {c.id: c for c in load_cases()}
    lock = threading.Lock()

    def one(numbered: tuple[int, Json]) -> Json:
        number, state = numbered
        run, _ = _replay(state['record'], cases[state['case']], len(state['record']['model_turns']))
        messages = [{'role': 'system', 'content': PROMPTS['teacher'] + '\n\n' + ASK}, state['context'][1]]
        try:
            reply = chat(url, messages, seed + number, 2400, _schema(run), 0)  # room for the thinking block and the answer
        except Exception as error:  # noqa: BLE001  recorded, so a failed request is visible and not silently dropped
            return {
                'state': {k: state[k] for k in ('case', 'case_digest', 'student_run', 'turn')},
                'decision': f'request failed: {type(error).__name__}',
                'kept': None,
            }
        entry = CorrectionEntry(
            protocol=PROTOCOL,
            case=state['case'],
            case_digest=state['case_digest'],
            student_run=state['student_run'],
            turn=state['turn'],
            weights_sha256=weights,
            generation=GenerationSettings.model_validate(generation or {}),
            reply_sha256=_digest(reply['text']),
        )
        with lock:
            append_entry(entry, manifest)
        kept, reason = judge(state, reply['text'])
        return {
            'state': {k: state[k] for k in ('case', 'case_digest', 'student_run', 'turn')},
            'record': state['record'],
            'context': state['context'],
            'reply': reply['text'],
            'thinking': reply.get('thinking'),
            'decision': reason,
            'kept': kept,
        }

    with concurrent.futures.ThreadPoolExecutor(max(workers, 1)) as pool:
        return list(pool.map(one, enumerate(state_items)))


def rows(corrections: list[Json], manifest: str | Path) -> list[Any]:
    """Rows from kept corrections whose exact reply the manifest holds for that state."""
    held = {(m.student_run, m.turn, m.reply_sha256) for m in read_manifest(manifest) if isinstance(m, CorrectionEntry)}
    made = []
    for item in corrections:
        state = item['state']
        if not item['kept'] or (state['student_run'], state['turn'], _digest(item['reply'])) not in held:
            continue
        kept, reason = judge({**state, 'record': item['record']}, item['reply'])  # re-judged, so an edited file cannot pass
        if kept is None or reason != 'kept':  # judge returns a correction exactly when it is kept
            continue
        # A row shows exactly the context the teacher answered. A correction asked under an older state format is not
        # turned into a row: the teacher never saw today's state, so it is asked again instead (DECISIONS, 2026-11-05).
        case = {c.id: c for c in load_cases()}[state['case']]
        _, current = _replay(item['record'], case, len(item['record']['model_turns']))
        context = item['context']
        if context != current:
            continue
        made.append(
            {
                'messages': context + [{'role': 'assistant', 'content': json.dumps({'name': kept['call']['name'], 'arguments': kept['call']['arguments']})}],
                'target_index': len(context),
                'stage': kept['stage'],
                'case': state['case'],
                'source': 'correction',
                'protocol': PROTOCOL,
                'episode': f'{state["student_run"][:16]}-{state["turn"]}',
                'justification': kept['justification'],
            }
        )
    return made


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('step', choices=('states', 'ask', 'rows'))
    parser.add_argument('--reports', nargs='*', default=[])
    parser.add_argument('--states')
    parser.add_argument('--corrections')
    parser.add_argument('--url')
    parser.add_argument('--weights-sha256')
    parser.add_argument('--manifest')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--stages', nargs='*', default=[], help='states: keep only loops that start in these stages, such as test')
    parser.add_argument('--student-identity', help='states: JSON of the adapter and runtime the student runs used, recorded with every state')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--server-settings', help='JSON of how the teacher server was started, recorded in every manifest entry')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.step == 'states':
        out = states(args.reports, args.stages, json.loads(args.student_identity) if args.student_identity else None)
        Path(args.output).write_text(json.dumps(out))
        print(json.dumps({'states': len(out), 'cases': len({s['case'] for s in out})}))
    elif args.step == 'ask':
        items = json.loads(Path(args.states).read_text())
        out = ask(
            items[: args.limit] if args.limit else items,
            args.url,
            args.weights_sha256,
            args.manifest,
            workers=args.workers,
            generation=json.loads(args.server_settings) if args.server_settings else None,
        )
        Path(args.output).write_text(json.dumps(out, indent=1))
        from collections import Counter

        print(json.dumps({'asked': len(out), 'decisions': dict(Counter(o['decision'] for o in out))}))
    else:
        out = rows([c for c in json.loads(Path(args.corrections).read_text()) if c.get('kept')], args.manifest)
        Path(args.output).write_text(''.join(json.dumps(r) + '\n' for r in out))
        print(json.dumps({'rows': len(out)}))


if __name__ == '__main__':
    main()
