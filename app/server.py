"""Aemon: try the agent, read the paired pilots, and follow training. Local only. Nothing here trains.

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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import Response

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))


import attachments as attach  # noqa: E402
import companies  # noqa: E402
import followup  # noqa: E402
import insights  # noqa: E402
import report as pdf_report  # noqa: E402
import store  # noqa: E402
import users  # noqa: E402
import wrapup  # noqa: E402
from aemon.evaluation.diagnostics.rescore import rebuild
from aemon.agent.experimental import verify
from aemon.agent.loop import play
from aemon.agent.records import record_of
from aemon.agent.state_view import with_status
from aemon.agent.tool_schemas import TOOL_SCHEMA
from aemon.common.constants.prompts import COMPACT, PROMPTS
from aemon.agent.backends.llama_client import chat  # noqa: E402
from aemon.common.types import Json, LoraSetting, Message, Schema  # noqa: E402
from aemon.environment.cases import load_cases  # noqa: E402
from aemon.environment.checks import guards_cleared  # noqa: E402
from aemon.environment.tools import Case, Investigation  # noqa: E402
from aemon.rows.provenance import case_digest  # noqa: E402

MODEL_URL = 'http://127.0.0.1:8091'

app = FastAPI(title='Aemon', docs_url=None, redoc_url=None, openapi_url=None)
# The React build (app/web, `npm run build`; app/run.sh builds it on first start)
DIST = Path(__file__).parent / 'web' / 'dist'
NO_CACHE = {'Cache-Control': 'no-cache'}  # the page names the current build's files, so a refresh always gets the new build
PAGE = DIST / 'index.html' if (DIST / 'index.html').is_file() else None
if PAGE is not None:
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')
    if (DIST / 'brand').is_dir():  # licensed company logos and banners (app/profiles/company_profiles.json records their provenance)
        app.mount('/brand', StaticFiles(directory=DIST / 'brand'), name='brand')
NO_BUILD = '<p>The interface is not built yet: run <code>npm --prefix app/web ci && npm --prefix app/web run build</code>, or start the app with <code>./app/run.sh</code> (it needs Node).</p>'
_cases, _tries, _lock = {}, {}, threading.Lock()

# Sign-in. Sessions and chat history live in the SQLite store (app/store.py), so both survive a restart.
COOKIE = 'lexsi_session'
SESSION_SECONDS = 12 * 3600
FAILED_LIMIT, FAILED_WINDOW = 5, 60  # failed sign-ins per name per minute
OPEN = {'/login', '/api/login'}
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
def login_page() -> Response:
    return FileResponse(PAGE, headers=NO_CACHE) if PAGE else HTMLResponse(NO_BUILD, status_code=503)


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
    # A finished answer whose numbers or test fail the checks is flagged on its report (docs/RECOVERY_REPORT.md): the
    # finish-on-time guard made these failures more common, so a run with the guard on says so in the flag.
    checks = record.get('checks') or {}
    out['answer_flags'] = [{'check': k, 'label': ANSWER_FLAGS[k], 'detail': checks[k].get('detail')} for k in ANSWER_FLAGS
                           if record.get('final') and (checks.get(k) or {}).get('passed') is False]
    out['finish_guard'] = 'budget' in ((record.get('settings') or {}).get('recovery') or [])
    if record.get('final'):  # the evidence checks of docs/VERIFY_EVAL_PLAN.md, shown to the reader; the run is not changed
        try:
            run = rebuild({**record, 'settings': {k: v for k, v in (record.get('settings') or {}).items() if k != 'recovery'}}, {case.id: case})
            out['answer_flags'] += [{'check': f'evidence_{f["kind"]}', 'label': EVIDENCE_FLAGS[f['kind']], 'detail': f['text']}
                                    for f in verify.findings(run, record['final'])]
        except Exception:  # noqa: BLE001  a record the tools cannot replay keeps its other flags
            pass
    return out


EVIDENCE_FLAGS = {
    'late': 'Cites a source published after the date the case is set',
    'numbers': 'Some numbers are in no source the answer cites',
    'support': 'No cited source was weighed as supporting the favoured theory',
    'company': "The favoured theory rests only on the company's own claims",
    'offering': 'The investigation never read what the company already sells to these customers',
}


ANSWER_FLAGS = {
    'no_invented_numbers': 'Some numbers in this answer come from no source it read',
    'experiment': 'The proposed test (or the decision to skip one) did not pass the experiment check',
}


@app.get('/')
def index() -> Response:
    return FileResponse(PAGE, headers=NO_CACHE) if PAGE else HTMLResponse(NO_BUILD, status_code=503)


def _model_ready() -> Any | Literal[False]:
    try:
        with urllib.request.urlopen(MODEL_URL + '/health', timeout=2) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError):
        return False


# Each choice runs under the prompt its adapter was trained with. All share one server and one base model; a request
# switches every loaded adapter off except the chosen one, so the base weights and runtime are identical across choices.
# 'system' is two adapters in one run (DECISIONS 2026-11-11): 'adapter' (version 1) writes the stages in DIG_STAGES,
# 'reasoner' (version 3) every later one, with the company status check on.
DIG_STAGES = ('brief', 'frame', 'status', 'status_reading', 'evidence')
MODELS = (
    {'id': 'system', 'label': 'aemon: version 1 gathers the evidence, version 3 reasons, with a company status check (4-bit base on this laptop)',
     'adapter': 'final_adapter.gguf', 'reasoner': 'v3_adapter.gguf', 'status_check': True, 'prompt': 'compact'},
    {'id': 'final', 'label': 'Fine-tuned Tiny Aya (final adapter; 4-bit base on this laptop, the reported results used full precision)', 'adapter': 'final_adapter.gguf', 'prompt': 'compact'},
    {'id': 'untrained', 'label': 'Untrained Tiny Aya', 'adapter': None, 'prompt': 'staged'},
    {'id': 'second', 'label': 'Trained Tiny Aya, second adapter', 'adapter': 'second_adapter.gguf', 'prompt': 'compact'},
    {'id': 'first', 'label': 'Trained Tiny Aya, first adapter (full history)', 'adapter': 'first_adapter.gguf', 'prompt': 'staged'},
)


# The one model the page runs. Set from the latest paired evaluation; the others stay available to the backend.
LIVE_MODEL = os.environ.get('LIVE_MODEL', 'system')
# Try it refuses a third read of one source (its text is already in the state), which stops the rereading loop the
# evaluated harness allowed. A harness change, not a model one: set REREAD_LIMIT=0 to run as evaluated.
REREAD_LIMIT = int(os.environ.get('REREAD_LIMIT', '2')) or None
# Try it's turn budget; the evaluated runs used 45. Set MAX_TURNS=45 to run as evaluated.
MAX_TURNS = int(os.environ.get('MAX_TURNS', '1000'))  # a run still ends when it finishes, gets stuck, or fills its context
WRAP_UP = os.environ.get('WRAP_UP', '1') == '1'  # a run that stops early still ends with a draft recommendation (not in the evaluated runs)
STUCK_HELP = os.environ.get('STUCK_HELP', '1') == '1'  # after two refusals in a row, say what it can do instead (not in the evaluated runs)
# Adopted on development (DECISIONS 2026-11-08): source dates in the state, and 3 weighed sources per theory before moving on
SOURCE_DATES = os.environ.get('SOURCE_DATES', '1') == '1'
MIN_ASSESSED = int(os.environ.get('MIN_ASSESSED', '3'))
MAX_ERRORS = int(os.environ.get('MAX_ERRORS', '6'))  # refusals in a row before a run stops (the evaluated runs had 4)
# Optional and off by default (docs/RECOVERY_EXPERIMENT.md, stage 2): when the steps left barely cover what the
# investigation still requires, say so and withdraw optional exploration. It passed the adoption rule on development by
# one finished run with quality unchanged; it does not make answers better, and it only acts near the step limit.
RECOVERY_BUDGET = ('budget',)


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
    if model.get('reasoner') and model['reasoner'] not in loaded and model['adapter'] in loaded:
        model = next(m for m in MODELS if m['id'] == 'final')  # the second adapter is not on this server: version 1 alone
    return model, loaded


# Company workspaces: companies the current adapters never trained on (validation companies in src/aemon/pipeline/splits.py).
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
# Starting questions, phrased the way a manager would ask them. The first is shown for the case's own question.
EXAMPLES = {
    'hellberg': [
        'Should we make hearing protection for everyday people, not just workplaces?',
        'Why do people take their ear protection off, and could we fix that?',
        "What's the cheapest way to find out if consumers would buy from us?",
    ],
    'neumann': [
        'Should we launch a line for home studios and podcasters?',
        'Would a cheaper mic win new buyers, or hurt our name with the pros?',
        'Are creators already buying from us, and is it worth a separate range?',
    ],
    'jotun': [
        'It is mid-2024. Could our marine coatings become something homeowners buy?',
        'Who outside shipping has a problem our coatings could solve?',
        "How would we test if people would pay for a Jotun product, without spending much?",
    ],
    'tanita': [
        'It is 1993. Should we sell a body-fat scale people can use at home?',
        'Who would want to check their body fat at home, and why?',
        'How could we test demand for a home scale before building it?',
    ],
    'deere': [
        'It is 1962. Should we build a small machine for homeowners?',
        'Would people with big gardens buy a small Deere, and could our dealers sell it?',
        'What would tell us homeowners really want a Deere, before we commit?',
    ],
}

# What-if cases. Every one adds simulated evidence halfway through, and the page marks it Simulated.
SCENARIOS = {
    'hellberg-new-evidence-looks': 'What if a test showed nicer-looking protectors are worn no more often?',
    'hellberg-new-evidence-comfort': 'What if a test showed comfier protectors are worn no more often?',
    'hellberg-new-evidence-favours-looks': 'What if a test showed nicer-looking protectors are worn far more often?',
}
IRRELEVANT_SCENARIO = 'What if an unrelated test turned up (warehouse packing errors)? It should change nothing.'


def _examples(case: Case) -> list[str]:
    """Plain starting questions for the workspace; without curated ones, the case's own question and two rephrasings."""
    scope = _scope(case.id)
    if scope in EXAMPLES:
        return EXAMPLES[scope]
    question = re.sub(r'^It is [^.]*\.\s*', '', case.question.strip())
    return [
        question,
        'Should we sell to individual buyers, or stay with the customers we have?',
        'What would we need to see before testing a consumer product?',
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
        if model.get('reasoner') and adapters.get(model['reasoner']) is not None:
            adapter += [model['reasoner'], _file_sha256(adapters[model['reasoner']])]
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
        'finished': final is not None and not final.get('draft'),
        'draft': bool(final and final.get('draft')),
        'calls': len(record.get('calls', [])),
        'refused': sum(not c['accepted'] for c in record.get('calls', [])),
        'stage_at_stop': point.get('stage_at_stop'),
        'recommendation': (final or {}).get('recommendation'),
        'position': (record.get('position') or {}).get('recommendation'),
    }


