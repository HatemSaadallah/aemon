# About `final_test_trained_conversion.json`

This file is the output of the **first** conversion check, retired on 6 November 2026 and kept because the final-test
job still ran it. It says `passed: false` because one of its five criteria, "conversion adds at most 0.15 to the base
gap", failed (0.237). That criterion compared log-probability gaps between the PEFT adapter and the converted GGUF
without separating conversion error from kernel noise between the two runtimes (bf16 on both sides), which is why it
was retired; the other four criteria passed (first token agrees on every prompt, greedy agreement 27 of 32 tokens,
log-probability gap at most 0.5, the adapter changes the output).

The gate that the result rests on is the second one (`src/aemon/evaluation/conversion/gate.py`): the converted adapter
replayed against the PEFT adapter on the same token inputs, with effect cosine at least 0.99 and probability-weighted
residual at most 0.15 on every replayed point, plus a weight-file audit. The evaluated adapter passed it (11 points,
lowest cosine 0.9990, largest residual 0.080), and `final_test_trained_adapter.gguf.sha256` in this folder matches the
gated file. Reports: `reports/conversion/`; decision: `docs/DECISIONS.md`, 6 November.
