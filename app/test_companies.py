import json

import companies
from aemon.environment.cases import load_cases


def test_every_profile_fact_cites_its_own_companys_dossier():
    cases = {c.id: c for c in load_cases()}
    profiles = json.loads(companies.PROFILES.read_text())['companies']
    assert companies.validate(profiles, {cid: cases[f'{cid}-base'].dossier.records for cid in profiles}) == []


def test_library_marks_sources_published_after_a_historical_case():
    case = next(c for c in load_cases() if c.id == 'tanita-base')
    year = companies.case_year(case)
    assert year == 1993
    lib = companies.library(case, year)
    assert lib and all(s['after_case'] == (bool(s['date']) and s['date'][:4].isdigit() and int(s['date'][:4]) > 1993) for s in lib)
