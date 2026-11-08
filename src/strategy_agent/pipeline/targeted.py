"""Version 2 targeted examples (docs/V2_PLAN.md): one verified teacher decision from a genuine student state, for two
skills, experiment design and recovery from a refused finish. Training companies only. Selection is this code and
nothing else; Claude writes no example and picks none.

1. states: replay version 1's own runs on training cases and keep, per run, the state before its first call in the
   test stage (experiment design) and the state before its first finish refused for citing only simulated evidence
   (recovery). The state is exactly the compact context the student saw.
2. ask: the teacher answers each state once (corrections.ask, whose reply is hashed into the manifest before judging).
3. gate: a reply kept by corrections.judge must also pass the stricter skill gate below, judged on the new call only.
4. rows: kept examples become rows tagged source 'targeted', only if their stored context still equals today's replay.

Usage: python -m strategy_agent.pipeline.targeted states --reports R.json [R2.json] --output states.json
       python -m strategy_agent.pipeline.targeted ask --states states.json --url URL --weights-sha256 SHA --manifest M.jsonl --output asked.json
       python -m strategy_agent.pipeline.targeted rows --asked asked.json --manifest M.jsonl --output rows.jsonl
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
from collections.abc import Sequence  # noqa: F811
from pathlib import Path
from typing import Any

from strategy_agent.agent.runner import _BY_NAME as BY_NAME
from strategy_agent.common.types import Json
from strategy_agent.env.cases import load_cases
from strategy_agent.env.checks import CHECKS, _similar, normalise
from strategy_agent.pipeline import corrections as c

JUSTIFICATION_LIMITS = {'learned': 700, 'uncertain': 500, 'why_next': 700}  # as in corrections._schema

# Instructions for the experiment states. The recovery prompt (corrections.ASK) tells the teacher not to move on before
# the evidence is in place, which at these states made it read more sources instead of designing the test.
EXPERIMENT_ASK = (
    'You are shown the state of an investigation another analyst was running, at the point where they designed the '
    'test. Make that decision well.\n'
    'Either propose one test, or decline it. A good test separates WHY customers would buy, not which message '
    'persuades them: vary real product attributes, trade-offs or price while keeping the presentation comparable, or '
    'measure a real commitment (a pre-order, a deposit, a paid trial, sell-through in a store or by mail order, use of a '
    'prototype) rather than only stated preference. If only a survey is feasible, say what it can and cannot show. '
    'Give a prediction for each open theory that follows from that theory, a measure, a sample, a cost and duration '
    'within the stated budget and time, and a decision rule, written out in full, that says what each result would '
    'lead the company to do. Be proportionate: one result from a small test usually justifies the next bounded step '
    '(a pilot, a prototype run, a partner trial), not building a product line, unless the state shows the costs, '
    'margins and uncertainty that would justify more.\n'
    'Decline the test if more information would not justify its cost, saying why from the state (it cannot change the '
    'decision, the evidence already settles it, acting now is worth more, or it does not fit the stated limits).\n'
    'Stay inside the case: if it is set in the past, use only methods available at that date and only facts from '
    'sources dated on or before it; do not use anything the analyst could not have known then.\n'
    'First say briefly what has been learned, which uncertainty separates the theories, and why this test (or '
    'declining) is the right next step, naming the theories and the sources it rests on.'
)
MONTHS = 'January|February|March|April|May|June|July|August|September|October|November|December'
# "It is 1977", "It is late 2012", "It is March 2016", "It is mid-May 2025", "It is spring 2021": every dated case (16 were
# missed by the first pattern, which knew only early, mid- and late; DECISIONS, 2026-11-08)
YEAR = re.compile(rf'\bIt is (?:the )?(?:early |mid-|late |end of |spring |summer |autumn |fall |winter )?(?:(?:{MONTHS}) )?(\d{{4}})')
ONLINE = re.compile(r'\b(online|internet|web|e-?mail|social media|landing page|app\b|smartphone|mturk|prolific)', re.I)
ENDS = ('.', ')', '!', '"', '\u201d')


OLD_LIMIT = 240  # the text limit the first version 2 batches were generated under (DECISIONS, 2026-11-08)


def _limits(schema: Json, value: Any, path: str = '') -> list[tuple[str, int, int]]:
    """Every string in value with its schema maxLength, as (path, length, limit)."""
    if isinstance(value, str):
        return [(path, len(value), schema['maxLength'])] if 'maxLength' in schema else []
    if isinstance(value, list):
        return [x for i, v in enumerate(value) for x in _limits(schema.get('items', {}), v, f'{path}[{i}]')]
    if isinstance(value, dict):
        props, extra = schema.get('properties', {}), schema.get('additionalProperties')
        return [x for k, v in value.items() for x in _limits(props.get(k, extra if isinstance(extra, dict) else {}), v, f'{path}.{k}' if path else k)]
    return []


def cut_off(call: Json, justification: Json | None) -> str:
    """A field the constrained generation stopped at its length limit is cut mid-text; it is never complete."""
    tool = BY_NAME.get(call.get('name', ''))
    if tool is None:
        return ''
    found = _limits(tool['properties']['arguments'], call.get('arguments') or {})
    found += _limits({'properties': {k: {'maxLength': n} for k, n in JUSTIFICATION_LIMITS.items()}}, justification or {})
    for path, length, limit in found:
        if limit >= 100 and (length >= limit - 2 or length == OLD_LIMIT):
            return f'{path} stops at its length limit ({length} characters), cut mid-text'
    return ''


def gate_case_bounds(run: Any, args: Json, justification: Json | None) -> str:
    """Structural checks that a test design stays complete and inside its case's time."""
    rule = str(args.get('decision_rule', '')).rstrip()
    if not rule.endswith(ENDS) or len(rule) >= 895 or re.search(r'[<>=\u2264\u2265(]\s*\d*\.$', rule):
        return 'the decision rule is not written out in full'
    found = YEAR.search(f'{run.case.question} {run.case.brief}')
    if not found:
        return ''
    year = int(found.group(1))
    text = ' '.join(str(args.get(k, '')) for k in ('name', 'method', 'sample', 'measure'))
    if year < 1995 and ONLINE.search(text):
        return f'an online method in a case set in {year}'
    said = json.dumps(justification or {}) + json.dumps(args)
    for source in run.read:
        date = str(getattr(run._source(source), 'date', '') or '')
        if date[:4].isdigit() and int(date[:4]) > year and re.search(rf'\b{re.escape(source)}\b', said):
            return f'relies on {source}, dated {date[:4]}, after the case is set ({year})'
    return ''


