"""Experimental failure-aware recovery controller (docs/RECOVERY_EXPERIMENT.md). Off unless asked for.

Four independently switchable features, each recorded in an episode's settings so no result can be mistaken for the
evaluated configuration:
- ``mask_rereads``  read_source offers only sources not yet read when unread ones exist, and is withdrawn when none
  exist and the step does not need a read; read text always stays in the state.
- ``progress``      a progress measure over accepted state changes; after a refusal, a structured refusal (category,
  reason, the step's unmet requirement, the actions that can succeed now); after repeated non-progress, a
  state-grounded recovery note.
- ``budget``        an estimate of the fewest actions still required to finish; when the remaining turns are tight, a
  budget note, and optional exploration (extra searches, rereads, extra theories) is withdrawn.
- ``citations``     finish may cite only real sources read; simulated results stay citable in revise_theory.

Nothing here writes to the record, invents evidence, chooses a recommendation, or relaxes a tool guard: every refusal
still happens on the record, and termination rules are unchanged.
"""

from __future__ import annotations

from typing import Any

from aemon.environment.stages import current_stage

FEATURES = ('mask_rereads', 'progress', 'budget', 'citations')
NO_PROGRESS_LIMIT = 3  # calls in a row without progress before the recovery note
BUDGET_MARGIN = 3  # spare turns kept above the minimum before exploration is withdrawn
EXPLORATORY = ('search_evidence', 'challenge_theory', 'add_theory', 'read_source', 'assess_evidence')

REQUIREMENT = {
    'brief': 'read the brief',
    'frame': 'frame the decision: objective, constraints and at least two alternatives',
    'evidence': 'read at least 3 sources',
    'theories': 'state at least 2 distinct theories',
    'assessment': 'weigh a source you have read for every theory',
    'challenge': 'search for evidence against the theory you favour (challenge_theory)',
    'challenge_reading': 'read what the challenge search found',
    'test': 'propose a test that separates the theories, or decline one with a reason',
    'position': 'state your position: favoured theory, recommendation and a belief per theory',
    'new_evidence': 'read the new evidence that has arrived',
    'update': 'revise or keep the theory the new evidence bears on, citing it',
    'conclude': 'finish with a recommendation that cites real sources you read',
}


def signature(run: Any) -> tuple:
    """The parts of the accepted state whose change counts as progress. Searches, rereads and refusals do not."""
    return (
        bool(getattr(run, 'brief_read', False)),
        bool(run.frame),
        frozenset(run.read),
        frozenset(run.theories),
        frozenset((a['theory_id'], a['evidence_id']) for a in run.assessments),
        len(run.challenge_searches),
        len(run.tests),
        bool(run.test_declined),
        bool(run.position),
        len(run.revisions),
        run.final is not None,
    )


def min_actions(run: Any) -> int:
    """The fewest accepted calls that could still finish this investigation, from the controller's unmet requirements."""
    stage = current_stage(run).name
    order = list(REQUIREMENT)
    if stage == 'done':
        return 0
    if stage not in order:
        return 1
    need = 0
    shock = run.case.shock is not None and run.staged
    for name in order[order.index(stage):]:
        if name == 'brief':
            need += 0 if getattr(run, 'brief_read', False) else 1
        elif name == 'frame':
            need += 0 if run.frame else 1
        elif name == 'evidence':
            need += max(0, 3 - len(run.read))
        elif name == 'theories':
            need += max(0, 2 - len(run.theories))
        elif name == 'assessment':
            assessed = {a['theory_id'] for a in run.assessments}
            need += max(2, len(run.theories)) - len(assessed & set(run.theories))
        elif name == 'challenge':
            need += 0 if run.challenge_searches else 1
        elif name == 'challenge_reading':
            need += 1 if stage == 'challenge_reading' else 0
        elif name == 'test':
            need += 0 if (run.tests or run.test_declined) else 1
        elif name == 'position':
            need += 0 if run.position else 1
        elif name in ('new_evidence', 'update'):
            need += 1 if shock and not any(r.get('evidence_ids') for r in run.revisions) else 0
        elif name == 'conclude':
            need += 1
    return max(need, 1)


def tight(run: Any) -> bool:
    left = getattr(run, 'turns_left', None)
    return left is not None and left <= min_actions(run) + BUDGET_MARGIN


def withdrawn(run: Any, name: str) -> bool:
    """Tools the recovery controller takes out of this turn's schema (never those the step requires)."""
    features = getattr(run, 'recovery', frozenset())
    stage = current_stage(run).name
    if 'mask_rereads' in features and name == 'read_source':
        unread = [i for i in run.surfaced if i not in run.read]
        if not unread and stage not in ('evidence', 'challenge_reading', 'new_evidence'):
            return True  # its text is already in the state; another read cannot change anything
    if 'budget' in features and tight(run) and name in EXPLORATORY:
        required = {
            'evidence': ('read_source', 'search_evidence'),
            'theories': ('add_theory', 'read_source', 'search_evidence'),
            'assessment': ('assess_evidence',),
            'challenge': ('challenge_theory',),
            'challenge_reading': ('read_source',),
            'new_evidence': ('read_source',),
        }.get(stage, ())
        return name not in required
    return False


def read_choices(run: Any, choices: list[str]) -> list[str]:
    if 'mask_rereads' not in getattr(run, 'recovery', frozenset()):
        return choices
    unread = [i for i in choices if i not in run.read]
    return unread or choices


def citable(run: Any, ids: list[str]) -> list[str]:
    if 'citations' not in getattr(run, 'recovery', frozenset()):
        return ids
    real = [i for i in ids if run._source(i).type != 'synthetic']
    return real or ids


def open_actions(run: Any, schema: dict) -> list[str]:
    return [t['properties']['name']['const'] for t in schema.get('anyOf', [])]


def refusal_note(run: Any, call: dict, schema: dict) -> dict:
    stage = current_stage(run).name
    return {
        'category': call.get('category', 'refused'),
        'explanation': str((call.get('result') or {}).get('error', ''))[:300],
        'current_requirement': REQUIREMENT.get(stage, current_stage(run).instruction),
        'actions_that_can_succeed_now': open_actions(run, schema),
    }


def recovery_note(run: Any, recent: list[dict], schema: dict) -> str:
    stage = current_stage(run).name
    tried = ', '.join(sorted({c['name'] + ('' if c['accepted'] else ' (refused)') for c in recent})) or 'nothing'
    why = []
    if any(not c['accepted'] for c in recent):
        why.append('the refused calls changed nothing')
    if any(c['name'] == 'read_source' and c['accepted'] for c in recent):
        why.append('rereading returns text already in your state')
    if any(c['name'] == 'search_evidence' and c['accepted'] for c in recent):
        why.append('a search alone does not meet the requirement')
    return (f'You have not advanced for {len(recent)} calls (tried: {tried}). Step: {stage}. Still required: '
            f'{REQUIREMENT.get(stage, "")}. Why recent calls did not advance: {"; ".join(why) or "they repeated earlier work"}. '
            f'Actions that can succeed now: {", ".join(open_actions(run, schema))}.')


def budget_note(run: Any) -> str:
    return (f'Turns left: {run.turns_left}. At least {min_actions(run)} accepted steps are still required to finish '
            f'({REQUIREMENT.get(current_stage(run).name, "")} first). Further searches and rereads are withdrawn. If the evidence '
            'is insufficient, say so in your recommendation and uncertainty rather than guessing.')
