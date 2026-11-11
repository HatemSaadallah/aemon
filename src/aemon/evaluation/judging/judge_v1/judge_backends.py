"""Evaluation-only transports. No outputs from this module may enter training or row selection."""
from __future__ import annotations
import concurrent.futures
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parent

def digest(value):
    return hashlib.sha256(value if isinstance(value,bytes) else json.dumps(value,sort_keys=True).encode()).hexdigest()

def manifest():
    return json.loads((ROOT/'backends_v1.json').read_text())

def parse_codex(lines):
    events=[json.loads(x) for x in lines.splitlines() if x.strip()]
    completed=[e for e in events if e.get('type')=='turn.completed']
    messages=[]
    for e in events:
        item=e.get('item',{})
        if item.get('type') not in (None,'agent_message','reasoning','error'):
            raise ValueError('isolated judge attempted a tool or non-text action')
        if e.get('type')=='item.completed' and item.get('type')=='agent_message':messages.append(item['text'])
    if len(completed)!=1 or len(messages)!=1:raise ValueError('missing or ambiguous final judge response')
    return messages[0], completed[0].get('usage'), events

def codex_command(prompt_path,backend='codex'):
    cfg=manifest()['judges'][backend];binary=Path(cfg['binary']).resolve()
    if digest(binary.read_bytes())!=cfg['binary_sha256']:raise ValueError('Codex binary changed')
    if subprocess.check_output([str(binary),'--version'],text=True).strip()!=cfg['cli_version']:raise ValueError('Codex CLI version changed')
    auth=Path.home()/'.codex/auth.json'
    if json.loads(auth.read_text()).get('auth_mode')!='chatgpt':raise ValueError('requires ChatGPT account auth')
    # The guest has no repository, keys, state database, memory, user config, plugins or skills.
    # auth.json is consumed by the transport; all model execution tools are disabled/fail closed.
    cmd=['bwrap','--die-with-parent','--new-session','--unshare-pid','--unshare-ipc','--unshare-uts',
         '--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--symlink','usr/bin','/bin',
         '--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/work','--dir','/home/USER/.codex',
         '--ro-bind',str(binary),'/judge-codex','--ro-bind',str(auth),'/home/USER/.codex/auth.json',
         '--ro-bind','/etc/ssl','/etc/ssl','--ro-bind','/etc/resolv.conf','/etc/resolv.conf','--ro-bind','/etc/hosts','/etc/hosts',
         '--ro-bind',str(prompt_path),'/judge_prompt.txt','--chdir','/work','--clearenv','--setenv','HOME','/home/USER',
         '--setenv','PATH','/usr/local/bin:/usr/bin:/bin']
    # Host-side preflight checks actual mount isolation; no model invocation.
    test=subprocess.run(cmd+['/usr/bin/test','!','-e',str(cfg['forbidden_repository'])],capture_output=True)
    if test.returncode:raise ValueError('repository isolation preflight failed')
    cmd+=['/judge-codex','exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--sandbox','read-only','--json','--model',cfg['model']]
    for key,value in cfg['settings'].items():cmd+=['-c',key+'='+json.dumps(value)]
    return cmd+['-']

def codex_call(packet, destination, backend='codex'):
    cfg=manifest()['judges'][backend];cmd=codex_command(ROOT/'judge_prompt_v1.txt',backend)
    with (destination/'events.jsonl').open('x') as output,(destination/'stderr.txt').open('x') as error:
        result=subprocess.run(cmd,input=json.dumps(packet),text=True,stdout=output,stderr=error,timeout=cfg['timeout_seconds'])
    raw=(destination/'events.jsonl').read_text()
    if result.returncode:raise ValueError('isolated Codex invocation failed; retained logs')
    text,usage,events=parse_codex(raw)
    return {'text':text,'usage':usage,'requested_model':cfg['model'],'resolved_model':None,
            'cli_version':cfg['cli_version'],'binary_sha256':cfg['binary_sha256'],'raw_events_sha256':digest(raw.encode()),
            'transport_warnings':[e for e in events if e.get('type')=='error' or e.get('item',{}).get('type')=='error'],
            'isolation':'fresh bubblewrap mount namespace, no repository/keys/memory; tool actions rejected'}