ONLINE = re.compile(r"\b(search|look|check|find|browse|google)\w*\b[^.?!]{0,40}\b(online|on the web|on the internet|the internet|web)\b|\b(search|look)\w* (it )?up online\b|\bonline (search|sources|research)\b", re.I)


def asks_online(text: str) -> bool:
    """The person asked for a web search in their own words ("search online for...", "look it up on the web")."""
    return bool(ONLINE.search(text or ''))


def _prepared(case: Case, items: list[Json], context: str | None) -> Case:
    """The case with the person's attached documents added to its sources and their new information in the brief."""
    brief = case.brief + attach.brief_note(items)
    if context and context.strip():
        brief += ('\n\nNew information from the person for this run (their account, not evidence; weigh it against the sources): '
                  + context.strip())
    return dataclasses.replace(case, dossier=attach.with_attachments(case.dossier, items), brief=brief)


# How deep an investigation goes: its search budget and its step limit. Standard is the setting used so far; the
# evaluated runs had 8 searches and 45 steps. A deeper run reads more, so it takes longer and may hit the context limit.
DEPTHS = {
    'quick': {'label': 'Quick', 'searches': 5, 'turns': 100},
    'standard': {'label': 'Standard', 'searches': 8, 'turns': 500},
    'thorough': {'label': 'Thorough', 'searches': 12, 'turns': MAX_TURNS},
}


