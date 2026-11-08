"""Sign-in, company workspaces and chat history. Temporary account and data folders, and a scripted stand-in model."""
import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
import server  # noqa: E402
import store  # noqa: E402
import users  # noqa: E402

PASSWORD = 'correct horse'


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv('LEXSI_USERS', str(tmp_path / 'config' / 'users.json'))
    monkeypatch.setenv('LEXSI_DATA', str(tmp_path / 'data'))
    monkeypatch.setattr(server, '_tries', {})
    (tmp_path / 'adapters').mkdir()
    (tmp_path / 'adapters' / 'second_adapter.gguf').write_bytes(b'stand-in adapter')
    monkeypatch.setattr(server, 'ADAPTERS', tmp_path / 'adapters')
    monkeypatch.setattr(server, '_failures', server.collections.defaultdict(server.collections.deque))
    server._sync_companies()
    for name in ('ada', 'bob'):  # members of every workspace, so the isolation tests below cover all of them
        users.add(name, PASSWORD, 'hellberg')
        for workspace in server.WORKSPACES:
            store.join(name, workspace)
    return tmp_path


def signed_in(name='ada'):
    client = TestClient(server.app)
    assert client.post('/api/login', json={'name': name, 'password': PASSWORD}).status_code == 200
    return client


def test_the_store_holds_salted_hashes_only_and_is_private(setup):
    path = store.database()
    assert path == setup / 'data' / 'strategy_lab.db'
    assert PASSWORD.encode() not in path.read_bytes() and store.user('ada')['salt'] != store.user('bob')['salt']
    assert path.stat().st_mode & 0o777 == 0o600 and path.parent.stat().st_mode & 0o777 == 0o700
    with pytest.raises(ValueError):
        users.add('../escape', PASSWORD, 'hellberg')
    with pytest.raises(ValueError):
        users.add('short', 'tiny', 'hellberg')


def test_every_page_and_api_route_needs_a_session(setup):
    client = TestClient(server.app)
    for route in server.app.routes:
        path = getattr(route, 'path', '')
        if path.startswith('/api/') and path not in server.OPEN:
            concrete = path.replace('{pilot_id}', 'pilot1').replace('{arm}', 'trained').replace('{index}', '0').replace('{identifier}', 'x').replace('{workspace}', 'hellberg')
            for method in getattr(route, 'methods', {'GET'}) - {'HEAD'}:
                assert client.request(method, concrete).status_code == 401, (method, concrete)
    page = client.get('/', follow_redirects=False)
    assert page.status_code == 303 and page.headers['location'] == '/login'
    assert client.get('/static/app.js', follow_redirects=False).status_code == 303
    assert client.get('/login').status_code == 200 and client.get('/static/login.js').status_code == 200


def test_a_wrong_password_or_unknown_name_is_refused(setup):
    client = TestClient(server.app)
    assert client.post('/api/login', json={'name': 'ada', 'password': 'wrong one'}).status_code == 401
    assert client.post('/api/login', json={'name': 'nobody', 'password': PASSWORD}).status_code == 401
    assert client.get('/api/me').status_code == 401


def test_the_session_cookie_is_http_only_and_strict(setup):
    client = TestClient(server.app)
    response = client.post('/api/login', json={'name': 'ada', 'password': PASSWORD})
    cookie = response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=strict' in cookie and 'path=/' in cookie and 'max-age=43200' in cookie
    assert client.get('/api/me').json()['user'] == 'ada'


def test_signing_out_ends_the_session(setup):
    client = signed_in()
    token = client.cookies.get(server.COOKIE)
    assert client.post('/api/logout').status_code == 200
    other = TestClient(server.app)
    other.cookies.set(server.COOKIE, token)
    assert other.get('/api/me').status_code == 401


def test_failed_sign_ins_are_rate_limited_per_name(setup):
    client = TestClient(server.app)
    for _ in range(server.FAILED_LIMIT):
        assert client.post('/api/login', json={'name': 'ada', 'password': 'wrong one'}).status_code == 401
    assert client.post('/api/login', json={'name': 'ada', 'password': PASSWORD}).status_code == 429
    assert client.post('/api/login', json={'name': 'bob', 'password': PASSWORD}).status_code == 200


def test_workspaces_are_the_configured_companies_with_their_own_prompts(setup):
    spaces = signed_in().get('/api/workspaces').json()['workspaces']
    assert [w['id'] for w in spaces] == list(server.WORKSPACES)
    for w in spaces:
        assert w['base_case'] == f"{w['id']}-base" and len(w['examples']) >= 3
        assert all(s['case'].startswith(w['id'] + '-') for s in w['scenarios'])
        others = [o['company'] for o in spaces if o['id'] != w['id']]
        assert not any(name in ' '.join(w['examples']) for name in others)


