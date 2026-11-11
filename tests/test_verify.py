from aemon.agent import loop
from aemon.agent.experimental import verify
from aemon.environment.cases import load_cases
from aemon.environment.tools import Investigation


def _run():
    case = next(c for c in load_cases() if c.id == 'hellberg-base')
    run = Investigation(case)
    run.call('read_brief', {})
    return run


def test_first_finish_is_reviewed_not_executed_then_the_next_is_executed_as_written():
    run = _run()
    seen = []
    real = run.call
    run.call = lambda n, a: (seen.append(n), real(n, a))[1]
    verify.install(run)
    args = {'recommendation': 'Invest 40 million', 'target_customer': 'x', 'value_proposition': 'y', 'uncertainty': 'z',
            'favoured_theory': 'T1', 'evidence_ids': [], 'next_action': 'a', 'would_change_if': ['b'], 'beliefs': {}}
    first = run.call('finish', args)
    assert 'verification' in first and 'error' not in first and seen == []
    assert {'numbers', 'support'} <= set(first['verification_kinds'])
    run.call('finish', args)  # executed: whatever the tools answer, the layer does not intervene twice
    assert seen == ['finish'] and len(run.verification) == 1


def test_runner_is_unchanged_by_import():
    assert verify._PLAY is loop.play
