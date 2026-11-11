"""Does the GGUF adapter behave like the PEFT adapter it was converted from? NOTHING HERE TRAINS.

The same token ids go to both sides: Transformers with the PEFT adapter in bf16, and a running llama-server holding
the bf16 GGUF with the converted adapter. For each prompt it compares the first token's top-10 log-probabilities and
a greedy continuation, with the adapter on and off. The adapter-off comparison checks the base conversion; the gap
between adapter on and off shows how large the adapter's effect is next to any conversion error.

Usage: python -m aemon.evaluation.conversion.check --model DIR --adapter PEFT_DIR --url URL --rows rows.jsonl --output out.json
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

import torch

from aemon.common.types import Json
from aemon.data.splits import is_validation

if TYPE_CHECKING:
    from peft import PeftModel


def server(url: str, ids: list[int], n: int, lora: float) -> tuple[list[Any], dict[Any, Any]]:
    body = {'prompt': ids, 'n_predict': n, 'temperature': 0, 'n_probs': 10, 'cache_prompt': False, 'lora': [{'id': 0, 'scale': lora}]}
    request = urllib.request.Request(url + '/completion', json.dumps(body).encode(), {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=600) as response:
        data = json.load(response)
    probs = data['completion_probabilities']
    return [p['id'] for p in probs], {t['id']: t['logprob'] for t in probs[0]['top_logprobs']}


def local(model: PeftModel, ids: list[int], n: int) -> tuple[Any | Any, dict[int, float]]:
    with torch.no_grad():
        tensor = torch.tensor([ids], device=model.device)
        first = torch.log_softmax(model(tensor).logits[0, -1].float(), -1)
        top = torch.topk(first, 10)
        out = model.generate(tensor, attention_mask=torch.ones_like(tensor), max_new_tokens=n, do_sample=False)
    return out[0, len(ids) :].tolist(), {int(i): float(v) for i, v in zip(top.indices, top.values, strict=False)}


def compare(a: tuple[list[int], dict[int, float]], b: tuple[list[int], dict[int, float]]) -> Json:
    (seq_a, top_a), (seq_b, top_b) = a, b
    agree = next((i for i, (x, y) in enumerate(zip(seq_a, seq_b, strict=False)) if x != y), min(len(seq_a), len(seq_b)))
    shared = set(top_a) & set(top_b)
    return {
        'same_first_token': bool(seq_a and seq_b and seq_a[0] == seq_b[0]),
        'greedy_tokens_agreeing': agree,
        'of': min(len(seq_a), len(seq_b)),
        'top10_overlap': len(shared),
        'max_logprob_gap_on_shared': round(max((abs(top_a[t] - top_b[t]) for t in shared), default=float('nan')), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--adapter', required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--rows', required=True)
    parser.add_argument('--prompts', type=int, default=8)
    parser.add_argument('--tokens', type=int, default=32)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    rows = [json.loads(line) for line in open(args.rows)]
    picked = [r for r in rows if is_validation(r['case'])] or rows  # unseen companies first, so the inputs were never trained on
    picked = picked[:: max(len(picked) // args.prompts, 1)][: args.prompts]
    model = PeftModel.from_pretrained(AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16, device_map={'': 0}), args.adapter).eval()
    results = []
    for row in picked:
        text = tokenizer.apply_chat_template(row['messages'][: row['target_index']], tokenize=False, add_generation_prompt=True)
        ids = tokenizer(text, add_special_tokens=False)['input_ids']
        with model.disable_adapter():
            base_local = local(model, ids, args.tokens)
        adapted_local = local(model, ids, args.tokens)
        base_server, adapted_server = server(args.url, ids, args.tokens, 0.0), server(args.url, ids, args.tokens, 1.0)
        results.append(
            {
                'case': row['case'],
                'stage': row.get('stage'),
                'prompt_tokens': len(ids),
                'adapter_on': compare(adapted_local, adapted_server),
                'adapter_off': compare(base_local, base_server),
                'adapter_effect_in_peft': compare(base_local, adapted_local),
            }
        )
    on = [r['adapter_on'] for r in results]
    summary = {
        'prompts': len(results),
        'first_token_agrees_with_adapter': sum(o['same_first_token'] for o in on),
        'mean_greedy_tokens_agreeing_with_adapter': round(sum(o['greedy_tokens_agreeing'] for o in on) / max(len(on), 1), 1),
        'of': args.tokens,
        'worst_logprob_gap_with_adapter': max(o['max_logprob_gap_on_shared'] for o in on),
        'first_token_changed_by_adapter_in_peft': sum(not r['adapter_effect_in_peft']['same_first_token'] for r in results),
        'worst_logprob_gap_without_adapter': max(r['adapter_off']['max_logprob_gap_on_shared'] for r in results),
        # What converting the adapter adds, on the same prompt, beyond the base model's own bf16 kernel difference
        'worst_gap_added_by_adapter_conversion': round(
            max(r['adapter_on']['max_logprob_gap_on_shared'] - r['adapter_off']['max_logprob_gap_on_shared'] for r in results), 4
        ),
    }
    # bf16 kernels differ, so a long greedy run may part late; the first token, most of the continuation and the top
    # log-probabilities must agree, and the adapter must change something. The log-probability tolerance is measured
    # against the same prompt without the adapter: on 2026-11-05 the base model alone, with no adapter, differed by up to
    # 0.19 between Transformers and llama.cpp at 4K-token contexts, so an absolute 0.15 failed the base conversion itself.
    # The conversion may add at most 0.15 to that, and no gap may exceed 0.5. See docs/DECISIONS.md.
    gate = {
        'first_token_agrees_on_every_prompt': summary['first_token_agrees_with_adapter'] == len(results),
        'greedy_agreement_at_least_75_percent': summary['mean_greedy_tokens_agreeing_with_adapter'] >= 0.75 * args.tokens,
        'conversion_adds_at_most_0.15_to_base_gap': summary['worst_gap_added_by_adapter_conversion'] <= 0.15,
        'logprob_gap_at_most_0.5': summary['worst_logprob_gap_with_adapter'] <= 0.5,
        'adapter_changes_some_first_token_or_logprobs': any(
            not r['adapter_effect_in_peft']['same_first_token'] or r['adapter_effect_in_peft']['max_logprob_gap_on_shared'] > 0.15 for r in results
        ),
    }
    summary['passed'] = all(gate.values())
    Path(args.output).write_text(
        json.dumps(
            {'summary': summary, 'gate': gate, 'results': results, 'note': 'bf16 on both sides; small gaps are expected from different kernels'}, indent=1
        )
    )
    print(json.dumps(summary))
    if not summary['passed']:
        raise SystemExit(f'conversion gate failed: {[k for k, v in gate.items() if not v]}')


if __name__ == '__main__':
    main()
