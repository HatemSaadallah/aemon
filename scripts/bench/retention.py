"""General-capability retention check: the base model against the same model with an adapter loaded, on the same
multiple-choice items, through one llama-server process (the adapter's scale switched between 0 and 1, so the
weights, the prompt and the decoding are otherwise identical).

Each item is asked zero-shot, "answer with the letter only". The answer is the most probable of A, B, C, D among the
top log-probabilities of the first reply token (the standard multiple-choice scoring, so a reply that starts with a
sentence still yields an answer); if no letter is among the top candidates, a short greedy reply is parsed for the
first standalone letter, and a reply without one counts as wrong and is reported separately. Reports accuracy per arm
and benchmark, the paired difference with a 95% bootstrap interval over items, and every reply.

Usage: python scripts/bench/retention.py --url http://127.0.0.1:PORT --items retention_items.jsonl \
           --arms base= v1=0 [v3=1] --out retention.json
`name=` means every adapter at scale 0; `name=i` means adapter i at scale 1 and the others at 0.
"""

import argparse
import json
import random
import re
import time
import urllib.request

LETTER = re.compile(r'(?<![A-Za-z])([ABCD])(?![A-Za-z])')


def post(url: str, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def set_adapters(base: str, active: int | None) -> None:
    current = json.loads(urllib.request.urlopen(base + '/lora-adapters', timeout=60).read())
    want = [{'id': a['id'], 'scale': 1.0 if a['id'] == active else 0.0} for a in current]
    post(base + '/lora-adapters', want)
    now = json.loads(urllib.request.urlopen(base + '/lora-adapters', timeout=60).read())
    assert [(a['id'], a['scale']) for a in now] == [(w['id'], w['scale']) for w in want], now


def prompt_for(it: dict) -> str:
    topic = it['subject'].replace('_', ' ')
    lines = [f'The following is a multiple choice question about {topic}. Answer with the letter only.', '',
             it['question'].strip()]
    lines += [f'{letter}. {text}' for letter, text in zip('ABCD', it['choices'])]
    lines += ['', 'Answer:']
    return '\n'.join(lines)


def ask(base: str, it: dict) -> tuple[str | None, str, str]:
    """Returns (prediction, how, reply text)."""
    body = {'messages': [{'role': 'user', 'content': prompt_for(it)}], 'temperature': 0, 'seed': 7,
            'max_tokens': 1, 'logprobs': True, 'top_logprobs': 20}
    out = post(base + '/v1/chat/completions', body)
    choice = out['choices'][0]
    reply = choice['message']['content'] or ''
    scores: dict[str, float] = {}
    try:
        for cand in choice['logprobs']['content'][0]['top_logprobs']:
            tok = cand['token'].strip().strip('*').strip()
            if tok in ('A', 'B', 'C', 'D'):
                scores[tok] = max(scores.get(tok, -1e9), cand['logprob'])
    except (KeyError, IndexError, TypeError):
        pass
    if scores:
        return max(scores, key=scores.get), 'logprob', reply
    out = post(base + '/v1/chat/completions', {'messages': body['messages'], 'temperature': 0, 'seed': 7, 'max_tokens': 32})
    reply = out['choices'][0]['message']['content'] or ''
    m = LETTER.search(reply)
    return (m.group(1) if m else None), 'generated', reply


def bootstrap(diffs: list[int], n: int = 10000, seed: int = 7) -> list[float]:
    rng = random.Random(seed)
    k = len(diffs)
    means = sorted(sum(rng.choice(diffs) for _ in range(k)) / k for _ in range(n))
    return [sum(diffs) / k, means[int(0.025 * n)], means[int(0.975 * n) - 1]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', required=True)
    ap.add_argument('--items', required=True)
    ap.add_argument('--arms', nargs='+', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    items = [json.loads(line) for line in open(a.items)]
    arms = []
    for spec in a.arms:
        name, _, idx = spec.partition('=')
        arms.append((name, int(idx) if idx else None))

    replies: dict[str, list[dict]] = {}
    for name, active in arms:
        set_adapters(a.url, active)
        t0 = time.time()
        rows = []
        for it in items:
            pred, how, reply = ask(a.url, it)
            rows.append({'id': it['id'], 'bench': it['bench'], 'reply': reply, 'pred': pred, 'how': how, 'correct': pred == it['answer']})
        replies[name] = rows
        acc = sum(r['correct'] for r in rows) / len(rows)
        print(f'{name}: accuracy {acc:.3f}, by logprob {sum(r["how"] == "logprob" for r in rows)}, no letter {sum(r["pred"] is None for r in rows)}, {time.time() - t0:.0f} s', flush=True)

    benches = sorted({it['bench'] for it in items})
    summary: dict = {'items': len(items), 'arms': {}, 'differences': {}}
    for name, rows in replies.items():
        summary['arms'][name] = {}
        for b in benches + ['all']:
            sel = [r for r in rows if b == 'all' or r['bench'] == b]
            summary['arms'][name][b] = {'n': len(sel), 'accuracy': sum(r['correct'] for r in sel) / len(sel),
                                        'by_logprob': sum(r['how'] == 'logprob' for r in sel),
                                        'no_letter': sum(r['pred'] is None for r in sel)}
    base_name = arms[0][0]
    for name, _ in arms[1:]:
        key = f'{name}_minus_{base_name}'
        summary['differences'][key] = {}
        for b in benches + ['all']:
            pairs = [(x, y) for x, y in zip(replies[base_name], replies[name]) if b == 'all' or x['bench'] == b]
            summary['differences'][key][b] = bootstrap([int(y['correct']) - int(x['correct']) for x, y in pairs])
    json.dump({'summary': summary, 'prompt': 'zero-shot, letter only; most probable letter among the first token\'s top-20 log-probabilities, else a 32-token greedy reply parsed',
               'replies': replies}, open(a.out, 'w'), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
