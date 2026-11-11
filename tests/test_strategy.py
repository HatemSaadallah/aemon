"""The checks must pass a real investigation and fail each kind of bad one.

Evidence here is an obviously fake fixture for testing the machinery, not a claim about anything.
"""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from aemon.evaluation.diagnostics.audit import ReplayMismatch, audit, replay, to_eventlog  # noqa: E402
from aemon.environment.checks import guards_cleared, run_checks  # noqa: E402
from aemon.rows.provenance import TEACHER_WEIGHTS, episode_id, record_provenance, training_source  # noqa: E402
from aemon.agent.backends.claude_control import BudgetExceeded, Claude, cost, spent
from aemon.environment.dossier import Dossier, Record, normalise  # noqa: E402
from aemon.agent.backends.llama_client import parse_call
from aemon.agent.loop import play
from aemon.agent.records import record_of, summary
from aemon.agent.state_view import guidance, next_step
from aemon.agent.tool_schemas import TOOL_SCHEMA, schema_for
from aemon.common.constants.prompts import PROMPTS
from aemon.environment.stages import current_stage  # noqa: E402
from aemon.environment.tools import TOOL_SIGNATURES, Case, Investigation  # noqa: E402
from auditkit.agent_eval import episode_from_eventlog  # noqa: E402

URL = 'https://example.invalid/fixture'
AYA_WEIGHTS = next(iter(TEACHER_WEIGHTS))


def record(identifier, kind, excerpt, topic=''):
    return Record(identifier, kind, f'Fixture {identifier}', URL, '2026-01-01', excerpt, topic=topic)


RECORDS = [
    record('E1', 'verified_observation', 'FIXTURE. Wearers in the trial said comfort was the main reason they removed the widget during long shifts.', 'comfort'),
    record('E2', 'verified_observation', 'FIXTURE. Young buyers reported that the look of the widget made them embarrassed to wear it in public settings.', 'appearance'),
    record('E3', 'company_claim', 'FIXTURE. Our widget is the most comfortable on the market, according to our own marketing team.', 'comfort'),
    record('E4', 'verified_observation', 'FIXTURE. Sales rose by 40 percent when the widget was placed at venue entrances, in one observational study.', 'distribution'),
    record('E5', 'verified_observation', 'FIXTURE. Appearance ratings did not predict continued use of the widget after six months in a cohort of 200 adults.', 'appearance'),
]
SHOCK = Record('SYN-1', 'synthetic', 'Simulated wear test', 'n/a', 'n/a', 'SIMULATED RESULT. Styled and plain designs were worn equally often in this simulated test.')


def make_case(shock=None):
    return Case('fixture', 'Fixture Co', 'Should we enter?', 'Fixture brief. Budget 20000 euros, 8 weeks.', 8, 20000, 12, Dossier(RECORDS), shock,
                ('appearance', 'look', 'style') if shock else (), True)


def theory(claim, why, prediction):
    return {'claim': claim, 'who_benefits': 'buyers', 'why_behaviour_changes': why, 'how_value_is_captured': 'premium pricing', 'assumptions': ['the group exists'], 'predictions': [prediction]}


GOOD_THEORIES = [
    theory('Appearance stops people wearing it, so styling unlocks a new segment', 'embarrassment falls when it looks like jewellery', 'Wear rate is higher for the styled version than the plain one'),
    theory('Comfort is the real barrier during long use', 'pain makes people take it off whatever it looks like', 'Removal rate falls by at least a third with the softer fit'),
    theory('Availability at the venue door matters more than the product', 'people only think about it at the moment of need', 'Purchase share is higher at venue entrances than online'),
]


def assess(run, theory_id, evidence_id, direction, quote, kind='customer_observation', limit='It does not show what real buyers would do'):
    return run.call('assess_evidence', {'theory_id': theory_id, 'evidence_id': evidence_id, 'direction': direction, 'quote': quote, 'evidence_kind': kind, 'does_not_show': limit})


def challenge(run, theory_id='T2', query='embarrassed public settings'):
    hits = run.call('challenge_theory', {'theory_id': theory_id, 'query': query})['results']
    for hit in hits:
        run.call('read_source', {'id': hit['id']})
    return hits


def good_run(case=None):
    run = Investigation(case or make_case())
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'Grow profitably beyond industrial customers', 'constraints': ['No retail team'],
                               'alternatives': ['Launch a consumer line', 'License the technology to a partner', 'Stay industrial and do not enter']})
    for query in ('comfort removed', 'look embarrassed', 'venue entrances', 'appearance ratings predict'):
        for hit in run.call('search_evidence', {'query': query})['results']:
            run.call('read_source', {'id': hit['id']})
    for item in GOOD_THEORIES:
        run.call('add_theory', item)
    assess(run, 'T1', 'E2', 'supports', 'made them embarrassed to wear it in public')
    assess(run, 'T1', 'E5', 'contradicts', 'did not predict continued use of the widget')
    assess(run, 'T2', 'E1', 'supports', 'comfort was the main reason they removed the widget')
    assess(run, 'T2', 'E2', 'contradicts', 'made them embarrassed to wear it')
    assess(run, 'T3', 'E4', 'supports', 'placed at venue entrances')
    challenge(run)
    return run


def propose(run):
    return run.call('propose_test', {'name': 'Three-arm wear test', 'theories': ['T1', 'T2'], 'method': 'Give each group one version', 'sample': '90 adults', 'measure': 'Wear rate over 2 weeks',
                                     'prediction_by_theory': {'T1': 'Styled version worn most', 'T2': 'Soft version worn most, styling makes no difference'},
                                     'decision_rule': 'Pursue the version with a wear rate at least 20 percent higher', 'cost_eur': 5000, 'weeks': 2})


def finish(run, **changes):
    arguments = {'recommendation': 'Do not launch yet. Run the wear test first.', 'target_customer': 'People who attend loud events', 'value_proposition': 'Protection worn for long periods',
                 'favoured_theory': 'T2', 'next_action': 'Commission the three-arm wear test this quarter', 'uncertainty': 'The evidence is observational and from other products',
                 'would_change_if': ['Styled versions are worn far more'], 'evidence_ids': ['E1', 'E2'], **({'beliefs': {k: 'uncertain' for k in run.theories}} if run.staged else {})}
    return run.call('finish', {**arguments, **changes})


def completed(case=None):
    run = good_run(case)
    propose(run)
    finish(run)
    return run


def failing(run):
    return {k for k, v in run_checks(run).items() if v['passed'] is False}


def test_a_real_investigation_passes_every_check():
    assert failing(completed()) == set()


# Bad investigations fail for the right reason

def test_a_generic_swot_answer_fails():
    run = Investigation(make_case())
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'Enter the market', 'constraints': ['Competition'], 'alternatives': ['Enter the market', 'Enter it faster']})
    assert {'framing', 'finished'} <= failing(run)


def test_three_rewordings_of_one_idea_are_not_three_theories():
    run = Investigation(make_case())
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'x objective', 'constraints': ['y'], 'alternatives': ['a', 'b', 'do not enter']})
    for suffix in ('today', 'soon', 'always'):
        run.call('add_theory', theory(f'Appearance stops people wearing the product {suffix}', 'embarrassment falls when the product looks better', 'Higher wear rate'))
    assert 'theories' in failing(run)


def test_vague_predictions_are_caught():
    run = Investigation(make_case())
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'x objective', 'constraints': ['y'], 'alternatives': ['a', 'b', 'do not enter']})
    run.call('add_theory', theory('Customers will like it a lot', 'it feels nice', 'It will resonate with people'))
    run.call('add_theory', GOOD_THEORIES[1])
    assert 'testable_predictions' in failing(run)


def test_advice_is_not_a_theory():
    run = Investigation(make_case())
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'x objective', 'constraints': ['y'], 'alternatives': ['a', 'b', 'do not enter']})
    run.call('add_theory', theory('The company should target children as a new segment', 'it is a growing group', 'Higher wear rate'))
    run.call('add_theory', GOOD_THEORIES[1])
    assert 'causal_form' in failing(run)


def test_generic_business_results_are_not_testable_predictions():
    run = Investigation(make_case())
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'x objective', 'constraints': ['y'], 'alternatives': ['a', 'b', 'do not enter']})
    run.call('add_theory', theory('Parents worry about hearing', 'they fear harm', 'Increased sales and market share'))
    run.call('add_theory', GOOD_THEORIES[1])
    assert 'testable_predictions' in failing(run)


def test_never_looking_for_challenges_fails():
    run = good_run()
    run.challenge_searches = []
    propose(run)
    finish(run)
    assert 'disconfirmation' in failing(run)


def test_challenging_only_other_theories_fails():
    run = good_run()
    run.challenge_searches = [dict(s, theory_id='T1') for s in run.challenge_searches]
    propose(run)
    finish(run)
    assert 'disconfirmation' in failing(run)


def test_looking_and_finding_nothing_against_it_passes():
    """Counterevidence means looking for it. It must not reward a forced contradiction."""
    run = good_run()
    run.assessments = [a for a in run.assessments if a['direction'] != 'contradicts']
    propose(run)
    finish(run)
    assert 'disconfirmation' not in failing(run)


def test_a_challenge_search_nobody_read_fails():
    run = Investigation(make_case())
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'x objective', 'constraints': ['y'], 'alternatives': ['a', 'b', 'do not enter']})
    run.call('add_theory', GOOD_THEORIES[0])
    run.call('challenge_theory', {'theory_id': 'T1', 'query': 'comfort'})
    run.final = {'favoured_theory': 'T1'}
    assert run_checks.__globals__['disconfirmation'](run)[0] is False


def test_a_theory_resting_only_on_company_claims_fails():
    run = good_run()
    run.assessments = [a for a in run.assessments if a['theory_id'] != 'T2']
    run.call('search_evidence', {'query': 'most comfortable marketing team'})
    run.call('read_source', {'id': 'E3'})
    assess(run, 'T2', 'E3', 'supports', 'the most comfortable on the market')
    propose(run)
    finish(run)
    assert 'evidence_classes' in failing(run)


def test_a_test_where_theories_agree_fails():
    run = good_run()
    run.call('propose_test', {'name': 'Survey', 'theories': ['T1', 'T2'], 'method': 'Ask people', 'sample': '100', 'measure': 'Interest',
                              'prediction_by_theory': {'T1': 'People will be interested', 'T2': 'People will be interested'}, 'decision_rule': 'If at least half are interested', 'cost_eur': 100, 'weeks': 1})
    finish(run)
    assert 'experiment' in failing(run)


def test_a_test_with_no_decision_rule_fails():
    run = good_run()
    run.call('propose_test', {'name': 'Study', 'theories': ['T1', 'T2'], 'method': 'Run it', 'sample': '100', 'measure': 'Wear',
                              'prediction_by_theory': {'T1': 'Styled wins', 'T2': 'Soft wins'}, 'decision_rule': 'Decide afterwards', 'cost_eur': 100, 'weeks': 1})
    finish(run)
    assert 'experiment' in failing(run)


@pytest.mark.parametrize('text', ['Enter now, the market is worth EUR900m.', 'It is worth a billion euros.', 'About nine hundred million people want this.', 'We expect 15-20 percent growth.'])
def test_disguised_invented_numbers_fail(text):
    run = good_run()
    propose(run)
    finish(run, recommendation=text)
    assert 'no_invented_numbers' in failing(run)


