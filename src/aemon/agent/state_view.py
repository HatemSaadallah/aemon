"""What the model is shown each turn: the state of the investigation, the stage guidance, and the system prompt
additions. Mechanical: it copies what is on record and interprets nothing. Nothing here changes a tool result, so
recorded investigations still replay.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from aemon.common.constants.prompts import STATUS_SIGNATURE, TOOL_SIGNATURES
from aemon.common.types import Json
from aemon.environment.stages import MIN_THEORIES, current_stage

if TYPE_CHECKING:
    from aemon.environment.tools import Investigation


def with_status(system: str) -> str:
    """The system prompt with company_status listed after the other tools, for status-check runs."""
    if TOOL_SIGNATURES not in system:
        raise ValueError('this prompt does not list the tools, so company_status cannot be added to it')
    return system.replace(TOOL_SIGNATURES, TOOL_SIGNATURES + '\n' + STATUS_SIGNATURE, 1)



SOURCES_NOTE = 'Each excerpt in sources_read is everything the dossier holds for that source: reading it again returns the same text.'


def state_of(run: Investigation, last_result: Json) -> str:
    """The whole investigation as it stands. Mechanical: it copies what is on record and interprets nothing."""
    case = run.case
    sources = [
        {'id': i, 'class': run._source(i).type, 'title': run._source(i).title, **({'date': run._source(i).date} if getattr(run, 'source_dates', False) else {}), 'excerpt': run._source(i).excerpt}
        for i in sorted(run.read)
    ]
    # Reads are listed too: a reread looked like progress to the student and the teacher alike (2026-11-05, DECISIONS)
    tried = [
        {'tool': c['name'], 'arguments': c['arguments']}
        for c in run.calls
        if not c['accepted'] or c['name'] in ('search_evidence', 'challenge_theory', 'read_source')
    ][-12:]
    state = {
        'question': case.question,
        'budgets': {**searches(run), 'test_budget_eur': case.test_budget, 'max_test_weeks': case.max_test_weeks},
        'frame': run.frame,
        'unread_results': sorted(i for i in run.surfaced if i not in run.read),
        'sources_read': sources,
        'sources_note': SOURCES_NOTE,
        # Everything a later step may need to justify itself is kept in full, so a conclusion never rests on reasoning it cannot see.
        'theories': {k: {f: v for f, v in t.items() if f != 'first_claim'} for k, t in run.theories.items()},
        'assessed': [{f: a[f] for f in ('theory_id', 'evidence_id', 'direction', 'quote', 'evidence_kind', 'does_not_show')} for a in run.assessments],
        'challenged': [s['theory_id'] for s in run.challenge_searches],
        'tests': run.tests,
        'test_declined': run.test_declined,
        'position': run.position,
        'revisions': run.revisions,
        'already_tried': tried,
    }
    if run.calls and not run.calls[-1]['accepted']:  # otherwise the context after a refusal is the one before it, and the call repeats
        state['your_last_call_was_refused'] = {'tool': run.calls[-1]['name'], 'arguments': run.calls[-1]['arguments']}
    if not case.brief or run.brief_read:
        state['brief'] = case.brief
    return 'Current state: ' + json.dumps(state) + '\nLatest tool result: ' + json.dumps(last_result)


def next_step(run: Investigation) -> str:
    """Workflow guidance in each tool result. It names the step, never the answer."""
    if run.frame is None:
        return 'Next: read_brief if you have not, then frame_problem.'
    unread = [i for i in run.surfaced if i not in run.read]
    if len(run.read) < 3 and unread:
        return f'Next: read_source. Unread results: {sorted(unread)[:3]}'
    if len(run.read) < 3:
        return 'Next: search_evidence for something specific and different.'
    if len(run.theories) < MIN_THEORIES:
        return 'Next: add_theory, with a different causal explanation.'
    unassessed = [k for k in run.theories if not any(a['theory_id'] == k for a in run.assessments)]
    if unassessed:
        return f'Next: assess_evidence for {unassessed[0]}, quoting exact words from a source you read.'
    if not run.challenge_searches:
        return 'Next: challenge_theory, to look for evidence that could prove your favoured theory wrong.'
    if not run.tests:
        return 'Next: propose_test.'
    shock = run.case.shock
    if run.shock_delivered and shock is not None and shock.id not in run.read:
        return f'Next: read_source {shock.id}.'
    if run.shock_delivered and shock is not None and not any(shock.id in r['evidence_ids'] for r in run.revisions):
        return 'You have new evidence. Decide what it means for each theory.'
    return 'Next: finish, or investigate further if you still need to.'


def searches(run: Investigation) -> dict[str, int]:
    """Searches the model may still spend on evidence, with the one held back for challenge_theory counted apart.
    The raw tool result counts the held-back search too, which led teacher and student to search into a refusal."""
    left = max(run.case.search_budget - len(run.searches), 0)
    held = 1 if left and not run.challenge_searches else 0
    return {'searches_left': left - held, 'kept_for_challenge': held}



def guidance(run: Investigation) -> Json:
    """Added to each tool result shown to the model, never to the recorded result, so recordings still replay."""
    stage = current_stage(run)
    return {'next': stage.instruction, 'open_tools': list(stage.tools), **searches(run)}


def stuck_help_text(run: Investigation) -> str:
    """After refusals in a row: what the agent can do instead, from its own state, so one stuck moment does not end the
    run. Opt-in (play(stuck_help=True)), recorded in the episode settings; it adds words to what the model is shown and
    never changes a tool result, so recordings still replay (DECISIONS, 2026-11-08)."""
    last = run.calls[-1] if run.calls else {}
    name, category = last.get('name', ''), last.get('category', '')
    stage = current_stage(run)
    unread = sorted(i for i in run.surfaced if i not in run.read)
    real = sorted(i for i in run.read if run._source(i).type != 'synthetic')
    if category == 'synthetic_as_evidence' and name == 'finish':
        return (f'Your last calls were refused because they cite the simulated result as evidence. Call finish again with evidence_ids '
                f'taken only from real sources you read: {real[:6]}. The simulated result may shape your uncertainty, not your evidence.')
    if category == 'synthetic_as_evidence':
        return 'A simulated result cannot support or contradict a theory about real demand: assess it as neutral, or use revise_theory.'
    if category == 'repeat' and name in ('search_evidence', 'challenge_theory'):
        return (f'That search already ran. Read one of its unread results instead: {unread[:4]}.' if unread
                else f'That search already ran and its results are read. Search a different angle, or move on with {list(stage.tools)}.')
    if category == 'repeat' and name == 'assess_evidence':
        weighed = {(a['theory_id'], a['evidence_id']) for a in run.assessments}
        todo = [(t, i) for t in run.theories for i in real if (t, i) not in weighed][:3]
        return f'You already weighed that source for that theory. Weigh another pair instead, e.g. {todo}, or move on with {list(stage.tools)}.' if todo else f'Every source read is weighed for every theory: move on with {list(stage.tools)}.'
    if category == 'repeat':
        return f'That call already ran. Take a different step: {list(stage.tools)}.'
    return f'Your last calls were refused. Change the call as the error says, or take another step: {list(stage.tools)}.'