class Attempt(BaseModel):
    model_config = ConfigDict(extra='forbid')
    workspace: str = Field(max_length=40)
    case: str = Field(max_length=80)
    question: str | None = Field(default=None, max_length=400)
    shown: str | None = Field(default=None, max_length=400)  # the words the person clicked, kept in their history
    model: str | None = Field(default=None, pattern='^(untrained|trained|first|second|final|system)$')  # None runs LIVE_MODEL
    fresh: bool = False  # run live even if a saved result exists
    live_research: bool = False  # search the web (snapshotted) instead of the fixed dossier; never part of an evaluation
    project: str | None = Field(default=None, max_length=40)  # start it inside a project: that project's memory applies
    depth: Literal['quick', 'standard', 'thorough'] = 'standard'
    attachments: list[str] = Field(default_factory=list, max_length=10)  # ids of the person's files and links, added to the sources
    context: str | None = Field(default=None, max_length=1500)  # new information for a re-investigation, from a follow-up
    budget_guard: bool = False  # experimental: wrap up when the steps are running out (RECOVERY_BUDGET); never part of an evaluation


def _run_attempt(identifier: str, case: Case, model: Json, loaded: list[str], prefix: list[Json] | None = None) -> None:
    """Runs one investigation in this server, whoever is watching: leaving the page changes nothing. Every turn is saved
    (the raw model turns as well as the record), so a run cut off by a restart resumes from its last turn (_resume)."""
    entry = _tries[identifier]
    prefix = list(prefix or [])
    lora = [{'id': i, 'scale': 1.0 if name == model['adapter'] else 0.0} for i, name in enumerate(loaded)]
    reason = [{'id': i, 'scale': 1.0 if name == model.get('reasoner') else 0.0} for i, name in enumerate(loaded)]
    status_check = bool(model.get('status_check'))
    system_prompt = with_status(PROMPTS[model['prompt']]) if status_check else PROMPTS[model['prompt']]

    def route(stage: str, errors: int = 0) -> LoraSetting:
        return lora if not model.get('reasoner') or stage in DIG_STAGES else reason

    def respond(messages: list[Message], seed: int, max_tokens: int, schema: Schema | None, temperature: float, lora: LoraSetting = None) -> Json:
        return chat(MODEL_URL, messages, seed, max_tokens, schema, temperature, lora=lora)

    def turns_of(run: Investigation) -> list[Json]:
        return prefix + [{'text': t.get('text', ''), 'tool_result': t.get('tool_result')} for t in getattr(run, 'model_turns', [])]

    def finished_record(run: Investigation, info: Json) -> Json:
        for call in run.calls:  # resumed turns are this model's own, replayed, not someone else's prefix
            call.pop('prefix', None)
        extra = ({'continued_after_turn' if entry.get('continues') else 'resumed_after_turn': len(prefix)} if prefix else {})
        more = {'continues': entry['continues']} if entry.get('continues') else {}
        return {**detail(record_of(run, info), case), 'memory_used': entry.get('memory_used') or [], 'depth': entry.get('depth', 'standard'), **extra, **more}

    def on_turn(run: Investigation) -> None:
        entry['record'] = finished_record(run, {'stop_reason': None})
        _record_history(entry['user'], entry['workspace'], identifier, record=entry['record'], turns=turns_of(run))
        if entry.get('stop'):
            raise Stopped

    try:
        run, info = play(
            case,
            respond,
            system_prompt,
            max(entry.get('max_turns', MAX_TURNS) - len(prefix), 1),
            MAX_ERRORS,
            520,
            True,
            TOOL_SCHEMA,
            staged=True,
            on_turn=on_turn,
            compact=model['prompt'] in COMPACT,
            reread_limit=REREAD_LIMIT,
            route=route if lora else None,
            status_check=status_check,
            prefix=prefix,
            stuck_help=STUCK_HELP,
            source_dates=SOURCE_DATES,
            min_assessed=MIN_ASSESSED,
            recovery_features=RECOVERY_BUDGET if entry.get('budget_guard') else (),
            attempt=entry.get('continues', 0),  # a continued run samples afresh rather than repeating the stuck turns
        )
        entry['record'] = finished_record(run, info)
        entry['status'] = 'finished'
    except Stopped:
        entry['status'], entry['error'] = 'stopped', 'stopped by you'
        if entry['record']:
            entry['record'] = {**entry['record'], 'stop_reason': 'stopped by you'}
    except Exception as error:  # noqa: BLE001  shown to the person watching, not swallowed
        entry['status'], entry['error'] = 'failed', f'{type(error).__name__}: {error}'
    record = entry['record']
    if record and not record.get('final') and entry['status'] != 'stopped' and WRAP_UP:  # never leave the person without an answer
        entry['wrapping'] = True
        stop = record.get('stop_reason') or ('error' if entry['status'] == 'failed' else None)
        final = wrapup.draft(chat, MODEL_URL, {**record, 'stop_reason': stop}, len(_loaded_adapters()))
        if final:
            record = entry['record'] = {**record, 'final': final, 'stop_reason': stop or record.get('stop_reason')}
            entry['status'], entry['error'] = 'finished', None
        entry['wrapping'] = False
    if entry['status'] == 'finished' and record and entry.get('cache_key') and not prefix and not (record.get('final') or {}).get('draft'):  # never a failed, stopped or resumed run
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


