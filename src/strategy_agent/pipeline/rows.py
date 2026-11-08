"""Training rows from teacher episodes. NOTHING HERE TRAINS.

Each row is exactly what the student will see at run time, rebuilt by replaying the teacher's calls
through the guarded tools: the student's own system prompt, the same tool results and guidance, and
the teacher's actual reply as the target. Replay must consume every recorded turn, reproduce the
recorded call sequence exactly, and reach an accepted finish itself, so a cut or padded stream fails.
Only accepted calls become targets, so a misquote is never taught. An episode is refused unless the
manifest shows a permitted teacher wrote exactly this reply stream, case and protocol, so editing a
target after collection is refused too. Every decision is logged with its reason.

Usage: python -m strategy.rows --reports A.json B.json --manifest provenance.jsonl --output rows.jsonl
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from strategy_agent.agent.runner import PROMPTS, guidance, next_step, state_of
from strategy_agent.common.constants.prompts import START  # noqa: F401
from strategy_agent.common.model_client import parse_call
from strategy_agent.common.paths import REVIEW
from strategy_agent.common.types import Json, Message
from strategy_agent.env.cases import load_cases
from strategy_agent.env.checks import guards_cleared
from strategy_agent.env.stages import current_stage
from strategy_agent.env.tools import Investigation
from strategy_agent.evaluation.audit import ReplayMismatch
from strategy_agent.pipeline.provenance import PROVENANCE, training_source

if TYPE_CHECKING:
    from transformers import PreTrainedTokenizerBase

    from strategy_agent.env.tools import Case


def transcript(record: Json, case: Case, system: str, compact: bool = False) -> tuple[list[Any], Investigation]:
    """The conversation as the model saw it, with each assistant turn marked trainable or not."""
    settings = record.get('settings', {})
    staged = settings.get('staged', False)
    run = Investigation(case, settings.get('complete_workflow', False), staged, settings.get('quote_marks', False), settings.get('reread_limit'))
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': START}]
    turns = []
    for index, turn in enumerate(record['model_turns']):
        if run.final is not None:
            raise ReplayMismatch('turns continue after the investigation finished')
        stage = current_stage(run).name if staged else None
        call, problem = parse_call(turn['text'], True)
        result = run.call(call['name'], call['arguments']) if call is not None else {'error': problem}
        if json.dumps(result, sort_keys=True) != json.dumps(turn['tool_result'], sort_keys=True):
            raise ReplayMismatch(f'turn {index + 1} returned something else on replay')
        reply = {'role': 'assistant', 'content': turn['text'], 'train': not problem and 'error' not in result, 'stage': stage}
        turns.append(messages + [reply])
        if run.final is not None:
            continue
        shown = {**result, **guidance(run)} if staged else dict(result, next=next_step(run))
        if compact:
            messages = [messages[0], {'role': 'user', 'content': state_of(run, shown)}]
        else:
            messages = messages + [{'role': 'assistant', 'content': turn['text']}, {'role': 'user', 'content': 'Tool result: ' + json.dumps(shown)}]
    recorded = [[c['name'], c['arguments'], c['accepted']] for c in record['calls']]
    if [[c['name'], c['arguments'], c['accepted']] for c in run.calls] != recorded:
        raise ReplayMismatch('the replayed calls differ from the recorded call sequence')
    return turns, run


def turn_rows(turns: list[list[Message]]) -> list[Json]:
    """One row per accepted call: the context it saw, and that call as the only target."""
    return [
        {'messages': [{k: v for k, v in m.items() if k not in ('train', 'stage')} for m in turn], 'target_index': len(turn) - 1, 'stage': turn[-1]['stage']}
        for turn in turns
        if turn[-1]['train']
    ]


class Overlength(ValueError):
    pass


def labels_for(tokenizer: PreTrainedTokenizerBase, row: Json, limit: int) -> Json:
    """Loss on the target reply only. The context is tokenized on its own and must be an exact prefix of
    the whole, or a mask would land on the wrong tokens. A row over the limit is refused, never cut."""
    messages, index = row['messages'], row['target_index']
    before = tokenizer(cast(str, tokenizer.apply_chat_template(messages[:index], tokenize=False, add_generation_prompt=True)), add_special_tokens=False)[
        'input_ids'
    ]
    ids = tokenizer(cast(str, tokenizer.apply_chat_template(messages[: index + 1], tokenize=False)), add_special_tokens=False)['input_ids']
    if list(ids[: len(before)]) != list(before):
        raise ValueError('the context tokens are not a prefix of the full row, so the loss mask would be wrong')
    if len(ids) > limit:
        raise Overlength(f'row of {len(ids)} tokens is over the limit of {limit}')
    return {'input_ids': ids, 'attention_mask': [1] * len(ids), 'labels': [-100] * len(before) + list(ids[len(before) :])}


def build(
    reports: Sequence[str | Path],
    manifest: str | Path = PROVENANCE,
    prompt: str = 'staged',
    compact: bool = False,
    exclude: Iterable[str] = (),
    require_finished: bool = True,
) -> tuple[list[Any], list[Any]]:
    """Every episode is accepted or rejected with a reason. Held-out cases are never used."""
    cases = {c.id: c for c in load_cases()}
    excluded: dict[str, Any] = json.loads(REVIEW.read_text()) if REVIEW.exists() else {}
    rows, decisions = [], []
    for path in reports:
        if str(path).endswith('.jsonl'):  # a stage still running: its episode log, with the config first
            lines = [json.loads(line) for line in Path(path).read_text().splitlines()]
            report = {'protocol': lines[0]['config']['protocol'], 'records': [line for line in lines[1:] if 'case' in line]}
        else:
            report = json.loads(Path(path).read_text())
        protocol = (report.get('protocol') or {}).get('id')
        for record in report['records']:
            decision = {'report': str(path), 'case': record['case'], 'episode': record.get('episode')}
            try:
                if record['case'] in exclude:
                    raise ValueError('held-out case')
                case = cases[record['case']]
                source = training_source(record['model_turns'], case, protocol, manifest)
                if source.episode in excluded:  # replay-valid but judged weak on review; the original stays recorded
                    raise ValueError(f'excluded after review: {excluded[source.episode]["reason"]}')
                turns, replayed = transcript(record, case, PROMPTS[prompt], compact)
                if require_finished and replayed.final is None:
                    raise ValueError('replay did not reach an accepted finish')
                made = turn_rows(turns)
                for index, row in enumerate(made):
                    row.update(case=record['case'], episode=source.episode, turn=index, teacher_weights=source.weights_sha256)
                rows += made
                decisions.append(dict(decision, accepted=True, rows=len(made), guards_cleared=guards_cleared(record['checks'])))
            except (ValueError, ReplayMismatch, KeyError) as error:
                decisions.append(dict(decision, accepted=False, reason=str(error)))
    return rows, decisions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--reports', nargs='+', required=True)
    parser.add_argument('--manifest', default=str(PROVENANCE))
    parser.add_argument('--prompt', default='staged', help='the student prompt the rows will be trained under')
    parser.add_argument('--compact', action='store_true')
    parser.add_argument('--exclude', nargs='*', default=[], help='held-out case ids, never used')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error('rows are never overwritten')
    rows, decisions = build(args.reports, args.manifest, args.prompt, args.compact, set(args.exclude))
    output.write_text(''.join(json.dumps(r) + '\n' for r in rows))
    output.with_suffix('.decisions.json').write_text(json.dumps(decisions, indent=1))
    print(
        json.dumps(
            {
                'rows': len(rows),
                'accepted': sum(d['accepted'] for d in decisions),
                'rejected': [(d['case'], d['reason']) for d in decisions if not d['accepted']],
            },
            indent=1,
        )
    )


if __name__ == '__main__':
    main()
