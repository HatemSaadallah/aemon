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


import store  # noqa: E402
import users  # noqa: E402
from strategy_agent.agent.runner import COMPACT, PROMPTS, TOOL_SCHEMA, play, record_of  # noqa: E402
from strategy_agent.common.model_client import chat  # noqa: E402
from strategy_agent.common.types import Json, LoraSetting, Message, Schema  # noqa: E402
from strategy_agent.env.cases import load_cases  # noqa: E402
from strategy_agent.env.checks import guards_cleared  # noqa: E402
from strategy_agent.env.tools import Case, Investigation  # noqa: E402
from strategy_agent.pipeline.provenance import case_digest  # noqa: E402

RUNS = ROOT / 'reports' / 'strategy'
MODEL_URL = 'http://127.0.0.1:8091'
# Paired pilots: the same cases, controller, prompt and settings, and the only difference is the adapter.
# A pilot is shown once both of its reports exist. Add the next one here.
PILOTS = (
    {
        'id': 'final',
        'label': 'Final test',
        'files': {'untrained': '../judge/final/final_test_base_base.json', 'trained': '../judge/final/final_test_trained_adapter.json'},
        'arms': {'untrained': 'Base model (staged prompt)', 'trained': 'Fine-tuned'},
        'note': 'Run once on four companies never used for training or selection: 16 cases, three attempts each (one attempt per case is shown). The base model uses the staged prompt chosen on development data, the fine-tuned model the compact one. Blind judges: 1.48 against 0.65 (mean of two judges).',
    },
    {
        'id': 'pilot1',
        'label': 'First pilot',
        'files': {'untrained': 'pilot1/first_base.json', 'trained': 'pilot1/first_adapter.json'},
        'arms': {'untrained': 'Untrained', 'trained': 'First adapter'},
        'note': 'Full-history prompt in both arms; the only difference is the adapter. The adapter learned from 45 teacher investigations, and the checkpoint with the lowest Hellberg loss was kept.',
    },
    {
        'id': 'pilot2',
        'label': 'Second pilot',
        'files': {'untrained': 'pilot2/second_base.json', 'trained': 'pilot2/second_adapter.json'},
        'arms': {'untrained': 'Untrained', 'trained': 'Second adapter'},
        'note': 'Compact prompt in both arms, so the only difference is the adapter; it learned from the same 45 teacher investigations as the first, built compact so no rows were dropped.',
    },
)
ARMS = ('untrained', 'trained')
BANNER = (
    'The final test ran once on four companies never used for training or selection. The two pilots are earlier development runs on Moldex and '
    'Hellberg, where Hellberg chose the checkpoint, so it is not unseen. '
    'Checks are guards against mechanical mistakes, not measures of strategy quality.'
)

