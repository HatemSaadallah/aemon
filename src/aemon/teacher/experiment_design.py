"""Experiment-design answers written as a structured design and composed into propose_test (2026-11-10, DECISIONS).

In three pilots most experiment answers were cut at a field's length limit: the constrained generation closes a string
when it reaches maxLength, and the teacher cannot count characters, so "keep it short" did not help. Here the teacher
fills one field per part of the design (target customers, treatment, control, recruitment, outcome, predictions,
threshold, next step per result, cost, duration), each with a generous guard limit only. The fields are composed
deterministically into propose_test's arguments. If a composed field, the reason of a decline or a justification is
over the tool's limit, the teacher gets one turn with the exact character counts to shorten those fields; if it is still
over, the answer is refused. Every raw reply and the composed reply are hashed into the manifest, and verify() checks
that the composed reply is exactly compose() of the last raw reply. The gates and the training rows are unchanged:
a row is the composed call, as for every other family.
"""

from __future__ import annotations

import json
from typing import Any

from aemon.agent.tool_schemas import _BY_NAME
from aemon.common.constants.prompts import PROMPTS
from aemon.agent.backends.llama_client import chat
from aemon.common.types import Json
from aemon.environment.cases import load_cases
from aemon.teacher import corrections as c
from aemon.rows.provenance import CorrectionEntry, GenerationSettings, append_entry, read_manifest
from aemon.teacher.targeted import JUSTIFICATION_LIMITS

COMPOSITION = 'experiment-structured-v1'
GUARD = 1600  # a runaway guard, far above what any field needs; the real limits are checked after composition
MARGIN = 3  # the cut-off screen treats a field within 2 characters of its limit as cut

DESIGN_ASK = (
    'You are shown the state of an investigation another analyst was running, at the point where they had to decide '
    'whether to test. Make that decision well: either design one experiment or decline to test.\n'
    'Design an experiment only if it can change what the company should do. A good experiment: tests the uncertainty '
    'that separates the open theories (why customers would buy, not which message persuades them); gives each theory '
    'a different prediction that follows from its causal mechanism; varies a real product attribute, price, channel '
    'or how it is sold between treatment and control, with the presentation otherwise the same, or measures a real '
    'commitment (a pre-order, a deposit, a paid trial, sell-through) rather than only stated preference; fits the '
    'stated budget and time; and has a decision threshold that leads, for every result, to a bounded next step (a '
    'pilot, a prototype run, a partner trial, or stopping), not to building a product line.\n'
    'Decline when more information would not justify its cost: the evidence already settles the question, no result '
    'could change the decision, acting now is worth more than waiting, a more fundamental constraint in the state '
    'blocks the decision (for example the company cannot make, sell or legally offer it), or no test fits the limits. '
    'Say which of these applies, from the state. Declining for a good reason is a correct answer, not a failure.\n'
    'Sample size, threshold, cost and duration are proposed parameters of your test, not facts: choose round, plausible '
    'values that fit the budget, do not claim statistical power or precision the state cannot justify, and never present '
    'them as facts about the market. Stay inside the case: methods, prices and currency of its country and date, and '
    'only sources dated on or before it.\n'
    'In recruitment say who takes part, how they are recruited and how many. Write each field as one or two plain sentences. In learned, uncertain and why_next write the exact ids of the '
    'sources and theories you rely on; in why_next say which theories the test separates and why (for example "separates '
    'T1 from T2 because..."), or why declining is right.'
)

_TEXT = {'type': 'string', 'maxLength': GUARD}


def schema(run: Any) -> Json:
    theories = sorted(run.theories)
    design = {
        'type': 'object',
        'additionalProperties': False,
        'required': ['name', 'theories', 'target_customers', 'treatment', 'control', 'recruitment', 'outcome', 'prediction_by_theory', 'threshold',
                     'next_step_by_result', 'cost_eur', 'weeks'],
        'properties': {
            'name': {'type': 'string', 'maxLength': 200},
            'theories': {'type': 'array', 'items': {'enum': theories}, 'minItems': 2, 'maxItems': 5},
            'target_customers': _TEXT, 'treatment': _TEXT, 'control': _TEXT, 'recruitment': _TEXT, 'outcome': _TEXT,
            'prediction_by_theory': {'type': 'object', 'additionalProperties': False, 'required': theories, 'properties': {k: _TEXT for k in theories}},
            'threshold': _TEXT, 'next_step_by_result': _TEXT,
            'cost_eur': {'type': 'number'}, 'weeks': {'type': 'number'},
        },
    }
    decline = {'type': 'object', 'additionalProperties': False, 'required': ['reason'], 'properties': {'reason': _TEXT}}
    decision = {'anyOf': [
        {'type': 'object', 'additionalProperties': False, 'required': ['design'], 'properties': {'design': design}},
        {'type': 'object', 'additionalProperties': False, 'required': ['decline'], 'properties': {'decline': decline}},
    ]}
    return {
        'type': 'object',
        'additionalProperties': False,
        'required': ['learned', 'uncertain', 'why_next', 'decision'],
        'properties': {'learned': _TEXT, 'uncertain': _TEXT, 'why_next': _TEXT, 'decision': decision},
    }


