"""The stage controller, a pure function of what has happened so far.

The harness fixes the order and the minimum work. The model decides the content: what to search,
which theories to hold, what to test, what the evidence means, and how much more to do before
moving on, because later stages keep the evidence tools open. Instructions name the step and never
the answer. Every arm that uses this uses it identically, so a base and a fine-tuned model differ
only in the model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from strategy_agent.common.constants.env import _LOOK_FURTHER, MIN_READ, MIN_THEORIES, WORKFLOW  # noqa: F401

if TYPE_CHECKING:
    from strategy_agent.env.tools import Investigation


class Stage(NamedTuple):
    name: str
    tools: tuple
    instruction: str


def _unread(run: Investigation) -> list[Any]:
    return sorted(i for i in run.surfaced if i not in run.read)[:3]


def _challenge_unread(run: Investigation) -> bool:
    """A challenge that found something and read none of it is not a challenge yet."""
    found = [s['found'] for s in run.challenge_searches if s['found']]
    return bool(found) and not any(i in run.read for ids in found for i in ids)


def current_stage(run: Investigation) -> Stage:
    if run.final is not None:
        return Stage('done', (), 'The investigation is finished.')
    if not run.brief_read:
        return Stage('brief', ('read_brief',), 'Stage: brief. Read the brief.')
    if run.frame is None:
        return Stage('frame', ('frame_problem',), 'Stage: frame. State the objective, the constraints and the alternatives, including no expansion.')
    if len(run.read) < MIN_READ:
        return Stage(
            'evidence',
            ('search_evidence', 'read_source'),
            f'Stage: evidence. You have read {len(run.read)} of at least {MIN_READ} sources. Unread results: {_unread(run)}',
        )
    if len(run.theories) < MIN_THEORIES:
        return Stage(
            'theories',
            ('add_theory', 'search_evidence', 'read_source'),
            f'Stage: theories. You have {len(run.theories)} of at least {MIN_THEORIES}. Add one with a different cause, or look further first.',
        )
    unassessed = [k for k in run.theories if not any(a['theory_id'] == k for a in run.assessments)]
    if unassessed:
        return Stage(
            'assessment',
            ('assess_evidence', 'read_source', 'search_evidence', 'add_theory'),
            f'Stage: assessment. Say how a source you read bears on {unassessed[0]}, quoting its exact words. Sources read: {sorted(run.read)}. You may add another theory if it has a different cause.',
        )
    if not run.challenge_searches:
        return Stage('challenge', ('challenge_theory',), 'Stage: challenge. Choose the theory you favour and search for what could prove it wrong.')
    if _challenge_unread(run):
        return Stage(
            'challenge_reading',
            ('read_source', 'challenge_theory'),
            f'Stage: challenge. Read what your challenge found: {run.challenge_searches[-1]["found"][:3]}',
        )
    if not run.tests and run.test_declined is None:
        return Stage(
            'test',
            ('propose_test', 'decline_test', 'add_theory', *_LOOK_FURTHER),
            'Stage: test. Propose an affordable experiment where theories predict different results, with a decision rule that has a threshold. If more information is not worth its cost, use decline_test and say why.',
        )
    if run.position is None:
        challenged = sorted({s['theory_id'] for s in run.challenge_searches})
        return Stage(
            'position',
            ('state_position', *_LOOK_FURTHER),
            f'Stage: position. Say which theory you favour now, what you would recommend, and how likely you find each theory. You have challenged {challenged}, and can only favour one of those, or challenge another first.',
        )
    shock = run.case.shock
    if run.shock_delivered and shock is not None and shock.id not in run.read:
        return Stage('new_evidence', ('read_source',), f'Stage: new evidence. Read {shock.id}. It is simulated, so treat it as a what-if.')
    if run.shock_delivered and shock is not None and not any(shock.id in r['evidence_ids'] for r in run.revisions):
        return Stage(
            'update',
            ('revise_theory',),
            f'Stage: update. Suppose {shock.id} were real. Use revise_theory to record what it would mean for the theory it bears most on, citing it. kept, revised and rejected are all allowed, and a result can change nothing.',
        )
    return Stage('conclude', ('finish', 'revise_theory', *_LOOK_FURTHER), 'Stage: conclude. Finish when you have done enough, or revise or look further first.')
