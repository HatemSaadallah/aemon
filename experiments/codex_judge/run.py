"""Codex as the second judge, 2026-11-11 (DECISIONS). Same frozen instrument and receipt as the final test
(reports/judge/codex_score_qualification_bound.json; the codex settings and pinned 0.166.0 binary are unchanged).

Three packet sets, in this order:
  1. test2     - the frozen second test, base and version 1 (the pending second judge for its headline)
  2. test2_v3  - exploratory: base, version 1 and version 3 together, blind
  3. final_v3  - exploratory: the same on the final test

Infrastructure failures only are retried, as in the final test: a packet whose Codex call failed on the usage limit or
timed out is archived (kept) and judged again after a wait (an hour on the usage limit), at most 30 rounds. A judge-invalid output stays missing.
Results stay outside the repository while judging; the key never enters the sandbox.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PY = str(REPO / '.venv/bin/python')
RESULTS = Path.home() / 'lexsi-backup/judge_results'
JUDGE = os.environ.get('JUDGE', 'codex')  # codexsol: gpt-6-sol, a separate judge (DECISIONS 2026-11-11); never mixed with codex scores
RECEIPT = {'codex': 'reports/judge/codex_score_qualification_bound.json', 'codexsol': 'reports/judge/codexsol_score_qualification.json'}[JUDGE]
SETS = [
    ('test2', 'reports/judge/test2', RESULTS / f'test2/{JUDGE}_test2', [('trained', 'base')]),
    ('test2_v3', 'reports/judge/test2_v3', RESULTS / f'test2_v3/{JUDGE}_test2_v3', [('v3', 'v1'), ('v1', 'base'), ('v3', 'base')]),
    ('final_v3', 'reports/judge/final_v3', RESULTS / f'final_v3/{JUDGE}_final_v3', [('v3', 'v1'), ('v1', 'base'), ('v3', 'base')]),
    # the combined system (DECISIONS 2026-11-11): base, v1, v3, combined and dig judged together blind
    ('system_test2', 'reports/judge/system_test2', RESULTS / f'system_test2/{JUDGE}_system_test2', [('combined', 'v1'), ('combined', 'v3'), ('combined', 'dig'), ('dig', 'v1'), ('combined', 'base')]),
    ('system_final', 'reports/judge/system_final', RESULTS / f'system_final/{JUDGE}_system_final', [('combined', 'v1'), ('combined', 'v3'), ('combined', 'dig'), ('dig', 'v1'), ('combined', 'base')]),
]
CLAUDE = {'test2': ('claude', 'reports/judge/test2/claude_test2/predictions.jsonl'),
          'test2_v3': ('claudecode', 'reports/judge/test2_v3/claudecode_predictions.jsonl'),
          'final_v3': ('claudecode', 'reports/judge/final_v3/claudecode_predictions.jsonl'),
          'system_test2': ('claudecode', 'reports/judge/system_test2/claudecode_predictions.jsonl'),
          'system_final': ('claudecode', 'reports/judge/system_final/claudecode_predictions.jsonl')}


def log(**k) -> None:
    print(json.dumps({'t': time.strftime('%H:%M:%S'), **k}), flush=True)


def infra(dest: Path) -> str | None:
    """Why a failed attempt was infrastructure, or None if it is the judge's own output (kept missing)."""
    r = json.loads((dest / 'result.json').read_text())
    if 'judgment' in r:
        return None
    text = ''.join((dest / f).read_text(errors='ignore') for f in ('stderr.txt', 'events.jsonl') if (dest / f).exists())
    err = str(r.get('error', ''))
    if 'usage limit' in text.lower():
        return 'usage_limit'
    if 'TimeoutExpired' in err or 'timed out' in err.lower():
        return 'timeout'
    if 'isolated Codex invocation failed' in err and not (dest / 'events.jsonl').exists():
        return 'no_model_turn'
    return None


def campaign(name: str, folder: str, res: Path) -> None:
    start = 1 + sum(1 for p in res.parent.glob(f'{res.name}_archived_infra_r*'))
    for rnd in range(start, start + 30):
        log(set=name, round=rnd, start=True)
        out = subprocess.run([PY, 'src/aemon/evaluation/judging/judge_v1/run_campaign.py', '--backend', JUDGE, '--packets', f'{folder}/packets.jsonl',
                              '--output', str(res), '--qualification', RECEIPT, '--workers', '4'], cwd=REPO, capture_output=True, text=True)
        (REPO / folder / f'{JUDGE}_run_round{rnd}.log').write_text(out.stdout + out.stderr)
        # partial attempt folders (no result.json) come only from an interrupted call; archive them with the failures
        failed = {}
        for d in sorted(p for p in res.iterdir() if p.is_dir()):
            if not (d / 'result.json').exists():
                failed[d] = 'partial'
            else:
                why = infra(d)
                if why:
                    failed[d] = why
        valid = sum(1 for d in res.iterdir() if d.is_dir() and d not in failed and 'judgment' in json.loads((d / 'result.json').read_text()))
        log(set=name, round=rnd, returncode=out.returncode, valid=valid, infra_failures=len(failed),
            causes={c: list(failed.values()).count(c) for c in set(failed.values())})
        if not failed:
            return
        archive = res.parent / f'{res.name}_archived_infra_r{rnd}'
        archive.mkdir(exist_ok=True)
        for d in failed:
            shutil.move(str(d), str(archive / d.name))
        # the round's aggregate lists the failed attempts too; run_packets will not overwrite it, so it is kept here
        if (res / 'predictions.jsonl').exists():
            shutil.move(str(res / 'predictions.jsonl'), str(archive / 'predictions_with_failures.jsonl'))
        (archive / 'causes.json').write_text(json.dumps({d.name: c for d, c in failed.items()}, indent=1))
        if 'usage_limit' in failed.values():
            log(set=name, waiting_minutes=60)
            time.sleep(3600)
    log(set=name, gave_up_after_rounds=30)
    raise SystemExit(f'{name}: still failing after 30 rounds')


def report(name: str, folder: str, res: Path, compares: list[tuple[str, str]]) -> None:
    shutil.copy(res / 'predictions.jsonl', REPO / folder / f'{JUDGE}_predictions.jsonl')
    other, path = CLAUDE[name]
    while not (REPO / path).exists():  # the other judge may still be running on this set
        time.sleep(120)
    key = REPO / folder / 'key.jsonl'  # copied into the repository only once every judge has finished
    if not key.exists():
        key = Path.home() / f'lexsi-backup/judge_keys/{name}_key.jsonl'
    for a, b in compares:
        for tag, judges in ((JUDGE, [f'{JUDGE}={res}/predictions.jsonl']),
                            ('both' if JUDGE == 'codex' else f'{other}_{JUDGE}', [f'{other}={path}', f'{JUDGE}={res}/predictions.jsonl'])):
            cmd = [PY, '-W', 'ignore', '-m', 'aemon.evaluation.judging.report', '--key', str(key), '--compare', f'{a},{b}',
                   '--output', f'{folder}/report_{tag}_{a}_vs_{b}.json']
            for j in judges:
                cmd += ['--judge', j]
            subprocess.run(cmd, cwd=REPO, check=True, capture_output=True)
        log(set=name, reported=f'{a} vs {b}')


def main() -> None:
    only = set(sys.argv[1:])
    for name, folder, res, compares in SETS:
        if only and name not in only:
            continue
        res.parent.mkdir(parents=True, exist_ok=True)
        campaign(name, folder, res)
        report(name, folder, res, compares)
    log(done=True)


if __name__ == '__main__':
    main()
