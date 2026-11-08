# Version 2: a short continuation on targeted decision examples

Registered 2026-11-08, before any version 2 data exists. Version 1 (job 744559, the reported final-test result) stays
intact and is never retrained in place. Nothing here touches the four final-test companies.

## Why

The final-test diagnosis (`docs/FINAL_TEST_DIAGNOSIS.md`) and the development runs agree on what the training data
lacked. On development (final adapter, 7 finished of 15): 4 of 7 finished runs fail experiment design because the rival
theories' predictions barely differ or the decision rule has no threshold (all those cases warranted a test); 5 of 7
mislabel the kind of evidence and 3 of 7 use unsourced numbers; 3 of 8 unfinished runs reread to the limit and 1 stalls
on refused finishes. Revision on directional evidence could not be confirmed on development (only 3 such cases, none
failing); its evidence is the final test alone. More ordinary investigations would not address these gaps.

## Four skills, in priority order

| skill | what a target must show |
|---|---|
| 1. Experiment design | rival mechanisms mapped to different observable predictions, and a decision rule with a threshold that says what each result would lead to; within the stated budget and time |
| 2. Belief revision | update the theory the new evidence bears on, keep unrelated theories, change nothing on irrelevant evidence |
| 3. Evidence judgment | separate product capability from customer demand; say exactly which claim a quote supports; label the kind of evidence correctly |
| 4. Recovery | after a redundant read or a refused finish, advance with real evidence; treat a simulated result as hypothetical |

## Examples: one verified decision each, 100 to 200 kept

