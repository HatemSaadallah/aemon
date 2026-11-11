"""Aemon API checks. Uses fixture runs in a temporary folder, and no model."""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
os.environ['LEXSI_NO_RESUME'] = '1'  # never resume runs from a real database at import
import server  # noqa: E402
from aemon.environment.cases import load_cases  # noqa: E402
from aemon.agent.records import record_of
from aemon.environment.tools import Investigation  # noqa: E402

XSS = '<img src=x onerror=alert(1)>'


@pytest.fixture
def client(tmp_path, monkeypatch):
    case = load_cases('moldex-new-evidence-looks')[0]
    run = Investigation(case, staged=True)
    run.call('read_brief', {})
    run.call('frame_problem', {'objective': XSS, 'constraints': ['Small budget'], 'alternatives': ['Enter', 'Partner', 'Do not enter']})
    client_record = record_of(run, {'stop_reason': 'repeated errors', 'turns': [{'text': 'secret'}]})
    monkeypatch.setattr(server, '_tries', {})
    monkeypatch.setenv('LEXSI_USERS', str(tmp_path / 'config' / 'users.json'))
    monkeypatch.setenv('LEXSI_DATA', str(tmp_path / 'data'))
    import users
    server._sync_companies()
    users.add('tester', 'correct horse', 'hellberg')
    client = TestClient(server.app)
    assert client.post('/api/login', json={'name': 'tester', 'password': 'correct horse'}).status_code == 200
    client.record = server.detail(client_record, case)
    return client


def test_model_text_in_a_report_is_escaped_and_its_numbers_come_from_the_record(client):
    import insights
    import report

    record = client.record
    record['assessments'] = [{'theory_id': 'T1', 'evidence_id': 'x', 'direction': 'supports', 'quote': XSS, 'class': 'verified_observation'}]
    record['theories'] = {'T1': {'claim': XSS}}
    metrics = insights.metrics(record, 20000, 12)
    assert metrics['evidence'][0]['supports'] == 1 and metrics['evidence'][0]['independent_supports'] == 1
    page = report.build(record, metrics, 'Moldex', XSS, [{'question': XSS, 'answer': XSS, 'sources': []}])
    assert '<img' not in page and '&lt;img' in page


def test_model_text_is_returned_as_data_and_the_page_never_builds_html():
    sources = [p.read_text() for p in (Path(__file__).parent / 'web' / 'src').rglob('*.ts*')]
    assert not any(bad in source for source in sources for bad in ('innerHTML', 'insertAdjacentHTML', 'document.write', 'dangerouslySetInnerHTML'))


def test_a_try_needs_the_model_server(client, monkeypatch):
    monkeypatch.setattr(server, '_model_ready', lambda: False)
    assert client.post('/api/try', json={'workspace': 'hellberg', 'case': 'hellberg-base'}).status_code == 503
    assert client.get('/api/try').json()['model_ready'] is False


def test_a_try_refuses_an_unknown_case_and_unknown_fields(client):
    assert client.post('/api/try', json={'workspace': 'hellberg', 'case': 'nothing'}).status_code == 404
    assert client.post('/api/try', json={'workspace': 'hellberg', 'case': 'hellberg-base', 'model': 'claude'}).status_code == 422


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


def test_the_numbers_and_suggestions_work_for_a_case_with_no_what_if(client):
    import insights

    record = dict(client.record, coverage={'shock': None})  # a base case records its what-if as None
    assert insights.suggestions(record) and insights.metrics(record)['beliefs'] == []
