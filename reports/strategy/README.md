# Investigation runs on the real untrained model

Quantized Q4 GGUF of Tiny Aya on the laptop, inference only, plus the Claude workflow test. Nothing here is trained, and all are small development runs. Do not combine scores across setups.

| Files | What they are |
|---|---|
| `smoke_strong_1`, `tune_strong_1` | Early prompt tuning |
| `baseline_plain`, `baseline_strong`, `diagnostic_assisted` | First baseline, 9 cases. Replaced. New evidence arrived only after a test was proposed, so only 1 of 6 strong runs received it, and 6 total rejections ended a run. |
| `fair/` | **Harness failure, kept on purpose.** A `challenges_theory` field made every strong run fail at its first search, because the model wrote "None" and the tool wanted "none". Says nothing about the model. |
| `fair2/` | First fair baseline: 12 cases, with fair delivery of new evidence and a limit on errors in a row. Replaced by the runs below |
| `staged/base_q4_open` | Arm A at `a7187b9`: open workflow with the strong prompt. Development run |
| `staged/base_q4_structured` | **Diagnostic.** First stage controller, at `a7187b9`. It found harness faults that contributed to its 0 of 12, so it does not show what the model can do |
| `staged/base_q4_structured_v3` | Arm B on the corrected controller, 15 cases, with a setup id. There is no v2: that run never started |
| `teacher/first_three_b` | Aya Expanse 32B Q4 on three cases. All rejected as training data, with reasons in `reviews/teacher_review/first_three.md` |
| `base_full/bf16_structured` | Tiny Aya at full precision, three-theory controller, `8a27c1f`: 0 of 15 finished |
| `base_full/bf16_protocol` | Tiny Aya at full precision under the agreed rules, `b14918e`: 1 of 15 finished, 11 reached two theories. The current best estimate of arm B |
| `variants/` | **Q4 development variants, partly stopped.** The laptop ran out of memory during them. Q4 understates the model (1 of 15 reached two theories, against 11 at full precision), so these are superseded by the full-precision variants |
| `teacher/cap_first_three` | **Harness failure.** Command A+ wrote a thinking block before each valid call, and the parser rejected it. Fixed in `b9cd4a6` |
| `variants_full/` | Full-precision variants on the same suite, `de00d9f`. Baseline 1 of 15 finished and 116 refusals, the same as `bf16_protocol`, so runs at temperature 0 reproduce. Reasoning first: 1 of 15 and 54 refusals. Compact state: 0 of 15, all stuck at evidence, so it is dropped |
| `provenance.jsonl` | Append-only record of which backend and weights produced each episode |
| `control/` | Claude as a workflow test, never training data. Spending is in `claude_ledger.jsonl`. `claude_structured_12` ran the first controller, and `claude_structured_v3` the corrected one |

Tool arguments changed between these sets, so earlier runs cannot be replayed by the current tools.
