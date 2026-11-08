"""The numbers behind an investigation, for its charts, its report and its follow-up answers.

Everything here is counted or read from the investigation's own record: nothing is estimated or invented. Beliefs are
the agent's own five-step judgement, not probabilities, and are labelled so wherever they are shown.
"""

from __future__ import annotations

import re
from typing import Any

from strategy_agent.common.constants.env import BELIEFS

Json = dict[str, Any]

# Plain words for the source classes, for people who are not analysts
SOURCE_KIND = {
    'verified_observation': 'Independent source',
    'company_claim': "Company's own claim",
    'analyst_assumption': 'Analyst assumption',
    'proposed_hypothesis': 'Hypothesis',
    'synthetic': 'Simulated what-if',
    'web_page': 'Web page (unchecked)',
}
STEP_GROUP = {  # the controller's stages, in the words a manager would use
    'brief': 'Understanding the question', 'frame': 'Understanding the question',
    'evidence': 'Gathering evidence', 'theories': 'Explaining why customers would buy',
    'assessment': 'Weighing evidence', 'challenge': 'Challenging the favourite', 'challenge_reading': 'Challenging the favourite',
    'test': 'Designing a test', 'position': 'Taking a position', 'new_evidence': 'Reacting to new evidence',
    'update': 'Reacting to new evidence', 'conclude': 'Recommendation',
}


def _number(text: str) -> int | None:
    found = re.search(r'\b(\d{1,3}(?:[,  ]\d{3})+|\d+)\b', text or '')
    return int(re.sub(r'\D', '', found.group(1))) if found else None


def beliefs(record: Json) -> list[Json]:
    """Each explanation's belief when the agent took its position, and after new evidence if any arrived."""
    position = (record.get('position') or {}).get('beliefs') or {}
    shock = (record.get('coverage') or {}).get('shock') or {}
    after = shock.get('beliefs_after') or {}
    favoured = (record.get('final') or {}).get('favoured_theory') or (record.get('position') or {}).get('favoured_theory')
    out = []
    for tid, theory in (record.get('theories') or {}).items():
        before = position.get(tid)
        later = after.get(tid) if shock.get('delivered') else None
        out.append({
            'id': tid,
            'claim': theory.get('claim', ''),
            'before': before,
            'after': later,
            'before_step': BELIEFS.index(before) if before in BELIEFS else None,
            'after_step': BELIEFS.index(later) if later in BELIEFS else None,
            'favoured': tid == favoured,
        })
    return out


def evidence(record: Json) -> list[Json]:
    """For each explanation: how many assessed sources support it, contradict it or are neutral, by kind of source."""
    sources = record.get('sources') or {}
    rows = {tid: {'id': tid, 'supports': 0, 'contradicts': 0, 'neutral': 0, 'independent_supports': 0, 'independent_contradicts': 0}
            for tid in (record.get('theories') or {})}
    for a in record.get('assessments') or []:
        row = rows.get(a.get('theory_id'))
        if row is None or a.get('direction') not in ('supports', 'contradicts', 'neutral'):
            continue
        row[a['direction']] += 1
        kind = a.get('class') or (sources.get(a.get('evidence_id')) or {}).get('class')
        if kind == 'verified_observation' and a['direction'] != 'neutral':
            row[f"independent_{a['direction']}"] += 1
    return list(rows.values())


def source_mix(record: Json) -> list[Json]:
    counts: dict[str, int] = {}
    for s in (record.get('sources') or {}).values():
        counts[s.get('class', 'unknown')] = counts.get(s.get('class', 'unknown'), 0) + 1
    return [{'class': k, 'label': SOURCE_KIND.get(k, k), 'count': n} for k, n in sorted(counts.items(), key=lambda x: -x[1])]


def test_numbers(record: Json, budget: float | None, max_weeks: float | None) -> Json | None:
    tests = record.get('tests') or {}
    if not tests:
        return {'declined': True, 'reason': (record.get('test_declined') or {}).get('reason')} if record.get('test_declined') else None
    test = next(iter(tests.values()))
    return {
        'declined': False,
        'name': test.get('name'),
        'cost': test.get('cost_eur'),
        'budget': budget,
        'weeks': test.get('weeks'),
        'max_weeks': max_weeks,
        'people': _number(test.get('sample', '')),
        'predictions': test.get('prediction_by_theory') or {},
        'rule': test.get('decision_rule'),
        'method': test.get('method'),
        'measure': test.get('measure'),
        'sample': test.get('sample'),
    }


def steps(record: Json) -> Json:
    groups: dict[str, int] = {}
    for call in record.get('calls') or []:
        name = STEP_GROUP.get(call.get('stage') or '', 'Other')
        groups[name] = groups.get(name, 0) + 1
    calls = record.get('calls') or []
    return {
        'total': len(calls),
        'corrected': sum(not c.get('accepted') for c in calls),
        'searches': sum(c.get('name') == 'search_evidence' for c in calls),
        'reads': sum(c.get('name') == 'read_source' for c in calls),
        'by_group': [{'label': k, 'count': v} for k, v in groups.items()],
    }


def checks(record: Json) -> Json:
    rows = (record.get('checks') or {}).values()
    evaluated = [c for c in rows if c.get('passed') is not None]
    return {'passed': sum(bool(c['passed']) for c in evaluated), 'evaluated': len(evaluated)}


def metrics(record: Json, budget: float | None = None, max_weeks: float | None = None) -> Json:
    return {
        'finished': record.get('final') is not None,
        'beliefs': beliefs(record),
        'scale': list(BELIEFS),
        'evidence': evidence(record),
        'sources': source_mix(record),
        'test': test_numbers(record, budget, max_weeks),
        'steps': steps(record),
        'checks': checks(record),
    }


def suggestions(record: Json) -> list[str]:
    """Follow-up questions a manager would ask next, chosen from what the record holds."""
    final = record.get('final') or {}
    theories = record.get('theories') or {}
    out = []
    if final:
        out.append('What would change this recommendation?')
    if len(theories) >= 2:
        out.append('Why is one explanation favoured over the other?')
    if record.get('tests'):
        out.append('What exactly would the test show, and what does it cost?')
    elif record.get('test_declined'):
        out.append('Why was no test proposed?')
    out.append('Which evidence is the weakest?')
    if (record.get('coverage') or {}).get('shock', {}).get('delivered'):
        out.append('How did the new evidence change the picture?')
    return out[:4]
