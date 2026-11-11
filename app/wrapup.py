"""When an investigation stops early, Aemon still gives an answer: a draft recommendation written from what
the investigation found, marked as a draft, with the reason it stopped and its confidence capped at Low.

The draft is written by the local model (adapters off, as for follow-ups) from the investigation's own record, and
may cite only real sources the investigation read. If even that fails, the interim position or the explanations
stand in, so the page always has something to show. Aemon only: the evaluated runs never use it.
"""

from __future__ import annotations

import json
from typing import Any

from followup import context

Json = dict[str, Any]
REASON = {
    'repeated errors': 'it got stuck repeating steps the checker would not accept',
    'turn limit': 'it ran out of steps',
    'context limit': 'it had more to read than fits in its memory',
}

SYSTEM = (
    'An investigation into a strategy question stopped before it finished. Write the best recommendation its record '
    'supports, for a non-technical manager. Use ONLY the record below. Be honest about what is missing: prefer a small, '
    'reversible next step (a pilot, a test, more evidence) over a big commitment. Cite only real sources from the record '
    'by id in evidence_ids; a SIMULATED result is never evidence. Never invent facts, figures or sources.'
)


def schema(record: Json) -> Json:
    theories = sorted((record.get('theories') or {}).keys()) or ['none']
    real = sorted(i for i, s in (record.get('sources') or {}).items() if not s.get('simulated')) or ['none']
    text = lambda n: {'type': 'string', 'maxLength': n}  # noqa: E731
    return {
        'type': 'object', 'additionalProperties': False,
        'required': ['recommendation', 'favoured_theory', 'next_action', 'uncertainty', 'would_change_if', 'evidence_ids'],
        'properties': {
            'recommendation': text(600), 'favoured_theory': {'enum': [*theories, 'none']}, 'next_action': text(300),
            'uncertainty': text(400), 'would_change_if': {'type': 'array', 'items': text(250), 'maxItems': 3},
            'evidence_ids': {'type': 'array', 'items': {'enum': real}, 'maxItems': 6},
        },
    }


def fallback(record: Json, reason: str) -> Json | None:
    """Without the model: the interim position if it took one, so the page still shows an answer."""
    position = record.get('position') or {}
    if position.get('recommendation'):
        return {'recommendation': position['recommendation'], 'favoured_theory': position.get('favoured_theory'),
                'next_action': 'Continue the investigation, or run a small test, before acting on this.',
                'uncertainty': f'The investigation stopped early: {reason}.', 'would_change_if': [], 'evidence_ids': [],
                'draft': True, 'draft_source': 'interim view'}
    return None


def draft(chat, url: str, record: Json, adapters: int) -> Json | None:  # noqa: ANN001
    """The draft final answer; with no evidence gathered it says so. None only when even the fallback has nothing."""
    stop = record.get('stop_reason') or 'error'
    reason = REASON.get(stop, f'it stopped ({stop})')
    brief = next((c.get('result', {}).get('brief') for c in record.get('calls') or [] if c.get('name') == 'read_brief' and c.get('accepted')), None)
    thin = not record.get('theories') and not record.get('sources')
    note = (' It gathered no evidence before stopping: say so plainly, and recommend how to find out.' if thin else '')
    messages = [{'role': 'system', 'content': SYSTEM},
                {'role': 'user', 'content': f'It stopped because {reason}.{note}\n\n' + (f'COMPANY BRIEF: {brief}\n' if brief else '') + context(record)}]
    lora = [{'id': i, 'scale': 0.0} for i in range(adapters)] or None
    try:
        reply = chat(url, messages, 13, 900, schema(record), 0.2, lora=lora)
        data = json.loads(reply['text'])
    except Exception:  # noqa: BLE001  the interim view stands in
        return fallback(record, reason)
    real = {i for i, s in (record.get('sources') or {}).items() if not s.get('simulated')}
    data['evidence_ids'] = [i for i in data.get('evidence_ids') or [] if i in real]
    if data.get('favoured_theory') == 'none':
        data['favoured_theory'] = None
    if not str(data.get('recommendation') or '').strip():
        return fallback(record, reason)
    return {**data, 'draft': True, 'draft_source': 'written after it stopped', 'stopped_because': reason}