app = FastAPI(title='Strategy Lab', docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/static', StaticFiles(directory=Path(__file__).parent / 'static'), name='static')
# The React build (app/web, `npm run build`) when it exists; otherwise the plain pages in app/static.
DIST = Path(__file__).parent / 'web' / 'dist'
PAGE = DIST / 'index.html' if (DIST / 'index.html').is_file() else None
if PAGE is not None:
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')
_cache, _cases, _tries, _lock = {}, {}, {}, threading.Lock()

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


def report(relative: str) -> Json | None:
    """Reads a report once per version on disk."""
    path = RUNS / relative
    if not path.exists():
        return None
    stamp = path.stat().st_mtime_ns
    if _cache.get(relative, (None,))[0] != stamp:
        _cache[relative] = (stamp, json.loads(path.read_text()))
    return _cache[relative][1]


def pilot_reports(pilot: Json) -> dict[str, Json] | None:
    reports = {arm: report(pilot['files'][arm]) for arm in ARMS}
    present = {arm: data for arm, data in reports.items() if data is not None}
    return present if len(present) == len(reports) else None


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


def outcome(record: Json) -> Json:
    point = record['stopping_point']
    return {
        'stop_reason': record['stop_reason'],
        'finished': record['final'] is not None,
        'furthest': point['furthest_stage'],
        'stage_at_stop': point['stage_at_stop'],
        'calls': point['calls'],
        'refused': point['refused'],
        'guards_cleared': guards_cleared(record['checks']),
    }


def totals(data: Json) -> Json:
    records = data['records']
    return {
        'cases': len(records),
        'finished': sum(r['final'] is not None for r in records),
        'refused': sum(r['stopping_point']['refused'] for r in records),
        'mean_calls': round(sum(r['stopping_point']['calls'] for r in records) / max(len(records), 1), 1),
        'stop_reasons': data['summary']['stop_reasons'],
    }


@app.get('/')
def index() -> FileResponse:
    return FileResponse(PAGE or Path(__file__).parent / 'static' / 'index.html')


@app.get('/api/pilots')
def pilots() -> Json:
    shown = []
    for pilot in PILOTS:
        reports = pilot_reports(pilot)
        if reports is None:
            continue
        by_case = {arm: {r['case']: (i, r) for i, r in enumerate(reports[arm]['records'])} for arm in ARMS}
        rows = [
            {
                'case': case,
                'company': reports['untrained']['records'][by_case['untrained'][case][0]]['company'],
                **{arm: {'index': by_case[arm][case][0], **outcome(by_case[arm][case][1])} for arm in ARMS},
            }
            for case in by_case['untrained']
            if case in by_case['trained']
        ]
        shown.append(
            {
                'id': pilot['id'],
                'label': pilot['label'],
                'note': pilot['note'],
                'arms': pilot['arms'],
                'totals': {arm: totals(reports[arm]) for arm in ARMS},
                'cases': rows,
            }
        )
    return {'banner': BANNER, 'pilots': shown}


def belief_move(shock: Json) -> list[Any]:
    """Did the affected theory's own five-point belief move in the direction the what-if was written to push?
    Undermining evidence should not raise it, supporting evidence should not lower it, irrelevant evidence should leave
    it unchanged. A direction check only: a weak packet may rationally change nothing, so this is not a quality score."""
    from strategy_agent.env.tools import BELIEFS

    before, after = shock.get('beliefs_before'), shock.get('beliefs_after')
    rows = []
    for theory in shock.get('affected_theories') or []:
        b, a = (before or {}).get(theory), (after or {}).get(theory)
        if b is None or a is None:
            verdict = 'no belief after' if b is not None else 'no belief before'
        else:
            step = BELIEFS.index(a) - BELIEFS.index(b)
            verdict = {'undermines': step <= 0, 'supports': step >= 0, 'irrelevant': step == 0}.get(shock['direction'])
            verdict = 'consistent' if verdict else 'inconsistent'
        rows.append({'theory': theory, 'before': b, 'after': a, 'verdict': verdict})
    return rows


@app.get('/api/beliefs')
def beliefs() -> Json:
    """For every what-if case in the pilots: whether the run reached it, and how its own beliefs moved."""
    out = []
    for pilot in PILOTS:
        reports = pilot_reports(pilot)
        if reports is None:
            continue
        for arm in ARMS:
            rows = []
            for index, record in enumerate(reports[arm]['records']):
                shock = record['coverage'].get('shock')
                if not shock:
                    continue
                rows.append(
                    {
                        'case': record['case'],
                        'index': index,
                        'direction': shock['direction'],
                        'delivered': shock['delivered'],
                        'read': shock['read'],
                        'revisions': [[r['theory_id'], r['status']] for r in record['revisions']],
                        'moves': belief_move(shock),
                    }
                )
            out.append({'pilot': pilot['id'], 'pilot_label': pilot['label'], 'arm': arm, 'arm_label': pilot['arms'][arm], 'cases': rows})
    return {'scale': ['very unlikely', 'unlikely', 'uncertain', 'likely', 'very likely'], 'arms': out}


@app.get('/api/pilots/{pilot_id}/{arm}/{index}')
def pilot_episode(pilot_id: str, arm: str, index: int) -> dict[str, dict[str, Any]]:
    pilot = next((p for p in PILOTS if p['id'] == pilot_id), None)
    reports = pilot_reports(pilot) if pilot and arm in ARMS else None
    if reports is None:
        raise HTTPException(404, 'no such pilot')
    records = reports[arm]['records']
    if not 0 <= index < len(records):
        raise HTTPException(404, 'no such episode')
    return {'record': detail(records[index], cases()[records[index]['case']])}


LIVE = ROOT / 'reports' / 'live' / 'training.json'


@app.get('/api/training/live')
def training_live() -> Any | dict[str, None]:
    """A mirror of the cluster training log, kept current by scripts/training_feed.py."""
    return json.loads(LIVE.read_text()) if LIVE.exists() else {'state': None}


def _model_ready() -> Any | Literal[False]:
    try:
        with urllib.request.urlopen(MODEL_URL + '/health', timeout=2) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError):
        return False


