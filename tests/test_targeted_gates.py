"""The version 2 gates that decide which teacher answers may train: text cut at its length limit is never kept."""

from aemon.teacher.targeted import cut_off


def call(**fields):
    arguments = {'name': 'Kit test', 'theories': ['T1', 'T2'], 'method': 'Sell two kits by mail order.', 'sample': '200 buyers.',
                 'measure': 'Orders.', 'prediction_by_theory': {'T1': 'More orders of A.', 'T2': 'More orders of B.'},
                 'decision_rule': 'If A sells 20% more, pilot A; otherwise pilot B.', 'cost_eur': 3000, 'weeks': 6}
    return {'name': 'propose_test', 'arguments': {**arguments, **fields}}


def test_a_complete_answer_passes_and_short_ids_are_not_cut():
    assert cut_off(call(), {'learned': 'x', 'uncertain': 'y', 'why_next': 'z'}) == ''


def test_a_field_at_its_limit_or_at_the_old_limit_is_cut():
    assert 'decision_rule' in cut_off(call(decision_rule='a' * 900), {})
    assert 'method' in cut_off(call(method='a' * 240), {})  # the limit the first batches were made under
    assert 'prediction_by_theory.T2' in cut_off(call(prediction_by_theory={'T1': 'up', 'T2': 'b' * 600}), {})
    assert 'why_next' in cut_off(call(), {'why_next': 'c' * 700})


class Case:
    question, brief = 'It is 1977. Should we build a cordless tool?', ''


class Run:
    case = Case()


def test_message_only_tests_big_steps_and_euros_before_1999_are_refused():
    from aemon.teacher.targeted import gate_mechanism

    message_only = {'name': 'Framing test', 'method': 'Show two framed ads: convenience-framed and prestige-framed.', 'sample': '200 shoppers', 'measure': 'deposits',
                    'decision_rule': 'If convenience wins by 10 points, run a pilot in one region; otherwise stop.'}
    assert 'wording or message' in gate_mechanism(Run(), message_only)
    priced = dict(message_only, method='Offer the same tool at two prices, $30 and $45, with the same display.')
    assert gate_mechanism(Run(), priced) == ''
    big = dict(priced, decision_rule='If demand at $45 exceeds 20%, develop the full product line.')
    assert 'bounded next step' in gate_mechanism(Run(), big)
    assert 'euros' in gate_mechanism(Run(), dict(priced, measure='A €50 deposit'))


def test_several_answers_to_one_state_give_at_most_one_kept(monkeypatch):
    from aemon.teacher import targeted

    state = {'skill': 'weigh', 'case': 'x', 'state': {'student_run': 'r', 'turn': 3}}

    def fake_ask(group, *a, **k):
        return [{'state': {'student_run': 'r', 'turn': 3}, 'record': {}, 'reply': '{}', 'kept': {'call': {}}, 'decision': 'kept'} for _ in group]

    monkeypatch.setattr(targeted.c, 'ask', fake_ask)
    monkeypatch.setattr(targeted, 'gate', lambda st, reply: ({'call': {}}, 'kept'))
    out = targeted.ask([state], 'u', 'w', 'm', 1, samples=3, temperature=0.7)
    assert len(out) == 3 and sum(isinstance(x['kept'], dict) for x in out) == 1 and out[1]['decision'] == 'another answer to this state was kept'


def test_one_price_for_the_whole_test_is_not_a_price_difference_and_plural_propositions_are_caught():
    from aemon.teacher.targeted import gate_mechanism

    cotral = {'name': 'Segment-framed pre-order', 'method': 'Offer a musician-framed or a sleep-framed offer for one earplug priced at €150, with a €50 deposit.',
              'sample': '400 people', 'measure': 'deposits', 'decision_rule': 'If both reach 30%, run a pilot in each; otherwise stop.'}
    assert 'wording or message' in gate_mechanism(Run(), cotral)
    assert gate_mechanism(Run(), dict(cotral, method='Offer the earplug at two price levels, $120 and $150, with the same framing.')) == ''
    plural = dict(cotral, method='Offer two prototypes at $120 and $150.', decision_rule='If both reach 30%, proceed to develop differentiated propositions for both segments.')
    assert 'bounded next step' in gate_mechanism(Run(), plural)
