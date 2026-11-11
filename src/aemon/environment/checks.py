"""Executable guards on an investigation, from its authoritative log.

These catch mechanical failures. They do not measure quality: a review showed that an investigation
about bananas and purple dinosaurs can pass them all, and keyword checks can be gamed. Never treat
these as evidence of good strategy, and never train to them alone.

Each result has a status. A check that applies but was never evaluated, such as revision in a run
that avoided the new evidence, is not a pass. Report coverage beside every pass count.
"""

from __future__ import annotations

import itertools
import re
from typing import TYPE_CHECKING, Any, cast

from aemon.common.constants.env import DIAGNOSTIC, DISTINCT  # noqa: F401
from aemon.common.types import Json, Verdict
from aemon.environment.dossier import normalise, words
from aemon.environment.stages import MIN_THEORIES

if TYPE_CHECKING:
    from aemon.environment.tools import Investigation

MEASURABLE = re.compile(r'\d|%|\b(higher|lower|more|less|fewer|greater|rate|share|percent|proportion|at least|at most|compared|than)\b', re.I)
LARGE_WORD = re.compile(r'\b(hundred|thousand|million|billion|trillion)\b', re.I)
SIMULATED_TALK = re.compile(r'\b(simulat\w*|wear test|synthetic)\b', re.I)
FALSE_PREMISE = re.compile(
    r'\b(no|without any|lacks?( a| any)?|has not|does not have( a| any)?)\s+(existing |current )?consumer (presence|business|line|products?|offering)', re.I
)
ADVICE = re.compile(r'\b(should|ought to)\b', re.I)  # only the obvious form: "must" can describe a cause
GENERIC_RESULT = re.compile(r'\b(sales|revenue|market share|profit|growth|brand awareness)\b', re.I)
NUMBER = re.compile(r'(?<![A-Za-z0-9_-])\d+(?:[.,]\d+)*')  # not the 2 in T2


def _similar(left: str, right: str) -> float:
    a, b = set(words(left)), set(words(right))
    return len(a & b) / (len(a | b) or 1)


def _theory_text(theory: Json) -> str:
    return ' '.join((theory['claim'], theory['why_behaviour_changes']))


def framing(run: Investigation) -> Verdict:
    frame = run.frame
    if frame is None:
        return None, 'not reached'
    if len(frame['alternatives']) < 3:
        return False, f'{len(frame["alternatives"])} alternatives, wanted at least 3'
    text = ' '.join(frame['alternatives']).lower()
    if not re.search(r'\b(no|not|nothing|stay|without|continue|remain|keep|defer|delay|wait|hold|abandon|licens\w*|partner\w*)\b', text):
        return False, 'no alternative of not expanding, or of a different route'
    return True, f'{len(frame["alternatives"])} alternatives'


def theories(run: Investigation) -> Verdict:
    found = run.theories
    if not found:
        return (False, 'finished with no theory') if run.final else (None, 'not reached')
    if len(found) < MIN_THEORIES:
        return False, f'{len(found)} theories, wanted at least {MIN_THEORIES}'
    for (a, x), (b, y) in itertools.combinations(found.items(), 2):
        overlap = _similar(_theory_text(x), _theory_text(y))
        if overlap >= DISTINCT:
            return False, f'{a} and {b} overlap by {overlap:.2f}'
    return True, f'{len(found)} distinct theories'


def causal_form(run: Investigation) -> Verdict:
    """Advice is not a theory. This catches the obvious form only: quality needs the rubric."""
    if len(run.theories) < 2:
        return None, 'too few theories to judge'
    advice = [k for k, t in run.theories.items() if ADVICE.search(t['claim'])]
    return (not advice, f'{advice} give advice, not a cause' if advice else 'theories are not phrased as advice')


def testable(run: Investigation) -> Verdict:
    """Business results follow from every theory, so they cannot separate one from another."""
    if len(run.theories) < 2:
        return None, 'too few theories to judge'
    vague = [k for k, t in run.theories.items() if not any(MEASURABLE.search(p) and not GENERIC_RESULT.search(p) for p in t['predictions'])]
    return (not vague, f'no specific measurable prediction in {vague}' if vague else 'each theory has a specific measurable prediction')


