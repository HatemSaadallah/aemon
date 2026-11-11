# V1.1 candidate: one runtime intervention, one evaluation (fixed 2026-11-10 15:45, before the run)

## Selection
Three runtime interventions were proposed. Each was checked against what V1 actually does on the 45 development runs
of the verification control arm (code 9f107b1). Today's lesson applies: V1 ignores advice it is shown (verification:
26 of 27 reviews answered by an unchanged evidence base), so only mechanical changes can work.

| intervention | what V1's runs show it could change | feasible today? |
|---|---|---|
| critical-fact retrieval | 13 of 45 runs never read what the company already sells; 6 of 24 finishes fail `existing_offering`. A harness search can surface records, but V1 must still choose to read and use them. | effect uncertain |
| **evidence metadata → evidence-consistent position** | in **10 of 24 finishes the favoured theory has no supporting weighing while another theory has one**; 21 of 24 cite a source never weighed. Constrained decoding makes the choice follow the record; V1 cannot ignore it. Historical source availability does not affect the deployed system or either frozen test, which are present-day. | yes, about 1 hour, no retraining |
| experiment validation | 26 of 27 tests fail `experiment_v2`, but a validator can only refuse. V1 cannot repair a test, and 17 of 45 runs already end on refusals. | low |

**Chosen: the evidence-consistent position** (`aemon.agent.experimental.grounded`). Wherever the agent's own weighings
support at least one theory, `state_position` and `finish` offer only those theories as the favoured one. `finish`
offers only real sources it weighed as citations. Texts remain the model's own. `state_position` writes the favoured
theory before its text, so the recommendation is written after the supported choice is fixed. Otherwise the choice is
left as it is. Separate entry point; the runner, tools, adapter and frozen results are unchanged.

## Evaluation
- **Arms:** the existing V1 control arm (job 751713, code 9f107b1) and V1.1 (one new job). The runner and tools are
  unchanged since 9f107b1; the new code only adds the module. Both arms use the same bf16 runtime, adapter 41794b57,
  compact prompt, settings and seeds, on the 15 development cases × 3 attempts. No frozen test is used.
- **Measures that the constraint does not decide by construction (primary):**
  1. blind quality (Claude, judge-v1 unchanged, arm hidden): the mean and the recommendation and evidence-judgement
     dimensions, with paired differences and a company-cluster bootstrap 95% interval;
  2. validated completion;
  3. finished runs;
  4. `numbers_cited` and `no_invented_numbers` failures;
  5. stops on repeated refusals.
- **Reported, but satisfied by construction:** `follows_evidence` and citations of unweighed sources. These are never
  counted as an improvement.

**V1.1 is better than V1 only if all of these hold:**
1. Blind mean V1.1 − V1 ≥ +0.05, with the interval's lower bound ≥ −0.02.
2. The recommendation dimension is not lower.
3. Validated completion is not lower.
4. At most 1 fewer finish.
5. No more `numbers_cited` failures.

Otherwise V1 is frozen for submission and V1.1 is reported as tried. One configuration, one run, no tuning.

## Result (2026-11-10 17:25, job 752407, code 426694f; 39 of 45 runs done when decided)
| | V1 (same 39 runs) | V1.1 |
|---|---|---|
| finished | 20 | 10 |
| validated completion | 3 | 1 |
| stopped by repeated refusals | 15 | 25 |
| unsupported recommendations | 16 | 6 (half as many finishes) |
| `numbers_cited` / `no_invented_numbers` failures | 5 / 7 | 3 / 4 |

**Cause.** The tools already require a theory to be challenged before it can be stated as the position. V1 usually
challenges the theory it prefers. The constraint then offers only a different, supported theory that was never
challenged. `state_position` is refused, V1 repeats the call, and the run ends: 46 of the refusals in the failed runs
are this one.

**Decision under the fixed rule.** Criterion 4 (at most 1 fewer finish) is already failed whatever the last 6 runs do:
10 behind, at most 6 to recover. Criterion 3 (validated completion) also fails on the runs so far. **V1.1 is not better
than V1. It is rejected, and V1 is frozen for submission.** Blind judging was not run, because it could not change the
decision.

A variant that also requires the theory to have been challenged would be a new configuration chosen after seeing
these results. It is not run before the deadline.

**All 45 runs (completed after the decision; `experiments/verify/report_v11.json`, whose treatment arm is labelled
`v1_verify` by the shared script):**

| | V1 | V1.1 |
|---|---|---|
| finished | 24 | 14 |
| validated completion | 3 | 1 |
| stopped by repeated refusals | 17 | 27 |
| unsupported recommendations | 20 | 10 |
| `numbers_cited` failures | 9 of 24 | 7 of 14 |

The decision stands.
