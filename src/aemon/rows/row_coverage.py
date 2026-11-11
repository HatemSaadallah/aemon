"""Which training rows survive the length limit, by stage and company, and whether each target is grounded.

A row over the limit is refused, never cut, so long late stages can silently vanish from training. This
builds the rows both ways, full history and compact state, from the same teacher reports, and reports:
retention and token lengths by stage, retention by company, episodes attempted, accepted and rejected
with reasons, and targets that name an evidence, theory or test id, or a number, missing from their context.
NOTHING HERE TRAINS.

Usage: python -m aemon.rows.row_coverage --reports cap*.json --manifest provenance.jsonl --tokenizer DIR --output coverage.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aemon.common.constants.pipeline import LATE  # noqa: F401
from aemon.common.types import Json
from aemon.environment.cases import load_cases  # noqa: E402
from aemon.rows.build_rows import Overlength, build, labels_for  # noqa: E402

if TYPE_CHECKING:
    from transformers import PreTrainedTokenizerBase

    from aemon.environment.tools import Case

NUMBER = re.compile(r'(?<![A-Za-z0-9])\d[\d,.]*\d|(?<![A-Za-z0-9])\d(?![A-Za-z0-9])')


def ungrounded(row: Json, case: Case) -> tuple[list[str | Any | Any], list[Any | Any]]:
    """Ids and numbers the target names that its context never shows."""
    target = row['messages'][row['target_index']]['content']
    context = ' '.join(m['content'] for m in row['messages'][: row['target_index']])
    ids = set(case.dossier.records) | ({case.shock.id} if case.shock else set())
    named = {i for i in ids if i in target} | set(re.findall(r'"(T\d+|X\d+)"', target))
    numbers = set()
    if row['stage'] in LATE:
        numbers = {n for n in NUMBER.findall(json.dumps(json.loads(target).get('arguments', {}))) if len(n.strip('.,')) > 1}
    return [i for i in named if i not in context], [n for n in numbers if n.strip('.,') not in context]


def coverage(reports: Sequence[str | Path], manifest: str | Path, tokenizer: PreTrainedTokenizerBase, limit: int, prompt: str, compact: bool) -> Json:
    cases = {c.id: c for c in load_cases()}
    rows, decisions = build(reports, manifest, prompt, compact)
    stages = defaultdict(lambda: {'kept': 0, 'refused': 0, 'lengths': [], 'ungrounded_ids': 0, 'new_numbers': 0})
    companies = defaultdict(Counter)
    for row in rows:
        stage, company = stages[row['stage']], row['case'].split('-')[0]
        try:
            length = len(labels_for(tokenizer, row, limit)['input_ids'])
            stage['kept'] += 1
            companies[company]['kept'] += 1
        except Overlength as error:
            length = int(str(error).split()[2])
            stage['refused'] += 1
            companies[company]['refused'] += 1
        stage['lengths'].append(length)
        ids, numbers = ungrounded(row, cases[row['case']])
        stage['ungrounded_ids'] += bool(ids)
        stage['new_numbers'] += bool(numbers)
    by_stage = {}
    for name, s in stages.items():
        lengths = sorted(s.pop('lengths'))
        by_stage[name] = dict(s, retained=round(s['kept'] / (s['kept'] + s['refused']), 2), median_tokens=lengths[len(lengths) // 2], max_tokens=lengths[-1])
    return {
        'prompt': prompt,
        'compact': compact,
        'limit': limit,
        'rows': len(rows),
        'by_stage': by_stage,
        'by_company': {k: dict(v) for k, v in sorted(companies.items())},
        'episodes': {
            'attempted': len(decisions),
            'accepted': sum(d['accepted'] for d in decisions),
            'rejected': dict(Counter(d['reason'] for d in decisions if not d['accepted'])),
            'attempted_by_company': dict(Counter(d['case'].split('-')[0] for d in decisions)),
            'accepted_by_company': dict(Counter(d['case'].split('-')[0] for d in decisions if d['accepted'])),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--reports', nargs='+', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--tokenizer', required=True)
    parser.add_argument('--limit', type=int, default=8192)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)
    out = {
        'note': 'Rows from the same teacher episodes, built two ways. Rows are not independent: many come from each episode.',
        'full_history': coverage(args.reports, args.manifest, tokenizer, args.limit, 'staged', False),
        'compact': coverage(args.reports, args.manifest, tokenizer, args.limit, 'compact', True),
    }
    Path(args.output).write_text(json.dumps(out, indent=1))
    for mode in ('full_history', 'compact'):
        print(mode, {k: f'{v["kept"]}/{v["kept"] + v["refused"]}' for k, v in out[mode]['by_stage'].items()})


if __name__ == '__main__':
    main()
