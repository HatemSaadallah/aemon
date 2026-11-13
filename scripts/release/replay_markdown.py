"""Readable transcripts of recorded frozen-test investigations, for reading without a GPU or a model server.

Each transcript is one run, step by step: every tool call the agent made, whether the environment accepted or refused
it and why, what it returned, and the recommendation. Nothing is re-run; the text comes from the saved runner reports in
reports/judge/final/ and reports/judge/test2/. Source excerpts and quotes are shown whole, as in the public dossier. The
blind judges' scores are shown for each run.

Writes six chosen final-test runs to docs/replays/, then a gallery of every run of each frozen test (docs/replays/final/,
docs/replays/test2/), each with an index of base and fine-tuned runs side by side. Scores and counts come from the judge
report code (aemon.evaluation.judging.report), so they match the published reports.

    python scripts/release/replay_markdown.py --out docs/replays
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))

from aemon.evaluation.judging.report import episode_scores, load, report  # noqa: E402

FINAL = REPO / 'reports/judge/final'
JUDGES = ('claude', 'codex')
# Each frozen test: where its files are, its runner reports per arm, its judges' predictions, and how pages name it.
TESTS = {
    'final': {'dir': FINAL, 'reports': {'trained': 'final_test_trained_adapter.json', 'base': 'final_test_base_base.json'},
              'judges': {'claude': 'claude_predictions.jsonl', 'codex': 'codex_predictions.jsonl'},
              'name': 'the frozen final test', 'title': 'Frozen final test (four unseen companies)'},
    'test2': {'dir': REPO / 'reports/judge/test2', 'reports': {'trained': 'test2_trained_adapter.json', 'base': 'test2_base_base.json'},
              'judges': {'claude': 'claude_test2/predictions.jsonl', 'codex': 'codex_predictions.jsonl'},
              'name': 'the second frozen test', 'title': 'Second frozen test (twelve more unseen companies)'},
}
ENDED = {'finished': 'finished', 'repeated errors': 'stopped on refused calls', 'context limit': 'context limit',
         'turn limit': 'turn limit'}
# (arm, case, attempt, why it is shown). The best-judged finished trained run of each company's base case, one
# trained run that stopped on refusals, and the untrained base model on the same case for contrast.
CHOSEN = [
    ('trained', 'epro-base', 1, 'Electrolux Professional: a finished investigation'),
    ('trained', 'rational-base', 0, 'RATIONAL: a finished investigation'),
    ('trained', 'simo-base', 1, 'Simonelli: a finished investigation'),
    ('trained', 'aqp-base', 1, 'Aquaporin: finished, well scored, and it misses the insolvency (the main limitation)'),
    ('trained', 'epro-base', 0, 'Electrolux Professional: a run that stops after four refusals in a row'),
    ('base', 'epro-base', 1, 'Electrolux Professional: the untrained base model, for contrast'),
]
REPORTS = {'trained': 'final_test_trained_adapter.json', 'base': 'final_test_base_base.json'}
ARM = {'trained': 'aemon (Tiny Aya Global + adapter, version 1)', 'base': 'Tiny Aya Global without the adapter (best prompt)'}


def scores(test: str = 'final') -> dict[tuple[str, str, int], dict[str, float]]:
    """Each judge's episode score per (arm, case, attempt); a missing or invalid judgment is left out."""
    t = TESTS[test]
    key = [json.loads(line) for line in (t['dir'] / 'key.jsonl').read_text().splitlines() if line.strip()]
    out: dict[tuple[str, str, int], dict[str, float]] = {}
    for judge, path in t['judges'].items():
        preds = load(str(t['dir'] / path))
        for k in key:
            p = preds.get(k['packet_id'])
            if p and 'judgment' in p:
                s, _ = episode_scores(p['judgment'])
                if s is not None:
                    out.setdefault((k['arm'], k['case'], k['attempt']), {})[judge] = s
    return out


def clip(text: object, n: int = 300) -> str:
    s = ' '.join(str(text).split())
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + ' …'


def whole(text: object) -> str:
    """An excerpt or quote in full, on one line so that it fits a table cell."""
    return ' '.join(str(text).split())