def test_a_test_cost_cannot_launder_a_number():
    run = good_run()
    run.call('propose_test', {'name': 'Study', 'theories': ['T1', 'T2'], 'method': 'm', 'sample': '90', 'measure': 'Wear', 'prediction_by_theory': {'T1': 'Styled wins', 'T2': 'Soft wins'},
                              'decision_rule': 'at least 20 percent higher', 'cost_eur': 912, 'weeks': 2})
    finish(run, recommendation='The market is worth 912 million.')
    assert 'no_invented_numbers' in failing(run)


def test_a_plan_may_repeat_the_design_of_its_own_test():
    run = good_run()
    run.call('propose_test', {'name': 'Study', 'theories': ['T1', 'T2'], 'method': 'Two arms', 'sample': 'About 6000 visitors', 'measure': 'Wear rate over 6 weeks', 'prediction_by_theory': {'T1': 'Styled wins', 'T2': 'Soft wins'},
                              'decision_rule': 'Advance only at 80 percent or above', 'cost_eur': 18000, 'weeks': 10})
    finish(run, next_action='Run the study over 10 weeks for 18000 euros', would_change_if=['Conversion under 80 percent after 6 weeks'])
    assert 'no_invented_numbers' not in failing(run)


def test_a_plan_cannot_bring_in_a_number_of_its_own():
    run = good_run()
    propose(run)
    finish(run, next_action='Spend 777000 euros on a campaign')
    assert 'no_invented_numbers' in failing(run)


def test_a_claim_about_the_world_cannot_borrow_a_test_design_number():
    run = good_run()
    propose(run)  # costs 5000
    finish(run, value_proposition='5000 people already want this')
    assert 'no_invented_numbers' in failing(run)


def test_invented_numbers_fail():
    run = good_run()
    propose(run)
    finish(run, recommendation='Enter now, because the market is worth 912 million and growing.')
    assert 'no_invented_numbers' in failing(run)


def test_numbers_from_sources_pass():
    run = good_run()
    propose(run)
    finish(run, recommendation='Do not launch yet: one study saw a 40 percent rise, but it was observational.')
    assert 'no_invented_numbers' not in failing(run)


def test_a_next_action_that_repeats_the_recommendation_fails():
    run = good_run()
    propose(run)
    finish(run, next_action='Do not launch yet. Run the wear test first.')
    assert 'recommendation' in failing(run)


# Guards

def test_a_misquote_is_refused_and_changes_nothing():
    run = good_run()
    before = len(run.assessments)
    result = assess(run, 'T3', 'E1', 'supports', 'comfort was the only reason anybody bought it')
    assert 'not in the source' in result['error'] and len(run.assessments) == before and run.calls[-1]['category'] == 'misquote'


def test_a_paraphrase_is_refused_but_typography_is_forgiven():
    run = good_run()
    assert 'error' in assess(run, 'T3', 'E2', 'neutral', 'buyers felt embarrassed by how it looked')
    assert normalise('it’s  a—test') == "it's a-test"


def test_evidence_must_be_read_before_it_is_used():
    run = Investigation(make_case())
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'x objective', 'constraints': ['y'], 'alternatives': ['a', 'b', 'c']})
    run.call('add_theory', GOOD_THEORIES[0])
    assert assess(run, 'T1', 'E1', 'supports', 'comfort was the main reason')['error']
    assert run.calls[-1]['category'] == 'unread_evidence'


def test_an_invented_source_is_refused():
    run = good_run()
    assert run.call('read_source', {'id': 'E99'})['error'] and run.calls[-1]['category'] == 'fabricated'


def test_a_real_id_that_no_search_returned_is_refused():
    run = Investigation(make_case())
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'x objective', 'constraints': ['y'], 'alternatives': ['a', 'b', 'c']})
    assert run.call('read_source', {'id': 'E1'})['error']


def test_search_budget_holds():
    case = Case('small', 'Co', 'Q', 'B', 1, 100, 4, Dossier(RECORDS))
    run = Investigation(case)
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'x objective', 'constraints': ['y'], 'alternatives': ['a', 'b', 'c']})
    assert 'results' in run.call('search_evidence', {'query': 'comfort'})
    assert run.call('search_evidence', {'query': 'look'})['error'] and len(run.searches) == 1


def test_a_repeated_search_is_refused_and_costs_nothing():
    run = Investigation(make_case())
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'x objective', 'constraints': ['y'], 'alternatives': ['a', 'b', 'c']})
    run.call('search_evidence', {'query': 'comfort'})
    assert 'already ran' in run.call('search_evidence', {'query': ' Comfort '})['error'] and len(run.searches) == 1


def test_a_repeated_theory_is_refused():
    run = good_run()
    assert 'already have' in run.call('add_theory', GOOD_THEORIES[0])['error'] and len(run.theories) == 3


def test_test_budget_and_length_hold():
    run = good_run()
    arguments = {'name': 'Big', 'theories': ['T1', 'T2'], 'method': 'm', 'sample': 's', 'measure': 'r', 'prediction_by_theory': {'T1': 'a', 'T2': 'b'}, 'decision_rule': 'at least 10', 'cost_eur': 999999, 'weeks': 2}
    assert 'budget' in run.call('propose_test', arguments)['error']
    assert 'weeks' in run.call('propose_test', {**arguments, 'cost_eur': 10, 'weeks': 99})['error']
    assert run.tests == {}


def test_a_test_needs_a_prediction_from_each_theory():
    run = good_run()
    assert run.call('propose_test', {'name': 'x', 'theories': ['T1', 'T2'], 'method': 'm', 'sample': 's', 'measure': 'r', 'prediction_by_theory': {'T1': 'a'}, 'decision_rule': 'more', 'cost_eur': 1, 'weeks': 1})['error']


def test_a_simulated_result_cannot_support_a_recommendation():
    run = shocked()
    propose(run)
    assert 'cannot support' in finish(run, evidence_ids=['E2', 'SYN-1'])['error'] and run.final is None


def test_a_simulated_result_cannot_be_assessed_as_support():
    run = shocked()
    result = assess(run, 'T1', 'SYN-1', 'supports', 'Styled and plain designs were worn equally')
    assert 'cannot support' in result['error'] and run.calls[-1]['category'] == 'synthetic_as_evidence'


def test_a_recommendation_leaning_on_a_simulated_result_fails():
    run = shocked()
    complete(run)
    finish(run, recommendation='Do not launch: the simulated wear test proved that styling does not matter.', evidence_ids=['E1', 'E2'])
    assert 'simulated_not_used' in failing(run)


def test_a_revised_theory_must_change():
    run = good_run()
    same = run.theories['T1']['claim']
    arguments = {'theory_id': 'T1', 'status': 'revised', 'reason': 'New evidence', 'new_claim': same, 'evidence_ids': ['E1']}
    assert 'different' in run.call('revise_theory', arguments)['error'] and run.theories['T1']['status'] == 'open'
    assert run.call('revise_theory', dict(arguments, new_claim='Appearance matters only among people who already intend to wear it'))['recorded']
    assert 'already intend' in run.theories['T1']['claim']


def test_evidence_in_revisions_and_finish_must_be_read():
    run = good_run()
    assert run.call('revise_theory', {'theory_id': 'T1', 'status': 'kept', 'reason': 'x', 'new_claim': 'none', 'evidence_ids': ['never-read']})['error']
    assert finish(run, evidence_ids=['never-read'])['error'] and run.final is None


def test_a_quote_needs_real_words():
    run = good_run()
    assert 'at least 3 words' in assess(run, 'T3', 'E1', 'neutral', 'comfort              was')['error']


def test_infinite_and_negative_costs_are_refused():
    run = good_run()
    base = {'name': 'x', 'theories': ['T1', 'T2'], 'method': 'm', 'sample': 's', 'measure': 'r', 'prediction_by_theory': {'T1': 'a', 'T2': 'b'}, 'decision_rule': 'at least 10', 'weeks': 2}
    assert run.call('propose_test', dict(base, cost_eur=float('nan')))['error'] and run.call('propose_test', dict(base, cost_eur=-5))['error']


def test_an_odd_tool_name_is_refused_cleanly():
    run = good_run()
    assert run.call(['finish'], {})['error'] and run.calls[-1]['category'] == 'unknown_tool'


def test_nothing_works_after_finish():
    run = completed()
    assert run.call('search_evidence', {'query': 'x'})['error'] and run.calls[-1]['category'] == 'after_finish'


def test_the_problem_can_only_be_framed_once():
    run = good_run()
    frame = dict(run.frame)
    assert run.call('frame_problem', {'objective': 'something new', 'constraints': ['y'], 'alternatives': ['a', 'b', 'c']})['error'] and run.frame == frame


def test_theories_get_their_ids_from_the_tool():
    run = good_run()
    assert list(run.theories) == ['T1', 'T2', 'T3']


# Revision

def shocked():
    run = Investigation(make_case(SHOCK))
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'Grow profitably', 'constraints': ['None'], 'alternatives': ['Launch', 'License to a partner', 'Do not enter']})
    run.call('search_evidence', {'query': 'look embarrassed'})
    run.call('read_source', {'id': 'E2'})
    run.call('add_theory', GOOD_THEORIES[0])
    update = run.call('add_theory', GOOD_THEORIES[1])['update']
    assert update['id'] == 'SYN-1' and 'SIMULATED' in update['note']
    run.call('read_source', {'id': 'SYN-1'})
    run.call('add_theory', GOOD_THEORIES[2])
    return run


def complete(run):
    for query in ('comfort removed', 'venue entrances'):
        for hit in run.call('search_evidence', {'query': query})['results']:
            run.call('read_source', {'id': hit['id']})
    for theory_id, evidence_id, quote in (('T1', 'E2', 'made them embarrassed'), ('T2', 'E1', 'comfort was the main reason'), ('T3', 'E4', 'placed at venue entrances')):
        assess(run, theory_id, evidence_id, 'supports', quote)
    challenge(run, query='appearance ratings')
    propose(run)


def test_revision_is_not_applicable_without_new_evidence():
    assert run_checks(completed())['revision']['passed'] is None


def test_new_evidence_arrives_for_any_run_with_two_theories_even_with_no_test():
    run = shocked()
    assert run.shock_delivered and not run.tests


def test_never_receiving_new_evidence_is_not_a_failed_revision():
    run = Investigation(make_case(SHOCK))
    run.call('read_brief', {})
    assert run_checks(run)['revision']['passed'] is None


def test_ignoring_new_evidence_fails():
    run = shocked()
    complete(run)
    finish(run)
    assert 'revision' in failing(run)


def favouring_case():
    record = Record('SYN-2', 'synthetic', 'Simulated', 'n/a', 'n/a', 'SIMULATED RESULT. Styled designs were worn far more often in this simulated test.')
    return Case('fixture', 'Fixture Co', 'Q', 'B', 8, 20000, 12, Dossier(RECORDS), record, (r'\bappearance\b',), 'supports')


def favoured_run():
    run = Investigation(favouring_case())
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'Grow profitably', 'constraints': ['None'], 'alternatives': ['Launch', 'License to a partner', 'Do not enter']})
    run.call('search_evidence', {'query': 'look embarrassed'})
    run.call('read_source', {'id': 'E2'})
    run.call('add_theory', GOOD_THEORIES[0])
    run.call('add_theory', GOOD_THEORIES[1])
    run.call('read_source', {'id': 'SYN-2'})
    return run


def test_rejecting_a_theory_the_evidence_favours_fails():
    run = favoured_run()
    run.call('revise_theory', {'theory_id': 'T1', 'status': 'rejected', 'reason': 'x', 'new_claim': 'none', 'evidence_ids': ['SYN-2']})
    assert 'revision' in failing(run)