def test_a_workspace_refuses_another_companys_case(setup, monkeypatch):
    monkeypatch.setattr(server, '_model_ready', lambda: True)
    monkeypatch.setattr(server, '_loaded_adapters', lambda: ['final_adapter.gguf', 'first_adapter.gguf', 'second_adapter.gguf'])
    client = signed_in()
    assert client.post('/api/try', json={'workspace': 'hellberg', 'case': 'jotun-base'}).status_code == 403
    assert client.post('/api/try', json={'workspace': 'moldex', 'case': 'moldex-base'}).status_code == 404
    assert client.get('/api/workspaces/moldex/history').status_code == 404


def stand_in(url, messages, seed, max_tokens, schema=None, temperature=0, lora=None):
    return {'text': '{"name": "read_brief", "arguments": {}}'}


def test_history_is_kept_per_user_and_company_and_survives_a_restart(setup, monkeypatch):
    monkeypatch.setattr(server, '_model_ready', lambda: True)
    monkeypatch.setattr(server, '_loaded_adapters', lambda: ['final_adapter.gguf', 'first_adapter.gguf', 'second_adapter.gguf'])
    monkeypatch.setattr(server, 'chat', stand_in)
    client = signed_in()
    started = client.post('/api/try', json={'workspace': 'jotun', 'case': 'jotun-base', 'question': 'Should Jotun sell paint to homeowners?'})
    assert started.status_code == 201
    identifier = started.json()['id']
    for _ in range(100):
        if client.get(f'/api/try/{identifier}').json()['status'] != 'running':
            break
        time.sleep(.05)
    entries = client.get('/api/workspaces/jotun/history').json()['entries']
    assert entries[0].get('error') is None, entries[0]
    assert [e['question'] for e in entries] == ['Should Jotun sell paint to homeowners?'] and entries[0]['status'] == 'finished'
    assert entries[0]['summary']['stop_reason'] == 'repeated errors'
    assert client.get(f'/api/workspaces/jotun/history/{identifier}').json()['record']['case'] == 'jotun-base'
    assert client.get('/api/workspaces/neumann/history').json()['entries'] == []
    other = signed_in('bob')
    assert other.get('/api/workspaces/jotun/history').json()['entries'] == [] and other.get(f'/api/try/{identifier}').status_code == 404
    monkeypatch.setattr(server, '_tries', {})  # a restart forgets live runs; history and sessions are in the database
    assert client.get('/api/workspaces/jotun/history').json()['entries'][0]['status'] == 'finished'
    assert store.history('ada', 'jotun')[0]['id'] == identifier


    # Pins, projects and deletion: per user, refused for another user's run, and a deleted project releases its runs.
    project = client.post('/api/workspaces/jotun/projects', json={'name': 'Homeowners'}).json()
    assert client.patch(f'/api/workspaces/jotun/history/{identifier}', json={'pinned': True, 'project': project['id']}).status_code == 200
    listing = client.get('/api/workspaces/jotun/history').json()
    assert listing['entries'][0]['pinned'] and listing['entries'][0]['project'] == project['id'] and [p['name'] for p in listing['projects']] == ['Homeowners']
    assert other.patch(f'/api/workspaces/jotun/history/{identifier}', json={'pinned': False}).status_code == 404
    assert other.delete(f'/api/workspaces/jotun/history/{identifier}').status_code == 404
    assert client.delete(f"/api/workspaces/jotun/projects/{project['id']}").status_code == 200
    assert client.get('/api/workspaces/jotun/history').json()['entries'][0]['project'] is None
    assert client.delete(f'/api/workspaces/jotun/history/{identifier}').status_code == 200
    assert client.get('/api/workspaces/jotun/history').json()['entries'] == [] and client.get(f'/api/workspaces/jotun/history/{identifier}').status_code == 404



def test_an_account_sees_only_the_companies_it_is_a_member_of(setup):
    users.add('carol', PASSWORD, 'neumann')
    client = signed_in('carol')
    assert [w['id'] for w in client.get('/api/workspaces').json()['workspaces']] == ['neumann']
    assert client.get('/api/me').json()['companies'] == ['neumann']
    assert client.get('/api/workspaces/hellberg/history').status_code == 404
    hellberg = next(w for w in server.workspaces() if w['id'] == 'hellberg')
    assert client.post('/api/try', json={'workspace': 'hellberg', 'case': hellberg['base_case']}).status_code == 404
    store.join('carol', 'hellberg')
    assert [w['id'] for w in client.get('/api/workspaces').json()['workspaces']] == ['neumann', 'hellberg']


