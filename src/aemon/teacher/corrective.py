"""Version 2 corrective examples (docs/CORRECTIVE_DISTILLATION_PROPOSAL.md): one verified teacher decision at a state
where version 1 itself went wrong, for six families. Training companies only; nothing here trains.

Families, each with the state it answers and the gate a reply must pass on top of corrections.judge (the call is
accepted by the tools, names something from the state and acts on it):
  numbers     at the student's finish: a recommendation whose every number comes from a read source or the brief, that
              cites real sources it assessed, including one for the favoured theory (targeted.gate_finish)
  experiment  at the student's test decision: propose a discriminating test, or decline one, and the choice must match
              whether the case warrants a test (the experiment check), plus every screen of targeted.gate
  classify    before an assessment the student labelled with the wrong evidence kind: the kind must match the
              annotation, and a theory that so far rests only on company claims must get a non-company source
  unstick     after two refusals in a row (outside the test step): a call that is accepted and changes the state
  simulated   at a finish refused for citing the simulated result: a finish on real evidence (targeted 'recovery')
  revise      at the first call after the simulated result arrives: revise_theory citing it, and the revision check passes

Instructions are per family; the teacher is never told the annotation it is gated on.

    python -m aemon.teacher.corrective states --reports R.json [R2.json] --per-family 10 --output states.json
    python -m aemon.teacher.corrective ask --states states.json --url URL --weights-sha256 SHA --manifest M.jsonl --output asked.json
    python -m aemon.teacher.corrective regate --asked asked.json --output regated.json
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from aemon.agent.recovery import signature
from aemon.common.constants.env import EVIDENCE_KINDS
from aemon.common.types import Json
from aemon.environment.cases import load_cases
from aemon.environment.checks import CHECKS
from aemon.teacher import corrections as c
from aemon.teacher import experiment_design
from aemon.teacher import targeted as t

FAMILIES = ('numbers', 'experiment', 'classify', 'unstick', 'simulated', 'revise')
SEED = 20261109

FINISH_ASK = (
    'You are shown the state of an investigation another analyst was running, at the point where they wrote the final '
    'recommendation. Write it well, with finish.\n'
    'Every number in the recommendation, target customer, value proposition and uncertainty must appear in a source '
    'you read or in the brief: do not carry the sample size, thresholds or prices of your own test into claims about '
    'the market, and write a qualitative statement when no source gives the figure. The next action and what would '
    'change your mind may repeat the design of a test already proposed in the state, but only if that test can separate '
    'the theories: if it varies only the wording or message, or jumps straight to building a product, do not recommend '
    'running it; name a better bounded next step instead. If no test was proposed, they contain no numbers either. In evidence_ids cite only real sources that have an assess_evidence on record in the '
    'state (a source only read does not count), including at least one weighed for the theory you favour; a simulated '
    'result is never evidence. Name the condition that would '
    'reverse the recommendation, and make the next action a bounded step, not the recommendation repeated.\n'
    'First say briefly what has been learned, which theory the evidence favours and why, naming the sources.'
)
DECIDE_TEST = (
    '\nYour call must be propose_test or decline_test. In why_next, name the theory ids the test separates (for example '
    '"separates T1 from T2 because...") or, if you decline, why more information is not worth its cost here. Decline '
    'when the evidence already settles the question, the result could not change what the company should do, or '
    'acting now is worth more than waiting; that is a correct answer, not a failure. Do not use numbers in the test that '
    'you will later present as facts about the market. Keep every field well under its length limit (learned under '
    '450 characters, method under 600): an answer cut at the limit is discarded. Prices use the currency of the case\'s '
    'country and year: no euros before 1999.'
)
CLASSIFY_ASK = (
    'You are shown the state of an investigation another analyst was running, at the point where they weighed a '
    'source. Weigh one source you have read with assess_evidence, quoting its exact words.\n'
    'Classify what kind of evidence the quoted passage is, from what the source is, not from what it says: '
    'company_assertion (the company or its people describing itself, its products or its plans, including press '
    'releases and interviews), customer_observation (what customers or users said or did, including product reviews and '
    'reports of how people used it), independent_study (only formal research: a peer-reviewed or published study, a '
    'systematic review, or a controlled test such as a consumer-testing organisation\'s), regulation (a law, standard, '
    'certification or official ruling), analogy (a different company, product, market or period offered as a parallel), '
    'market_fact (a fact or figure reported by a third party that is not formal research: encyclopedias, news and trade '
    'press, patents, histories, extension leaflets, field reports). An article by a journalist or an encyclopedia entry '
    'is market_fact, not independent_study, unless it reports what customers did or said. '
    'If a theory so far rests only on the company\'s own claims, prefer '
    'a source that does not come from the company. Say whether it supports, contradicts or has no bearing on the theory, '
    'and what it does not show, in your own words.\n'
    'First say briefly what has been learned, what this source adds and why it is the right one to weigh.'
)
UNSTICK_ASK = (
    'You are shown the state of an investigation another analyst was running. Their last two calls were refused, and '
    'the reasons are in the state. Make the single call that the investigation needs now and that the tools will '
    'accept: read what the refusal says, do not repeat a refused call or one already made, and if the step needs '
    'something the state does not have yet (a source read, a second theory, a weighing), make that call.\n'
    'First say briefly what has been learned, why the last calls were refused, and what your call adds.'
)
REVISE_ASK = (
    'You are shown the state of an investigation another analyst was running, just after a simulated result arrived. '
    'Respond to it with revise_theory, citing it. A simulated result is not evidence about the market: it can change '
    'what to test or how confident to be, never the facts. If it bears on no theory, keep the theories and say why it '
    'is irrelevant; if it bears on one, say how and how far that should move your belief, and what it does not show.\n'
    'First say briefly what the simulated result shows, which theory it bears on, if any, and why.'
)
# Second pilot (2026-11-10): a third of the first pilot's answers named no id from the state or acted on a different one
NAME_IDS = (
    '\nIn learned, uncertain and why_next write the exact ids (source ids, theory ids such as T1, test ids) of what you '
    'rely on, and make the call act on one of the ids you name in why_next.'
)
ASKS = {'numbers': FINISH_ASK, 'experiment': t.EXPERIMENT_ASK + DECIDE_TEST, 'classify': CLASSIFY_ASK, 'unstick': UNSTICK_ASK,
        'simulated': c.ASK, 'revise': REVISE_ASK}
ASKS = {f: text + NAME_IDS for f, text in ASKS.items()}
# The decision each state is about; in the first pilot 11 of 30 such answers made a different call (mostly read_source)
CALLS = {'numbers': ('finish',), 'experiment': ('propose_test', 'decline_test'), 'classify': ('assess_evidence',)}


def _company(case: Any) -> str:
    return case.id.split('-')[0]


def states(reports: Sequence[str | Path], per_family: int = 0, seed: int = SEED) -> list[Json]:
    """Every candidate state per family from version 1's training-company runs, then (per_family > 0) a sample spread
    over companies. One state per run per family: the first place the failure occurs."""
    cases = {x.id: x for x in load_cases()}
    final = {x['id'] for x in c.held_out()[0]}
    pools: dict[str, list[Json]] = collections.defaultdict(list)
    for path in reports:
        report = json.loads(Path(path).read_text())
        who = {k: report.get(k) for k in ('model_identity', 'code_revision', 'runtime')}
        for record in report['records']:
            cid = record['case']
            if c.is_validation(cid) or cid in final or cid not in cases or len(record['calls']) != len(record['model_turns']):
                continue
            case, calls = cases[cid], record['calls']
            full, _ = c._replay(record, case, len(calls))
            picks = {}
            finish = next((i for i, x in enumerate(calls) if x['name'] == 'finish'), None)
            if finish is not None and calls[finish].get('category') != 'synthetic_as_evidence':
                picks['numbers'] = finish
            test = next((i for i, x in enumerate(calls) if x['name'] in ('propose_test', 'decline_test')), None)
            if test is not None:
                picks['experiment'] = test
            wrong = next((i for i, x in enumerate(calls) if x['name'] == 'assess_evidence' and x['accepted'] and x.get('stage') != 'test'
                          and (kind := full._source((x.get('arguments') or {}).get('evidence_id')).kind) in EVIDENCE_KINDS
                          and (x.get('arguments') or {}).get('evidence_kind') != kind), None)
            if wrong is not None:
                picks['classify'] = wrong
            stuck = next((i for i in range(2, len(calls)) if not calls[i - 1]['accepted'] and not calls[i - 2]['accepted']
                          and calls[i - 1].get('stage') != 'test'), None)
            if stuck is not None:
                picks['unstick'] = stuck
            refused = next((i for i, x in enumerate(calls) if x['name'] == 'finish' and not x['accepted'] and x.get('category') == 'synthetic_as_evidence'), None)
            if refused is not None:
                picks['simulated'] = refused
            update = next((i for i, x in enumerate(calls) if x.get('stage') == 'update'), None)
            if update is not None and case.shock is not None:
                picks['revise'] = update
            student = c._digest(json.dumps([[x['text'], x['tool_result']] for x in record['model_turns']], sort_keys=True))
            for family, index in picks.items():
                dated = {**record, 'settings': {**record['settings'], 'source_dates': True}}  # the teacher sees dates
                _, context = c._replay(dated, case, index)
                pools[family].append({
                    'skill': family, 'case': cid, 'case_digest': c.case_digest(case), 'student_run': student, 'student_identity': who,
                    'turn': index, 'record': {'settings': dated['settings'], 'model_turns': record['model_turns'][:index]},
                    'context': context, 'student_call': calls[index],
                })
    out = []
    rng = random.Random(seed)
    for family in FAMILIES:
        pool = sorted(pools[family], key=lambda x: (x['case'], x['student_run']))
        rng.shuffle(pool)
        if per_family:  # round robin over companies, so a small batch covers as many as it can
            by: dict[str, list[Json]] = collections.defaultdict(list)
            for item in pool:
                by[_company(cases[item['case']])].append(item)
            queues = [by[k] for k in sorted(by, key=lambda k: rng.random())]
            pool = [q[i] for i in range(max(map(len, queues), default=0)) for q in queues if i < len(q)][:per_family]
        out.extend(pool)
    return out


def gate(state: Json, reply_text: str) -> tuple[Json | None, str]:
    family = state['skill']
    if family == 'experiment':
        kept, reason = t.gate(state, reply_text)
        if kept is None:
            return kept, reason
        case = {x.id: x for x in load_cases()}[state['case']]
        name = kept['call']['name']
        if name == 'propose_test' and not case.test_warranted:
            return None, 'gate: more information is not worth a test here, so the right call declines'
        if name == 'decline_test' and case.test_warranted:
            return None, 'gate: declined a test this case warrants'
        return kept, reason
    if family == 'simulated':
        return t.gate({**state, 'skill': 'recovery'}, reply_text)
    kept, reason = c.judge(state, reply_text)
    if kept is None:
        return None, reason
    case = {x.id: x for x in load_cases()}[state['case']]
    before, _ = c._replay(state['record'], case, len(state['record']['model_turns']))
    call, args = kept['call'], kept['call'].get('arguments') or {}
    after, _ = c._replay(state['record'], case, len(state['record']['model_turns']))
    after.call(call['name'], args)
    problem = ''
    if family == 'numbers':
        problem = 'a finish state must finish' if call['name'] != 'finish' else t.gate_finish(after, args) if after.final else 'the finish was not accepted'
        plan = ' '.join((str(args.get('next_action', '')), *map(str, args.get('would_change_if') or [])))
        weak = [k for k, test in before.tests.items() if re.search(rf'\b{k}\b', plan) and t.gate_mechanism(before, test)]
        if not problem and weak:  # review, 2026-11-10: all four kept pilot-3 finishes recommended running a message-only test
            problem = f'the next action runs {weak[0]}, an earlier test that fails a design screen'
    elif family == 'classify':
        problem = t.gate_weigh(before, call)
        if not problem:
            kind = before._source(args['evidence_id']).kind
            if kind and args.get('evidence_kind') != kind:
                problem = 'the evidence kind does not match what the source is'
            support = [a for a in before.assessments if a['theory_id'] == args.get('theory_id') and a['direction'] == 'supports']
            if not problem and support and all(a['class'] == 'company_claim' for a in support) and before._source(args['evidence_id']).type == 'company_claim':
                problem = 'the theory rests only on company claims and this is another one'
    elif family == 'unstick':
        if signature(after) == signature(before):
            problem = 'the call is accepted but changes nothing'
    elif family == 'revise':
        if call['name'] != 'revise_theory' or case.shock.id not in (args.get('evidence_ids') or []):
            problem = 'the response to the simulated result must be revise_theory citing it'
        else:
            verdict, why = CHECKS['revision'](after)
            if verdict is False:
                problem = f'revision: {why}'
    problem = problem or late_source(before, args)
    return (None, f'gate: {problem}') if problem else (kept, 'kept')


def late_source(run: Any, args: Json) -> str:
    """A call that cites or weighs a source dated after the year the case is set in (review, 2026-11-10: the
    dossiers hold later sources, and five kept answers relied on one). Only the call is checked: it is what trains."""
    found = t.YEAR.search(f'{run.case.question} {run.case.brief}')
    if not found:
        return ''
    year, named = int(found.group(1)), json.dumps(args)
    for source in run.read:
        date = str(getattr(run._source(source), 'date', '') or '')
        if date[:4].isdigit() and int(date[:4]) > year and re.search(rf'\b{re.escape(source)}\b', named):
            return f'the call relies on {source}, dated {date[:4]}, after the case is set ({year})'
    return ''


def ask(items: list[Json], url: str, weights: str, manifest: str, workers: int, generation: Json | None = None, samples: int = 1, temperature: float = 0.0,
        structured: bool = True) -> list[Json]:
    asked = []
    for family in FAMILIES:
        group = [x for x in items if x['skill'] == family]
        if family == 'experiment' and group and structured:  # the structured design, composed into propose_test
            asked += experiment_design.ask(group, url, weights, manifest, generation)
            continue
        for n in range(samples if group else 0):
            answers = c.ask(group, url, weights, manifest, seed=31 + 1000 * n, workers=workers, generation=generation, ask_text=ASKS[family],
                            temperature=temperature if n else 0.0, calls=CALLS.get(family, ()),
                           cite_assessed=family == 'numbers')
            for state, item in zip(group, answers, strict=True):
                item['skill'], item['sample'] = family, n
                if 'reply' in item:  # judged again by the family gate, whatever corrections.judge said about the test step
                    item['kept'], item['decision'] = gate({**item['state'], 'skill': family, 'record': item['record']}, item['reply'])
                asked.append(item)
    seen = set()
    for item in asked:  # one row per state: the first sample that passes
        key = (item['state']['student_run'], item['state']['turn'], item['skill'])
        if isinstance(item.get('kept'), dict):
            if key in seen:
                item['kept'], item['decision'] = None, 'another answer to this state was kept'
            seen.add(key)
    return asked


def regate(asked: list[Json]) -> list[Json]:
    out = []
    for item in asked:
        item = dict(item)
        if 'reply' in item and 'record' in item:
            item.setdefault('decision_at_generation', item.get('decision'))
            item['kept'], item['decision'] = gate({**item['state'], 'skill': item['skill'], 'record': item['record']}, item['reply'])
        out.append(item)
    return out


def rows(asked: list[Json], manifest: str, approved: set[tuple[str, int, str]] | None = None) -> list[Json]:
    """Rows from kept answers that the manifest holds and today's replay rebuilds exactly (corrections.rows), re-gated by
    the family gate; with approved, only the (student run, turn, family) a reviewer marked Keep."""
    made = []
    for item in asked:
        key = (item['state']['student_run'], item['state']['turn'], item['skill'])
        if not isinstance(item.get('kept'), dict) or (approved is not None and key not in approved):
            continue
        kept, _ = gate({**item['state'], 'skill': item['skill'], 'record': item['record']}, item['reply'])
        if kept is None or ('composition' in item and not experiment_design.verify(item, manifest)):
            continue
        made += [dict(row, source='corrective', skill=item['skill']) for row in c.rows([dict(item, kept=kept)], manifest)]
    return made


def summary(asked: list[Json]) -> Json:
    by = collections.defaultdict(collections.Counter)
    for x in asked:
        by[x['skill']]['answers'] += 1
        by[x['skill']]['kept' if isinstance(x.get('kept'), dict) else 'refused'] += 1
    reasons = {f: collections.Counter(x['decision'] for x in asked if x['skill'] == f and not isinstance(x.get('kept'), dict)).most_common(5) for f in by}
    return {'by_family': {f: dict(v) for f, v in by.items()}, 'top_rejections': reasons}


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='step', required=True)
    s = sub.add_parser('states')
    s.add_argument('--reports', nargs='+', required=True)
    s.add_argument('--per-family', type=int, default=0, help='a sample of this many per family, spread over companies (0: all)')
    s.add_argument('--families', default=','.join(FAMILIES))
    s.add_argument('--output', required=True)
    a = sub.add_parser('ask')
    a.add_argument('--states', required=True)
    a.add_argument('--url', required=True)
    a.add_argument('--weights-sha256', required=True)
    a.add_argument('--manifest', required=True)
    a.add_argument('--workers', type=int, default=1)
    a.add_argument('--server-settings')
    a.add_argument('--samples', type=int, default=1)
    a.add_argument('--temperature', type=float, default=0.0)
    a.add_argument('--output', required=True)
    g = sub.add_parser('regate')
    g.add_argument('--asked', required=True)
    g.add_argument('--output', required=True)
    args = p.parse_args()
    if args.step == 'states':
        wanted = set(args.families.split(','))
        items = [x for x in states(args.reports, args.per_family) if x['skill'] in wanted]
        Path(args.output).write_text(json.dumps(items, ensure_ascii=False))
        print(json.dumps({'states': len(items), 'by_family': collections.Counter(x['skill'] for x in items),
                          'companies': len({x['case'].split('-')[0] for x in items})}))
    elif args.step == 'ask':
        items = json.loads(Path(args.states).read_text())
        generation = json.loads(args.server_settings) if args.server_settings else None
        asked = ask(items, args.url, args.weights_sha256, args.manifest, args.workers, generation, args.samples, args.temperature)
        Path(args.output).write_text(json.dumps(asked, ensure_ascii=False))
        print(json.dumps(summary(asked)))
    else:
        asked = regate(json.loads(Path(args.asked).read_text()))
        Path(args.output).write_text(json.dumps(asked, ensure_ascii=False))
        print(json.dumps(summary(asked)))


if __name__ == '__main__':
    main()
