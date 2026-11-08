"""AuditKIT over complete investigations, with a full replay through the guarded tools."""

from __future__ import annotations

import json
import statistics
from collections.abc import Sequence
from typing import TYPE_CHECKING

from agenttune.agentic.events import Event, EventKind, EventLog
from auditkit.agent_eval import AgentCase, AgentEvalRunner, AgentEvalSpec, CustomPredicate, episode_from_eventlog

from strategy_agent.common.types import Json
from strategy_agent.env.checks import guards_cleared, run_checks
from strategy_agent.env.tools import Investigation

if TYPE_CHECKING:
    from auditkit.agent_eval import AgentEpisode

    from strategy_agent.env.tools import Case

ALLOWED = [
    'read_brief',
    'frame_problem',
    'search_evidence',
    'challenge_theory',
    'read_source',
    'add_theory',
    'assess_evidence',
    'propose_test',
    'decline_test',
    'state_position',
    'revise_theory',
    'finish',
]


class ReplayMismatch(ValueError):
    pass


def to_eventlog(calls: list[Json], model_only: bool = False) -> EventLog:
    """Replay needs every call. Diagnostics of the model must not credit it with what the harness did."""
    log = EventLog(tier='full')
    for entry in calls:
        if model_only and entry.get('harness'):
            continue
        log.append(Event(EventKind.TOOL_CALL, {'action': {'name': entry['name'], 'arguments': entry['arguments']}}))
        log.append(Event(EventKind.TOOL_RESULT, {'output': json.dumps(entry['result'], sort_keys=True)}))
    log.append(Event(EventKind.TURN_COMPLETE, {}))
    return log


def replay(audited: AgentEpisode, case: Case, **settings: bool) -> Investigation:
    run = Investigation(case, **settings)
    events = [e for e in audited.events if e.type in ('tool_call', 'tool_result')]
    if len(events) % 2:
        raise ReplayMismatch('a call without a result')
    for call, result in zip(events[::2], events[1::2], strict=False):
        if call.type != 'tool_call' or result.type != 'tool_result':
            raise ReplayMismatch('events are out of order')
        actual = run.call(call.payload.get('name'), call.payload.get('arguments'))
        if json.dumps(actual, sort_keys=True) != result.payload.get('output'):
            raise ReplayMismatch(f'{call.payload.get("name")} returned something else')
    return run


def clears_the_guards(audited: AgentEpisode, agent_case: AgentCase) -> bool:
    """Replays the complete log, harness calls included. Guards are necessary, never sufficient."""
    meta = agent_case.metadata
    try:
        return guards_cleared(run_checks(replay(episode_from_eventlog(to_eventlog(meta['calls'])), meta['case'], **meta['settings'])))
    except ReplayMismatch:
        return False


def audit(records: list[Json], cases: Sequence[Case]) -> Json:
    """Replay shows a log is consistent with the tools. It does not show who wrote the calls."""
    by_id = {case.id: case for case in cases}
    mismatches = 0
    for record in records:
        try:
            replay(episode_from_eventlog(to_eventlog(record['calls'])), by_id[record['case']], **record.get('settings', {}))
        except ReplayMismatch:
            mismatches += 1
    check = CustomPredicate(clears_the_guards, version='strategy-v2', name='clears_the_guards')
    agent_cases, episodes = [], []
    for index, record in enumerate(records):
        identifier = f'{record["case"]}/{index}'
        built = episode_from_eventlog(to_eventlog(record['calls'], model_only=True))
        built.case_id = identifier
        agent_cases.append(
            AgentCase(
                id=identifier,
                task='SIMULATED OR PUBLIC-EVIDENCE strategic investigation',
                outcome=check,
                allowed_tools=ALLOWED,
                metadata={'case': by_id[record['case']], 'calls': record['calls'], 'settings': record.get('settings', {})},
            )
        )
        episodes.append(built)
    run = AgentEvalRunner().run(
        AgentEvalSpec(
            cases=agent_cases,
            episodes=episodes,
            mode='recorded',
            name='strategy',
            scorers=['tool_call_validity', 'redundant_tool_calls', 'agent_loop_detection', 'tool_permission'],
        )
    )
    verdicts = [row.outcome.get('verdict') for row in run.rows]

    def mean_of(scorer: str) -> float | None:
        values = [row.diagnostics[scorer]['value'] for row in run.rows if scorer in row.diagnostics and row.diagnostics[scorer].get('value') is not None]
        return statistics.mean(values) if values else None

    return {
        'cases': len(verdicts),
        'replay_mismatches': mismatches,
        'guards_cleared': verdicts.count('success'),
        'guards_not_cleared': verdicts.count('failure'),
        'other': len(verdicts) - verdicts.count('success') - verdicts.count('failure'),
        'known_tool_names': mean_of('tool_call_validity'),
        'redundant_tool_calls': mean_of('redundant_tool_calls'),
        'no_looping': mean_of('agent_loop_detection'),
    }
