"""An LLM reviewer (DeepSeek V4-Pro) for the corrective examples, in place of the human Keep/Drop review. NO TRAINING.

Hatem's decision of 2026-11-10: DeepSeek reviews the examples. Recorded in docs/DECISIONS.md with its qualification
rule, fixed before it ran. The reviewer is a different model from the one that wrote the answers (V4-Flash), sees each
exported example exactly as the Review page shows it (state, call, full reasoning, keyword flags), and applies the
written rubric below, built from the criteria of the earlier human reviews and the plan's substantive review (section 9).

    python -m aemon.teacher.hosted_review qualify --output Q.json       # against Hatem's 6 decisions
    python -m aemon.teacher.hosted_review review BATCH.json            # writes keep into unreviewed examples

A human decision is never overwritten: only examples whose keep is null are reviewed. Each decision is written with
reviewed_by "deepseek-v4-pro (LLM reviewer)", review_source "llm", its problems and what it teaches.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

from aemon.agent.backends import hosted_client
from aemon.common.types import Json

REVIEWER = 'deepseek-v4-pro'
HUMAN = ['reviews/v2_round2/targeted3_kept_for_review.json', 'reviews/v2_round2/targeted4_kept_for_review.json']
HIDDEN = ('keep', 'review_note', 'reviewed_by', 'reviewed_at', 'review_source', 'note_check', 'llm_review')

RUBRIC = """You review training examples for a small model that learns to investigate strategy questions for manufacturers
(frame the decision, rival causal theories, weigh quoted evidence, design a test or decline one, recommend). Each example
is one step: the state of an investigation (question, the case's date, theories, sources read with their dates) and the
call a teacher model made there, with its reasoning. Only examples you keep will be trained on, so keep an example only
if it shows a careful strategy analyst's correct move at that point. When in doubt, drop.

Drop if any of these holds.
Experiment design (propose_test or decline_test):
- the arms differ only in wording, framing, copy, message or positioning of the same product at the same price, without
  a same-price control; or the test is survey-only stated preference (intent, Likert) with no behaviour or commitment;
- the predictions do not discriminate: both theories predict the same result, or one rival is a strawman or a variant of
  the other that the answer itself treats as unsupported;
- the decision rule jumps to developing, launching or scaling a product line, sub-brand or proposition instead of a
  bounded next step; or it has no threshold that a result could clearly meet or miss;
- the commitment asked of participants is trivial for the decision (a token deposit for an expensive product);
- it declines a test in a case where a feasible, decision-relevant test exists, or its decline contradicts its own
  reasoning (why_next describes a test, or the reason says a test could settle it).
Evidence and grounding:
- it relies on a source dated after the case's date for what was knowable then, or prices in a currency or uses facts
  from a later period;
- it labels encyclopedia, company-history, press or news text as an independent study, or says a source shows more than
  its quote does; does_not_show is empty, generic or wrong;
- it uses a number, price, percentage, age range or date not in a cited source, or cites sources read but never weighed.
Reasoning and progress:
- learned, uncertain or why_next is empty, generic, or contradicts the call (it says one thing and does another);
- the call does not move the investigation forward (rereads a source already read, repeats a call, or ignores what the
  state says is needed next);
- a revision of belief is disproportionate to the new evidence or not linked to it.

Keep only if none of these holds and the call is right for the state, grounded in named sources and theories of the
state, with complete, specific reasoning. Do not drop an example only because a text field is long or because of a
tool's character limit: limits are checked separately. The flags are keyword hints, not judgments."""

SCHEMA: Json = {
    'type': 'object', 'additionalProperties': False, 'required': ['keep', 'problems', 'teaches', 'confidence'],
    'properties': {
        'keep': {'type': 'boolean'},
        'problems': {'type': 'array', 'items': {'type': 'string'}},
        'teaches': {'type': 'string'},
        'confidence': {'type': 'string', 'enum': ['low', 'medium', 'high']},
    },
}


def shown(example: Json) -> Json:
    return {k: v for k, v in example.items() if k not in HIDDEN}


def review_one(example: Json) -> Json:
    messages = [{'role': 'system', 'content': RUBRIC},
                {'role': 'user', 'content': 'Review this example. Answer with the answer tool.\n\n' + json.dumps(shown(example), ensure_ascii=False, indent=1)}]
    reply = hosted_client.chat('hosted', messages, 0, 4000, SCHEMA, 0.0)
    try:
        verdict = json.loads(reply['text'])
    except json.JSONDecodeError:
        return {'error': reply['text'][:300]}
    return verdict


def review_all(examples: list[Json], workers: int = int(os.environ.get('REVIEW_WORKERS', 16))) -> list[Json]:
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        return list(pool.map(review_one, examples))


def qualify(output: str) -> Json:
    """The reviewer's decisions on the 6 examples Hatem reviewed, against his. Rule fixed in DECISIONS before the run."""
    examples = [x for f in HUMAN for x in json.loads(Path(f).read_text())['examples'] if x.get('keep') is not None]
    verdicts = review_all(examples)
    rows = [{'case': x['case'], 'human': x['keep'], 'llm': v.get('keep'), 'problems': v.get('problems'), 'error': v.get('error')}
            for x, v in zip(examples, verdicts, strict=True)]
    agree = sum(r['llm'] == r['human'] for r in rows)
    out = {'reviewer': REVIEWER, 'examples': len(rows), 'agree': agree, 'human_keeps_kept': sum(r['human'] and r['llm'] is True for r in rows),
           'qualified': agree >= 5 and all(r['llm'] is True for r in rows if r['human']), 'rows': rows,
           'spent_usd_estimate': round(hosted_client.spent(), 4)}
    Path(output).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def review(batch: str) -> Json:
    data = json.loads(Path(batch).read_text())
    todo = [x for x in data['examples'] if x.get('keep') is None]
    verdicts = review_all(todo)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    for example, verdict in zip(todo, verdicts, strict=True):
        if 'error' in verdict:
            continue  # stays unreviewed, so it cannot train
        example.update(keep=bool(verdict['keep']), review_note='; '.join(verdict.get('problems') or []) or verdict.get('teaches', ''),
                       reviewed_by=f'{REVIEWER} (LLM reviewer)', reviewed_at=now, review_source='llm', llm_review=verdict)
    Path(batch).write_text(json.dumps(data, ensure_ascii=False, indent=1))
    kept = sum(1 for x in data['examples'] if x.get('keep') is True)
    return {'batch': batch, 'reviewed': sum(1 for v in verdicts if 'error' not in v), 'errors': sum(1 for v in verdicts if 'error' in v),
            'kept': kept, 'examples': len(data['examples']), 'spent_usd_estimate': round(hosted_client.spent(), 4)}


def main() -> None:
    if 'DEEPSEEK_API_KEY' not in os.environ:
        sys.exit('DEEPSEEK_API_KEY is not set')
    os.environ['HOSTED_MODEL'] = REVIEWER
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='step', required=True)
    q = sub.add_parser('qualify')
    q.add_argument('--output', required=True)
    r = sub.add_parser('review')
    r.add_argument('batch')
    args = p.parse_args()
    result: Any = qualify(args.output) if args.step == 'qualify' else review(args.batch)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
