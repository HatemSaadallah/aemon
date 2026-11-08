# Tooling verification

Claude, November 1, 2026. TESTED means executed here, VERIFIED means read from a primary source, ESTIMATED means derived from measurements, and UNTESTED means nobody has run it. Revised after Codex's review on PR #2, which reran the GPU probes.

## Bottom line

Three separate results, which should not be merged into one claim:

1. **Software path.** One GRPO optimizer step runs on this GPU with the existing driver. This is gradient plumbing on a tiny random model with a meaningless reward. It shows nothing about useful learning.
2. **Memory.** A shape-matched, random-weight NF4 and LoRA probe fits at about 1,024 tokens per step. Shapes come from the GGUF header, so the real `config.json`, attention settings and tokenizer remain unverified.
3. **Real model, inference only.** Cohere's ungated Q4 GGUF of Tiny Aya now runs on this GPU, and its chat template matches AgentTune's copy. See `real_model/README.md`.
4. **Not done.** Nothing has been trained on real weights, and end-to-end distillation is untested. The full weights remain gated, which blocks real training. See below.

## What Hatem has to do

| # | Action | Why | Status |
|---|---|---|---|
| 1 | Accept the licence on https://huggingface.co/CohereLabs/tiny-aya-global | The token gets `403 GatedRepo`, "you are not in the authorized list". | VERIFIED |
| 2 | Enable "Read access to contents of all public gated repos you can access" on the fine-grained token, or make a read token | The token's global scopes are only `discussion.write` and `post.write`, so it will probably still fail after step 1. | INFERRED |
| 3 | Free at least 10 GB | 1.9 GB is free, after the 2.1 GB Q4 GGUF, which can be deleted once training replaces it and the weights are 6.7 GB. The largest single item is `~/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct` at 15 GB. Nothing was deleted. | VERIFIED |

## Results

| Check | Result | Evidence |
|---|---|---|
| CUDA on driver 550.163 | Works with `torch 2.11.0+cu128`. No driver change. | TESTED |
| 4-bit NF4 | Works: bitsandbytes 0.50.2 on the GPU. | TESTED |
| AgentTune install | Works after one fix (below). | TESTED |
| Cohere tool-call tests | 51 passed, CPU, no downloads. | `agenttune_cohere_tests.txt` |
| Tool round trip | 2 tool calls executed on the GPU, with generation forced. Not yet by a real model. | TESTED, forced |
| One GRPO step on the GPU | Non-zero gradient: norm 0.055, loss 0.696, 18 of 18 parameters changed. Tiny random model, reward is the batch index: plumbing only. | `grpo_gpu_smoke.py --real-generate` |
| One GRPO step, NF4 and LoRA | Non-zero gradient: norm 0.011, 28 `Linear4bit` modules. 14 of 28 LoRA tensors changed. We expect that because `lora_B` starts at zero, so `lora_A` gets no gradient on step one. Same limits as above. | `--real-generate --quant-lora` |
| Tiny Aya shapes | `cohere2`, 36 blocks, 2048 hidden, 11008 feed-forward, 16 heads, 4 KV heads, vocab 262144. These give 3.349B parameters, implying 6.70 GB, which matches the published checkpoint. Real config, attention and tokenizer are unverified. | `gguf_header.py`, `gguf_header.json` |
| Chat template | Does not render `tools`. AgentTune puts schemas in the system prompt and returns results as user turns. | VERIFIED, test fixture |
| AuditKIT with our metric | `CustomPredicate` scored a regret threshold correctly, success and failure. | `check_bridge.py`, `check_bridge.json` |
| AgentTune to AuditKIT | `episode_from_eventlog` imports a run with full coverage. **Gotcha:** when the agent ends with a `finish` tool call, `final_answer` is `None`, so a predicate on it marks every correct decision as a failure. Read the `finish` call from `episode.events` instead. | `check_bridge.py`, `check_bridge.json` |

### Two results that nearly misled us