NUMBER = re.compile(r'\d+(?:[.,]\d+)?')
UP = re.compile(r'\b(higher|more|increase\w*|rise\w*|greater|above|exceed\w*|grow\w*|larger)\b', re.I)
DOWN = re.compile(r'\b(lower|less|fewer|decrease\w*|fall\w*|drop\w*|below|smaller|declin\w*)\b', re.I)
SAME = re.compile(r'\b(no difference|same|unchanged|similar|equal|no change)\b', re.I)
COST_PER_PERSON = (1.0, 500.0)  # euros per participant a stated test may plausibly cost; outside it the cost is not credible


OTHERWISE = re.compile(
    r'\b(otherwise|else|if not|if instead|if neither|if both|if (?:the )?(?:difference|gap) is (?:below|under|less)|below this|under this)\b', re.I
)


ACTION = re.compile(
    r'\b(proceed|pursue|develop|launch|invest|enter|recommend|stop|drop|abandon|pause|continue|scale|pivot|do not|don\'t|reject|favour|favor)\w*', re.I
)
CONTENT = re.compile(r'[a-z][a-z-]{4,}')


def explained(justification: Json, args: Json, theories: Sequence[str]) -> str:
    """'' when the teacher's own reasoning links the intervention, the rival predictions and the resulting action.
    A threshold alone is not proof of a discriminating test."""
    text = ' '.join(str(justification.get(k, '')) for k in ('learned', 'uncertain', 'why_next'))
    named = [t for t in theories if re.search(rf'\b{re.escape(t)}\b', text)]
    if len(named) < 2:
        return 'the reasoning does not name the theories the test separates'
    method = {w for w in CONTENT.findall(str(args.get('method', '')).lower())}
    if not method & set(CONTENT.findall(text.lower())):
        return 'the reasoning does not refer to the intervention'
    if not (ACTION.search(text) or ACTION.search(str(args.get('decision_rule', '')))):
        return 'neither the reasoning nor the rule says what action each result leads to'
    return ''


SIDE_WORD = re.compile(r'[a-z][a-z-]{3,}')
SPLIT = re.compile(r'\s(?:than|compared (?:to|with)|versus|vs\.?)\s', re.I)
LABEL = re.compile(r'\b(?i:condition|arm|group|variant|version|option|scenario)\s+([A-Z0-9])\b')


