# Final evaluation plan

Written 2026-11-04, before the final training run and before any final-test output exists. Codex owns the protocol
(`docs/EVALUATION_PROTOCOL.md`) and reviews this plan. Anything here may change only before the freeze, with the reason
recorded in `docs/DECISIONS.md`; after the freeze, nothing changes.

## Order

1. **Before training:** loss masking (`src/strategy_agent/training/masking_gate.py` and the prefix check in `strategy/rows.labels_for`),
   split isolation (the freeze and split tests in `tests/test_strategy.py`), and row coverage (`src/strategy_agent/pipeline/row_coverage.py`:
   no length refusals, no target naming anything missing from its context). A failure stops the run.
2. **Train once:** all accepted teacher investigations plus recovery corrections at about 20% of supervised tokens, as
   a target and not a requirement; the report gives the actual share by rows and tokens. Checkpoint chosen on the
   company-balanced validation loss over the six companies in `src/strategy_agent/pipeline/splits.py`.
3. **After training, before any evaluation:** the adapter conversion gate (`src/strategy_agent/evaluation/conversion_check.py`). A failure
   stops evaluation.
4. **Development evaluation** on the six validation companies, every case.
5. **Choices, from development results only,** recorded before the freeze (below).
6. **Freeze**, then **one final test campaign** on the four held-out companies.

## The comparison

- **Strongest prompted base.** Tiny Aya without an adapter, under the same tools, stage controller, evidence and budgets.
  Its prompt is chosen on development data only: the base arm runs both the `staged` and the `compact` prompt on the
  validation cases, and the one with the higher mean blind-judge score is the base for the final test (completion breaks
  a tie). The choice is recorded before the freeze.
- **The trained arm.** The final adapter, or the second adapter as the fallback, chosen on development results only by
  the same rule: higher mean blind-judge score on the validation cases, completion breaking a tie. If the final adapter
  fails a gate in steps 1 to 3, the second adapter is used and the failure is reported.
- Both arms use the same bf16 GGUF, llama.cpp build, context, temperature, seeds and turn and error limits; the only
  difference is the adapter (and, for the base, the prompt chosen above).

## Measures, in development and in the final test

The same in both campaigns:
- **Blind quality judging** with Codex's frozen judge package (PR #24): the rubric's dimensions and the per-episode score,
  two judges that are neither the student nor the teacher, arm names removed, packet order randomised, anchors included.
  Completion and fewer loops alone cannot establish better investigation.
- **Mechanical measures** from `src/strategy_agent/evaluation/progress.py`: finished, highest stage completed, refused and repeated calls per
  run, sources read and used; plus the guards (`src/strategy_agent/env/checks.py`), reported as guards, not quality.
- Negative controls: the scripted always-keep and always-revise policies on the same what-if packets.

## The final test campaign, defined now

- **Cases:** every case in `cases_heldout.json` at the freeze (the four companies' base and irrelevant-evidence cases,
  plus Codex's supporting and undermining packets if PR #23 is merged and refrozen before the freeze, and not otherwise).
- **Seeds:** three attempts per case and arm (attempts 0, 1 and 2: seed by case and attempt as in `src/strategy_agent/agent/runner.py`),
  temperature 0, 0.4 only on a retry straight after a refused call, as in development.
- **Budgets:** the case budgets in the dossier; 45 turns, 4 errors in a row, 520 tokens per turn, the same context.
- **Infrastructure retries:** an episode is rerun with the same seed only if the harness or server failed (an HTTP error
  other than a context limit, a server crash, a node failure), at most twice, every retry logged with its cause. An
  episode is never rerun because of anything the model did. An episode that still fails is reported as missing.
- **Reporting:** each company separately, then pooled with case-cluster bootstrap intervals; every judge separately;
  all missing episodes and exclusions. Four companies support only a limited claim about generalisation, and the report
  says so.

## Claim wording

At most: "on four companies it never saw, under the same investigation setup, the fine-tuned agent scored X against the
prompted base's Y under a blind LLM rubric", with the per-company results beside it. Not "better strategy" in general,
and nothing about business outcomes. A mixed result is reported as mixed, showing where training helped and where it
did not.
