import json

from aemon.agent.experimental import novelty
from aemon.environment.cases import load_cases
from aemon.environment.dossier import Dossier
from aemon.environment.tools import Investigation


def test_ranking_matches_the_original_and_import_changes_nothing():
    case = next(c for c in load_cases() if c.id == 'hellberg-base')
    for q in ('consumer demand', 'dishwasher household price', 'regulation hygiene standard'):
        assert [r.id for r in Dossier.search(case.dossier, q)] == novelty.ranked(case.dossier, q)[:3]
    assert Dossier.search is novelty._SEARCH and Investigation._run_search is novelty._RUN_SEARCH


def test_a_repeated_topic_returns_unseen_records_first(monkeypatch):
    monkeypatch.setattr(Dossier, 'search', novelty.search)
    monkeypatch.setattr(Investigation, '_run_search', novelty.run_search)
    case = next(c for c in load_cases() if c.id == 'hellberg-base')
    run = Investigation(case)
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'decide', 'constraints': ['budget'], 'alternatives': ['invest', 'do not invest']})
    first = [r['id'] for r in run.call('search_evidence', {'query': 'consumer demand'})['results']]
    second = [r['id'] for r in run.call('search_evidence', {'query': 'consumer demand households'})['results']]
    order = novelty.ranked(case.dossier, 'consumer demand households')
    assert second == ([i for i in order if i not in first] + [i for i in order if i in first])[:3]
    assert run.call('search_evidence', {'query': 'consumer demand'}).get('error')  # the repeat refusal is unchanged
