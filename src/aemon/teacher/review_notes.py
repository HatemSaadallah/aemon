"""What the Review page shows beside a corrective example: the student's own action at that state, why it was wrong
(the same checks run on the student's call), and automated notes on the correction's substance. Advisory: the notes
select nothing, and which examples train is the reviewer's decision.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aemon.common.types import Json
from aemon.environment.checks import experiment, no_invented_numbers
from aemon.teacher import corrections as c
from aemon.teacher import targeted as t

STATE_FILES = ('experiments/v2_corrective/all_states.json', 'experiments/v2_corrective/all_states_v3.json')
THEORY_STEP = re.compile(r'\b(add (?:a |the )?(?:\w+ )?theor|formulate|new theory)', re.I)
READ_STEP = re.compile(r'\bread(?:ing)?\b', re.I)


def student_calls(root: Path) -> dict[tuple[str, int, str], Json]:
    found = {}
    for name in STATE_FILES:
        path = root / name
        if path.exists():
            for s in json.loads(path.read_text()):
                found[(s['student_run'], s['turn'], s['skill'])] = s.get('student_call')
    return found


def _short(call: Json | None) -> Json | None:
    if not call:
        return None
    args = {k: (v[:300] + '…' if isinstance(v, str) and len(v) > 300 else v) for k, v in (call.get('arguments') or {}).items()}
    return {'name': call.get('name'), 'arguments': args, 'accepted': call.get('accepted'), 'category': call.get('category')}


def why_wrong(skill: str, run: Any, record: Json, case: Any, student: Json | None) -> str:
    if not student:
        return 'student call not on record'
    name, args = student.get('name'), student.get('arguments') or {}
    if skill == 'unstick':
        refusals = [m.get('tool_result', '') for m in record['model_turns'][-2:]]
        return f'after two refusals the student made {name}; last refusal: ' + str(refusals[-1])[:240] if refusals else f'student made {name}'
    if skill == 'classify':
        kind = run._source(args.get('evidence_id')).kind if args.get('evidence_id') in run.read else None
        return f"labelled {args.get('evidence_id')} as {args.get('evidence_kind')}; the annotation (v1) says {kind}"
    after, _ = c._replay(record, case, len(record['model_turns']))
    result = after.call(name, args)
    if 'error' in result:
        return f'the tools refused it: {result["error"][:200]}'
    if skill == 'numbers':
        ok, detail = no_invented_numbers(after) if after.final else (None, 'not accepted')
        padding = t.gate_finish(after, args) if after.final else ''
        return '; '.join(x for x in ((detail if ok is False else ''), padding) if x) or 'passes the finish checks (the correction must be better on substance)'
    if skill == 'experiment':
        if name == 'propose_test' and not case.test_warranted:
            return 'proposed a test where the case does not warrant one'
        if name == 'decline_test' and case.test_warranted:
            return 'declined a test this case warrants'
        screens = t.gate_mechanism(after, args) if name == 'propose_test' else ''
        ok, detail = experiment(after)
        return '; '.join(x for x in (screens, detail if ok is False else '') if x) or 'passes the experiment checks (the correction must be better on substance)'
    if skill == 'revise':
        return "the student's own call already passes this family's gate: likely teaches little"
    return ''


def quality_notes(skill: str, run: Any, call: Json, justification: Json, student: Json | None) -> list[str]:
    notes, args = [], call.get('arguments') or {}
    if student and student.get('name') == call.get('name') and json.dumps(student.get('arguments'), sort_keys=True) == json.dumps(args, sort_keys=True):
        notes.append('identical to the student call: teaches nothing')
    if skill == 'numbers':
        plan = ' '.join((args.get('next_action', ''), *args.get('would_change_if', [])))
        for key, test in run.tests.items():
            if key in plan and t.gate_mechanism(run, test):
                notes.append(f'the next action runs {key}, an earlier test that fails a design screen ({t.gate_mechanism(run, test)[:70]})')
    if skill == 'unstick':
        why = justification.get('why_next', '')
        if call.get('name') == 'read_source' and THEORY_STEP.search(why) and not READ_STEP.search(why):
            notes.append('why_next says to add a theory but the call reads a source')
        if call.get('name') == 'add_theory' and READ_STEP.search(why) and not THEORY_STEP.search(why):
            notes.append('why_next says to read but the call adds a theory')
        if student and student.get('name') == call.get('name'):
            notes.append(f'same tool as the student ({call.get("name")}), different arguments: check the progress is real')
    if skill == 'experiment' and call.get('name') == 'propose_test':
        screen = t.gate_mechanism(run, args)
        if screen:
            notes.append(screen)
    return notes
