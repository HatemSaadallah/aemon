"""Readable transcripts of recorded final-test investigations, for reading without a GPU or a model server.

Each transcript is one run from the frozen final test, step by step: every tool call the agent made, whether the
environment accepted or refused it and why, what it returned, and the recommendation. Nothing is re-run; the text comes
from the saved runner reports in reports/judge/final/. Source excerpts and quotes are shown whole, as in the public
dossier. The blind judges' scores are shown for each run.

    python scripts/release/replay_markdown.py --out docs/replays
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))

from aemon.evaluation.judging.report import episode_scores, load  # noqa: E402

FINAL = REPO / 'reports/judge/final'
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
ARM = {'trained': 'Aemon (Tiny Aya Global + adapter, version 1)', 'base': 'Tiny Aya Global without the adapter (best prompt)'}


def scores() -> dict[tuple[str, str, int], dict[str, float]]:
    key = [json.loads(line) for line in (FINAL / 'key.jsonl').read_text().splitlines() if line.strip()]
    out: dict[tuple[str, str, int], dict[str, float]] = {}
    for judge in ('claude', 'codex'):
        preds = load(str(FINAL / f'{judge}_predictions.jsonl'))
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


def render(arm: str, record: dict, why: str, score: dict[str, float]) -> str:
    judged = ', '.join(f'{j} {v:.2f}' for j, v in sorted(score.items()))
    mean = f'{statistics.mean(score.values()):.2f}' if score else 'not judged'
    lines = [f'# {record["company"]}: `{record["case"]}`, attempt {record["attempt"]}', '', f'*{why}.*', '',
             f'- **Model:** {ARM[arm]}', f'- **How it ended:** {record["stop_reason"]} after {len(record["calls"])} tool calls',
             f'- **Blind judge score (0 to 3):** {mean} (mean of judges; {judged})', '',
             'Recorded during the frozen final test; nothing here is re-run. Excerpts are shown whole.', '',
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
    if record['case'].startswith('aqp'):
        lines += ['', '## What it missed', '',
                  'The dossier holds Aquaporin\'s withdrawal of its offering, its resolution to start insolvency proceedings '
                  'and the bankruptcy order of 2 February 2026 (`aqp-insolvency-2026`). No run of either model found it, and '
                  'every finished run of the fine-tuned model recommends investing. The blind judges still scored this run '
                  'well, because they judge the reasoning on the evidence the run saw. See docs/FINAL_TEST_DIAGNOSIS.md.']
    return '\n'.join(lines) + '\n'


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
        index.append(f'| [{why}]({name}) | {"Aemon" if arm == "trained" else "base"} | {record["stop_reason"]} | {mean} |')
    index += ['', 'Regenerate with `python scripts/release/replay_markdown.py`. All 96 final-test runs are in '
              '`reports/judge/final/final_test_*.json`.']
    (out / 'README.md').write_text('\n'.join(index) + '\n')
    print(json.dumps({'written': len(CHOSEN) + 1, 'folder': str(out)}))


if __name__ == '__main__':
    main()
