"""Mirrors a cluster training log into a local JSON file for the Strategy Lab's live view.

Reads through the one persistent SSH connection, never opens another, every --every seconds.
Usage: python scripts/training_feed.py JOB_ID [--every 30]
"""
import argparse
import ast
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'reports' / 'live' / 'training.json'
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ControlMaster=no', '-o', f'ControlPath={Path.home()}/.ssh/cm-lexsi', 'CLUSTER_ACCOUNT@CLUSTER_HOST']
PROGRESS = re.compile(r'(\d+)/(\d+) \[([\d:]+)<([\d:]+),\s*([\d.]+)(s/it|it/s)\]')


REMOTE = r"""
L=$(ls ~/lexsi/logs/*-JOB.out | head -1)
sacct -j JOB --format=State -n -X | tr -d ' '
echo ===
sed -n '/overfit gate passed/,$p' $L | grep -oE "\{'(loss|eval_loss)'[^}]*\}"
echo ===
tail -c 20000 $L | tr '\r' '\n' | grep -oE '[0-9]+/[0-9]+ \[[0-9:]+<[0-9:]+, *[0-9.]+(s/it|it/s)\]'
echo ===
grep -hE 'rows built|overfit gate|first training|crashed|gate failed' $L
"""


def snapshot(job):
    text = subprocess.run(SSH + [REMOTE.replace('JOB', str(job))], capture_output=True, text=True, timeout=60).stdout
    state, logs, bars, notes = (text.split('===') + ['', '', '', ''])[:4]
    train, held = [], []
    for line in logs.split('\n'):
        line = line.strip()
        if not line:
            continue
        item = {k: float(v) for k, v in ast.literal_eval(line).items()}
        if 'eval_loss' in item:
            held.append({'step': len(train), **item})
        else:
            train.append({'step': len(train) + 1, **item})
    found = [m for m in map(PROGRESS.search, bars.split('\n')) if m]
    main_bar = max(found, key=lambda m: int(m[2])) if found else None  # the training bar, not an evaluation bar
    main_bar = next((m for m in reversed(found) if int(m[2]) == int(main_bar[2])), None) if main_bar else None
    progress = {'step': int(main_bar[1]), 'total': int(main_bar[2]), 'elapsed': main_bar[3], 'remaining': main_bar[4], 'rate': f'{main_bar[5]} {main_bar[6]}'} if main_bar else None
    return {'job': job, 'state': state.strip(), 'updated': time.strftime('%H:%M:%S'), 'progress': progress, 'train': train, 'held_out': held,
            'notes': [n for n in notes.strip().split('\n') if n]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('job')
    parser.add_argument('--every', type=int, default=30)
    args = parser.parse_args()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            data = snapshot(args.job)
            OUT.write_text(json.dumps(data))
            if data['state'] and not data['state'].startswith(('RUNNING', 'PENDING')):
                break
        except (subprocess.SubprocessError, ValueError, SyntaxError) as error:
            print('feed error:', type(error).__name__, error, flush=True)
        time.sleep(args.every)


if __name__ == '__main__':
    main()
