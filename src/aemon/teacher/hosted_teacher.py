"""The corrective pipeline with a hosted teacher (DeepSeek) instead of the llama.cpp server. NO TRAINING. Development only.

A separate entry point: corrections.chat and experiment_design.chat are pointed at common.hosted_client.chat for this
process only, so the evaluated runner, aemon and the Command A+ jobs are unchanged. The states, instructions,
families and gates are the corrective pipeline's own (pipeline/corrective.py); only the model answering differs.

    DEEPSEEK_API_KEY=... python -m aemon.teacher.hosted_teacher ask --states S.json --manifest M.jsonl --output O.json

Provenance: there are no weights to hash, so weights_sha256 is the sha256 of the model label (API model id and the
version DeepSeek's pricing page names), and the generation settings record the endpoint, model, label, thinking mode,
token limit, repair turns and that the API takes no seed. Every request is logged with usage and cost (HOSTED_LOG).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request

from aemon.agent.backends import hosted_client
from aemon.teacher import corrections, corrective, experiment_design

LABELS = {'deepseek-flash': 'DeepSeek-V4.1-Flash-1017', 'deepseek-v4-pro': 'DeepSeek-V4-Pro-0813'}  # api-docs.deepseek.com, 2026-11-10


def label() -> str:
    name = hosted_client.model()
    return f'deepseek-api {name} {LABELS.get(name, "unknown version")}'


def balance() -> float:
    request = urllib.request.Request('https://api.deepseek.com/user/balance', headers={'Authorization': 'Bearer ' + os.environ['DEEPSEEK_API_KEY']})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    return sum(float(b['total_balance']) for b in data.get('balance_infos', []) if b.get('currency') == 'USD')


def reshorten(asked_path: str, manifest: str, output: str, workers: int = 8) -> None:
    """One more shortening turn (DECISIONS 2026-11-10 18:55 UTC) for experiment answers refused only because a field was
    still over its limit after experiment_design's one shortening turn: the same conversation continued, the teacher's
    own shortened text, then compose, the limits and the family gate exactly as experiment_design.ask applies them."""
    import concurrent.futures

    from aemon.common.constants.prompts import PROMPTS
    from aemon.environment.cases import load_cases
    from aemon.teacher.corrective import gate
    from aemon.rows.provenance import CorrectionEntry, GenerationSettings, append_entry

    cases = {x.id: x for x in load_cases()}
    weights = hashlib.sha256(label().encode()).hexdigest()
    generation = GenerationSettings.model_validate({'hosted_model': hosted_client.model(), 'model_label': label(), 'shortening_turns': 2})
    todo = [x for x in json.loads(open(asked_path).read())
            if x.get('skill') == 'experiment' and str(x.get('decision', '')).startswith('still over the length limit') and x.get('raw_replies')]

    def one(item: dict) -> dict:
        state = item['state']
        run, _ = corrections._replay(item['record'], cases[state['case']], len(item['record']['model_turns']))
        messages = [{'role': 'system', 'content': PROMPTS['teacher'] + '\n\n' + experiment_design.DESIGN_ASK}, item['context'][1]]
        for raw in item['raw_replies']:  # the conversation so far, each reply followed by its exact counts
            over = experiment_design.over_limits(experiment_design.compose(json.loads(raw)))
            messages += [{'role': 'assistant', 'content': raw}, {'role': 'user', 'content': experiment_design.shorten_note(over)}]
        try:
            reply = hosted_client.chat('hosted', messages, 0, 3000, experiment_design.schema(run), 0.0)
            answer = experiment_design.compose(json.loads(reply['text']))
        except Exception as error:  # noqa: BLE001
            return dict(item, decision=f'second shortening failed: {type(error).__name__}', kept=None, shortening_turns=2)
        append_entry(CorrectionEntry(protocol=corrections.PROTOCOL, case=state['case'], case_digest=state['case_digest'], student_run=state['student_run'],
                                     turn=state['turn'], weights_sha256=weights, generation=generation, reply_sha256=corrections._digest(reply['text'])), manifest)
        text = json.dumps(answer, ensure_ascii=False)
        append_entry(CorrectionEntry(protocol=corrections.PROTOCOL, case=state['case'], case_digest=state['case_digest'], student_run=state['student_run'],
                                     turn=state['turn'], weights_sha256=weights, generation=generation, reply_sha256=corrections._digest(text)), manifest)
        out = dict(item, reply=text, raw_replies=[*item['raw_replies'], reply['text']], thinking=[*(item.get('thinking') or []), reply.get('thinking')],
                   shortening_turns=2)
        over = experiment_design.over_limits(answer)
        if over:
            out['kept'], out['decision'] = None, 'still over the length limit after two shortenings: ' + ', '.join(over)
        else:
            out['kept'], out['decision'] = gate({**item['state'], 'record': item['record'], 'skill': 'experiment'}, text)
        return out

    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        done = list(pool.map(one, todo))
    open(output, 'w').write(json.dumps(done, ensure_ascii=False))
    print(json.dumps({'reshortened': len(done), 'kept': sum(isinstance(x.get('kept'), dict) for x in done),
                      'still_over': sum(str(x.get('decision', '')).startswith('still over') for x in done),
                      'spent_usd_estimate': round(hosted_client.spent(), 4)}))


def main() -> None:
    if 'DEEPSEEK_API_KEY' not in os.environ:
        sys.exit('DEEPSEEK_API_KEY is not set')
    corrections.chat = hosted_client.chat  # this process only
    experiment_design.chat = hosted_client.chat
    argv = sys.argv[1:]
    if argv and argv[0] == 'reshorten':  # reshorten ASKED.json MANIFEST.jsonl OUTPUT.json
        reshorten(argv[1], argv[2], argv[3])
        return
    if argv and argv[0] == 'ask':
        settings = {'endpoint': hosted_client.BASE, 'hosted_model': hosted_client.model(), 'model_label': label(), 'thinking': True,
                    'max_tokens': int(os.environ.get('HOSTED_MAX_TOKENS', 16000)), 'repair_turns': int(os.environ.get('HOSTED_REPAIRS', 2)),
                    'seed': 'not supported by the API', 'strict_tool_schema': True, 'prompt_version': 'corrective (unchanged)'}
        start = balance()
        print(json.dumps({'balance_usd_before': start, 'budget_usd': float(os.environ.get('HOSTED_BUDGET_USD', '5')), 'model': label()}), flush=True)
        argv += ['--url', 'hosted', '--weights-sha256', hashlib.sha256(label().encode()).hexdigest(), '--server-settings', json.dumps(settings)]
    sys.argv = [sys.argv[0], *argv]
    corrective.main()
    if argv and argv[0] == 'ask':
        print(json.dumps({'spent_usd_estimate': round(hosted_client.spent(), 4), 'balance_usd_after': balance()}))


if __name__ == '__main__':
    main()
