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

from strategy_agent.common.types import Json
from strategy_agent.env.cases import load_cases
from strategy_agent.env.checks import CHECKS, _similar, normalise
from strategy_agent.pipeline import corrections as c

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
    if state['skill'] == 'experiment':
        problem = (
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
            test_turn = next((i for i, x in enumerate(record['calls']) if x.get('stage') == 'test'), None)
            if test_turn is not None:
                picks.append(('experiment', test_turn))
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
    asked = c.ask(items, url, weights, manifest, seed=29, workers=workers, generation=generation)
    for item, state in zip(asked, items, strict=True):
        item['skill'] = state['skill']
        if isinstance(item.get('kept'), dict):  # kept is the correction object or None, never False
            kept, reason = gate({**item['state'], 'skill': state['skill'], 'record': item['record']}, item['reply'])
            item['kept'], item['decision'] = kept, reason
    return asked


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
    args = p.parse_args()
    if args.command == 'states':
        out = states(args.reports)
        Path(args.output).write_text(json.dumps(out))
        print(json.dumps({'states': len(out), 'by_skill': {k: sum(x['skill'] == k for x in out) for k in ('experiment', 'recovery')}}))
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
