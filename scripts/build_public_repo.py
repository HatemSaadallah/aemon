"""Build the public GitHub snapshot of this repository: no history, no third-party papers, and every dossier excerpt cut
to one short quote wherever it appears (the release policy in scripts/build_release.py).

Usage: python scripts/build_public_repo.py --out DIR
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_release import Redactor, load_records, short  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DROP = ('papers/', 'sources/')  # the source papers and their extracted text are the publishers', not ours
# Personal and internal identifiers, replaced by placeholders in the public copy (named in the README)
SCRUB = {'CLUSTER_ACCOUNT': 'CLUSTER_ACCOUNT', 'CLUSTER_HOST': 'CLUSTER_HOST', '/home/USER': '/home/USER'}
TEXT = {'.sha256', '.jinja', '.py', '.md', '.json', '.jsonl', '.txt', '.ts', '.tsx', '.js', '.css', '.html', '.sh', '.sbatch', '.toml', '.cfg', '.yml', '.yaml', '.csv', '.log'}


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument('--out', required=True)
    args = a.parse_args()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    files = subprocess.run(['git', 'ls-files'], cwd=REPO, capture_output=True, text=True, check=True).stdout.splitlines()
    red = Redactor(load_records())
    changed = dropped = 0
    for f in files:
        if f.startswith(DROP):
            dropped += 1
            continue
        src, dst = REPO / f, out / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in TEXT:
            text = src.read_text(errors='surrogateescape')
            new = red.text(text)
            for old, placeholder in SCRUB.items():
                new = new.replace(old, placeholder)
            changed += new != text
            dst.write_text(new, errors='surrogateescape')
        else:
            shutil.copy2(src, dst)
    evidence = out / 'data/dossier/evidence.json'
    data = json.loads((REPO / 'data/dossier/evidence.json').read_text())
    records = data['records'] if isinstance(data, dict) else data
    for r in records:
        if r.get('type') != 'synthetic':
            r['excerpt'] = short(r['excerpt'])
    data['redacted'] = (
        'Public copy: each excerpt is cut to its first sentence, at most 25 words (scripts/build_release.py). The full '
        'excerpts, which the frozen digest in docs/final_test_freeze.json covers, are kept in the private repository.'
    )
    evidence.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    text_files = [p for p in out.rglob('*') if p.is_file() and p.suffix in TEXT]
    unscrubbed = sum(p.read_text(errors='ignore').count(k) for p in text_files for k in SCRUB)
    left = sum(red.leftovers(p.read_text(errors='ignore')) for p in out.rglob('*') if p.is_file() and p.suffix in TEXT)
    print(json.dumps({'files': len(files) - dropped, 'dropped': dropped, 'redacted_files': changed, 'full_excerpts_left': left, 'identifiers_left': unscrubbed}))


if __name__ == '__main__':
    main()
