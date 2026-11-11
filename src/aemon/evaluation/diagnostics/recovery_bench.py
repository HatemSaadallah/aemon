"""Failure-state benchmark and ablation runner (docs/RECOVERY_EXPERIMENT.md, phases C and E). NOTHING HERE TRAINS.

build: from recorded version 1 runs on training companies (and, as a separate exploratory stratum, development runs
       for the simulated-evidence failure), take each failed episode's dead end, the state just after its last
       progress, as one checkpoint. One checkpoint per episode; stratified by the step and termination of the dead end;
       held-out and test-set-2 cases are refused.
run:   resume every checkpoint under configurations A-F with the same weights, prompt, decoding, seeds, remaining turns
       and refusal count, and write one result per checkpoint and configuration.

    python -m aemon.evaluation.diagnostics.recovery_bench build --reports R1.json R2.json --dev DEV.jsonl --out MANIFEST.json
    python -m aemon.evaluation.diagnostics.recovery_bench run --manifest MANIFEST.json --url URL --configs A,B,C,D,E,F --out RESULTS.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from aemon.agent.adapter_routing import lora_route, loaded_adapters
from aemon.agent.loop import play
from aemon.agent.records import record_of
from aemon.agent.tool_schemas import TOOL_SCHEMA
from aemon.common.constants.prompts import PROMPTS
from aemon.agent.backends.llama_client import chat, parse_call
from aemon.environment.cases import load_cases
from aemon.environment.checks import guards_cleared
from aemon.common.constants.env import WORKFLOW
from aemon.environment.tools import Investigation
from aemon.evaluation.diagnostics.failures import classify, replay_progress
from aemon.data.splits import is_validation

VERSION = 'recovery-bench-v1'
CONFIGS = {
    'A': (), 'B': ('mask_rereads',), 'C': ('progress',), 'D': ('budget',), 'E': ('citations',),
    'F': ('mask_rereads', 'progress', 'budget', 'citations'),
}
MAX_TURNS, MAX_ERRORS, MAX_TOKENS = 45, 4, 520  # the evaluated settings
QUOTAS = {('theories', 'repeated errors'): 8, ('theories', 'turn limit'): 5, ('test', 'turn limit'): 6, ('test', 'repeated errors'): 5}
OTHER = 6  # every other dead end up to this many


def _sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _checkpoint(record: dict, case: Any, source: str, stratum: str) -> dict | None:
    steps = replay_progress(record, case)
    last = max((s['i'] for s in steps if s['progress']), default=-1)
    if last + 1 >= len(steps):
        return None
    target = last + 1  # the first call of the dead end
    s = record['settings']
    run = Investigation(case, s.get('complete_workflow', False), True, s.get('quote_marks', False), s.get('reread_limit'),
                        s.get('source_dates', False), s.get('min_assessed', 1), status_check=s.get('status_check', False))
    prefix = []
    for turn in record['model_turns']:
        if len(run.calls) >= target:
            break
        call, problem = parse_call(turn['text'], True)
        result = run.call(call['name'], call['arguments']) if call is not None else {'error': problem}
        assert json.dumps(result, sort_keys=True) == json.dumps(turn['tool_result'], sort_keys=True)
        prefix.append({'text': turn['text'], 'tool_result': turn['tool_result']})
    errors = 0
    for turn in reversed(prefix):
        if 'error' not in turn['tool_result']:
            break
        errors += 1
    label = classify(record, case)
    return {
        'id': hashlib.sha256((record['case'] + str(record.get('attempt')) + source + str(len(prefix))).encode()).hexdigest()[:12],
        'case': record['case'], 'company': record['case'].split('-')[0], 'attempt': record.get('attempt', 0),
        'split': 'validation' if is_validation(record['case']) else 'training', 'stratum': stratum,
        'stage': steps[target]['stage'], 'original_stop': record['stop_reason'], 'failure_types': label['types'],
        'earliest_failure': label['earliest'], 'prefix_turns': len(prefix), 'turns_left': MAX_TURNS - len(prefix),
        'errors_at_start': errors, 'searches_used': len(run.searches), 'settings': s, 'source': source,
        'original_calls_after': len(record['calls']) - target, 'prefix': prefix,
    }


def build(reports: list[str], dev: str | None, seed: int = 20261109) -> dict:
    cases = {c.id: c for c in load_cases()}
    rng = random.Random(seed)
    pools: dict[tuple, list] = defaultdict(list)
    sources = {}
    for path in reports:
        data = json.loads(Path(path).read_text())
        sources[path] = {'sha256': _sha(path), 'code_revision': data.get('code_revision'), 'protocol': (data.get('protocol') or {}).get('id'),
                         'model_identity': data.get('model_identity')}
        for record in data['records']:
            if record.get('final') is not None or record['case'] not in cases or is_validation(record['case']):
                continue
            cp = _checkpoint(record, cases[record['case']], path, '')
            if cp:
                pools[(cp['stage'], cp['original_stop'])].append(cp)
    chosen, companies = [], defaultdict(int)
    for key in sorted(pools, key=str):
        quota = QUOTAS.get(key)
        group = sorted(pools[key], key=lambda c: c['id'])
        rng.shuffle(group)
        group.sort(key=lambda c: companies[c['company']])  # spread over companies
        take = group[:quota] if quota else group
        for cp in take:
            if quota is None and sum(1 for c in chosen if c['stratum'] == 'other') >= OTHER:
                break
            cp['stratum'] = f'{key[0]} / {key[1]}' if quota else 'other'
            companies[cp['company']] += 1
            chosen.append(cp)
    if dev:  # exploratory stratum: the simulated-evidence dead end at the conclusion only occurs in development cases
        sources[dev] = {'sha256': _sha(dev), 'note': 'development (validation) runs, exploratory stratum only'}
        for line in Path(dev).read_text().splitlines():
            record = json.loads(line) if line.strip() else {}
            if 'calls' not in record or record.get('final') is not None:
                continue
            if 'D' not in classify(record, cases[record['case']])['types']:
                continue
            cp = _checkpoint(record, cases[record['case']], dev, 'exploratory: simulated evidence (development)')
            if cp and cp['stage'] in ('conclude', 'update', 'new_evidence', 'position'):
                chosen.append(cp)
    return {'version': VERSION, 'seed': seed, 'created': time.strftime('%Y-%m-%dT%H:%M:%S'), 'sources': sources,
            'max_turns': MAX_TURNS, 'max_errors': MAX_ERRORS, 'max_tokens': MAX_TOKENS, 'prompt': 'compact', 'checkpoints': chosen}


def stage_index(name: str) -> int:
    order = [w['stage'] for w in WORKFLOW] + ['done']
    return order.index(name) if name in order else -1


def resume(cp: dict, features: tuple, respond: Any, route: Any) -> dict:
    case = {c.id: c for c in load_cases()}[cp['case']]
    s = cp['settings']
    started = time.time()
    run, info = play(case, respond, PROMPTS['compact'], cp['turns_left'], MAX_ERRORS, MAX_TOKENS, True, TOOL_SCHEMA, staged=True,
                     compact=True, quote_marks=s.get('quote_marks', True), attempt=cp['attempt'], prefix=cp['prefix'],
                     errors_at_start=cp['errors_at_start'], recovery_features=features, route=route,
                     reread_limit=s.get('reread_limit'), source_dates=s.get('source_dates', False), min_assessed=s.get('min_assessed', 1), status_check=s.get('status_check', False))
    record = record_of(run, info)
    new = [c for c in record['calls'] if not c.get('prefix')]
    steps = replay_progress(record, case)[cp['prefix_turns'] and len(record['calls']) - len(new):]
    progress = [x for x in steps if x['progress']]
    end_stage = steps[-1]['stage'] if steps else cp['stage']
    from aemon.environment.stages import current_stage
    final_stage = current_stage(run).name
    return {
        'checkpoint': cp['id'], 'features': list(features), 'stop_reason': info['stop_reason'], 'finished': run.final is not None,
        'guards_cleared': guards_cleared(record['checks']) if run.final is not None else False,
        'checks_failed': sorted(k for k, v in record['checks'].items() if v.get('passed') is False),
        'calls': len(new), 'accepted': sum(c['accepted'] for c in new), 'refused': sum(not c['accepted'] for c in new),
        'refused_by_category': {k: sum(1 for c in new if not c['accepted'] and c.get('category') == k) for k in {c.get('category') for c in new if not c['accepted']}},
        'progress_calls': len(progress), 'first_progress_at': (progress[0]['i'] - steps[0]['i'] + 1) if progress else None,
        'stage_at_start': cp['stage'], 'stage_at_end': final_stage, 'advanced': stage_index(final_stage) > stage_index(cp['stage']) or run.final is not None,
        'synthetic_citation_refusals': sum(1 for c in new if c.get('category') == 'synthetic_as_evidence'),
        'rereads': sum(1 for c in new if c['name'] == 'read_source' and c['accepted'] and sum(1 for x in record['calls'][:record['calls'].index(c)] if x['name'] == 'read_source' and x['accepted'] and (x.get('arguments') or {}).get('id') == (c.get('arguments') or {}).get('id'))),
        'prompt_tokens': sum(t.get('prompt_tokens', 0) for t in info['turns']), 'completion_tokens': sum(t.get('completion_tokens', 0) for t in info['turns']),
        'seconds': round(time.time() - started, 1), 'end_stage_last_call': end_stage,
        'record': {k: record[k] for k in ('final', 'stop_reason', 'settings', 'checks')} | {'calls': new},
    }


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    b.add_argument('--reports', nargs='+', required=True)
    b.add_argument('--dev')
    b.add_argument('--out', required=True)
    r = sub.add_parser('run')
    r.add_argument('--manifest', required=True)
    r.add_argument('--url', required=True)
    r.add_argument('--configs', default='A,B,C,D,E,F')
    r.add_argument('--adapter', default='final_adapter.gguf', help='which loaded adapter to switch on (by file name)')
    r.add_argument('--adapter-index', type=int, help='its index on the server, when names are not reported')
    r.add_argument('--out', required=True)
    r.add_argument('--label', default='', help='runtime label recorded with every result')
    args = p.parse_args()
    if args.command == 'build':
        manifest = build(args.reports, args.dev)
        Path(args.out).write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
        counts = defaultdict(int)
        for cp in manifest['checkpoints']:
            counts[cp['stratum']] += 1
        print(json.dumps({'checkpoints': len(manifest['checkpoints']), 'by_stratum': counts, 'companies': len({c['company'] for c in manifest['checkpoints']})}, indent=1))
        return
    manifest = json.loads(Path(args.manifest).read_text())
    n = loaded_adapters(args.url)
    index = args.adapter_index if args.adapter_index is not None else 0
    lora = [{'id': i, 'scale': 1.0 if i == index else 0.0} for i in range(n)]

    def respond(messages, seed, max_tokens, schema, temperature, lora=None):  # noqa: ANN001, ANN202
        return chat(args.url, messages, seed, max_tokens, schema, temperature, lora=lora)

    done = set()
    out = Path(args.out)
    if out.exists():
        done = {(json.loads(x)['checkpoint'], json.loads(x)['config']) for x in out.read_text().splitlines() if x.strip()}
    with out.open('a') as f:
        for cp in manifest['checkpoints']:
            for config in args.configs.split(','):
                if (cp['id'], config) in done:
                    continue
                result = resume(cp, CONFIGS[config], respond, (lambda stage: lora) if n else None)
                result.update(config=config, manifest_version=manifest['version'], runtime=args.label, adapter_index=index)
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
                f.flush()
                print(cp['id'], config, result['stop_reason'], result['advanced'], result['calls'], flush=True)


if __name__ == '__main__':
    main()
