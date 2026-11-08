"""The version 2 gates that decide which teacher answers may train: text cut at its length limit is never kept."""

from strategy_agent.pipeline.targeted import cut_off


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
