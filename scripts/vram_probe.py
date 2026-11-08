"""Measure LoRA training memory for the REAL Tiny Aya architecture on this GPU.

The gated weights are not needed: memory depends on shapes, not on weight values.
Shapes come from the ungated GGUF header of CohereLabs/tiny-aya-global-GGUF
(36 blocks, 2048 hidden, 11008 feed-forward, 16 heads, 4 KV heads, vocab 262144).
Weights here are RANDOM. Output says nothing about model quality or token content.

Layers are quantized to NF4 one at a time on the GPU, so the roughly 6.7 GB bf16
checkpoint never has to exist in RAM or on disk. Differences from a real load:
real NF4 statistics differ slightly, and activations do not depend on content.

Usage: python vram_probe.py [--output vram_probe.json]
"""
import argparse
import json
import time
from pathlib import Path

import bitsandbytes as bnb
import torch
import transformers
from accelerate import init_empty_weights
from peft import LoraConfig, get_peft_model

ARCH = dict(vocab_size=262144, hidden_size=2048, intermediate_size=11008, num_hidden_layers=36,
            num_attention_heads=16, num_key_value_heads=4, max_position_embeddings=4096,
            pad_token_id=0, bos_token_id=5, eos_token_id=255001)
LORA_TARGETS = ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj']
DTYPE = torch.bfloat16


def mb(x):
    return x // 2**20


def build():
    cfg = transformers.Cohere2Config(**ARCH)
    with init_empty_weights():
        model = transformers.AutoModelForCausalLM.from_config(cfg, dtype=DTYPE)
    embed = torch.nn.Embedding(ARCH['vocab_size'], ARCH['hidden_size'], device='cuda', dtype=DTYPE)
    torch.nn.init.normal_(embed.weight, std=.02)
    model.model.embed_tokens = embed
    model.lm_head.weight = embed.weight  # tied: the GGUF has no separate output tensor

    for name, module in list(model.named_modules()):
        for child_name, child in list(module.named_children()):
            if isinstance(child, torch.nn.Linear) and child_name != 'lm_head':
                layer = bnb.nn.Linear4bit(child.in_features, child.out_features, bias=child.bias is not None,
                                          compute_dtype=DTYPE, quant_type='nf4', device='cpu')
                weight = torch.randn(child.out_features, child.in_features) * .02
                layer.weight = bnb.nn.Params4bit(weight, requires_grad=False, quant_type='nf4',
                                                 compress_statistics=True)
                setattr(module, child_name, layer.to('cuda'))
    for name, param in list(model.named_parameters()):
        if param.is_meta:
            owner = model.get_submodule(name.rsplit('.', 1)[0])
            setattr(owner, name.rsplit('.', 1)[1],
                    torch.nn.Parameter(torch.ones(param.shape, device='cuda', dtype=DTYPE)))
    model.model.rotary_emb = type(model.model.rotary_emb)(config=cfg).to('cuda')
    return model, cfg


def step(model, optimizer, batch, length):
    ids = torch.randint(10, ARCH['vocab_size'] - 10, (batch, length), device='cuda')
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    with torch.autocast('cuda', dtype=DTYPE):
        loss = model(input_ids=ids, labels=ids).loss
    if not torch.isfinite(loss):
        raise FloatingPointError(f'non-finite loss at batch={batch} length={length}')
    loss.backward()
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    torch.cuda.synchronize()
    return {'batch': batch, 'length': length, 'loss': round(float(loss), 3), 'seconds': round(time.perf_counter() - start, 2),
            'peak_allocated_MB': mb(torch.cuda.max_memory_allocated()),
            'peak_reserved_MB': mb(torch.cuda.max_memory_reserved())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=str(Path(__file__).with_name('vram_probe.json')))
    args = parser.parse_args()
    torch.manual_seed(0)
    out = {'weights': 'RANDOM, real architecture from GGUF header', 'arch': ARCH, 'lora': {'r': 16, 'alpha': 32},
           'torch': torch.__version__, 'device': torch.cuda.get_device_name(0)}
    start = time.perf_counter()
    model, cfg = build()
    out['build_seconds'] = round(time.perf_counter() - start, 1)
    out['loaded_MB'] = mb(torch.cuda.memory_allocated())
    # Count from shapes: a 4-bit parameter stores packed bytes, so numel() would undercount.
    params = ARCH['vocab_size'] * ARCH['hidden_size'] + sum(
        m.in_features * m.out_features for m in model.modules() if isinstance(m, bnb.nn.Linear4bit))
    out['true_params_billions'] = round(params / 1e9, 3)
    out['bf16_size_GB_implied'] = round(params * 2 / 1e9, 2)  # the published checkpoint is 6.70 GB
    print('loaded', out['loaded_MB'], 'MB')

    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, target_modules=LORA_TARGETS,
                                             task_type='CAUSAL_LM'))
    for param in model.parameters():
        if param.requires_grad:
            param.data = param.data.to('cuda', dtype=DTYPE)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    out['lora_trainable_millions'] = round(trainable / 1e6, 1)
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4)
    model.train()

    out['steps'] = []
    for batch, length in [(1, 256), (1, 512), (2, 512), (1, 1024), (2, 1024), (4, 512), (4, 1024), (2, 2048)]:
        try:
            result = step(model, optimizer, batch, length)
        except torch.cuda.OutOfMemoryError:
            result = {'batch': batch, 'length': length, 'OOM': True}
            optimizer.zero_grad(set_to_none=True)
            torch.cuda.empty_cache()
        print(result, flush=True)
        out['steps'].append(result)
        Path(args.output).write_text(json.dumps(out, indent=2) + '\n')

    model.eval()
    model.base_model.model.config.use_cache = True
    model.gradient_checkpointing_disable()
    torch.cuda.reset_peak_memory_stats()
    prompt = torch.randint(10, ARCH['vocab_size'] - 10, (1, 512), device='cuda')
    start = time.perf_counter()
    with torch.inference_mode(), torch.autocast('cuda', dtype=DTYPE):
        generated = model.generate(input_ids=prompt, attention_mask=torch.ones_like(prompt), do_sample=False,
                                   max_new_tokens=48, min_new_tokens=48, pad_token_id=0)
    torch.cuda.synchronize()
    seconds = time.perf_counter() - start
    new_tokens = generated.shape[1] - prompt.shape[1]
    out['generation'] = {'prompt_tokens': 512, 'new_tokens': new_tokens, 'seconds': round(seconds, 2),
                         'tokens_per_second_including_prompt_pass': round(new_tokens / seconds, 1),
                         'peak_allocated_MB': mb(torch.cuda.max_memory_allocated())}
    with torch.inference_mode(), torch.autocast('cuda', dtype=DTYPE):
        logits = model(input_ids=prompt[:, :64]).logits
    if not torch.isfinite(logits).all():
        raise FloatingPointError('non-finite logits in eval mode')
    out['generation']['logits_finite'] = True
    print(out['generation'])
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n')


if __name__ == '__main__':
    main()
