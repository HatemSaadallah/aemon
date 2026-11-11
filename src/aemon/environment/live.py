"""Live research for Try it: a dossier that searches the web instead of the fixed records. Not part of any evaluation.

Every result page is fetched once and saved as a snapshot (URL, retrieval time, sha256 of the page text, the excerpt the
agent sees), so its quotes are checked against fixed text and the run can be replayed from the snapshots. A page on the
company's own site is a company claim; any other page is a web page no analyst has checked, which its access note says.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from aemon.environment.dossier import Dossier, Record, words

AGENT = 'Mozilla/5.0 (X11; Linux x86_64) StrategyLab-research-prototype'
EXCERPT_WORDS = 80
SCRIPT = re.compile(r'<(script|style|noscript|svg|nav|footer|header)\b.*?</\1>', re.S | re.I)
TAG = re.compile(r'<[^>]+>')
SPACE = re.compile(r'\s+')


def page_text(raw: str) -> str:
    return SPACE.sub(' ', html.unescape(TAG.sub(' ', SCRIPT.sub(' ', raw)))).strip()


def best_excerpt(text: str, query: str, fallback: str) -> str:
    """The window of about EXCERPT_WORDS words that shares most words with the query, cut at sentence boundaries."""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.split()) >= 4]
    wanted = set(words(query))
    best, score = '', -1
    for i in range(len(sentences)):
        window, n = [], 0
        for s in sentences[i:]:
            if n + len(s.split()) > EXCERPT_WORDS and window:
                break
            window.append(s)
            n += len(s.split())
        hit = len(wanted & set(words(' '.join(window))))
        if hit > score:
            best, score = ' '.join(window), hit
    best = ' '.join(best.split()[:EXCERPT_WORDS]).strip()
    return best if score > 0 and best else ' '.join(fallback.split()[:EXCERPT_WORDS]) or 'No readable text on this page.'


class LiveDossier(Dossier):
    def __init__(self, company: str, folder: Path, search=None, fetch=None, extra: Dossier | None = None) -> None:  # noqa: ANN001  injectable for tests
        super().__init__(list(extra.records.values()) if extra else [])
        self.extra = extra  # the person's own attached documents, searched alongside the web
        self.company = company
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self._search_web = search or self._ddgs
        self._fetch = fetch or self._http
        brand = [w for w in re.findall(r'[a-z0-9]+', company.lower()) if len(w) > 2 and w not in {'group', 'inc', 'company', 'corporation', 'ltd', 'the'}]
        self._brand = brand[:2]

    @staticmethod
    def _ddgs(query: str, k: int) -> list[dict[str, str]]:
        """Web results without ads; a query that finds nothing is retried once, shortened to its first six words."""
        from ddgs import DDGS

        ads = ('bing.com/aclick', 'duckduckgo.com/y.js', '/aclk?', 'doubleclick')
        for attempt in (query, ' '.join(query.split()[:6])):
            try:
                found = DDGS().text(attempt, max_results=k + 3)
            except Exception:  # noqa: BLE001  the engine sometimes says there are no results; try once more
                found = []
            hits = [{'title': r.get('title', ''), 'url': r.get('href', ''), 'snippet': r.get('body', '')} for r in found if not any(a in r.get('href', '') for a in ads)]
            if hits:
                return hits[:k]
            time.sleep(1)
        return []

    @staticmethod
    def _http(url: str) -> str:
        request = urllib.request.Request(url, headers={'User-Agent': AGENT})
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.read(2_000_000).decode(response.headers.get_content_charset() or 'utf-8', errors='replace')

    def _is_company_site(self, url: str) -> bool:
        host = urllib.parse.urlparse(url).netloc.lower()
        return any(b in host for b in self._brand)

    def search(self, query: str, k: int = 3) -> list[Record]:
        try:
            hits = self._search_web(query, k)
        except Exception as error:  # noqa: BLE001  a failed search finds nothing, and the reason is saved
            (self.folder / 'search_errors.jsonl').open('a').write(json.dumps({'query': query, 'error': str(error)[:300]}) + '\n')
            return []
        found = list(self.extra.search(query, 2)) if self.extra else []
        for hit in hits[:k]:
            url = hit.get('url') or ''
            if not url.startswith('http'):
                continue
            identifier = 'web-' + hashlib.sha1(url.encode()).hexdigest()[:10]
            if identifier not in self.records:
                try:
                    text = page_text(self._fetch(url))
                except Exception:  # noqa: BLE001  an unreachable page keeps the search engine's snippet
                    text = hit.get('snippet', '')
                excerpt = best_excerpt(text, query, hit.get('snippet', ''))
                company = self._is_company_site(url)
                retrieved = time.strftime('%Y-%m-%d')
                record = Record(
                    id=identifier,
                    type='company_claim' if company else 'web_page',
                    title=(hit.get('title') or url)[:200],
                    url=url,
                    date=f'retrieved {retrieved}',
                    excerpt=excerpt,
                    access_limitation=(
                        "Live web page on the company's own site, retrieved for this run."
                        if company
                        else 'Live web page retrieved for this run; no analyst has checked it, and its date is unknown.'
                    ),
                    scope='live',
                )
                self.records[identifier] = record
                snapshot = {
                    'id': identifier,
                    'url': url,
                    'retrieved_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'query': query,
                    'class': record.type,
                    'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                    'excerpt': excerpt,
                    'text': text[:200_000],
                }
                (self.folder / f'{identifier}.json').write_text(json.dumps(snapshot, ensure_ascii=False))
            found.append(self.records[identifier])
        return found