RESUME_WAIT = int(os.environ.get('LEXSI_RESUME_WAIT', 900))  # seconds to wait for the model server after a restart


def _resume(wait: float = RESUME_WAIT) -> None:
    """After a restart: every investigation still marked running resumes from its saved turns, one at a time, once the
    model server is up. Replay checks each saved turn returns exactly its saved result. A live web run cannot be
    replayed (the web changes), and a run saved before resuming existed has no turns: both are marked interrupted."""
    pending = []
    for e in store.running():
        settings, turns = e.get('run_settings') or {}, e.get('turns') or []
        if not settings or settings.get('live') or e.get('case') not in cases():
            _record_history(e['user'], e['workspace'], e['id'], status='interrupted', error='Aemon restarted during this run', ended=time.time())
            continue
        with _lock:
            _tries[e['id']] = {
                'status': 'running', 'record': e.get('record'), 'error': None, 'model': settings.get('model'), 'model_label': '',
                'user': e['user'], 'workspace': e['workspace'], 'cache_key': None, 'identity': None,
                'memory_used': settings.get('memory_used') or [], 'resuming': True,
            }
        pending.append((e, settings, turns))
    deadline = time.time() + wait
    for e, settings, turns in pending:
        while not _model_ready() and time.time() < deadline:
            time.sleep(5)
        entry = _tries[e['id']]
        try:
            model, loaded = _model(settings.get('model') or LIVE_MODEL)
            if not _model_ready() or (model['adapter'] and model['adapter'] not in loaded):
                raise RuntimeError('the model server did not come back')
        except Exception as error:  # noqa: BLE001
            entry['status'], entry['error'] = 'interrupted', f'could not resume: {error}'
            _record_history(e['user'], e['workspace'], e['id'], status='interrupted', error=entry['error'], ended=time.time())
            continue
        depth = DEPTHS.get(settings.get('depth') or 'standard', DEPTHS['standard'])
        base = cases()[e['case']]
        items = attach.load(store.folder(), e['user'], settings.get('attachments') or [])
        case = dataclasses.replace(base, question=settings['question'], brief=settings['brief'], search_budget=depth['searches'], dossier=attach.with_attachments(base.dossier, items))
        entry['max_turns'], entry['depth'] = depth['turns'], settings.get('depth') or 'standard'
        entry['budget_guard'] = bool(settings.get('budget_guard'))
        entry['resuming'] = False
        _run_attempt(e['id'], case, model, loaded, prefix=turns)


