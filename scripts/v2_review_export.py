"""The version 2 answers kept by the gates, written out for Hatem's review (Markdown to read, JSON to keep).

Every kept answer is shown in full: the state it answered (question, case date, theories, sources read with their
dates), the teacher's call and its complete reasoning, and keyword flags to help reading. The flags are not judgments
and select nothing; which examples train is Hatem's choice, recorded in the JSON's "keep" field.

    python scripts/v2_review_export.py ANSWERS.json [ANSWERS.json ...] --output reviews/v2_round2/examples
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from strategy_agent.env.cases import load_cases  # noqa: E402
from strategy_agent.pipeline import corrections as c  # noqa: E402
from strategy_agent.pipeline.targeted import ONLINE, YEAR  # noqa: E402

COMMITMENT = re.compile(r'pre-?order|deposit|paid trial|sell-?through|in-store sales|mail order|prototype use|pilot sales', re.I)
ATTRIBUTE = re.compile(r'conjoint|attribute|feature|trade-?off|price levels?|two prices|different prices', re.I)
FRAMING = re.compile(r'fram(?:e|ed|ing)|messag|marketed as|wording|headline|positioning|branded', re.I)
STATED = re.compile(r'survey|intent|likert|self-reported|stated|questionnaire', re.I)
BIG_STEP = re.compile(r'launch|build (?:a|the) (?:product|line)|develop(?:ing)? (?:a|an|the) [^.;,]*proposition|roll ?out|scale', re.I)


def flags(call: dict, year: int | None) -> list[str]:
    a = call.get('arguments') or {}
    design = ' '.join(str(a.get(k, '')) for k in ('name', 'method', 'sample', 'measure'))
    whole = design + ' ' + ' '.join(str(v) for v in (a.get('prediction_by_theory') or {}).values())
    if call['name'] == 'decline_test':
        return ['declines the test']
    out = []
    if COMMITMENT.search(design):
        out.append('asks for a real commitment (deposit, pre-order, paid use)')
    elif STATED.search(design):
        out.append('stated preference only')
    if FRAMING.search(whole):
        out.append('the arms differ in framing or message')
    if ATTRIBUTE.search(design):
        out.append('varies product attributes or price levels')
    if year is not None and year < 2005 and ONLINE.search(design):
        out.append(f'online method in a {year} case')
    if BIG_STEP.search(str(a.get('decision_rule', ''))):
        out.append('rule leads straight to developing or launching')
    return out


def entry(n: int, item: dict, cases: dict) -> dict:
    case = cases[item['state']['case']]
    run, _ = c._replay(item['record'], case, len(item['record']['model_turns']))
    found = YEAR.search(f'{case.question} {case.brief}')
    year = int(found.group(1)) if found else None
    kept = item['kept']
    return {
        'n': n,
        'case': case.id,
        'case_date': str(year) if year else 'present day',
        'origin': 'reread' if item['skill'] == 'experiment-reread' else 'test step',
        'question': case.question,
        'student_turn': item['state']['turn'],
        'theories': {k: t['claim'] for k, t in run.theories.items()},
        'sources_read': {s: str(getattr(run._source(s), 'date', '') or 'unknown') for s in sorted(run.read)},
        'call': kept['call'],
        'justification': kept['justification'],
        'decision_at_generation': item.get('decision_at_generation', item.get('decision')),
        'flags': flags(kept['call'], year),
        'teacher_reply_raw': item['reply'],
        'keep': None,
    }


def markdown(entries: list[dict], counts: dict) -> str:
    lines = [
        '# Version 2, second round: every answer kept by the gates, for review',
        '',
        "Selection is Hatem's: fill in **Keep?** (or the JSON's `keep`). The flags are keyword checks to help reading, "
        'not judgments. Each answer is shown whole; nothing below is truncated.',
        '',
        f"Answers: {counts['answers']} ({counts['valid']} valid replies, {counts['failures']} request failures); "
        f"kept by the gates: {counts['kept']} ({counts['by_call']}). Rejections, first failing check: "
        + '; '.join(f'{n} {r}' for r, n in counts['rejections']) + '.',
        '',
    ]
    for e in entries:
        call, a, j = e['call'], e['call'].get('arguments') or {}, e['justification']
        lines += [f"## {e['n']}. {e['case']} ({e['case_date']}, from the {e['origin']})", '', f"**Question:** {e['question']}", '']
        lines += [f'- **{k}:** {v}' for k, v in e['theories'].items()] + ['']
        lines += ['**Sources read (dossier date):** ' + ', '.join(f'{s} ({d})' for s, d in e['sources_read'].items()), '']
        if call['name'] == 'propose_test':
            lines += [
                f"**Test:** {a.get('name', '')}. {a.get('method', '')}",
                '',
                f"**Sample:** {a.get('sample', '')}  ",
                f"**Measure:** {a.get('measure', '')}  ",
                f"**Cost:** €{a.get('cost_eur', '?')}, {a.get('weeks', '?')} weeks; theories tested: {', '.join(a.get('theories') or [])}",
                '',
            ]
            lines += [f'- **Predicts {k}:** {v}' for k, v in (a.get('prediction_by_theory') or {}).items()] + ['']
            lines += [f"**Decision rule:** {a.get('decision_rule', '')}", '']
        else:
            lines += [f"**Declines the test:** {a.get('reason', json.dumps(a, ensure_ascii=False))}", '']
        lines += [
            f"**Teacher, learned:** {j.get('learned', '')}",
            '',
            f"**Teacher, uncertain:** {j.get('uncertain', '')}",
            '',
            f"**Teacher, why next:** {j.get('why_next', '')}",
            '',
            f"**Flags:** {'; '.join(e['flags']) or 'none'}",
            '',
            '**Keep? (Hatem):** ',
            '',
        ]
    return '\n'.join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('answers', nargs='+')
    p.add_argument('--output', required=True, help='path without extension; .md and .json are written')
    args = p.parse_args()
    items = [x for f in args.answers for x in json.loads(Path(f).read_text())]
    cases = {x.id: x for x in load_cases()}
    kept = [x for x in items if isinstance(x.get('kept'), dict)]
    entries = [entry(i + 1, x, cases) for i, x in enumerate(kept)]
    counts = {
        'answers': len(items),
        'valid': sum('reply' in x for x in items),
        'failures': sum(str(x.get('decision', '')).startswith('request failed') for x in items),
        'kept': len(kept),
        'by_call': ', '.join(f'{n} {k}' for k, n in collections.Counter(e['call']['name'] for e in entries).most_common()) or 'none',
        'rejections': collections.Counter(x['decision'] for x in items if 'reply' in x and not isinstance(x.get('kept'), dict)).most_common(),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix('.json').write_text(json.dumps({'counts': counts, 'examples': entries}, ensure_ascii=False, indent=1))
    out.with_suffix('.md').write_text(markdown(entries, counts))
    print(json.dumps({k: v for k, v in counts.items() if k != 'rejections'}), '->', out.with_suffix('.md'))


if __name__ == '__main__':
    main()
