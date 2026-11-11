"""The Bocconi cluster from Python: status, submit, log. Over the one SSH master only (never a new connection).

    python scripts/cluster/cluster.py status                 # running and queued jobs, and the last day's finished ones
    python scripts/cluster/cluster.py submit jobs/X.sbatch --env NAME=a REVISION=abc --after 123 [--gpu]
    python scripts/cluster/cluster.py log 123 [--lines 40]    # the tail of a job's output file

Slurm's own commands (sbatch, squeue, sacct) do the work on the login node, parsed into tables here; nothing is
computed there. If the master socket is gone, the tool says so and stops: reopen it once (see the HPC notes), never in
a loop. gnode04 is excluded by default (jobs die there at once, seen 2026-11-08).
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

try:
    import tabulate as tabulate_module
    from tabulate import tabulate
except ModuleNotFoundError:  # started with the system python3, as scripts and docs call it: rerun with the project's
    import os

    VENV = Path(__file__).resolve().parents[2] / '.venv' / 'bin' / 'python'
    if not VENV.exists() or Path(sys.executable).resolve() == VENV.resolve():
        raise
    os.execv(str(VENV), [str(VENV), *sys.argv])

HOST = 'CLUSTER_ACCOUNT@CLUSTER_HOST'
SOCKET = str(Path.home() / '.ssh' / 'cm-lexsi')
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ControlMaster=no', '-o', f'ControlPath={SOCKET}', '-o', 'ProxyCommand=false', HOST]
EXCLUDE = 'gnode04'
REMOTE = '~/lexsi'


def master_up() -> bool:
    return subprocess.run(['ssh', '-O', 'check', '-o', f'ControlPath={SOCKET}', HOST], capture_output=True).returncode == 0


class Unavailable(RuntimeError):
    """The master is down or a remote command failed."""


def remote(command: str) -> str:
    if not master_up():
        raise Unavailable('The SSH master is not running. Reopen it once (HPC notes), then try again.')
    done = subprocess.run([*SSH, command], capture_output=True, text=True, timeout=120)
    if done.returncode:
        raise Unavailable(f'remote command failed ({done.returncode}): {done.stderr.strip()[:400]}')
    return done.stdout


QUEUE = ['job', 'name', 'state', 'elapsed', 'limit', 'gpu', 'node']
FINISHED = ['job', 'name', 'state', 'elapsed', 'ended', 'node', 'exit']


def jobs() -> dict[str, list[dict[str, str]]]:
    """Running and queued jobs, and the last day's finished ones, as rows (used by Aemon's Cluster page)."""
    out = remote("squeue -u $USER -h -o '%i|%j|%T|%M|%l|%b|%R' ; echo '@@' ; "
                 "sacct -u $USER -S now-1days -X -n -P -o JobID,JobName%30,State,Elapsed,End,NodeList,ExitCode")
    queue_text, _, done_text = out.partition('@@')
    queue = [dict(zip(QUEUE, r.split('|'))) for r in queue_text.strip().splitlines() if r]
    live = {r['job'] for r in queue}
    finished = [dict(zip(FINISHED, r.split('|'))) for r in done_text.strip().splitlines() if r]
    finished = [dict(r, ended=r.get('ended', '').replace('T', ' ')) for r in finished if r['job'] not in live]
    return {'queue': queue, 'finished': finished[-15:]}


def table(rows: list[list[str]], header: list[str]) -> str:
    """Left-aligned columns two spaces apart under a dashed rule; job ids stay text, so they are not right-aligned."""
    tabulate_module.MIN_PADDING = 0  # columns as wide as their widest cell, header included
    return tabulate(rows, header, tablefmt='simple', disable_numparse=True, stralign='left')


def status() -> None:
    data = jobs()
    q = [[r.get(k, '') for k in QUEUE] for r in data['queue']]
    print(table(q, QUEUE) if q else 'No running or queued jobs.')
    if data['finished']:
        print('\nFinished in the last day:')
        print(table([[r.get(k, '') for k in FINISHED] for r in data['finished']], FINISHED))


def sbatch_flags(exclude: str, after: str | None = None, dependency: str | None = None, array: str | None = None) -> str:
    """--after JOB is shorthand for --dependency afterok:JOB; --dependency passes any Slurm dependency (afterany:123, ...)."""
    if after and dependency:
        raise SystemExit('give --after or --dependency, not both')
    dependency = f'afterok:{after}' if after else dependency
    return (f'--parsable --export=ALL --exclude={exclude}' + (f' --dependency={shlex.quote(dependency)}' if dependency else '')
            + (f' --array={shlex.quote(array)}' if array else ''))


def submit(script: str, env: list[str], after: str | None, exclude: str, dependency: str | None = None, array: str | None = None) -> None:
    name = Path(script).name
    pairs = ' '.join(shlex.quote(e) for e in env)
    # The script is copied next to the job's code, as earlier jobs were; the environment goes in with --export=ALL
    # because some values (CASES) contain commas, which --export=K=V would split.
    subprocess.run([*SSH, f'cat > {REMOTE}/{name}'], input=Path(script).read_bytes(), check=True, timeout=120)
    flags = sbatch_flags(exclude, after, dependency, array)
    job = remote(f'cd {REMOTE} && env {pairs} sbatch {flags} {name}').strip()
    print(f'submitted {name} as job {job}' + (f', after {after} succeeds' if after else '') + (f', waiting on {dependency}' if dependency else '')
          + (f', array {array}' if array else ''))


def log(job: str, lines: int) -> None:
    print(remote(f'f=$(ls -t {REMOTE}/*-{shlex.quote(job)}.out 2>/dev/null | head -1); '
                 f'[ -n "$f" ] && {{ echo "== $f"; tail -n {int(lines)} "$f"; }} || echo "no output file for job {job} yet"'))


def main() -> None:
    p = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    sub = p.add_subparsers(dest='step', required=True)
    sub.add_parser('status')
    s = sub.add_parser('submit')
    s.add_argument('script')
    s.add_argument('--env', nargs='*', default=[], metavar='KEY=VALUE')
    s.add_argument('--after', help='start only after this job succeeds')
    s.add_argument('--dependency', help='any Slurm dependency, such as afterany:754710 (the job ends, whatever its state)')
    s.add_argument('--array', help='Slurm array indices, such as 0-4%%4 (five tasks, at most four at once)')
    s.add_argument('--exclude', default=EXCLUDE)
    g = sub.add_parser('log')
    g.add_argument('job')
    g.add_argument('--lines', type=int, default=40)
    a = p.parse_args()
    try:
        run(a)
    except Unavailable as error:
        sys.exit(str(error))


def run(a: argparse.Namespace) -> None:
    if a.step == 'status':
        status()
    elif a.step == 'submit':
        submit(a.script, a.env, a.after, a.exclude, a.dependency, a.array)
    else:
        log(a.job, a.lines)


if __name__ == '__main__':
    main()