# Each choice runs under the prompt its adapter was trained with. All share one server and one base model; a request
# switches every loaded adapter off except the chosen one, so the base weights and runtime are identical across choices.
MODELS = (
    {'id': 'untrained', 'label': 'Untrained Tiny Aya', 'adapter': None, 'prompt': 'compact'},
    {'id': 'second', 'label': 'Trained Tiny Aya, second adapter', 'adapter': 'second_adapter.gguf', 'prompt': 'compact'},
    {'id': 'first', 'label': 'Trained Tiny Aya, first adapter (full history)', 'adapter': 'first_adapter.gguf', 'prompt': 'staged'},
)


# The one model the page runs. Set from the latest paired evaluation; the others stay available to the backend.
LIVE_MODEL = os.environ.get('LIVE_MODEL', 'second')


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
    model: str | None = Field(default=None, pattern='^(untrained|trained|first|second)$')  # None runs LIVE_MODEL
    fresh: bool = False  # run live even if a saved result exists


def _run_attempt(identifier: str, case: Case, model: Json, loaded: list[str]) -> None:
    entry = _tries[identifier]
    lora = [{'id': i, 'scale': 1.0 if name == model['adapter'] else 0.0} for i, name in enumerate(loaded)]

    def respond(messages: list[Message], seed: int, max_tokens: int, schema: Schema | None, temperature: float, lora: LoraSetting = None) -> Json:
        return chat(MODEL_URL, messages, seed, max_tokens, schema, temperature, lora=lora)

    def on_turn(run: Investigation) -> None:
        entry['record'] = detail(record_of(run, {'stop_reason': None}), case)

    try:
        run, info = play(
            case,
            respond,
            PROMPTS[model['prompt']],
            45,
            4,
            520,
            True,
            TOOL_SCHEMA,
            staged=True,
            on_turn=on_turn,
            compact=model['prompt'] in COMPACT,
            route=(lambda stage: lora) if lora else None,
        )
        entry['record'] = detail(record_of(run, info), case)
        entry['status'] = 'finished'
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
        'model': {'id': live['id'], 'label': live['label'], 'available': live['adapter'] is None or live['adapter'] in loaded},
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
        out.append({k: e.get(k) for k in ('id', 'question', 'case', 'started', 'ended', 'summary', 'error', 'cached_at')} | {'status': status})
    return {'workspace': workspace, 'entries': out}


@app.get('/api/workspaces/{workspace}/history/{identifier}')
def workspace_run(workspace: str, identifier: str, request: Request) -> dict[str, Any]:
    _workspace_or_404(workspace, request.state.user)
    entry = next((e for e in _history(request.state.user, workspace) if e['id'] == identifier), None)
    if entry is None or not entry.get('record'):
        raise HTTPException(404, 'no such investigation')
    return {'record': entry['record']}


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
    bound = _cache_key(case, model)
    key, identity = bound if bound else (None, None)
    saved = store.cached(key) if key and not body.fresh else None
    if saved:  # a saved result, shown at once and labelled as saved, with the date it was made
        identifier = uuid.uuid4().hex
        record, created = saved
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
        _tries[identifier] = {
            'status': 'running',
            'record': None,
            'error': None,
            'model': model['id'],
            'model_label': model['label'],
            'user': user,
            'workspace': body.workspace,
            'cache_key': key,
            'identity': identity,
        }
    _record_history(user, body.workspace, identifier, question=shown, case=body.case, model=model['id'], started=time.time(), status='running')
    threading.Thread(target=_run_attempt, args=(identifier, case, model, loaded), daemon=True).start()
    return {'id': identifier}


@app.get('/api/try/{identifier}')
def try_result(identifier: str, request: Request) -> Json:
    entry = _tries.get(identifier)
    if entry is None or entry['user'] != request.state.user:
        raise HTTPException(404, 'no such attempt')
    return {k: v for k, v in entry.items() if k not in ('user', 'cache_key')}


_sync_companies()  # at import, before any request: the companies table and the demo memberships
