"""One AgentTune GRPO step on the GPU through the Tiny Aya fallback template.

GRADIENT PLUMBING ONLY. The model is tiny and random, and the reward is the batch index,
deliberately unrelated to correctness. A pass shows the software path works on this torch,
CUDA and driver stack. It shows nothing about useful learning, real Tiny Aya quality, or
memory. Forced mode exists to run a tool call, because random weights never emit one.

AgentTune's own test sets use_cpu=True, so it cannot show GPU training. This script
sets use_cpu=False and fails unless the trained parameters really are on CUDA.

Usage: python grpo_gpu_smoke.py --agenttune-repo /path/to/AgentTune/clone
"""
import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

import torch
import transformers
from datasets import Dataset
from torch.optim.optimizer import (register_optimizer_step_post_hook,
                                   register_optimizer_step_pre_hook)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--agenttune-repo', required=True)
    parser.add_argument('--real-generate', action='store_true',
                        help='do not patch generate; the tiny random model emits real varied text')
    parser.add_argument('--quant-lora', action='store_true',
                        help='load in 4-bit NF4 with LoRA through AgentTune kwarg routing')
    args = parser.parse_args()
    sys.path.insert(0, str(Path(args.agenttune_repo) / 'tests'))
    import test_cohere_tool_calls as fixtures

    from agenttune.core.backend_factory import create_agentic_trainer

    if not torch.cuda.is_available():
        raise SystemExit('CUDA unavailable')
    tmp = Path(tempfile.mkdtemp(prefix='grpo_gpu_'))
    tok = fixtures._tokenizer('tiny_aya_default.jinja')
    cfg = transformers.Cohere2Config(
        vocab_size=len(tok), hidden_size=32, intermediate_size=64, num_hidden_layers=2,
        num_attention_heads=2, num_key_value_heads=1, max_position_embeddings=4096,
        pad_token_id=tok.pad_token_id, bos_token_id=tok.bos_token_id, eos_token_id=tok.eos_token_id)
    torch.manual_seed(0)
    transformers.AutoModelForCausalLM.from_config(cfg).save_pretrained(tmp / 'model')
    tok.save_pretrained(tmp / 'model')

    calls, state = [], {'n': 0}

    def forced_generate(self, input_ids=None, **_):
        state['n'] += 1
        text = fixtures.R7B_CALL if state['n'] % 2 else 'The answer is 5.'
        # Each row must differ. With identical completions the opposite advantages cancel,
        # the gradient is numerically zero, and Adam turns noise into tiny weight changes.
        rows = []
        for row in range(input_ids.shape[0]):
            suffix = '' if text is fixtures.R7B_CALL else f' Variant {row}: ' + 'abcdefgh'[row % 8] * (row + 1)
            ids = tok(text + suffix, add_special_tokens=False, return_tensors='pt').input_ids[0]
            rows.append(torch.cat([ids, torch.tensor([tok.eos_token_id])]))
        width = max(len(r) for r in rows)
        padded = torch.stack([torch.cat([r, torch.full((width - len(r),), tok.pad_token_id)]) for r in rows])
        return torch.cat([input_ids, padded.to(input_ids.device)], 1)

    def add(a: int, b: int) -> int:
        """Add two integers.

        Args:
            a: first integer
            b: second integer
        """
        calls.append((a, b))
        return a + b

    if not args.real_generate:
        transformers.GenerationMixin.generate = forced_generate
    extra = {}
    if args.quant_lora:
        extra = dict(
            model_init_kwargs={'quantization_config': transformers.BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_compute_dtype=torch.bfloat16),
                'device_map': {'': 0}},
            gradient_checkpointing=True,
            peft_config=dict(r=4, lora_alpha=8, target_modules='all-linear', task_type='CAUSAL_LM'))
    torch.cuda.reset_peak_memory_stats()
    trainer = create_agentic_trainer(
        algorithm='grpo', backend='trl', model=str(tmp / 'model'), tools=[add],
        train_dataset=Dataset.from_list([{'prompt': [{'role': 'user', 'content': '2+3?'}]}] * 2),
        # Rewards must differ within a group: equal rewards give zero advantage, zero loss
        # and no weight change, which is what AgentTune's own test reward produces here.
        reward_funcs=[lambda completions, **kw: [float(i) for i in range(len(completions))]],
        output_dir=str(tmp / 'out'), max_steps=1, per_device_train_batch_size=2,
        gradient_accumulation_steps=1, num_generations=2, max_completion_length=16,
        max_steps_per_turn=2, use_vllm=False, report_to='none', save_steps=1000,
        warmup_steps=0, bf16=False, use_cpu=False, beta=0.0, **extra)
    # Optimizer hooks see the real parameters whatever the wrapper does internally.
    seen = {'before': [], 'steps': 0, 'changed': 0, 'total': 0, 'devices': set(), 'grad_norm': 0.}

    def pre_step(optimizer, *_):
        seen['before'] = [(p, p.detach().clone()) for g in optimizer.param_groups for p in g['params']]
        seen['grad_norm'] = sum(float(p.grad.norm()) for p, _ in seen['before'] if p.grad is not None)

    def post_step(optimizer, *_):
        seen['steps'] += 1
        for p, old in seen['before']:
            seen['total'] += 1
            seen['changed'] += int(not torch.equal(old, p.detach()))
            seen['devices'].add(str(p.device))

    register_optimizer_step_pre_hook(pre_step)
    register_optimizer_step_post_hook(post_step)
    trainer.train()
    final = getattr(trainer, 'model', None) or getattr(getattr(trainer, 'trainer', None), 'model', None)
    four_bit = sum(type(m).__name__ == 'Linear4bit' for m in final.modules()) if final is not None else None
    report = {'tiny_random_model': True, 'devices': sorted(seen['devices']), 'optimizer_steps': seen['steps'],
              'linear4bit_modules': four_bit,
              'real_generate': args.real_generate, 'quant_lora': args.quant_lora,
              'tool_calls_executed': len(calls), 'parameters_changed_by_step': seen['changed'],
              'parameters_total': seen['total'], 'grad_norm_sum': seen['grad_norm'],
              'cuda_peak_MB': torch.cuda.max_memory_allocated() // 2**20}
    print(json.dumps(report))
    if not math.isfinite(seen['grad_norm']):
        raise SystemExit('FAILED: non-finite gradient')
    if not any(d.startswith('cuda') for d in seen['devices']):
        raise SystemExit('FAILED: optimizer parameters are not on CUDA')
    if not args.real_generate and not len(calls):
        raise SystemExit('FAILED: no tool call executed')
    if seen['changed'] == 0:
        raise SystemExit('FAILED: the training step changed no parameters')
    if args.quant_lora and not four_bit:
        raise SystemExit('FAILED: 4-bit quantization did not apply')
    if seen['grad_norm'] < 1e-3:
        raise SystemExit('FAILED: gradient is numerically zero, so a change proves nothing')


if __name__ == '__main__':
    main()
