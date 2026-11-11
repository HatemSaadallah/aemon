"""Build the public data release: every third-party excerpt cut to one short quote, everywhere it appears.

Hatem's policy (2026-11-08): the dossier is published as metadata plus a short quote per record, and the training rows,
evaluation transcripts and judge packets are published as redacted copies made the same way. Simulated what-if records
are written by the case authors and stay whole. The quotes the agent itself made when assessing a source stay as
made: each is a single sentence the environment checked word for word against the source. Each published file is listed in MANIFEST.json with the sha256 of the
original it was made from and of the redacted copy, so the redaction can be checked against the private originals.

Usage: python scripts/release/build_release.py --rows ROWS_DIR --out OUT_DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
WORDS = 25


def short(excerpt: str) -> str:
    """The first sentence, at most WORDS words."""
    first = re.split(r'(?<=[.!?])\s+', excerpt.strip(), maxsplit=1)[0]
    words = first.split()
    return ' '.join(words[:WORDS]) + (' …' if len(words) > WORDS or first != excerpt.strip() else '')


def load_records() -> list[dict[str, Any]]:
    data = json.loads((REPO / 'data/dossier/evidence.json').read_text())
    return data['records'] if isinstance(data, dict) else data


class Redactor:
    def __init__(self, records: list[dict[str, Any]]):
        pairs = []
        for r in records:
            if r.get('type') == 'synthetic':
                continue
            e, s = r['excerpt'], short(r['excerpt'])
            if e.strip() != s.strip():
                pairs.append((e, s))
                pairs.append((json.dumps(e)[1:-1], json.dumps(s)[1:-1]))  # the same excerpt inside a JSON-encoded state
        self.pairs = sorted(pairs, key=lambda p: -len(p[0]))  # longest first, so no excerpt is cut inside another
        self.long = [e for e, _ in pairs]

    def text(self, value: str) -> str:
        for full, cut in self.pairs:
            if full in value:
                value = value.replace(full, cut)
        return value

    def any(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, list):
            return [self.any(v) for v in value]
        if isinstance(value, dict):
            return {k: self.any(v) for k, v in value.items()}
        return value

    def leftovers(self, blob: str) -> int:
        return sum(blob.count(e) for e in self.long if len(e) > 80)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument('--rows', required=True, help='folder holding final.jsonl and final_corrections.jsonl')
    a.add_argument('--out', required=True)
    args = a.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    records = load_records()
    red = Redactor(records)
    manifest: dict[str, Any] = {'policy': __doc__.split('\n\n')[1], 'words_per_quote': WORDS, 'files': {}}

    def write(name: str, original: bytes, redacted: str) -> None:
        # Two teacher outputs in the correction rows end mid-emoji (cut at the token limit): a lone surrogate, which
        # UTF-8 cannot hold. It becomes U+FFFD in the published copy, counted here.
        redacted, lone = re.subn(r'[\ud800-\udfff]', '\ufffd', redacted)
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(redacted)
        left = red.leftovers(redacted)
        if left:
            raise SystemExit(f'{name}: {left} full excerpts left after redaction')
        manifest['files'][name] = {'original_sha256': sha(original), 'published_sha256': sha(redacted.encode())} | ({'lone_surrogates_replaced': lone} if lone else {})

    meta = [
        {k: r.get(k) for k in ('id', 'type', 'kind', 'scope', 'title', 'url', 'date', 'geography', 'population', 'access_limitation', 'bears_on')}
        | {'quote': r['excerpt'] if r.get('type') == 'synthetic' else short(r['excerpt'])}
        for r in records
    ]
    src = (REPO / 'data/dossier/evidence.json').read_bytes()
    write('dossier/records.jsonl', src, ''.join(json.dumps(m, ensure_ascii=False) + '\n' for m in meta))
    for name in ('cases.json', 'cases_heldout.json'):
        raw = (REPO / 'data/dossier' / name).read_bytes()
        write(f'dossier/{name}', raw, json.dumps(red.any(json.loads(raw)), indent=1, ensure_ascii=False))

    def jsonl(src_path: Path, name: str) -> None:
        raw = src_path.read_bytes()
        lines = [json.dumps(red.any(json.loads(line)), ensure_ascii=False) for line in raw.decode().splitlines() if line.strip()]
        write(name, raw, '\n'.join(lines) + '\n')

    def whole(src_path: Path, name: str) -> None:
        raw = src_path.read_bytes()
        write(name, raw, json.dumps(red.any(json.loads(raw)), indent=1, ensure_ascii=False))

    rows = Path(args.rows)
    jsonl(rows / 'final.jsonl', 'training/rows.jsonl')
    jsonl(rows / 'final_corrections.jsonl', 'training/correction_rows.jsonl')
    for split in ('dev', 'final'):
        d = REPO / 'reports/judge' / split
        jsonl(d / 'packets.jsonl', f'evaluation/{split}/judge_packets.jsonl')
        for f in sorted(d.glob('*predictions.jsonl')) + [d / 'key.jsonl']:
            jsonl(f, f'evaluation/{split}/{f.name}')
        for f in sorted(d.glob('dev_*.json')) + sorted(d.glob('final_test_*.json')) + sorted(d.glob('report_*.json')):
            whole(f, f'evaluation/{split}/{f.name}')
    (out / 'MANIFEST.json').write_text(json.dumps(manifest, indent=1))
    print(json.dumps({'files': len(manifest['files']), 'out': str(out)}))


if __name__ == '__main__':
    main()
