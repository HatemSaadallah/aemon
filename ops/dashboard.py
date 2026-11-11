"""Operations dashboard on its own port (8100), separate from Aemon (8000), which it never touches.

    .venv/bin/python ops/dashboard.py          # then open http://localhost:8100

One page, refreshed every 20 seconds: the Slurm jobs (scripts/cluster/cluster.py, over the one SSH master, cached 30 s), the
hosted-teacher runs in experiments/hosted_teacher (states answered, kept by the gates, requests, cost), the DeepSeek
balance (cached 60 s) and the review batches in reviews/v2_round5. Read-only: it submits, cancels and writes nothing.
Bound to 127.0.0.1 only.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import dotenv_values
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'experiments' / 'hosted_teacher'
PORT = int(os.environ.get('OPS_PORT', 8100))
app = FastAPI()
_cache: dict[str, tuple[float, Any]] = {}


def _env() -> None:
    """Keys from .env fill in what the environment does not already set. Values are never printed."""
    env = ROOT / '.env'
    for key, value in (dotenv_values(env, interpolate=False) if env.exists() else {}).items():
        if value is not None:
            os.environ.setdefault(key, value.strip())


def cached(key: str, seconds: float, make: Any) -> Any:
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < seconds:
        return hit[1]
    try:
        value = make()
    except Exception as error:  # noqa: BLE001  shown on the page
        value = {'error': str(error)[:300]}
    _cache[key] = (time.time(), value)
    return value


def jobs() -> Any:
    spec = importlib.util.spec_from_file_location('cluster_tool', ROOT / 'scripts' / 'cluster.py')
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module.jobs()


def balance() -> Any:
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        return None
    request = urllib.request.Request('https://api.deepseek.com/user/balance', headers={'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.load(response)
    return sum(float(b['total_balance']) for b in data.get('balance_infos', []) if b.get('currency') == 'USD')


def _lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def runs() -> list[dict[str, Any]]:
    parts = sorted(f.stem.replace('states_', '') for f in RUNS.glob('states_*.json') if 'retry' not in f.stem)
    out = []
    for label, prefix in (('DeepSeek V4.1-Flash', ''), ('DeepSeek V4-Pro', 'pro_')):
        rows = []
        for part in parts:
            total = len(json.loads((RUNS / f'states_{part}.json').read_text()))
            requests = _lines(RUNS / f'requests_{prefix}{part}.jsonl')
            asked_path = RUNS / f'asked_{prefix}{part}.json'
            asked = json.loads(asked_path.read_text()) if asked_path.exists() else None
            manifest = RUNS / f'provenance_{prefix}{part}.jsonl'
            rows.append({'part': part, 'states': total, 'finished': asked is not None,
                         'kept': sum(isinstance(a.get('kept'), dict) for a in asked) if asked else None,
                         'replies': len(manifest.read_text().splitlines()) if manifest.exists() else 0,
                         'requests': len(requests), 'usd': sum(r.get('usd', 0) for r in requests),
                         'last': requests[-1]['at'][11:19] if requests else '-'})
        if any(r['requests'] for r in rows):
            out.append({'teacher': label, 'parts': rows})
    return out


def reviews() -> list[dict[str, Any]]:
    out = []
    for path in sorted((ROOT / 'reviews' / 'v2_round5').glob('*_kept_for_review.json')):
        examples = json.loads(path.read_text()).get('examples', [])
        by: dict[str, list[int]] = {}
        for e in examples:
            by.setdefault(e.get('skill') or '-', [0, 0, 0])[0 if e.get('keep') is True else 1 if e.get('keep') is False else 2] += 1
        out.append({'batch': path.stem.replace('_kept_for_review', ''), 'examples': len(examples), 'by_family': by})
    return out


LOG_DIRS = {'corrective round': RUNS, 'investigations': ROOT / 'experiments' / 'hosted_investigations',
            'new cases': ROOT / 'data' / 'dossier' / 'raw' / 'train3'}


def log_files() -> list[tuple[str, Path]]:
    return [(source, f) for source, folder in LOG_DIRS.items() for f in sorted(folder.rglob('requests*.jsonl'))]


def spend() -> float:
    return sum(r.get('usd', 0) for _, f in log_files() for r in _lines(f))


def requests_log(source: str, limit: int) -> dict[str, Any]:
    rows = []
    for src, f in log_files():
        if source and src != source:
            continue
        part = f.stem.replace('requests_', '').replace('requests', 'all')
        for r in _lines(f):
            u = r.get('usage', {})
            rows.append({'at': r.get('at', ''), 'source': src, 'part': part, 'model': r.get('model') or r.get('requested'),
                         'prompt': u.get('prompt_tokens', 0), 'cached': u.get('prompt_cache_hit_tokens', 0),
                         'output': u.get('completion_tokens', 0), 'reasoning': (u.get('completion_tokens_details') or {}).get('reasoning_tokens', 0),
                         'usd': r.get('usd', 0), 'seconds': r.get('seconds'), 'finish': r.get('finish'), 'tool_call': r.get('tool_call'), 'peak': r.get('peak')})
    rows.sort(key=lambda r: r['at'], reverse=True)
    by: dict[str, dict[str, float]] = {}
    for r in rows:
        b = by.setdefault(r['source'], {'requests': 0, 'usd': 0.0, 'prompt': 0, 'cached': 0, 'output': 0})
        b['requests'] += 1
        b['usd'] += r['usd']
        b['prompt'] += r['prompt']
        b['cached'] += r['cached']
        b['output'] += r['output']
    return {'total': len(rows), 'by_source': by, 'rows': rows[:limit]}


def investigations() -> dict[str, Any]:
    folder = LOG_DIRS['investigations']
    parts = []
    for cases_file in sorted(folder.glob('cases_part*.txt')) + sorted(folder.glob('cases_new*.txt')):
        part = cases_file.stem.replace('cases_', '')
        planned = len(cases_file.read_text().split(',')) * (1 if part.startswith('new') else 2)
        done = finished = 0
        for r in _lines(folder / f'{part}.episodes.jsonl'):
            if 'config' in r:
                continue
            done += 1
            finished += r.get('stop_reason') == 'finished'
        requests = _lines(folder / f'requests_{part}.jsonl')
        parts.append({'part': part, 'planned': planned, 'done': done, 'finished': finished, 'complete': (folder / f'{part}.json').exists(),
                      'requests': len(requests), 'usd': sum(r.get('usd', 0) for r in requests),
                      'last': requests[-1]['at'][11:19] if requests else '-'})
    return {'parts': parts}


@app.get('/api/status')
def status() -> dict[str, Any]:
    return {'at': time.strftime('%H:%M:%S'), 'jobs': cached('jobs', 30, jobs), 'balance': cached('balance', 60, balance),
            'spend': round(spend(), 3), 'runs': runs(), 'reviews': reviews(), 'investigations': investigations()}


@app.get('/api/requests')
def deepseek_requests(source: str = '', limit: int = 200) -> dict[str, Any]:
    return requests_log(source, max(1, min(limit, 2000)))


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ops dashboard</title><style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--ink2:#5f5f5a;--line:#e4e4df;--good:#1f7a4d;--goodw:#e3f3ea;--bad:#b3261e;--badw:#fbe7e5;--warn:#8a5a00;--warnw:#fdf1d8;--bar:#2f6fde}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1e1c;--ink:#ececE8;--ink2:#a3a39c;--line:#33332f;--goodw:#163526;--good:#7fd1a5;--badw:#3d1a18;--bad:#f2a49d;--warnw:#3a2c0c;--warn:#f0c46a;--bar:#7aa7ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1180px;margin:0 auto;padding:20px 16px 48px}h1{font-size:20px;margin:0}h2{font-size:15px;margin:0 0 10px}
header{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.muted{color:var(--ink2)}.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));margin-bottom:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:14px;overflow-x:auto}
.tile .v{font-size:24px;font-weight:650;font-variant-numeric:tabular-nums}.tile .k{color:var(--ink2);font-size:12.5px}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
th{color:var(--ink2);font-weight:550}td.n{text-align:right;font-variant-numeric:tabular-nums}
.chip{display:inline-block;border-radius:999px;padding:1px 9px;font-size:12px;font-weight:600;background:var(--line);color:var(--ink2)}
.chip.good{background:var(--goodw);color:var(--good)}.chip.bad{background:var(--badw);color:var(--bad)}.chip.warn{background:var(--warnw);color:var(--warn)}
.bar{height:6px;background:var(--line);border-radius:3px;min-width:90px;overflow:hidden}.bar i{display:block;height:100%;background:var(--bar)}
.err{color:var(--bad)}</style></head><body><main>
<header><h1>Ops dashboard</h1><span class="muted" id="at">loading…</span></header>
<div class="grid" id="tiles"></div>
<section class="card"><h2>Cluster jobs</h2><div id="jobs"></div></section>
<section class="card"><h2>Whole investigations (DeepSeek V4-Pro)</h2><div id="inv"></div></section>
<section class="card"><h2>Hosted teacher runs</h2><div id="runs"></div></section>
<section class="card"><h2>Review (DeepSeek V4-Pro, strict filter)</h2><div id="reviews"></div></section>
<section class="card"><h2>DeepSeek API log</h2>
<div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px">
<label>Source <select id="src"><option value="">All</option><option>investigations</option><option>new cases</option><option>corrective round</option></select></label>
<label>Show <select id="lim"><option>50</option><option selected>200</option><option>1000</option></select></label>
<span class="muted" id="logsum"></span></div><div id="bysrc"></div><div id="log"></div></section>
</main><script>
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const chip=s=>{const t=String(s||'');const c=/RUNNING|COMPLETED|done/.test(t)?'good':/FAIL|CANCEL|TIMEOUT|OUT_OF/.test(t)?'bad':/PENDING|running/.test(t)?'warn':'';return `<span class="chip ${c}">${esc(t)}</span>`};
const tbl=(head,rows)=>rows.length?`<table><thead><tr>${head.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(c=>`<td${typeof c==='number'?' class="n"':''}>${typeof c==='object'&&c&&c.html?c.html:esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`:'<p class="muted">None.</p>';
const tile=(k,v)=>`<div class="card tile"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`;
async function load(){try{const d=await (await fetch('/api/status')).json();
document.getElementById('at').textContent='updated '+d.at+' · refreshes every 20 s';
const j=d.jobs||{};const q=j.queue||[];let html='';
if(j.error)html=`<p class="err">${esc(j.error)}</p>`;else{html+=tbl(['Job','Name','State','Elapsed','Limit','GPU','Node / reason'],q.map(r=>[r.job,r.name,{html:chip(r.state)},r.elapsed,r.limit,r.gpu,r.node]));
html+='<h2 style="margin-top:14px">Finished in the last day</h2>'+tbl(['Job','Name','State','Elapsed','Ended','Node','Exit'],(j.finished||[]).slice().reverse().map(r=>[r.job,r.name,{html:chip(r.state)},r.elapsed,r.ended,r.node,r.exit]))}
document.getElementById('jobs').innerHTML=html;
let states=0,answered=0,kept=0;
document.getElementById('runs').innerHTML=d.runs.map(run=>{const rows=run.parts.map(p=>{states+=p.states;if(p.finished){answered+=p.states;kept+=p.kept||0}
const pct=p.finished?100:Math.min(99,Math.round(100*p.replies/Math.max(1,p.states*(p.part.startsWith('exp')?3:1))));
return [p.part,p.states,{html:`<div class="bar"><i style="width:${pct}%"></i></div>`},{html:chip(p.finished?'done':'running')},p.kept??'–',p.requests,'$'+p.usd.toFixed(3),p.last]});
return `<h2>${esc(run.teacher)}</h2>`+tbl(['Part','States','Progress','State','Kept by gates','Requests','Cost','Last request'],rows)}).join('')||'<p class="muted">No runs yet.</p>';
document.getElementById('reviews').innerHTML=tbl(['Batch','Examples','Kept / dropped / not reviewed, by family'],d.reviews.map(r=>[r.batch,r.examples,Object.entries(r.by_family).map(([f,c])=>`${f} ${c[0]}/${c[1]}/${c[2]}`).join(' · ')]));
const inv=(d.investigations||{}).parts||[];let ip=0,id=0,ifin=0,iusd=0;
document.getElementById('inv').innerHTML=tbl(['Part','Planned','Done','Finished','Progress','State','Requests','Cost','Last request'],inv.map(p=>{ip+=p.planned;id+=p.done;ifin+=p.finished;iusd+=p.usd;
const pct=Math.round(100*p.done/Math.max(1,p.planned));return [p.part,p.planned,p.done,p.finished,{html:`<div class="bar"><i style="width:${pct}%"></i></div>`},{html:chip(p.complete?'done':'running')},p.requests,'$'+p.usd.toFixed(2),p.last]}))+(inv.length?`<p class="muted" style="margin-top:8px">${id} of ${ip} done, ${ifin} finished with a recommendation, $${iusd.toFixed(2)} spent.</p>`:'');
const bal=typeof d.balance==='number'?'$'+d.balance.toFixed(2):'–';
document.getElementById('tiles').innerHTML=tile('Jobs running or queued',q.length)+tile('DeepSeek balance',bal)+tile('Spent on DeepSeek (logged)','$'+d.spend.toFixed(2))+tile('Answers kept by the gates',kept);
}catch(e){document.getElementById('at').textContent='dashboard error: '+e}}
async function loadLog(){try{const src=document.getElementById('src').value, lim=document.getElementById('lim').value;
const d=await (await fetch('/api/requests?source='+encodeURIComponent(src)+'&limit='+lim)).json();
document.getElementById('logsum').textContent=d.total+' requests logged';
document.getElementById('bysrc').innerHTML=tbl(['Source','Requests','Prompt tokens','Cache hits','Output tokens','Cost'],Object.entries(d.by_source).map(([k,b])=>[k,b.requests,b.prompt,b.cached,b.output,'$'+b.usd.toFixed(3)]));
document.getElementById('log').innerHTML='<div style="margin-top:12px"></div>'+tbl(['Time (UTC)','Source','Part','Model','Prompt','Cached','Output','Reasoning','Cost','Seconds','Ended','Tool call','Peak'],
d.rows.map(r=>[r.at.slice(11,19),r.source,r.part,r.model,r.prompt,r.cached,r.output,r.reasoning,'$'+r.usd.toFixed(4),r.seconds,{html:chip(r.finish==='tool_calls'||r.finish==='stop'?'done':r.finish)},r.tool_call?'yes':'no',r.peak?'peak':'off-peak']));
}catch(e){document.getElementById('logsum').textContent='log error: '+e}}
document.getElementById('src').onchange=loadLog;document.getElementById('lim').onchange=loadLog;
load();loadLog();setInterval(load,20000);setInterval(loadLog,20000);
</script></body></html>"""


@app.get('/', response_class=HTMLResponse)
def page() -> str:
    return PAGE


if __name__ == '__main__':
    _env()
    sys.path.insert(0, str(ROOT / 'src'))
    uvicorn.run(app, host='127.0.0.1', port=PORT, log_level='warning')
