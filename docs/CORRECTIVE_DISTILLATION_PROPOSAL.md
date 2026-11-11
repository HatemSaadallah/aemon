# Corrective distillation from configuration D's invalid finishes: proposal for review (nothing is trained)

Status 2026-11-09: proposal only. No data is generated and no training run starts before Nour reviews the example
states and the evaluation plan below. Version 1, the evaluated configuration and both frozen test sets are untouched.

## 1. What D's finishes got wrong (stage 1, 28 training checkpoints; `experiments/recovery/stage1_invalid_finishes_D.json`)
Under D, 11 continuations finished. 2 passed every non-diagnostic guard and 9 did not, so finishing is not mechanically
valid completion, and neither says anything yet about recommendation quality (blind judging is stage 2 only).
Each failed guard was traced to the call that caused it, either in the checkpoint prefix, which version 1 wrote before
it got stuck and D never touched, or in the continuation that ran under D (`experiments/recovery/invalid_finishes.py`).

| guard failed (of 11 finishes) | n | caused in the continuation | inherited from the prefix | both |
|---|---|---|---|---|
| no_invented_numbers | 7 | 4 | 0 | 3 |
| experiment | 6 | 5 | 1 | 0 |
| evidence_kinds | 6 | 1 | 5 | 0 |
| evidence_classes | 5 | 2 | 1 | 2 |
| tool_use (whole-run refusal rate) | 5 | (prefix refusals count) | | |
| testable_predictions | 2 | 0 | 0 | 2 |
| existing_offering | 1 | 0 | 0 | 1 |

**Invented numbers (7).** In every located case the number first appears in the test D pushed the agent to write
(`propose_test`: sample ages "25–55", thresholds "WTP ≥ €150", "at least 15%") and is then repeated in the final answer
as a claim about the world (target customer, recommendation). The guard allows a plan to reuse its own test design but
not a claim; the model does not keep the two apart. One number (200000) is not found in any call and comes from the
final text alone.

**Experiments (6).** Two kinds: (a) a test proposed where the case does not warrant one, so the right action was
`decline_test` with a reason (2); (b) a test whose predictions per theory are near-mirror sentences ("T1: safety offer
≥10% higher… / T2: sustainability offer ≥10% higher…"), which the guard reads as not discriminating (4). Nine of the
ten tests written under D use the same template (online survey, 200–500 panel respondents, purchase intent and
willingness to pay): when the budget note arrives, the model writes the cheapest test it knows rather than one that
separates its theories. None of the 10 declined.

**Evidence kinds (6) and classes (5).** These come mostly from earlier weighing (5 of 6 kinds were wrong before the
checkpoint): D does not cause them; it lets those runs reach the end, where the guard is checked. Class failures are
theories that rest only on the company's own claims; the agent did not look for independent evidence.

**What this means for D.** D turns "ran out of steps" into "finished with a weak test and borrowed numbers". The
controller can make the run reach a conclusion; it cannot make the test or the evidence handling good. Those are policy
errors and need training or stricter guards.

## 2. Proposed dataset: four on-policy state families
States are taken where version 1 (with D on, the runtime that would ship) actually is, on training companies only.
Command A+ writes the single next call (Claude is never a teacher: commercial terms D.4). Every kept example passes the
existing tool guards plus the per-family gate. Development cases, held-out cases and test set 2 are never used.

| family | state | correct target | per-family gate (mechanical) | source of states |
|---|---|---|---|---|
| F1 test or decline | test step, any budget | `decline_test` with a reason when the case does not warrant a test; otherwise `propose_test` whose predictions differ in direction or measure, not just wording, and whose decision rule has a threshold | `experiment` check passes on the resulting state; prediction similarity < 0.8 | D continuations at the test step (stage 1 + new D rollouts on training cases) |
| F2 test-number hygiene | position and finish after a test | claims use only numbers from read sources or the brief; test design numbers appear only in next_action / would_change_if | `no_invented_numbers` passes; every claim number is in a read excerpt | the 7 failing finishes' states, plus new D rollouts that reach finish |
| F3 evidence kind | `assess_evidence` | the annotated kind for that source passage | kind matches the case annotation | prefix states from failed runs (weighing step) |
| F4 independent evidence | theories supported only by company claims | search or read a non-company source, then assess it | `evidence_classes` passes after the follow-up | theory states from failed runs |

Expected size before gating: on the order of 150–250 states per family (from about 75 failed training runs plus new D
rollouts). Acceptance rates for targeted teacher batches have been 3% (test design, round 3) to 37% (weighing), so the
kept set may be small for F1; that is reported, not padded. Recovery examples (no progress for 3 calls → a call that
progresses) are kept separate and labelled, since D already handles most of those without training.

## 3. Review before any training
1. Generate the states and teacher answers (cluster, Slurm only), gate them, and export 20 per family to the Review
   page, each showing the state, the call and the gate verdict.
2. Nour reviews: accept the families, change a gate, or drop a family.
3. Only after that: mix with the version 1 training data in the version 1 proportions, train a new adapter (named
   version 2-candidate), and evaluate as below. Version 1 stays as it is.

## 4. Evaluation plan (to fix before training)
- **Arms:** version 1 + D against version 2-candidate + D, same base, runtime, controller and seeds, on the 15
  development cases × 3 attempts. Version 1 as evaluated is a third, reference arm.
- **Reported separately, never merged:**
  - recovery: whether the agent moves past the step it was stuck on, on the stage 1 benchmark
  - completion: an accepted finish
  - mechanically valid completion: a finish with every non-diagnostic guard cleared
  - recommendation quality: the mean blind-judge score (Claude now, Codex from 11 November), with company-bootstrap intervals
- **Primary:** mechanically valid completion. The candidate is preferred only if it is higher, the judge quality is not
  lower, and the invented-number and experiment failures fall.
- **Guard-rail metrics:** simulated-evidence citations (must be 0), refusals by category, rereads.
- **Frozen test sets:** not used. A frozen test is run once only after this plan is approved and the candidate is
  selected on development alone.