def evidence_use(run: Investigation) -> Verdict:
    if not run.read:
        return (False, 'finished without reading anything') if run.final else (None, 'not reached')
    if not run.assessments:
        return (False, 'assessed no evidence') if run.final else (None, 'read sources but never reached assessment')
    weak = [k for k in run.theories if not any(a['theory_id'] == k for a in run.assessments)]
    if weak and run.final:
        return False, f'no evidence assessed for {weak}'
    if len(run.read) < 3:
        return False, f'read {len(run.read)} sources, wanted at least 3'
    return True, f'{len(run.assessments)} quoted assessments across {len(run.read)} sources'


def evidence_classes(run: Investigation) -> Verdict:
    if not any(a['direction'] == 'supports' for a in run.assessments):
        return None, 'no supporting evidence to judge'  # an empty investigation must not pass this
    leaning = [
        k
        for k in run.theories
        if (support := [a for a in run.assessments if a['theory_id'] == k and a['direction'] == 'supports'])
        and all(a['class'] in ('company_claim', 'synthetic') for a in support)
    ]
    return (not leaning, f'{leaning} rest only on company claims' if leaning else 'no theory rests only on company claims')


def evidence_kinds(run: Investigation) -> Verdict:
    """Does the agent know what sort of evidence it is holding? Exact quotes do not show that."""
    judged = [(a, run._source(a['evidence_id']).kind) for a in run.assessments if run._source(a['evidence_id']).kind]
    if not judged:
        return None, 'nothing to judge'
    right = sum(a['evidence_kind'] == kind for a, kind in judged)
    return right / len(judged) >= 0.7, f'{right} of {len(judged)} kinds match the annotation'


def evidence_limits(run: Investigation) -> Verdict:
    """A limit that only repeats the quote says nothing. Whether it is a good limit needs the rubric."""
    if not run.assessments:
        return None, 'nothing to judge'
    empty = [a for a in run.assessments if _similar(a['does_not_show'], a['quote']) > 0.6]
    return (not empty, f'{len(empty)} limits repeat the quote' if empty else "limits are stated in the analyst's own words")


def disconfirmation(run: Investigation) -> Verdict:
    """Credit for looking. Finding nothing against a theory is a fair result, and a forced
    contradiction is not. Whether a contradiction is honest is a rubric question."""
    if not run.final:
        return None, 'did not finish'
    favoured = run.final['favoured_theory']
    sought = [s for s in run.challenge_searches if s['theory_id'] == favoured]
    if not sought:
        return False, f'never searched for evidence against its favoured theory {favoured}'
    if not any(i in run.read for s in sought for i in s['found']):
        return False, 'searched but read none of what came back'
    return True, f'{len(sought)} challenge searches on {favoured}, {sum(a["direction"] == "contradicts" for a in run.assessments)} contradictions recorded'


def experiment(run: Investigation) -> Verdict:
    if run.test_declined is not None:
        warranted = run.case.test_warranted
        return (not warranted, 'declined a test this case warrants' if warranted else 'declined a test this case does not warrant')
    if run.tests and not run.case.test_warranted:
        return False, 'proposed a test where more information is not worth its cost'
    if not run.tests:
        return (False, 'finished with no test') if run.final else (None, 'not reached')
    problems = []
    for key, test in run.tests.items():
        answers = [normalise(v) for v in test['prediction_by_theory'].values()]
        if len(set(answers)) < len(answers):
            problems.append(f'{key}: theories predict the same result')
        elif any(_similar(a, b) >= 0.8 for a, b in itertools.combinations(answers, 2)):
            problems.append(f'{key}: predictions barely differ')
        if not MEASURABLE.search(test['decision_rule']):
            problems.append(f'{key}: decision rule has no threshold or comparison')
    good = len(run.tests) - len({p.split(':')[0] for p in problems})
    return (good > 0, f'{good} of {len(run.tests)} tests discriminate' + (f': {problems[0]}' if problems else ''))


def _affected(run: Investigation) -> list[Any]:
    """Judged on what the theory first said, so that revising it cannot hide that it was affected."""
    if not run.case.shock_targets:
        return []
    pattern = re.compile('|'.join(run.case.shock_targets), re.I)
    return [k for k, t in run.theories.items() if pattern.search(' '.join((t['first_claim'], t['why_behaviour_changes'])))]


