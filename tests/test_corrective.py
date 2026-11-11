"""Corrective states (pipeline/corrective.py) come only from training cases, and the student's own wrong call never passes."""

import json
from pathlib import Path

import pytest

from aemon.environment.cases import load_cases
from aemon.teacher import corrective
from aemon.data.splits import is_validation

STATES = Path(__file__).resolve().parents[1] / 'experiments' / 'v2_corrective' / 'all_states.json'


@pytest.mark.skipif(not STATES.exists(), reason='states not built')
def test_states_hold_no_development_or_frozen_case_and_the_student_call_fails_its_gate():
    frozen = {c.id for c in load_cases(split='heldout')} | {c.id for c in load_cases(split='heldout2')}
    states = json.loads(STATES.read_text())
    assert states and not any(s['case'] in frozen or is_validation(s['case']) for s in states)
    for s in [x for x in states if x['skill'] == 'classify'][:10]:  # the student labelled these kinds wrongly
        a = s['student_call']['arguments']
        why = f"Weighing {a['evidence_id']} for {a['theory_id']}"
        reply = json.dumps({'learned': why, 'uncertain': why, 'why_next': why, 'call': {'name': 'assess_evidence', 'arguments': a}})
        assert corrective.gate(s, reply)[0] is None
