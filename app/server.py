"""Strategy Lab: try the agent, read the paired pilots, and follow training. Local only. Nothing here trains.

Model text is data. It is served as JSON and the page renders it as text, never as markup.
Every page and API route needs a signed-in user (accounts: app/users.py). Try it works inside one company workspace at
a time: a question there runs only on that company's own dossier, and each user keeps a chat history per company.
"""

import collections
import dataclasses
import json
import os
import re
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import Response

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))


import followup  # noqa: E402
import insights  # noqa: E402
import report as pdf_report  # noqa: E402
import store  # noqa: E402
import users  # noqa: E402
from strategy_agent.agent.runner import COMPACT, PROMPTS, TOOL_SCHEMA, play, record_of  # noqa: E402
from strategy_agent.common.model_client import chat  # noqa: E402
from strategy_agent.common.types import Json, LoraSetting, Message, Schema  # noqa: E402
from strategy_agent.env.cases import load_cases  # noqa: E402
from strategy_agent.env.checks import guards_cleared  # noqa: E402
from strategy_agent.env.tools import Case, Investigation  # noqa: E402
from strategy_agent.pipeline.provenance import case_digest  # noqa: E402

MODEL_URL = 'http://127.0.0.1:8091'

app = FastAPI(title='Strategy Lab', docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/static', StaticFiles(directory=Path(__file__).parent / 'static'), name='static')
# The React build (app/web, `npm run build`) when it exists; otherwise the plain pages in app/static.
DIST = Path(__file__).parent / 'web' / 'dist'
PAGE = DIST / 'index.html' if (DIST / 'index.html').is_file() else None
if PAGE is not None:
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')
_cases, _tries, _lock = {}, {}, threading.Lock()

# Sign-in. Sessions and chat history live in the SQLite store (app/store.py), so both survive a restart.
COOKIE = 'lexsi_session'
SESSION_SECONDS = 12 * 3600
FAILED_LIMIT, FAILED_WINDOW = 5, 60  # failed sign-ins per name per minute
OPEN = {'/login', '/api/login', '/static/style.css', '/static/login.js'}
_failures, _auth_lock = collections.defaultdict(collections.deque), threading.Lock()


def _user_of(request: Request) -> str | None:
    return store.session_user(request.cookies.get(COOKIE))


@app.middleware('http')
async def require_sign_in(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    if request.url.path in OPEN or (PAGE is not None and request.url.path.startswith('/assets/')):
        return await call_next(request)
    user = _user_of(request)
    if user is None:
        if request.url.path.startswith('/api/'):
            return JSONResponse({'detail': 'sign in first'}, status_code=401)
        return RedirectResponse('/login', status_code=303)
    request.state.user = user
    return await call_next(request)


class SignIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(max_length=64)
    password: str = Field(max_length=256)


@app.get('/login')
def login_page() -> FileResponse:
    return FileResponse(PAGE or Path(__file__).parent / 'static' / 'login.html')


@app.post('/api/login')
def login(body: SignIn) -> JSONResponse:
    name = body.name.strip().lower()
    now = time.time()
    with _auth_lock:
        recent = _failures[name]
        while recent and recent[0] < now - FAILED_WINDOW:
            recent.popleft()
        if len(recent) >= FAILED_LIMIT:
            raise HTTPException(429, 'too many failed sign-ins for this name; wait a minute')
    if not users.verify(name, body.password):
        with _auth_lock:
            _failures[name].append(now)
        raise HTTPException(401, 'wrong name or password')
    token = secrets.token_urlsafe(32)
    with _auth_lock:
        _failures.pop(name, None)
    store.start_session(token, name, now + SESSION_SECONDS)
    response = JSONResponse({'user': name})
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite='strict', secure=False, path='/')
    return response


@app.post('/api/logout')
def logout(request: Request) -> JSONResponse:
    store.end_session(request.cookies.get(COOKIE))
    response = JSONResponse({'signed_out': True})
    response.delete_cookie(COOKIE, path='/')
    return response


@app.get('/api/me')
def me(request: Request) -> dict[str, Any]:
    return {'user': request.state.user, 'companies': store.companies_of(request.state.user)}


def cases() -> Json:
    if not _cases:
        _cases.update({case.id: case for case in load_cases()})
        _cases.update({case.id: case for case in load_cases(split='heldout')})  # the final test's runs open here too
    return _cases


def source_of(case: Case, identifier: str) -> Json | None:
    record = case.shock if case.shock is not None and case.shock.id == identifier else case.dossier.records.get(identifier)
    if record is None:
        return None
    return {
        'id': record.id,
        'title': record.title,
        'class': record.type,
        'url': record.url if record.url.startswith(('http://', 'https://')) else None,
        'date': record.date,
        'excerpt': record.excerpt,
        'simulated': record.type == 'synthetic',
    }


def detail(record: Json, case: Case) -> dict[str, Any]:
    out = {k: v for k, v in record.items() if k != 'model_turns'}
    ids = {*record['read'], *(a['evidence_id'] for a in record['assessments'])}
    out['sources'] = {i: s for i in ids if (s := source_of(case, i))}
    out['question'] = case.question
    out['guards_cleared'] = guards_cleared(record['checks'])
    return out


@app.get('/')
def index() -> FileResponse:
    return FileResponse(PAGE or Path(__file__).parent / 'static' / 'index.html')


def _model_ready() -> Any | Literal[False]:
    try:
        with urllib.request.urlopen(MODEL_URL + '/health', timeout=2) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError):
        return False