- AgentTune's own GRPO test sets `use_cpu=True`, so passing it says nothing about GPU training.
- Patching `generate` gives gradients of about 1e-9 and `train_loss` 0, yet 14 to 15 parameters still change because Adam rescales numerical noise. A "parameters changed" check is not evidence of learning. `grpo_gpu_smoke.py` now fails unless the gradient is real, and the forced mode fails that check by design.

## The pipeline on our own task

`../pipeline.py` connects both tools on the two-assumptions family, with no model weights. The planner plays cases through the same game the app serves, each run becomes an AgentTune `EventLog`, `Project.add_trajectory` and `sft_dataset` turn those into training rows, and AuditKIT scores each agent's runs. The Pipeline tab in the Decision Lab shows the result and can rerun it live.

```bash
python pipeline.py --n 100 --agenttune-repo /tmp/at
```

At 100 simulated cases: 100 demonstration rows with 196 demonstration tool calls, and 57 rows that correctly stop with no research. **Nothing was trained.** Cases passing the combined check were Optimal planner 100, Myopic VOI 77, One look 71, No research 59 and Spends the whole budget 0. A negative control that calls a tool it does not have scored 0, with 59% valid calls. These are classical policies, so this shows the plumbing and the scoring work. It says nothing about a trained model.

Three things we learned that matter for real training:

- AgentTune's targets use `<tool_call>` tags, but its default fallback prompt asks for a JSON list. We pass one `TOOL_PROMPT` to training and evaluation through `tools_fallback_prompt`, so the model is not trained on one format and told another.
- Tiny Aya's vendored template rejects raw rows ("Conversation roles must alternate"). AgentTune's repair functions fix them. After repair the system prompt survives, with 6 of 6 tool results and 7 of 7 calls kept. That is the template file only, not the model's real tokenizer.
- AuditKIT's loop detector flags the optimal planner on 7% of runs, because repeating a noisy study can be correct. We treat loop and redundancy scores as diagnostics, not verdicts.

**Loss masking is not settled.** `sft_dataset` writes `segment_weights` and `loss_mask`, but the stand-in review found nothing in AgentTune that reads them, and `SFTConfig.assistant_only_loss` defaults to False, so by default loss covers every token. Real training must set assistant-only loss and check it on Tiny Aya's template. That is untested. `Project.train` also rebuilds rows, and may drop our system prompt.

## Memory on this GPU

From `vram_probe.py`: **shape-matched, random weights**, NF4, LoRA r=16, gradient checkpointing. Memory depends mainly on shapes, and repeated runs matched to the MB, but this is not a real-checkpoint measurement. Attention settings could change it. The probe stops on a non-finite loss. Loss was 12.48, which matches ln(262144) = 12.48 for random predictions over this vocabulary.

About 6.6 GiB of the 8 GB is usable, because the desktop holds about 1.1 GB in dGPU-only mode.

| Tokens per step | Batch × length | Peak allocated | Peak reserved | Seconds |
|---:|---|---:|---:|---:|
| 256 | 1 × 256 | 3,283 MB | 3,912 MB | 0.70 |
| 512 | 1 × 512 | 4,215 MB | 5,448 MB | 0.66 |
| 1,024 | 2 × 512 | 5,831 MB | 6,598 MB | 1.23 |
| 1,024 | 1 × 1024 | 5,831 MB | 6,598 MB | 1.19 |
| 2,048 | 2 × 1024, 4 × 512 | OOM | | |
| 2,048+ | 4 × 1024, 2 × 2048 | OOM | | |

- Weights load at 2,409 MB. LoRA adds 30.2M trainable parameters.
- Generation at 512 prompt tokens and 48 new tokens: 17.9 to 24.3 tokens per second across six runs by both agents, always with a 2,711 MB peak. Consecutive runs on an idle machine gave 19.7 and 23.9, so this is run-to-run variance, cause unknown. Treat throughput as variable, not a planning constant. Codex reran the probes on this laptop with these same scripts and matched memory to the MiB: `reviews/reproduction/README.md`.
- INFERRED: peaks depend on total tokens, not batch shape, which fits logits over a 262,144-word vocabulary dominating. Computing logits only for completion tokens should help. UNTESTED.

