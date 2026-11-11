"""Build the public data release: the dossier, cases, training rows, teacher investigations and evaluation files as they are.

Hatem's policy (2026-11-11: "keep them as they are and publish them ... publish everything related to the data"): the
dossier is published byte for byte, and the training rows, evaluation transcripts, judge packets, judge outputs and
answer keys are published with their excerpts whole. The earlier cut of every third-party excerpt to one short quote
(policy of 2026-11-08) is removed. Two things still differ from the private originals: personal and cluster
identifiers are replaced by placeholders, and a lone surrogate (a teacher output cut mid-emoji) becomes U+FFFD. Each
published file is listed in MANIFEST.json with the file it was made from, the sha256 of that original and of the
published copy, and the count of each replacement, so the release can be checked against the originals.

Usage: python scripts/release/build_release.py --rows ROWS_DIR --out OUT_DIR [--corrections FILE]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
# Personal and internal identifiers, replaced by the same placeholders as scripts/release/build_public_repo.py
SCRUB = {'CLUSTER_ACCOUNT': 'CLUSTER_ACCOUNT', 'CLUSTER_HOST': 'CLUSTER_HOST', '/home/USER': '/home/USER', '/home/USER': '/home/USER'}
SURROGATE = re.compile(r'[\ud800-\udfff]')
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}')
SECRET = re.compile(
    r'hf_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}'
    r'|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer [A-Za-z0-9._-]{20,}'
)

# Judging campaigns under reports/judge. 'finished' campaigns publish their packets, runs, reports, judge outputs and,
# where the repository holds it, the answer key. An unfinished campaign publishes packets and run reports only.
CAMPAIGNS: dict[str, dict[str, Any]] = {
    'dev': {'finished': True},
    'final': {'finished': True},
    'final_v3': {'finished': True},
    'test2': {'finished': True, 'extra': {'claude_test2/predictions.jsonl': 'claude_predictions.jsonl'}},
    'test2_v3': {'finished': True},
    'screen3': {'finished': True},
    'switch': {'finished': True},
    'system_test2': {'finished': True},
    'system_final': {'finished': False},  # judging in progress on 2026-11-11: no predictions, no key
}
HOSTED = 'experiments/hosted_investigations'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fix_surrogates(text: str, lines: bool) -> tuple[str, int]:
    """Lone surrogates (JSON escapes of half an emoji) become U+FFFD; nothing else in the text is touched."""
    if '\\ud' not in text and '\\uD' not in text:
        return text, 0
    count = 0

    def one(chunk: str, indent: int | None) -> str:
        nonlocal count
        fixed, n = SURROGATE.subn('�', json.dumps(json.loads(chunk), ensure_ascii=False, indent=indent))
        count += n
        return fixed if n else chunk

    if lines:
        return ''.join(one(line, None) + '\n' if line.strip() else line for line in text.splitlines()), count
    return one(text, 1), count


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument('--rows', required=True, help='folder holding final.jsonl and the v3_deepseek_* rows')
    a.add_argument('--corrections', help='final_corrections.jsonl, when it is not in the rows folder')
    a.add_argument('--out', required=True)
    args = a.parse_args()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    manifest: dict[str, Any] = {'policy': (__doc__ or '').split('\n\n')[1], 'placeholders': sorted(set(SCRUB.values())), 'files': {}}

    def publish(src: Path, name: str, source: str | None = None, exact: bool = False) -> None:
        raw = src.read_bytes()
        text = raw.decode()
        replaced = {old: text.count(old) for old in SCRUB if old in text}
        for old, placeholder in SCRUB.items():
            text = text.replace(old, placeholder)
        text, lone = fix_surrogates(text, lines=name.endswith('.jsonl'))
        data = text.encode()
        if exact and data != raw:
            raise SystemExit(f'{name}: must be published byte for byte, and a replacement would change it')
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        entry: dict[str, Any] = {'source': source or str(src.relative_to(REPO)), 'original_sha256': sha(raw), 'published_sha256': sha(data)}
        if replaced:
            entry['identifiers_replaced'] = sum(replaced.values())
        if lone:
            entry['lone_surrogates_replaced'] = lone
        manifest['files'][name] = entry

    # The dossier, the cases of every split, and the two frozen test definitions
    dossier = REPO / 'data/dossier'
    publish(dossier / 'evidence.json', 'dossier/evidence.json', exact=True)
    for name in ('cases.json', 'cases_heldout.json', 'cases_heldout2.json', 'evidence_kinds_v2.json'):
        publish(dossier / name, f'dossier/{name}')
    for name in ('final_test_freeze.json', 'test2_freeze.json'):
        publish(REPO / 'docs' / name, f'dossier/{name}')

    # Training rows: version 1 (Command A+), its correction rows, and the DeepSeek V4-Pro rows added for version 3
    rows = Path(args.rows)
    corrections = Path(args.corrections) if args.corrections else rows / 'final_corrections.jsonl'
    publish(rows / 'final.jsonl', 'training/rows.jsonl', 'rows/final.jsonl')
    publish(corrections, 'training/correction_rows.jsonl', 'rows/final_corrections.jsonl')
    publish(rows / 'v3_deepseek_train.jsonl', 'training/v3_deepseek_rows.jsonl', 'rows/v3_deepseek_train.jsonl')
    publish(rows / 'v3_deepseek_val.jsonl', 'training/v3_deepseek_validation_rows.jsonl', 'rows/v3_deepseek_val.jsonl')
    publish(REPO / HOSTED / 'v3_rows_report.json', 'training/v3_rows_report.json')

    # The DeepSeek V4-Pro teacher investigations the version 3 rows were built from
    hosted = REPO / HOSTED
    for f in sorted(hosted.glob('*.episodes.jsonl')) + sorted(hosted.glob('provenance_*.jsonl')) + sorted(hosted.glob('requests_*.jsonl')):
        publish(f, f'teacher_investigations/deepseek_v4_pro/{f.name}')
    for f in sorted(hosted.glob('pilot.json')) + sorted(hosted.glob('part?.json')) + sorted(hosted.glob('new?.json')):
        publish(f, f'teacher_investigations/deepseek_v4_pro/{f.name}')

    # Judging campaigns
    judge = REPO / 'reports/judge'
    for f in sorted(judge.glob('*_qualification*.json')):
        publish(f, f'evaluation/judge_qualification/{f.name}')
    for split, spec in CAMPAIGNS.items():
        d = judge / split
        publish(d / 'packets.jsonl', f'evaluation/{split}/judge_packets.jsonl')
        runs = [f for f in sorted(d.glob('*.json')) if not f.name.startswith('report_')]
        for f in runs:  # run reports: the transcripts of each arm
            publish(f, f'evaluation/{split}/{f.name}')
        if not spec['finished']:
            continue
        for f in sorted(d.glob('report_*.json')) + sorted(d.glob('*predictions.jsonl')):
            publish(f, f'evaluation/{split}/{f.name}')
        for rel, name in spec.get('extra', {}).items():
            publish(d / rel, f'evaluation/{split}/{name}')
        if (d / 'key.jsonl').exists():
            publish(d / 'key.jsonl', f'evaluation/{split}/key.jsonl')

    # Status-check runs (the company status check, with and without each adapter)
    for f in sorted((REPO / 'reports/status_check').glob('*.json')):
        publish(f, f'evaluation/status_check/{f.name}')

    (out / 'MANIFEST.json').write_text(json.dumps(manifest, indent=1) + '\n')
    shutil.copyfile(REPO / 'docs/DATASET_CARD.md', out / 'README.md')

    # Checks on what was written: the dossier byte for byte, no identifier, no secret, and every email address listed
    files = [p for p in out.rglob('*') if p.is_file()]
    left = secrets = 0
    emails: dict[str, int] = {}
    for p in files:
        text = p.read_text()
        left += sum(text.count(k) for k in SCRUB)
        secrets += len(SECRET.findall(text))
        for m in EMAIL.findall(text):
            emails[m] = emails.get(m, 0) + 1
    unfinished = [n for n in manifest['files'] if any(n.startswith(f'evaluation/{s}/') and ('predictions' in n or n.endswith('key.jsonl')) for s, c in CAMPAIGNS.items() if not c['finished'])]
    same = (out / 'dossier/evidence.json').read_bytes() == (dossier / 'evidence.json').read_bytes()
    print(json.dumps({
        'files': len(manifest['files']), 'bytes': sum(p.stat().st_size for p in files), 'out': str(out), 'excerpts': 'as they are',
        'dossier_identical': same, 'identifiers_left': left, 'secrets': secrets, 'emails': emails, 'unfinished_campaign_outputs': unfinished,
    }, ensure_ascii=False))
    if not same or left or secrets or emails or unfinished:
        raise SystemExit('release check failed: do not upload this build')


if __name__ == '__main__':
    main()
