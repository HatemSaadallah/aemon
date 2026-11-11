"""Twelve guarded tools for one investigation: ten always, plus state_position and decline_test in staged runs, and
company_status when the status check is on. Everything authoritative lives here, not with the agent.

A refused call changes nothing, says why, and is logged with a category. Quotes must match the
source exactly, and evidence must have been read before it is used. A synthetic record may prompt
a revision, but it cannot be cited as support for a theory or for the recommendation. These guards
catch mechanical errors only. A correct quote can still be misused, which no guard can see.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

from aemon.common.constants.env import BELIEFS, EVIDENCE_KINDS, MAX_THEORIES, MIN_LIMIT, MIN_QUOTE, SYNTHETIC_CLASSES  # noqa: F401
from aemon.common.constants.prompts import POSITION_SIGNATURE, TOOL_SIGNATURES  # noqa: F401
from aemon.common.types import Json
from aemon.environment.dossier import Dossier, Record, normalise
from aemon.environment.stages import MIN_THEORIES, current_stage

# company_status: the company's name plus these words, the same for every company (DECISIONS 2026-11-11)
COMPANY_SUFFIXES = {'ltd', 'inc', 'plc', 'gmbh', 'group', 'corp', 'corporation', 'company', 'limited', 'holding', 'holdings', 'the', 'and'}
STATUS_QUERY = ('results annual report financial insolvency bankruptcy bankrupt going concern acquisition acquired merger profit '
                'warning restructuring funding rights issue delisting administration liquidity guidance outlook layoffs')


class Rejected(Exception):
    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category


def _fields(arguments: object, keys: Sequence[str]) -> None:
    if type(arguments) is not dict or set(arguments) != set(keys):
        wanted = f'exactly these arguments: {sorted(keys)}' if keys else 'no arguments: use "arguments": {}'
        raise Rejected('arguments', f'expected {wanted}')


def _text(value: object, name: str, limit: int = 600) -> str:
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise Rejected('arguments', f'{name}: expected text of at most {limit} characters')
    return value.strip()


def _texts(value: object, name: str, least: int = 1, most: int = 6, limit: int = 300) -> list[str]:
    if type(value) is not list or not least <= len(value) <= most:
        raise Rejected('arguments', f'{name}: expected a list of {least} to {most} items')
    return [_text(item, name, limit) for item in value]


def _number(value: object, name: str, low: float = 0) -> float:
    if type(value) not in (int, float) or not math.isfinite(cast(float, value)) or cast(float, value) < low:
        raise Rejected('arguments', f'{name}: expected a number of at least {low}')
    return cast(float, value)


@dataclass(frozen=True)
class Case:
    id: str
    company: str
    question: str
    brief: str
    search_budget: int
    test_budget: float  # in euros, an analyst assumption stated in the brief
    max_test_weeks: int
    dossier: Dossier
    shock: Record | None = None  # a labelled synthetic result, delivered once two theories exist
    shock_targets: tuple = ()  # patterns that identify the theories the shock bears on
    shock_direction: str = 'undermines'  # or 'supports', so always revising is not a winning policy
    simulated: bool = False  # true when the case itself is synthetic
    premise_records: tuple = ()  # records that correct an easy false premise about the company
    test_warranted: bool = True  # declared before any run: is more information worth its cost here?


class Investigation:
    def __init__(
        self, case: Case, complete_workflow: bool = False, staged: bool = False, quote_marks: bool = False, reread_limit: int | None = None,
        source_dates: bool = False,
        min_assessed: int = 1,
        status_check: bool = False,
    ) -> None:
        self.case = case
        # Opt-in (DECISIONS 2026-11-11, Aquaporin): company_status, then reading one of its results, comes right after
        # framing, and finish must cite a status source it read. Recorded in each episode's settings, so episodes made
        # without it replay unchanged.
        self.status_check = status_check
        self.status_ids: list[str] | None = None
        # Opt-in: refuse reading one source more than this many times (its full text is already in the state). Recorded in
        # each episode's settings, so episodes made without it replay unchanged (DECISIONS, 2026-11-08).
        self.reread_limit = reread_limit
        self.source_dates = source_dates  # the state lists each source's date (opt-in; DECISIONS, 2026-11-08)
        self.min_assessed = min_assessed  # weighed sources each theory needs before the investigation moves on (1 as evaluated)
        self.read_counts: dict[str, int] = {}
        self.complete_workflow = complete_workflow  # refuse finish until every stage has happened
        self.staged = staged  # the stage controller decides which tools are open
        # Quotation marks around an exact quote are formatting, not words. Half the teacher's refused quotes were exact words
        # in quotation marks. Recorded in each episode's settings, so episodes made before this replay under the old rule.
        self.quote_marks = quote_marks
        self.calls = []
        self.searches = []
        self.challenge_searches = []
        self.surfaced, self.read = set(), set()
        self.frame = None
        self.theories, self.assessments, self.tests, self.revisions = {}, [], {}, []
        self.final = None
        self.position = None
        self.test_declined = None
        self.brief_read = False
        self.shock_delivered = False
        self._handlers = {
            'read_brief': self._read_brief,
            'frame_problem': self._frame,
            'search_evidence': self._search,
            'challenge_theory': self._challenge,
            'read_source': self._read_source,
            'add_theory': self._add_theory,
            'assess_evidence': self._assess,
            'propose_test': self._propose_test,
            'revise_theory': self._revise,
            'finish': self._finish,
        }
        if staged:
            self._handlers.update(state_position=self._state_position, decline_test=self._decline_test)
        if status_check:
            self._handlers['company_status'] = self._company_status

    def call(self, name: object, arguments: object) -> Json:
        entry = {'name': name, 'arguments': arguments}
        try:
            if type(name) is not str or name not in self._handlers:
                raise Rejected('unknown_tool', f'no tool named {name}')
            if self.final is not None:
                raise Rejected('after_finish', 'the investigation is finished')
            if self.staged:
                stage = current_stage(self)
                entry['stage'] = stage.name
                if name not in stage.tools:
                    raise Rejected('stage', f'not at this stage ({stage.name}). Open now: {list(stage.tools)}')
            result = self._handlers[name](arguments)
            entry.update(accepted=True, result=result)
        except Rejected as error:
            result = {'error': str(error)}
            entry.update(accepted=False, category=error.category, result=result)
        self.calls.append(entry)
        return result

    def _need_frame(self) -> None:
        if self.frame is None:
            raise Rejected('order', 'call frame_problem first')

    def _read_brief(self, arguments: Json) -> Json:
        _fields(arguments, ())
        self.brief_read = True
        case = self.case
        return {
            'company': case.company,
            'question': case.question,
            'brief': case.brief,
            'search_budget': case.search_budget,
            'test_budget_eur': case.test_budget,
            'max_test_weeks': case.max_test_weeks,
            'simulated_case': case.simulated,
        }

    def _frame(self, arguments: Json) -> dict[str, bool]:
        if self.frame is not None:
            raise Rejected('repeat', 'the problem is already framed')
        if not self.brief_read:
            raise Rejected('order', 'call read_brief first')
        _fields(arguments, ('objective', 'constraints', 'alternatives'))
        self.frame = {
            'objective': _text(arguments['objective'], 'objective'),
            'constraints': _texts(arguments['constraints'], 'constraints'),
            'alternatives': _texts(arguments['alternatives'], 'alternatives', least=2),
        }
        return {'accepted': True}

    def _search(self, arguments: Json) -> Json:
        _fields(arguments, ('query',))
        self._need_frame()
        return self._run_search(_text(arguments['query'], 'query', 200), None)

    def _company_status(self, arguments: Json) -> Json:
        """The company's latest news, newest first: what an analyst checks before anything else. One fixed query, the same
        for every company (its name and words for a change in its position), so it names no answer. Uses no search."""
        _fields(arguments, ())
        self._need_frame()
        if self.status_ids is not None:
            raise Rejected('repeat', 'you already checked the company status. Read its results')
        real = [r for r in self.case.dossier.search(f'{self.case.company} {STATUS_QUERY}', k=40) if r.type not in SYNTHETIC_CLASSES]
        # only records that name the company: the query's words also match other companies' results and deals (for
        # Hellberg it returned 3M's); if none names it, the best matches as before
        names = {w for w in normalise(self.case.company).replace('/', ' ').split() if len(w) >= 3 and w not in COMPANY_SUFFIXES}
        named = [r for r in real if names & set(normalise(f'{r.title} {r.excerpt}').replace('/', ' ').split())]
        hits = named[:8] or real[:8]
        dated = sorted(hits, key=lambda r: (r.date[:1].isdigit(), r.date), reverse=True)[:3]
        self.status_ids = [r.id for r in dated]
        self.surfaced.update(self.status_ids)
        return {'results': [{'id': r.id, 'title': r.title, 'class': r.type, 'date': r.date} for r in dated],
                'note': "The company's latest news, newest first. Read one before building theories. finish asks for company_position: its current position and how that bears on the recommendation."}

    def _challenge(self, arguments: Json) -> Json:
        _fields(arguments, ('theory_id', 'query'))
        self._need_frame()
        self._need_theory(arguments['theory_id'])
        return self._run_search(_text(arguments['query'], 'query', 200), arguments['theory_id'])

    def _run_search(self, query: str, target: str | None) -> Json:
        left = self.case.search_budget - len(self.searches)
        if left <= 0:
            raise Rejected('budget', 'no searches left')
        if self.staged and target is None and left == 1 and not self.challenge_searches:
            raise Rejected('budget', 'your last search is kept for challenge_theory')
        if normalise(query) in {normalise(q) for q in self.searches}:
            raise Rejected('repeat', 'you already ran that search. Read its results, or search for something different')
        hits = self.case.dossier.search(query)
        self.searches.append(query)
        if target:  # looking for a challenge is what counts, whatever it finds
            self.challenge_searches.append({'theory_id': target, 'query': query, 'found': [r.id for r in hits]})
        self.surfaced.update(r.id for r in hits)
        return {'results': [{'id': r.id, 'title': r.title, 'class': r.type} for r in hits], 'searches_left': left - 1}

    def _source(self, identifier: str) -> Record:
        """A source the run has already read or been given, so it exists."""
        record = self._record(identifier)
        if record is None:
            raise LookupError(f'no source {identifier}')
        return record

    def _record(self, identifier: str) -> Record | None:
        record = self.case.dossier.records.get(identifier)
        if record is None and self.shock_delivered and self.case.shock is not None and self.case.shock.id == identifier:
            record = self.case.shock
        return record

    def _read_source(self, arguments: Json) -> dict[str, str]:
        _fields(arguments, ('id',))
        identifier = arguments['id']
        record = self._record(identifier) if type(identifier) is str else None  # rereading is free
        if record is None or identifier not in self.surfaced:
            raise Rejected('fabricated', 'that id did not come from a search')
        if self.reread_limit is not None and self.read_counts.get(identifier, 0) >= self.reread_limit:
            raise Rejected(
                'repeat',
                'you already have this source: its full text is in sources_read, and reading it again returns the same text. '
                'Use what you have: assess it, or take the next step of the stage.',
            )
        self.read_counts[identifier] = self.read_counts.get(identifier, 0) + 1
        self.read.add(identifier)
        return {
            'id': record.id,
            'class': record.type,
            'title': record.title,
            'url': record.url,
            'date': record.date,
            'geography': record.geography,
            'excerpt': record.excerpt,
            'access_limitation': record.access_limitation,
        }

    def _add_theory(self, arguments: Json) -> dict[str, str]:
        self._need_frame()
        _fields(arguments, ('claim', 'who_benefits', 'why_behaviour_changes', 'how_value_is_captured', 'assumptions', 'predictions'))
        if len(self.theories) >= MAX_THEORIES:
            raise Rejected('budget', f'at most {MAX_THEORIES} theories')
        if any(normalise(t['claim']) == normalise(str(arguments['claim'])) for t in self.theories.values()):
            raise Rejected('repeat', 'you already have that theory. A new theory must give a different causal explanation')
        identifier = f'T{len(self.theories) + 1}'
        self.theories[identifier] = {
            'claim': _text(arguments['claim'], 'claim'),
            'who_benefits': _text(arguments['who_benefits'], 'who_benefits'),
            'why_behaviour_changes': _text(arguments['why_behaviour_changes'], 'why_behaviour_changes'),
            'how_value_is_captured': _text(arguments['how_value_is_captured'], 'how_value_is_captured'),
            'assumptions': _texts(arguments['assumptions'], 'assumptions'),
            'predictions': _texts(arguments['predictions'], 'predictions'),
            'status': 'open',
            'first_claim': arguments['claim'].strip(),
        }
        result: Json = {'theory_id': identifier}
        if not self.staged and self.case.shock is not None and not self.shock_delivered and len(self.theories) >= 2:
            # Every run that holds two theories gets the same chance to respond.
            result['update'] = self._deliver_shock()
        return result

    def _deliver_shock(self) -> dict[str, str]:
        shock = cast(Record, self.case.shock)  # only called in cases that have one
        self.shock_delivered = True
        self.surfaced.add(shock.id)
        return {
            'id': shock.id,
            'title': shock.title,
            'class': 'synthetic',
            'note': 'A new SIMULATED result is available. Read it with read_source.',
        }

    def _beliefs(self, value: object) -> Json:
        """The model's own view of each theory. The harness calculates nothing from these."""
        if type(value) is not dict or set(value) != set(self.theories) or any(v not in BELIEFS for v in value.values()):
            raise Rejected('arguments', f'beliefs needs one of {list(BELIEFS)} for each of {sorted(self.theories)}')
        return value

    def _decline_test(self, arguments: Json) -> dict[str, bool]:
        _fields(arguments, ('reason',))
        self.test_declined = _text(arguments['reason'], 'reason')
        return {'recorded': True}

    def _state_position(self, arguments: Json) -> dict[str, bool]:
        """What the model believes just before new evidence, so its response can be read within one run."""
        _fields(arguments, ('favoured_theory', 'recommendation', 'beliefs'))
        favoured = arguments['favoured_theory']
        self._need_theory(favoured)
        beliefs = self._beliefs(arguments['beliefs'])
        if not any(s['theory_id'] == favoured for s in self.challenge_searches):
            raise Rejected('order', f'use challenge_theory on {favoured} before you state it as your position')
        self.position = {'favoured_theory': favoured, 'recommendation': _text(arguments['recommendation'], 'recommendation', 900), 'beliefs': beliefs}
        result: Json = {'recorded': True}
        if self.case.shock is not None:  # the same point in every run, whatever came before it
            result['update'] = self._deliver_shock()
        return result

    def _need_theory(self, identifier: object) -> None:
        if type(identifier) is not str or identifier not in self.theories:
            raise Rejected('unknown_theory', f'no theory {identifier}')

    def _assess(self, arguments: Json) -> Json:
        _fields(arguments, ('theory_id', 'evidence_id', 'direction', 'quote', 'evidence_kind', 'does_not_show'))
        self._need_theory(arguments['theory_id'])
        identifier = arguments['evidence_id']
        if type(identifier) is not str or identifier not in self.read:
            raise Rejected('unread_evidence', 'read_source that evidence first')
        if arguments['direction'] not in ('supports', 'contradicts', 'neutral'):
            raise Rejected('arguments', 'direction must be supports, contradicts or neutral')
        quote = _text(arguments['quote'], 'quote')
        if self.quote_marks:
            quote = quote.strip().strip('"\'“”‘’').strip()
        if len(normalise(quote)) < MIN_QUOTE or len(quote.split()) < 3:
            raise Rejected('arguments', f'quote at least 3 words and {MIN_QUOTE} characters')
        if normalise(quote) not in normalise(self._source(identifier).excerpt):
            raise Rejected('misquote', 'that quote is not in the source. Copy its exact words')
        if arguments['evidence_kind'] not in EVIDENCE_KINDS:
            raise Rejected('arguments', f'evidence_kind must be one of {list(EVIDENCE_KINDS)}')
        limit = _text(arguments['does_not_show'], 'does_not_show')
        if len(limit) < MIN_LIMIT:
            raise Rejected('arguments', f'does_not_show: say what this evidence cannot establish, in at least {MIN_LIMIT} characters')
        if self._source(identifier).type in SYNTHETIC_CLASSES and arguments['direction'] == 'supports':
            raise Rejected('synthetic_as_evidence', 'a simulated result cannot support a theory about real demand. Use neutral, or revise_theory')
        pair = (arguments['theory_id'], identifier)
        if any((a['theory_id'], a['evidence_id']) == pair for a in self.assessments):
            raise Rejected('repeat', 'that evidence is already assessed for that theory')
        self.assessments.append(
            {
                'theory_id': arguments['theory_id'],
                'evidence_id': identifier,
                'direction': arguments['direction'],
                'quote': quote,
                'class': self._source(identifier).type,
                'evidence_kind': arguments['evidence_kind'],
                'does_not_show': limit,
            }
        )
        return {'assessed': True, 'class_of_evidence': self._source(identifier).type}

    def _propose_test(self, arguments: Json) -> dict[str, str]:
        _fields(arguments, ('name', 'theories', 'method', 'sample', 'measure', 'prediction_by_theory', 'decision_rule', 'cost_eur', 'weeks'))
        names = arguments['theories']
        if type(names) is not list or len(set(map(str, names))) < 2:
            raise Rejected('arguments', 'a test must compare at least two theories')
        for name in names:
            self._need_theory(name)
        predictions = arguments['prediction_by_theory']
        if type(predictions) is not dict or set(predictions) != set(names):
            raise Rejected('arguments', 'prediction_by_theory needs one prediction for each theory in the test')
        cost, weeks = _number(arguments['cost_eur'], 'cost_eur'), _number(arguments['weeks'], 'weeks', 1)
        spent = sum(t['cost_eur'] for t in self.tests.values())
        if spent + cost > self.case.test_budget:
            raise Rejected('budget', f'that goes over the test budget of {self.case.test_budget}')
        if weeks > self.case.max_test_weeks:
            raise Rejected('budget', f'tests can run for at most {self.case.max_test_weeks} weeks')
        identifier = f'X{len(self.tests) + 1}'
        self.tests[identifier] = {
            'name': _text(arguments['name'], 'name', 120),
            'theories': list(names),
            'method': _text(arguments['method'], 'method', 900),
            'sample': _text(arguments['sample'], 'sample'),
            'measure': _text(arguments['measure'], 'measure'),
            'prediction_by_theory': {k: _text(v, 'prediction') for k, v in predictions.items()},
            'decision_rule': _text(arguments['decision_rule'], 'decision_rule', 900),
            'cost_eur': cost,
            'weeks': weeks,
        }
        return {'test_id': identifier, 'note': 'Proposed only. Nothing has been run, and its figures are analyst assumptions.'}

    def _revise(self, arguments: Json) -> dict[str, bool]:
        _fields(arguments, ('theory_id', 'status', 'reason', 'new_claim', 'evidence_ids'))
        self._need_theory(arguments['theory_id'])
        if arguments['status'] not in ('kept', 'revised', 'rejected'):
            raise Rejected('arguments', 'status must be kept, revised or rejected')
        reason = _text(arguments['reason'], 'reason')
        evidence = arguments['evidence_ids']
        if (
            type(evidence) is not list
            or not evidence
            or any(e not in self.read for e in evidence if type(e) is str)
            or any(type(e) is not str for e in evidence)
        ):
            raise Rejected('unread_evidence', 'evidence_ids must list evidence you have read')
        theory = self.theories[arguments['theory_id']]
        new_claim = None
        if arguments['status'] == 'revised':
            new_claim = _text(arguments['new_claim'], 'new_claim')
            if normalise(new_claim) == normalise(theory['claim']):
                raise Rejected('arguments', 'a revised theory must say something different. Write the changed claim in new_claim')
            theory['claim'] = new_claim
        theory['status'] = arguments['status']
        self.revisions.append(
            {'theory_id': arguments['theory_id'], 'status': arguments['status'], 'reason': reason, 'new_claim': new_claim, 'evidence_ids': evidence}
        )
        return {'recorded': True}

    def missing_stages(self) -> list[Any]:
        """What a complete investigation still lacks. It names steps, and judges no content."""
        missing = []
        if len(self.read) < 3:
            missing.append('read at least 3 sources')
        if len(self.theories) < MIN_THEORIES:
            missing.append(f'add theories: you have {len(self.theories)} of {MIN_THEORIES}')
        unassessed = [k for k in self.theories if not any(a['theory_id'] == k for a in self.assessments)]
        if unassessed:
            missing.append(f'assess evidence for {unassessed}')
        if not self.challenge_searches:
            missing.append('use challenge_theory on your favoured theory')
        if not self.tests:
            missing.append('propose_test')
        return missing

    def _finish(self, arguments: Json) -> dict[str, bool]:
        _fields(
            arguments,
            ('recommendation', 'target_customer', 'value_proposition', 'favoured_theory', 'next_action', 'uncertainty', 'would_change_if', 'evidence_ids')
            + (('beliefs',) if self.staged else ())
            + (('company_position',) if self.status_check else ()),
        )
        self._need_frame()
        if self.staged:
            self._beliefs(arguments['beliefs'])
        if self.complete_workflow and self.missing_stages():
            raise Rejected('order', 'not finished yet. Still needed: ' + '; '.join(self.missing_stages()))
        self._need_theory(arguments['favoured_theory'])
        evidence = arguments['evidence_ids']
        if type(evidence) is not list or not evidence or any(type(e) is not str or e not in self.read for e in evidence):
            raise Rejected('unread_evidence', 'evidence_ids must list evidence you have read')
        if any(self._source(e).type in SYNTHETIC_CLASSES for e in evidence):
            raise Rejected('synthetic_as_evidence', 'a simulated result cannot support a recommendation about real demand')
        # The status check asks for a statement, not a citation: requiring a status source among evidence_ids was met by
        # appending the id without a word about it (Aquaporin), and refused runs whose status results were incidental
        self.final = {
            'recommendation': _text(arguments['recommendation'], 'recommendation', 900),
            'target_customer': _text(arguments['target_customer'], 'target_customer'),
            'value_proposition': _text(arguments['value_proposition'], 'value_proposition'),
            'favoured_theory': arguments['favoured_theory'],
            'next_action': _text(arguments['next_action'], 'next_action'),
            'uncertainty': _text(arguments['uncertainty'], 'uncertainty'),
            'would_change_if': _texts(arguments['would_change_if'], 'would_change_if'),
            'evidence_ids': evidence,
        }
        if self.staged:
            self.final['beliefs'] = arguments['beliefs']
        if self.status_check:
            self.final['company_position'] = _text(arguments['company_position'], 'company_position')
        return {'finished': True}
