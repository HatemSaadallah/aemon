"""Build the public GitHub snapshot of this repository: no history, no third-party papers, and personal or internal
identifiers replaced by placeholders. The dossier is published as it is (Hatem, 2026-11-11: "keep them as they are and
publish them"), so public runs read the same excerpts as the evaluated ones. The earlier cut to one short quote per
excerpt is removed from this build.

Usage: python scripts/release/build_public_repo.py --out DIR
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parents[2]
DROP = ('papers/', 'sources/', 'docs/PUBLIC_README.md', 'SUMMARY.md', 'TODO.md')  # internal working notes stay private too  # the source papers and their extracted text are the publishers', not ours
# Personal and internal identifiers, replaced by placeholders in the public copy (named in the README)
SCRUB = {'CLUSTER_ACCOUNT': 'CLUSTER_ACCOUNT', 'CLUSTER_HOST': 'CLUSTER_HOST', '/home/USER': '/home/USER', '/home/USER': '/home/USER'}
TEXT = {'.sha256', '.jinja', '.py', '.md', '.json', '.jsonl', '.txt', '.ts', '.tsx', '.js', '.css', '.html', '.sh', '.sbatch', '.toml', '.cfg', '.yml', '.yaml', '.csv', '.log', '.out', '.err', '.tex', '.bib', '.R'}


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument('--out', required=True)
    args = a.parse_args()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    files = subprocess.run(['git', 'ls-files'], cwd=REPO, capture_output=True, text=True, check=True).stdout.splitlines()
    changed = dropped = 0
    for f in files:
        if f.startswith(DROP):
            dropped += 1
            continue
        src, dst = REPO / f, out / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in TEXT:
            text = src.read_text(errors='surrogateescape')
            new = text
            for old, placeholder in SCRUB.items():
                new = new.replace(old, placeholder)
            changed += new != text
            dst.write_text(new, errors='surrogateescape')
        else:
            shutil.copy2(src, dst)
    # The public README is its own document: results and how to run them, without the internal working notes
    (out / 'README.md').write_text((REPO / 'docs/PUBLIC_README.md').read_text())
    text_files = [p for p in out.rglob('*') if p.is_file()]  # every file, so a type missing from TEXT is caught
    unscrubbed = sum(p.read_text(errors='ignore').count(k) for p in text_files for k in SCRUB)
    print(json.dumps({'files': len(files) - dropped, 'dropped': dropped, 'redacted_files': changed, 'excerpts': 'as they are', 'identifiers_left': unscrubbed}))


if __name__ == '__main__':
    main()
