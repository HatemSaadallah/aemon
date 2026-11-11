"""Live web research for Try it: labels, snapshots, and quotes held to the saved excerpt. No network."""

import json

from aemon.environment.cases import load_cases
from aemon.environment.live import LiveDossier
from aemon.environment.tools import Investigation

PAGES = {
    'https://www.hellbergsafety.com/consumers': '<html><nav>menu</nav><p>Hellberg sells hearing protectors to retail buyers through partners. Comfort is the main reason users keep them on.</p></html>',
    'https://www.cdc.gov/niosh/hearing': '<p>Workers often stop wearing hearing protection because of comfort and communication problems, a NIOSH survey found.</p>',
}


def fake_search(query, k):
    return [{'title': url.split('/')[-1], 'url': url, 'snippet': 'snippet'} for url in PAGES][:k]


def test_live_pages_are_labelled_snapshotted_and_quoted_exactly(tmp_path):
    dossier = LiveDossier('Hellberg Safety', tmp_path, search=fake_search, fetch=PAGES.__getitem__)
    hits = dossier.search('why do workers stop wearing hearing protection comfort', 3)
    assert [h.type for h in hits] == ['company_claim', 'web_page']
    assert all(h.date.startswith('retrieved ') for h in hits)
    snapshot = json.loads((tmp_path / f'{hits[1].id}.json').read_text())
    assert snapshot['url'] == 'https://www.cdc.gov/niosh/hearing' and len(snapshot['text_sha256']) == 64 and 'menu' not in snapshot['excerpt']

    case = next(c for c in load_cases() if c.id == 'hellberg-base')
    import dataclasses

    run = Investigation(dataclasses.replace(case, dossier=dossier), staged=False)
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': 'Decide', 'constraints': ['small budget'], 'alternatives': ['enter', 'do not enter']})
    found = run.call('search_evidence', {'query': 'workers stop wearing hearing protection comfort'})
    assert {r['id'] for r in found['results']} == {h.id for h in hits}
    read = run.call('read_source', {'id': hits[1].id})
    assert read['excerpt'] == hits[1].excerpt and read['class'] == 'web_page'
