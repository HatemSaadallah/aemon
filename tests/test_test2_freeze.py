"""The second test set: frozen, unseen by development and training, and separate from the final test."""

import json

from aemon.common.paths import DOCS
from aemon.environment.cases import load_cases
from aemon.data.freeze import digest


def test_the_second_test_set_is_frozen_and_development_never_sees_it():
    frozen = json.loads((DOCS / 'test2_freeze.json').read_text())
    assert digest('cases_heldout2.json')['digest'] == frozen['digest']
    test2 = load_cases(split='heldout2')
    scopes = {c.id.split('-')[0] for c in test2} | {r.scope for c in test2 for r in c.dossier.records.values()} - {'market'}
    for case in load_cases() + load_cases(split='heldout'):
        assert not scopes & {r.scope for r in case.dossier.records.values()}
    names = {c.company for c in load_cases() + load_cases(split='heldout')}
    assert not names & {c.company for c in test2} and len({c.company for c in test2}) == 12