def _side(text: str) -> set[str]:
    return set(SIDE_WORD.findall(text.lower())) | {f'label-{x}' for x in LABEL.findall(text)}


def mirrored(a: str, b: str) -> bool:
    """Opposite or different comparisons: A puts something ahead that B does not, and the other way round. The
    environment's word-overlap test reads these as near-identical. A structural screen only: it does not read
    direction, so "A is lower than B" against "B is higher than A" (the same outcome) passes as different; accepted
    examples are inspected in a sample for substantive discrimination."""
    pa, pb = SPLIT.split(a, maxsplit=1), SPLIT.split(b, maxsplit=1)
    if len(pa) < 2 or len(pb) < 2:
        return False
    la, ra, lb, rb = _side(pa[0]), _side(pa[1]), _side(pb[0]), _side(pb[1])
    return bool(la - lb) and bool(lb - la) and bool(((la - lb) & rb) or ((lb - la) & ra) or (la - lb - rb and lb - la - ra))


def gate_test(run: Any, args: Json, justification: Json | None = None) -> str:
    """'' when a proposed test shows the skill, else why not. Judged on this test alone; run is the state before it."""
    case = run.case
    predictions = {k: str(v) for k, v in (args.get('prediction_by_theory') or {}).items() if k in run.theories}
    if len(predictions) < 2:
        return 'fewer than two of the open theories get a prediction'
    for k, v in predictions.items():
        if not (NUMBER.search(v) or UP.search(v) or DOWN.search(v) or SAME.search(v)):
            return f'the prediction for {k} commits to no number or direction'
    answers = [normalise(v) for v in predictions.values()]
    texts = list(predictions.values())
    for i, j in itertools.combinations(range(len(texts)), 2):
        if (answers[i] == answers[j] or _similar(answers[i], answers[j]) >= 0.8) and not mirrored(texts[i], texts[j]):
            return 'the predictions barely differ'
    rule = str(args.get('decision_rule', ''))
    if not NUMBER.search(rule):
        return 'the decision rule has no number'
    named = sum(1 for k in predictions if re.search(rf'\b{re.escape(k)}\b', rule))
    branches = len(re.findall(r'\bif\b', rule, re.I))
    if named < 2 and not OTHERWISE.search(rule) and branches < 2:
        return 'the decision rule does not say what the other outcome leads to'
    try:
        cost, weeks = float(args.get('cost_eur')), float(args.get('weeks'))
    except (TypeError, ValueError):
        return 'cost or weeks is not a number'
    if cost > case.test_budget or weeks > case.max_test_weeks:
        return 'over the stated budget or time'
    sizes = [int(n.replace(',', '')) for n in NUMBER.findall(str(args.get('sample', ''))) if n.replace(',', '').isdigit()]
    if not sizes or not (COST_PER_PERSON[0] <= cost / max(sizes) <= COST_PER_PERSON[1]):
        return 'the cost per participant is not credible for the stated sample'
    return explained(justification or {}, args, list(predictions))


NO_CHANGE = re.compile(
    r'\b(would not change|wouldn.t change|regardless of|either (?:result|outcome)|whatever the (?:result|outcome)|same decision|not change the (?:decision|recommendation))\b',
    re.I,
)
REDUNDANT = re.compile(r'\b(already (?:shows|show|establish\w*|answer\w*|settle\w*|decisive|known)|redundant|adds? (?:little|nothing))\b', re.I)
ACT_NOW = re.compile(r'\b(not worth|cost of (?:delay|waiting)|act now|outweigh\w*|exceeds? (?:its|the) value|value of (?:the )?information)\b', re.I)


def gate_decline(run: Any, args: Json) -> str:
    """A decline is right when testing cannot change the decision, repeats what the evidence already settles, is worth
    less than acting now, or does not fit the stated limits. Any of these, grounded in the state, passes; none is
    required because a case author expected it."""
    case = run.case
    reason = str(args.get('reason', ''))
    if len(reason.split()) < 15:
        return 'the decline is not explained'
    concrete = set(run.read) | set(run.theories)
    if not any(re.search(rf'\b{re.escape(i)}\b', reason) for i in concrete):
        return 'the decline names no theory or source from the state'
    figures = {str(case.test_budget), f'{case.test_budget:,}', str(case.max_test_weeks)}
    over_budget = any(f in reason for f in figures) and any(
        float(n.replace(',', '')) > case.test_budget for n in NUMBER.findall(reason) if n.replace(',', '').replace('.', '').isdigit()
    )
    if not (NO_CHANGE.search(reason) or REDUNDANT.search(reason) or ACT_NOW.search(reason) or over_budget):
        return 'the decline gives no reason testing is not worth it (no effect on the decision, already settled, worth less than acting, or over the stated limits)'
    return ''


