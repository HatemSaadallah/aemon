"""Blinded judge packets from evaluation runs, in the judge-v1 packet format. NOTHING HERE TRAINS.

Each run record becomes one packet: the case, the sources the agent read with the excerpt the dossier holds, and the
accepted calls in order as events (frame, search, theories, assess, challenge, test, update, position, finish). Refused
calls changed nothing and are left out; identical calls in a row are shown once with a count, so a loop is visible
without filling the packet. A run that stopped early ends with an event that says so, and the judge marks unreached
dimensions not_reached. Revision applies only when the case has a what-if update.

Blinding: a packet carries no arm, model, adapter, prompt or run name. Its id is a hash of its content, packet order is
shuffled with a fixed seed, and the key that maps each id to its arm, case, attempt and source report is written to a
separate file that the judges never see. Judge output never selects or filters training data.

Usage: python -m strategy_agent.evaluation.judge_packets --report ARM=REPORT.json [--report ARM=REPORT.json ...]
           --packets packets.jsonl --key key.jsonl [--seed N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from strategy_agent.common.types import Json
from strategy_agent.env.cases import load_cases

DIMENSIONS = (
    'problem_framing',
    'causal_mechanism',
    'distinct_theories',
    'assumptions_predictions',
    'evidence_judgement',
    'seeking_challenge',
    'experiment_design',
    'revision',
    'recommendation',
)
LIMITS = (
    'Evidence is limited to the case dossier: each source shows everything the dossier holds for it, often a short excerpt, '
    'not the whole original. Results marked simulated are what-if evidence, not real observations.'
)


def _text(value: Any) -> str:
    if isinstance(value, list):
        return '; '.join(_text(v) for v in value)
    if isinstance(value, dict):
        return '; '.join(f'{k}: {_text(v)}' for k, v in value.items())
    return '' if value is None else str(value)


def _event(call: Json) -> tuple[str, str] | None:
    """The action and a plain description of one accepted call, or None for a call shown elsewhere (a read)."""
    a: Json = call['arguments'] if isinstance(call.get('arguments'), dict) else {}
    r: Json = call['result'] if isinstance(call.get('result'), dict) else {}
    name = call['name']
    if name == 'frame_problem':
        return 'frame', f'Objective: {_text(a.get("objective"))}. Constraints: {_text(a.get("constraints"))}. Alternatives: {_text(a.get("alternatives"))}.'
    if name == 'search_evidence':
        found = [str(x.get('id')) for x in r.get('results', []) if isinstance(x, dict)]
        return 'search', f'Searched for "{_text(a.get("query"))}"; found {", ".join(found) if found else "nothing"}.'
    if name == 'challenge_theory':
        found = [str(x.get('id')) for x in r.get('results', []) if isinstance(x, dict)]
        return (
            'challenge',
            f'Looked for evidence against {_text(a.get("theory_id"))}: "{_text(a.get("query"))}"; found {", ".join(found) if found else "nothing"}.',
        )
    if name == 'add_theory':
        return 'theories', (
            f'{_text(r.get("theory_id"))}: {_text(a.get("claim"))} Who benefits: {_text(a.get("who_benefits"))}. Why behaviour changes: '
            f'{_text(a.get("why_behaviour_changes"))}. How value is captured: {_text(a.get("how_value_is_captured"))}. '
            f'Assumptions: {_text(a.get("assumptions"))}. Predictions: {_text(a.get("predictions"))}.'
        )
    if name == 'assess_evidence':
        return 'assess', (
            f'{_text(a.get("theory_id"))} {_text(a.get("direction"))}, from {_text(a.get("evidence_id"))} ({_text(a.get("evidence_kind"))}): '
            f'"{_text(a.get("quote"))}". Does not show: {_text(a.get("does_not_show"))}.'
        )
    if name == 'propose_test':
        return 'test', (
            f'Test "{_text(a.get("name"))}" between {_text(a.get("theories"))}. Method: {_text(a.get("method"))}. Sample: {_text(a.get("sample"))}. '
            f'Measure: {_text(a.get("measure"))}. Predictions: {_text(a.get("prediction_by_theory"))}. Decision rule: {_text(a.get("decision_rule"))}. '
            f'Cost: {_text(a.get("cost_eur"))} euros, {_text(a.get("weeks"))} weeks.'
        )
    if name == 'decline_test':
        return 'test', f'Declined to test: {_text(a.get("reason"))}'
    if name == 'revise_theory':
        return 'update', (
            f'{_text(a.get("theory_id"))} {_text(a.get("status"))}: {_text(a.get("reason"))} New claim: {_text(a.get("new_claim"))}. '
            f'Evidence: {_text(a.get("evidence_ids"))}.'
        )
    if name == 'state_position':
        return 'position', f'Favours {_text(a.get("favoured_theory"))}: {_text(a.get("recommendation"))} Beliefs: {_text(a.get("beliefs"))}.'
    if name == 'finish':
        return 'finish', (
            f'Recommendation: {_text(a.get("recommendation"))} Target customer: {_text(a.get("target_customer"))}. Value proposition: '
            f'{_text(a.get("value_proposition"))}. Favoured theory: {_text(a.get("favoured_theory"))}. Next action: {_text(a.get("next_action"))}. '
            f'Uncertainty: {_text(a.get("uncertainty"))}. Would change if: {_text(a.get("would_change_if"))}. Beliefs: {_text(a.get("beliefs"))}.'
        )
    return None  # read_brief and read_source: the brief is in the case, read sources are listed with their excerpts


def packet_of(record: Json, cases: dict[str, Any]) -> Json:
    case = cases[record['case']]
    events: list[Json] = []
    last: tuple[str, str] | None = None
    for call in record['calls']:
        if not call.get('accepted'):
            continue
        shown = _event(call)
        if shown is None:
            continue
        if shown == last:  # the same call again: counted on the event already shown
            events[-1]['repeats'] = events[-1].get('repeats', 1) + 1
            continue
        events.append({'id': f'A{len(events) + 1}', 'action': shown[0], 'text': shown[1]})
        last = shown
    for e in events:
        if e.get('repeats'):
            e['text'] += f' (made {e.pop("repeats")} times in a row)'
    if record.get('final') is None:
        events.append(
            {
                'id': f'A{len(events) + 1}',
                'action': 'stopped',
                'text': f'The investigation stopped before a recommendation ({_text(record.get("stop_reason")) or "no reason recorded"}).',
            }
        )
    records = dict(case.dossier.records)
    if case.shock is not None:
        records[case.shock.id] = case.shock
    sources = [{'id': i, 'class': records[i].type, 'excerpt': records[i].excerpt} for i in record.get('read', []) if i in records]
    shock = (record.get('coverage') or {}).get('shock') or {}
    packet: Json = {
        'case': {'company': case.company, 'question': case.question, 'source_limits': LIMITS},
        'sources': sources,
        'events': events,
        'scheduled_update': case.shock is not None,
        'update_delivered': bool(shock.get('delivered')),
        'applicable_dimensions': [d for d in DIMENSIONS if d != 'revision' or case.shock is not None],
    }
    packet['packet_id'] = hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()[:16]
    return packet


def build(reports: list[tuple[str, str]], seed: int = 20261106, split: str = 'development') -> tuple[list[Json], list[Json]]:
    cases = {c.id: c for c in load_cases(split=split)}
    packets: dict[str, Json] = {}
    key: list[Json] = []
    for arm, path in reports:
        report = json.loads(Path(path).read_text())
        for record in report['records']:
            p = packet_of(record, cases)
            packets.setdefault(p['packet_id'], p)  # identical runs look identical to a judge: judged once, scored for each
            key.append(
                {
                    'packet_id': p['packet_id'],
                    'arm': arm,
                    'case': record['case'],
                    'company': record['case'].split('-')[0],
                    'attempt': record.get('attempt', 0),
                    'episode': record.get('episode'),
                    'report': str(path),
                    'model': report.get('model'),
                    'finished': record.get('final') is not None,
                }
            )
    order = sorted(packets)
    random.Random(seed).shuffle(order)
    return [packets[i] for i in order], key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', action='append', required=True, help='ARM=path to a runner report')
    parser.add_argument('--packets', required=True)
    parser.add_argument('--key', required=True)
    parser.add_argument('--seed', type=int, default=20261106)
    parser.add_argument('--split', choices=('development', 'heldout'), default='development')
    args = parser.parse_args()
    pairs = [tuple(x.split('=', 1)) for x in args.report]
    packets, key = build([(a, p) for a, p in pairs], args.seed, args.split)
    for path in (args.packets, args.key):
        if Path(path).exists():
            raise SystemExit(f'{path} exists; packets and keys are never overwritten')
    Path(args.packets).write_text(''.join(json.dumps(p) + '\n' for p in packets))
    Path(args.key).write_text(''.join(json.dumps(k) + '\n' for k in key))
    print(json.dumps({'packets': len(packets), 'runs': len(key), 'runs_by_arm': {a: sum(k['arm'] == a for k in key) for a, _ in pairs}}))


if __name__ == '__main__':
    main()
