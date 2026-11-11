"""New training cases written by DeepSeek, from public sources our verifier checks (DECISIONS 2026-11-10 23:30 UTC).

Claude may not author training data, and a case's question and brief go into every training row, so these cases are
written by DeepSeek. DeepSeek's terms allow training other models on its outputs. NO TRAINING here.

    propose   DeepSeek lists manufacturers not already in any dossier file.
    research  per company: web searches (ddgs), the pages fetched as verify_sources does, and DeepSeek copies exact
              quotes with their metadata, plus one or two sentences on what the company makes and for whom.
    then      python -m aemon.data.verify_sources FOLDER/raw.json FOLDER/raw_verification.json
              (a quote enters only if it is on its live page), cases.json from the fixed template, and
              python -m aemon.data.add_cases --split training FOLDER

The question and most of the brief are the existing template, word for word. DeepSeek writes only the company
description and the records, and every record must be verified on its page.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import time
from pathlib import Path
from typing import Any

from aemon.agent.backends import hosted_client
from aemon.common.types import Json
from aemon.data.verify_sources import page_text

ROOT = Path(__file__).resolve().parents[3]
KINDS = ('company_assertion', 'news_report', 'survey', 'market_data', 'regulatory', 'retail_listing', 'academic')
QUERIES = ('{n} company products customers', '{n} annual report sales by segment', '{n} consumer products retail',
           '{n} distribution channels dealers', '{n} market share industry', '{n} history founded')
TEMPLATE = ('{description} You have not been told how far it already reaches individual buyers, so find out. You are an '
            'outside analyst working only from public sources. This company has not asked this question, has not been '
            'contacted, and nothing here describes its intentions. Some of its financial and contractual detail may not be '
            'public, so say what you could not find. Product redesign, a different route to buyers, a different customer '
            'group and no expansion are all open. The test budget of 20000 euros and the 12-week limit are analyst '
            'assumptions for this exercise, not company figures. ')
QUESTION = ('Should {company} develop a differentiated consumer proposition for a specific use case, beyond its existing '
            '{offer}? What evidence would justify that investment?')

PROPOSE = {'type': 'object', 'additionalProperties': False, 'required': ['companies'], 'properties': {'companies': {
    'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'slug', 'why'],
                               'properties': {'name': {'type': 'string'}, 'slug': {'type': 'string', 'maxLength': 24},
                                              'why': {'type': 'string', 'maxLength': 200}}}}}}
RECORD = {'type': 'object', 'additionalProperties': False,
          'required': ['url', 'source_title', 'source_date', 'excerpt', 'type', 'kind', 'geography', 'population', 'does_not_establish'],
          'properties': {'url': {'type': 'string'}, 'source_title': {'type': 'string', 'maxLength': 200},
                         'source_date': {'type': 'string', 'maxLength': 10}, 'excerpt': {'type': 'string', 'maxLength': 450},
                         'type': {'type': 'string', 'enum': ['company_claim', 'verified_observation']},
                         'kind': {'type': 'string', 'enum': list(KINDS)}, 'geography': {'type': 'string', 'maxLength': 80},
                         'population': {'type': 'string', 'maxLength': 120}, 'does_not_establish': {'type': 'string', 'maxLength': 240}}}
RESEARCH = {'type': 'object', 'additionalProperties': False, 'required': ['description', 'offer', 'records'],
            'properties': {'description': {'type': 'string', 'maxLength': 420}, 'offer': {'type': 'string', 'maxLength': 160},
                           'records': {'type': 'array', 'items': RECORD}}}


def known() -> set[str]:
    names = set()
    for f in ('cases.json', 'cases_heldout.json', 'cases_heldout2.json'):
        names |= {c['company'] for c in json.loads((ROOT / 'data' / 'dossier' / f).read_text())['cases']}
    return names


def propose(n: int, output: str) -> None:
    exclude = sorted(known())
    ask = (f'List {n} real manufacturers, each mainly selling to businesses or institutions (industrial, medical, safety, '
           'laboratory, agricultural, building or professional equipment and materials), whose technology could plausibly '
           'reach a consumer use case. Mix countries, sizes and eras: some listed, some family-owned, and about a third '
           'historical cases (a company as it was in a named past year). Do not include any of these, or a company in the '
           'same group: ' + '; '.join(exclude) + '. For each: its name, a short lowercase slug (letters only), and one line '
           'on its technology and customers. Answer with the answer tool.')
    reply = hosted_client.chat('hosted', [{'role': 'user', 'content': ask}], 0, 6000, PROPOSE, 0.0)
    companies = json.loads(reply['text'])['companies']
    taken = {re.sub(r'[^a-z]', '', x.lower()) for x in exclude}
    companies = [c for c in companies if re.sub(r'[^a-z]', '', c['name'].lower()) not in taken]
    Path(output).write_text(json.dumps(companies, ensure_ascii=False, indent=1))
    print(json.dumps({'proposed': len(companies)}))


def search(query: str, k: int = 4) -> list[Json]:
    from ddgs import DDGS

    for attempt in range(2):
        try:
            found = DDGS().text(query, max_results=k + 2)
            return [{'title': r.get('title', ''), 'url': r.get('href', '')} for r in found if r.get('href', '').startswith('http')][:k]
        except Exception:  # noqa: BLE001
            time.sleep(2 + attempt * 3)
    return []


def pages(company: str) -> list[Json]:
    seen, out = set(), []
    for q in QUERIES:
        for hit in search(q.format(n=company)):
            if hit['url'] in seen or len(out) >= 10:
                continue
            seen.add(hit['url'])
            try:
                text = re.sub(r'\s+', ' ', page_text(hit['url']))
            except Exception:  # noqa: BLE001  unreachable pages are skipped, as the verifier would fail them
                continue
            if len(text) > 800:
                out.append({'url': hit['url'], 'title': hit['title'], 'text': text[:7000]})
    return out


def research_one(company: Json) -> Json | None:
    found = pages(company['name'])
    if len(found) < 3:
        return None
    ask = ('You are building an evidence dossier from public sources about ' + company['name'] + '. Below are web pages, '
           'each with its URL. Copy 8 to 12 short quotes WORD FOR WORD from them (one or two sentences each, no ellipses, no '
           'edits): they are checked letter for letter against the live page, and a quote not on its page is dropped. '
           'Cover what the company makes, for whom, how it sells, its size, any reach to consumers or retail, and the '
           'market. For each quote give its URL exactly as given, the page title, the date the page states (YYYY-MM-DD, '
           'YYYY-MM or YYYY; "unknown" if none), type company_claim when the company says it about itself and '
           'verified_observation otherwise, the kind, the geography and population it is about, and what it does NOT '
           'establish. Then write description: one or two sentences on what the company makes and for whom, using only '
           'facts in your quotes, and offer: a short phrase naming its existing products and customers. Answer with the '
           'answer tool.\n\n' + '\n\n'.join(f'URL: {p["url"]}\nTITLE: {p["title"]}\nTEXT: {p["text"]}' for p in found))
    reply = hosted_client.chat('hosted', [{'role': 'user', 'content': ask}], 0, 8000, RESEARCH, 0.0)
    try:
        out = json.loads(reply['text'])
    except json.JSONDecodeError:
        return None
    slug = company['slug']
    records = []
    for i, r in enumerate(out['records']):
        if r['url'] in {p['url'] for p in found}:
            records.append(dict(r, id=f'{slug}-{i + 1:02d}', access_limitation='none', bears_on='[]'))
    return {'name': company['name'], 'slug': slug, 'description': out['description'], 'offer': out['offer'], 'records': records}


def research(companies_path: str, folder: str, workers: int) -> None:
    companies = json.loads(Path(companies_path).read_text())
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        done = [x for x in pool.map(research_one, companies) if x and len(x['records']) >= 4]
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    raw = {'accessed': time.strftime('%Y-%m-%d'), 'author': f'DeepSeek ({hosted_client.model()}), quotes from live pages',
           'companies': [{k: c[k] for k in ('name', 'slug', 'records')} for c in done]}
    (out / 'raw.json').write_text(json.dumps(raw, ensure_ascii=False, indent=1))
    (out / 'descriptions.json').write_text(json.dumps({c['slug']: {'name': c['name'], 'description': c['description'], 'offer': c['offer']} for c in done},
                                                     ensure_ascii=False, indent=1))
    print(json.dumps({'companies': len(done), 'records': sum(len(c['records']) for c in done), 'spent_usd_estimate': round(hosted_client.spent(), 4)}))


def cases(folder: str) -> None:
    """cases.json from the template, using only verified records; a company with fewer than 4 verified records is left out."""
    out = Path(folder)
    raw = json.loads((out / 'raw.json').read_text())
    verified = {r['id'] for r in json.loads((out / 'raw_verification.json').read_text())['results'] if r['status'] == 'verified'}
    desc = json.loads((out / 'descriptions.json').read_text())
    made, kept_companies = [], []
    for c in raw['companies']:
        ok = [r for r in c['records'] if r['id'] in verified]
        if len(ok) < 4:
            continue
        kept_companies.append(dict(c, records=ok))
        d = desc[c['slug']]
        premise = [r['id'] for r in ok if r['type'] == 'company_claim'][:3] or [ok[0]['id']]
        made.append({'company': c['name'], 'question': QUESTION.format(company=c['name'], offer=d['offer']),
                     'brief': TEMPLATE.format(description=d['description'].strip()), 'scope': c['slug'], 'search_budget': 8,
                     'test_budget': 20000, 'max_test_weeks': 12, 'id': f'{c["slug"]}-base', 'premise_records': premise, 'test_warranted': True})
    (out / 'raw.json').write_text(json.dumps(dict(raw, companies=kept_companies), ensure_ascii=False, indent=1))
    (out / 'cases.json').write_text(json.dumps({'cases': made}, ensure_ascii=False, indent=1))
    print(json.dumps({'cases': len(made), 'verified_records': sum(len(c['records']) for c in kept_companies)}))


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='step', required=True)
    a = sub.add_parser('propose')
    a.add_argument('--n', type=int, default=40)
    a.add_argument('--output', required=True)
    b = sub.add_parser('research')
    b.add_argument('--companies', required=True)
    b.add_argument('--folder', required=True)
    b.add_argument('--workers', type=int, default=8)
    c = sub.add_parser('cases')
    c.add_argument('--folder', required=True)
    args: Any = p.parse_args()
    if args.step == 'propose':
        propose(args.n, args.output)
    elif args.step == 'research':
        research(args.companies, args.folder, args.workers)
    else:
        cases(args.folder)


if __name__ == '__main__':
    main()