def test_keeping_a_theory_the_evidence_favours_passes():
    assert 'revision' not in failing(favoured_run())


def test_rejecting_every_theory_on_one_simulated_result_fails():
    run = shocked()
    for key in list(run.theories):
        run.call('revise_theory', {'theory_id': key, 'status': 'rejected', 'reason': 'simulated', 'new_claim': 'none', 'evidence_ids': ['SYN-1']})
    assert 'every theory' in run_checks(run)['revision']['detail']


def test_a_word_inside_another_word_does_not_count_as_affected():
    record = Record('SYN-3', 'synthetic', 'Simulated', 'n/a', 'n/a', 'SIMULATED RESULT. Nothing.')
    case = Case('fixture', 'Fixture Co', 'Q', 'B', 8, 20000, 12, Dossier(RECORDS), record, (r'\bstyle\b',))
    run = Investigation(case)
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'Grow profitably', 'constraints': ['None'], 'alternatives': ['a', 'b', 'do not enter']})
    run.call('add_theory', theory('Lifestyle buyers want it', 'it fits a lifestyle', 'Higher wear rate'))
    run.call('add_theory', GOOD_THEORIES[1])
    run.call('read_source', {'id': 'SYN-3'})
    assert run_checks(run)['revision']['passed'] is None


def test_receiving_and_not_reading_new_evidence_fails():
    run = Investigation(make_case(SHOCK))
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'Grow profitably', 'constraints': ['None'], 'alternatives': ['Launch', 'License to a partner', 'Do not enter']})
    run.call('add_theory', GOOD_THEORIES[0])
    run.call('add_theory', GOOD_THEORIES[1])
    assert 'did not read' in run_checks(run)['revision']['detail']


def test_revising_the_affected_theory_passes():
    run = shocked()
    run.call('revise_theory', {'theory_id': 'T1', 'status': 'rejected', 'reason': 'Styled and plain were worn equally in the simulation', 'new_claim': 'none', 'evidence_ids': ['SYN-1']})
    complete(run)
    finish(run)
    assert 'revision' not in failing(run)


def test_keeping_a_rejected_theory_as_favourite_fails():
    run = shocked()
    run.call('revise_theory', {'theory_id': 'T1', 'status': 'rejected', 'reason': 'Styled and plain were worn equally', 'new_claim': 'none', 'evidence_ids': ['SYN-1']})
    complete(run)
    finish(run, favoured_theory='T1')
    assert 'revision' in failing(run)


def test_revising_without_citing_the_new_evidence_fails():
    run = shocked()
    run.call('revise_theory', {'theory_id': 'T1', 'status': 'revised', 'reason': 'Changed my mind', 'new_claim': 'Something else entirely', 'evidence_ids': ['E2']})
    complete(run)
    finish(run)
    assert 'revision' in failing(run)


def test_the_workflow_mode_refuses_an_early_finish_and_says_what_is_missing():
    run = Investigation(make_case(), complete_workflow=True)
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'x objective', 'constraints': ['y'], 'alternatives': ['a', 'b', 'do not enter']})
    run.call('add_theory', GOOD_THEORIES[0])
    run.call('search_evidence', {'query': 'comfort'})
    run.call('read_source', {'id': 'E1'})
    result = finish(run, favoured_theory='T1', evidence_ids=['E1'])
    assert 'propose_test' in result['error'] and 'challenge_theory' in result['error'] and run.final is None


def test_the_workflow_mode_allows_a_complete_investigation():
    run = good_run(Case('fixture', 'Fixture Co', 'Q', 'B', 8, 20000, 12, Dossier(RECORDS)))
    run.complete_workflow = True
    propose(run)
    assert finish(run)['finished']


# Reached versus not reached

def test_a_stage_never_reached_is_not_scored_as_a_failure():
    run = Investigation(make_case())
    run.call('read_brief', {})
    checks = run_checks(run)
    assert checks['theories']['passed'] is None and checks['experiment']['passed'] is None and checks['disconfirmation']['passed'] is None


def test_finishing_without_a_stage_is_a_failure():
    run = Investigation(make_case())
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'x objective', 'constraints': ['y'], 'alternatives': ['a', 'b', 'do not enter']})
    run.call('search_evidence', {'query': 'comfort'})
    run.call('read_source', {'id': 'E1'})
    run.call('add_theory', GOOD_THEORIES[0])
    finish(run, favoured_theory='T1', evidence_ids=['E1'])
    assert {'experiment', 'theories'} <= failing(run)


def test_the_report_separates_end_to_end_from_stage_quality():
    done, stopped = record_of(completed()), record_of(Investigation(make_case()))
    result = summary([done, stopped])
    assert result['end_to_end_success'] == 1 and result['finished'] == 1
    assert result['checks']['experiment'] == {'passed': 1, 'reached': 1, 'applied': 2, 'of_all': 2}


def test_the_stopping_point_is_recorded():
    run = good_run()
    run.call('frame_problem', {'objective': 'again', 'constraints': ['y'], 'alternatives': ['a', 'b', 'c']})
    point = record_of(run)['stopping_point']
    assert point['furthest_stage'] == 'challenge_theory' and point['most_common_rejection'] == 'repeat'


# Evidence kinds, limits and premises

def annotated_case():
    records = [Record('E1', 'company_claim', 'x', URL, 'd', 'FIXTURE. Our widget is the most comfortable on the market.', kind='company_assertion', does_not_establish='demand')]
    records += [r for r in RECORDS if r.id != 'E1']
    return Case('fixture', 'Fixture Co', 'Q', 'B', 8, 20000, 12, Dossier(records), premise_records=('E4',))


def test_wrongly_labelling_a_marketing_claim_a_study_fails():
    run = Investigation(annotated_case())
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'x objective', 'constraints': ['y'], 'alternatives': ['a', 'b', 'c']})
    run.call('add_theory', GOOD_THEORIES[1])
    run.call('search_evidence', {'query': 'most comfortable'})
    run.call('read_source', {'id': 'E1'})
    assess(run, 'T1', 'E1', 'supports', 'the most comfortable on the market', kind='independent_study')
    assert 'evidence_kinds' in failing(run)


def test_a_limit_that_repeats_the_quote_fails():
    run = good_run()
    assess(run, 'T3', 'E1', 'neutral', 'comfort was the main reason they removed the widget', limit='comfort was the main reason they removed the widget')
    assert 'evidence_limits' in failing(run)


def test_an_unknown_evidence_kind_is_refused():
    run = good_run()
    assert 'evidence_kind' in assess(run, 'T3', 'E1', 'neutral', 'comfort was the main reason', kind='vibes')['error']


def test_a_limit_is_required():
    run = good_run()
    assert 'does_not_show' in assess(run, 'T3', 'E1', 'neutral', 'comfort was the main reason', limit='no')['error']


def premise_case():
    return Case('fixture', 'Fixture Co', 'Q', 'B', 8, 20000, 12, Dossier(RECORDS), premise_records=('E4',))


def test_missing_the_existing_offering_fails():
    run = good_run(premise_case())
    run.read.discard('E4')
    propose(run)
    finish(run)
    assert 'existing_offering' in failing(run)


def test_claiming_no_consumer_presence_fails_even_after_reading():
    run = good_run(premise_case())
    propose(run)
    finish(run, recommendation='The company has no consumer business today, so test the market first.')
    assert 'existing_offering' in failing(run)


def test_a_challenge_must_name_a_real_theory():
    run = good_run()
    assert run.call('challenge_theory', {'theory_id': 'T9', 'query': 'anything else'})['error']


# Replay and AuditKIT

def test_auditkit_passes_a_clean_investigation_and_fails_a_bad_one():
    case = make_case()
    bad = good_run(case)
    bad.call('frame_problem', {'objective': 'again', 'constraints': ['y'], 'alternatives': ['a', 'b', 'c']})
    result = audit([record_of(completed(case)), record_of(bad)], [case])
    assert result['guards_cleared'] == 1 and result['guards_not_cleared'] == 1


def test_a_forged_tool_result_fails_replay():
    case = make_case()
    calls = copy.deepcopy(completed(case).calls)
    next(c for c in calls if c['name'] == 'read_source')['result']['excerpt'] = 'Forged evidence.'
    with pytest.raises(ReplayMismatch):
        replay(episode_from_eventlog(to_eventlog(calls)), case)


def test_replay_reproduces_the_run():
    case = make_case()
    run = completed(case)
    again = replay(episode_from_eventlog(to_eventlog(run.calls)), case)
    assert again.final == run.final and again.theories == run.theories


# Prompts and evidence rules

def test_the_schema_covers_every_tool_and_the_prompt_names_them():
    names = {tool['properties']['name']['const'] for tool in TOOL_SCHEMA['anyOf']}
    assert names == set(Investigation(make_case())._handlers)
    assert all(name in TOOL_SIGNATURES for name in names)


def test_guidance_names_steps_and_never_answers():
    run = shocked()
    run.read.discard('SYN-1')
    run.calls.clear()
    run.assessments = [{'theory_id': k, 'direction': 'supports'} for k in run.theories]
    run.challenge_searches = [{'theory_id': 'T1'}]
    run.tests = {'X1': {}}
    run.read.update({'E1', 'E2', 'E4'})
    run.read.add('SYN-1')
    assert 'reject' not in next_step(run).lower() and 'revise' not in next_step(run).lower()


def test_prompts_share_the_same_tools():
    assert TOOL_SIGNATURES in PROMPTS['plain'] and TOOL_SIGNATURES in PROMPTS['strong']


def test_synthetic_records_must_be_labelled():
    with pytest.raises(ValueError):
        Record('S', 'synthetic', 't', 'n/a', 'n/a', 'A study showed strong demand.')


def test_sourced_records_need_a_url_and_a_real_class():
    with pytest.raises(ValueError):
        Record('S', 'verified_observation', 't', '', 'd', 'text')
    with pytest.raises(ValueError):
        Record('S', 'rumour', 't', URL, 'd', 'text')


def test_the_summary_keeps_each_dimension_separate():
    result = summary([record_of(completed())])
    assert result['checks']['framing'] == {'passed': 1, 'reached': 1, 'applied': 1, 'of_all': 1} and result['checks']['revision']['reached'] == 0


# The stage controller

def stance(run, favoured='T2'):
    return {'favoured_theory': favoured, 'recommendation': 'Test before investing', 'beliefs': {k: 'likely' if k == favoured else 'uncertain' for k in run.theories}}


def to_stage(run, name, limit=40):
    """Walks a staged fixture run forward with correct calls until it reaches the named stage."""
    steps = {
        'brief': lambda: run.call('read_brief', {}),
        'frame': lambda: run.call('frame_problem', {'objective': 'Grow beyond industrial customers', 'constraints': ['No retail team'], 'alternatives': ['Launch', 'License to a partner', 'Do not enter']}),
        'evidence': lambda: [run.call('read_source', {'id': hit['id']}) for query in ('comfort removed', 'look embarrassed', 'venue entrances') for hit in run.call('search_evidence', {'query': query})['results']],
        'theories': lambda: run.call('add_theory', GOOD_THEORIES[len(run.theories)]),
        'assessment': lambda: assess(run, *{'T1': ('T1', 'E2', 'supports', 'made them embarrassed to wear it in public'), 'T2': ('T2', 'E1', 'supports', 'comfort was the main reason they removed the widget'),
                                            'T3': ('T3', 'E4', 'supports', 'placed at venue entrances')}[next(k for k in run.theories if not any(a['theory_id'] == k for a in run.assessments))]),
        'challenge': lambda: run.call('challenge_theory', {'theory_id': 'T2', 'query': 'embarrassed public settings'}),
        'challenge_reading': lambda: [run.call('read_source', {'id': i}) for i in run.challenge_searches[-1]['found']],
        'test': lambda: propose(run),
        'position': lambda: run.call('state_position', stance(run)),
        'new_evidence': lambda: run.call('read_source', {'id': run.case.shock.id}),
        'update': lambda: run.call('revise_theory', {'theory_id': 'T1', 'status': 'revised', 'reason': 'The simulated result weakens it', 'new_claim': 'Appearance matters only for a small group', 'evidence_ids': [run.case.shock.id]}),
    }
    for _ in range(limit):
        stage = current_stage(run).name
        if stage == name:
            return run
        steps[stage]()
    raise AssertionError(f'never reached {name}, stuck at {current_stage(run).name}')


