"""Sign-in, company workspaces and chat history. Temporary account and data folders, and a scripted stand-in model."""
import json
import os
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ['LEXSI_NO_RESUME'] = '1'  # never resume runs from a real database at import
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
    monkeypatch.setattr(server, '_new_accounts', server.collections.deque())
    server._sync_companies()
    for name in ('ada', 'bob'):  # members of every workspace, so the isolation tests below cover all of them
        users.add(name, PASSWORD, 'hellberg')
        for workspace in server.WORKSPACES:
            store.join(name, workspace)
    return tmp_path


def signed_in(name='ada'):
    client = TestClient(server.app)
    assert client.post('/api/login', json={'name': name}).status_code == 200
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
    assert client.get('/brand/x.png', follow_redirects=False).status_code == 303
    assert client.get('/login').status_code == 200


def test_a_new_name_opens_an_account_in_every_company_and_the_same_name_reopens_it(setup):
    client = TestClient(server.app)
    assert client.post('/api/login', json={'name': 'Newcomer'}).status_code == 200
    me = client.get('/api/me').json()
    assert me['user'] == 'newcomer' and set(me['companies']) == set(server.WORKSPACES)
    salt = store.user('newcomer')['salt']
    again = TestClient(server.app)
    assert again.post('/api/login', json={'name': 'newcomer'}).status_code == 200
    assert store.user('newcomer')['salt'] == salt  # the same account, not a new one
    assert not users.verify('newcomer', '')  # no password matches an account opened by name


def test_a_name_that_is_not_a_safe_folder_name_is_refused(setup):
    client = TestClient(server.app)
    for bad in ('../escape', '', 'two words', 'x' * 40):
        assert client.post('/api/login', json={'name': bad}).status_code in (400, 422), bad
    assert client.get('/api/me').status_code == 401


def test_the_session_cookie_is_http_only_and_strict(setup):
    client = TestClient(server.app)
    response = client.post('/api/login', json={'name': 'ada'})
    cookie = response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=strict' in cookie and 'path=/' in cookie and 'max-age=43200' in cookie
    assert client.get('/api/me').json()['user'] == 'ada'


def test_a_hosted_copy_in_another_sites_frame_gets_a_partitioned_secure_cookie(setup, monkeypatch):
    monkeypatch.setenv('CROSS_SITE_COOKIE', '1')
    cookie = TestClient(server.app).post('/api/login', json={'name': 'ada'}).headers['set-cookie'].lower()
    assert 'samesite=none' in cookie and 'secure' in cookie and 'partitioned' in cookie and 'httponly' in cookie


def test_signing_out_ends_the_session(setup):
    client = signed_in()
    token = client.cookies.get(server.COOKIE)
    assert client.post('/api/logout').status_code == 200
    other = TestClient(server.app)
    other.cookies.set(server.COOKIE, token)
    assert other.get('/api/me').status_code == 401


def test_new_accounts_are_rate_limited_but_existing_names_still_sign_in(setup, monkeypatch):
    monkeypatch.setattr(server, 'NEW_ACCOUNTS_PER_HOUR', 2)
    client = TestClient(server.app)
    assert client.post('/api/login', json={'name': 'one'}).status_code == 200
    assert client.post('/api/login', json={'name': 'two'}).status_code == 200
    assert client.post('/api/login', json={'name': 'three'}).status_code == 429
    assert client.post('/api/login', json={'name': 'ada'}).status_code == 200


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
    # the report is built from the same record
    monkeypatch.setattr(server.pdf_report, 'pdf', lambda page, company='': b'%PDF-' + page.encode()[:20])
    pdf = client.get(f'/api/workspaces/jotun/history/{identifier}/report.pdf')
    assert pdf.status_code == 200 and pdf.headers['content-type'] == 'application/pdf' and pdf.content.startswith(b'%PDF-')
    # deleting the investigation deletes its follow-ups; deleting the project deletes its notes
    assert client.delete(f'/api/workspaces/jotun/history/{identifier}').status_code == 200
    assert store.followups('ada', 'jotun', identifier) == []
    assert client.delete(f"/api/workspaces/jotun/projects/{project['id']}").status_code == 200
    assert client.get(f"/api/memory?workspace=jotun").json()['project'] == []


