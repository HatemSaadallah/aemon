"""Company profiles for aemon (UI only).

Two sources, kept apart:
- `app/profiles/company_profiles.json`: curated profile facts. Every fact cites records of the company's own dossier,
  and `validate` refuses a profile whose citations do not exist.
- the company's dossier, read as it is: the source library, counted and listed, never changed.

Nothing here is read by the agent, its tools or its evaluation. The frozen research data (`data/dossier/`) is only
read.

Logos: none are bundled. A profile may name one under `logo` with its provenance (`file`, `source_url`, `retrieved`,
`licence_note`); without one the page shows a monogram. Accent colours are a design choice from a neutral palette,
not the company's brand colours.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PROFILES = Path(__file__).parent / 'profiles' / 'company_profiles.json'
ACCENTS = ['#3047c9', '#0f766e', '#9a3412', '#6d28d9', '#1d4ed8', '#b45309', '#be123c', '#047857']
YEAR = re.compile(r'\bIt is (?:early |mid-|late )?(?:[A-Z][a-z]+ )?(1[89]\d\d|20\d\d)\b')
CITED = ('industry', 'headquarters', 'founded', 'parent', 'website')
LISTS = ('about', 'products', 'customers', 'markets', 'timeline', 'positioning', 'context_companies')

_cache: dict[str, Any] = {}


def load() -> dict[str, Any]:
    if 'profiles' not in _cache:
        _cache['profiles'] = json.loads(PROFILES.read_text())['companies'] if PROFILES.exists() else {}
    return _cache['profiles']


def validate(profiles: dict[str, Any], dossiers: dict[str, dict[str, Any]]) -> list[str]:
    """Every citation must name a record of that company's own dossier."""
    problems = []
    for cid, p in profiles.items():
        records = dossiers.get(cid)
        if records is None:
            problems.append(f'{cid}: no such company in the app')
            continue
        cited = [s for k in CITED if p.get(k) for s in p[k].get('sources', [])]
        cited += [s for k in LISTS for item in p.get(k) or [] for s in item.get('sources', [])]
        problems += [f'{cid}: cites {s}, which is not in its dossier' for s in cited if s not in records]
    return problems


def case_year(case: Any) -> int | None:
    found = YEAR.search(case.question or '')
    return int(found.group(1)) if found else None


def publisher(title: str, url: str | None) -> str | None:
    for sep in (' · ', ' | ', ' — ', ' - '):
        if sep in title:
            return title.rsplit(sep, 1)[1].strip()[:80]
    host = re.sub(r'^https?://(www\.)?', '', url or '').split('/')[0]
    return host or None


def accent(cid: str, order: list[str]) -> str:
    return ACCENTS[order.index(cid) % len(ACCENTS)] if cid in order else ACCENTS[0]


def library(case: Any, year: int | None) -> list[dict[str, Any]]:
    """The company's sources as the dossier holds them, with the date relative to the case."""
    out = []
    for r in case.dossier.records.values():
        if r.type == 'synthetic':
            continue
        date = str(r.date or '')
        out.append({
            'id': r.id, 'title': r.title, 'publisher': publisher(r.title, r.url), 'url': r.url, 'date': date or None,
            'origin': r.type, 'kind': r.kind or None, 'about': r.topic or None, 'excerpt': r.excerpt,
            'limitation': r.access_limitation or None, 'does_not_establish': r.does_not_establish or None,
            'after_case': bool(year and date[:4].isdigit() and int(date[:4]) > year),
            'existing_offering': r.id in (case.premise_records or ()),
        })
    return sorted(out, key=lambda s: (s['date'] or '0000'), reverse=True)


def summary(cid: str, case: Any, order: list[str], investigations: int) -> dict[str, Any]:
    p = load().get(cid, {})
    year = case_year(case)
    sources = [r for r in case.dossier.records.values() if r.type != 'synthetic']
    return {
        'id': cid,
        'name': p.get('display_name') or case.company,
        'legal_name': (p.get('legal_name') or case.company),
        'tagline': p.get('tagline') or None,
        'industry': (p.get('industry') or {}).get('text'),
        'headquarters': (p.get('headquarters') or {}).get('text'),
        'case_year': year,
        'accent': accent(cid, order),
        'logo': p.get('logo'),
        'banner': p.get('banner'),
        'sources': len(sources),
        'independent_sources': sum(r.type == 'verified_observation' for r in sources),
        'investigations': investigations,
        'profiled': bool(p),
    }


def profile(cid: str, case: Any, order: list[str], investigations: list[dict[str, Any]], examples: list[str], scenarios: list[dict[str, Any]],
            others: list[dict[str, Any]]) -> dict[str, Any]:
    p = load().get(cid, {})
    year = case_year(case)
    head = summary(cid, case, order, len(investigations))
    records = {r.id: r for r in case.dossier.records.values()}

    def cite(ids: list[str]) -> list[dict[str, Any]]:
        return [{'id': i, 'title': records[i].title, 'date': records[i].date, 'origin': records[i].type, 'url': records[i].url} for i in ids if i in records]

    def fact(value: Any) -> Any:
        return {**value, 'sources': cite(value.get('sources', []))} if isinstance(value, dict) else value

    same = (p.get('industry') or {}).get('text')
    return {
        **head,
        'brief_description': re.split(r'(?<=[.!?])\s', case.brief.strip(), maxsplit=1)[0],
        'facts': {k: fact(p.get(k)) for k in CITED if p.get(k)},
        'case_context': p.get('case_context') or ({'set_in': str(year), 'note': f'Sources dated after {year} describe later events.'} if year else None),
        **{k: [fact(x) for x in p.get(k) or []] for k in LISTS},
        'library': library(case, year),
        'investigations': investigations,
        'questions': examples,
        'scenarios': scenarios,
        'related': [o for o in others if same and o.get('industry') == same and o['id'] != cid],
        'others': [o for o in others if o['id'] != cid],
    }
