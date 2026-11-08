"""Strategy Lab API checks. Uses fixture runs in a temporary folder, and no model."""
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import server  # noqa: E402
from strategy_agent.env.cases import load_cases  # noqa: E402
from strategy_agent.agent.runner import record_of, summary  # noqa: E402
from strategy_agent.env.tools import Investigation  # noqa: E402

XSS = '<img src=x onerror=alert(1)>'


@pytest.fixture
def client(tmp_path, monkeypatch):
    case = load_cases('moldex-new-evidence-looks')[0]
    run = Investigation(case, staged=True)
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': XSS, 'constraints': ['Small budget'], 'alternatives': ['Enter', 'Partner', 'Do not enter']})
    record = record_of(run, {'stop_reason': 'repeated errors', 'turns': [{'text': 'secret'}]})
    for name in ('first_base', 'first_adapter'):
        report = {'model': name, 'runtime': 'llama.cpp', 'summary': summary([record]), 'records': [record]}
        path = tmp_path / 'pilot1' / f'{name}.json'
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(report))
    monkeypatch.setattr(server, 'RUNS', tmp_path)
    monkeypatch.setattr(server, '_cache', {})
    monkeypatch.setattr(server, '_tries', {})
    monkeypatch.setenv('LEXSI_USERS', str(tmp_path / 'config' / 'users.json'))
    monkeypatch.setenv('LEXSI_DATA', str(tmp_path / 'data'))
    import users
    server._sync_companies()
    users.add('tester', 'correct horse', 'hellberg')
    client = TestClient(server.app)
    assert client.post('/api/login', json={'name': 'tester', 'password': 'correct horse'}).status_code == 200
    return client


def test_the_results_say_which_runs_are_the_final_test_and_which_are_development(client):
    data = client.get('/api/pilots').json()
    banner = data['banner']
    assert 'final test ran once' in banner and 'development runs' in banner and 'not measures of strategy quality' in banner
    final = next(p for p in data['pilots'] if p['id'] == 'final')
    assert 'never used for training or selection' in final['note'] and 'staged prompt' in final['note']


def test_a_pilot_is_shown_only_when_both_arms_have_reports(client):
    pilots = client.get('/api/pilots').json()['pilots']
    assert [p['id'] for p in pilots] == ['pilot1']
    assert pilots[0]['totals']['untrained']['cases'] == 1 and client.get('/api/pilots/pilot2/trained/0').status_code == 404


def test_each_case_pairs_the_two_arms_and_says_where_they_stopped(client):
    row = client.get('/api/pilots').json()['pilots'][0]['cases'][0]
    assert row['case'] == 'moldex-new-evidence-looks'
    for arm in ('untrained', 'trained'):
        assert row[arm]['stop_reason'] == 'repeated errors' and row[arm]['stage_at_stop'] == 'evidence' and not row[arm]['finished'] and row[arm]['index'] == 0


def test_an_episode_leaves_out_raw_model_turns_but_keeps_the_question(client):
    record = client.get('/api/pilots/pilot1/trained/0').json()['record']
    assert 'model_turns' not in record and record['question'] and record['frame']['objective'] == XSS


def test_a_missing_episode_is_a_404(client):
    assert client.get('/api/pilots/pilot1/trained/9').status_code == 404
    assert client.get('/api/pilots/pilot1/claude/0').status_code == 404
    assert client.get('/api/pilots/nothing/trained/0').status_code == 404


def test_model_text_is_returned_as_data_and_the_page_never_builds_html():
    source = (Path(__file__).parent / 'static' / 'app.js').read_text()
    assert 'innerHTML' not in source and 'insertAdjacentHTML' not in source and 'document.write' not in source


def test_a_try_needs_the_model_server(client, monkeypatch):
    monkeypatch.setattr(server, '_model_ready', lambda: False)
    assert client.post('/api/try', json={'workspace': 'hellberg', 'case': 'hellberg-base'}).status_code == 503
    assert client.get('/api/try').json()['model_ready'] is False


def test_a_try_refuses_an_unknown_case_and_unknown_fields(client):
    assert client.post('/api/try', json={'workspace': 'hellberg', 'case': 'nothing'}).status_code == 404
    assert client.post('/api/try', json={'workspace': 'hellberg', 'case': 'hellberg-base', 'model': 'claude'}).status_code == 422


def test_the_live_view_reports_nothing_when_no_feed_is_running(client, monkeypatch, tmp_path):
    monkeypatch.setattr(server, 'LIVE', tmp_path / 'none.json')
    assert client.get('/api/training/live').json() == {'state': None}


def test_the_trained_model_needs_the_adapter_loaded(client, monkeypatch):
    monkeypatch.setattr(server, '_model_ready', lambda: True)
    monkeypatch.setattr(server, '_loaded_adapters', lambda: [])
    assert client.post('/api/try', json={'workspace': 'hellberg', 'case': 'hellberg-base', 'model': 'trained'}).status_code == 409
    assert client.post('/api/try', json={'workspace': 'hellberg', 'case': 'hellberg-base', 'model': 'second'}).status_code == 409
    monkeypatch.setattr(server, '_loaded_adapters', lambda: ['first_adapter.gguf'])
    assert server._model('trained')[0]['id'] == 'first'
    assert client.post('/api/try', json={'workspace': 'hellberg', 'case': 'hellberg-base', 'model': 'second'}).status_code == 409
    assert client.post('/api/try', json={'workspace': 'hellberg', 'case': 'hellberg-base', 'model': 'something'}).status_code == 422


def test_the_workflow_lists_every_stage_and_describes_every_tool(client):
    data = client.get('/api/workflow').json()
    assert [s['stage'] for s in data['stages']][:2] == ['brief', 'frame'] and data['stages'][-1]['stage'] == 'conclude'
    assert {t for s in data['stages'] for t in s['tools']} <= set(data['tools'])


def test_the_page_runs_one_live_model_and_refuses_it_when_its_adapter_is_missing(client, monkeypatch):
    monkeypatch.setattr(server, '_model_ready', lambda: True)
    monkeypatch.setattr(server, '_loaded_adapters', lambda: [])
    data = client.get('/api/try').json()
    assert data['model']['id'] == server.LIVE_MODEL and 'models' not in data
    assert data['model']['available'] is (dict((m['id'], m) for m in server.MODELS)[server.LIVE_MODEL]['adapter'] is None)
    if not data['model']['available']:
        assert client.post('/api/try', json={'workspace': 'hellberg', 'case': 'hellberg-base'}).status_code == 409


def test_belief_moves_are_judged_against_the_what_if_direction(client):
    from server import belief_move
    up = {'direction': 'undermines', 'affected_theories': ['T1'], 'beliefs_before': {'T1': 'uncertain'}, 'beliefs_after': {'T1': 'likely'}}
    assert belief_move(up)[0]['verdict'] == 'inconsistent'
    assert belief_move(dict(up, direction='supports'))[0]['verdict'] == 'consistent'
    assert belief_move(dict(up, beliefs_after=None))[0]['verdict'] == 'no belief after'
    data = client.get('/api/beliefs').json()
    assert data['scale'][0] == 'very unlikely' and all('cases' in a for a in data['arms'])