## Estimates from those numbers

These extrapolate from single steps and are not measurements. One step's time is not a measured SFT epoch.

| Job | Assumption | ESTIMATED |
|---|---|---|
| One SFT pass over 1,200 episodes | One 1,024-token step per episode at 1.2 s. Multi-turn episodes may yield several examples, so this is a lower bound. | At least 25 minutes |
| One episode | 3 turns of 60 tokens at 18 to 24 tokens per second, with no tool time | 8 to 10 seconds |
| 900 evaluation episodes | At 8 to 10 s each | 2 to 2.5 hours |
| GRPO | 2 generations of 512 tokens fit one step. Published scale does not. | Small pilot only |

## Still UNTESTED

1. Any of this on the real weights: loading, quantizing, the real config and tokenizer, a real tool round trip, or tool-call quality.
2. `create_distill_trainer` with 4-bit. It takes `dtype` and `device_map` but no quantization option, so it probably needs a custom `trainer_factory`. This is the recommended training path, so it is the main remaining technical risk.
3. Whether `completion_only_loss` masks tool results on multi-turn trajectories.
4. Useful learning of any kind. No run here has a reward or loss tied to correct behaviour.

## Reproduce

Do not skip the third command: PyPI's `torchvision` does not match the CUDA 12.8 torch and breaks `import peft` with `operator torchvision::nms does not exist`. Python 3.12.13. `.venv` uses 8.1 GB.

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python "torch==2.11.0+cu128" --index-url https://download.pytorch.org/whl/cu128
uv pip install --python .venv/bin/python "agenttune @ git+https://github.com/Lexsi-Labs/AgentTune@d4db4c1" "auditkit @ git+https://github.com/Lexsi-Labs/AuditKIT@71316da" pytest
uv pip install --python .venv/bin/python --reinstall-package torchvision "torchvision==0.26.0+cu128" --index-url https://download.pytorch.org/whl/cu128
```

All 277 packages, including transitive dependencies, are locked in `requirements.lock.txt`. Key versions: transformers 5.22.1, trl 1.7.1, peft 0.21.2, bitsandbytes 0.50.2, agenttune 1.1.3, auditkit 1.1.3. `torchao` prints warnings about optional native libraries, and nothing we ran depended on them.

```bash
git clone https://github.com/Lexsi-Labs/AgentTune /tmp/at && git -C /tmp/at checkout d4db4c1
cd tooling
python gguf_header.py
python check_bridge.py
python grpo_gpu_smoke.py --agenttune-repo /tmp/at --real-generate --quant-lora
python grpo_gpu_smoke.py --agenttune-repo /tmp/at   # fails its gradient check by design
python vram_probe.py
```

## Sources

- GGUF header: https://huggingface.co/CohereLabs/tiny-aya-global-GGUF at revision `a602ea7eeec3a4ad6f77a1b8cf6a53512824922b`, file `tiny-aya-global-q4_k_m.gguf`.
- Gated base model: https://huggingface.co/CohereLabs/tiny-aya-global at revision `af89d219b53ed9b13b8a4645f9c8028973510324`, metadata only.
- https://github.com/Lexsi-Labs/AgentTune at `d4db4c12d52342227c4113a70183d0f64aa2f345`.
- https://github.com/Lexsi-Labs/AuditKIT at `71316da`, full hash in `requirements.lock.txt`.

## Licences

| Item | Terms | Consequence |
|---|---|---|
| Tiny Aya, Aya Expanse | CC-BY-NC-4.0, gated | An ROI figure for self-hosting is hypothetical without a commercial licence. |
| AgentTune | LSAL v1.1, noncommercial | Keep notices. No Lexsi or AgentTune branding. |
| AuditKIT | LSAL v1.2 | Personal and academic use is under Section 1. Section 1A's written acknowledgement applies to an organization acting as such. Treating a student team as Section 1 is our reading, not legal advice. |