Each example is the actual compact state, the tools open at that stage, and one target action from the teacher
(Command A+). States are genuine: they come from replaying recorded teacher or student runs on **training companies
only**, so the existing rule holds (a row is kept only if its stored context equals today's replay).

Matched variants are written as real training-only cases (`data/dossier/cases_v2.json`), same company and dossier,
so a recorded run's opening calls replay unchanged up to the point where the variant takes effect:
- **Revision pairs:** the same state at the update step, with a simulated result that supports the targeted mechanism
  in one case and undermines it in the other (mirrored counts, identical record id and title, as in PR #23).
- **Capability versus demand:** the same source assessed for a capability claim and for a demand claim.
- **Test or decline:** the same state at the test step under the case's budget and time, and under explicitly tighter
  ones (a budget or time limit below what any discriminating test needs). The decline is justified by the stated
  constraint, never required because a case author expected it; where a test is still feasible, proposing one is right.
- **Refused finish:** the state after a finish that cited only the simulated record, corrected by citing real evidence.

## Quality bar

Provenance and replay are necessary, not sufficient (the teacher passed every check in 1 of 223 investigations).
Each target must also pass a skill check fixed in code before any example is generated
(`src/strategy_agent/pipeline/targeted.py`):
- experiment: the experiment check passes (distinct predictions, measurable threshold), cost and weeks within the
  stated limits; a decline must name the binding constraint from the state;
- revision: addresses an affected theory, changes nothing on irrelevant evidence, does not reject a theory the evidence
  supports, cites the new evidence;
- evidence: quote exact, evidence kind equals the record's annotation where it has one, `does_not_show` names the claim
  left unresolved;
- recovery: no repeat, the call advances the stage or cites real (non-simulated) evidence.
Weak targets are rejected, not accepted to meet a count. Every kept and rejected example is written with its reason.
Claude does not write, score or pick training examples: selection is the code above, and the counts and a sample are
shown to Hatem.

## Training

- Start from the final adapter (`--init-adapter`), a short continuation (about one pass over the mix).
- Mix the targeted rows with an evenly spaced sample of existing teacher rows from the same training companies, so the
  whole workflow is still practised; targeted rows get a meaningful share of supervised tokens (target about 30%,
  against 0.35% for the version 1 corrections).
- Validation rows and early stopping as before; the converted adapter must pass gate v2.

## Choosing, and claiming

- Development evaluation on the same six validation companies, same harness and judges as version 1. Version 2 is
  preferred only if the mean judge score is higher **and** it does not lose completion (finished at least as many as
  version 1) or decline tests where they are warranted.
- Version 1's final-test result stays the reported result for version 1. A generalisation claim for version 2 needs
  fresh held-out companies, frozen before it is run, evaluated once; without them version 2 is reported as a
  development result only.

## Revision, 2026-11-08, after an independent critique (stand-in reviewer; Codex unavailable). Hatem chose this reduced scope.

- **Scope:** two skills only, experiment design and recovery from refused finishes, timeboxed to three days so the
  write-up is protected; reported as a development result.
- **Budget variants dropped.** `read_brief` returns the test budget, so a recorded run cannot replay on a case with a
  different budget (replay fails at the first call), and "small budget, so decline" would teach a shortcut. Directional
  what-if variants are kept only where the replayed state already holds a theory the evidence bears on.
- **States:** prefer the student's own (version 1) states on training companies, on-policy for the weaknesses; the
  teacher continues one or two calls after each recovery, so the row shows what follows.
- **Stricter gates, judged on the new item only:** predictions differ in a number or a direction, not just in
  wording; the decision rule contains a digit and covers at least two predicted outcomes; cost per participant within a
  fixed range; a recovery finish passes `no_invented_numbers`, `simulated_not_used` and `recommendation` and cites at
  least two real sources; near-duplicate `does_not_show` texts are dropped. Hatem reviews a sample of kept rows.
- **Mix:** a stratified sample of 400-600 existing teacher rows (stage proportions kept), targeted rows 15-20% of
  supervised tokens, learning rate 2e-5 to 3e-5, about 100-150 steps, warmup 10%, early stopping on the teacher rows'
  validation loss; targeted-row loss logged separately.
- **Selection, fixed now:** both versions run 3 attempts x 15 validation cases under identical code and seeds; paired
  by case and attempt. Version 2 is preferred only if the mean-of-judges difference is at least +0.10 with a 95% lower
  bound above 0, and it finishes no more than 2 fewer of 45 runs. One configuration, one evaluation, no tuning after.
  Development numbers are reported as optimistic.
- Not used: a frontier model editing the weights directly (Anthropic's terms bar using Claude to develop another
  model; such edits are reported to clear blockages rather than add capabilities).

## Second revision, 2026-11-08 (Hatem's review), before any example was generated

- **A decline passes on any grounded reason**: testing cannot change the decision, the evidence already settles it,
  it is worth less than acting now, or it does not fit the stated limits; the reason must name a theory or source from
  the state. "Over budget" is one reason among several, never the requirement.
- **A threshold is not proof of a discriminating test.** A kept test must also come with the teacher's own reasoning
  naming the theories it separates, the intervention, and the action each result leads to.
- **No citation count.** A recovery finish must cite real sources it read and assessed, at least one assessed for the
  favoured theory, and nothing it never assessed (no padding).
- Revision is out of this iteration's scope; when it returns, a supporting result need not move a belief rating: the
  gate requires a justified update, not compulsory movement.
- Budget variants were dropped as a scope decision: they would need a new case replayed or generated from its first
  call, not an edit inside a recorded run.
- Target 80-120 kept examples; the actual targeted-token share is recorded. The learning rate and mix are experimental
  choices, not proven safe settings.
- On direct weight editing (not used): the MIT CSAIL authors report a GPT-6 Astra edit raising Qwen3.5-0.8B on
  MATH-500 from 7.9% to 48.1%; an independent replication reports 12.9% for its own attempt. Repeatability is open,
  and it says nothing about Tiny Aya's investigation behaviour.

## Third revision, 2026-11-08 (Hatem): experiment-focused

Collection gave 82 states from 122 version 1 runs on training cases: 81 at the test step and 1 refused simulated-only
finish, a failure that rarely occurs on training companies. Version 2 is therefore experiment-focused fine-tuning; the
one recovery state is kept only if its teacher response is sound, and the run is not described as a recovery
intervention. No further collection round. Quality and diversity of the accepted examples matter more than the count:
they are checked for mechanisms that genuinely differ (not merely reversed wording), for saying what each outcome would
justify, for spread across companies and kinds of experiment, and for justified declines where they occur, with no
quota. The dry-run rate on development outputs is not a yield forecast; the teacher's actual results decide.

## Fourth revision, 2026-11-08: one documented fix-and-regenerate round (Hatem)

The 17 examples accepted in the first round were reviewed by Hatem's criteria with three advisory reviews (two Claude
agents and Gemini; `reviews/v2_examples/`): none rated sound. They tested messages rather than purchase mechanisms,
measured only stated preference, jumped from a survey gap to building, used online methods in pre-internet cases, used
facts from after the decision date, and had decision rules cut off by the 240-character schema limit. Hatem chose one
documented round of correction and regeneration, recorded here before it runs:

- **Field limits:** the test-design fields get room (decision rule and method 900 characters, predictions 600, sample
  and measure 500; the teacher's reasoning fields 700/500/700), so constrained generation no longer cuts them. This
  changes the harness: version 1 must be re-run under the same limits for any comparison with version 2.
- **Teacher instructions** (`targeted.EXPERIMENT_ASK`) now ask for what the first instructions omitted: separate why
  customers buy (vary product attributes, trade-offs or price with comparable presentation, or measure a real
  commitment) rather than which message persuades; predictions that follow from each theory; a complete, proportionate
  decision rule (usually the next bounded step); declining when information is not worth its cost; and staying inside
  the case's time (methods available then, no facts from later sources).
- **Three new structural gates** (`targeted.gate_case_bounds`): the decision rule is complete; no online method in a
  case set before 1995; no reliance on a source dated after the case. Whether a test varies real attributes or
  measures a commitment is left to review, so the checker cannot be gamed into accepting it.
- **One pass:** each of the same 54 states is asked once. No state is asked again whatever the result.
- **Review before training:** the accepted answers are exported as before, reviewed by Hatem (with advisory reviews if
  he wants them), and only the examples he keeps are trained on.