def claude_estimate(packet):
    # Conservative UTF8-byte token upper bound, protocol overhead, uncached/cache-write price, output ceiling.
    cfg=manifest()['judges']['claude'];n=len((ROOT/'judge_prompt_v1.txt').read_bytes())+len(json.dumps(packet).encode())+1024
    return n*5/1e6+cfg['max_tokens']*20/1e6

def claude_call(packet,destination,repo,run_id,run_cap):
    import sys
    sys.path.insert(0,str(Path(repo)/'src'))
    import anthropic
    from aemon.agent.backends.claude_control import Claude, api_key, spent, TOTAL_CAP_USD, LEDGER, _bare_json
    cfg=manifest()['judges']['claude'];estimate=claude_estimate(packet)
    LEDGER.parent.mkdir(parents=True,exist_ok=True)
    reservation=str(uuid.uuid4())
    def append(item):
        with LEDGER.open('a') as stream:stream.write(json.dumps(item)+'\n')
    with LEDGER.with_suffix('.judge.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        rows=[json.loads(x) for x in LEDGER.read_text().splitlines()] if LEDGER.exists() else []
        used=sum(x['usd'] for x in rows if x.get('purpose')==run_id)
        if used+estimate>run_cap or spent(LEDGER)+estimate>TOTAL_CAP_USD:raise ValueError('judge ledger cap would be exceeded')
        append({'purpose':run_id,'model':cfg['model'],'usd':estimate,'kind':'reservation_upper_bound','reservation':reservation})
    client=anthropic.Anthropic(api_key=api_key(),max_retries=0,timeout=180)
    backend=Claude(run_id,run_cap,effort=cfg['effort'],model=cfg['model'],client=client,ledger=LEDGER)
    # Unknown-cost failures retain the reservation. No automatic billable retries.
    response=client.messages.create(model=cfg['model'],max_tokens=cfg['max_tokens'],
        system=(ROOT/'judge_prompt_v1.txt').read_text(),messages=[{'role':'user','content':json.dumps(packet)}],
        output_config={'effort':cfg['effort']},cache_control={'type':'ephemeral'})
    raw=response.model_dump(mode='json')
    (destination/'response.json').write_text(json.dumps(raw))
    with LEDGER.with_suffix('.judge.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        usd=backend._charge(response.usage)
        append({'purpose':run_id,'model':cfg['model'],'usd':-estimate,'kind':'reservation_release','reservation':reservation})
    if response.model!=cfg['model']:raise ValueError('Claude returned a different model')
    if response.stop_reason!='end_turn':raise ValueError('judge response did not finish: '+str(response.stop_reason))
    text=''.join(b.text for b in response.content if b.type=='text')
    return {'text':_bare_json(text),'usage':raw.get('usage'),'usd':usd,'requested_model':cfg['model'],'resolved_model':response.model,
            'raw_response_sha256':digest(json.dumps(raw).encode()),'max_tokens':cfg['max_tokens'],'temperature':None,'temperature_reason':'model API rejects sampling parameters'}

def claudecode_call(packet,destination):
    """Claude Code in print mode on the subscription login: the judge prompt replaces the system prompt, every tool and MCP
    server is off, no settings, sessions or project files, in an empty folder. No API ledger charge (not API-billed)."""
    import shutil,tempfile
    cfg=manifest()['judges']['claudecode'];binary=shutil.which('claude')
    if not binary:raise ValueError('claude CLI not found')
    env={k:v for k,v in os.environ.items() if k not in ('ANTHROPIC_API_KEY','CLAUDE_API_KEY')};env['DISABLE_AUTOUPDATER']='1'
    flags=[str(ROOT/'judge_prompt_v1.txt') if f=='<judge_prompt_v1.txt>' else f for f in cfg['flags']]
    version=subprocess.check_output([binary,'--version'],text=True,env=env).strip()
    with tempfile.TemporaryDirectory(prefix='judge-cc-') as work:
        if Path(work).resolve().is_relative_to(ROOT.parents[4]):raise ValueError('working folder inside the repository')
        result=subprocess.run([binary,*flags],input=json.dumps(packet),text=True,capture_output=True,cwd=work,env=env,timeout=cfg['timeout_seconds'])
    (destination/'response.json').write_text(result.stdout);(destination/'stderr.txt').write_text(result.stderr)
    if result.returncode:raise ValueError('Claude Code invocation failed; retained logs')
    raw=json.loads(result.stdout)
    if raw.get('is_error') or raw.get('subtype')!='success':raise ValueError('Claude Code reported an error: '+str(raw.get('subtype')))
    if raw.get('stop_reason')!='end_turn':raise ValueError('judge response did not finish: '+str(raw.get('stop_reason')))
    if raw.get('num_turns')!=1 or raw.get('permission_denials'):raise ValueError('judge took more than one turn or tried a tool')
    models=set(raw.get('modelUsage',{}))
    if models!={cfg['model']}:raise ValueError('Claude Code used other models: '+str(sorted(models)))
    text=raw['result'].strip()
    if text.startswith('```'):text=text.split('\n',1)[-1].rsplit('```',1)[0].strip()
    return {'text':text,'usage':raw.get('usage'),'notional_list_usd':raw.get('total_cost_usd'),'billed':'subscription, not the API ledger',
            'requested_model':cfg['model'],'resolved_model':sorted(models)[0],'cli_version':version,'session_id':raw.get('session_id'),
            'raw_response_sha256':digest(result.stdout.encode())}

def run_packets(backend,packets_path,output,repo,run_cap=8,workers=1,adopt=None):
    import judge
    frozen=judge.config();instrument=manifest();packets=judge.read(packets_path);out=Path(output)
    out.mkdir(parents=True,exist_ok=True)
    run_id='judge-v1:'+out.name+':'+backend
    plans={'backend':backend,'instrument_sha256':digest(instrument),'packets_sha256':digest(Path(packets_path).read_bytes()),
           'prompt_sha256':frozen['artifact_sha256']['judge_prompt_v1.txt'],'evaluation_only':True,
           'planned_packets':len(packets),'qualification':Path(packets_path).name=='qualification_blind.jsonl',
           'run_cap_usd':run_cap,'claude_conservative_full_batch_usd':sum(claude_estimate(p) for p in packets) if backend=='claude' else None}
    plan=out/'plan.json'
    if plan.exists() and json.loads(plan.read_text())!=plans:raise ValueError('run identity changed')
    if not plan.exists():plan.write_text(json.dumps(plans,indent=2))
    if backend=='claude' and plans['claude_conservative_full_batch_usd']>run_cap:raise ValueError('whole batch estimate exceeds run cap')
    def one(packet):
        pid=packet['packet_id']
        if not isinstance(pid,str) or not pid.isalnum():raise ValueError('packet id must be opaque alphanumeric')
        dest=out/pid;result_path=dest/'result.json'
        if result_path.exists():
            previous=json.loads(result_path.read_text())
            if previous['packet_sha256']!=digest(packet) or previous['instrument_sha256']!=digest(instrument):raise ValueError('resume identity changed')
            return previous
        if dest.exists():raise ValueError('partial attempt requires explicit investigation, never silent rerun')
        dest.mkdir()
        result={'packet_id':pid,'packet_sha256':digest(packet),**{k:plans[k] for k in ('instrument_sha256','packets_sha256','prompt_sha256')},
                'judge':backend,'model':instrument['judges'][backend]['model'],'evaluation_only':True,'attempt':1}
        started=time.time()
        try:
            if adopt and pid==adopt['packet_id']:
                raw=Path(adopt['path']).read_text();text,usage,events=parse_codex(raw)
                (dest/'events.jsonl').write_text(raw)
                response={'text':text,'usage':usage,'requested_model':result['model'],'resolved_model':None,'cli_version':instrument['judges']['codex']['cli_version'],
                          'binary_sha256':instrument['judges']['codex']['binary_sha256'],'adopted_first_isolation_probe':True,'raw_events_sha256':digest(raw.encode())}
            elif backend in ('codex','codexsol'):response=codex_call(packet,dest,backend)
            elif backend=='claudecode':response=claudecode_call(packet,dest)
            else:response=claude_call(packet,dest,repo,run_id,run_cap)
            result['response']=response
            value=judge.validate(json.loads(response['text']),pid,packet.get('applicable_dimensions'))
            known={e['id'] for e in packet['events']}|{s['id'] for s in packet.get('sources',[])}
            for value_dim in list(value['dimensions'].values())+value['red_flags']:
                if not set(value_dim['event_ids'])<=known:raise ValueError('judge cites nonexistent event/source id')
            result['judgment']=value
        except Exception as error:
            result['error']={'type':type(error).__name__,'message':str(error)[:1000]}
        result['seconds']=round(time.time()-started,3)
        result_path.write_text(json.dumps(result,indent=2))
        print(json.dumps({'judge':backend,'packet':pid,'valid':'judgment' in result}),flush=True)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers if backend in ('codex','codexsol','claudecode') else 1) as pool:
        results=list(pool.map(one,packets))
    target=out/'predictions.jsonl'
    if target.exists():raise ValueError('aggregate already exists')
    target.write_text(''.join(json.dumps(r)+'\n' for r in results))
    return target

def qualify(predictions):
    import judge
    c=judge.config();m=manifest();rows=judge.read(predictions);key=judge.read(ROOT/'qualification_key_v1.jsonl');truth={x['packet_id']:x for x in key}
    blind={x['packet_id']:x for x in judge.read(ROOT/'qualification_blind.jsonl')}
    groups={'positive':[],'negative':[]};errors=[];flags=[];seen=set();backend=None
    for row in rows:
        pid=row.get('packet_id');backend=backend or row.get('judge')
        try:
            if pid in seen:raise ValueError('duplicate output')
            seen.add(pid);t=truth[pid]
            if row.get('fixture'):raise ValueError('fixture cannot qualify')
            if row.get('packet_sha256')!=digest(blind[pid]):raise ValueError('packet digest mismatch')
            if row.get('judgment')!=json.loads(row['response']['text']):raise ValueError('judgment differs from raw response')
            if row.get('judge')!=backend or row.get('model')!=m['judges'][backend]['model']:raise ValueError('backend identity mismatch')
            if row.get('instrument_sha256')!=digest(m) or row.get('prompt_sha256')!=c['artifact_sha256']['judge_prompt_v1.txt'] or row.get('packets_sha256')!=c['artifact_sha256']['qualification_blind.jsonl']:raise ValueError('instrument/input digest mismatch')
            p=judge.validate(row['judgment'],pid,t['applicable_dimensions'])
            for d,status in t.get('expected_status',{}).items():
                if p['dimensions'][d]['status']!=status:raise ValueError('scheduled stage status mismatch')
            groups['positive' if t['expected_suitable'] else 'negative'].append((t,p['suitable_for_training']==t['expected_suitable']))
            if not set(t['required_flags'])<={f['kind'] for f in p['red_flags']}:flags.append(pid)
        except (ValueError,KeyError,TypeError) as error:errors.append(str(pid)+': '+str(error))
    if seen!=set(truth):errors.append('qualification coverage mismatch')
    stats={}
    for label,items in groups.items():
        n=len(items);k=sum(ok for _,ok in items)
        stats[label]={'correct':k,'n':n,'clusters':len({t['cluster_id'] for t,_ in items}),'rate':k/n if n else None,'wilson_95':judge.wilson(k,n,c['z'])}
    passed=not errors and not flags and all(s['clusters']==s['n'] and s['n']>=c['minimum_'+label+'_clusters'] and s['rate']>=c['minimum_rate'] and s['wilson_95'][0]>=c['minimum_wilson_lower'] for label,s in stats.items())
    return {'judge':backend,'instrument_sha256':digest(m),'status':'qualified_on_synthetic_controls' if passed else 'not_qualified',
            'statistics':stats,'errors':errors,'missed_required_flags':flags,'evaluation_only':True,
            'note':'Frozen config_v1 statistical rule and keys, with separately declared API/CLI transport settings. No claim of natural-episode accuracy or training suitability.'}