# Each choice runs under the prompt its adapter was trained with. All share one server and one base model; a request
# switches every loaded adapter off except the chosen one, so the base weights and runtime are identical across choices.
MODELS = (
    {'id': 'final', 'label': 'Fine-tuned Tiny Aya (final adapter; 4-bit base on this laptop, the reported results used full precision)', 'adapter': 'final_adapter.gguf', 'prompt': 'compact'},
    {'id': 'untrained', 'label': 'Untrained Tiny Aya', 'adapter': None, 'prompt': 'staged'},
    {'id': 'second', 'label': 'Trained Tiny Aya, second adapter', 'adapter': 'second_adapter.gguf', 'prompt': 'compact'},
    {'id': 'first', 'label': 'Trained Tiny Aya, first adapter (full history)', 'adapter': 'first_adapter.gguf', 'prompt': 'staged'},
)


# The one model the page runs. Set from the latest paired evaluation; the others stay available to the backend.
LIVE_MODEL = os.environ.get('LIVE_MODEL', 'final')
# Try it refuses a third read of one source (its text is already in the state), which stops the rereading loop the
# evaluated harness allowed. A harness change, not a model one: set REREAD_LIMIT=0 to run as evaluated.
REREAD_LIMIT = int(os.environ.get('REREAD_LIMIT', '2')) or None
# Try it's turn budget; the evaluated runs used 45. Set MAX_TURNS=45 to run as evaluated.
MAX_TURNS = int(os.environ.get('MAX_TURNS', '60'))


def _loaded_adapters() -> list[str]:
    """File names of the adapters the server holds, in id order. Loaded, but not applied until a request asks."""
    try:
        with urllib.request.urlopen(MODEL_URL + '/lora-adapters', timeout=2) as response:
            return [Path(a['path']).name for a in sorted(json.load(response), key=lambda a: a['id'])]
    except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError):
        return []


def _adapter_loaded() -> bool:
    return bool(_loaded_adapters())


def _model(identifier: str) -> tuple[Json | dict[str, str], list[str] | list[Any]]:
    """'trained' means the newest adapter the server holds."""
    loaded = _loaded_adapters()
    if identifier == 'trained':
        identifier = next((m['id'] for m in MODELS if m['adapter'] in loaded), 'second')
    model = next(m for m in MODELS if m['id'] == identifier)
    return model, loaded


# Company workspaces: companies the current adapters never trained on (validation companies in src/strategy_agent/pipeline/splits.py).
WORKSPACES = ('hellberg', 'neumann', 'jotun', 'tanita', 'deere')
SHOCK_LABEL = {
    'undermines': 'simulated evidence against a theory',
    'supports': 'simulated evidence for a theory',
    'irrelevant': 'irrelevant simulated evidence',
}


def _scope(case_id: str) -> str:
    return case_id.split('-')[0]


def _first_sentence(text: str) -> str | Any:
    return re.split(r'(?<=[.!?])\s', text.strip(), maxsplit=1)[0]


# Plain-language starting questions per workspace. They add no fact the brief does not state: groups named after
# "such as" are suggestions for the agent to test, not claims about the company. The first runs the case's own
# question (so its date and framing stay exactly as written); the others run as free questions on the same dossier.
EXAMPLES = {
    'hellberg': [
        'Should Hellberg make hearing protection for a specific group of everyday users, and which group?',
        'Why do people skip hearing protection when they need it, and could a different product change that?',
        'Is there enough demand from individual buyers to justify a consumer product? What would a cheap first test look like?',
    ],
    'neumann': [
        'Should Neumann make a range for home-studio musicians and podcasters, or keep one professional range for everyone?',
        'Would a more affordable Neumann product for creators win new buyers, or weaken the brand with professionals?',
        'How much does Neumann already sell to individual creators, and what would show a separate range is worth it?',
    ],
    'jotun': [
        'It is mid-2024. Could Jotun turn its ship and industrial coatings know-how into a product for ordinary people?',
        'Which everyday users, such as boat owners or homeowners, have a problem that tough marine-grade coatings could solve?',
        'What is the cheapest way to test whether individual buyers would pay for a Jotun coating product?',
    ],
    'tanita': [
        'It is 1993. Should Tanita sell a body-fat analyser that people can use at home, not only in clinics and gyms?',
        'Who would want to track their body fat at home, and why would they pay for it?',
        'How could Tanita test demand for a home body-fat scale before investing in it?',
    ],
    'deere': [
        'It is 1962. Should Deere build a machine for individual buyers, using its tractor engineering?',
        'Which individual buyers, such as people with large gardens, would want a small Deere machine, and could its dealers sell it?',
        'What evidence would show that ordinary buyers want a Deere product, and how could that be tested cheaply?',
    ],
}