def staged_run(shock=None):
    return Investigation(make_case(shock), staged=True)


def test_a_staged_run_walks_every_stage_to_the_end():
    run = to_stage(staged_run(SHOCK), 'conclude')
    assert 'error' not in finish(run, evidence_ids=['E1', 'E2'])
    assert run.final is not None and all(c['accepted'] for c in run.calls)
    assert [c['stage'] for c in run.calls][:2] == ['brief', 'frame']


def test_a_tool_outside_its_stage_is_refused_and_changes_nothing():
    run = staged_run()
    result = run.call('finish', {})
    assert 'not at this stage' in result['error'] and run.calls[-1]['category'] == 'stage' and run.calls[-1]['stage'] == 'brief'
    run = to_stage(staged_run(), 'theories')
    assert 'not at this stage' in run.call('propose_test', {})['error'] and not run.tests


def test_finish_stays_closed_until_every_stage_has_happened():
    run = staged_run()
    for stage in ('frame', 'evidence', 'theories', 'assessment', 'challenge', 'test', 'position'):
        to_stage(run, stage)
        assert 'finish' not in current_stage(run).tools
    to_stage(run, 'conclude')
    assert 'finish' in current_stage(run).tools


def test_later_stages_leave_the_model_free_to_look_further():
    run = to_stage(staged_run(), 'test')
    assert {'search_evidence', 'read_source', 'challenge_theory', 'assess_evidence'} <= set(current_stage(run).tools)
    assert 'error' not in run.call('search_evidence', {'query': 'appearance ratings'})


def test_the_position_must_name_a_challenged_theory():
    run = to_stage(staged_run(SHOCK), 'position')
    result = run.call('state_position', stance(run, 'T1'))
    assert 'challenge_theory on T1' in result['error'] and run.position is None and not run.shock_delivered


def test_new_evidence_arrives_only_after_the_position_in_a_staged_run():
    run = to_stage(staged_run(SHOCK), 'test')
    assert len(run.theories) == 2 and not run.shock_delivered and 'SYN-1' not in run.surfaced
    to_stage(run, 'position')
    assert not run.shock_delivered
    result = run.call('state_position', stance(run))
    assert result['update']['id'] == 'SYN-1' and current_stage(run).name == 'new_evidence' and current_stage(run).tools == ('read_source',)


def test_an_unstaged_run_keeps_its_delivery_point():
    run = good_run(make_case(SHOCK))
    assert run.shock_delivered and 'state_position' not in run._handlers


def test_keeping_a_theory_is_a_valid_response_to_new_evidence():
    run = to_stage(staged_run(SHOCK), 'update')
    assert 'kept' in current_stage(run).instruction and 'rejected' in current_stage(run).instruction
    assert 'error' not in run.call('revise_theory', {'theory_id': 'T2', 'status': 'kept', 'reason': 'It does not bear on comfort', 'new_claim': 'none', 'evidence_ids': ['SYN-1']})
    assert current_stage(run).name == 'conclude'


def test_the_instructions_never_say_which_way_to_respond():
    run = to_stage(staged_run(SHOCK), 'update')
    text = current_stage(run).instruction.lower()
    assert not any(word in text for word in ('undermin', 'weaken', 'against', 'supports', 'favours', 'wrong'))


def test_the_last_search_is_kept_for_the_challenge():
    case = Case('fixture', 'Fixture Co', 'Q', 'Brief', 2, 20000, 12, Dossier(RECORDS))
    run = Investigation(case, staged=True)
    run.call('read_brief', {})
    to_stage(run, 'evidence')
    assert 'error' not in run.call('search_evidence', {'query': 'comfort'})
    assert 'kept for challenge_theory' in run.call('search_evidence', {'query': 'venue'})['error'] and run.calls[-1]['category'] == 'budget'


def test_the_schema_offers_only_the_open_tools():
    run = to_stage(staged_run(), 'position')
    names = {tool['properties']['name']['const'] for tool in schema_for(run)['anyOf']}
    assert names <= set(current_stage(run).tools) and 'state_position' in names and 'finish' not in names
    assert guidance(run)['open_tools'] == list(current_stage(run).tools)


def test_a_staged_run_replays_exactly_including_its_refusals():
    case = make_case(SHOCK)
    run = to_stage(Investigation(case, staged=True), 'conclude')
    run.call('propose_test', {})  # still open here, and refused for its arguments
    to_stage(run, 'conclude')
    run.calls.insert(0, run.calls[0])  # replay must notice a log that was tampered with
    with pytest.raises(ReplayMismatch):
        replay(episode_from_eventlog(to_eventlog(run.calls)), case, staged=True)
    del run.calls[0]
    finish(run)
    again = replay(episode_from_eventlog(to_eventlog(run.calls)), case, staged=True)
    assert again.final == run.final and again.position == run.position


def test_a_refused_finish_is_counted_on_its_own():
    run = staged_run()
    run.call('finish', {})
    run.call('finish', {})
    assert record_of(run)['stopping_point']['rejected_finishes'] == 2
    assert summary([record_of(run)])['rejected_finishes'] == 2


# Coverage and attribution

def test_avoiding_the_new_evidence_is_not_clearing_the_guards():
    case = make_case(SHOCK)
    run = good_run(case)  # holds a theory it bears on, and reads nothing new
    propose(run)
    run.call('read_source', {'id': 'SYN-1'})
    run.call('revise_theory', {'theory_id': 'T1', 'status': 'revised', 'reason': 'Weaker now', 'new_claim': 'Appearance matters for few', 'evidence_ids': ['SYN-1']})
    finish(run, recommendation='Do not launch yet. Run the trial first.')
    assert guards_cleared(run_checks(run))
    case_without_target = Case('fixture', 'Fixture Co', 'Q', 'Brief', 8, 20000, 12, Dossier(RECORDS), SHOCK, ('nothing that matches',), simulated=True)
    avoided = good_run(case_without_target)
    propose(avoided)
    avoided.call('read_source', {'id': 'SYN-1'})
    avoided.call('revise_theory', {'theory_id': 'T2', 'status': 'kept', 'reason': 'It does not bear on this', 'new_claim': 'none', 'evidence_ids': ['SYN-1']})
    finish(avoided, recommendation='Do not launch yet. Run the trial first.')
    checks = run_checks(avoided)
    assert checks['revision']['passed'] is None and checks['revision']['status'] == 'not_evaluated' and not guards_cleared(checks)


def test_a_check_with_nothing_to_apply_to_stays_out_of_the_way():
    checks = run_checks(completed())
    assert checks['revision']['status'] == 'not_applicable' and guards_cleared(checks)


def test_a_run_that_supported_nothing_has_not_cleared_the_guards():
    run = completed()
    run.assessments = [a for a in run.assessments if a['direction'] != 'supports']
    checks = run_checks(run)
    assert checks['evidence_classes']['status'] == 'not_evaluated' and not guards_cleared(checks)


def test_a_revised_theory_still_counts_as_affected():
    case = make_case(SHOCK)
    run = to_stage(Investigation(case, staged=True), 'update')
    run.call('revise_theory', {'theory_id': 'T1', 'status': 'revised', 'reason': 'Weaker', 'new_claim': 'Only a few care', 'evidence_ids': ['SYN-1']})
    assert 'T1' in record_of(run)['coverage']['shock']['affected_theories']


def test_coverage_reports_the_change_of_mind_within_a_run():
    run = to_stage(staged_run(SHOCK), 'conclude')
    finish(run, favoured_theory='T1')
    shock = record_of(run)['coverage']['shock']
    assert shock['favoured_before'] == 'T2' and shock['favoured_after'] == 'T1' and shock['favoured_changed'] and shock['delivered'] and shock['read'] and shock['cited_in_revision']
    assert summary([record_of(run)])['shock_coverage']['favoured_changed'] == 1


def test_coverage_says_whether_the_evidence_touched_the_favoured_theory():
    for targets, touched in ((('removal', 'pain'), True), (('venue',), False)):
        case = Case('fixture', 'Fixture Co', 'Q', 'Brief', 8, 20000, 12, Dossier(RECORDS), SHOCK, targets, simulated=True)
        run = to_stage(Investigation(case, staged=True), 'new_evidence')
        assert run.position['favoured_theory'] == 'T2' and record_of(run)['coverage']['shock']['bears_on_favoured'] is touched


def test_the_model_log_leaves_out_what_the_harness_did():
    run = completed()
    run.calls[2]['harness'] = True
    assert len(to_eventlog(run.calls, model_only=True).events) == len(to_eventlog(run.calls).events) - 2
    assert record_of(run)['stopping_point']['harness_actions'] == 1


def test_auditkit_replays_harness_calls_but_does_not_credit_the_model_with_them():
    case = make_case()
    run = completed(case)
    for call in run.calls:
        if call['name'] == 'search_evidence':
            call['harness'] = True
    result = audit([record_of(run)], [case])
    assert result['replay_mismatches'] == 0 and result['guards_cleared'] == 1


# Claude is a control and a judge, and never a teacher

class FakeUsage:
    input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens = 1000, 0, 0, 1000


class FakeBlock:
    def __init__(self, kind, text):
        self.type, self.text = kind, text

    def to_dict(self):
        return {'type': self.type, 'text': self.text}


class FakeClient:
    def __init__(self, replies):
        self.replies, self.sent = list(replies), []
        self.messages = self

    def create(self, **request):
        self.sent.append(copy.deepcopy(request))
        return type('Reply', (), {'usage': FakeUsage(), 'stop_reason': 'end_turn', 'content': [FakeBlock('thinking', ''), FakeBlock('text', self.replies.pop(0))]})()


def turns_of(case, calls):
    replay = Investigation(case, staged=True)
    return [{'text': json.dumps({'name': c['name'], 'arguments': c['arguments']}), 'tool_result': replay.call(c['name'], c['arguments'])} for c in calls]


def manifest_with(tmp_path, turns, case, backend='llama', weights=AYA_WEIGHTS, protocol='p'):
    path = tmp_path / 'provenance.jsonl'
    record_provenance(turns, case, {'backend': backend, 'weights_sha256': weights, 'id': 'm'}, protocol, path)
    return path


def staged_teacher_turns():
    case = make_case(SHOCK)
    run = to_stage(Investigation(case, staged=True), 'conclude')
    finish(run)
    return case, turns_of(case, run.calls)


def test_only_a_listed_teacher_can_become_training_data(tmp_path):
    case, turns = staged_teacher_turns()
    assert training_source(turns, case, 'p', manifest_with(tmp_path, turns, case))