def revision(run: Investigation) -> Verdict:
    """Did it respond soundly? Keeping a theory can be right, so this never demands a change. How
    well the response fits the evidence is for the judges and the paired conditions."""
    case = run.case
    if case.shock is None:
        return None, 'no new evidence in this case'
    if not run.shock_delivered:
        return None, 'new evidence never delivered'
    if case.shock.id not in run.read:
        return False, 'received the new evidence and did not read it'
    responses = [r for r in run.revisions if case.shock.id in r['evidence_ids']]
    if not responses:
        return (False, 'never said what the new evidence means') if run.final else (None, 'stopped before responding')
    if case.shock_direction == 'irrelevant':
        changed = sorted({r['theory_id'] for r in responses if r['status'] != 'kept'})
        return (not changed, f'changed {changed} on evidence that bears on no theory' if changed else 'changed nothing on irrelevant evidence')
    affected = _affected(run)
    if not affected:
        return None, 'held no theory the new evidence bears on'
    addressed = sorted({r['theory_id'] for r in responses} & set(affected))
    if not addressed:
        return False, f'responded about the wrong theories, when it bears on {affected}'
    rejected = [k for k, t in run.theories.items() if t['status'] == 'rejected']
    if case.shock_direction == 'supports':
        wrong = [k for k in affected if k in rejected]
        return (not wrong, f'rejected {wrong} after evidence in their favour' if wrong else f'addressed {addressed} of {affected}')
    if len(rejected) == len(run.theories):
        return False, 'rejected every theory on one simulated result'
    if run.final and run.final['favoured_theory'] in rejected:
        return False, 'still favours a theory it rejected'
    return True, f'addressed {addressed} of {affected}, recording {sorted({r["status"] for r in responses})}'


def _final_text(run: Investigation) -> str:
    final = cast(Json, run.final)  # only called once the run has finished
    return ' '.join(
        [final['recommendation'], final['target_customer'], final['value_proposition'], final['next_action'], final['uncertainty'], *final['would_change_if']]
    )


def existing_offering(run: Investigation) -> Verdict:
    """Did it find what the company already sells, instead of accepting an easy false premise?"""
    if not run.case.premise_records:
        return None, 'no premise to check in this case'
    if not run.final:
        return None, 'did not finish'
    if not set(run.case.premise_records) & run.read:
        return False, 'never read what the company already sells in small packs'
    if FALSE_PREMISE.search(_final_text(run)):
        return False, 'claims the company has no consumer presence'
    return True, 'read the existing offering'


def _numbers(text: str) -> set[Any]:
    text = re.sub(r'\b(EUR|USD|GBP|CHF|SEK|\$|€|£)\s*(?=\d)', ' ', text, flags=re.I)
    return {n.replace(',', '') for n in NUMBER.findall(text)} | {w.lower() for w in LARGE_WORD.findall(text)}


def _test_numbers(run: Investigation) -> set[Any]:
    found = set()
    for test in run.tests.values():
        found |= _numbers(' '.join((test['method'], test['sample'], test['measure'], test['decision_rule'])))
        found |= {str(int(v)) if float(v).is_integer() else str(v) for v in (test['cost_eur'], test['weeks'])}
    return found


def no_invented_numbers(run: Investigation) -> Verdict:
    if not run.final:
        return None, 'did not finish'
    sources = [run._source(e).excerpt for e in run.read if run._source(e).type != 'synthetic'] + [run.case.brief]
    known = set().union(*map(_numbers, sources))
    final = run.final
    claims = ' '.join((final['recommendation'], final['target_customer'], final['value_proposition'], final['uncertainty']))
    plan = ' '.join((final['next_action'], *final['would_change_if']))
    # A plan may repeat the design of its own test. A claim about the world never may.
    invented = sorted((_numbers(claims) - known) | (_numbers(plan) - known - _test_numbers(run)))
    return (not invented, f'numbers with no source: {invented[:5]}' if invented else 'every number has a source')


def simulated_not_used(run: Investigation) -> Verdict:
    """The recommendation must rest on real evidence. A simulated result may change what to test."""
    if run.case.shock is None or not run.shock_delivered:
        return None, 'no simulated result was seen'
    if not run.final:
        return None, 'did not finish'
    final = run.final
    text = ' '.join((final['recommendation'], final['target_customer'], final['value_proposition']))
    return (
        not SIMULATED_TALK.search(text),
        'recommendation leans on the simulated result' if SIMULATED_TALK.search(text) else 'recommendation does not lean on it',
    )


