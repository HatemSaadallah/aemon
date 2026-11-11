"""What a finished investigation leaves behind: its record, the summary over many records, and the identities
(protocol, suite, model) that decide which runs may be compared.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aemon.agent.backends.llama_client import headers
from aemon.common.types import Json
from aemon.environment.checks import coverage, guards_cleared, rejected_categories, run_checks
from aemon.environment.stages import current_stage

if TYPE_CHECKING:
    from aemon.environment.tools import Case, Investigation


STAGES = (
    'read_brief',
    'frame_problem',
    'company_status',
    'search_evidence',
    'read_source',
    'add_theory',
    'assess_evidence',
    'challenge_theory',
    'propose_test',
    'decline_test',
    'state_position',
    'revise_theory',
    'finish',
)


def recovered_after_refusal(run: Investigation) -> int:
    """Refused, then the model got the same tool right on its next call. The harness repaired nothing."""
    return sum(not a['accepted'] and b['accepted'] and a['name'] == b['name'] for a, b in zip(run.calls, run.calls[1:], strict=False))


def stopping_point(run: Investigation) -> Json:
    done = [c['name'] for c in run.calls if c['accepted']]
    rejected = rejected_categories(run)
    return {
        'furthest_stage': max(done, key=STAGES.index) if done else None,
        'calls': len(run.calls),
        'most_common_rejection': max(rejected, key=lambda category: rejected[category]) if rejected else None,
        'stage_at_stop': current_stage(run).name if run.staged else None,
        'rejected_finishes': sum(c['name'] == 'finish' and not c['accepted'] for c in run.calls),
        'harness_actions': sum(bool(c.get('harness')) for c in run.calls),
        'refused': sum(not c['accepted'] for c in run.calls),
        'recovered_after_refusal': recovered_after_refusal(run),
    }


def record_of(run: Investigation, info: Json | None = None) -> Json:
    return {
        'stopping_point': stopping_point(run),
        'challenge_searches': run.challenge_searches,
        'case': run.case.id,
        'company': run.case.company,
        'simulated_case': run.case.simulated,
        'checks': run_checks(run),
        'rejections': rejected_categories(run),
        'settings': {'complete_workflow': run.complete_workflow, 'staged': run.staged, 'quote_marks': run.quote_marks}
        | ({'reread_limit': run.reread_limit} if run.reread_limit is not None else {})
        | ({'source_dates': True} if getattr(run, 'source_dates', False) else {})
        | ({'status_check': True} if getattr(run, 'status_check', False) else {})
        | ({'stuck_help': True} if getattr(run, 'stuck_help', False) else {})
        | ({'min_assessed': run.min_assessed} if getattr(run, 'min_assessed', 1) != 1 else {})
        | ({'recovery': sorted(run.recovery)} if getattr(run, 'recovery', None) else {}),
        'coverage': coverage(run),
        'position': run.position,
        'test_declined': run.test_declined,
        'frame': run.frame,
        'theories': run.theories,
        'assessments': run.assessments,
        'tests': run.tests,
        'revisions': run.revisions,
        'final': run.final,
        'searches': run.searches,
        'read': sorted(run.read),
        'calls': run.calls,
        'stop_reason': (info or {}).get('stop_reason'),
        'model_turns': (info or {}).get('turns', []),
    }


def summary(records: list[Json]) -> Json:
    names = list(records[0]['checks']) if records else []
    table = {}
    for name in names:
        reached = [r for r in records if r['checks'][name]['status'] in ('passed', 'failed')]
        table[name] = {
            'passed': sum(r['checks'][name]['status'] == 'passed' for r in reached),
            'reached': len(reached),
            'applied': sum(r['checks'][name]['status'] != 'not_applicable' for r in records),
            'of_all': len(records),
        }
    whole = [guards_cleared(r['checks']) for r in records]
    shocked = [r['coverage']['shock'] for r in records if r['coverage']['shock']]
    shock = {
        'cases': len(shocked),
        'delivered': sum(s['delivered'] for s in shocked),
        'read': sum(s['read'] for s in shocked),
        'held_affected_theory': sum(bool(s['affected_theories']) for s in shocked),
        'addressed_an_affected_theory': sum(bool(s['affected_addressed']) for s in shocked),
        'bore_on_favoured': sum(s['bears_on_favoured'] for s in shocked),
        'cited_in_revision': sum(s['cited_in_revision'] for s in shocked),
        'favoured_changed': sum(s['favoured_changed'] for s in shocked),
    }
    stops, furthest = {}, {}
    for record in records:
        stops[record['stop_reason']] = stops.get(record['stop_reason'], 0) + 1
        place = record['stopping_point']['furthest_stage']
        furthest[place] = furthest.get(place, 0) + 1
    rejections = {}
    for record in records:
        for key, value in record['rejections'].items():
            rejections[key] = rejections.get(key, 0) + value
    return {
        'episodes': len(records),
        'finished': sum(r['final'] is not None for r in records),
        'end_to_end_success': sum(whole),
        'stop_reasons': stops,
        'furthest_stage': furthest,
        'checks': table,
        'rejections': rejections,
        'shock_coverage': shock,
        'supporting_evidence_attempted': sum(r['coverage']['supporting_evidence_assessed'] > 0 for r in records),
        'rejected_finishes': sum(r['stopping_point']['rejected_finishes'] for r in records),
        'harness_actions': sum(r['stopping_point']['harness_actions'] for r in records),
        'refused_calls': sum(r['stopping_point']['refused'] for r in records),
        'recovered_after_refusal': sum(r['stopping_point']['recovered_after_refusal'] for r in records),
        'harness_corrections': 0,
        'resources': {
            key: round(sum(t.get(key, 0) for r in records for t in r['model_turns']), 3) for key in ('prompt_tokens', 'completion_tokens', 'seconds', 'usd')
        },
        'mean_calls': sum(len(r['calls']) for r in records) / (len(records) or 1),
    }


def _digest(data: object) -> str:
    return hashlib.sha256(data if type(data) is bytes else json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]


AGENT_MODULES = ('loop', 'tool_schemas', 'state_view', 'adapter_routing', 'records', 'run_investigations')


def protocol_of(system: str, generation: Json) -> Json:
    """Code, prompt and generation settings. A base and a fine-tuned arm must share this."""
    from aemon.common.paths import DOSSIER

    package = Path(__file__).resolve().parents[1]
    files = {
        'controller': package / 'environment/stages.py',
        'tools': package / 'environment/tools.py',
        'checks': package / 'environment/checks.py',
        'constants': package / 'common/constants/env.py',
        'prompts': package / 'common/constants/prompts.py',
        'evidence': DOSSIER / 'evidence.json',
        'cases': DOSSIER / 'cases.json',
    }
    parts = {name: _digest(path.read_bytes()) for name, path in files.items()}
    # the agent loop and everything it shows the model (runner.py until the aemon layout split it into these modules)
    loop = b''.join((package / 'agent' / f'{name}.py').read_bytes() for name in AGENT_MODULES)
    parts.update(runner=_digest(loop), chat=_digest((package / 'agent/backends/llama_client.py').read_bytes()), system_prompt=_digest(system),
                 generation=_digest(generation))
    return {'id': _digest(parts), 'parts': parts, 'generation': generation}


def suite_of(cases: Sequence[Case], attempts: int) -> Json:
    """The ordered cases and attempts, so two runs on different cases can never look matched."""
    items = [[c.id, _digest([c.question, c.brief, c.shock.excerpt if c.shock else None, c.shock_direction, c.test_warranted])] for c in cases]
    return {'id': _digest([items, attempts]), 'cases': [c.id for c in cases], 'attempts': attempts}


def model_of(backend: str, name: str, weights_sha256: str | None = None, props: Json | None = None, generation: Json | None = None) -> Json:
    """What actually ran. A label alone proves nothing, so the weights hash, server details and the generation settings
    the server was started with (reasoning budget, context, slots, which the server does not report) go in."""
    props = props or {}
    info = {
        'backend': backend,
        'name': name,
        'weights_sha256': weights_sha256,
        'build': props.get('build_info'),
        'template': _digest(str(props.get('chat_template', ''))),
        'file': Path(str(props.get('model_path', ''))).name,
        'slots': props.get('total_slots'),
        'generation': generation or {},
    }
    return {**info, 'id': _digest(info)}


def matched(a: Json, b: Json) -> Any:
    """Only runs that share a protocol and suite, on different models, may be compared as an effect of the model."""
    return a['protocol']['id'] == b['protocol']['id'] and a['suite']['id'] == b['suite']['id'] and a['model']['id'] != b['model']['id']


def server_props(url: str) -> Any:
    with urllib.request.urlopen(urllib.request.Request(url + '/props', headers=headers()), timeout=30) as response:
        return json.load(response)