@pytest.mark.parametrize('backend, weights', [('claude', None), ('claude', AYA_WEIGHTS), ('llama', 'not-a-listed-hash'), ('llama', None)])
def test_any_other_source_is_refused(tmp_path, backend, weights):
    case, turns = staged_teacher_turns()
    with pytest.raises(ValueError):
        training_source(turns, case, 'p', manifest_with(tmp_path, turns, case, backend, weights))


def test_an_episode_outside_the_manifest_is_refused(tmp_path):
    case, turns = staged_teacher_turns()
    with pytest.raises(ValueError):
        training_source(turns, case, 'p', tmp_path / 'nothing.jsonl')


def test_a_claude_episode_stays_refused_if_a_teacher_entry_is_added_later(tmp_path):
    case, turns = staged_teacher_turns()
    path = manifest_with(tmp_path, turns, case, 'claude', None)
    record_provenance(turns, case, {'backend': 'llama', 'weights_sha256': AYA_WEIGHTS, 'id': 'm'}, 'p', path)
    with pytest.raises(ValueError):
        training_source(turns, case, 'p', path)


def test_the_episode_id_binds_text_results_case_and_protocol():
    case, turns = staged_teacher_turns()
    base = episode_id(turns, case, 'p')
    edited = copy.deepcopy(turns)
    edited[0]['text'] = edited[0]['text'].replace('{', '{"analysis": "added later", ', 1)
    forged = copy.deepcopy(turns)
    forged[2]['tool_result'] = {'forged': True}
    assert episode_id(turns[:1], case, 'p') != base and episode_id(edited, case, 'p') != base and episode_id(forged, case, 'p') != base
    assert episode_id(turns, case, 'other protocol') != base and episode_id(turns, make_case(), 'p') != base
    relabelled = copy.deepcopy(turns)
    relabelled[0]['label'] = 'aya-expanse-32b'
    assert episode_id(relabelled, case, 'p') == base


def test_a_control_run_goes_through_the_same_guards_and_keeps_its_reply_blocks(tmp_path):
    client = FakeClient(['```json\n{"name": "read_brief", "arguments": {}}\n```', '{"name": "finish", "arguments": {}}'])
    backend = Claude('test', 1, client=client, ledger=tmp_path / 'ledger.jsonl')
    play(make_case(), backend, 'SYSTEM', 2, 4, 100, True, None, staged=True)
    assert client.sent[0]['system'] == 'SYSTEM' and client.sent[0]['messages'][0]['role'] == 'user'
    assert client.sent[1]['messages'][1]['content'][0]['type'] == 'thinking'  # sent back unchanged


def test_spending_is_recorded_and_the_caps_hold(tmp_path):
    ledger = tmp_path / 'ledger.jsonl'
    backend = Claude('test', .01, client=FakeClient(['{}', '{}']), ledger=ledger)
    backend([{'role': 'system', 'content': 's'}, {'role': 'user', 'content': 'u'}], 0, 1, None, 0)
    assert spent(ledger) == pytest.approx(.024) and cost('claude-opus-5-5', {'input': 1e6, 'cache_write': 0, 'cache_read': 0, 'output': 0}) == 4
    with pytest.raises(BudgetExceeded):
        backend([{'role': 'system', 'content': 's'}, {'role': 'user', 'content': 'u'}], 0, 1, None, 0)
    fresh = Claude('test', 100, client=FakeClient(['{}']), ledger=ledger)
    ledger.write_text('{"usd": 60.0}\n')
    with pytest.raises(BudgetExceeded):
        fresh([{'role': 'system', 'content': 's'}, {'role': 'user', 'content': 'u'}], 0, 1, None, 0)


def test_a_reply_that_is_not_a_call_is_refused_not_a_crash():
    assert parse_call('[1, 2]', True)[0] is None and parse_call('{"name": "x"}', True)[0] is None


def fields(run, name):
    tool = next(t for t in schema_for(run)['anyOf'] if t['properties']['name']['const'] == name)
    return tool['properties']['arguments']['properties']


def test_the_schema_can_only_name_ids_that_exist():
    run = to_stage(staged_run(SHOCK), 'position')
    assert fields(run, 'state_position')['favoured_theory'] == {'enum': ['T1', 'T2']}  # T1 is unchallenged, and refused on the record
    assert set(fields(run, 'state_position')['beliefs']['required']) == {'T1', 'T2'}
    assert fields(run, 'assess_evidence')['theory_id'] == {'enum': ['T1', 'T2']} and set(fields(run, 'assess_evidence')['evidence_id']['enum']) == run.read
    to_stage(run, 'conclude')
    assert 'SYN-1' in fields(run, 'finish')['evidence_ids']['items']['enum'] and fields(run, 'finish')['beliefs']['properties']['T1'] == {'enum': ['very unlikely', 'unlikely', 'uncertain', 'likely', 'very likely']}
    assert finish(run, evidence_ids=['E1', 'SYN-1'])['error'] and run.calls[-1]['category'] == 'synthetic_as_evidence'  # still the model's mistake to make


def test_a_tool_with_nothing_to_act_on_is_not_offered():
    run = to_stage(staged_run(), 'evidence')
    assert [t['properties']['name']['const'] for t in schema_for(run)['anyOf']] == ['search_evidence']


def test_the_update_stage_cannot_loop_on_assessments():
    run = to_stage(staged_run(SHOCK), 'update')
    assert current_stage(run).tools == ('revise_theory',)


def test_a_staged_finish_records_beliefs_beside_the_earlier_position():
    run = to_stage(staged_run(SHOCK), 'conclude')
    finish(run, beliefs={'T1': 'unlikely', 'T2': 'very likely'})
    shock = record_of(run)['coverage']['shock']
    assert shock['beliefs_before'] == {'T1': 'uncertain', 'T2': 'likely'} and shock['beliefs_after'] == {'T1': 'unlikely', 'T2': 'very likely'}


@pytest.mark.parametrize('beliefs', [{'T1': 'likely'}, {'T1': 'likely', 'T2': 60}, {'T1': 'likely', 'T2': 'probably'}, {'T1': 'likely', 'T2': 'likely', 'T9': 'likely'}, 'high'])
def test_beliefs_must_cover_each_theory_with_a_whole_number(beliefs):
    run = to_stage(staged_run(), 'position')
    assert 'beliefs needs' in run.call('state_position', {**stance(run), 'beliefs': beliefs})['error'] and run.position is None


def test_the_harness_never_changes_the_beliefs_it_is_given():
    run = to_stage(staged_run(SHOCK), 'position')
    given = stance(run)
    run.call('state_position', given)
    assert run.position['beliefs'] == given['beliefs']


def test_a_turn_hook_sees_each_step():
    seen = []
    play(make_case(), lambda *_: {'text': '{"name": "read_brief", "arguments": {}}'}, 'S', 2, 4, 100, True, None, staged=True, on_turn=lambda run: seen.append(len(run.calls)))
    assert seen == [1, 2]


def test_resources_are_totalled_across_a_report():
    record = record_of(Investigation(make_case()), {'turns': [{'prompt_tokens': 10, 'completion_tokens': 2, 'seconds': 1.5}, {'prompt_tokens': 5, 'completion_tokens': 1, 'seconds': .5, 'usd': .01}]})
    assert summary([record])['resources'] == {'prompt_tokens': 15, 'completion_tokens': 3, 'seconds': 2.0, 'usd': .01}


# How a run responds to new evidence

def respond_to(direction, targets, status, theory_id='T1'):
    case = Case('fixture', 'Fixture Co', 'Q', 'Brief', 8, 20000, 12, Dossier(RECORDS), SHOCK, targets, direction, True)
    run = to_stage(Investigation(case, staged=True), 'update')
    run.call('revise_theory', {'theory_id': theory_id, 'status': status, 'reason': 'Because of the result', 'new_claim': 'A narrower claim' if status == 'revised' else 'none', 'evidence_ids': ['SYN-1']})
    return run


APPEARANCE = ('appearance', 'look', 'style')


def test_keeping_a_theory_after_evidence_against_it_can_pass():
    assert run_checks(respond_to('undermines', APPEARANCE, 'kept'))['revision']['passed'] is True


def test_rejecting_a_theory_the_evidence_favoured_fails():
    assert run_checks(respond_to('supports', APPEARANCE, 'rejected'))['revision']['passed'] is False


@pytest.mark.parametrize('status, passes', [('kept', True), ('revised', False), ('rejected', False)])
def test_a_change_on_irrelevant_evidence_fails(status, passes):
    run = respond_to('irrelevant', (), status)
    assert run_checks(run)['revision']['passed'] is passes and record_of(run)['coverage']['shock']['affected_theories'] == []


def test_rejecting_everything_on_one_result_fails():
    run = respond_to('undermines', APPEARANCE, 'rejected')
    for theory in ('T2', 'T3'):
        run.call('revise_theory', {'theory_id': theory, 'status': 'rejected', 'reason': 'Because', 'new_claim': 'none', 'evidence_ids': ['SYN-1']})
    assert run_checks(run)['revision']['passed'] is False


def test_the_ids_and_titles_of_new_evidence_do_not_give_the_direction_away():
    from aemon.environment.cases import load_cases
    shocks = [c.shock for c in load_cases() if c.shock]
    assert {c.shock_direction for c in load_cases() if c.shock} == {'undermines', 'supports', 'irrelevant'}
    assert not any(word in f'{s.id} {s.title}'.lower() for s in shocks for word in ('favour', 'support', 'undermin', 'against', 'irrelevant'))


def test_a_recovery_is_counted_and_the_harness_repairs_nothing():
    run = to_stage(staged_run(), 'position')
    bad = stance(run, 'T1')
    run.call('state_position', bad)
    run.call('state_position', {**bad, 'favoured_theory': 'T2'})
    point = record_of(run)['stopping_point']
    assert point['refused'] == 1 and point['recovered_after_refusal'] == 1 and run.calls[-2]['arguments'] == bad and summary([record_of(run)])['harness_corrections'] == 0


def test_the_protocol_id_ignores_the_model_and_tracks_everything_else():
    from aemon.agent.records import protocol_of
    base = protocol_of('prompt', {'max_tokens': 520})
    assert base == protocol_of('prompt', {'max_tokens': 520})
    assert protocol_of('other', {'max_tokens': 520})['id'] != base['id'] and protocol_of('prompt', {'max_tokens': 400})['id'] != base['id']
    assert {'controller', 'tools', 'checks', 'runner', 'constants', 'prompts', 'evidence', 'cases', 'chat', 'system_prompt', 'generation'} == set(base['parts'])


def test_two_runs_on_different_cases_never_look_matched():
    from aemon.agent.records import matched, suite_of
    a, b = make_case(), make_case(SHOCK)
    assert suite_of([a], 1)['id'] != suite_of([b], 1)['id'] != suite_of([a, b], 1)['id']
    assert suite_of([a, b], 1)['id'] != suite_of([b, a], 1)['id'] and suite_of([a], 1)['id'] != suite_of([a], 2)['id']
    run = {'protocol': {'id': 'p'}, 'suite': {'id': 's'}, 'model': {'id': 'base'}}
    assert matched(run, {**run, 'model': {'id': 'adapter'}}) and not matched(run, {**run, 'suite': {'id': 'other'}}) and not matched(run, run)


def test_the_model_identity_comes_from_what_was_served():
    from aemon.agent.records import model_of
    props = {'build_info': 'b12032-dde879bc4', 'chat_template': 'x', 'model_path': '/m/a.gguf'}
    a, b = model_of('llama', 'same label', 'hash-a', props), model_of('llama', 'same label', 'hash-b', props)
    assert a['id'] != b['id'] and a['file'] == 'a.gguf' and a['build'] == 'b12032-dde879bc4'


