"""The experimental recovery controller (docs/RECOVERY_EXPERIMENT.md): isolation, guards, masking and replay."""

import json
from pathlib import Path

import pytest

from aemon.agent import recovery
from aemon.agent.loop import play
from aemon.agent.records import record_of
from aemon.agent.tool_schemas import TOOL_SCHEMA, schema_for
from aemon.common.constants.prompts import PROMPTS
from aemon.environment.cases import load_cases
from aemon.environment.stages import current_stage
from aemon.environment.tools import Investigation

BENCH = Path(__file__).resolve().parents[1] / 'experiments' / 'recovery' / 'benchmark_v1.json'


def case(cid='hellberg-new-evidence-looks'):
    return next(c for c in load_cases() if c.id == cid)


def started(features=(), cid='hellberg-new-evidence-looks'):
    run = Investigation(case(cid), staged=True, quote_marks=True)
    run.recovery = frozenset(features)
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'Decide', 'constraints': ['small budget'], 'alternatives': ['enter', 'do not enter']})
    hits = run.call('search_evidence', {'query': 'hearing protection comfort wearers'})['results']
    return run, [h['id'] for h in hits]


def tools_of(schema):
    return {t['properties']['name']['const']: t for t in schema['anyOf']}


def test_with_recovery_off_the_schema_is_unchanged():
    a, _ = started()
    b, _ = started()
    del b.recovery  # an Investigation made by older code has no attribute at all
    assert json.dumps(schema_for(a), sort_keys=True) == json.dumps(schema_for(b), sort_keys=True)


def test_masking_prefers_unread_sources_and_keeps_read_text_in_state():
    run, ids = started(('mask_rereads',))
    run.call('read_source', {'id': ids[0]})
    run.call('read_source', {'id': ids[1]})
    run.call('read_source', {'id': ids[2]})
    run.theories = {'T1': {'claim': 'a'}, 'T2': {'claim': 'b'}}  # theories step reached
    offered = tools_of(schema_for(run)).get('read_source')
    unread = [i for i in run.surfaced if i not in run.read]
    if unread:
        assert set(offered['properties']['arguments']['properties']['id']['enum']) == set(unread)
    else:
        assert offered is None
    assert set(ids[:3]) <= run.read  # read text is not removed from the state


def test_citations_mask_keeps_simulated_results_out_of_finish_but_not_out_of_revision():
    run, ids = started(('citations',))
    for i in ids[:3]:
        run.call('read_source', {'id': i})
    run.shock_delivered = True  # as after state_position
    run.read.add(run.case.shock.id)
    run.theories = {'T1': {'claim': 'a'}, 'T2': {'claim': 'b'}}
    from aemon.agent.tool_schemas import _narrow
    fin = _narrow('finish', run)['properties']['arguments']['properties']['evidence_ids']['items']['enum']
    rev = _narrow('revise_theory', run)['properties']['arguments']['properties']['evidence_ids']['items']['enum']
    assert run.case.shock.id not in fin and run.case.shock.id in rev


def test_guards_still_refuse_with_every_feature_on():
    run, ids = started(recovery.FEATURES)
    result = run.call('read_source', {'id': 'not-a-real-source'})
    assert 'error' in result and run.calls[-1]['category'] == 'fabricated'
    result = run.call('assess_evidence', {'theory_id': 'T9', 'evidence_id': ids[0], 'direction': 'supports', 'quote': 'x', 'evidence_kind': 'market_fact', 'does_not_show': 'y'})
    assert 'error' in result


def test_withdrawn_tools_are_never_required_ones_and_never_outside_the_stage():
    run, _ = started(recovery.FEATURES)
    run.turns_left = 1  # as tight as it gets
    offered = set(tools_of(schema_for(run)))
    assert offered and offered <= set(current_stage(run).tools)
    assert offered & {'search_evidence', 'read_source'}  # the evidence step still has what it needs


def test_minimum_actions_falls_as_requirements_are_met():
    run, ids = started()
    before = recovery.min_actions(run)
    run.call('read_source', {'id': ids[0]})
    assert recovery.min_actions(run) == before - 1


def test_unknown_features_are_refused_and_features_are_recorded():
    with pytest.raises(ValueError):
        play(case(), lambda *a, **k: {'text': ''}, PROMPTS['compact'], 1, 4, 100, True, TOOL_SCHEMA, staged=True, recovery_features=('magic',))
    turns = iter(['{"name": "read_brief", "arguments": {}}'] * 3)
    run, info = play(case(), lambda *a, **k: {'text': next(turns)}, PROMPTS['compact'], 2, 4, 100, True, TOOL_SCHEMA, staged=True,
                     compact=True, recovery_features=('progress', 'budget'))
    assert record_of(run, info)['settings']['recovery'] == ['budget', 'progress']


def test_recovery_notes_name_only_what_the_state_holds():
    run, ids = started(('progress',))
    run.call('search_evidence', {'query': 'hearing protection comfort wearers'})  # refused as a repeat
    schema = schema_for(run)
    note = recovery.refusal_note(run, run.calls[-1], schema)
    assert note['category'] == 'repeat' and set(note['actions_that_can_succeed_now']) <= set(current_stage(run).tools)
    text = recovery.recovery_note(run, run.calls[-3:], schema)
    hidden = [r for r in run.case.dossier.records if r not in run.surfaced]
    assert not any(h in text for h in hidden)


@pytest.mark.skipif(not BENCH.exists(), reason='benchmark not built')
def test_every_checkpoint_restores_exactly_and_holds_no_test_case():
    bench = json.loads(BENCH.read_text())
    frozen = {c.id for c in load_cases(split='heldout')} | {c.id for c in load_cases(split='heldout2')}
    cases = {c.id: c for c in load_cases()}
    from aemon.agent.backends.llama_client import parse_call
    for cp in bench['checkpoints']:
        assert cp['case'] not in frozen and cp['case'] in cases
        run = Investigation(cases[cp['case']], cp['settings'].get('complete_workflow', False), True, cp['settings'].get('quote_marks', False))
        for turn in cp['prefix']:
            call, problem = parse_call(turn['text'], True)
            result = run.call(call['name'], call['arguments']) if call else {'error': problem}
            assert json.dumps(result, sort_keys=True) == json.dumps(turn['tool_result'], sort_keys=True)
        assert cp['turns_left'] == 45 - len(cp['prefix']) and cp['turns_left'] > 0
