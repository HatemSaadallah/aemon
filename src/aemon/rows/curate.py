"""CuratorKIT over the training rows: it decides which rows to keep, and never rewrites one.

A row is the state the student sees and the one tool call it must produce. Its target holds exact quotes that the
environment checks character by character, so CuratorKIT's cleaning transforms stay off and kept rows are written
back byte for byte. What CuratorKIT does here:
- exact deduplication on (state, target call). Its instruction_following key is instruction + output, so the state
  goes in `instruction`; deduplicating on the target alone would merge the same call made in different states;
- its secrets gate (credentials or keys in a row are refused). Its hex-entropy detector is off (limit above the 4 bits
  a hex character can carry): on aemon's states it fired only on record and episode hashes, 7 false positives in the
  4,302 v1 rows; the keyword, private-key and base64 detectors stay on;
- the run record: manifest.json, lexsi_provenance.json, checksums.txt and a dataset card.
Near-duplicate (MinHash) matching stays off: consecutive turns of one investigation share most of their state and
would be merged although each teaches a different call.

    python -m aemon.rows.curate --rows rows.jsonl --output rows.curated.jsonl --record curation/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from aemon.common.types import Json


def key(row: Json) -> tuple[str, str]:
    """What makes two rows the same lesson: everything the student sees before the target (the system prompt is the
    same in every row, so it is left out) and the target call itself."""
    t = row['target_index']
    return json.dumps(row['messages'][1:t], ensure_ascii=False, sort_keys=True), row['messages'][t]['content']


def curate(rows: list[Json], record: Path, name: str = 'aemon_rows') -> tuple[list[Json], Json]:
    from curatorkit import Curator, CuratorConfig  # optional dependency, needed only here

    record.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        source = Path(work) / 'rows_for_curatorkit.jsonl'
        with source.open('w') as out:
            for row in rows:
                state, target = key(row)
                out.write(json.dumps({'instruction': state, 'input': '', 'output': target}, ensure_ascii=False) + '\n')
        config = CuratorConfig(dataset=str(source), dedup='exact', clean=False, schema_gate=False, secrets_gate=True, secrets_hex_limit=4.1,
                               min_tokens=1, max_tokens=1_000_000, output_dir=str(record), export_formats=['alpaca'], name=name)
        result = Curator(config).run()
    kept_keys = {(json.loads(line)['instruction'], json.loads(line)['output']) for line in (record / 'sft_alpaca.jsonl').read_text().splitlines() if line.strip()}
    kept, dropped, seen = [], [], {}
    for i, row in enumerate(rows):
        k = key(row)
        if k in seen:
            dropped.append({'row': i, 'case': row.get('case'), 'episode': row.get('episode'), 'turn': row.get('turn'), 'stage': row.get('stage'),
                            'reason': 'exact duplicate (same state and target)', 'duplicate_of': seen[k]})
        elif k not in kept_keys:
            dropped.append({'row': i, 'case': row.get('case'), 'episode': row.get('episode'), 'turn': row.get('turn'), 'stage': row.get('stage'),
                            'reason': 'refused by a CuratorKIT gate (see rejected.jsonl)'})
        else:
            seen[k] = i
            kept.append(row)
    (record / 'sft_alpaca.jsonl').unlink()  # CuratorKIT's own export is not the training file; the kept rows are
    summary = {'rows_in': len(rows), 'rows_kept': len(kept), 'dropped': len(dropped),
               'dropped_by_reason': {r: sum(d['reason'] == r for d in dropped) for r in sorted({d['reason'] for d in dropped})},
               'dropped_by_stage': {s: sum(d['stage'] == s for d in dropped) for s in sorted({str(d['stage']) for d in dropped})},
               'curatorkit': {k: len(v) if isinstance(v, (list, tuple)) else v for k in ('passed', 'rejected') if (v := getattr(result, k, None)) is not None and not callable(v)}}
    (record / 'aemon_decisions.json').write_text(json.dumps({'summary': summary, 'dropped': dropped}, indent=1))
    return kept, summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--rows', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--record', required=True, help='folder for CuratorKIT run record and the drop decisions')
    a = p.parse_args()
    raw = Path(a.rows).read_text().splitlines()
    rows = [json.loads(line) for line in raw if line.strip()]
    kept, summary = curate(rows, Path(a.record), Path(a.rows).stem)
    # kept rows are the original lines, unchanged
    by_identity = {id(r): line for r, line in zip(rows, [x for x in raw if x.strip()])}
    Path(a.output).write_text(''.join(by_identity[id(r)] + '\n' for r in kept))
    summary['input_sha256'] = hashlib.sha256(Path(a.rows).read_bytes()).hexdigest()
    summary['output_sha256'] = hashlib.sha256(Path(a.output).read_bytes()).hexdigest()
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
