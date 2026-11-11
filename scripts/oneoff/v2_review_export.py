"""The version 2 answers kept by the gates, written out for Hatem's review (Markdown to read, JSON to keep).

Every kept answer is shown in full: the state it answered (question, case date, theories, sources read with their
dates), the teacher's call and its complete reasoning, and keyword flags to help reading. The flags are not judgments
and select nothing; which examples train is Hatem's choice, recorded in the JSON's "keep" field.

    python scripts/oneoff/v2_review_export.py ANSWERS.json [ANSWERS.json ...] --output reviews/v2_round2/examples

With --verify MANIFEST, the saved replies are first re-judged by today's gates (targeted.regate, no new sampling), one
answer is kept per state (corrective families: corrective.regate and corrective.rows), and only answers that also pass provenance (the exact reply is in the manifest), replay (the
student's run rebuilds the exact context the teacher saw, targeted.rows) and the split check (a training case, never
development or either frozen test set) are exported. Each check's counts are in the output.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from aemon.environment.cases import load_cases  # noqa: E402
from aemon.teacher import corrections as c  # noqa: E402
from aemon.teacher import targeted  # noqa: E402
from aemon.teacher import corrective  # noqa: E402
from aemon.teacher import review_notes  # noqa: E402
from aemon.data.splits import is_validation  # noqa: E402
from aemon.teacher.targeted import ONLINE, YEAR  # noqa: E402

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


STUDENT = review_notes.student_calls(Path(__file__).resolve().parents[2])


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
        'origin': {'experiment-reread': 'reread', 'weigh': 'weighing step', 'numbers': 'final recommendation', 'classify': 'evidence kind',
                   'unstick': 'after two refusals', 'simulated': 'refused simulated finish', 'revise': 'simulated result arrived'}.get(item['skill'], 'test step'),
        'question': case.question,
        'student_turn': item['state']['turn'],
        'student_run': item['state']['student_run'],
        'skill': item['skill'],
        'theories': {k: t['claim'] for k, t in run.theories.items()},
        'sources_read': {s: str(getattr(run._source(s), 'date', '') or 'unknown') for s in sorted(run.read)},
        'call': kept['call'],
        'justification': kept['justification'],
        'decision_at_generation': item.get('decision_at_generation', item.get('decision')),
        'flags': flags(kept['call'], year),
        'teacher_reply_raw': item['reply'],
        **(_compare(item, run, case, kept) if item.get('skill') in corrective.FAMILIES else {}),
        'keep': None,
    }


def _compare(item: dict, run, case, kept: dict) -> dict:
    student = STUDENT.get((item['state']['student_run'], item['state']['turn'], item['skill']))
    return {
        'student_action': review_notes._short(student),
        'why_wrong': review_notes.why_wrong(item['skill'], run, item['record'], case, student),
        'quality_notes': review_notes.quality_notes(item['skill'], run, kept['call'], kept['justification'], student),
        **({'composition': item['composition'], 'shortened': item.get('shortened')} if item.get('composition') else {}),
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
        if 'why_wrong' in e:
            sa = e.get('student_action') or {}
            lines += [f"**Student's action:** `{sa.get('name')}` {json.dumps(sa.get('arguments'), ensure_ascii=False)[:600]}", '',
                      f"**Why it was wrong:** {e['why_wrong']}", '',
                      f"**Automated quality notes:** {'; '.join(e['quality_notes']) or 'none'}", '']
        if call['name'] not in ('propose_test', 'decline_test'):
            lines += [f"**Teacher's call:** `{call['name']}` {json.dumps(a, ensure_ascii=False)}", '']
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
        elif call['name'] == 'decline_test':
            lines += [f"**Declines the test:** {a.get('reason', '')}", '']
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
    p.add_argument('--verify', metavar='MANIFEST', help='re-gate, one answer per state, and require provenance, replay and split')
    args = p.parse_args()
    items = [x for f in args.answers for x in json.loads(Path(f).read_text())]
    cases = {x.id: x for x in load_cases()}
    kept = [x for x in items if isinstance(x.get('kept'), dict)]
    checks = collections.Counter()
    if args.verify:
        frozen = {x.id for x in load_cases(split='heldout')} | {x.id for x in load_cases(split='heldout2')}
        # corrective answers are re-judged by their own family's gate and rebuilt by corrective.rows
        own = [x for x in items if x.get('skill') in corrective.FAMILIES]
        items = targeted.regate([x for x in items if x.get('skill') not in corrective.FAMILIES]) + corrective.regate(own)
        kept, seen = [], set()
        for x in items:
            if not isinstance(x.get('kept'), dict):
                checks['refused by today\'s gates' if x.get('decision_at_generation') == 'kept' else 'not kept'] += 1
                continue
            key = (x['state']['student_run'], x['state']['turn'], x.get('skill'))
            cid = x['state']['case']
            if key in seen:
                checks['later answer to a state already kept'] += 1
            elif cid in frozen or cid not in cases or is_validation(cid):
                checks['not a training case'] += 1
            elif not (corrective.rows if x.get('skill') in corrective.FAMILIES else targeted.rows)([x], args.verify):
                checks['provenance or replay failed'] += 1
            else:
                seen.add(key)
                kept.append(x)
        checks['passed every check'] = len(kept)
    entries = [entry(i + 1, x, cases) for i, x in enumerate(kept)]
    counts = {
        'answers': len(items),
        'valid': sum('reply' in x for x in items),
        'failures': sum(str(x.get('decision', '')).startswith('request failed') for x in items),
        'kept': len(kept),
        **({'verification': dict(checks)} if args.verify else {}),
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