def stand_in_chat(url, messages, seed, max_tokens, schema=None, temperature=0, lora=None):
    if schema and 'answer' in schema.get('properties', {}):
        stand_in_chat.seen = messages  # the follow-up prompt, checked below
        return {'text': json.dumps({'answer': 'The test would show which explanation holds.', 'sources': ['not-a-source'], 'answered_from_record': True})}
    stand_in_chat.briefs = [*getattr(stand_in_chat, 'briefs', []), messages]
    return {'text': '{"name": "read_brief", "arguments": {}}'}


def test_memory_followups_mind_map_and_report(setup, monkeypatch):
    monkeypatch.setattr(server, '_model_ready', lambda: True)
    monkeypatch.setattr(server, '_loaded_adapters', lambda: ['final_adapter.gguf'])
    monkeypatch.setattr(server, 'chat', stand_in_chat)
    client, other = signed_in(), signed_in('bob')
    # memory: global, company and project notes, private to each account; a full memory refuses instead of failing silently
    project = client.post('/api/workspaces/jotun/projects', json={'name': 'Homeowners'}).json()
    assert client.post('/api/memory', json={'text': 'I decide on budgets under 50k.'}).status_code == 201
    assert client.post('/api/memory', json={'text': 'We sell through distributors.', 'workspace': 'jotun'}).status_code == 201
    assert client.post('/api/memory', json={'text': 'Only Norway for now.', 'workspace': 'jotun', 'project': project['id']}).status_code == 201
    assert client.post('/api/memory', json={'text': 'x' * 10, 'project': project['id']}).status_code == 422  # a project note names its company
    seen = client.get(f"/api/memory?workspace=jotun&project={project['id']}").json()
    assert [len(seen[k]) for k in ('global', 'company', 'project')] == [1, 1, 1] and seen['enabled']
    assert other.get('/api/memory?workspace=jotun').json()['global'] == []
    assert other.delete(f"/api/memory/{seen['global'][0]['id']}").status_code == 404
    # a run in the project gets all three notes in its brief, and records them
    started = client.post('/api/try', json={'workspace': 'jotun', 'case': 'jotun-base', 'question': 'Should Jotun sell to homeowners?', 'project': project['id']})
    assert started.status_code == 201
    identifier = started.json()['id']
    for _ in range(100):
        if client.get(f'/api/try/{identifier}').json()['status'] != 'running':
            break
        time.sleep(.05)
    detail = client.get(f'/api/workspaces/jotun/history/{identifier}').json()
    assert len(detail['memory_used']) == 3 and detail['metrics']['steps']['total'] >= 1
    assert any('Only Norway for now.' in m['content'] for call in stand_in_chat.briefs for m in call)
    # a follow-up is answered from the record; a cited id that is not in the record is dropped
    asked = client.post(f'/api/workspaces/jotun/history/{identifier}/followups', json={'question': 'What would the test show?'})
    assert asked.status_code == 201
    for _ in range(100):
        items = client.get(f'/api/workspaces/jotun/history/{identifier}/followups').json()['followups']
        if items[0]['status'] != 'answering':
            break
        time.sleep(.05)
    assert items[0]['answer'].startswith('The test would show') and items[0]['sources'] == []
    assert 'distributors' in stand_in_chat.seen[1]['content']
    assert other.post(f'/api/workspaces/jotun/history/{identifier}/followups', json={'question': 'Hi there'}).status_code == 404
    # the mind map groups it under its project; the report is built from the same record
    tree = client.get('/api/workspaces/jotun/mindmap').json()
    assert [c['label'] for c in tree['children']] == ['Homeowners'] and tree['children'][0]['children'][0]['id'] == identifier
    monkeypatch.setattr(server.pdf_report, 'pdf', lambda page: b'%PDF-' + page.encode()[:20])
    pdf = client.get(f'/api/workspaces/jotun/history/{identifier}/report.pdf')
    assert pdf.status_code == 200 and pdf.headers['content-type'] == 'application/pdf' and pdf.content.startswith(b'%PDF-')
    # deleting the investigation deletes its follow-ups; deleting the project deletes its notes
    assert client.delete(f'/api/workspaces/jotun/history/{identifier}').status_code == 200
    assert store.followups('ada', 'jotun', identifier) == []
    assert client.delete(f"/api/workspaces/jotun/projects/{project['id']}").status_code == 200
    assert client.get(f"/api/memory?workspace=jotun").json()['project'] == []
