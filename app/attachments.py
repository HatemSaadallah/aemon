"""Files and links a person attaches to an investigation, turned into sources the agent can search, read and quote.

A file (PDF, Word, text, Markdown, CSV or HTML) or a web page is read once, its text split into passages of about 90
words at sentence boundaries, and saved for its owner. Each passage becomes a record of class user_document: "provided
by you, not checked by an analyst". Quotes are checked against the passage, like any other source. The agent is told
which documents are attached, so it can search for them; nothing in them is treated as independent evidence.
"""

from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import re
import subprocess
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any

from aemon.environment.dossier import Dossier, Record

Json = dict[str, Any]
MAX_BYTES = 15_000_000
MAX_PASSAGES = 120
PASSAGE_WORDS = 90
KINDS = {'.pdf', '.docx', '.txt', '.md', '.csv', '.html', '.htm', '.json'}
SCRIPT = re.compile(r'<(script|style|noscript|svg|nav|footer|header)\b.*?</\1>', re.S | re.I)
TAG = re.compile(r'<[^>]+>')
SPACE = re.compile(r'\s+')


class Unreadable(ValueError):
    pass


def folder(root: Path, user: str) -> Path:
    path = Path(root) / 'attachments' / hashlib.sha256(user.encode()).hexdigest()[:16]
    path.mkdir(parents=True, exist_ok=True)
    return path


def html_text(raw: str) -> str:
    return SPACE.sub(' ', html.unescape(TAG.sub(' ', SCRIPT.sub(' ', raw)))).strip()


def file_text(name: str, data: bytes) -> str:
    suffix = Path(name).suffix.lower()
    if suffix not in KINDS:
        raise Unreadable(f'{suffix or "this kind of file"} is not supported: attach a PDF, Word, text, Markdown, CSV or HTML file')
    if suffix == '.pdf':
        with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
            f.write(data)
            f.flush()
            try:
                out = subprocess.run(['pdftotext', '-layout', '-q', f.name, '-'], capture_output=True, timeout=60, check=True).stdout.decode('utf-8', 'replace')
            except (OSError, subprocess.SubprocessError):
                from pdfminer.high_level import extract_text  # fallback when pdftotext is missing

                out = extract_text(io.BytesIO(data))
        return SPACE.sub(' ', out).strip()
    if suffix == '.docx':
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                xml = z.read('word/document.xml').decode('utf-8', 'replace')
        except (zipfile.BadZipFile, KeyError) as error:
            raise Unreadable('this Word file could not be opened') from error
        return html_text(re.sub(r'</w:p>', '\n', xml))
    raw = data.decode('utf-8', 'replace')
    return html_text(raw) if suffix in ('.html', '.htm') else SPACE.sub(' ', raw).strip()


def passages(text: str) -> list[str]:
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    out, current = [], []
    for s in sentences:
        current.append(s)
        if sum(len(x.split()) for x in current) >= PASSAGE_WORDS:
            out.append(' '.join(current))
            current = []
    if current:
        out.append(' '.join(current))
    return [' '.join(p.split()[:PASSAGE_WORDS * 2]) for p in out if len(p.split()) >= 5][:MAX_PASSAGES]


def save(root: Path, user: str, workspace: str, name: str, text: str, url: str = '', kind: str = 'file') -> Json:
    parts = passages(text)
    if not parts:
        raise Unreadable('no readable text was found in it')
    item = {
        'id': uuid.uuid4().hex[:12], 'workspace': workspace, 'kind': kind, 'name': name[:160], 'url': url, 'added': time.time(),
        'words': len(text.split()), 'passages': parts, 'sha256': hashlib.sha256(text.encode()).hexdigest(),
    }
    (folder(root, user) / f"{item['id']}.json").write_text(json.dumps(item, ensure_ascii=False))
    return summary(item)


def add_file(root: Path, user: str, workspace: str, name: str, data_base64: str) -> Json:
    try:
        data = base64.b64decode(data_base64, validate=True)
    except ValueError as error:
        raise Unreadable('the file did not arrive intact') from error
    if len(data) > MAX_BYTES:
        raise Unreadable('the file is larger than 15 MB')
    return save(root, user, workspace, name, file_text(name, data))


def add_link(root: Path, user: str, workspace: str, url: str, fetch: Any) -> Json:  # noqa: ANN401  fetch is injectable for tests
    if not re.match(r'^https?://', url):
        raise Unreadable('a link must start with http:// or https://')
    try:
        raw = fetch(url)
    except Exception as error:  # noqa: BLE001
        raise Unreadable(f'the page could not be fetched ({type(error).__name__})') from error
    title = re.search(r'<title[^>]*>(.*?)</title>', raw, re.S | re.I)
    name = html.unescape(title.group(1)).strip() if title else url
    return save(root, user, workspace, SPACE.sub(' ', name) or url, html_text(raw), url=url, kind='link')


def summary(item: Json) -> Json:
    return {k: item[k] for k in ('id', 'workspace', 'kind', 'name', 'url', 'added', 'words')} | {'passages': len(item['passages'])}


def listing(root: Path, user: str, workspace: str) -> list[Json]:
    items = [json.loads(p.read_text()) for p in folder(root, user).glob('*.json')]
    return sorted((summary(i) for i in items if i['workspace'] == workspace), key=lambda i: -i['added'])


def load(root: Path, user: str, ids: list[str]) -> list[Json]:
    out = []
    for i in ids:
        path = folder(root, user) / f'{re.sub(r"[^0-9a-f]", "", i)}.json'
        if path.exists():
            out.append(json.loads(path.read_text()))
    return out


def remove(root: Path, user: str, identifier: str) -> bool:
    path = folder(root, user) / f'{re.sub(r"[^0-9a-f]", "", identifier)}.json'
    if path.exists():
        path.unlink()
        return True
    return False


def records(items: list[Json]) -> list[Record]:
    out = []
    for item in items:
        day = time.strftime('%Y-%m-%d', time.localtime(item['added']))
        for n, text in enumerate(item['passages']):
            out.append(Record(
                id=f"you-{item['id']}-{n + 1}", type='user_document', title=f"{item['name']} (part {n + 1} of {len(item['passages'])})",
                url=item.get('url') or '', date=f'attached {day}', excerpt=text,
                access_limitation='Provided by the person asking; not checked by an analyst.', scope='user',
            ))
    return out


def with_attachments(dossier: Dossier, items: list[Json]) -> Dossier:
    """The case's own sources plus the person's passages, searched together."""
    return Dossier(list(dossier.records.values()) + records(items)) if items else dossier


def brief_note(items: list[Json]) -> str:
    if not items:
        return ''
    names = '; '.join(f"“{i['name']}”" for i in items)
    return (f'\n\nThe person attached their own material, searchable like any source (class user_document, not checked by an '
            f'analyst): {names}. Search for it and weigh it like any other source; it is not independent evidence.')