def describe(result: object) -> str:
    """One or a few lines for what a tool returned."""
    if not isinstance(result, dict):
        return clip(result)
    if 'error' in result:
        return f'**Refused:** {clip(result["error"])}'
    if 'results' in result:
        hits = result['results'] or []
        if not hits:
            return 'No results.'
        return 'Found: ' + '; '.join(f'`{h.get("id")}` {clip(h.get("title", ""), 90)}' for h in hits[:6])
    if 'excerpt' in result:
        return f'*{clip(result.get("title", ""), 120)}* ({result.get("class", "")}): "{whole(result["excerpt"])}"'
    if 'question' in result:
        return f'**Question:** {clip(result["question"], 400)}'
    return clip(json.dumps(result, ensure_ascii=False), 200)


def arguments(args: object) -> str:
    if not isinstance(args, dict) or not args:
        return ''
    parts = []
    for k, v in args.items():
        if k == 'quote':
            parts.append(f'**{k}:** {whole(v)}')
            continue
        parts.append(f'**{k}:** {clip(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False), 260)}')
    return '<br>'.join(parts)


def mean_of_judges(score: dict[str, float]) -> float | None:
    """As in the published report: only a run scored by both judges has a mean of judges."""
    return statistics.mean(score[j] for j in JUDGES) if all(j in score for j in JUDGES) else None


def render(arm: str, record: dict, why: str, score: dict[str, float], test: str = 'final', back: str = '') -> str:
    judged = ', '.join(f'{j} {v:.2f}' for j, v in sorted(score.items()))
    m = mean_of_judges(score)
    if m is not None:
        score_line = f'{m:.2f} (mean of judges; {judged})'
    elif score:
        missing = ', '.join(j for j in JUDGES if j not in score)
        score_line = f'no mean of judges: the judgment by {missing} is missing or invalid ({judged})'
    else:
        score_line = 'not judged'
    lines = [f'# {record["company"]}: `{record["case"]}`, attempt {record["attempt"]}', '', f'*{why}.*', '']
    if back:
        lines += [back, '']
    lines += [f'- **Model:** {ARM[arm]}', f'- **How it ended:** {record["stop_reason"]} after {len(record["calls"])} tool calls',
              f'- **Blind judge score (0 to 3):** {score_line}', '',
              f'Recorded during {TESTS[test]["name"]}; nothing here is re-run. Excerpts are shown whole.', '',
              '| # | Stage | Tool call | Environment |', '|---|---|---|---|']
    for i, c in enumerate(record['calls'], 1):
        ok = '' if c.get('accepted') else ' (refused)'
        call = f'`{c["name"]}`{ok}' + (f'<br>{arguments(c.get("arguments"))}' if c.get('arguments') else '')
        lines.append(f'| {i} | {c.get("stage", "")} | {call.replace("|", "/")} | {describe(c.get("result")).replace("|", "/")} |')
    final = record.get('final') or {}
    lines += ['', '## Outcome', '']
    if final:
        for k, v in final.items():
            lines.append(f'- **{k.replace("_", " ")}:** {clip(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False), 600)}')
    else:
        lines.append('No recommendation: the run stopped before finishing.')
    if test == 'final' and record['case'].startswith('aqp'):
        judges = ('The blind judges still scored this run well, because they judge the reasoning on the evidence the run '
                  'saw.' if not back else 'The blind judges judge the reasoning on the evidence the run saw, not on what it '
                  'missed.')
        lines += ['', '## What it missed', '',
                  'The dossier holds Aquaporin\'s withdrawal of its offering, its resolution to start insolvency proceedings '
                  'and the bankruptcy order of 2 February 2026 (`aqp-insolvency-2026`). No run of either model found it, and '
                  f'every finished run of the fine-tuned model recommends investing. {judges} See docs/FINAL_TEST_DIAGNOSIS.md.']
    return '\n'.join(lines) + '\n'


def fmt(x: float | None, signed: bool = False) -> str:
    return 'n/a' if x is None else (f'{x:+.2f}' if signed else f'{x:.2f}')


def ended(record: dict) -> str:
    return f'{ENDED.get(record["stop_reason"], record["stop_reason"])} ({len(record["calls"])} calls)'


def cell(score: dict[str, float], page: str) -> str:
    each = ', '.join(f'{j} {fmt(score.get(j))}' for j in JUDGES)
    return f'[{fmt(mean_of_judges(score))}]({page}) ({each})'