def test_a_run_cut_off_by_a_restart_resumes_from_its_saved_turns(setup, monkeypatch):
    monkeypatch.setattr(server, '_model_ready', lambda: True)
    monkeypatch.setattr(server, '_loaded_adapters', lambda: ['final_adapter.gguf'])
    monkeypatch.setattr(server, 'chat', stand_in)
    client = signed_in()
    started = client.post('/api/try', json={'workspace': 'jotun', 'case': 'jotun-base', 'question': 'Should Jotun sell to homeowners?'})
    identifier = started.json()['id']
    for _ in range(100):
        if client.get(f'/api/try/{identifier}').json()['status'] != 'running':
            break
        time.sleep(.05)
    saved = next(e for e in store.history('ada', 'jotun') if e['id'] == identifier)
    assert saved['run_settings']['question'] == 'Should Jotun sell to homeowners?' and len(saved['turns']) >= 2
    # a restart in the middle: the run is still marked running with only its first turn saved, and the server forgets it
    store.record('ada', 'jotun', identifier, status='running', turns=saved['turns'][:1])
    monkeypatch.setattr(server, '_tries', {})
    server._resume(wait=0)
    again = next(e for e in store.history('ada', 'jotun') if e['id'] == identifier)
    assert again['status'] == 'finished' and again['record']['resumed_after_turn'] == 1
    assert len(again['record']['calls']) == len(saved['record']['calls']) and not any(c.get('prefix') for c in again['record']['calls'])
    # a live web run cannot be replayed: it is marked interrupted, not left running
    store.record('ada', 'jotun', identifier, status='running', run_settings={**saved['run_settings'], 'live': True})
    server._resume(wait=0)
    assert next(e for e in store.history('ada', 'jotun') if e['id'] == identifier)['status'] == 'interrupted'


def test_depth_sets_the_search_budget_and_step_limit_and_survives_a_resume(setup, monkeypatch):
    monkeypatch.setattr(server, '_model_ready', lambda: True)
    monkeypatch.setattr(server, '_loaded_adapters', lambda: ['final_adapter.gguf'])
    monkeypatch.setattr(server, 'chat', stand_in)
    client = signed_in()
    assert client.post('/api/try', json={'workspace': 'jotun', 'case': 'jotun-base', 'depth': 'deep'}).status_code == 422
    identifier = client.post('/api/try', json={'workspace': 'jotun', 'case': 'jotun-base', 'depth': 'quick'}).json()['id']
    for _ in range(100):
        if client.get(f'/api/try/{identifier}').json()['status'] != 'running':
            break
        time.sleep(.05)
    saved = next(e for e in store.history('ada', 'jotun') if e['id'] == identifier)
    assert saved['record']['depth'] == 'quick' and saved['run_settings']['depth'] == 'quick'
    assert '"search_budget": 5' in json.dumps(saved['turns'][0]['tool_result'])
    store.record('ada', 'jotun', identifier, status='running', turns=saved['turns'][:1])
    monkeypatch.setattr(server, '_tries', {})
    server._resume(wait=0)
    assert next(e for e in store.history('ada', 'jotun') if e['id'] == identifier)['record']['depth'] == 'quick'


def test_a_run_that_stopped_early_continues_from_where_it_stopped_with_help(setup, monkeypatch):
    seen = []

    def stuck(url, messages, seed, max_tokens, schema=None, temperature=0, lora=None):  # always repeats itself
        seen.append(messages[-1]['content'])
        return {'text': '{"name": "read_brief", "arguments": {}}'}

    monkeypatch.setattr(server, '_model_ready', lambda: True)
    monkeypatch.setattr(server, '_loaded_adapters', lambda: ['final_adapter.gguf'])
    monkeypatch.setattr(server, 'chat', stuck)
    client = signed_in()
    identifier = client.post('/api/try', json={'workspace': 'jotun', 'case': 'jotun-base'}).json()['id']

    def wait():
        for _ in range(100):
            if client.get(f'/api/try/{identifier}').json()['status'] != 'running':
                return
            time.sleep(.05)

    wait()
    first = client.get(f'/api/workspaces/jotun/history/{identifier}').json()['record']
    assert first['stop_reason'] == 'repeated errors' and any('"help"' in m for m in seen)  # stuck help after two refusals
    assert client.post(f'/api/workspaces/jotun/history/{identifier}/continue').status_code == 200
    wait()
    again = client.get(f'/api/workspaces/jotun/history/{identifier}').json()['record']
    assert again['continued_after_turn'] == len(first['calls']) and len(again['calls']) > len(first['calls']) and again['continues'] == 1
    assert len([e for e in store.history('ada', 'jotun') if e['id'] == identifier]) == 1  # still one run