# What-if cases, in plain words. Every one is simulated evidence delivered mid-investigation, and the label says so.
SCENARIOS = {
    'hellberg-new-evidence-looks': 'Simulated test: a better-looking protector is worn no more often than a plain one. What changes?',
    'hellberg-new-evidence-comfort': 'Simulated test: a softer, better-fitting protector is worn no more often than the standard one. What changes?',
    'hellberg-new-evidence-favours-looks': 'Simulated test: a better-looking protector is worn far more often than a plain one. What changes?',
}
IRRELEVANT_SCENARIO = 'Simulated test about warehouse packing errors, unrelated to buyers. Does the agent rightly change nothing?'


def _examples(case: Case) -> list[str]:
    """Plain starting questions for the workspace; without curated ones, the case's own question and two rephrasings."""
    scope = _scope(case.id)
    if scope in EXAMPLES:
        return EXAMPLES[scope]
    question = re.sub(r'^It is [^.]*\.\s*', '', case.question.strip())
    name = re.sub(r'\s*\([^)]*\)', '', case.company).strip()
    return [
        question,
        f'Should {name} offer a product to individual buyers, or stay with the customers it serves now? What would you need to find out first?',
        f'What evidence would show whether a consumer proposition from {name} is worth testing, and what would that test look like?',
    ]


def _scenario_label(case: Case) -> str:
    """A what-if case in plain words, always marked simulated."""
    if case.id in SCENARIOS:
        return SCENARIOS[case.id]
    if case.shock_direction == 'irrelevant':
        return IRRELEVANT_SCENARIO
    label = f'What if: {SHOCK_LABEL.get(case.shock_direction, "simulated evidence")}'
    topic = case.id.split('new-evidence-', 1)[-1].replace('favours-', '')
    return f'{label}, about {topic.replace("-", " ")}'


def workspaces() -> list[Any]:
    out = []
    for scope in WORKSPACES:
        own = sorted((c for c in cases().values() if _scope(c.id) == scope), key=lambda c: (c.shock is not None, c.id))
        if not own:
            continue
        base = own[0]
        out.append(
            {
                'id': scope,
                'company': base.company,
                'description': _first_sentence(base.brief),
                'base_case': base.id,
                'examples': _examples(base),
                'scenarios': [{'case': c.id, 'label': _scenario_label(c), 'question': c.question} for c in own if c.shock is not None],
            }
        )
    return out


def _history(user: str, workspace: str) -> list[dict[str, Any]]:
    return store.history(user, workspace)


def _record_history(user: str, workspace: str, identifier: str, **fields: object) -> None:
    """One entry per investigation, written when it starts and again when it ends, so a restart loses nothing."""
    store.record(user, workspace, identifier, **fields)


CODE_REVISION = os.environ.get('CODE_REVISION') or (os.popen(f'git -C {ROOT} rev-parse --short HEAD 2>/dev/null').read().strip() or 'unknown')
ADAPTERS = Path.home() / '.cache' / 'lexsi' / 'adapters'


_HASHES: dict[tuple[str, int, int], str] = {}


def _file_sha256(path: Path) -> str:
    """The adapter's contents, hashed once per file version."""
    import hashlib

    stat = path.stat()
    marker = (str(path), stat.st_size, stat.st_mtime_ns)
    if marker not in _HASHES:
        digest = hashlib.sha256()
        with open(path, 'rb') as handle:
            for block in iter(lambda: handle.read(1 << 20), b''):
                digest.update(block)
        _HASHES[marker] = digest.hexdigest()
    return _HASHES[marker]


