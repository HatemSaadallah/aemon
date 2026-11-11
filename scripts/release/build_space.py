"""Assemble the folder a Hugging Face Docker Space is built from (deploy/space/README.md): the app, the agent package,
the dossier, both adapters, and a seed of finished investigations so a visitor has reports to open.

Usage: python scripts/release/build_space.py --out DIR [--seed-db PATH] [--per-company N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KEEP = ('app/', 'src/aemon/', 'data/dossier/')
DROP = ('app/test_', 'app/run.sh', 'app/run_model.sh', 'data/dossier/raw/')
# Personal and internal identifiers never go into a public copy (the same list as build_public_repo.py)
SCRUB = {'CLUSTER_ACCOUNT': 'CLUSTER_ACCOUNT', 'CLUSTER_HOST': 'CLUSTER_HOST', '/home/USER': '/home/USER', '/home/USER': '/home/USER'}
TEXT = {'.py', '.md', '.json', '.jsonl', '.txt', '.ts', '.tsx', '.js', '.css', '.html', '.sh', '.toml', '.jinja'}
ADAPTERS = {  # the gated conversions the evaluations ran (jobs/eval_switch.sbatch)
    'final_adapter.gguf': '41794b5756b9e0f87c58dd14e451756d15c897d595886dee9921181298fdb9d1',
    'v3_adapter.gguf': 'ea9193807fe9d5132878021bdf73de40ee84e2486f6688db9b3c3e29e04e1443',
}


def scrub(text: str) -> str:
    for old, placeholder in SCRUB.items():
        text = text.replace(old, placeholder)
    return text


def seed(db_path: Path, per_company: int) -> list[dict]:
    """The newest finished investigations with a real (not draft) recommendation, per company, without the raw turns."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    out, count = [], {}
    for r in db.execute("SELECT * FROM history WHERE status = 'finished' AND record IS NOT NULL ORDER BY COALESCE(started, 0) DESC"):
        record = json.loads(r['record'])
        final = record.get('final') or {}
        if not final.get('recommendation') or final.get('draft') or count.get(r['workspace'], 0) >= per_company:
            continue
        count[r['workspace']] = count.get(r['workspace'], 0) + 1
        out.append({'id': r['id'], 'workspace': r['workspace'], 'question': r['question'], 'case': r['case_id'], 'model': r['model'], 'status': 'finished',
                    'started': r['started'], 'ended': r['ended'], 'summary': json.loads(r['summary']) if r['summary'] else None, 'record': record,
                    'run_settings': json.loads(r['run_settings']) if r['run_settings'] else None})
    return out


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument('--out', required=True)
    a.add_argument('--seed-db', default=str(Path.home() / '.local/share/lexsi/strategy_lab.db'))
    a.add_argument('--per-company', type=int, default=3)
    a.add_argument('--adapters', default=str(Path.home() / '.cache/lexsi/adapters'))
    args = a.parse_args()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    files = [f for f in subprocess.run(['git', 'ls-files'], cwd=REPO, capture_output=True, text=True, check=True).stdout.splitlines()
             if f.startswith(KEEP) and not f.startswith(DROP)]
    for f in files:
        src, dst = REPO / f, out / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in TEXT:
            dst.write_text(scrub(src.read_text(errors='surrogateescape')), errors='surrogateescape')
        else:
            shutil.copy2(src, dst)
    for name in ('Dockerfile', 'start.sh', 'README.md'):
        shutil.copy2(REPO / 'deploy/space' / name, out / name)
    (out / 'adapters').mkdir()
    for name, digest in ADAPTERS.items():
        source = Path(args.adapters) / name
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise SystemExit(f'{name} is not the gated adapter')
        shutil.copy2(source, out / 'adapters' / name)
    (out / '.gitattributes').write_text('*.gguf filter=lfs diff=lfs merge=lfs -text\n')
    (out / '.dockerignore').write_text('app/web/node_modules\napp/web/dist\n.git\n')
    entries = seed(Path(args.seed_db), args.per_company) if Path(args.seed_db).is_file() else []
    (out / 'seed').mkdir()
    (out / 'seed/history.json').write_text(scrub(json.dumps(entries, ensure_ascii=False)))
    revision = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO, capture_output=True, text=True).stdout.strip()
    (out / 'REVISION').write_text(revision + '\n')
    left = sum(p.read_text(errors='ignore').count(k) for p in out.rglob('*') if p.is_file() and p.suffix in TEXT | {''} and p.stat().st_size < 5_000_000 for k in SCRUB)
    print(json.dumps({'files': len(files), 'seeded': {w: sum(e['workspace'] == w for e in entries) for w in sorted({e['workspace'] for e in entries})},
                      'identifiers_left': left, 'revision': revision, 'megabytes': round(sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) / 1e6, 1)}))


if __name__ == '__main__':
    main()
