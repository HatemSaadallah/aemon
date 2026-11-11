"""The stage controller, a pure function of what has happened so far.

The harness fixes the order and the minimum work. The model decides the content: what to search,
which theories to hold, what to test, what the evidence means, and how much more to do before
moving on, because later stages keep the evidence tools open. Instructions name the step and never
the answer. Every arm that uses this uses it identically, so a base and a fine-tuned model differ
only in the model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from aemon.common.constants.env import _LOOK_FURTHER, MIN_READ, MIN_THEORIES, WORKFLOW  # noqa: F401

if TYPE_CHECKING:
    from aemon.environment.tools import Investigation


class Stage(NamedTuple):
    name: str
    tools: tuple
    instruction: str


def _status_ids(run: Investigation) -> set[str]:
    return set(getattr(run, 'status_ids', None) or [])


def _unread(run: Investigation) -> list[Any]:
    return sorted(i for i in run.surfaced if i not in run.read and i not in _status_ids(run))[:3]


def _evidence_read(run: Investigation) -> int:
    """Sources read for the evidence minimum. Company status sources do not count: with them counted, the status
    reading met the minimum and runs went to theories with no market search at all (DECISIONS 2026-11-11)."""
    return len(run.read - _status_ids(run))


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
    if getattr(run, 'status_check', False):
        if run.status_ids is None:
            return Stage('status', ('company_status',), "Stage: status. Check the company's current position with company_status before anything else.")
        if run.status_ids and not any(i in run.read for i in run.status_ids):
            return Stage('status_reading', ('read_source',), f'Stage: status. Read the newest of the company status results: {run.status_ids}')
    if _evidence_read(run) < MIN_READ:
        return Stage(
            'evidence',
            ('search_evidence', 'read_source'),
            f'Stage: evidence. You have read {_evidence_read(run)} of at least {MIN_READ} sources. Unread results: {_unread(run)}',
        )
    if len(run.theories) < MIN_THEORIES:
        return Stage(
            'theories',
            ('add_theory', 'search_evidence', 'read_source'),
            f'Stage: theories. You have {len(run.theories)} of at least {MIN_THEORIES}. Add one with a different cause, or look further first.',
        )
    # Each theory needs min_assessed weighed sources (1 as evaluated; opt-in more, never more than the real sources read)
    real = [i for i in run.read if run._source(i).type != 'synthetic']
    need = max(1, min(getattr(run, 'min_assessed', 1), len(real)))
    count = {k: sum(a['theory_id'] == k for a in run.assessments) for k in run.theories}
    unassessed = [k for k in run.theories if count[k] < need]
    if unassessed:
        k = unassessed[0]
        todo = sorted(i for i in real if not any(a['theory_id'] == k and a['evidence_id'] == i for a in run.assessments))
        ask = (f'Say how a source you read bears on {k}, quoting its exact words.' if need == 1
               else f'Weigh at least {need} sources for each theory; {k} has {count[k]}. Say how another source bears on {k}, quoting its exact words: {todo[:5]}. Include ones that cut against it.')
        return Stage(
            'assessment',
            ('assess_evidence', 'read_source', 'search_evidence', 'add_theory'),
            f'Stage: assessment. {ask} Sources read: {sorted(run.read)}. You may add another theory if it has a different cause.',
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