def gallery(test: str, root: Path) -> dict:
    """One page per run of a frozen test, and an index pairing base and fine-tuned runs by case and attempt."""
    t = TESTS[test]
    out = root / test
    out.mkdir(parents=True, exist_ok=True)
    reports = {arm: {(r['case'], r['attempt']): r for r in json.loads((t['dir'] / f).read_text())['records']}
               for arm, f in t['reports'].items()}
    judged = scores(test)
    published = report(str(t['dir'] / 'key.jsonl'), {j: str(t['dir'] / p) for j, p in t['judges'].items()}, ('trained', 'base'))
    total = sum(len(r) for r in reports.values())
    back = f'[All {total} runs of {t["name"]}](README.md) · [all recorded investigations](../README.md)'
    for arm, records in reports.items():
        for (case, attempt), record in records.items():
            why = f'One of the {total} runs of {t["name"]}, {"fine-tuned" if arm == "trained" else "base"} model'
            (out / f'{arm}_{case}_{attempt}.md').write_text(render(arm, record, why, judged.get((arm, case, attempt), {}), test, back))
    pairs = sorted(set(reports['base']) & set(reports['trained']))
    rows = []
    for case, attempt in pairs:
        b, f = reports['base'][(case, attempt)], reports['trained'][(case, attempt)]
        sb, sf = judged.get(('base', case, attempt), {}), judged.get(('trained', case, attempt), {})
        mb, mf = mean_of_judges(sb), mean_of_judges(sf)
        diff = mf - mb if mb is not None and mf is not None else None
        line = (f'| {f["company"]} | `{case}` | {attempt} | {ended(b)} | {cell(sb, f"base_{case}_{attempt}.md")} | '
                f'{ended(f)} | {cell(sf, f"trained_{case}_{attempt}.md")} | {fmt(diff, signed=True)} |')
        rows.append({'line': line, 'b': b, 'f': f, 'diff': diff})
    # The summary's means are the judge report's own; recompute them from the per-run scores to check they agree.
    for arm in ('base', 'trained'):
        means = [m for (a, _, _), s in judged.items() if a == arm and (m := mean_of_judges(s)) is not None]
        assert round(statistics.mean(means), 3) == published['mean_of_judges']['by_arm'][arm], (test, arm)
    diffs = [r['diff'] for r in rows if r['diff'] is not None]
    higher, lower = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
    finished = {arm: sum(r['stop_reason'] == 'finished' for r in reports[arm].values()) for arm in reports}
    stops = {arm: Counter(ENDED.get(r['stop_reason'], r['stop_reason']) for r in reports[arm].values()) for arm in reports}
    mj, by_judge = published['mean_of_judges']['by_arm'], {j: published['judges'][j]['by_arm'] for j in JUDGES}
    filters = [
        ('Fine-tuned finished, base did not', [r for r in rows if r['f']['stop_reason'] == 'finished' and r['b']['stop_reason'] != 'finished']),
        ('Fine-tuned scored lower than base', [r for r in rows if r['diff'] is not None and r['diff'] < 0]),
        ('Both stopped', [r for r in rows if r['f']['stop_reason'] != 'finished' and r['b']['stop_reason'] != 'finished']),
    ]
    header = ['| Company | Case | Attempt | Base: how it ended | Base: blind score | Fine-tuned: how it ended | '
              'Fine-tuned: blind score | Fine-tuned minus base |', '|---|---|---|---|---|---|---|---|']
    n = {arm: len(reports[arm]) for arm in reports}
    lines = [f'# {t["title"]}: every run', '',
             f'All {total} runs of {t["name"]}, readable without a GPU: {len(pairs)} pairs of a base run and a fine-tuned '
             f'run on the same case and attempt. Each score links to that run\'s page (every tool call, what the environment '
             'accepted or refused, and the recommendation). Nothing is re-run, and every number here is computed from '
             f'the files in `{t["dir"].relative_to(REPO)}/` by `scripts/release/replay_markdown.py`.', '',
             f'- **Base** is {ARM["base"]}; **fine-tuned** is {ARM["trained"]}.',
             '- **Blind score** is 0 to 3: the mean of the two judges, then each judge (the judges did not know which '
             'model ran). A run has a mean of judges only when both judgments are valid, as in the published report.', '',
             '## Summary', '',
             '| | Base | Fine-tuned |', '|---|---|---|',
             f'| Finished investigations | {finished["base"]} of {n["base"]} | {finished["trained"]} of {n["trained"]} |']
    for how, label in (('stopped on refused calls', 'Stopped on refused calls'), ('context limit', 'Stopped at the context limit'),
                       ('turn limit', 'Stopped at the turn limit')):
        lines.append(f'| {label} | {stops["base"][how]} | {stops["trained"][how]} |')
    assert sum(finished.values()) + sum(stops[a][h] for a in stops for h in ENDED.values() if h != 'finished') == total
    lines.append(f'| **Blind score, mean of judges** | **{mj["base"]:.2f}** | **{mj["trained"]:.2f}** |')
    for j in JUDGES:
        lines.append(f'| Blind score, {j} only | {by_judge[j]["base"]["mean"]:.2f} (n = {by_judge[j]["base"]["n"]}) | '
                     f'{by_judge[j]["trained"]["mean"]:.2f} (n = {by_judge[j]["trained"]["n"]}) |')
    lines += ['', f'On the mean of judges, the fine-tuned run scored higher than the base run in **{higher}** of {len(diffs)} '
              f'pairs, lower in **{lower}**, and equal in **{len(diffs) - higher - lower}**.']
    if len(diffs) < len(pairs):
        lines += ['', f'{len(pairs) - len(diffs)} pair(s) are left out of that count because a judgment is missing or invalid:']
        key = {k['packet_id']: k for k in (json.loads(x) for x in (t['dir'] / 'key.jsonl').read_text().splitlines() if x.strip())}
        lines += [f'- {m["judge"]}, {m["arm"]} run of `{m["case"]}`, attempt {key[m["packet_id"]]["attempt"]} '
                  f'(packet `{m["packet_id"]}`)' for m in published['missing']]
    lines += ['', 'Filters:', '']
    lines += [f'- [{title}](#{title.lower().replace(",", "").replace(" ", "-")}) ({len(rs)} pairs)' for title, rs in filters]
    lines += ['- [All runs](#all-runs)', '']
    for title, rs in filters + [('All runs', rows)]:
        lines += [f'## {title}', '']
        lines += header + [r['line'] for r in rs] if rs else ['None.']
        lines.append('')
    lines.append('Regenerate with `python scripts/release/replay_markdown.py`.')
    (out / 'README.md').write_text('\n'.join(lines) + '\n')
    return {'test': test, 'pages': total, 'pairs': len(pairs), 'finished': finished, 'mean_of_judges': mj,
            'higher': higher, 'lower': lower, 'equal': len(diffs) - higher - lower}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--out', default=str(REPO / 'docs/replays'))
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    reports = {arm: {(r['case'], r['attempt']): r for r in json.loads((FINAL / f).read_text())['records']} for arm, f in REPORTS.items()}
    judged = scores()
    index = ['# Recorded investigations', '',
             'Six runs from the frozen final test (four companies the model never saw), readable without a GPU. Each '
             'page shows every tool call, what the environment accepted or refused, and the recommendation.', '',
             '| Run | Model | Ended | Judge score |', '|---|---|---|---|']
    for arm, case, attempt, why in CHOSEN:
        record = reports[arm][(case, attempt)]
        score = judged.get((arm, case, attempt), {})
        name = f'{arm}_{case}_{attempt}.md'
        (out / name).write_text(render(arm, record, why, score))
        mean = f'{statistics.mean(score.values()):.2f}' if score else 'n/a'
        index.append(f'| [{why}]({name}) | {"aemon" if arm == "trained" else "base"} | {record["stop_reason"]} | {mean} |')
    summaries = [gallery(test, out) for test in TESTS]
    index += ['', '## Every run', '',
              'Every run of both frozen tests, base and fine-tuned side by side, with filters (fine-tuned finished and base '
              'did not, fine-tuned scored lower, both stopped):', '']
    for s in summaries:
        t = TESTS[s['test']]
        index.append(f'- [{t["title"]}]({s["test"]}/README.md): {s["pages"]} runs; finished {s["finished"]["base"]} base, '
                     f'{s["finished"]["trained"]} fine-tuned; mean of judges {s["mean_of_judges"]["base"]:.2f} base, '
                     f'{s["mean_of_judges"]["trained"]:.2f} fine-tuned.')
    index += ['', 'Regenerate with `python scripts/release/replay_markdown.py`. The runner reports are '
              '`reports/judge/final/final_test_*.json` and `reports/judge/test2/test2_*.json`.']
    (out / 'README.md').write_text('\n'.join(index) + '\n')
    print(json.dumps({'written': len(CHOSEN) + 1, 'folder': str(out), 'galleries': summaries}))


if __name__ == '__main__':
    main()