def _served_identity(model: Json) -> Json | None:
    """What the model server actually holds: base model file, llama.cpp build, context and default generation settings,
    and the content hash of the adapter it loaded for this choice. None when any of it cannot be read."""
    try:
        with urllib.request.urlopen(MODEL_URL + '/props', timeout=2) as response:
            props = json.load(response)
        with urllib.request.urlopen(MODEL_URL + '/lora-adapters', timeout=2) as response:
            adapters = {Path(a['path']).name: Path(a['path']) for a in json.load(response)}
    except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError):
        return None
    adapter = None
    if model['adapter']:
        path = adapters.get(model['adapter'])
        if path is None or not path.exists():
            return None
        adapter = [model['adapter'], _file_sha256(path)]
    settings = props.get('default_generation_settings') or {}
    return {
        'base': props.get('model_path'),
        'build': props.get('build_info'),
        'context': settings.get('n_ctx'),
        'adapter': adapter,
        'prompt': model['prompt'],
        'code': CODE_REVISION,
    }


def _cache_key(case: Case, model: Json) -> tuple[str, Json] | None:
    """A finished run is reused only for the same case and evidence (its provenance digest, budgets included), the same
    model choice and prompt, the adapter contents and base model the server actually holds, the runtime build and
    context, and the same code. If any identity cannot be read, nothing is reused."""
    import hashlib

    served = _served_identity(model)
    if served is None:
        return None
    identity = {
        'case': case.id,
        'case_digest': case_digest(case),
        'budgets': [case.search_budget, case.test_budget, case.max_test_weeks],
        'model': model['id'],
        **served,
    }
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest(), identity


def _summary(record: Json) -> Json:
    final, point = record.get('final'), record.get('stopping_point') or {}
    return {
        'stop_reason': record.get('stop_reason'),
        'finished': final is not None,
        'calls': len(record.get('calls', [])),
        'refused': sum(not c['accepted'] for c in record.get('calls', [])),
        'stage_at_stop': point.get('stage_at_stop'),
        'recommendation': (final or {}).get('recommendation'),
        'position': (record.get('position') or {}).get('recommendation'),
    }


class Attempt(BaseModel):
    model_config = ConfigDict(extra='forbid')
    workspace: str = Field(max_length=40)
    case: str = Field(max_length=80)
    question: str | None = Field(default=None, max_length=400)
    shown: str | None = Field(default=None, max_length=400)  # the words the person clicked, kept in their history
    model: str | None = Field(default=None, pattern='^(untrained|trained|first|second|final)$')  # None runs LIVE_MODEL
    fresh: bool = False  # run live even if a saved result exists
    live_research: bool = False  # search the web (snapshotted) instead of the fixed dossier; never part of an evaluation
    project: str | None = Field(default=None, max_length=40)  # start it inside a project: that project's memory applies


def _run_attempt(identifier: str, case: Case, model: Json, loaded: list[str]) -> None:
    entry = _tries[identifier]
    lora = [{'id': i, 'scale': 1.0 if name == model['adapter'] else 0.0} for i, name in enumerate(loaded)]

    def respond(messages: list[Message], seed: int, max_tokens: int, schema: Schema | None, temperature: float, lora: LoraSetting = None) -> Json:
        return chat(MODEL_URL, messages, seed, max_tokens, schema, temperature, lora=lora)

    def on_turn(run: Investigation) -> None:
        entry['record'] = detail(record_of(run, {'stop_reason': None}), case)
        if entry.get('stop'):
            raise Stopped

    try:
        run, info = play(
            case,
            respond,
            PROMPTS[model['prompt']],
            MAX_TURNS,
            4,
            520,
            True,
            TOOL_SCHEMA,
            staged=True,
            on_turn=on_turn,
            compact=model['prompt'] in COMPACT,
            reread_limit=REREAD_LIMIT,
            route=(lambda stage: lora) if lora else None,
        )
        entry['record'] = {**detail(record_of(run, info), case), 'memory_used': entry.get('memory_used') or []}
        entry['status'] = 'finished'
    except Stopped:
        entry['status'], entry['error'] = 'stopped', 'stopped by you'
        if entry['record']:
            entry['record'] = {**entry['record'], 'stop_reason': 'stopped by you', 'memory_used': entry.get('memory_used') or []}
    except Exception as error:  # noqa: BLE001  shown to the person watching, not swallowed
        entry['status'], entry['error'] = 'failed', f'{type(error).__name__}: {error}'
    record = entry['record']
    if entry['status'] == 'finished' and record and entry.get('cache_key'):  # never a failed or interrupted run
        store.save_run(entry['cache_key'], {**record, 'generated_by': entry.get('identity')})
    _record_history(
        entry['user'],
        entry['workspace'],
        identifier,
        status=entry['status'],
        error=entry['error'],
        ended=time.time(),
        summary=_summary(record) if record else None,
        record=record,
    )


@app.get('/api/workflow')
def workflow() -> Json:
    """The stage controller for people: stages in order, the tools each opens, and what moves it on. It is the same
    table the tests check against the controller, and the tool descriptions are the ones the model is given."""
    from strategy_agent.env.stages import WORKFLOW
    from strategy_agent.env.tools import POSITION_SIGNATURE, TOOL_SIGNATURES

    tools = {}
    for line in (TOOL_SIGNATURES + '\n' + POSITION_SIGNATURE).splitlines():
        name, _, rest = line.partition(' ')
        if name and ' : ' in rest:
            tools[name] = rest.rsplit(' : ', 1)[1].strip()
    return {'stages': [dict(w, tools=list(w['tools'])) for w in WORKFLOW], 'tools': tools}


