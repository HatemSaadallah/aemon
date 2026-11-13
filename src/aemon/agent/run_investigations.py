"""Whole investigations on the real model, from the command line. NO TRAINING. Case content is labelled by class.

Assumes llama-server on --url (or --backend claude, a positive control that is never training data). Each episode is
written to disk before the next starts, and results are never overwritten.

Usage: python -m aemon.agent.run_investigations --prompt compact --cases hellberg-base --output run.json
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import threading
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

from aemon.agent.adapter_routing import loaded_adapters, lora_route
from aemon.agent.backends.claude_control import MODEL as CLAUDE_MODEL
from aemon.agent.backends.claude_control import Claude
from aemon.agent.backends.llama_client import chat
from aemon.agent.loop import play
from aemon.agent.records import model_of, protocol_of, record_of, server_props, suite_of, summary
from aemon.agent.state_view import with_status
from aemon.agent.tool_schemas import TOOL_SCHEMA
from aemon.common.constants.prompts import COMPACT, PROMPTS, REASONED, STRUCTURED
from aemon.environment.cases import load_cases
from aemon.rows.provenance import PROVENANCE, record_provenance

if TYPE_CHECKING:
    from aemon.environment.tools import Case


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8091')
    parser.add_argument('--prompt', choices=sorted(PROMPTS), default='strong')
    parser.add_argument('--cases', default='all')
    parser.add_argument('--split', choices=('development', 'heldout', 'heldout2'), default='development', help='heldout and heldout2 only for the two test sets')
    parser.add_argument('--max-turns', type=int, default=45)
    parser.add_argument('--max-errors', type=int, default=4, help='errors in a row before stopping')
    parser.add_argument('--reread-limit', type=int, help='refuse reading one source more than this many times (off by default, as evaluated)')
    parser.add_argument('--source-dates', action='store_true', help="list each source's date in the state (off by default, as evaluated)")
    parser.add_argument('--status-check', action='store_true', help='company_status right after framing, and finish must cite a status source it read (off by default, as evaluated)')
    parser.add_argument('--min-assessed', type=int, default=1, help='weighed sources each theory needs before moving on (1 as evaluated)')
    parser.add_argument('--stuck-help', action='store_true', help='after two refusals in a row, say what the agent can do instead (off by default, as evaluated)')
    parser.add_argument('--recovery', default='', help="experimental recovery features, comma-separated (docs/RECOVERY_EXPERIMENT.md); off as evaluated; development only, except the adopted guards, also allowed on the test sets (exploratory)")
    parser.add_argument('--max-tokens', type=int, default=520)
    parser.add_argument('--context', type=int, default=12288, help='the server context size, recorded with the run')
    parser.add_argument('--output', required=True)
    parser.add_argument('--backend', choices=('llama', 'claude'), default='llama', help='claude is a positive control and never training data')
    parser.add_argument('--model-label', default='tiny-aya-global-q4_k_m.gguf a602ea7', help='what llama-server is serving, recorded with the run')
    parser.add_argument('--weights-sha256', help='the hash of the served weights, which decides whether a run can be a teacher')
    parser.add_argument('--manifest', default=str(PROVENANCE), help='the append-only record of where each episode came from')
    parser.add_argument('--temperature', type=float, default=0, help='the baselines stay at 0, and only teacher attempts vary')
    parser.add_argument('--attempts', type=int, default=1, help='runs per case, each with its own seed')
    parser.add_argument('--workers', type=int, default=1, help='episodes run at once, which needs the same number of server slots')
    parser.add_argument('--first-attempt', type=int, default=0, help='so a later stage gets new seeds rather than repeating an earlier one')
    parser.add_argument('--server-settings', help='JSON of how the server was started, such as {"reasoning_budget": 512}; recorded in every manifest entry')
    parser.add_argument('--lora-route', help="stage to adapter id, such as 'default=0,test=1', for adapters loaded on the server; 'stuck=ID' (with 'stuck_after=N', default 2) hands a turn to another adapter after N refusals in a row")
    parser.add_argument('--effort', default='medium', help='claude backend only')
    parser.add_argument('--run-cap-usd', type=float, default=5.0, help='claude backend only')
    args = parser.parse_args()
    recovery_features = tuple(f for f in args.recovery.split(',') if f)
    # Experimental features run on development only. On test set 2 and the final test only the loop guards adopted on
    # development and the budget guard with them (DECISIONS 2026-11-12 05:20, 06:40 and 16:30), and the two features taken
    # forward from the development screens of 18:15 and 19:55 (DECISIONS 21:55), may run, labelled exploratory (both sets
    # have been run before; the final test's frozen result stands).
    adopted = {'no_repeats', 'quote_menu', 'resample_repeats', 'budget', 'grounded_beliefs', 'evidence_first'}
    if recovery_features and args.split != 'development' and not (args.split in ('heldout', 'heldout2') and set(recovery_features) <= adopted):
        parser.error('recovery features are experimental: development only, except the adopted loop guards on test set 2 and the final test')
    if args.backend == 'claude':
        respond = Claude(f'control {args.prompt}', args.run_cap_usd, args.effort)
        model, runtime = CLAUDE_MODEL, f'Anthropic API, effort {args.effort}, no seed or temperature, so runs do not repeat exactly'
        model_id = model_of('claude', model)
    else:
        respond = lambda messages, seed, max_tokens, schema, temperature, lora=None: chat(args.url, messages, seed, max_tokens, schema, temperature, lora=lora)  # noqa: E731
        model, runtime = args.model_label, 'llama.cpp b12032, temperature 0, 0.4 only on a retry straight after a rejected call'
        model_id = model_of('llama', model, args.weights_sha256, server_props(args.url), json.loads(args.server_settings) if args.server_settings else None)
    cases = load_cases(args.cases, split=args.split)
    system = with_status(PROMPTS[args.prompt]) if args.status_check else PROMPTS[args.prompt]
    revision = (
        os.environ.get('CODE_REVISION') or subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, check=False).stdout.strip()
    )
    dirty = bool(subprocess.run(['git', 'status', '--porcelain', '--', 'src', 'data'], capture_output=True, text=True, check=False).stdout.strip())
    config = {
        'inference_only': True,
        'trained': False,
        'code_revision': revision,
        'uncommitted_changes': dirty,
        'arguments': vars(args),
        'system_prompt': system,
        'tool_schema': TOOL_SCHEMA,
        'guidance_in_tool_results': args.prompt != 'plain',
        'finish_needs_every_stage': args.prompt == 'workflow',
        'stage_controller': args.prompt in STRUCTURED,
        'server_context': args.context,
        'model': model,
        'runtime': runtime,
        'protocol': protocol_of(
            system,
            {
                'prompt': args.prompt,
                'split': args.split,
                'max_turns': args.max_turns,
                'consecutive_errors': args.max_errors,
                'max_tokens': args.max_tokens,
                'context': args.context,
                'temperature': args.temperature,
                'retry_temperature': 0.4,
            },
        ),
        'suite': suite_of(cases, args.attempts) | {'first_attempt': args.first_attempt},
        'model_identity': model_id,
    }
    output = Path(args.output)
    if output.exists() or output.with_suffix('.episodes.jsonl').exists():
        parser.error(f'{output} already exists, and results are never overwritten')
    output.parent.mkdir(parents=True, exist_ok=True)
    records, errors, lock = [], [], threading.Lock()
    jobs = [(c, a) for c in cases for a in range(args.first_attempt, args.first_attempt + args.attempts)]

    def one(job: tuple[Case, int]) -> None:
        """One episode. Each has its own seed and investigation, so episodes never share state."""
        case, attempt = job
        try:
            run, info = play(
                case,
                respond,
                system,
                args.max_turns,
                args.max_errors,
                args.max_tokens,
                args.prompt != 'plain',
                TOOL_SCHEMA,
                args.prompt == 'assisted',
                args.prompt == 'workflow',
                args.prompt in STRUCTURED,
                temperature=args.temperature,
                attempt=attempt,
                reasoned=args.prompt in REASONED,
                compact=args.prompt in COMPACT,
                route=lora_route(args.lora_route, loaded_adapters(args.url)) if args.lora_route else None,
                reread_limit=args.reread_limit,
                source_dates=args.source_dates,
                status_check=args.status_check,
                stuck_help=args.stuck_help,
                min_assessed=args.min_assessed,
                recovery_features=recovery_features,
            )
            record = dict(record_of(run, info), attempt=attempt)
            with lock:
                record['episode'] = record_provenance(info['turns'], case, model_id, config['protocol']['id'], args.manifest)
        except Exception:  # noqa: BLE001  one bad episode must not lose the rest
            with lock:
                errors.append({'case': case.id, 'attempt': attempt, 'error': traceback.format_exc(limit=3)})
                log.write(json.dumps({'harness_error': errors[-1]}) + '\n')
                log.flush()
            return
        with lock:
            records.append(record)
            log.write(json.dumps(record) + '\n')
            log.flush()
            os.fsync(log.fileno())
            print(
                json.dumps(
                    {
                        'case': case.id,
                        'attempt': attempt,
                        'stop': info['stop_reason'],
                        'turns': len(info['turns']),
                        'passed': sum(bool(c['passed']) for c in record['checks'].values()),
                        'failed': [k for k, c in record['checks'].items() if c['passed'] is False],
                    }
                ),
                flush=True,
            )

    with open(output.with_suffix('.episodes.jsonl'), 'w') as log:
        log.write(json.dumps({'config': config}) + '\n')
        log.flush()
        if args.workers > 1:  # the server batches concurrent episodes, which is much faster for a large model
            with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
                list(pool.map(one, jobs))
        else:
            for job in jobs:
                one(job)
    order = {(c.id, a): i for i, (c, a) in enumerate(jobs)}
    records.sort(key=lambda r: order[(r['case'], r['attempt'])])
    report = dict(config, prompt=args.prompt, summary=summary(records), harness_errors=errors, records=records)
    try:
        from aemon.evaluation.diagnostics.audit import audit

        report['auditkit'] = audit(records, cases)
    except ImportError as error:
        report['auditkit'] = {'skipped': str(error)}
    output.write_text(json.dumps(report, indent=1))
    print(json.dumps({'summary': report['summary'], 'auditkit': report['auditkit']}, indent=1))
    refused = [r['case'] for r in records if str(r['stop_reason']).startswith('server refused')]
    if errors or refused or not records:  # a server fault must never read as model behaviour
        raise SystemExit(f'{len(errors)} episodes failed in the harness, and the server refused {refused}')


if __name__ == '__main__':
    main()