def gate_finish(run: Any, args: Json) -> str:
    """Run is the state after the finish was accepted."""
    cited = list(args.get('evidence_ids') or [])
    real = [i for i in cited if i in run.read and run._source(i).type != 'synthetic']
    if not real:
        return 'the finish cites no real source it read'
    assessed = {a['evidence_id'] for a in run.assessments}
    if any(i not in assessed for i in real):
        return 'the finish cites a source it never assessed (padding)'
    favoured = args.get('favoured_theory')
    if not any(a['evidence_id'] in real and a['theory_id'] == favoured for a in run.assessments):
        return 'no cited source was assessed for the favoured theory'
    for name in ('no_invented_numbers', 'simulated_not_used', 'recommendation'):
        verdict, why = CHECKS[name](run)
        if verdict is False:
            return f'{name}: {why}'
    return ''


def gate(state: Json, reply_text: str) -> tuple[Json | None, str]:
    kept, reason = c.judge(state, reply_text)
    if kept is None:
        return None, reason
    case = {x.id: x for x in load_cases()}[state['case']]
    before, _ = c._replay(state['record'], case, len(state['record']['model_turns']))
    call = kept['call']
    args = call.get('arguments') or {}
    if state['skill'].startswith('experiment'):
        problem = cut_off(call, kept.get('justification')) or gate_case_bounds(before, args, kept.get('justification')) if call['name'] == 'propose_test' else ''
        problem = problem or (
            gate_test(before, args, kept.get('justification'))
            if call['name'] == 'propose_test'
            else gate_decline(before, args)
            if call['name'] == 'decline_test'
            else 'not a test decision'
        )
    else:
        if call['name'] != 'finish':
            problem = 'a recovery from a refused finish must finish, citing real evidence'
        else:
            after, _ = c._replay(state['record'], case, len(state['record']['model_turns']))
            after.call(call['name'], args)
            problem = gate_finish(after, args) if after.final else 'the finish was not accepted'
    return (None, f'gate: {problem}') if problem else (kept, 'kept')


def states(reports: Sequence[str | Path]) -> list[Json]:
    cases = {x.id: x for x in load_cases()}
    final = {x['id'] for x in c.held_out()[0]}
    out = []
    for path in reports:
        report = json.loads(Path(path).read_text())
        who = {k: report.get(k) for k in ('model_identity', 'code_revision', 'runtime')}
        for record in report['records']:
            if c.is_validation(record['case']) or record['case'] in final or record['case'] not in cases:
                continue
            if len(record['calls']) != len(record['model_turns']):
                continue
            case = cases[record['case']]
            student = c._digest(json.dumps([[t['text'], t['tool_result']] for t in record['model_turns']], sort_keys=True))
            picks = []
            # the point where the student itself designed (or declined) the test, so the evidence it had is in place
            test_turn = next((i for i, x in enumerate(record['calls']) if x['name'] in ('propose_test', 'decline_test')), None)
            if test_turn is not None:
                picks.append(('experiment', test_turn))
            # where it reread one source a third time in the test stage instead of designing the test (DECISIONS, 2026-11-08)
            loop = next((i for i in c.loop_starts(record) if record['calls'][i]['name'] == 'read_source' and record['calls'][i].get('stage') == 'test'), None)
            if loop is not None and loop != test_turn:
                picks.append(('experiment-reread', loop))
            refused = next(
                (i for i, x in enumerate(record['calls']) if x['name'] == 'finish' and not x['accepted'] and x.get('category') == 'synthetic_as_evidence'),
                None,
            )
            if refused is not None:
                picks.append(('recovery', refused))
            for skill, index in picks:
                _, context = c._replay(record, case, index)
                out.append(
                    {
                        'skill': skill,
                        'case': case.id,
                        'case_digest': c.case_digest(case),
                        'student_run': student,
                        'student_identity': who,
                        'turn': index,
                        'record': {'settings': record['settings'], 'model_turns': record['model_turns'][:index]},
                        'context': context,
                        'student_call': record['calls'][index],
                    }
                )
    return out


