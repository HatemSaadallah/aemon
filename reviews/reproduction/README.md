# Codex reproduction of Claude PR #2

Reviewed head `a4d1e27a77ad4c48a15b4d15579ec5838664871a`, November 1, 2026, same laptop and shared environment. This is an independent execution/review of Claude's code, not independently written GPU software.

## Intervals

`python3 reviews/recheck_intervals.py [path/to/tooling/redteam]`

Recomputed scenario values on all 400 test, 400 shift and 400 conjunctive scenarios using Claude's evaluator. Wrote separate normal-CI, bootstrap-statistic and power-statistic implementations; did not call Claude's CI/bootstrap/power functions. Used its documented random resampling stream (2,000 draws, seed 0) to permit numerical comparison. All policy interval endpoints match submitted JSON within 1e-10. Rounded interval endpoints printed in findings.md also match, including all three originally corrected test intervals and conjunctive intervals.

Posterior-value power-size bootstrap: [84.840984, 7321.403604]. Realized-utility: [154.281557, unbounded]. These are unstable plug-in summaries, not guarantees of future test power. Their exact reproduction does not validate the approximation. Normal regret intervals with negative lower bounds remain untruncated approximate intervals, not physically negative regret.

## GPU

Commands used the existing `.venv/bin/python`, Claude's reviewed probe scripts, and cached AgentTune checkout d4db4c1; no weights/dependencies were downloaded.

- `vram_probe.py --output .../vram_probe.json` completed. Memory matched every successful configuration to the MiB: 3283/3912 at 256 tokens, 4215/5448 at 512, 5831/6598 at both 2×512 and 1×1024 (allocated/reserved). All four tested configurations at 2048+ total tokens raised the expected OOM.
- Shape-matched random-weight generation: 17.9 tokens/sec vs Claude's prior 24.3, about 26% slower; peak allocation matched at 2711 MiB. This is one short un-warmed run, not evidence of a stable performance regression or real-checkpoint throughput.
- `grpo_gpu_smoke.py --agenttune-repo <cached checkout> --real-generate --quant-lora` completed. One CUDA optimizer step, 28 quantized linear modules, 14/28 LoRA tensors changed, gradient-norm sum 0.0110064, 187 MiB peak. Zero tool calls emitted by random generation, as expected: no real-model tool-use quality is demonstrated. Synthetic batch-index reward tests gradient plumbing only.
- Three `test_redteam` unit checks passed.

Real Tiny Aya weights, exact checkpoint configuration, distillation quantization/masking, and useful learning remain untested. GPU is released after these checks. Full terminal logs stay ignored locally; JSON results are committed. Sample-size `Infinity` in Claude's JSON is a nonstandard Python extension; our output uses the string `unbounded` to preserve valid JSON.