@app.get('/api/workflow')
def workflow() -> Json:
    """The stage controller for people: stages in order, the tools each opens, and what moves it on. It is the same
    table the tests check against the controller, and the tool descriptions are the ones the model is given."""
    from aemon.environment.stages import WORKFLOW
    from aemon.environment.tools import POSITION_SIGNATURE, TOOL_SIGNATURES

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
        'depths': [{'id': k, **v} for k, v in DEPTHS.items()],
    }


@app.get('/api/try/running')
def my_running(request: Request) -> Json:
    """This person's investigations still running, in any company, so every page can show them and say when they end."""
    user = request.state.user
    mine = [(i, t) for i, t in _tries.items() if t['user'] == user and t['status'] == 'running']
    questions = {e['id']: e.get('question') for w in {t['workspace'] for _, t in mine} for e in _history(user, w)}
    return {'running': [{'id': i, 'workspace': t['workspace'], 'question': questions.get(i) or '', 'resuming': bool(t.get('resuming'))} for i, t in mine]}


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


@app.get('/api/companies')
def list_companies(request: Request) -> Json:
    """The directory: this account's companies with their profile summary and real counts (app/companies.py)."""
    own = store.companies_of(request.state.user)
    order = [w['id'] for w in workspaces()]
    out = []
    for w in workspaces():
        if w['id'] in own:
            done = [e for e in _history(request.state.user, w['id'])]
            out.append(companies.summary(w['id'], cases()[w['base_case']], order, len(done)))
    return {'companies': out}


