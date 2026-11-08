"""AuditKIT checks for our domain metric and the AgentTune bridge. SIMULATED ONLY.

Records the results in check_bridge.json. Exits non-zero if behaviour changes.
"""
import json
from pathlib import Path

from agenttune.agentic import DictToolHarness, Project, ReActStrategy
from auditkit.agent_eval import AgentCase, AgentEpisode, CustomPredicate, episode_from_eventlog


def within_regret(episode, case):
    return episode.final_state.get('bayes_regret', float('inf')) <= case.metadata['max_regret']


def finish_arguments(episode):
    """The agent's decision when it ends with a `finish` tool call."""
    calls = [e.payload for e in episode.events if e.type == 'tool_call' and e.payload.get('name') == 'finish']
    return calls[-1].get('arguments', {}) if calls else {}


def main():
    regret = CustomPredicate(within_regret, version='regret-v1', name='within_regret')
    case = AgentCase(id='sim-regret', task='SIMULATED launch decision', outcome=regret,
                     metadata={'max_regret': 0.1})
    verdicts = {name: regret.evaluate(AgentEpisode(events=[], final_state={'bayes_regret': value},
                                                   case_id='sim-regret'), case).verdict
                for name, value in [('low_regret', 0.02), ('high_regret', 1.4)]}

    harness = DictToolHarness({'run_study': lambda name: {'simulated': True, 'positive': True}}, max_steps=4)
    strategy = ReActStrategy(lambda s: {'name': 'run_study', 'arguments': {'name': 'market_trial'}}
                             if s.step == 0 else {'name': 'finish', 'arguments': {'answer': 'launch'}})
    episode = episode_from_eventlog(Project(strategy=strategy, harness=harness).infer('SIMULATED launch decision'))
    naive = CustomPredicate(lambda e, c: 'launch' in str(e.final_answer), version='naive-v1', name='naive')
    correct = CustomPredicate(lambda e, c: finish_arguments(e).get('answer') == 'launch',
                              version='finish-v1', name='finish_call')
    bridge = AgentCase(id='sim-bridge', task='SIMULATED launch decision', outcome=correct)
    out = {'simulated': True, 'custom_predicate': verdicts, 'events': len(episode.events),
           'coverage': episode.coverage_label(), 'final_answer': episode.final_answer,
           'predicate_on_final_answer': naive.evaluate(episode, bridge).verdict,
           'predicate_on_finish_call': correct.evaluate(episode, bridge).verdict}
    Path(__file__).with_name('check_bridge.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out))
    expected = verdicts == {'low_regret': 'success', 'high_regret': 'failure'} \
        and out['predicate_on_finish_call'] == 'success' and out['predicate_on_final_answer'] == 'failure'
    if not expected:
        raise SystemExit('FAILED: behaviour differs from what TOOLING.md records')


if __name__ == '__main__':
    main()