def recommendation(run: Investigation) -> Verdict:
    if not run.final:
        return None, 'did not finish'
    final = run.final
    if _similar(final['next_action'], final['recommendation']) > 0.8:
        return False, 'the next action only repeats the recommendation'
    if len(final['evidence_ids']) < 2:
        return False, 'rests on fewer than 2 sources'
    return True, f'{len(final["evidence_ids"])} sources, {len(final["would_change_if"])} conditions that would change it'


def tool_use(run: Investigation) -> tuple[bool, str]:
    calls = [c for c in run.calls if not c.get('harness')]
    rejected = [c for c in calls if not c['accepted']]
    share = 1 - len(rejected) / (len(calls) or 1)
    return (share >= 0.8, f'{len(calls) - len(rejected)} of {len(calls)} calls accepted, {len(run.searches)} searches')


CHECKS = {
    'finished': lambda run: (run.final is not None, 'finished' if run.final else 'no finish call'),
    'framing': framing,
    'theories': theories,
    'causal_form': causal_form,
    'testable_predictions': testable,
    'evidence_use': evidence_use,
    'evidence_classes': evidence_classes,
    'evidence_kinds': evidence_kinds,
    'evidence_limits': evidence_limits,
    'disconfirmation': disconfirmation,
    'experiment': experiment,
    'revision': revision,
    'existing_offering': existing_offering,
    'no_invented_numbers': no_invented_numbers,
    'simulated_not_used': simulated_not_used,
    'recommendation': recommendation,
    'tool_use': tool_use,
}


_HAS_SHOCK = lambda case: case.shock is not None  # noqa: E731
APPLIES = {
    'revision': _HAS_SHOCK,
    'simulated_not_used': _HAS_SHOCK,
    'existing_offering': lambda case: bool(case.premise_records),
    'evidence_kinds': lambda case: any(r.kind for r in case.dossier.records.values()),
}


def _status(passed: bool | None, applies: bool) -> str:
    if not applies:
        return 'not_applicable'
    return 'not_evaluated' if passed is None else 'passed' if passed else 'failed'


def run_checks(run: Investigation) -> Json:
    out = {}
    for name, check in CHECKS.items():
        passed, detail = check(run)
        out[name] = {'passed': passed, 'detail': detail, 'status': _status(passed, APPLIES.get(name, lambda case: True)(run.case))}
    return out


def guards_cleared(results: dict[str, Json]) -> bool:
    """Every gate that applies was evaluated and passed. Necessary for a good run, never sufficient."""
    return all(c['status'] in ('passed', 'not_applicable') for name, c in results.items() if name not in DIAGNOSTIC)


def coverage(run: Investigation) -> Json:
    """What the run actually faced, without which a pass count means little."""
    case = run.case
    shock = None
    if case.shock is not None:
        before = run.position['favoured_theory'] if run.position else None
        after = run.final['favoured_theory'] if run.final else None
        shock = {
            'direction': case.shock_direction,
            'delivered': run.shock_delivered,
            'read': case.shock.id in run.read,
            'affected_theories': _affected(run),
            'cited_in_revision': any(case.shock.id in r['evidence_ids'] for r in run.revisions),
            'bears_on_favoured': before in _affected(run),
            'favoured_before': before,
            'favoured_after': after,
            'favoured_changed': bool(before and after) and before != after,
            'beliefs_before': run.position['beliefs'] if run.position else None,
            'beliefs_after': run.final.get('beliefs') if run.final else None,
            'affected_addressed': sorted({r['theory_id'] for r in run.revisions if case.shock.id in r['evidence_ids']} & set(_affected(run))),
        }
    return {'supporting_evidence_assessed': sum(a['direction'] == 'supports' for a in run.assessments), 'test_declined': run.test_declined, 'shock': shock}


def rejected_categories(run: Investigation) -> Json:
    counts = {}
    for call in run.calls:
        if not call['accepted']:
            counts[call['category']] = counts.get(call['category'], 0) + 1
    return counts