@app.get('/api/companies/{company}')
def company_profile(company: str, request: Request) -> Json:
    """One company: curated, cited profile facts, its source library, its investigations and possible questions."""
    _workspace_or_404(company, request.state.user)
    order = [w['id'] for w in workspaces()]
    w = next(x for x in workspaces() if x['id'] == company)
    entries = workspace_history(company, request)['entries']
    own = store.companies_of(request.state.user)
    others = [companies.summary(x['id'], cases()[x['base_case']], order, 0) for x in workspaces() if x['id'] in own]
    return companies.profile(company, cases()[w['base_case']], order, sorted(entries, key=lambda e: e.get('started') or 0, reverse=True),
                             w['examples'], w['scenarios'], others)


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
        'settings': {k: v for k, v in (entry.get('run_settings') or {}).items() if k in ('depth', 'live', 'model', 'context', 'asked_online', 'budget_guard')}
        | {'attachments': [attach.summary(i) for i in attach.load(store.folder(), request.state.user, (entry.get('run_settings') or {}).get('attachments') or [])]},
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


class Attachment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str | None = Field(default=None, max_length=200)
    data_base64: str | None = Field(default=None, max_length=21_000_000)
    url: str | None = Field(default=None, max_length=2000)


@app.post('/api/workspaces/{workspace}/attachments', status_code=201)
def add_attachment(workspace: str, body: Attachment, request: Request) -> Json:
    """A file (name and base64 content) or a link, read once and kept as passages the agent can search and quote."""
    _workspace_or_404(workspace, request.state.user)
    try:
        if body.url:
            from aemon.environment.live import LiveDossier

            return attach.add_link(store.folder(), request.state.user, workspace, body.url.strip(), LiveDossier._http)
        if body.name and body.data_base64:
            return attach.add_file(store.folder(), request.state.user, workspace, body.name, body.data_base64)
    except attach.Unreadable as error:
        raise HTTPException(422, f'could not use it: {error}') from error
    raise HTTPException(422, 'send a file (name and data_base64) or a url')


@app.get('/api/workspaces/{workspace}/attachments')
def list_attachments(workspace: str, request: Request) -> Json:
    _workspace_or_404(workspace, request.state.user)
    return {'attachments': attach.listing(store.folder(), request.state.user, workspace)}


@app.delete('/api/workspaces/{workspace}/attachments/{identifier}')
def remove_attachment(workspace: str, identifier: str, request: Request) -> Json:
    _workspace_or_404(workspace, request.state.user)
    if not attach.remove(store.folder(), request.state.user, identifier):
        raise HTTPException(404, 'no such attachment')
    return {'deleted': identifier}


# Review of teacher examples (reviews/v2_round*/<batch>_kept_for_review.json): only examples the reviewer keeps train.
REVIEWS = ROOT / 'reviews'
REVIEWER = os.environ.get('LEXSI_REVIEWER', 'hatem')


def _reviewer(request: Request) -> None:
    if request.state.user != REVIEWER:
        raise HTTPException(404, 'not found')


def _review_file(batch: str) -> Path:
    path = next((p for p in REVIEWS.glob('v2_round*/*_kept_for_review.json') if f'{p.parent.name}/{p.stem}' == batch), None)
    if path is None:
        raise HTTPException(404, 'no such batch')
    return path