def test_attached_files_and_links_become_sources_the_agent_can_search_read_and_quote(setup, monkeypatch):
    import base64
    import io
    import zipfile

    import attachments as attach

    fact = 'Our pilot with 40 cycling clubs sold 1,200 zorblax earplugs in six weeks at full price.'
    docx = io.BytesIO()
    with zipfile.ZipFile(docx, 'w') as z:
        z.writestr('word/document.xml', f'<w:document><w:body><w:p><w:r><w:t>{fact}</w:t></w:r></w:p></w:body></w:document>')
    client = signed_in()
    up = client.post('/api/workspaces/jotun/attachments', json={'name': 'pilot.docx', 'data_base64': base64.b64encode(docx.getvalue()).decode()})
    assert up.status_code == 201 and up.json()['passages'] == 1
    assert client.post('/api/workspaces/jotun/attachments', json={'name': 'x.exe', 'data_base64': 'AAAA'}).status_code == 422
    monkeypatch.setattr('aemon.environment.live.LiveDossier._http', staticmethod(lambda url: '<title>Club survey</title><p>Most riders keep earplugs in for the whole ride. They want to hear traffic.</p>'))
    link = client.post('/api/workspaces/jotun/attachments', json={'url': 'https://example.org/survey'})
    assert link.status_code == 201 and link.json()['name'] == 'Club survey'
    assert [a['name'] for a in client.get('/api/workspaces/jotun/attachments').json()['attachments']] == ['Club survey', 'pilot.docx']
    assert signed_in('bob').post('/api/try', json={'workspace': 'jotun', 'case': 'jotun-base', 'attachments': [up.json()['id']]}).status_code == 404
    assert attach.passages('Too short.') == [] and len(attach.passages(' '.join(['A full sentence here.'] * 60))) >= 2

    turns = iter([
        '{"name": "read_brief", "arguments": {}}',
        '{"name": "frame_problem", "arguments": {"objective": "Decide", "constraints": ["budget"], "alternatives": ["enter", "do not enter"]}}',
        '{"name": "search_evidence", "arguments": {"query": "zorblax earplugs cycling clubs pilot"}}',
    ])
    briefs = []

    def scripted(url, messages, seed, max_tokens, schema=None, temperature=0, lora=None):
        briefs.append(messages[-1]['content'])
        try:
            return {'text': next(turns)}
        except StopIteration:  # read the first result it found, then repeat itself until the run stops
            found = [line for line in briefs if '"results"' in line][-1]
            first = json.loads(found.split('Latest tool result: ', 1)[1])['results'][0]['id']
            return {'text': json.dumps({'name': 'read_source', 'arguments': {'id': first}})}

    monkeypatch.setattr(server, '_model_ready', lambda: True)
    monkeypatch.setattr(server, '_loaded_adapters', lambda: ['final_adapter.gguf'])
    monkeypatch.setattr(server, 'chat', scripted)
    started = client.post('/api/try', json={'workspace': 'jotun', 'case': 'jotun-base', 'attachments': [up.json()['id']], 'context': 'We already sell to two bike shops.'})
    identifier = started.json()['id']
    for _ in range(100):
        if client.get(f'/api/try/{identifier}').json()['status'] != 'running':
            break
        time.sleep(.05)
    detail = client.get(f'/api/workspaces/jotun/history/{identifier}').json()
    mine = [s for s in detail['record']['sources'].values() if s['class'] == 'user_document']
    assert mine and mine[0]['excerpt'] == fact and mine[0]['title'].startswith('pilot.docx')
    assert any('We already sell to two bike shops.' in b and 'pilot.docx' in b for b in briefs)
    assert detail['settings']['context'] == 'We already sell to two bike shops.' and detail['settings']['attachments'][0]['name'] == 'pilot.docx'
    assert store._read('SELECT key FROM run_cache') == []  # a run with the person's own material is never saved for reuse


