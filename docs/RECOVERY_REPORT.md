# Failure-aware recovery for Aemon: final report (2026-11-09)

Pre-registration, audit, taxonomy and benchmark: `docs/RECOVERY_EXPERIMENT.md`. Analysis of D's invalid finishes and the
next training proposal: `docs/CORRECTIVE_DISTILLATION_PROPOSAL.md`. Nothing here changes version 1, the evaluated
configuration, either frozen test set or their results; no new training ran.

## Four outcomes, kept apart
| term | meaning | measured by |
|---|---|---|
| **Recovery** | a run stuck at a step reaches a later step or finishes | stage 1 only (checkpoints) |
| **Completion** | the agent's `finish` call was accepted | both stages |
| **Mechanically valid completion** | finished, and every non-diagnostic guard cleared | both stages |
| **Recommendation quality** | mean blind-judge score, 0–3 per dimension, unreached = 0 | stage 2 only (Claude; Codex from 11 Nov) |

A higher number in one row says nothing about the rows below it unless measured there.

## Stage 1: resuming 28 dead ends (Mac, Q4 runtime; paired; company-bootstrap 95% intervals)
| | A as evaluated | B reread mask | C progress notes | **D budget** | E citations | F all four |
|---|---|---|---|---|---|---|
| recovery | 6 | 11 | 5 | **15** | 6 | 17 |
| completion | 3 | 7 | 3 | **11** | 3 | 11 |
| valid completion | 1 | 1 | 0 | **2** | 1 | 0 |
| recovery vs A | | +0.18 [0.00, 0.38] | −0.04 [−0.19, 0.11] | **+0.32 [0.16, 0.52]**, 9 better / 0 worse | 0 | +0.39 [0.19, 0.62], 12 / 1 |

D is selected under the fixed rule (F is excluded because its valid completion, 0, is below A's 1).
**Most of D's extra finishes are not valid:** 9 of 11 fail at least one guard: invented numbers 7, experiment 6,
evidence kind 6, evidence class 5. Traced to their cause, the invented numbers and the experiment failures are made in
the continuation, by the test that D pushes the agent to write: 9 of 10 are the same cheap survey template, none
declines a test, and its sample and threshold numbers reappear in the final claims. The evidence-kind errors (5 of 6) were
already in the run before D took over. Stage 1 therefore shows **more recovery and more completion, not better
investigations**.

## Stage 2: 45 end-to-end development runs (cluster, bf16 runtime, same code 52d4f4a, adapter 41794b57, seeds)
| | as evaluated | D budget | difference |
|---|---|---|---|
| completion | 24 / 45 | 25 / 45 | +1 run |
| valid completion | 3 | 3 | 0 |
| stops: repeated errors / turn limit | 17 / 4 | 17 / 3 | |
| simulated-evidence refusals; accepted simulated citations | 12; 0 | 12; 0 | |
| **quality (Claude, blind, 45 pairs)** | **1.047** | **1.053** | **+0.006 [−0.017, 0.031]** |
| quality by company (D − control) | | | acr +0.04, jotun +0.06, neumann −0.06, deere/hellberg/tanita 0 |

37 of 45 runs are identical step for step: D acts only when the steps left barely cover what the run still needs, and
most full runs fail earlier, after four refusals in a row, which D does not touch. The 8 that differ diverge after call 32.

## Adoption rule (fixed 12:50, before any result)
1. finishes more runs: **25 > 24, passes by one run**
2. does not lower judged quality (+0.006 [−0.017, 0.031]) nor valid completion (3 = 3): **passes**
3. keeps every guard and termination rule: **passes** (schema masking only; guards and stops unchanged, tested)
4. adds no simulated-evidence citation: **passes** (0 in both)

## What was integrated, what stays experimental, what needs training
**Integrated (optional, off by default, labelled):** Aemon has a *Finish-on-time guard* toggle next to Web
search. When on, the run's label says "experimental step-budget guard (not part of the evaluated setup)", saved results
are never reused across it, and the page warns that answers can be rushed. Version 1, the frozen evaluation settings
and every default are unchanged. In the Lab the step limits are 100–1000, so the guard only acts near the end of a long
run.

**Experimental, not integrated:** B (reread mask: much more efficient, recovery gain borderline, 2 regressions), E
(citations: fixes the simulated-evidence dead end 3/3 but those finishes are not valid), F (excluded by the rule: valid
completion 0, one case where A finished and F did not), C (no effect).

**Needs fine-tuning, not a controller:** the four failure families in the distillation proposal: test-or-decline
judgement and discriminating tests, keeping test numbers out of claims, evidence-kind classification, and looking for
independent evidence. The dominant end-to-end failure, four refusals in a row (17 of 45 runs), is also a policy problem.

## Recommendation
**D should remain experimental.** It meets the pre-registered rule, but only by one finished run in 45, with quality and
valid completion unchanged, so it is available in Aemon as an opt-in, labelled option and not as the
default. It is not evidence of better investigations: its gain on stuck runs comes with rushed tests and borrowed
numbers. Making it a default needs the corrective training first (reviewed examples, then a development comparison of
version 1 + D against the new candidate + D), and one more safeguard: a run that finishes under the guard should be
flagged on its report when the invented-number or experiment check fails.

## Deviations and limits
- The first stage 2 submission ran 3 of 45 runs (Slurm split the case list at commas); resubmitted with the full list
  under new names, the 3-run outputs kept and unused.
- Two judge attempts failed before any API call (missing SDK on the Mac; per-run cap counted earlier campaigns that used
  the same folder name). The batch cap was raised from 6 to 13 dollars because the check uses a worst-case estimate;
  actual spend $5.16 for 50 packets (the 45 + 45 runs share 37 identical packets), above the $3–4 estimate.
- Both stage 2 arms ran with the conversion gate's known diagnostic failure, as every development run of this adapter
  has; they are compared only to each other.
- Stage 1 ran on the Mac's Q4 runtime, stage 2 on the evaluated bf16 runtime. Recovery rates are conditional on failure.
- One judge so far; Codex judging is possible from 11 November and is reported separately when run.

## Worked examples (stage 1)
- **Valid recovery, festool-new-evidence-irrelevant (test step, 16 steps left).** A spent all 16 steps reading sources.
  Under D the budget note arrived, it proposed a test, stated a position, revised and finished in 13 calls with every
  guard cleared.
- **Recovery without quality, leitz-base (test step, 5 steps left).** A kept searching and ran out. D finished in 3 calls
  (test, position, finish), but the test's "≥ €150" and "120" reappeared in the recommendation: invented numbers.
- **Negative, trdc-new-evidence-irrelevant under F.** A recovered from one repeat refusal and finished. Under F the
  masked schema and notes left the model re-submitting the same assessment four times until it was stopped.