@app.get('/api/review')
def review_batches(request: Request) -> Json:
    _reviewer(request)
    out = []
    for path in sorted(REVIEWS.glob('v2_round*/*_kept_for_review.json')):
        examples = json.loads(path.read_text()).get('examples', [])
        advisory = sorted(p.name for p in path.parent.glob('advisory_*.md'))
        out.append({'batch': f'{path.parent.name}/{path.stem}', 'examples': len(examples), 'advisory': advisory,
                    'kept': sum(e.get('keep') is True for e in examples), 'dropped': sum(e.get('keep') is False for e in examples)})
    return {'batches': out}


@app.get('/api/review/{folder}/{name}')
def review_batch(folder: str, name: str, request: Request) -> Json:
    _reviewer(request)
    path = _review_file(f'{folder}/{name}')
    data = json.loads(path.read_text())
    advisory = {p.stem.removeprefix('advisory_'): p.read_text() for p in sorted(path.parent.glob('advisory_*.md'))}
    return {'batch': f'{folder}/{name}', 'counts': data.get('counts'), 'examples': data.get('examples', []), 'advisory': advisory}


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    keep: bool | None = None
    note: str | None = Field(default=None, max_length=2000)


@app.patch('/api/review/{folder}/{name}/{n}')
def review_decide(folder: str, name: str, n: int, body: ReviewDecision, request: Request) -> Json:
    """Records the reviewer's keep or drop (and note) in the batch file itself, which is what training reads."""
    _reviewer(request)
    path = _review_file(f'{folder}/{name}')
    with _lock:
        data = json.loads(path.read_text())
        example = next((e for e in data.get('examples', []) if e.get('n') == n), None)
        if example is None:
            raise HTTPException(404, 'no such example')
        example['keep'], example['review_note'] = body.keep, (body.note or '').strip() or None
        example['reviewed_by'], example['reviewed_at'] = request.state.user, time.strftime('%Y-%m-%dT%H:%M:%S')
        tmp = path.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1))
        tmp.replace(path)
    return {'n': n, 'keep': body.keep}