def ask(items: list[Json], url: str, weights: str, manifest: str, workers: int, generation: Json | None = None) -> list[Json]:
    experiment = [x for x in items if x['skill'].startswith('experiment')]
    recovery = [x for x in items if not x['skill'].startswith('experiment')]
    asked_by_id: dict[int, Json] = {}
    for group, text in ((experiment, EXPERIMENT_ASK), (recovery, c.ASK)):
        if group:
            for state, answer in zip(group, c.ask(group, url, weights, manifest, seed=29, workers=workers, generation=generation, ask_text=text), strict=True):
                asked_by_id[id(state)] = answer
    asked = [asked_by_id[id(x)] for x in items]
    for item, state in zip(asked, items, strict=True):
        item['skill'] = state['skill']
        if isinstance(item.get('kept'), dict):  # kept is the correction object or None, never False
            kept, reason = gate({**item['state'], 'skill': state['skill'], 'record': item['record']}, item['reply'])
            item['kept'], item['decision'] = kept, reason
    return asked


def regate(asked: list[Json]) -> list[Json]:
    """The same saved replies judged again by the current code, with no new sampling: used once, after the environment's
    text limit for a test's method and rule was raised to match the schema the teacher was given (DECISIONS, 2026-11-08).
    Every reply is re-judged, including those the old limit refused, and the decision made at generation is kept."""
    out = []
    for item in asked:
        item = dict(item)
        if 'reply' in item and 'record' in item:
            item.setdefault('decision_at_generation', item.get('decision'))
            kept, reason = gate({**item['state'], 'skill': item['skill'], 'record': item['record']}, item['reply'])
            item['kept'], item['decision'] = kept, reason
        out.append(item)
    return out


def rows(asked: list[Json], manifest: str) -> list[Json]:
    """corrections.rows rebuilds and re-judges each row; the stricter gate is applied again on top."""
    made = []
    for item in asked:
        if not isinstance(item.get('kept'), dict):
            continue
        kept, reason = gate({**item['state'], 'skill': item['skill'], 'record': item['record']}, item['reply'])
        if kept is None:
            continue
        for row in c.rows([item], manifest):
            made.append(dict(row, source='targeted', skill=item['skill']))
    return made


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('states')
    s.add_argument('--reports', nargs='+', required=True)
    s.add_argument('--output', required=True)
    a = sub.add_parser('ask')
    a.add_argument('--states', required=True)
    a.add_argument('--url', required=True)
    a.add_argument('--weights-sha256', required=True)
    a.add_argument('--manifest', required=True)
    a.add_argument('--workers', type=int, default=4)
    a.add_argument('--server-settings', help='JSON of how the teacher server was started, recorded in the manifest')
    a.add_argument('--output', required=True)
    r = sub.add_parser('rows')
    r.add_argument('--asked', required=True)
    r.add_argument('--manifest', required=True)
    r.add_argument('--output', required=True)
    g = sub.add_parser('regate')
    g.add_argument('--asked', required=True)
    g.add_argument('--output', required=True)
    args = p.parse_args()
    if args.command == 'regate':
        out = regate(json.loads(Path(args.asked).read_text()))
        Path(args.output).write_text(json.dumps(out))
        changed = [x for x in out if 'decision_at_generation' in x and x['decision_at_generation'] != x['decision']]
        print(json.dumps({'answers': len(out), 'kept': sum(isinstance(x.get('kept'), dict) for x in out), 'changed': len(changed),
                          'now_kept': sum(isinstance(x.get('kept'), dict) for x in changed)}))
    elif args.command == 'states':
        out = states(args.reports)
        Path(args.output).write_text(json.dumps(out))
        print(json.dumps({'states': len(out), 'by_skill': {k: sum(x['skill'] == k for x in out) for k in ('experiment', 'experiment-reread', 'recovery')}}))
    elif args.command == 'ask':
        generation = json.loads(args.server_settings) if args.server_settings else None
        out = ask(json.loads(Path(args.states).read_text()), args.url, args.weights_sha256, args.manifest, args.workers, generation)
        Path(args.output).write_text(json.dumps(out))
        kept = [x for x in out if isinstance(x.get('kept'), dict)]
        print(json.dumps({'asked': len(out), 'kept': len(kept), 'reasons': sorted({x['decision'] for x in out})[:20]}))
    else:
        out = rows(json.loads(Path(args.asked).read_text()), args.manifest)
        Path(args.output).write_text(''.join(json.dumps(x) + '\n' for x in out))
        print(json.dumps({'rows': len(out), 'by_skill': {k: sum(x['skill'] == k for x in out) for k in ('experiment', 'recovery')}}))


if __name__ == '__main__':
    main()
