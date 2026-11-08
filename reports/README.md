# Real-model runs

Everything here is **inference or measurement only**. Development runs, not a final test.

## Runtime on the laptop

- Model: Cohere's own `CohereLabs/tiny-aya-global-GGUF`, file `tiny-aya-global-q4_k_m.gguf`, revision `a602ea7eeec3a4ad6f77a1b8cf6a53512824922b`, sha256 `d01d995272af305b2b843efcff8a10cf9869cf53e764cb72b0e91b777484570a`. CC-BY-NC-4.0.
- Runtime: llama.cpp build b12032, all layers on the GPU, temperature 0.
- Chat template: read from the model file. Its sha256 `2147c474f41b522b7296f74692b9f31e45f49a31465960576a9d321339c5915a` matches AgentTune's vendored `tiny_aya_default.jinja`.
- Q4 is not the precision used in the cluster pilots, which run the bf16 GGUF, so laptop runs are not pilot results.

Start the server with `./app/run_model.sh`, which also loads a trained adapter if one is present.

## Files

| Path | What it is |
|---|---|
| `strategy/` | Investigation runs of every arm and diagnostic, with their reports and episode logs |
| `strategy/pilot1/` | The first paired pilot: base and first adapter, the same 10 cases and settings |
| `strategy/row_coverage_first.json` | Row retention by stage and company, full history against compact, from `src/strategy_agent/pipeline/row_coverage.py` |
| `checkpoint_gate.json` | The loss-masking gate from `src/strategy_agent/training/masking_gate.py` |
| `live/` | The live training feed for the Strategy Lab, kept current by `scripts/training_feed.py`. Not committed |

The launch-decision runs that used to live here were removed with that code on November 3, 2026. They are in git history.