@app.post('/api/workspaces/{workspace}/history/{identifier}/continue')
def continue_run(workspace: str, identifier: str, request: Request) -> Json:
    """Carries on an investigation that stopped early, from exactly where it stopped: its saved turns are replayed and
    the model takes over with fresh sampling and the stuck help shown at once. It keeps its id, so it stays one run."""
    user = request.state.user
    entry = _entry_or_404(workspace, identifier, user)
    settings, turns, record = entry.get('run_settings') or {}, entry.get('turns') or [], entry['record']
    if record.get('final') and not record['final'].get('draft'):
        raise HTTPException(409, 'this investigation already finished')
    if not settings or not turns or settings.get('live'):
        raise HTTPException(409, 'this investigation cannot be continued: it was saved before continuing existed, or it searched the live web')
    if not _model_ready():
        raise HTTPException(503, 'the model server is not running')
    model, loaded = _model(settings.get('model') or LIVE_MODEL)
    if model['adapter'] and model['adapter'] not in loaded:
        raise HTTPException(409, f'{model["label"]} is not loaded on the model server')
    depth = DEPTHS.get(settings.get('depth') or 'standard', DEPTHS['standard'])
    base = cases()[entry['case']]
    items = attach.load(store.folder(), user, settings.get('attachments') or [])
    case = dataclasses.replace(base, question=settings['question'], brief=settings['brief'], search_budget=depth['searches'], dossier=attach.with_attachments(base.dossier, items))
    with _lock:
        if any(t['status'] == 'running' for t in _tries.values()):
            raise HTTPException(409, 'an investigation is already running')
        continues = int(record.get('continues') or 0) + 1
        _tries[identifier] = {
            'status': 'running', 'record': record, 'error': None, 'model': model['id'], 'model_label': model['label'], 'user': user,
            'workspace': workspace, 'cache_key': None, 'identity': None, 'memory_used': settings.get('memory_used') or [],
            'max_turns': len(turns) + 200, 'depth': settings.get('depth') or 'standard', 'continues': continues,
            'budget_guard': bool(settings.get('budget_guard')),
        }
    _record_history(user, workspace, identifier, status='running', error=None)
    threading.Thread(target=_run_attempt, args=(identifier, case, model, loaded), kwargs={'prefix': turns}, daemon=True).start()
    return {'id': identifier, 'continues': continues}


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
        data = pdf_report.pdf(page, company)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(503, f'the report could not be printed: {error}') from error
    name = re.sub(r'[^A-Za-z0-9]+', '-', (entry.get('question') or 'investigation'))[:60].strip('-') or 'investigation'
    return Response(data, media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="{name}.pdf"'})


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
    depth = DEPTHS[body.depth]
    case = dataclasses.replace(case, search_budget=depth['searches'])  # part of the case digest, so saved runs never mix depths
    items = attach.load(store.folder(), user, body.attachments)
    if len(items) != len(set(body.attachments)) or any(i['workspace'] != body.workspace for i in items):
        raise HTTPException(404, 'an attachment was not found')
    case = _prepared(case, items, body.context)
    asked_online = not body.live_research and asks_online(f'{body.question or ""} {body.context or ""}')
    if asked_online:  # "search online" in the question or the new information turns web search on, and the page says why
        body.live_research = True
    if notes:  # memory, as context in the brief; it changes the case, so a saved run without it is never reused
        case = dataclasses.replace(case, brief=case.brief + '\n\nNotes from the person asking (their context, not evidence; never quote them): ' + ' '.join(f'({i + 1}) {n}' for i, n in enumerate(notes)))
    bound = _cache_key(case, model)
    key, identity = bound if bound else (None, None)
    saved = store.cached(key) if key and not body.fresh and not body.live_research and not items and not body.context and not body.budget_guard else None
    if saved:  # a saved result, shown at once and labelled as saved, with the date it was made
        identifier = uuid.uuid4().hex
        record, created = saved
        record = {**record, 'memory_used': notes, 'depth': body.depth}
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
            from aemon.environment.live import LiveDossier

            extra = attach.with_attachments(attach.Dossier([]), items) if items else None
            case = dataclasses.replace(case, dossier=LiveDossier(case.company, store.folder() / 'live_snapshots' / identifier, extra=extra))
        _tries[identifier] = {
            'status': 'running',
            'record': None,
            'error': None,
            'live_research': body.live_research,
            'model': model['id'],
            'model_label': model['label'] + (' · live web research (snapshotted; not part of the evaluated setup)' if body.live_research else '')
            + (' · experimental step-budget guard (not part of the evaluated setup)' if body.budget_guard else ''),
            'user': user,
            'workspace': body.workspace,
            'cache_key': None if body.live_research or items or body.context or body.budget_guard else key,  # a run with the person's own material is never shared
            'identity': identity,
            'memory_used': notes,
            'max_turns': depth['turns'],
            'depth': body.depth,
            'budget_guard': body.budget_guard,
        }
    _record_history(user, body.workspace, identifier, question=shown + (' (live web)' if body.live_research else ''), case=body.case, model=model['id'], started=time.time(), status='running', project=body.project,
                    run_settings={'question': case.question, 'brief': case.brief, 'model': model['id'], 'live': body.live_research, 'memory_used': notes, 'depth': body.depth,
                                  'attachments': body.attachments, 'context': body.context, 'asked_online': asked_online, 'budget_guard': body.budget_guard})
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


def _test_account() -> None:
    """A hosted copy's shared test account (AEMON_TEST_USER and AEMON_TEST_PASSWORD, set as secrets where it is hosted):
    created at start in every company, so the people testing can be given one name and password. An empty history is
    filled once from AEMON_SEED (a JSON list of finished investigations), so there are reports to open before any run."""
    name, password = os.environ.get('AEMON_TEST_USER', '').strip().lower(), os.environ.get('AEMON_TEST_PASSWORD', '')
    if not name or not password:
        return
    users.add(name, password, WORKSPACES[0])
    for w in workspaces():
        store.join(name, w['id'])
    seed = os.environ.get('AEMON_SEED')
    if seed and Path(seed).is_file() and not any(store.history(name, w['id']) for w in workspaces()):
        for e in json.loads(Path(seed).read_text()):
            if e['workspace'] in WORKSPACES:
                store.record(name, e['workspace'], e['id'], **{k: v for k, v in e.items() if k not in ('id', 'workspace')})


_sync_companies()  # at import, before any request: the companies table and the demo memberships
_test_account()
if os.environ.get('LEXSI_NO_RESUME') != '1':  # the tests resume by hand
    threading.Thread(target=_resume, daemon=True).start()
