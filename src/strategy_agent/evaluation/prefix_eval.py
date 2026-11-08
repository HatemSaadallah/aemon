"""Stage-prefix evaluation: every arm takes over the same teacher episode at the same point. INFERENCE ONLY.

Full runs mostly stop before the test stage, so they say little about test design. Here each accepted teacher episode
on the chosen development cases is replayed through the guarded tools up to the first turn of a stage, by default the
test stage, and the model continues from exactly the state a live run would show. It stops when the investigation
leaves that stage, or at the turn or error limit. The teacher's own turn there is kept as a reference for judges, never
as a correct answer. Arms differ only in the server and --lora-route; prompt, settings and prefixes are identical.

Episodes come from the provenance-checked teacher reports, so a prefix is exactly what a permitted teacher wrote.
Use development companies that were never trained on (Hellberg is held out of training but chose the checkpoint).

Usage: python -m strategy.prefix_eval --reports cap*.json --manifest provenance.jsonl --cases hellberg --url URL
       --model-label LABEL [--lora-route default=0,test=1] --output out.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from strategy_agent.agent.runner import COMPACT, PROMPTS, TOOL_SCHEMA, loaded_adapters, lora_route, play, record_of
from strategy_agent.common.model_client import chat, parse_call
from strategy_agent.common.types import Json, LoraSetting, Message, Schema
from strategy_agent.env.cases import load_cases
from strategy_agent.env.stages import current_stage
from strategy_agent.env.tools import Investigation
from strategy_agent.pipeline.provenance import training_source

if TYPE_CHECKING:
    from strategy_agent.env.tools import Case


def entry_point(record: Json, case: Case, stage: str) -> int | None:
    """Index of the first recorded turn taken in that stage, or None if the episode never reached it."""
    run = Investigation(case, record['settings'].get('complete_workflow', False), True, record['settings'].get('quote_marks', False))
    for index, turn in enumerate(record['model_turns']):
        if current_stage(run).name == stage:
            return index
        call, problem = parse_call(turn['text'], True)
        if call is not None:  # parse_call sets exactly one of call and problem
            run.call(call['name'], call['arguments'])
        if run.final is not None:
            return None
    return None


def prefixes(reports: Sequence[str | Path], manifest: str | Path, selection: str, stage: str) -> list[Any]:
    cases = {c.id: c for c in load_cases()}
    out = []
    for path in reports:
        report = json.loads(Path(path).read_text())
        protocol = (report.get('protocol') or {}).get('id')
        for record in report['records']:
            if not record['case'].startswith(tuple(selection)) or record['final'] is None:
                continue
            case = cases[record['case']]
            source = training_source(record['model_turns'], case, protocol, manifest)  # refuses anything not provably the teacher's
            index = entry_point(record, case, stage)
            if index is not None:
                out.append(
                    {
                        'case': case,
                        'episode': source.episode,
                        'turns': record['model_turns'][:index],
                        'reference': record['model_turns'][index : index + 3],
                        'quote_marks': record['settings'].get('quote_marks', False),
                    }
                )
    return sorted(out, key=lambda p: (p['case'].id, p['episode']))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--reports', nargs='+', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--cases', nargs='+', required=True, help='development case id prefixes, such as hellberg')
    parser.add_argument('--stage', default='test')
    parser.add_argument('--url', required=True)
    parser.add_argument('--model-label', required=True)
    parser.add_argument('--lora-route', help="such as 'default=none' for the base, 'default=0', or 'default=0,test=1'")
    parser.add_argument('--prompt', default='compact')
    parser.add_argument('--max-turns', type=int, default=12)
    parser.add_argument('--max-tokens', type=int, default=520)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    route = lora_route(args.lora_route, loaded_adapters(args.url)) if args.lora_route else None

    def respond(messages: list[Message], seed: int, max_tokens: int, schema: Schema | None, temperature: float, lora: LoraSetting = None) -> Json:
        return chat(args.url, messages, seed, max_tokens, schema, temperature, lora=lora)

    records = []
    for item in prefixes(args.reports, args.manifest, args.cases, args.stage):

        def left(run: Investigation) -> bool:
            return current_stage(run).name != args.stage

        run, info = play(
            item['case'],
            respond,
            PROMPTS[args.prompt],
            args.max_turns,
            4,
            args.max_tokens,
            True,
            TOOL_SCHEMA,
            staged=True,
            compact=args.prompt in COMPACT,
            route=route,
            prefix=item['turns'],
            stop_when=left,
            quote_marks=item['quote_marks'],
        )
        own = [c for c in run.calls if not c.get('prefix')]
        records.append(
            dict(
                record_of(run, info),
                prefix_episode=item['episode'],
                prefix_turns=len(item['turns']),
                teacher_reference=item['reference'],
                outcome={
                    'proposed_test': any(c['name'] == 'propose_test' and c['accepted'] for c in own),
                    'declined_test': any(c['name'] == 'decline_test' and c['accepted'] for c in own),
                    'left_stage': info['stop_reason'] == 'left the stage',
                    'own_calls': len(own),
                    'refused': sum(not c['accepted'] for c in own),
                },
            )
        )
    revision = (
        os.environ.get('CODE_REVISION') or subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, check=False).stdout.strip()
    )
    outcomes = [r['outcome'] for r in records]
    summary = {
        'prefixes': len(records),
        'left_stage': sum(o['left_stage'] for o in outcomes),
        'proposed_test': sum(o['proposed_test'] for o in outcomes),
        'declined_test': sum(o['declined_test'] for o in outcomes),
        'refused_calls': sum(o['refused'] for o in outcomes),
    }
    Path(args.output).write_text(
        json.dumps(
            {
                'inference_only': True,
                'trained': False,
                'code_revision': revision,
                'arguments': vars(args),
                'model': args.model_label,
                'note': 'Development probe. The teacher reference is for judges, not a correct answer.',
                'summary': summary,
                'records': records,
            },
            indent=1,
        )
    )
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