@app.get('/api/try')
def try_status() -> Json:
    loaded = _loaded_adapters()
    live = next(m for m in MODELS if m['id'] == LIVE_MODEL)
    return {
        'model_ready': _model_ready(),
        'adapter_loaded': bool(loaded),
        'model': {
            'id': live['id'],
            'label': live['label']
            + ('. A third read of one source is refused here, unlike the evaluated setup' if REREAD_LIMIT else '')
            + (f'. Up to {MAX_TURNS} steps here (the evaluated runs had 45)' if MAX_TURNS != 45 else ''),
            'available': live['adapter'] is None or live['adapter'] in loaded,
        },
        'busy': any(t['status'] == 'running' for t in _tries.values()),
    }


# The company an account joins when it belongs to none, so the demo shows one company (LEXSI_DEMO_COMPANY overrides it).
DEMO_COMPANY = os.environ.get('LEXSI_DEMO_COMPANY', 'hellberg')


def _sync_companies() -> None:
    """The companies table holds every workspace in the dossier; an account in no company joins the demo one."""
    for w in workspaces():
        store.put_company(w['id'], w['company'])
    store.give_default_membership(DEMO_COMPANY)


@app.get('/api/workspaces')
def list_workspaces(request: Request) -> dict[str, list[Any]]:
    """Only the companies the signed-in account is a member of, in the order it joined them."""
    own = store.companies_of(request.state.user)
    by_id = {w['id']: w for w in workspaces()}
    return {'workspaces': [by_id[c] for c in own if c in by_id]}


def _workspace_or_404(workspace: str, user: str) -> None:
    """An account sees only companies it is a member of: any other workspace is answered as if it did not exist."""
    if workspace not in WORKSPACES or not any(_scope(c) == workspace for c in cases()) or workspace not in store.companies_of(user):
        raise HTTPException(404, 'no such workspace')


@app.get('/api/workspaces/{workspace}/history')
def workspace_history(workspace: str, request: Request) -> Json:
    """Earlier investigations in this workspace, newest last, without their full trees. A run left running by a
    restart is shown as interrupted."""
    _workspace_or_404(workspace, request.state.user)
    out = []
    for e in _history(request.state.user, workspace):
        status = e.get('status')
        if status == 'running' and e['id'] not in _tries:
            status = 'interrupted'
        out.append({k: e.get(k) for k in ('id', 'question', 'case', 'started', 'ended', 'summary', 'error', 'cached_at', 'pinned', 'project')} | {'status': status})
    return {'workspace': workspace, 'entries': out, 'projects': store.projects(request.state.user, workspace)}


@app.get('/api/workspaces/{workspace}/history/{identifier}')
def workspace_run(workspace: str, identifier: str, request: Request) -> dict[str, Any]:
    _workspace_or_404(workspace, request.state.user)
    entry = next((e for e in _history(request.state.user, workspace) if e['id'] == identifier), None)
    if entry is None or not entry.get('record'):
        raise HTTPException(404, 'no such investigation')
    record = entry['record']
    return {
        'record': record,
        'metrics': _metrics(record),
        'suggestions': insights.suggestions(record) if record.get('final') or record.get('theories') else [],
        'followups': store.followups(request.state.user, workspace, identifier),
        'memory_used': record.get('memory_used') or [],
    }


def _metrics(record: Json) -> Json:
    case = cases().get(record.get('case') or '')
    return insights.metrics(record, case.test_budget if case else None, case.max_test_weeks if case else None)


def _entry_or_404(workspace: str, identifier: str, user: str) -> Json:
    _workspace_or_404(workspace, user)
    entry = next((e for e in _history(user, workspace) if e['id'] == identifier), None)
    if entry is None or not entry.get('record'):
        raise HTTPException(404, 'no such investigation')
    return entry


class FollowUp(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=2, max_length=500)


def _notes(user: str, project: str | None, workspace: str | None = None) -> list[str]:
    if store.setting(user, 'memory', 'on') != 'on':
        return []
    return [m['text'] for m in store.memories(user, project, workspace=workspace)]


def _answer_followup(item_id: str, record: Json, question: str, notes: list[str], earlier: list[Json]) -> None:
    try:
        text, cited, status = followup.answer(chat, MODEL_URL, record, question, notes, earlier, len(_loaded_adapters()))
    except Exception as error:  # noqa: BLE001  shown to the person instead of a silent failure
        text, cited, status = f'The model could not answer just now ({type(error).__name__}). Try again in a moment.', [], 'failed'
    store.finish_followup(item_id, text, cited, status)


