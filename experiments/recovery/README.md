# recovery

The failure-aware recovery experiment, pre-registered on 2026-11-09 (`docs/RECOVERY_EXPERIMENT.md`). It measured how
much of version 1's unreliability a recovery controller fixes without retraining, on a benchmark of recorded
checkpoints (`benchmark_v1.json`). Stage 1 results and the report are `stage1_results.jsonl` and `stage1_report.json`;
`invalid_finishes.py` traces each failed guard to the checkpoint prefix or the continuation. The code is
`aemon.agent.recovery` (the controller, switched on with `--recovery`, development split only) and
`aemon.evaluation.diagnostics.recovery_bench` / `recovery_report`.

See `docs/RECOVERY_EXPERIMENT.md`, `docs/RECOVERY_PILOT.md` and `docs/RECOVERY_REPORT.md`; DECISIONS.md records no separate
heading for it.
