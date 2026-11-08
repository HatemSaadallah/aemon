"""Diagnostic: does a narrower question change how far the untrained model gets? NO TRAINING.

One live run on a narrowed question finished where the broad one stalled, so this checks whether that
was luck. Same controller, prompt and settings as arm B. Narrower questions name a group and leave the
answer open. This is exploratory: nine runs on development cases, and it decides nothing by itself.
"""
import dataclasses
import json
import subprocess
from pathlib import Path

from strategy_agent.common.model_client import chat
from strategy_agent.env.cases import load_cases
from strategy_agent.agent.runner import PROMPTS, TOOL_SCHEMA, play, record_of, summary

GROUPS = ('amateur musicians', 'light sleepers', 'teenagers at concerts')
COMPANY = {'moldex-base': 'Moldex-Metric', 'cotral-base': 'Cotral Lab', 'hellberg-base': 'Hellberg Safety'}
URL = 'http://127.0.0.1:8091'
OUT = Path('reports/strategy/diagnostics/narrow_questions.json')


def respond(messages, seed, max_tokens, schema, temperature):
    return chat(URL, messages, seed, max_tokens, schema, temperature)


def main():
    assert not OUT.exists(), 'results are never overwritten'
    OUT.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for case in load_cases(','.join(COMPANY)):
        for group in GROUPS:
            narrowed = dataclasses.replace(case, question=f'Should {COMPANY[case.id]} build a hearing protector for {group}? What evidence would justify that investment?')
            run, info = play(narrowed, respond, PROMPTS['staged'], 45, 4, 520, True, TOOL_SCHEMA, staged=True)
            record = dict(record_of(run, info), question=narrowed.question)
            records.append(record)
            print(json.dumps({'case': case.id, 'group': group, 'stop': info['stop_reason'], 'stage': record['stopping_point']['stage_at_stop'], 'calls': len(run.calls), 'theories': len(run.theories)}), flush=True)
    revision = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, check=False).stdout.strip()
    OUT.write_text(json.dumps({'trained': False, 'code_revision': revision, 'model': 'tiny-aya-global-q4_k_m.gguf a602ea7', 'summary': summary(records), 'records': records}, indent=1))


if __name__ == '__main__':
    main()