def test_diagnostics_are_reported_without_gating():
    from aemon.environment.checks import DIAGNOSTIC
    run = completed()
    checks = run_checks(run)
    for name in DIAGNOSTIC:
        checks[name] = {'passed': False, 'detail': 'x', 'status': 'failed'}
    assert guards_cleared(checks)
    checks['experiment'] = {'passed': False, 'detail': 'x', 'status': 'failed'}
    assert not guards_cleared(checks)


def test_a_descriptive_must_is_no_longer_advice():
    run = good_run()
    run.call('add_theory', theory('Comfort must be high before wear rises, so the barrier is physical', 'pain removes the plug', 'Removal falls by a third'))
    assert not any('T4' in str(v) for v in [run_checks(run)['causal_form']['detail']])


def test_the_teacher_prompt_is_general_and_keeps_the_same_tools():
    from aemon.common.constants.prompts import STRUCTURED
    teacher = PROMPTS['teacher']
    assert 'teacher' in STRUCTURED and teacher.startswith(PROMPTS['staged'])
    assert not any(name in teacher for name in ('Moldex', 'Cotral', 'Hellberg', 'hearing', 'earplug', 'SYN-'))


def test_an_attempt_changes_the_seed_and_a_retry_still_uses_its_own_temperature():
    seen = []

    def respond(messages, seed, max_tokens, schema, temperature):
        seen.append((seed, temperature))
        return {'text': '{"name": "nothing", "arguments": {}}'}
    play(make_case(), respond, 'S', 2, 4, 100, True, None, staged=True, temperature=.5, attempt=2)
    start = sum(map(ord, 'fixture')) + 2000
    assert seen == [(start, .5), (start + 1, .4)]


# Agreed with Codex's review of #17

def test_silence_on_favourable_evidence_does_not_pass():
    case = Case('fixture', 'Fixture Co', 'Q', 'Brief', 8, 20000, 12, Dossier(RECORDS), SHOCK, APPEARANCE, 'supports', True)
    run = good_run(case)
    propose(run)
    run.call('read_source', {'id': 'SYN-1'})
    finish(run)
    assert run_checks(run)['revision']['passed'] is False and 'never said' in run_checks(run)['revision']['detail']


def test_a_response_only_to_an_unaffected_theory_fails():
    case = Case('fixture', 'Fixture Co', 'Q', 'Brief', 8, 20000, 12, Dossier(RECORDS), SHOCK, ('venue',), 'undermines', True)
    run = to_stage(Investigation(case, staged=True), 'update')
    run.call('revise_theory', {'theory_id': 'T1', 'status': 'kept', 'reason': 'Nothing changes', 'new_claim': 'none', 'evidence_ids': ['SYN-1']})
    assert record_of(run)['coverage']['shock']['affected_addressed'] == []


def test_the_wrong_theory_check_uses_what_was_addressed():
    theories = [GOOD_THEORIES[0], GOOD_THEORIES[2]]  # appearance and venue
    case = Case('fixture', 'Fixture Co', 'Q', 'Brief', 8, 20000, 12, Dossier(RECORDS), SHOCK, ('venue',), 'undermines', True)
    run = Investigation(case, staged=True)
    run.theories = {'T1': {**theories[0], 'status': 'open', 'first_claim': theories[0]['claim']}, 'T2': {**theories[1], 'status': 'open', 'first_claim': theories[1]['claim']}}
    run.shock_delivered, run.read = True, {'SYN-1'}
    run.revisions = [{'theory_id': 'T1', 'status': 'kept', 'reason': 'x', 'new_claim': None, 'evidence_ids': ['SYN-1']}]
    assert run_checks(run)['revision']['passed'] is False and 'wrong theories' in run_checks(run)['revision']['detail']
    run.revisions[0]['theory_id'] = 'T2'
    assert run_checks(run)['revision']['passed'] is True


def test_stopping_before_a_response_is_not_a_failed_response():
    run = to_stage(staged_run(SHOCK), 'update')
    assert run_checks(run)['revision']['status'] == 'not_evaluated'


def test_two_distinct_theories_are_enough_and_a_third_stays_open():
    run = to_stage(staged_run(), 'assessment')
    assert len(run.theories) == 2 and 'add_theory' in current_stage(run).tools
    assert run.call('add_theory', GOOD_THEORIES[2])['theory_id'] == 'T3'
    run = to_stage(staged_run(), 'conclude')
    finish(run)
    assert run_checks(run)['theories']['passed'] is True


def test_one_theory_is_still_not_enough():
    run = staged_run()
    to_stage(run, 'theories')
    run.call('add_theory', GOOD_THEORIES[0])
    assert current_stage(run).name == 'theories'


def declined(warranted):
    case = Case('fixture', 'Fixture Co', 'Q', 'Brief', 8, 20000, 12, Dossier(RECORDS), test_warranted=warranted)
    run = to_stage(Investigation(case, staged=True), 'test')
    assert 'decline_test' in current_stage(run).tools
    assert 'error' not in run.call('decline_test', {'reason': 'The evidence already settles it'})
    return run


def test_declining_a_warranted_test_fails_and_declining_an_unwarranted_one_passes():
    assert run_checks(declined(True))['experiment']['passed'] is False
    assert run_checks(declined(False))['experiment']['passed'] is True


def test_declining_moves_on_and_is_recorded():
    run = declined(True)
    assert current_stage(run).name == 'position' and record_of(run)['test_declined'] and record_of(run)['coverage']['test_declined']


def test_proposing_a_test_the_case_does_not_warrant_fails():
    case = Case('fixture', 'Fixture Co', 'Q', 'Brief', 8, 20000, 12, Dossier(RECORDS), test_warranted=False)
    run = to_stage(Investigation(case, staged=True), 'test')
    propose(run)
    assert run_checks(run)['experiment']['passed'] is False


def test_a_source_can_be_read_again_at_no_search_cost():
    run = to_stage(staged_run(), 'assessment')
    used, source = len(run.searches), sorted(run.read)[0]
    assert source in fields(run, 'read_source')['id']['enum'] and 'error' not in run.call('read_source', {'id': source}) and len(run.searches) == used


def test_hitting_the_context_limit_is_a_stop_and_not_a_fault():
    import io
    import urllib.error

    def full(*_):
        raise urllib.error.HTTPError('u', 400, 'bad', {}, io.BytesIO(b'request (8256 tokens) exceeds the available context size'))
    assert play(make_case(), full, 'S', 2, 4, 100, True, None, staged=True)[1]['stop_reason'] == 'context limit'


def test_any_other_refusal_stays_a_fault():
    import io
    import urllib.error

    def broken(*_):
        raise urllib.error.HTTPError('u', 500, 'bad', {}, io.BytesIO(b'something else'))
    assert play(make_case(), broken, 'S', 2, 4, 100, True, None, staged=True)[1]['stop_reason'] == 'server refused: 500'


# Development variants: reasoning before the call, and a compact state

def test_a_reasoned_schema_puts_the_analysis_first_and_requires_it():
    run = to_stage(staged_run(), 'frame')
    tool = schema_for(run, True)['anyOf'][0]
    assert list(tool['properties'])[0] == 'analysis' and 'analysis' in tool['required']
    assert 'analysis' not in schema_for(run)['anyOf'][0]['properties']


def test_a_compact_run_shows_state_and_not_a_transcript():
    seen = []

    def respond(messages, seed, max_tokens, schema, temperature):
        seen.append(copy.deepcopy(messages))
        return {'text': '{"analysis": "start", "name": "read_brief", "arguments": {}}'}
    play(make_case(), respond, 'S', 3, 4, 100, True, None, staged=True, compact=True, reasoned=True)
    assert len(seen[-1]) == 2 and seen[-1][1]['content'].startswith('Current state: ') and 'already_tried' in seen[-1][1]['content']


def test_the_compact_state_lists_refused_calls_and_quotable_excerpts():
    from aemon.agent.state_view import state_of
    run = to_stage(staged_run(), 'assessment')
    run.call('add_theory', GOOD_THEORIES[0])
    text = state_of(run, {'error': 'x'})
    assert 'you already have' not in text and '"tool": "add_theory"' in text and run._record(sorted(run.read)[0]).excerpt[:30] in text


def test_the_state_copies_the_record_and_interprets_nothing():
    from aemon.agent.state_view import state_of
    run = to_stage(staged_run(SHOCK), 'update')
    text = state_of(run, {})
    assert 'SYN-1' in text and 'undermin' not in text.lower()


def test_a_thinking_block_is_kept_and_the_call_after_it_still_parses():
    from aemon.agent.backends.llama_client import split_thinking
    call, thinking = split_thinking('<|START_THINKING|>I should read the brief.<|END_THINKING|>{"name": "read_brief", "arguments": {}}')
    assert parse_call(call, True)[0]['name'] == 'read_brief' and thinking == 'I should read the brief.'
    assert split_thinking('{"name": "read_brief"}') == ('{"name": "read_brief"}', None)


def test_rereading_cannot_meet_the_reading_minimum():
    run = to_stage(staged_run(), 'evidence')
    hits = run.call('search_evidence', {'query': 'comfort removed'})['results']
    run.call('read_source', {'id': hits[0]['id']})
    if len(run.read) < 3 and any(i not in run.read for i in run.surfaced):
        assert hits[0]['id'] not in fields(run, 'read_source')['id']['enum']


# Training rows

def scripted_teacher(case, manifest, backend='llama', weights=AYA_WEIGHTS):
    """A fixture standing in for a teacher: a scripted staged run, recorded the way the runner records it."""
    run = to_stage(Investigation(case, staged=True), 'conclude')
    finish(run)
    turns = turns_of(case, run.calls)
    record = dict(record_of(run, {'turns': turns, 'stop_reason': 'finished'}))
    record_provenance(turns, case, {'backend': backend, 'weights_sha256': weights, 'id': 'm'}, 'p', manifest)
    return record


def build_from(tmp_path, record, case, **kwargs):
    from aemon.rows import build_rows as rows_module
    path = tmp_path / 'report.json'
    path.write_text(json.dumps({'protocol': {'id': 'p'}, 'records': [record]}))
    original = rows_module.load_cases
    rows_module.load_cases = lambda: [case]
    try:
        return rows_module.build([path], tmp_path / 'provenance.jsonl', **kwargs)
    finally:
        rows_module.load_cases = original


def test_a_teacher_episode_becomes_one_row_per_accepted_call(tmp_path):
    case = make_case(SHOCK)
    record = scripted_teacher(case, tmp_path / 'provenance.jsonl')
    rows, decisions = build_from(tmp_path, record, case)
    accepted = sum(c['accepted'] for c in record['calls'])
    assert decisions[0]['accepted'] and len(rows) == accepted
    assert all(r['messages'][0]['content'] == PROMPTS['staged'] and r['messages'][r['target_index']]['role'] == 'assistant' for r in rows)
    assert json.loads(rows[-1]['messages'][-1]['content'])['name'] == 'finish'


def test_a_refused_call_is_context_and_never_a_target(tmp_path):
    case = make_case(SHOCK)
    run = Investigation(case, staged=True)
    run.call('finish', {})
    to_stage(run, 'conclude')
    finish(run)
    turns = turns_of(case, run.calls)
    record = dict(record_of(run, {'turns': turns, 'stop_reason': 'finished'}))
    record_provenance(turns, case, {'backend': 'llama', 'weights_sha256': AYA_WEIGHTS, 'id': 'm'}, 'p', tmp_path / 'provenance.jsonl')
    rows, decisions = build_from(tmp_path, record, case)
    assert decisions[0]['accepted']
    assert not any(json.loads(r['messages'][-1]['content']) == {'name': 'finish', 'arguments': {}} for r in rows)
    assert any('not at this stage' in m['content'] for m in rows[-1]['messages'] if m['role'] == 'user')