@app.post('/api/workspaces/{workspace}/history/{identifier}/followups', status_code=201)
def ask_followup(workspace: str, identifier: str, body: FollowUp, request: Request) -> Json:
    """A question about a finished investigation, answered from its record by the local model."""
    user = request.state.user
    entry = _entry_or_404(workspace, identifier, user)
    if not _model_ready():
        raise HTTPException(503, 'the model server is not running')
    earlier = store.followups(user, workspace, identifier)
    if any(f['status'] == 'answering' for f in earlier):
        raise HTTPException(409, 'still answering the last question')
    item = store.add_followup(user, workspace, identifier, body.question.strip())
    threading.Thread(target=_answer_followup, args=(item['id'], entry['record'], item['question'], _notes(user, entry.get('project'), workspace), earlier), daemon=True).start()
    return item


@app.get('/api/workspaces/{workspace}/history/{identifier}/followups')
def list_followups(workspace: str, identifier: str, request: Request) -> Json:
    _entry_or_404(workspace, identifier, request.state.user)
    return {'followups': store.followups(request.state.user, workspace, identifier)}


@app.get('/api/workspaces/{workspace}/history/{identifier}/report.pdf')
def investigation_report(workspace: str, identifier: str, request: Request) -> Response:
    """A PDF report of one investigation: summary first, then explanations, evidence, test, follow-ups and sources."""
    user = request.state.user
    entry = _entry_or_404(workspace, identifier, user)
    company = next((w['company'] for w in workspaces() if w['id'] == workspace), workspace)
    page = pdf_report.build(entry['record'], _metrics(entry['record']), company, entry.get('question') or entry['record'].get('question', ''),
                        store.followups(user, workspace, identifier), entry.get('ended'))
    try:
        data = pdf_report.pdf(page)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(503, f'the report could not be printed: {error}') from error
    name = re.sub(r'[^A-Za-z0-9]+', '-', (entry.get('question') or 'investigation'))[:60].strip('-') or 'investigation'
    return Response(data, media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="{name}.pdf"'})


@app.get('/api/workspaces/{workspace}/mindmap')
def mind_map(workspace: str, request: Request) -> Json:
    """Every investigation in this workspace as a tree: company, projects, investigations, explanations, evidence."""
    user = request.state.user
    _workspace_or_404(workspace, user)
    company = next((w['company'] for w in workspaces() if w['id'] == workspace), workspace)
    groups = {p['id']: {'id': f"p-{p['id']}", 'kind': 'project', 'label': p['name'], 'children': []} for p in store.projects(user, workspace)}
    loose = {'id': 'p-none', 'kind': 'project', 'label': 'Not in a project', 'children': []}
    for e in reversed(_history(user, workspace)):
        record = e.get('record') or {}
        final = record.get('final') or {}
        m = _metrics(record) if record else None
        node = {
            'id': e['id'], 'kind': 'investigation', 'label': e.get('question') or record.get('question') or 'Investigation',
            'status': 'finished' if final else (e.get('status') or 'stopped'), 'pinned': bool(e.get('pinned')),
            'detail': final.get('recommendation') or '', 'started': e.get('started'), 'children': [],
        }
        for b in (m or {}).get('beliefs', []):
            ev = next((r for r in m['evidence'] if r['id'] == b['id']), {})
            theory = {'id': f"{e['id']}-{b['id']}", 'kind': 'explanation', 'label': b['claim'], 'belief': b['after'] or b['before'],
                      'favoured': b['favoured'], 'supports': ev.get('supports', 0), 'contradicts': ev.get('contradicts', 0), 'children': []}
            for a in (record.get('assessments') or []):
                if a.get('theory_id') == b['id'] and a.get('direction') in ('supports', 'contradicts') and len(theory['children']) < 3:
                    source = (record.get('sources') or {}).get(a.get('evidence_id')) or {}
                    theory['children'].append({'id': f"{e['id']}-{b['id']}-{len(theory['children'])}", 'kind': 'evidence', 'label': a.get('quote', ''),
                                               'direction': a['direction'], 'detail': source.get('title') or a.get('evidence_id'), 'children': []})
            node['children'].append(theory)
        (groups.get(e.get('project')) or loose)['children'].append(node)
    children = [g for g in groups.values()] + ([loose] if loose['children'] else [])
    return {'id': 'root', 'kind': 'company', 'label': company, 'children': children}


class MemoryNote(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=2, max_length=400)
    project: str | None = Field(default=None, max_length=40)
    workspace: str | None = Field(default=None, max_length=40)


class MemoryEdit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=2, max_length=400)


class MemorySwitch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool


def _own_project(user: str, workspace: str | None, project: str | None) -> None:
    if project is None:
        return
    if workspace is None:
        raise HTTPException(422, 'a project memory needs its workspace')
    _workspace_or_404(workspace, user)
    if project not in {p['id'] for p in store.projects(user, workspace)}:
        raise HTTPException(404, 'no such project')


@app.get('/api/memory')
def memory(request: Request, workspace: str | None = None, project: str | None = None) -> Json:
    """Global notes, and a project's notes when one is named. Memory can be switched off; notes are then kept but unused."""
    user = request.state.user
    _own_project(user, workspace, project)
    if workspace:
        _workspace_or_404(workspace, user)
    return {
        'enabled': store.setting(user, 'memory', 'on') == 'on',
        'global': store.memories(user),
        'company': store.memories(user, workspace=workspace, include_global=False, company_only=True) if workspace else [],
        'project': store.memories(user, project, include_global=False) if project else [],
        'limit': MEMORY_LIMIT,
    }


MEMORY_LIMIT = 40  # notes per account, so memory never fails silently when full


@app.post('/api/memory', status_code=201)
def remember(body: MemoryNote, request: Request) -> Json:
    _own_project(request.state.user, body.workspace, body.project)
    if body.workspace:
        _workspace_or_404(body.workspace, request.state.user)
    if store.memory_count(request.state.user) >= MEMORY_LIMIT:
        raise HTTPException(409, f'memory is full ({MEMORY_LIMIT} notes): remove one to add another')
    return store.add_memory(request.state.user, body.text.strip(), body.project, body.workspace)


@app.patch('/api/memory/settings')
def memory_switch(body: MemorySwitch, request: Request) -> Json:
    store.set_setting(request.state.user, 'memory', 'on' if body.enabled else 'off')
    return {'enabled': body.enabled}


@app.patch('/api/memory/{identifier}')
def edit_memory(identifier: str, body: MemoryEdit, request: Request) -> Json:
    if not store.update_memory(request.state.user, identifier, body.text.strip()):
        raise HTTPException(404, 'no such memory')
    return {'id': identifier, 'text': body.text.strip()}


@app.delete('/api/memory/{identifier}')
def forget(identifier: str, request: Request) -> Json:
    if not store.delete_memory(request.state.user, identifier):
        raise HTTPException(404, 'no such memory')
    return {'deleted': identifier}


class HistoryChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pinned: bool | None = None
    project: str | None = Field(default=None, max_length=40)
    clear_project: bool = False  # move it out of its project, back to the main history


class ProjectName(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=80)


@app.delete('/api/workspaces/{workspace}/history/{identifier}')
def delete_history_entry(workspace: str, identifier: str, request: Request) -> Json:
    """Removes one investigation from this person's history. A running one is left alone until it ends."""
    _workspace_or_404(workspace, request.state.user)
    entry = _tries.get(identifier)
    if entry is not None and entry['status'] == 'running':
        raise HTTPException(409, 'that investigation is still running')
    if not store.delete_history(request.state.user, workspace, identifier):
        raise HTTPException(404, 'no such investigation')
    with _lock:
        _tries.pop(identifier, None)
    return {'deleted': identifier}


@app.patch('/api/workspaces/{workspace}/history/{identifier}')
def change_history_entry(workspace: str, identifier: str, body: HistoryChange, request: Request) -> Json:
    _workspace_or_404(workspace, request.state.user)
    user = request.state.user
    fields: dict[str, object] = {}
    if body.pinned is not None:
        fields['pinned'] = body.pinned
    if body.clear_project:
        fields['project'] = None
    elif body.project is not None:
        if body.project not in {p['id'] for p in store.projects(user, workspace)}:
            raise HTTPException(404, 'no such project')
        fields['project'] = body.project
    if not fields or not store.update_history(user, workspace, identifier, **fields):
        raise HTTPException(404, 'no such investigation')
    return {'id': identifier, **fields}


@app.get('/api/workspaces/{workspace}/projects')
def list_projects(workspace: str, request: Request) -> Json:
    _workspace_or_404(workspace, request.state.user)
    return {'projects': store.projects(request.state.user, workspace)}


@app.post('/api/workspaces/{workspace}/projects', status_code=201)
def new_project(workspace: str, body: ProjectName, request: Request) -> Json:
    _workspace_or_404(workspace, request.state.user)
    return store.create_project(request.state.user, workspace, body.name.strip())


@app.patch('/api/workspaces/{workspace}/projects/{project}')
def rename_project(workspace: str, project: str, body: ProjectName, request: Request) -> Json:
    _workspace_or_404(workspace, request.state.user)
    if not store.rename_project(request.state.user, workspace, project, body.name.strip()):
        raise HTTPException(404, 'no such project')
    return {'id': project, 'name': body.name.strip()}