def compose(raw: Json) -> Json:
    """The teacher's structured answer as the answer every gate reads: a propose_test or decline_test call."""
    decision = raw['decision']
    if 'decline' in decision:
        call = {'name': 'decline_test', 'arguments': {'reason': decision['decline']['reason'].strip()}}
    else:
        d = decision['design']
        call = {'name': 'propose_test', 'arguments': {
            'name': d['name'].strip(),
            'theories': list(d['theories']),
            'method': f"Target customers: {d['target_customers'].strip()} Treatment: {d['treatment'].strip()} Control: {d['control'].strip()}",
            'sample': d['recruitment'].strip(),
            'measure': d['outcome'].strip(),
            'prediction_by_theory': {k: v.strip() for k, v in d['prediction_by_theory'].items() if k in d['theories']},
            'decision_rule': f"{d['threshold'].strip()} {d['next_step_by_result'].strip()}",
            'cost_eur': d['cost_eur'],
            'weeks': d['weeks'],
        }}
    return {**{k: raw[k].strip() for k in ('learned', 'uncertain', 'why_next')}, 'call': call}


def over_limits(answer: Json) -> dict[str, tuple[int, int]]:
    """Fields longer than the tool or justification limit allows (with the cut-off screen's margin): name -> (length, limit)."""
    fields = _BY_NAME[answer['call']['name']]['properties']['arguments']['properties']
    found = {}
    for k, v in answer['call']['arguments'].items():
        limit = fields.get(k, {}).get('maxLength')
        if isinstance(v, str) and limit and len(v) > limit - MARGIN:
            found[k] = (len(v), limit - MARGIN)
    for k, v in (answer['call']['arguments'].get('prediction_by_theory') or {}).items():
        limit = fields['prediction_by_theory']['additionalProperties']['maxLength'] if 'prediction_by_theory' in fields else 0
        if limit and len(v) > limit - MARGIN:
            found[f'prediction_by_theory.{k}'] = (len(v), limit - MARGIN)
    for k, limit in JUSTIFICATION_LIMITS.items():
        if len(answer[k]) > limit - MARGIN:
            found[k] = (len(answer[k]), limit - MARGIN)
    return found


# Which structured fields make up each composed field, so the shortening turn names the fields the teacher wrote
PARTS = {'method': 'target_customers, treatment and control together', 'sample': 'recruitment', 'measure': 'outcome',
         'decision_rule': 'threshold and next_step_by_result together', 'reason': 'decline.reason'}


def shorten_note(over: dict[str, tuple[int, int]]) -> str:
    lines = [f'- {PARTS.get(k, k)}: {n} characters, at most {limit}' for k, (n, limit) in over.items()]
    return ('Some fields are too long for the tool and would be cut mid-sentence:\n' + '\n'.join(lines) +
            '\nReturn the same answer in the same JSON shape with those fields shortened to fit, keeping their meaning and '
            'every id, number and theory they name. Change nothing else.')


def ask(items: list[Json], url: str, weights: str, manifest: str, generation: Json | None = None, seed: int = 31) -> list[Json]:
    cases = {x.id: x for x in load_cases()}
    out = []
    for number, state in enumerate(items):
        run, _ = c._replay(state['record'], cases[state['case']], len(state['record']['model_turns']))
        messages = [{'role': 'system', 'content': PROMPTS['teacher'] + '\n\n' + DESIGN_ASK}, state['context'][1]]
        brief = {k: state[k] for k in ('case', 'case_digest', 'student_run', 'turn')}

        def record(text: str) -> None:
            append_entry(CorrectionEntry(protocol=c.PROTOCOL, case=state['case'], case_digest=state['case_digest'], student_run=state['student_run'],
                                         turn=state['turn'], weights_sha256=weights, generation=GenerationSettings.model_validate(generation or {}),
                                         reply_sha256=c._digest(text)), manifest)

        raws, thinking = [], []
        try:
            reply = chat(url, messages, seed + number, 3000, schema(run), 0.0)
            record(reply['text'])
            raws.append(reply['text']), thinking.append(reply.get('thinking'))
            answer = compose(json.loads(reply['text']))
            over = over_limits(answer)
            if over:  # one turn with the exact counts; the teacher's own shortened text, never ours
                messages += [{'role': 'assistant', 'content': reply['text']}, {'role': 'user', 'content': shorten_note(over)}]
                reply = chat(url, messages, seed + number + 500, 3000, schema(run), 0.0)
                record(reply['text'])
                raws.append(reply['text']), thinking.append(reply.get('thinking'))
                answer = compose(json.loads(reply['text']))
                over = over_limits(answer)
        except Exception as error:  # noqa: BLE001  recorded, so a failed request is visible and not silently dropped
            out.append({'state': brief, 'decision': f'request failed: {type(error).__name__}', 'kept': None, 'skill': 'experiment', 'sample': 0, 'raw_replies': raws})
            continue
        text = json.dumps(answer, ensure_ascii=False)
        record(text)
        item = {'state': brief, 'record': state['record'], 'context': state['context'], 'reply': text, 'raw_replies': raws, 'thinking': thinking,
                'composition': COMPOSITION, 'shortened': len(raws) > 1, 'skill': 'experiment', 'sample': 0}
        if over:
            item['kept'], item['decision'] = None, 'still over the length limit after one shortening: ' + ', '.join(over)
        else:
            from aemon.teacher.corrective import gate  # the family gate, as for every corrective answer

            item['kept'], item['decision'] = gate({**state, 'skill': 'experiment'}, text)
        out.append(item)
    return out


def verify(item: Json, manifest: str) -> bool:
    """The composed reply is exactly compose() of the last raw reply, and every reply is in the manifest."""
    if item.get('composition') != COMPOSITION or not item.get('raw_replies'):
        return False
    held = {(m.student_run, m.turn, m.reply_sha256) for m in read_manifest(manifest) if isinstance(m, CorrectionEntry)}
    key = (item['state']['student_run'], item['state']['turn'])
    if any((*key, c._digest(r)) not in held for r in item['raw_replies']):
        return False
    return json.dumps(compose(json.loads(item['raw_replies'][-1])), ensure_ascii=False) == item['reply']
