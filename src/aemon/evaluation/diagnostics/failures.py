"""Failure taxonomy for recorded investigations (docs/RECOVERY_EXPERIMENT.md, phase B). Reads records; trains nothing.

Each episode is replayed call by call so progress is measured on the accepted state, then labelled with every failure
type it shows, the earliest observable one, and the termination reason, kept apart:

A repeated source reading   an accepted read of a source already read
B repeated invalid call     a refused call equal to an earlier refused call, or refused as a repeat
C missing prerequisite      refused for order, stage or unread evidence
D simulated-evidence misuse refused because a simulated result was used as evidence
E unproductive persistence  NO_PROGRESS calls in a row without progress in one step
F turn-budget exhaustion    the run hit its turn limit
G invalid conclusion        finish was attempted and refused, and the run did not finish
H context or schema         context full, server refusal, or a reply that was not a valid call

A refusal is not a failure by itself: recovery after a refusal is counted separately.
"""

from __future__ import annotations

import json
from typing import Any

from aemon.agent.recovery import signature
from aemon.environment.stages import current_stage
from aemon.environment.tools import Investigation

NO_PROGRESS = 6
LETTERS = 'ABCDEFGH'
NAMES = {
    'A': 'repeated source reading', 'B': 'repeated invalid call', 'C': 'missing prerequisite', 'D': 'simulated-evidence misuse',
    'E': 'unproductive stage persistence', 'F': 'turn-budget exhaustion', 'G': 'invalid conclusion', 'H': 'context or schema',
}


def _key(call: dict) -> str:
    return call['name'] + json.dumps(call.get('arguments'), sort_keys=True)


def replay_progress(record: dict, case: Any) -> list[dict]:
    """Per recorded call: its index, step, whether it was accepted and whether the accepted state changed."""
    settings = record.get('settings', {})
    run = Investigation(case, settings.get('complete_workflow', False), True, settings.get('quote_marks', False),
                        settings.get('reread_limit'), settings.get('source_dates', False), settings.get('min_assessed', 1), status_check=settings.get('status_check', False))
    out = []
    for i, call in enumerate(record['calls']):
        stage = current_stage(run).name
        before = signature(run)
        result = run.call(call['name'], call.get('arguments') or {})
        out.append({'i': i, 'stage': stage, 'name': call['name'], 'accepted': 'error' not in result,
                    'category': call.get('category'), 'progress': signature(run) != before})
    return out


def classify(record: dict, case: Any) -> dict:
    steps = replay_progress(record, case)
    calls = record['calls']
    events: list[tuple[int, str]] = []
    reads: dict[str, int] = {}
    refused_seen: set[str] = set()
    still, still_stage = 0, None
    for s, call in zip(steps, calls):
        i = s['i']
        if call['name'] == 'read_source' and s['accepted']:
            rid = (call.get('arguments') or {}).get('id')
            reads[rid] = reads.get(rid, 0) + 1
            if reads[rid] >= 2:
                events.append((i, 'A'))
        if not s['accepted']:
            k = _key(call)
            if k in refused_seen or call.get('category') == 'repeat':
                events.append((i, 'B'))
            refused_seen.add(k)
            if call.get('category') in ('order', 'stage', 'unread_evidence'):
                events.append((i, 'C'))
            if call.get('category') == 'synthetic_as_evidence':
                events.append((i, 'D'))
            if call.get('category') is None or call.get('category') == 'arguments' and 'JSON' in str((call.get('result') or {}).get('error', '')):
                events.append((i, 'H'))
            if call['name'] == 'finish' and record.get('final') is None:
                events.append((i, 'G'))
        if s['progress']:
            still, still_stage = 0, None
        else:
            still = still + 1 if still_stage in (None, s['stage']) else 1
            still_stage = s['stage']
            if still == NO_PROGRESS:
                events.append((i - NO_PROGRESS + 1, 'E'))
    stop = record.get('stop_reason')
    if stop == 'turn limit':
        events.append((len(calls), 'F'))
    if stop == 'context limit' or str(stop).startswith('server refused'):
        events.append((len(calls), 'H'))
    events.sort()
    types = sorted({t for _, t in events})
    first = events[0] if events else None
    refusals = [s for s in steps if not s['accepted']]
    recovered = sum(1 for s in refusals if any(x['progress'] for x in steps[s['i'] + 1:s['i'] + 4]))
    return {
        'case': record['case'], 'stop_reason': stop, 'finished': record.get('final') is not None,
        'types': types, 'earliest': first[1] if first else None, 'earliest_index': first[0] if first else None,
        'subsequent': [t for _, t in events[1:] if not first or t != first[1]][:8],
        'calls': len(calls), 'progress_calls': sum(s['progress'] for s in steps), 'refusals': len(refusals),
        'recovered_after_refusal': recovered, 'stage_at_stop': steps[-1]['stage'] if steps else None,
    }