def test_a_tampered_record_is_rejected_on_replay(tmp_path):
    case = make_case(SHOCK)
    record = scripted_teacher(case, tmp_path / 'provenance.jsonl')
    record['model_turns'][3]['tool_result'] = {'forged': True}
    rows, decisions = build_from(tmp_path, record, case)
    assert not rows and not decisions[0]['accepted'] and 'manifest' in decisions[0]['reason']


@pytest.mark.parametrize('backend, weights', [('claude', None), ('llama', 'not-a-teacher')])
def test_rows_are_never_built_from_another_source(tmp_path, backend, weights):
    case = make_case(SHOCK)
    record = scripted_teacher(case, tmp_path / 'provenance.jsonl', backend, weights)
    rows, decisions = build_from(tmp_path, record, case)
    assert not rows and not decisions[0]['accepted'] and 'teacher' in decisions[0]['reason']


def test_held_out_cases_and_unfinished_runs_give_no_rows(tmp_path):
    case = make_case(SHOCK)
    record = scripted_teacher(case, tmp_path / 'provenance.jsonl')
    assert build_from(tmp_path, record, case, exclude={'fixture'})[1][0]['reason'] == 'held-out case'
    assert build_from(tmp_path, record, case)[1][0]['accepted']


def test_compact_rows_hold_the_state_and_not_a_transcript(tmp_path):
    case = make_case(SHOCK)
    record = scripted_teacher(case, tmp_path / 'provenance.jsonl')
    rows, _ = build_from(tmp_path, record, case, compact=True)
    assert all(len(r['messages']) == 3 for r in rows[1:]) and rows[-1]['messages'][1]['content'].startswith('Current state: ')


def test_loss_falls_on_the_target_reply_only():
    from aemon.rows.build_rows import labels_for

    class Words:
        def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
            return ' '.join(f"<{m['role']}> {m['content']}" for m in messages) + (' <assistant>' if add_generation_prompt else '')

        def __call__(self, text, add_special_tokens=False):
            return {'input_ids': text.split()}
    row = {'messages': [{'role': 'system', 'content': 's'}, {'role': 'user', 'content': 'u v'}, {'role': 'assistant', 'content': 'call here'}], 'target_index': 2}
    out = labels_for(Words(), row, 50)
    assert [t for t, l in zip(out['input_ids'], out['labels']) if l != -100] == ['call', 'here']
    with pytest.raises(ValueError):
        labels_for(Words(), row, 3)


# Codex's probes on #17, kept as tests

def test_a_truncated_reply_stream_is_refused_even_with_its_original_calls_and_final(tmp_path):
    case = make_case(SHOCK)
    record = scripted_teacher(case, tmp_path / 'provenance.jsonl')
    record['model_turns'] = record['model_turns'][:1]
    rows, decisions = build_from(tmp_path, record, case)
    assert not rows and not decisions[0]['accepted']


def test_text_added_to_a_target_after_collection_is_refused(tmp_path):
    case = make_case(SHOCK)
    record = scripted_teacher(case, tmp_path / 'provenance.jsonl')
    record['model_turns'][0]['text'] = '{"analysis": "added later", ' + record['model_turns'][0]['text'][1:]
    rows, decisions = build_from(tmp_path, record, case)
    assert not rows and not decisions[0]['accepted']


def test_a_stream_that_replays_but_never_finishes_is_refused(tmp_path):
    case = make_case(SHOCK)
    run = to_stage(Investigation(case, staged=True), 'conclude')
    turns = turns_of(case, run.calls)
    record = dict(record_of(run, {'turns': turns, 'stop_reason': 'turn limit'}), final={'pretend': True})
    record_provenance(turns, case, {'backend': 'llama', 'weights_sha256': AYA_WEIGHTS, 'id': 'm'}, 'p', tmp_path / 'provenance.jsonl')
    rows, decisions = build_from(tmp_path, record, case)
    assert not rows and 'accepted finish' in decisions[0]['reason']


def test_rows_record_their_stage():
    from aemon.rows.build_rows import transcript
    case = make_case(SHOCK)
    run = to_stage(Investigation(case, staged=True), 'conclude')
    finish(run)
    turns, _ = transcript(dict(record_of(run, {'turns': turns_of(case, run.calls)})), case, PROMPTS['staged'])
    stages = [t[-1]['stage'] for t in turns]
    assert stages[0] == 'brief' and stages[-1] == 'conclude' and 'update' in stages


def test_a_tokenizer_whose_context_is_not_a_prefix_is_refused():
    from aemon.rows.build_rows import labels_for

    class Shifting:
        def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
            return ' '.join(m['content'] for m in messages) + (' GEN' if add_generation_prompt else '')

        def __call__(self, text, add_special_tokens=False):
            return {'input_ids': text.replace('GEN', 'X').split()}
    row = {'messages': [{'role': 'user', 'content': 'u'}, {'role': 'assistant', 'content': 'call'}], 'target_index': 1}
    with pytest.raises(ValueError, match='prefix'):
        labels_for(Shifting(), row, 50)


def test_the_final_test_is_frozen():
    from aemon.data.freeze import FROZEN, digest

    dossier = json.loads((Path(__file__).resolve().parents[1] / 'data/dossier/evidence.json').read_text())
    if dossier.get('redacted'):
        pytest.skip('public copy: excerpts are cut to short quotes, and the frozen digest covers the full excerpts')
    assert digest() == json.loads(FROZEN.read_text()), 'the held-out cases or their evidence changed: refreeze deliberately and record why'


def test_development_never_sees_the_final_test():
    from aemon.environment.cases import load_cases
    from aemon.data.freeze import held_out
    cases, scopes, records = held_out()
    development = load_cases()
    assert not {c.id for c in development} & {c['id'] for c in cases}
    assert not {c.company for c in development} & {c['company'] for c in cases}
    assert not [i for c in development for i, r in c.dossier.records.items() if r.scope in scopes]
    assert all(c.get('shared_scopes') == [] for c in cases), 'a held-out company must not share the market evidence'


def test_the_search_held_for_a_challenge_is_not_offered_as_free():
    from aemon.environment.cases import load_cases
    from aemon.agent.state_view import searches
    case = next(c for c in load_cases() if c.id == 'moldex-base')
    run = Investigation(case, staged=True)
    run.searches = ['q'] * (case.search_budget - 1)
    assert searches(run) == {'searches_left': 0, 'kept_for_challenge': 1}
    run.challenge_searches = [{'theory_id': 'T1', 'query': 'q', 'found': []}]
    assert searches(run) == {'searches_left': 1, 'kept_for_challenge': 0}


def test_a_route_applies_one_adapter_per_stage_and_switches_the_rest_off():
    from aemon.agent.adapter_routing import lora_route
    route = lora_route('default=0,test=1')
    assert route('theories') == [{'id': 0, 'scale': 1.0}, {'id': 1, 'scale': 0.0}]
    assert route('test') == [{'id': 0, 'scale': 0.0}, {'id': 1, 'scale': 1.0}]
    assert lora_route('default=none,test=0')('frame') == [{'id': 0, 'scale': 0.0}]
    assert lora_route('default=none', loaded=2)('test') == [{'id': 0, 'scale': 0.0}, {'id': 1, 'scale': 0.0}]
    assert lora_route('default=none')('test') == []
    with pytest.raises(ValueError):
        lora_route('test=1')


def test_play_tells_the_backend_which_adapters_each_stage_uses():
    from aemon.environment.cases import load_cases
    from aemon.agent.adapter_routing import lora_route
    case = next(c for c in load_cases() if c.id == 'moldex-base')
    seen = []
    def respond(messages, seed, max_tokens, schema, temperature, lora=None):
        seen.append(lora)
        return {'text': '{"name": "read_brief", "arguments": {}}'}
    play(case, respond, PROMPTS['staged'], 3, 4, 100, True, TOOL_SCHEMA, staged=True, route=lora_route('default=0,test=1'))
    assert seen and all(s == [{'id': 0, 'scale': 1.0}, {'id': 1, 'scale': 0.0}] for s in seen)


def test_a_stuck_run_hands_its_next_turns_to_the_other_adapter_until_a_call_is_accepted():
    from aemon.environment.cases import load_cases
    from aemon.agent.adapter_routing import lora_route
    route = lora_route('default=1,stuck=0')
    assert route('evidence', 1) == [{'id': 0, 'scale': 0.0}, {'id': 1, 'scale': 1.0}]
    assert route('evidence', 2) == [{'id': 0, 'scale': 1.0}, {'id': 1, 'scale': 0.0}]
    assert lora_route('default=1,stuck=0,stuck_after=3')('evidence', 2)[1]['scale'] == 1.0
    case = next(c for c in load_cases() if c.id == 'moldex-base')
    replies = iter(['{"name": "frame_problem", "arguments": {}}'] * 3 + ['{"name": "read_brief", "arguments": {}}'] * 3)
    used = []
    def respond(messages, seed, max_tokens, schema, temperature, lora=None):
        used.append(next(i for i, a in enumerate(lora) if a['scale']))
        return {'text': next(replies)}
    run, info = play(case, respond, PROMPTS['compact'], 5, 4, 100, True, TOOL_SCHEMA, compact=True, route=route)
    # three refusals (framing before the brief), then the brief is accepted: turns 3 and 4 go to the other adapter
    assert used == [1, 1, 0, 0, 1] and [t['adapters'] for t in info['turns']] == [[1], [1], [0], [0], [1]]


def test_adapter_settings_reach_the_server_in_its_own_form():
    from aemon.agent.backends.llama_client import lora_body
    assert lora_body(0) == [{'id': 0, 'scale': 0.0}]
    assert lora_body([{'id': 0, 'scale': 0.0}, {'id': 1, 'scale': 1.0}]) == [{'id': 0, 'scale': 0.0}, {'id': 1, 'scale': 1.0}]
    with pytest.raises(ValueError):
        lora_body([[{'id': 0, 'scale': 1.0}]])


def test_an_exact_quote_in_quotation_marks_counts_only_when_the_episode_says_so():
    from aemon.environment.cases import load_cases
    case = next(c for c in load_cases() if c.id == 'moldex-base')
    source = next(iter(case.dossier.records.values()))
    words = ' '.join(source.excerpt.split()[:8])
    for marks, accepted in ((False, False), (True, True)):
        run = Investigation(case, staged=False, quote_marks=marks)
        run.call('read_brief', {})
        run.call('frame_problem', {'objective': 'Decide', 'constraints': ['Small budget'], 'alternatives': ['Enter', 'Do not enter']})
        run.read.add(source.id)
        run.theories['T1'] = {'claim': 'c', 'status': 'open'}
        result = run.call('assess_evidence', {'theory_id': 'T1', 'evidence_id': source.id, 'direction': 'supports', 'quote': '“' + words + '”',
                                              'evidence_kind': 'market_fact', 'does_not_show': 'It does not show demand'})
        assert ('error' not in result) is accepted, result


