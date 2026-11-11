"""Checks each evidence record against its live source. A record enters the dossier only if its
excerpt is really on the page.

Usage: python -m strategy.verify_sources INPUT.json OUTPUT.json
"""

from __future__ import annotations

import concurrent.futures as cf
import html
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

from aemon.common.types import Json
from aemon.environment.dossier import normalise

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
    'Accept': 'text/html,application/pdf;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en',
}


def page_text(url: str) -> str:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read(25_000_000)
        kind = response.headers.get('Content-Type', '')
    if 'pdf' in kind or url.lower().endswith('.pdf'):
        result = subprocess.run(['pdftotext', '-layout', '-', '-'], input=body, capture_output=True, check=False)
        return result.stdout.decode('utf-8', 'ignore')
    text = body.decode('utf-8', 'ignore')
    text = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', text)
    text = re.sub(r'(?s)<[^>]+>', ' ', text)
    return html.unescape(text)


def squash(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', normalise(text)).strip()


def check(record: Json, cache: dict[str, str]) -> tuple[str, str, str]:
    url = record['url']
    try:
        if url not in cache:
            cache[url] = page_text(url)
        text = cache[url]
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return record['id'], 'fetch_failed', str(error)[:100]
    if normalise(record['excerpt']) in normalise(text):
        return record['id'], 'verified', 'exact'
    if squash(record['excerpt']) in squash(text):
        return record['id'], 'verified', 'exact apart from punctuation'
    return record['id'], 'not_found', f'page has {len(text)} characters'


def main() -> None:
    data = json.load(open(sys.argv[1]))
    records = data.get('records') or [dict(r, company=c['name']) for c in data['companies'] for r in c['records']]
    cache = {}
    with cf.ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda r: check(r, cache), records))
    summary = {}
    for _, status, _detail in results:
        summary[status] = summary.get(status, 0) + 1
    json.dump({'summary': summary, 'results': [{'id': i, 'status': s, 'detail': d} for i, s, d in results]}, open(sys.argv[2], 'w'), indent=1)
    print(summary)


if __name__ == '__main__':
    main()
