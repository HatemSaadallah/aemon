import json

from aemon.agent.experimental import grounded
from aemon.agent import tool_schemas
from aemon.environment.cases import load_cases
from aemon.environment.tools import Investigation

RUNS = 'experiments/verify/ver1_control_adapter.json'


def _at(name):
    cases = {c.id: c for c in load_cases()}
    for r in json.load(open(RUNS))['records']:
        idx = next((i for i, c in enumerate(r['calls']) if c['name'] == name and c['accepted']), None)
        if idx is None:
            continue
        run = Investigation(cases[r['case']], **{k: v for k, v in r['settings'].items() if k != 'recovery'})
        for c in r['calls'][:idx]:
            run.call(c['name'], c['arguments'])
        if grounded.supported(run) and set(grounded.supported(run)) != set(run.theories):
            return run
    raise AssertionError('no state with a partly supported set of theories')


def test_position_offers_only_supported_theories_and_runner_default_is_unchanged():
    run = _at('state_position')
    original = tool_schemas._narrow('state_position', run)['properties']['arguments']['properties']['favoured_theory']['enum']
    narrowed = grounded.narrow('state_position', run)['properties']['arguments']['properties']['favoured_theory']['enum']
    assert set(narrowed) == set(grounded.supported(run)) < set(original)
    assert tool_schemas._narrow is grounded._NARROW  # importing the module does not patch the runner