@app.delete('/api/workspaces/{workspace}/projects/{project}')
def remove_project(workspace: str, project: str, request: Request) -> Json:
    """Deletes the project; its investigations stay, back in the main history."""
    _workspace_or_404(workspace, request.state.user)
    if not store.delete_project(request.state.user, workspace, project):
        raise HTTPException(404, 'no such project')
    return {'deleted': project}


@app.post('/api/try', status_code=201)
def start_try(body: Attempt, request: Request) -> Json:
    _workspace_or_404(body.workspace, request.state.user)
    if body.case not in cases():
        raise HTTPException(404, 'no such case')
    if _scope(body.case) != body.workspace:  # a workspace only ever runs on its own company's dossier
        raise HTTPException(403, 'that case belongs to another company')
    model, loaded = _model(body.model or LIVE_MODEL)
    case = cases()[body.case]
    if body.question and body.question.strip():
        case = dataclasses.replace(case, question=body.question.strip())
    user, shown = request.state.user, (body.shown or '').strip() or case.question
    if body.project is not None and body.project not in {p['id'] for p in store.projects(user, body.workspace)}:
        raise HTTPException(404, 'no such project')
    notes = _notes(user, body.project, body.workspace)
    if notes:  # memory, as context in the brief; it changes the case, so a saved run without it is never reused
        case = dataclasses.replace(case, brief=case.brief + '\n\nNotes from the person asking (their context, not evidence; never quote them): ' + ' '.join(f'({i + 1}) {n}' for i, n in enumerate(notes)))
    bound = _cache_key(case, model)
    key, identity = bound if bound else (None, None)
    saved = store.cached(key) if key and not body.fresh and not body.live_research else None
    if saved:  # a saved result, shown at once and labelled as saved, with the date it was made
        identifier = uuid.uuid4().hex
        record, created = saved
        record = {**record, 'memory_used': notes}
        with _lock:
            _tries[identifier] = {
                'status': 'finished',
                'record': record,
                'error': None,
                'model': model['id'],
                'model_label': model['label'],
                'user': user,
                'workspace': body.workspace,
                'cached_at': created,
                'identity': record.get('generated_by'),
            }
        _record_history(
            user,
            body.workspace,
            identifier,
            question=shown,
            case=body.case,
            model=model['id'],
            started=time.time(),
            ended=time.time(),
            status='finished',
            summary=_summary(record),
            record=record,
            cached_at=created,
            project=body.project,
        )
        return {'id': identifier, 'cached_at': created}
    if not _model_ready():
        raise HTTPException(503, 'the model server is not running')
    if model['adapter'] and model['adapter'] not in loaded:
        raise HTTPException(409, f'{model["label"]} is not loaded on the model server')
    with _lock:
        if any(t['status'] == 'running' for t in _tries.values()):
            raise HTTPException(409, 'an investigation is already running')
        identifier = uuid.uuid4().hex
        if body.live_research:  # the fixed dossier is swapped for live web search, every page saved as a snapshot
            from strategy_agent.env.live import LiveDossier

            case = dataclasses.replace(case, dossier=LiveDossier(case.company, store.folder() / 'live_snapshots' / identifier))
        _tries[identifier] = {
            'status': 'running',
            'record': None,
            'error': None,
            'live_research': body.live_research,
            'model': model['id'],
            'model_label': model['label'] + (' · live web research (snapshotted; not part of the evaluated setup)' if body.live_research else ''),
            'user': user,
            'workspace': body.workspace,
            'cache_key': None if body.live_research else key,
            'identity': identity,
            'memory_used': notes,
        }
    _record_history(user, body.workspace, identifier, question=shown + (' (live web)' if body.live_research else ''), case=body.case, model=model['id'], started=time.time(), status='running', project=body.project)
    threading.Thread(target=_run_attempt, args=(identifier, case, model, loaded), daemon=True).start()
    return {'id': identifier}


class Stopped(Exception):
    """Raised between turns when the person stops an investigation."""


@app.post('/api/try/{identifier}/stop')
def stop_try(identifier: str, request: Request) -> Json:
    entry = _tries.get(identifier)
    if entry is None or entry['user'] != request.state.user:
        raise HTTPException(404, 'no such attempt')
    if entry['status'] == 'running':
        entry['stop'] = True
    return {'id': identifier, 'stopping': entry['status'] == 'running'}


@app.get('/api/try/{identifier}')
def try_result(identifier: str, request: Request) -> Json:
    entry = _tries.get(identifier)
    if entry is None or entry['user'] != request.state.user:
        raise HTTPException(404, 'no such attempt')
    return {k: v for k, v in entry.items() if k not in ('user', 'cache_key', 'stop')}


_sync_companies()  # at import, before any request: the companies table and the demo memberships
