"""Development-only measures added for the V2 comparison (docs/V2_CORRECTIVE_PLAN.md section 6), reported next to the
original checks and never in place of them. Mechanical and conservative: a pass here is necessary, not sufficient, and
the blind judge remains the measure of quality.

  numbers_cited      every number in the finish's claims appears in a source it cites or in the brief (the original
                     check accepts any source read)
  origin_honest      a favoured theory supported only by the company's own claims is not called proven, validated or
                     independently confirmed
  follows_evidence   the favoured theory has a supporting assessment from a cited real source, and no cited source was
                     assessed as contradicting it without the uncertainty saying so
  states_unknowns    the uncertainty names something unknown or untested, not just a restatement
  experiment_v2      the experiment check passes and its passing test clears the design screens (targeted.gate_mechanism)
  evidence_kinds_v2  as evidence_kinds (70% of assessments), but a kind counts as right if the v2 overlay lists it as
                     acceptable (data/dossier/evidence_kinds_v2.json), and a v1 kind outside the tool's six is mapped by
                     docs/EVIDENCE_KIND_GUIDE.md (company origin: company_assertion, else market_fact)

    python -m aemon.evaluation.diagnostics.grounding_v2 REPORT.json [REPORT.json ...]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from aemon.common.constants.env import EVIDENCE_KINDS
from aemon.common.types import Json
from aemon.environment.cases import load_cases
from aemon.environment.checks import _numbers, experiment
from aemon.evaluation.diagnostics.rescore import rebuild
from aemon.teacher.targeted import gate_mechanism

STRONG = re.compile(r'\b(proven|validated|confirm(?:s|ed)|independently|demonstrat(?:es|ed)|establish(?:es|ed))\b', re.I)
UNKNOWN = re.compile(r'\b(unknown|uncertain|unclear|not (?:yet )?(?:known|tested|shown|established|verified|quantified)|untested|unverified|no (?:evidence|data|source)|whether)\b', re.I)

Verdict = tuple[bool | None, str]


def _real(run: Any, ids: list[str]) -> list[str]:
    return [i for i in ids if i in run.read and run._source(i).type != 'synthetic']


def numbers_cited(run: Any) -> Verdict:
    if not run.final:
        return None, 'did not finish'
    f = run.final
    cited = _real(run, f.get('evidence_ids') or [])
    known = set().union(_numbers(run.case.brief), *(_numbers(run._source(i).excerpt) for i in cited))
    claims = ' '.join((f['recommendation'], f['target_customer'], f['value_proposition'], f['uncertainty']))
    missing = sorted(_numbers(claims) - known)
    return (not missing, f'numbers not in a cited source: {missing[:5]}' if missing else 'every claimed number is in a cited source')


def origin_honest(run: Any) -> Verdict:
    if not run.final:
        return None, 'did not finish'
    f = run.final
    support = [a for a in run.assessments if a['theory_id'] == f['favoured_theory'] and a['direction'] == 'supports']
    if not support or any(run._source(a['evidence_id']).type != 'company_claim' for a in support):
        return True, 'the favoured theory has non-company support, or none is claimed'
    text = ' '.join((f['recommendation'], f['value_proposition']))
    return (not STRONG.search(text), 'company claims presented as validation' if STRONG.search(text) else 'company-only support stated modestly')


def follows_evidence(run: Any) -> Verdict:
    if not run.final:
        return None, 'did not finish'
    f = run.final
    cited = set(_real(run, f.get('evidence_ids') or []))
    on = [a for a in run.assessments if a['theory_id'] == f['favoured_theory'] and a['evidence_id'] in cited]
    if not any(a['direction'] == 'supports' for a in on):
        return False, 'no cited source was weighed as supporting the favoured theory'
    against = [a['evidence_id'] for a in on if a['direction'] == 'contradicts']
    if against and not any(i in f['uncertainty'] for i in against) and not UNKNOWN.search(f['uncertainty']):
        return False, f'cited contradicting evidence not acknowledged: {against[:3]}'
    return True, 'the favoured theory rests on weighed, cited support'


def states_unknowns(run: Any) -> Verdict:
    if not run.final:
        return None, 'did not finish'
    u = run.final['uncertainty']
    return (bool(UNKNOWN.search(u)) and len(u.split()) >= 8, 'names what is unknown' if UNKNOWN.search(u) else 'no unknown named')


def experiment_v2(run: Any) -> Verdict:
    passed, detail = experiment(run)
    if not passed or run.test_declined is not None:
        return passed, detail
    screened = [gate_mechanism(run, t) for t in run.tests.values()]
    clean = [s for s in screened if not s]
    return (bool(clean), f'{len(clean)} of {len(screened)} tests clear the design screens' + (f': {screened[0]}' if not clean else ''))


OVERLAY = Path(__file__).resolve().parents[4] / 'data' / 'dossier' / 'evidence_kinds_v2.json'


def acceptable_kinds(source: Any, overlay: dict) -> set[str]:
    if source.id in overlay:
        return set(overlay[source.id]['acceptable'])
    if source.kind in EVIDENCE_KINDS:
        return {source.kind}
    return {'company_assertion' if source.type == 'company_claim' else 'market_fact'}


def evidence_kinds_v2(run: Any) -> Verdict:
    overlay = json.loads(OVERLAY.read_text())['records'] if OVERLAY.exists() else {}
    judged = [(a, acceptable_kinds(run._source(a['evidence_id']), overlay)) for a in run.assessments if run._source(a['evidence_id']).kind]
    if not judged:
        return None, 'nothing annotated was weighed'
    right = sum(a['evidence_kind'] in kinds for a, kinds in judged)
    return right / len(judged) >= 0.7, f'{right} of {len(judged)} kinds acceptable under v2'


MEASURES = {'numbers_cited': numbers_cited, 'origin_honest': origin_honest, 'follows_evidence': follows_evidence,
            'states_unknowns': states_unknowns, 'experiment_v2': experiment_v2, 'evidence_kinds_v2': evidence_kinds_v2}


def score(record: Json, cases: dict) -> dict[str, Verdict]:
    settings = {k: v for k, v in (record.get('settings') or {}).items() if k != 'recovery'}  # a controller setting, not the tools'
    run = rebuild({**record, 'settings': settings}, cases)
    return {k: f(run) for k, f in MEASURES.items()}


def main() -> None:
    cases = {c.id: c for c in load_cases()}
    for name in sys.argv[1:]:
        report = json.loads(Path(name).read_text())
        totals = {k: [0, 0] for k in MEASURES}
        for record in report['records']:
            for k, (ok, _) in score(record, cases).items():
                if ok is not None:
                    totals[k][1] += 1
                    totals[k][0] += bool(ok)
        print(Path(name).name, {k: f'{p}/{n}' for k, (p, n) in totals.items()})


if __name__ == '__main__':
    main()