def test_the_workflow_diagram_matches_the_controller():
    from aemon.environment.cases import load_cases
    from aemon.evaluation.diagnostics.fixed_policies import scripted
    from aemon.environment.stages import WORKFLOW, current_stage
    from aemon.environment.tools import Investigation
    declared = {w['stage']: tuple(w['tools']) for w in WORKFLOW}
    seen = {}
    for case in load_cases():
        if not case.id.startswith('moldex-'):
            continue
        recorded = scripted(case, 'revised')
        replay = Investigation(case, staged=True)
        for call in recorded.calls:
            stage = current_stage(replay)
            seen[stage.name] = stage.tools
            replay.call(call['name'], call['arguments'])
    assert seen.pop('done', None) is None
    for name, tools in seen.items():
        assert declared[name] == tuple(tools), name
    assert {'brief', 'frame', 'evidence', 'theories', 'assessment', 'challenge', 'test', 'position', 'new_evidence', 'update', 'conclude'} <= set(seen)


def test_a_search_the_budget_would_refuse_is_not_offered():
    from aemon.environment.cases import load_cases
    from aemon.agent.tool_schemas import schema_for
    case = next(c for c in load_cases() if c.id == 'moldex-base')
    run = Investigation(case, staged=True)
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'Decide', 'constraints': ['Small budget'], 'alternatives': ['Enter', 'Do not enter']})
    offered = lambda: {t['properties']['name']['const'] for t in schema_for(run)['anyOf']}
    assert 'search_evidence' in offered()
    run.searches = ['q'] * (case.search_budget - 1)
    run.surfaced.add(next(iter(case.dossier.records)))
    assert 'search_evidence' not in offered()


def test_the_compact_state_shows_a_refused_call_so_it_is_not_repeated():
    from aemon.environment.cases import load_cases
    from aemon.agent.state_view import state_of
    case = next(c for c in load_cases() if c.id == 'moldex-base')
    run = Investigation(case, staged=True)
    run.call('read_brief', {})
    run.call('read_source', {'id': 'nothing-like-this'})
    assert 'your_last_call_was_refused' in state_of(run, {})
    run.call('frame_problem', {'objective': 'Decide', 'constraints': ['Small budget'], 'alternatives': ['Enter', 'Do not enter']})
    assert 'your_last_call_was_refused' not in state_of(run, {})


def test_validation_companies_are_development_companies_and_never_the_final_test():
    from aemon.environment.cases import load_cases
    from aemon.data.freeze import held_out
    from aemon.data.splits import VALIDATION_COMPANIES, is_validation
    development = load_cases()
    scopes = {c.id.split('-')[0] for c in development}
    assert set(VALIDATION_COMPANIES) <= scopes
    assert not set(VALIDATION_COMPANIES) & set(held_out()[1])
    assert any(is_validation(c.id) and not c.test_warranted for c in development), 'validation needs a case where no test is warranted'
    assert sum(not is_validation(c.id) for c in development) > 3 * sum(is_validation(c.id) for c in development)


def test_validation_is_capped_per_company_and_averaged_over_companies():
    import aemon.training.train as train_pilot
    rows = [{'case': f'{c}-base', 'n': i} for c, k in (('neumann', 100), ('jotun', 10)) for i in range(k)]
    capped = train_pilot.cap_per_company(rows, 40)
    assert sum(r['case'].startswith('neumann') for r in capped) == 40 and sum(r['case'].startswith('jotun') for r in capped) == 10
    assert [r['n'] for r in capped if r['case'].startswith('neumann')][:3] == [0, 2, 5]
    trainer = object.__new__(train_pilot.CompanyTrainer)
    trainer.company_sets = {'jotun': 'J', 'neumann': 'N'}
    logged = []
    trainer.log = logged.append
    losses = {'J': 1.0, 'N': 0.5}
    original = train_pilot.SFTTrainer.evaluate
    train_pilot.SFTTrainer.evaluate = lambda self, data, ignore, prefix: {f'{prefix}_loss': losses[data]}
    try:
        out = trainer.evaluate()
    finally:
        train_pilot.SFTTrainer.evaluate = original
    assert out['eval_loss'] == 0.75 and out['eval_jotun_loss'] == 1.0 and logged == [{'eval_loss': 0.75}]


def test_progress_counts_completed_stages_repeats_and_used_sources():
    from aemon.evaluation.diagnostics.progress import progress
    record = {'final': None, 'calls': [
        {'name': 'read_brief', 'arguments': {}, 'stage': 'brief', 'accepted': True, 'result': {}},
        {'name': 'frame_problem', 'arguments': {}, 'stage': 'frame', 'accepted': True, 'result': {}},
        {'name': 'search_evidence', 'arguments': {'query': 'q'}, 'stage': 'evidence', 'accepted': True, 'result': {}},
        {'name': 'search_evidence', 'arguments': {'query': 'q'}, 'stage': 'evidence', 'accepted': False, 'result': {'error': 'you already ran that search'}},
        {'name': 'read_source', 'arguments': {'id': 'a'}, 'stage': 'evidence', 'accepted': True, 'result': {}},
        {'name': 'read_source', 'arguments': {'id': 'b'}, 'stage': 'evidence', 'accepted': True, 'result': {}},
        {'name': 'assess_evidence', 'arguments': {'evidence_id': 'a'}, 'stage': 'assessment', 'accepted': True, 'result': {}}]}
    p = progress(record)
    assert p['highest_stage_completed'] == 'evidence' and p['repeated'] == 1 and p['sources_read'] == 2 and p['sources_used'] == 1 and p['refused'] == 1


def _pilot2_states():
    from aemon.teacher.corrections import states
    return states([str(Path(__file__).resolve().parent.parent / 'reports/strategy/pilot2/second_adapter.json')])


def test_correction_states_come_from_training_companies_one_per_loop():
    from aemon.teacher.corrections import MAX_PER_RUN
    from aemon.data.splits import is_validation
    found = _pilot2_states()
    assert found and not any(is_validation(s['case']) for s in found)
    per_run = {}
    for s in found:
        per_run[s['student_run']] = per_run.get(s['student_run'], 0) + 1
    assert max(per_run.values()) <= MAX_PER_RUN


def test_a_correction_is_kept_only_if_it_works_and_names_what_it_acts_on(tmp_path):
    import re
    from aemon.teacher.corrections import PROTOCOL, _digest, judge, rows
    state = _pilot2_states()[0]
    unread = json.loads('[' + re.search(r'"unread_results": \[([^\]]*)\]', state['context'][1]['content']).group(1) + ']')
    good = {'learned': f'{unread[0]} is unread', 'uncertain': 'consumer reach', 'why_next': f'read {unread[0]}', 'call': {'name': 'read_source', 'arguments': {'id': unread[0]}}}
    assert judge(state, json.dumps(good))[1] == 'kept'
    assert judge(state, json.dumps(dict(good, learned='x', uncertain='y', why_next='z')))[1] == 'the justification names nothing from the state'
    refused = state['refused_next']
    assert judge(state, json.dumps(dict(good, call={'name': refused['name'], 'arguments': refused['arguments']})))[1] == 'repeats an earlier call'
    kept, _ = judge(state, json.dumps(good))
    item = {'state': {k: state[k] for k in ('case', 'case_digest', 'student_run', 'turn')}, 'record': state['record'], 'context': state['context'], 'reply': json.dumps(good), 'kept': kept}
    manifest = tmp_path / 'm.jsonl'
    manifest.write_text('')
    assert rows([item], manifest) == []  # not in the manifest, so refused
    manifest.write_text(json.dumps({'protocol': PROTOCOL, 'case': state['case'], 'case_digest': state['case_digest'], 'student_run': state['student_run'], 'turn': state['turn'], 'weights_sha256': 'w', 'reply_sha256': _digest(json.dumps(good))}) + '\n')
    made = rows([item], manifest)
    assert len(made) == 1 and made[0]['source'] == 'correction' and json.loads(made[0]['messages'][-1]['content'])['name'] == 'read_source'
    assert rows([dict(item, reply=json.dumps(dict(good, why_next='edited')))], manifest) == []  # an edited reply no longer matches


def test_extra_rows_are_kept_under_their_token_share():
    import subprocess
    script = Path(__file__).resolve().parent.parent / 'src' / 'aemon' / 'training' / 'train.py'
    text = script.read_text()
    assert "--extra-token-share" in text and "'supervised_by_source'" in text and "'extra_share'" in text



def test_the_status_check_comes_after_framing_finds_aquaporins_insolvency_and_must_be_weighed():
    from aemon.environment.cases import load_cases
    from aemon.environment.stages import current_stage
    from aemon.agent.tool_schemas import schema_for
    case = next(c for c in load_cases(split='heldout') if c.id == 'aqp-base')
    off = Investigation(case, staged=True)
    assert 'error' in off.call('company_status', {})  # off by default: frozen runs see no new tool
    run = Investigation(case, staged=True, status_check=True)
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'decide', 'constraints': ['cash'], 'alternatives': ['enter', 'do nothing']})
    assert current_stage(run).name == 'status' and [t['properties']['name']['const'] for t in schema_for(run)['anyOf']] == ['company_status']
    status = run.call('company_status', {})
    ids = [r['id'] for r in status['results']]
    assert ids[0] == 'aqp-trustee-appointed' and {'aqp-insolvency-2026', 'aqp-strategic-review-failed'} & set(ids)
    assert 'error' in run.call('company_status', {})
    assert current_stage(run).name == 'status_reading'
    assert schema_for(run)['anyOf'][0]['properties']['arguments']['properties']['id'] == {'enum': sorted(ids)}
    run.call('read_source', {'id': ids[0]})
    assert current_stage(run).name == 'evidence'
    for other_status in ids[1:]:  # status sources never meet the evidence minimum, so market evidence is still gathered
        run.call('read_source', {'id': other_status})
    assert current_stage(run).name == 'evidence' and 'You have read 0 of' in current_stage(run).instruction
    assert all(i not in ids for i in (schema_for(run)['anyOf'][-1]['properties']['arguments']['properties'].get('id', {}).get('enum') or []))
    other = next(r.id for r in case.dossier.search('consumer water filter') if r.id not in ids)
    run.surfaced.add(other); run.read.add(other)
    run.theories['T1'] = {'claim': 'x'}
    run.final = None
    run.staged = False  # the finish rule alone, without beliefs or the stage gate
    args = {'recommendation': 'invest', 'target_customer': 'x', 'value_proposition': 'x', 'favoured_theory': 'T1', 'next_action': 'x',
            'uncertainty': 'x', 'would_change_if': ['x'], 'evidence_ids': [other]}
    refused = run.call('finish', args)  # the status check asks finish to say where the company stands
    assert 'error' in refused and 'company_position' in refused['error']
    position = 'Aquaporin filed for bankruptcy in February 2026, so it cannot fund a consumer launch.'
    assert run.call('finish', {**args, 'company_position': position}) == {'finished': True}
    assert run.final['company_position'] == position


def test_status_check_runs_record_the_setting_and_list_the_tool_in_the_prompt():
    from aemon.agent.state_view import with_status
    from aemon.environment.cases import load_cases
    assert 'company_status {}' in with_status(PROMPTS['compact']) and 'company_status' not in PROMPTS['compact']
    case = next(c for c in load_cases(split='heldout') if c.id == 'aqp-base')
    replies = iter(['{"name": "read_brief", "arguments": {}}', '{"name": "frame_problem", "arguments": {"objective": "decide", "constraints": ["cash"], "alternatives": ["enter", "do nothing"]}}', '{"name": "company_status", "arguments": {}}'])
    run, info = play(case, lambda *a, **k: {'text': next(replies)}, with_status(PROMPTS['compact']), 3, 4, 100, True, TOOL_SCHEMA, staged=True, compact=True, status_check=True)
    assert run.status_ids and record_of(run, info)['settings']['status_check'] is True
