"""Follow-up questions on a finished investigation, answered from that investigation's record only.

The answer is written by the local Tiny Aya Global model (the base model: the fine-tuned adapter was trained on tool
calls, not on conversation). It sees the record (question, framing, explanations, assessed quotes, test, recommendation)
and the sources' excerpts, the person's memory notes, and the earlier follow-ups. It must cite source ids; any id that
is not in the record is dropped, and an answer the record cannot support says so.
"""

from __future__ import annotations

import json
from typing import Any

Json = dict[str, Any]

SYSTEM = (
    'You answer a manager\'s follow-up question about a strategy investigation that has finished. Use ONLY the '
    'investigation below and the source excerpts in it. Write plain, short English for a non-technical reader: two to '
    'six sentences, numbers where the record has them. Cite the sources you rely on by id in "sources". If the '
    'investigation does not contain the answer, say so plainly and say what evidence would be needed; never invent '
    'facts, figures or sources. Notes the manager asked you to remember are context about them, not evidence.'
)


def _clip(text: Any, n: int) -> str:
    text = str(text or '')
    return text if len(text) <= n else text[: n - 1].rstrip() + '…'


def context(record: Json) -> str:
    final = record.get('final') or {}
    lines = [f"QUESTION: {record.get('question', '')}"]
    frame = record.get('frame') or {}
    if frame:
        lines.append(f"OBJECTIVE: {_clip(frame.get('objective'), 300)}")
        lines.append('ALTERNATIVES: ' + '; '.join(_clip(a, 120) for a in frame.get('alternatives') or []))
    position = (record.get('position') or {}).get('beliefs') or {}
    for tid, t in (record.get('theories') or {}).items():
        lines.append(f"EXPLANATION {tid} (belief: {position.get(tid, 'not stated')}): {_clip(t.get('claim'), 300)}")
    for a in (record.get('assessments') or [])[:14]:
        lines.append(f"ASSESSED [{a.get('evidence_id')}] for {a.get('theory_id')}: {a.get('direction')}. Quote: \"{_clip(a.get('quote'), 220)}\". Does not show: {_clip(a.get('does_not_show'), 160)}")
    for test in (record.get('tests') or {}).values():
        lines.append(
            f"TEST: {_clip(test.get('name'), 120)}. Method: {_clip(test.get('method'), 300)} Sample: {_clip(test.get('sample'), 200)} "
            f"Cost EUR {test.get('cost_eur')}, {test.get('weeks')} weeks. Decision rule: {_clip(test.get('decision_rule'), 400)}"
        )
        for tid, p in (test.get('prediction_by_theory') or {}).items():
            lines.append(f'PREDICTION {tid}: {_clip(p, 200)}')
    if record.get('test_declined'):
        lines.append(f"TEST DECLINED: {_clip((record['test_declined'] or {}).get('reason'), 300)}")
    for r in record.get('revisions') or []:
        lines.append(f"REVISION {r.get('theory_id')} ({r.get('status')}): {_clip(r.get('reason'), 250)}")
    if final:
        lines.append(f"RECOMMENDATION: {_clip(final.get('recommendation'), 400)}")
        lines.append(f"NEXT ACTION: {_clip(final.get('next_action'), 240)}")
        lines.append(f"UNCERTAINTY: {_clip(final.get('uncertainty'), 240)}")
        lines.append('WOULD CHANGE IF: ' + '; '.join(_clip(w, 200) for w in final.get('would_change_if') or []))
    else:
        lines.append('The investigation stopped before a recommendation.')
    for sid, s in (record.get('sources') or {}).items():
        kind = 'SIMULATED what-if, not real evidence' if s.get('simulated') else s.get('class')
        lines.append(f"SOURCE [{sid}] {_clip(s.get('title'), 100)} ({s.get('date')}, {kind}): {_clip(s.get('excerpt'), 300)}")
    return '\n'.join(lines)


def schema(record: Json) -> Json:
    ids = sorted((record.get('sources') or {}).keys()) or ['none']
    return {
        'type': 'object',
        'additionalProperties': False,
        'required': ['answer', 'sources', 'answered_from_record'],
        'properties': {
            'answer': {'type': 'string', 'maxLength': 1200},
            'sources': {'type': 'array', 'items': {'enum': ids}, 'maxItems': 6},
            'answered_from_record': {'type': 'boolean'},
        },
    }


def messages(record: Json, question: str, notes: list[str], earlier: list[Json]) -> list[Json]:
    user = [context(record)]
    if notes:
        user.append('NOTES THE MANAGER ASKED YOU TO REMEMBER (context, not evidence):\n' + '\n'.join(f'- {_clip(n, 300)}' for n in notes))
    for f in earlier[-4:]:
        if f.get('answer'):
            user.append(f"EARLIER QUESTION: {_clip(f['question'], 300)}\nEARLIER ANSWER: {_clip(f['answer'], 600)}")
    user.append(f'FOLLOW-UP QUESTION: {question}')
    return [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': '\n\n'.join(user)}]


def answer(chat, url: str, record: Json, question: str, notes: list[str], earlier: list[Json], adapters: int) -> tuple[str, list[str], str]:  # noqa: ANN001
    """Returns (answer, cited source ids that exist in the record, status). Every loaded adapter is set to 0 by name:
    left unset, the server would apply them."""
    lora = [{'id': i, 'scale': 0.0} for i in range(adapters)] or None
    reply = chat(url, messages(record, question, notes, earlier), 7, 700, schema(record), 0.2, lora=lora)
    try:
        data = json.loads(reply['text'])
    except (json.JSONDecodeError, TypeError):
        return 'I could not form an answer to that. Try asking it another way.', [], 'failed'
    known = set((record.get('sources') or {}).keys())
    cited = [s for s in dict.fromkeys(data.get('sources') or []) if s in known]
    text = str(data.get('answer') or '').strip() or 'The investigation does not contain an answer to that.'
    return text, cited, 'answered' if data.get('answered_from_record', True) else 'not_in_record'
