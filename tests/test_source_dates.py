"""Source dates in the state: opt-in, recorded in the episode settings, so earlier episodes replay unchanged."""

import json

from aemon.agent.records import record_of
from aemon.agent.state_view import state_of
from aemon.environment.cases import load_cases
from aemon.environment.tools import Investigation


def read_one(dated: bool) -> tuple[Investigation, dict]:
    case = next(c for c in load_cases() if c.id == 'hellberg-base')
    run = Investigation(case, staged=False, source_dates=dated)
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'Decide', 'constraints': ['small budget'], 'alternatives': ['enter', 'do not enter']})
    found = run.call('search_evidence', {'query': 'hearing protection consumers'})
    result = run.call('read_source', {'id': found['results'][0]['id']})
    return run, result


def test_dates_are_listed_only_when_asked_and_the_setting_is_recorded():
    plain, result = read_one(False)
    dated, _ = read_one(True)
    plain_state = json.loads(state_of(plain, result).split('\n')[0].removeprefix('Current state: '))
    dated_state = json.loads(state_of(dated, result).split('\n')[0].removeprefix('Current state: '))
    assert 'date' not in plain_state['sources_read'][0] and dated_state['sources_read'][0]['date']
    assert 'source_dates' not in record_of(plain, {})['settings'] and record_of(dated, {})['settings']['source_dates'] is True


def test_more_weighed_sources_can_be_required_before_moving_on():
    from aemon.environment.stages import current_stage

    for need, expected in ((1, 'challenge'), (3, 'assessment')):
        case = next(c for c in load_cases() if c.id == 'hellberg-base')
        run = Investigation(case, staged=True, min_assessed=need)
        run.call('read_brief', {})
        run.call('frame_problem', {'objective': 'Decide', 'constraints': ['small budget'], 'alternatives': ['enter', 'do not enter']})
        hits = run.call('search_evidence', {'query': 'hearing protection consumers comfort'})['results']
        for h in hits[:3]:
            run.call('read_source', {'id': h['id']})
        run.theories = {'T1': {'claim': 'a'}, 'T2': {'claim': 'b'}}
        run.assessments = [{'theory_id': t, 'evidence_id': hits[0]['id'], 'direction': 'neutral'} for t in ('T1', 'T2')]
        assert current_stage(run).name == expected
