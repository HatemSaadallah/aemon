"""Each swap of hand-written code for a package gives the same output as the code it replaced. None of them changes what
the model sees or a published number. The replaced code is kept here verbatim as the reference."""
import io
import json
import urllib.error
import urllib.request

import pytest

from aemon.agent.backends import hosted_client


# --- 1. tenacity in the hosted client's retry ---------------------------------------------------------------------

def _old_post(body, sleep):  # hosted_client._post before tenacity, verbatim except the injected sleep
    request = urllib.request.Request(hosted_client.BASE + '/chat/completions', data=json.dumps(body).encode(), headers={
        'Content-Type': 'application/json', 'Authorization': 'Bearer test'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (429, 500, 502, 503) and attempt < 3:
                sleep(10 * (attempt + 1))
                continue
            raise RuntimeError(f'DeepSeek HTTP {error.code}: {error.read()[:300]!r}') from None
        except (urllib.error.URLError, TimeoutError):
            if attempt < 3:
                sleep(10 * (attempt + 1))
                continue
            raise
    raise RuntimeError('unreachable')


def _http(code):
    return urllib.error.HTTPError('u', code, 'x', {}, io.BytesIO(b'body'))


class _Reply(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


SCENARIOS = {  # the failures the server gives before it answers
    'ok': [],
    'one 429 then ok': [('http', 429)],
    'three 503 then ok': [('http', 503)] * 3,
    'four 502': [('http', 502)] * 4,
    'a 400': [('http', 400)],
    'timeout then 500 then ok': [('timeout',), ('http', 500)],
    'four dropped connections': [('url',)] * 4,
    'a 404 after a timeout': [('timeout',), ('http', 404)],
}


def _make(failure):
    return {'http': lambda: _http(failure[-1]), 'timeout': lambda: TimeoutError('slow'), 'url': lambda: urllib.error.URLError('down')}[failure[0]]()


def _outcome(post, failures, monkeypatch):
    queue, calls, sleeps = [_make(f) for f in failures], [], []

    def urlopen(request, timeout):
        calls.append((request.full_url, request.data, timeout))
        if queue:
            raise queue.pop(0)
        return _Reply(b'{"choices": []}')

    monkeypatch.setattr(urllib.request, 'urlopen', urlopen)
    monkeypatch.setattr(hosted_client, '_sleep', sleeps.append)
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test')
    try:
        result = ('returned', post(sleeps.append))
    except Exception as error:  # noqa: BLE001
        result = ('raised', type(error).__name__, str(error))
    return result, calls, sleeps


@pytest.mark.parametrize('name', SCENARIOS)
def test_hosted_retry_with_tenacity_matches_the_old_loop(name, monkeypatch):
    old = _outcome(lambda sleep: _old_post({'a': 1}, sleep), SCENARIOS[name], monkeypatch)
    new = _outcome(lambda sleep: hosted_client._post({'a': 1}), SCENARIOS[name], monkeypatch)
    assert new == old  # same result or error, same requests, same waits
    assert len(old[1]) <= 4


# --- 2. scipy's Spearman in the judge report ------------------------------------------------------------------------

def _old_spearman(a, b):  # report.spearman before scipy, verbatim
    import statistics
    if len(a) < 3:
        return None

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r

    ra, rb = ranks(a), ranks(b)
    if statistics.pstdev(ra) == 0 or statistics.pstdev(rb) == 0:
        return None
    return round(statistics.correlation(ra, rb), 3)


def test_scipy_spearman_matches_the_old_one_on_ties_short_and_constant_inputs():
    import random
    from aemon.evaluation.judging.report import spearman
    rng = random.Random(7)
    cases = [([1, 2], [2, 1]), ([1, 1, 1], [1, 2, 3]), ([1, 2, 3], [5, 5, 5]), ([0, 0.5, 0.5, 1], [1, 0.5, 0.5, 0])]
    cases += [([rng.choice([0, 0.5, 1, 1.5, 2, 2.5, 3]) for _ in range(n)], [rng.choice([0, 1, 2, 3]) for _ in range(n)]) for n in range(3, 120)]
    for a, b in cases:
        assert spearman(a, b) == _old_spearman(a, b), (a, b)


ENV_FILES = [  # fake values only
    'CLAUDE_API_KEY=sk-test-plain\nDEEPSEEK_API_KEY=ds-test\n',
    '# keys\nCLAUDE_API_KEY="sk-test-double"\n\nDEEPSEEK_API_KEY=\'ds-test-single\'\nOPS_PORT=8100\n',
    'OTHER=1\nCLAUDE_API_KEY=sk-test-after-other   \n',
    'DEEPSEEK_API_KEY=ds-only\n',
    '',
]


def _old_api_key(env):  # claude_backend.api_key's file branch before python-dotenv, verbatim
    for line in env.read_text().splitlines() if env.exists() else ():
        if line.startswith('CLAUDE_API_KEY='):
            return line.split('=', 1)[1].strip().strip('\'"')
    return 'not set'


def _old_dashboard_env(env):  # ops/dashboard._env before python-dotenv, verbatim, into a dict instead of os.environ
    out = {}
    for line in env.read_text().splitlines() if env.exists() else []:
        if '=' in line and not line.lstrip().startswith('#'):
            key, _, value = line.partition('=')
            out.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    return out


@pytest.mark.parametrize('text', ENV_FILES)
def test_dotenv_reads_the_same_keys_and_values_as_the_old_parsers(text, tmp_path, monkeypatch):
    import importlib.util
    from pathlib import Path
    from aemon.agent.backends import claude_control
    (tmp_path / '.env').write_text(text)
    monkeypatch.delenv('CLAUDE_API_KEY', raising=False)
    monkeypatch.setattr(claude_control, 'ROOT', tmp_path)
    try:
        new_key = claude_control.api_key()
    except SystemExit:
        new_key = 'not set'
    assert new_key == _old_api_key(tmp_path / '.env')
    spec = importlib.util.spec_from_file_location('dashboard', Path(__file__).resolve().parents[1] / 'ops' / 'dashboard.py')
    dashboard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dashboard)
    monkeypatch.setattr(dashboard, 'ROOT', tmp_path)
    old = _old_dashboard_env(tmp_path / '.env')
    for key in old:  # recorded, so the keys _env sets are removed again after the test
        monkeypatch.setenv(key, 'placeholder')
        monkeypatch.delenv(key)
    dashboard._env()
    import os
    assert {k: os.environ.get(k) for k in old} == old


def _old_table(rows, header):  # scripts/cluster.py table before tabulate, verbatim
    widths = [max(len(str(r[i])) for r in [header, *rows]) for i in range(len(header))]
    line = lambda r: '  '.join(str(c).ljust(w) for c, w in zip(r, widths))  # noqa: E731
    return '\n'.join([line(header), line(['-' * w for w in widths]), *map(line, rows)])


def test_tabulate_gives_the_same_columns_as_the_old_padding():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('cluster', Path(__file__).resolve().parents[1] / 'scripts' / 'cluster' / 'cluster.py')
    cluster = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cluster)
    queue = ['job', 'name', 'state', 'elapsed', 'limit', 'gpu', 'node']
    rows = [['754713', 'eval-switch', 'PENDING', '0:00', '3:00:00', 'gres/gpu:4g.40gb:1', '(QOSMaxJobsPerUserLimit)'],
            ['754711', 'eval-switch', 'RUNNING', '0:02', '3:00:00', 'gres/gpu:4g.40gb:1', 'gnode03'], ['7', 'x', '', '', '', '', '']]
    for r in (rows, rows[:1]):
        new, old = cluster.table(r, queue), _old_table(r, queue)
        assert new.splitlines() == [line.rstrip() for line in old.splitlines()]  # only trailing spaces differ


def _cluster():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('cluster', Path(__file__).resolve().parents[1] / 'scripts' / 'cluster' / 'cluster.py')
    cluster = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cluster)
    return cluster