def test_asking_to_search_online_turns_web_search_on():
    assert server.asks_online('Please search online for cyclist earplug prices')
    assert server.asks_online('look it up on the web')
    assert server.asks_online('Can you check the internet for competitors?')
    assert not server.asks_online('Should Hellberg sell to cyclists?') and not server.asks_online('an online survey of riders')


def test_a_run_that_stops_early_still_ends_with_a_draft_answer_that_can_be_continued(setup, monkeypatch):
    def stuck_then_draft(url, messages, seed, max_tokens, schema=None, temperature=0, lora=None):
        if schema and 'would_change_if' in schema.get('properties', {}) and 'call' not in schema.get('properties', {}):
            return {'text': json.dumps({'recommendation': 'Run a small test before investing.', 'favoured_theory': 'none', 'next_action': 'Test with 50 buyers.',
                                        'uncertainty': 'Demand is unknown.', 'would_change_if': ['A test shows no demand.'], 'evidence_ids': ['none']})}
        return {'text': '{"name": "read_brief", "arguments": {}}'}

    monkeypatch.setattr(server, '_model_ready', lambda: True)
    monkeypatch.setattr(server, '_loaded_adapters', lambda: ['final_adapter.gguf'])
    monkeypatch.setattr(server, 'chat', stuck_then_draft)
    client = signed_in()
    identifier = client.post('/api/try', json={'workspace': 'jotun', 'case': 'jotun-base'}).json()['id']
    for _ in range(100):
        if client.get(f'/api/try/{identifier}').json()['status'] != 'running':
            break
        time.sleep(.05)
    detail = client.get(f'/api/workspaces/jotun/history/{identifier}').json()
    final = detail['record']['final']
    assert final['draft'] and final['recommendation'] == 'Run a small test before investing.' and final['evidence_ids'] == []
    assert final['stopped_because'].startswith('it got stuck') and detail['record']['stop_reason'] == 'repeated errors'
    entry = next(e for e in client.get('/api/workspaces/jotun/history').json()['entries'] if e['id'] == identifier)
    assert entry['status'] == 'finished' and entry['summary']['draft'] and not entry['summary']['finished']
    assert store._read('SELECT key FROM run_cache') == []  # a draft is never reused as a saved result
    assert client.post(f'/api/workspaces/jotun/history/{identifier}/continue').status_code == 200


def test_only_the_reviewer_reviews_and_the_decision_is_written_to_the_batch_file(setup, monkeypatch, tmp_path):
    folder = tmp_path / 'reviews' / 'v2_round9'
    folder.mkdir(parents=True)
    (folder / 'b_kept_for_review.json').write_text(json.dumps({'counts': {}, 'examples': [{'n': 1, 'keep': None}, {'n': 2, 'keep': None}]}))
    (folder / 'advisory_design.md').write_text('# advice')
    monkeypatch.setattr(server, 'REVIEWS', tmp_path / 'reviews')
    monkeypatch.setattr(server, 'REVIEWER', 'ada')
    client, other = signed_in(), signed_in('bob')
    assert other.get('/api/review').status_code == 404
    assert client.get('/api/review').json()['batches'][0]['batch'] == 'v2_round9/b_kept_for_review'
    assert client.patch('/api/review/v2_round9/b_kept_for_review/2', json={'keep': False, 'note': 'message-only test'}).status_code == 200
    saved = json.loads((folder / 'b_kept_for_review.json').read_text())['examples'][1]
    assert saved['keep'] is False and saved['review_note'] == 'message-only test' and saved['reviewed_by'] == 'ada'
    assert client.get('/api/review/v2_round9/b_kept_for_review').json()['advisory'] == {'design': '# advice'}
    assert other.patch('/api/review/v2_round9/b_kept_for_review/1', json={'keep': True}).status_code == 404


def test_a_hosted_copy_gets_its_shared_test_account_in_every_company(setup, monkeypatch):
    monkeypatch.setenv('AEMON_TEST_USER', 'judges')
    monkeypatch.setenv('AEMON_TEST_PASSWORD', 'a long test phrase')
    server._test_account()
    client = TestClient(server.app)
    assert client.get('/api/me').status_code == 401  # sign-in is still required
    assert client.post('/api/login', json={'name': 'judges'}).status_code == 200
    assert set(client.get('/api/me').json()['companies']) == set(server.WORKSPACES)
