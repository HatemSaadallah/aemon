import json
from unittest import mock

from aemon.teacher import corrective, experiment_design as ed

STATES = 'experiments/v2_corrective/pilot3_states.json'


def _state():
    return next(s for s in json.load(open(STATES)) if s['skill'] == 'experiment')


def _raw(state, long=False):
    from aemon.environment.cases import load_cases
    from aemon.teacher import corrections as c
    run, _ = c._replay(state['record'], {x.id: x for x in load_cases()}[state['case']], len(state['record']['model_turns']))
    ts = sorted(run.theories)
    return {'learned': 'x' * (900 if long else 50), 'uncertain': 'u', 'why_next': f'separates {ts[0]} from {ts[1]}', 'decision': {'design': {
        'name': 'n', 'theories': ts[:2], 'target_customers': 'a', 'treatment': 'b', 'control': 'c', 'recruitment': '200 people', 'outcome': 'o',
        'prediction_by_theory': {k: f'p{k}' for k in ts}, 'threshold': '30%', 'next_step_by_result': 'pilot', 'cost_eur': 1000, 'weeks': 4}}}


def test_compose_and_limits():
    s = _state()
    a = ed.compose(_raw(s))
    assert a['call']['name'] == 'propose_test' and a['call']['arguments']['method'].startswith('Target customers: a')
    assert not ed.over_limits(a) and 'learned' in ed.over_limits(ed.compose(_raw(s, long=True)))


def test_one_shortening_turn_then_provenance(tmp_path):
    s, manifest = _state(), tmp_path / 'm.jsonl'
    replies = iter([json.dumps(_raw(s, long=True)), json.dumps(_raw(s))])
    with mock.patch.object(ed, 'chat', side_effect=lambda *a, **k: {'text': next(replies)}):
        [item] = ed.ask([s], 'http://x', 'w', str(manifest))
    assert item['shortened'] and ed.verify(item, str(manifest))
    item['reply'] = item['reply'].replace('pilot', 'launch')  # an edited reply no longer verifies
    assert not ed.verify(item, str(manifest))
    assert corrective.CALLS['experiment'] == ('propose_test', 'decline_test')