def test_submit_flags_are_unchanged_without_the_new_options_and_pass_array_and_dependency_through():
    flags = _cluster().sbatch_flags
    old = lambda exclude, after: f'--parsable --export=ALL --exclude={exclude}' + (f' --dependency=afterok:{after}' if after else '')  # noqa: E731
    for after in (None, '754710'):
        assert flags('gnode04', after) == old('gnode04', after)
    assert flags('gnode04', dependency='afterany:754710', array='0-4%4') == '--parsable --export=ALL --exclude=gnode04 --dependency=afterany:754710 --array=0-4%4'
    with pytest.raises(SystemExit):
        flags('gnode04', '1', 'afterany:2')


@pytest.mark.parametrize('task,arm,route', [(0, 'v1', 'default=0'), (2, 'v3_rescue', 'default=1,stuck=0'), (3, '3', 'default=1,brief=0,evidence=0')])
def test_the_route_array_job_picks_its_arm_by_task_id(task, arm, route):
    import subprocess
    from pathlib import Path
    script = (Path(__file__).resolve().parents[1] / 'jobs' / 'eval_routes.sbatch').read_text()
    head = script[script.index('IFS='):script.index('L=$HOME/lexsi')]
    env = {'ROUTES': 'v1:default=0;v3:default=1;v3_rescue:default=1,stuck=0;default=1,brief=0,evidence=0', 'NAME_PREFIX': 'switch',
           'SLURM_ARRAY_TASK_ID': str(task), 'PATH': '/usr/bin:/bin'}
    out = subprocess.run(['bash', '-c', 'set -euo pipefail\n' + head + 'echo "$ARM|$ROUTE|$NAME"'], env=env, capture_output=True, text=True, check=True)
    assert out.stdout.strip().splitlines()[-1] == f'{arm}|{route}|switch_{arm}'


def test_the_final_test_report_recomputes_identically():
    from pathlib import Path
    from aemon.evaluation.judging.report import report
    final = Path(__file__).resolve().parents[1] / 'reports/judge/final'
    new = report(str(final / 'key.jsonl'), {'claude': str(final / 'claude_predictions.jsonl'), 'codex': str(final / 'codex_predictions.jsonl')},
                 ('trained', 'base'))
    assert json.loads(json.dumps(new)) == json.loads((final / 'report_trained_vs_base.json').read_text())
