"""One authored investigation of the real Moldex case, through the real tools and real evidence.

It proves the checks can pass on the true dossier, and it shows what a good run looks like. It is
one analyst's reading, not ground truth, and the theories in it are hypotheses. Its quotes are
checked word for word by the tools, so it cannot drift from the sources.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aemon.environment.cases import load_cases
from aemon.environment.checks import run_checks
from aemon.environment.tools import Investigation

if TYPE_CHECKING:
    from aemon.environment.tools import Case

THEORIES = {
    'looks': {
        'claim': 'Appearance holds back use among concert-goers, so a discreet redesign would open a consumer segment for an industrial maker.',
        'who_benefits': 'People who attend loud music events and avoid visible earplugs',
        'why_behaviour_changes': 'Embarrassment falls when the product does not look like workwear, so they keep it in.',
        'how_value_is_captured': 'A branded product sold at a higher price per pair than bulk workplace plugs',
        'assumptions': ['Embarrassment, not forgetting, is what stops wearing'],
        'predictions': ['Observed wearing is higher for a discreet design than for a plain plug when both are available at the same price'],
    },
    'availability': {
        'claim': 'People do not wear protection because it is not to hand at the moment of need, so supply through venues matters more than redesign.',
        'who_benefits': 'Event-goers who did not plan ahead, and venues that want to protect audiences',
        'why_behaviour_changes': 'A prompt and a plug at the door turn a forgotten intention into use.',
        'how_value_is_captured': 'Bulk sales to venue operators, close to how the company already sells through business buyers',
        'assumptions': ['Venues will pay for or stock plugs', 'Forgetting explains more non-use than dislike does'],
        'predictions': ['Observed wearing is higher where plugs are offered at the door than where the same plugs are only sold online beforehand'],
    },
    'sleep': {
        'claim': 'Sleepers have a stronger recurring need than concert-goers, so foam plugs for sleep are a better first consumer market than music.',
        'who_benefits': 'Adults whose sleep is disturbed by noise',
        'why_behaviour_changes': 'Disturbed sleep is felt every night, so the problem reminds them to buy again.',
        'how_value_is_captured': 'Repeat purchases of low-cost foam plugs through retail or online',
        'assumptions': ['Foam plugs made for workers can be comfortable overnight'],
        'predictions': ['The repeat purchase rate is higher for sleep buyers than for music buyers over the same period'],
    },
}
ASSESSMENTS = [
    (
        'T1',
        'bockstael-2015-looks',
        'supports',
        'mainly depended on comfort and looks',
        'customer_observation',
        'Liking in a test room does not show people would wear them at events',
    ),
    (
        'T1',
        'long-2024-nonusers',
        'contradicts',
        'HP nonusers most frequently cited never considering HP',
        'customer_observation',
        'A survey of stated reasons does not rule out appearance as a smaller barrier',
    ),
    (
        'T2',
        'crutzen-2021-celebrate-safe',
        'supports',
        'in the experimental condition was higher in comparison to events in the control condition',
        'independent_study',
        'It bundled messages, sales and an ear check, so availability alone is not isolated',
    ),
    (
        'T2',
        'sonova-2019-swiss-free-plugs',
        'contradicts',
        'obliged to hand out free ear protection',
        'company_assertion',
        'A company survey with no comparison group does not show free supply fails',
    ),
    (
        'T3',
        'basner-2026-sleep',
        'supports',
        'Earplugs mitigated nearly all EN effects on sleep',
        'independent_study',
        'A lab study of efficacy does not show people would buy them repeatedly',
    ),
    (
        'T3',
        'nhs-hyperacusis',
        'neutral',
        'short-term use may help in very noisy environments',
        'regulation',
        'This guidance concerns hyperacusis, so it transfers to ordinary sleepers only by analogy',
    ),
]
SEARCHES = (
    'music events ear plugs use trial availability',
    'nonusers never considering hearing protection',
    'looks comfort appreciation earplugs',
    'Earplugs mitigated sleep noise',
    'hyperacusis do not wear earplugs all the time',
    'Moldex Spark Plugs blister packaging storage container',
)
CHALLENGE = ('T2', 'promoters obliged free ear protection never wear')


def investigate(case: Case) -> Investigation:
    run = Investigation(case)
    run.call('read_brief', {})
    run.call(
        'frame_problem',
        {
            'objective': 'Find out whether any specific use case justifies a differentiated consumer proposition beyond what Moldex already sells',
            'constraints': [
                'Financial data was not found',
                'How far small packs reach individual buyers is unknown',
                'Hearing protectors may fall under strict PPE rules',
            ],
            'alternatives': [
                'Redesign a product for music fans',
                'Supply venues and event operators as a business customer',
                'Offer foam plugs for sleep',
                'No expansion: keep the existing offering',
            ],
        },
    )
    for query in SEARCHES:
        for hit in run.call('search_evidence', {'query': query})['results']:
            run.call('read_source', {'id': hit['id']})
    for theory in THEORIES.values():
        run.call('add_theory', theory)
    for theory_id, evidence_id, direction, quote, kind, limit in ASSESSMENTS:
        run.call(
            'assess_evidence',
            {'theory_id': theory_id, 'evidence_id': evidence_id, 'direction': direction, 'quote': quote, 'evidence_kind': kind, 'does_not_show': limit},
        )
    for hit in run.call('challenge_theory', {'theory_id': CHALLENGE[0], 'query': CHALLENGE[1]})['results']:
        run.call('read_source', {'id': hit['id']})
    run.call(
        'propose_test',
        {
            'name': 'Door offer against discreet design at small venues',
            'theories': ['T1', 'T2'],
            'method': 'At matched events, offer either plain plugs at the door, discreet plugs at the door, or plain plugs online beforehand. Staff who cannot see the arm label count people wearing protection from a fixed position.',
            'sample': 'About 18 events, 6 in each arm',
            'measure': 'Share of attendees seen wearing protection, and share of venues that sign a paid order',
            'prediction_by_theory': {
                'T1': 'Discreet plugs at the door beat plain plugs at the door',
                'T2': 'Both door arms beat online, with no gap between discreet and plain',
            },
            'decision_rule': 'Pursue venue supply if door arms beat online by at least 5 points and at least a third of venues sign a paid order',
            'cost_eur': 15000,
            'weeks': 10,
        },
    )
    run.call(
        'revise_theory',
        {
            'theory_id': 'T1',
            'status': 'revised',
            'reason': 'Non-users mostly cite not having thought about protection, so appearance looks like a secondary barrier at most',
            'new_claim': 'Appearance may matter for people who already intend to wear protection, but it is unlikely to be the main barrier for non-users.',
            'evidence_ids': ['long-2024-nonusers'],
        },
    )
    return run


def conclude(run: Investigation) -> Investigation:
    run.call(
        'finish',
        {
            'recommendation': 'Do not build a differentiated consumer proposition yet. Test venue supply first, because it is closest to how Moldex sells to business buyers and the best trial here favoured availability, though bundled with prompting.',
            'target_customer': 'Venue and event operators first, for people who attend loud events',
            'value_proposition': 'Protection available at the moment of need, supplied to the venue',
            'favoured_theory': 'T2',
            'next_action': 'Run the door offer test at small venues before any product redesign',
            'uncertainty': 'No study separates availability from prompting, economics were not found, how far small packs already reach individuals is unknown, and venue willingness to pay is untested',
            'would_change_if': ['Discreet plugs clearly beat plain plugs at the door', 'Too few venues sign a paid order'],
            'evidence_ids': ['crutzen-2021-celebrate-safe', 'long-2024-nonusers', 'sonova-2019-swiss-free-plugs', 'mdx-spark-blister'],
        },
    )
    return run


def main() -> None:
    case = next(c for c in load_cases('moldex-base'))
    run = conclude(investigate(case))
    rejected = [(c['name'], c['result']['error']) for c in run.calls if not c['accepted']]
    print('rejected calls:', rejected)
    for name, item in run_checks(run).items():
        print(f'{name:22} {item["passed"]}  {item["detail"]}')


if __name__ == '__main__':
    main()
