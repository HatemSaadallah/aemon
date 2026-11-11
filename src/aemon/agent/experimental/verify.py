"""Evidence verification before the final recommendation: an experimental, separately run layer (2026-11-10).

When the agent calls finish, the proposed recommendation is checked once against what is on record. If anything is
found, the finish is not executed: the agent is shown the findings and may revise, or may finish with an explicit
"Insufficient evidence:" recommendation. Its next finish is executed as written, whatever it says. The layer only
reports. It never edits, deletes or invents evidence or text, it never blocks completion, and it costs at most one turn
per run. It does not count as a refused call.

Findings (each from the record, never from a model):
  late       a cited source dated after the year the case is set in (the agent is not shown dates otherwise)
  numbers    a number in the recommendation, customer, value proposition or uncertainty that is in no cited source
             or the brief
  support    no cited source was weighed as supporting the favoured theory
  company    the favoured theory's weighed support comes only from the company's own claims
  offering   the case records what the company already sells, and the investigation never read it

The evaluated runner (aemon.agent.run_investigations) is not changed: this module wraps one investigation's `call` method
through play's on_turn callback, and runs run_investigations.main with that wrapper:

    python -m aemon.agent.experimental.verify [the runner's arguments]  # development split only
"""

from __future__ import annotations

import sys
from typing import Any

from aemon.agent import loop, run_investigations
from aemon.common.types import Json
from aemon.environment.checks import _numbers
from aemon.teacher.targeted import YEAR

VERSION = 'verify-v1'
ABSTAIN = 'Insufficient evidence:'


def _year(case: Any) -> int | None:
    found = YEAR.search(f'{case.question} {case.brief}')
    return int(found.group(1)) if found else None


def findings(run: Any, args: Json) -> list[Json]:
    cited = [i for i in (args.get('evidence_ids') or []) if i in run.read and run._source(i).type != 'synthetic']
    out = []
    year = _year(run.case)
    for i in cited:
        date = str(getattr(run._source(i), 'date', '') or '')
        if year is not None and date[:4].isdigit() and int(date[:4]) > year:
            out.append({'kind': 'late', 'text': f'{i} is dated {date[:10]}, after the case is set ({year}): use it only for facts '
                                                 f'that were known by {year}, or do not cite it'})
    known = set().union(_numbers(run.case.brief), *(_numbers(run._source(i).excerpt) for i in cited))
    claims = ' '.join(str(args.get(k, '')) for k in ('recommendation', 'target_customer', 'value_proposition', 'uncertainty'))
    missing = sorted(_numbers(claims) - known)
    if missing:
        out.append({'kind': 'numbers', 'text': f'these numbers are in no source you cite or the brief: {", ".join(map(str, missing[:6]))}. '
                                               'Cite the source that gives them, or remove them, or state them as assumptions'})
    favoured = args.get('favoured_theory')
    support = [a for a in run.assessments if a['theory_id'] == favoured and a['direction'] == 'supports']
    cited_support = [a for a in support if a['evidence_id'] in cited]
    if not cited_support:
        out.append({'kind': 'support', 'text': f'no source you cite was weighed as supporting {favoured}: cite the weighed support, '
                                               'favour a theory the evidence supports, or say the evidence is insufficient'})
    elif all(run._source(a['evidence_id']).type == 'company_claim' for a in support):
        out.append({'kind': 'company', 'text': f"{favoured} rests only on the company's own claims: say so in the recommendation, "
                                               'or weigh an independent source first'})
    premise = set(run.case.premise_records or ())
    if premise and not premise & run.read:
        out.append({'kind': 'offering', 'text': 'the dossier records what the company already sells to these customers, and you '
                                                'have not read it: find it before recommending'})
    return out


def note(found: list[Json]) -> Json:
    return {
        'verification': [f['text'] for f in found],
        'verification_kinds': [f['kind'] for f in found],
        'next': ('Your finish was checked against the record and not yet submitted. Revise it so every claim rests on the '
                 'evidence you weighed, using other tools first if you need to. If the evidence cannot justify a '
                 f'recommendation, finish with a recommendation that begins "{ABSTAIN}" and says what would be needed. '
                 'Your next finish is submitted as written.'),
    }


def install(run: Any) -> None:
    if getattr(run, 'verification', None) is not None:
        return
    run.verification = []
    original = run.call

    def call(name: str, arguments: Json) -> Json:
        if name == 'finish' and not run.verification and isinstance(arguments, dict):
            found = findings(run, arguments)
            run.verification.append({'turn': len(run.calls), 'findings': [f['kind'] for f in found]})
            if found:
                return note(found)
        return original(name, arguments)

    run.call = call


def play(*args: Any, **kwargs: Any) -> Any:
    previous = kwargs.pop('on_turn', None)

    def on_turn(run: Any) -> None:
        install(run)
        if previous:
            previous(run)

    return _PLAY(*args, on_turn=on_turn, **kwargs)


_PLAY = loop.play


def main() -> None:
    if '--split' in sys.argv and sys.argv[sys.argv.index('--split') + 1] != 'development':
        raise SystemExit('the verification layer is experimental: development split only')
    run_investigations.play = play  # this process only; the evaluated loop's code and defaults are unchanged
    run_investigations.main()


if __name__ == '__main__':
    main()
