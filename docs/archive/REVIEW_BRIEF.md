# Strategy Agent: Status for Review

Two-eyed Ravens, Lexsi Track 3 (Agentic Fine-tuning). Status at November 2, 2026.

## Where it stands

We are building a small AI agent that investigates a strategic business question the way a scientist would. A working prototype runs end to end on real, verified evidence, and the real training path works on the Bocconi cluster. **No model has been trained, beyond one plumbing step, so there is no fine-tuning result yet.**

The untrained model cannot yet do the job. It frames problems well, but it does not complete an investigation or reliably change its view when evidence goes against it. We want feedback before committing to what to train.

## The project

**Goal.** A strategic opportunity-analysis agent for manufacturers exploring new consumer markets, inspired by Camuffo, Gambardella and Pignataro's scientific approach to strategy.

**What the agent must learn.** Clarify the objective, frame alternatives, build competing causal theories, state testable predictions, look for evidence that could prove them wrong, design discriminating experiments, revise when evidence changes, and recommend a next action with its uncertainty.

**First case, provisional.** Should Moldex-Metric, a maker of hearing and respiratory protection, develop a differentiated consumer proposition for a specific use case, beyond its existing hearing-protection offering? What evidence would justify that investment? Product redesign, venue distribution, a new customer group and no expansion all stay open. Cotral Lab and Hellberg Safety are comparison cases.

This is external analysis from public sources. No company has been contacted, and we claim no business outcome.

**Required stack.** A permitted Cohere model (Tiny Aya), AgentTune for fine-tuning, AuditKIT for evaluating complete episodes, compared with the strongest prompted base model.

## What exists

| Part | State |
|---|---|
| Evidence dossier | 142 records whose exact quotes were checked against live sources. 6 failed and were left out. Each is classed (verified, company claim, and so on) and annotated with its kind, place, population and what it does not establish. The annotations are LLM-written, not yet checked by a person. |
| Investigation tools | Ten guarded tools. Quotes must match the source, evidence must be read before use, and simulated results cannot support a recommendation. |
| Automatic checks | 17 checks. They are guards only: a deliberately nonsense investigation once passed the checks that existed then. |
| Rubric | A human scoring rubric, which is meant to be the main quality measure. No person has used it yet. |
| Evaluation | AuditKIT over complete episodes, with replay through the tools. |
| Training path | Tested on the cluster for one step (below). |
| Tests | 76 prototype tests pass. |

The work is on a branch and not yet merged, because the latest changes have not had independent review.

## Results: real untrained model

Quantized Tiny Aya on a laptop, strong prompt, step guidance and enforced JSON. Twelve cases: three companies, each with no new evidence, two simulated results that undermine a theory, and one that favours it. These are small development runs.

| Measure | Result |
|---|---|
| Passed every applicable check | 0 of 12 |
| Finished | 7 of 12 |
| Framed the problem well | 12 of 12 |
| Gave three distinct theories | 2 of 12 |
| Valid experiment, among finished runs | 0 of 7 |
| Challenged its favoured theory, among finished runs | 1 of 7 |
| Sound recommendation, among finished runs | 1 of 7 |
| Received the new evidence | 3 of 9 |
| Revised and cited it, among those 3 | 1 |

**Main pattern.** It quits early, often after about 8 calls, with one theory and no test. Supplying better sources improved its evidence quality in a separate run, but completion got worse (2 of 12).

**Latest test.** On three tuning cases, we refused to let it finish until every stage had happened. None finished: it kept calling finish rather than doing the missing work. Three cases is very few.

**Blind LLM pre-screen, on an earlier version.** Six model runs scored 5 to 8 of 24, and an authored reference scored 21. The same author wrote both the reference and the rubric, so that comparison is not fair. It is not human review.

The causes are suspected, not proven.

## Results: real checkpoint

Full weights on an A100 slice. All seven checks passed. This proves the plumbing, not that training helps.

| Check | Result |
|---|---|
| Weights | Load correctly: 3.349 billion parameters, 6.2 GB. Checksums match. |
| Forward pass and tool call | Work. The generated call used the right tool but invented arguments. |
| Loss masking | Loss falls only on the model's own turns: 478 of 3,735 tokens. |
| System prompt | Survives in the training row. |
| One AgentTune optimizer step | Finite loss, real gradients, only LoRA tensors change, 10 GB peak. |
| Adapter | Saves and reloads exactly: 288 of 288 tensors. |

A training row of about 3,700 tokens fits comfortably, so hardware is not the constraint.

## What we got wrong

These matter for judging how far to trust the results.

- We first said Moldex had no consumer line. It sells small blister packs, and third parties recommend its plugs for sleep. The question and briefs were corrected.
- An early "0 of 6 revised" was misleading, because only 1 of those runs ever received the new evidence. Delivery was fixed.
- One rerun scored 0 of 12 because of our own tool bug. It is kept and labelled.
- The prompt, checks and reference were all developed on Moldex, so Moldex cannot be the final test. A new company and product category must be held out.

## Plan

1. Find out whether a stronger setup can get the model through a complete investigation.
2. Rerun the baseline at full precision, so base and trained models are matched.
3. Get two people to review the rubric and reference runs.
4. Freeze held-out cases, write verified demonstrations, overfit a tiny set, then run a bounded pilot.
5. Compare with the strongest prompted base, with human rubric scores as the main outcome.

## Where we want feedback

1. **Is the model being asked to do the right job?** A small model may not be able to steer a ten-tool workflow. One option is for a fixed harness to run the steps, with the model doing only one stage at a time: writing a theory, assessing a source, designing a test. That is easier to train and evaluate, but it means the model is no longer deciding what to investigate. Is that still a meaningful agent for this track?
2. **What should training target?** Workflow control, or the quality of each stage?
3. **Is Moldex the right case, and is the question well framed?**
4. **Are authored demonstrations acceptable?** They would be executed through the real tools and labelled, but they are not a stronger model's output, and the track's "teacher" wording may not cover them.
5. **Is the evaluation sound?** Is the rubric measuring investigation quality, and is the paired test fair: does the recommendation change when evidence undermines the favoured theory, compared with a control where evidence favours it?
6. **What are we missing?** Especially anything that would make a before/after result misleading.
