# Version 2 corrective adapter: training and evaluation plan (fixed 2026-11-09, before any corrective example exists)

Nothing trains until Nour has reviewed the examples on the Review page and this plan, and created the approval file
the training job checks for. Version 1, its frozen final-test result, the evaluated configuration and both frozen test
sets are untouched. Neither test set is used for training, gating or selection.

## 1. Data
- **Corrective rows:** only examples marked Keep on the Review page: the 63 verified round 3 answers and the corrective
  families (`src/aemon/pipeline/corrective.py`) after the pilot and full batch. `scripts/oneoff/v2_reviewed_rows.py`
  rebuilds each into a row only if the manifest holds its exact reply, today's replay rebuilds the context the
  teacher saw and its gate still keeps it; it stops if any approved example fails to rebuild.
- **States:** version 1's own runs on training companies (122 runs, 57 companies). No development company (hellberg,
  neumann, jotun, tanita, deere, acr), no final-test company, no test-set-2 company (tested).
- **Base rows:** version 1's training rows (`rows/final.jsonl`), so the whole workflow is still practised.

## 2. Training (`jobs/train_v2_corrective.sbatch`)
Continue version 1's adapter; corrective rows at most 20% of supervised tokens; learning rate 2.5e-5; 150 steps,
warmup 10%; validation loss on the six development companies; seed 7. The corrective rows' loss is logged separately.
These are experimental choices, recorded here so they are not tuned after seeing a result.

## 3. Controlled evaluation: model effect separate from controller effect
Four arms, the same 15 development cases × 3 attempts, the same bf16 runtime, llama.cpp build, prompt (compact),
settings (45 turns, 4 refusals, 520 tokens, temperature 0 with 0.4 on a retry), seeds and code revision:

| | as-evaluated controller | with budget awareness (D) |
|---|---|---|
| version 1 | V1 | V1 + D |
| version 2 | V2 | V2 + D |

- **Model effect (primary):** V2 − V1 under the as-evaluated controller, paired by case and attempt.
- **Controller effect:** (V1 + D) − V1 and (V2 + D) − V2. **Interaction:** whether D helps V2 differently from V1.
- The as-evaluated control (V1) and V1 + D were already run today (stage 2, jobs 749589/749590) at code 52d4f4a; they
  are re-run in the same job batch as V2 so all four arms share one code revision.

## 4. Measures, reported separately and never merged
1. **Reasoning quality:** the mean blind-judge score (Claude now, Codex when available; judge-v1 package unchanged), and
   per dimension: distinct theories, causal mechanism, assumptions and predictions.
2. **Evidence grounding:** the evidence-judgement dimension; the share of finished runs passing `no_invented_numbers`,
   `evidence_kinds` and `evidence_classes`.
3. **Experiment design:** the experiment-design dimension; the share passing `experiment` (including correct
   declines).
4. **Decision validity:** the recommendation and revision dimensions; mechanically valid completion (finished with
   every non-diagnostic guard cleared).
5. Completion, refusals by category and simulated-evidence citations as guard rails, never as the goal.

## 5. Decision rule (fixed now)
V2 is preferred over V1 only if, under the as-evaluated controller:
- the mean judge difference is at least +0.10 with a 95% case-cluster bootstrap lower bound above 0 (4,000 resamples);
- mechanically valid completion is not lower, and none of `no_invented_numbers`, `experiment`, `evidence_kinds` falls;
- it finishes no more than 2 fewer of 45 runs and adds no simulated-evidence citation.
One configuration, one evaluation, no tuning afterwards; development numbers are reported as optimistic. A claim beyond
development needs a frozen test: test set 2 allows a version 2 arm only under its own freeze rule (adopted on
development by 11 November, the same settings, before any per-case look); otherwise version 2 is a development result.

## 6. Amendment, fixed 2026-11-10 11:30, before any version 2 adapter exists (Nour's sprint brief)
**Known false positives of the experiment check.** The environment's `experiment` check passes a test when its
predictions differ and its decision rule has a threshold. On stage 2's as-evaluated development arm (code 52d4f4a), 9
tests pass it, and 8 of them fail the teacher-side design screens (`targeted.gate_mechanism`): 4 vary only the wording,
3 lead straight to building a product line, 1 prices in euros in a 1993 case (the budget arm is the same). Those screens
are keyword-based and have errors of their own. Both are therefore reported:
- `experiment` (v1, unchanged), so earlier numbers stay reproducible;
- `experiment_v2` (new, development only): `experiment` passes and the passing test clears `gate_mechanism`.

Both measures are applied identically to both arms.
`evidence_kinds_v2` (the annotation overlay, docs/EVIDENCE_KIND_GUIDE.md) is reported next to `evidence_kinds` in the
same way, only if the overlay has been reviewed before the evaluation runs.

**Adoption rule** (V2 against V1 under the as-evaluated controller, the 45 paired development runs of section 3; this
replaces section 5 where they differ):
1. Validated completion (finished with every non-diagnostic guard cleared): V2 at least V1 + 3 of 45.
2. Blind quality (Claude, judge-v1 unchanged, adapter hidden): mean V2 − V1 at least +0.10, with the company-cluster
   bootstrap 95% lower bound above 0.
3. Numerical grounding: no more finished runs failing `no_invented_numbers` than V1, and a lower failing share among
   finished runs.
4. Experiment design: `experiment_v2` passes not fewer than V1, and the experiment-design judge dimension not lower.
5. No serious regression: no judge dimension falls by more than 0.15; at most 2 fewer finishes; no more runs stopped
   by four refusals in a row; no accepted simulated-evidence citation.

**Decision:** all five pass → adopt V2 (a development result; it becomes Aemon default only with that
label). 1 or 2 pass with no failure of 5 → V2 stays experimental. Otherwise → keep V1. Raw completion alone never
decides it. The targets of 8/45 valid and +0.15 quality are aspirations, not thresholds. No frozen test set is used for
training, tuning or this decision. A V2 claim beyond development needs untouched companies.

## 7. Amendment, fixed 2026-11-10 11:40, before any example is approved: how the corrective rows are mixed
Section 2's `--extra-rows` with 150 steps would barely train on the corrections. The trainer caps extra rows and never
repeats them, and 150 steps × 4 rows = 600 presentations drawn from about 3,900 base rows plus about 100 corrective
rows. That is about 4% of target tokens, and each corrective row would be seen about 0.15 times. Instead,
`scripts/oneoff/v2_training_set.py` builds one continuation set:
- every approved corrective row twice;
- revise capped at 10% of the corrective rows (lowest priority; the student already passes its gate 22/22);
- a seeded sample (seed 7) of version 1's own training rows, so the corrective rows are 20% of supervised target
  characters;
- all base rows of the six development companies, used for validation only.

The job trains one epoch over this set from version 1's adapter. Learning rate 2.5e-5, warmup 10% and seed 7 are
unchanged. The trainer's validation split by company is unchanged, and so is the masking: contexts and target_index are
copied as they are.

The builder refuses (exit 2) any non-training case and drops duplicates. Its manifest records:
- input and output hashes;
- per-family and per-call counts;
- the realised share.

Dry run on the 31 unreviewed pilot rows (mechanics only, nothing approved): 24 corrective rows after the revise cap,
333 replayed base rows, 411 validation rows, a share of 0.199, and 381 presentations (about 96 optimizer steps).

The share stays at 20%, not 15%. With about 100 rows, 20% already means repeating base rows rarely and each
correction twice. A lower share would push the corrective signal toward the 150-step problem.

**Representation limits to note:**
- `decline_test` is the right call in only 3 of 53 experiment states (2 companies). Declines will be rare in the data,
  and that is a property of the training cases.
- Classification rows are matched to an annotation that is about 75–83% reliable (reports/annotation_audit).

## 8. Amendment, fixed 2026-11-10 11:45, before any V2 adapter: screening before the full evaluation (Nour)
**Screen (exploratory).** The 15 development cases of section 3, attempt 1 only (temperature 0, the same seeds), for V1
and V2. Both arms are run fresh in one job batch on the same code revision, bf16 runtime, prompt, settings and
as-evaluated controller. That makes 30 runs. The runs are judged blind by Claude (judge-v1 unchanged, adapter hidden,
about $1–2).

**Go to the full evaluation** (section 3's 45 paired runs; the screen's runs are attempt 1 of those and are reused,
not rerun) only if both conditions hold:
1. At least one of these improves for V2 against V1 on the 15 pairs:
   - validated completion +1 or more;
   - fewer finished runs failing `no_invented_numbers` or `numbers_cited`;
   - `experiment_v2` passes +1 or more;
   - at least 2 fewer runs stopped by four refusals in a row.
2. No serious regression:
   - mean blind quality V2 − V1 not below −0.10;
   - no more than 2 fewer finishes;
   - no accepted simulated-evidence citation.

Otherwise stop. V1 stays, and the screen is reported as the result.

**Reporting.** With 15 pairs and 6 companies the screen can show direction only. It is reported in full, every number,
labelled exploratory. The adoption decision is made only by section 6's rule on the full 45. Because the go decision
used attempt 1, the report says so.

## 9. Substantive review of the accepted pool, and the data threshold (2026-11-10 11:55, before any V2)
Two independent advisory reviews (the human review still decides) read every accepted example against the
substantive criteria. Round 3 (63 examples) gave 1 keep, 6 borderline and 56 drop. Round 4 (27) gave 2 keep, 4
borderline and 21 drop. Spot checks confirm the main reasons:
- 17 of 63 round 3 calls rely on a source dated after the case's year;
- 36 of 60 round 3 weighings label the source independent_study, mostly encyclopedia, company-history or news text;
- two round 4 revise answers have empty reasoning fields.

The teacher (Command A+) makes the same errors as the student on evidence kind and dates, so gates alone cannot turn its
answers into good supervision. The corrective gate now also refuses a call that relies on a source dated after the
case's year, and a finish whose next action runs a weak earlier test.

**Threshold, fixed now:** a V2 candidate is proposed for training only if, after the experiment pilot and the batch,
the reviewed pool has at least 30 examples rated keep, in at least 3 families, with experiment design among them.
Fewer could not plausibly move the 45-run measures. In that case version 1 stays, and the corrective work is reported
as a finding about the teacher's limits.

## 10. Experiment pilot 4 result and the V2 stop decision (2026-11-10 12:50)
Pilot 4 (job 751667, code fc297ac, structured design with one shortening turn; 8 states, of which 1 does not warrant a
test) kept 1 of 8. On substance it is 0 of 8:
- 6 answers decline, 5 of them in cases that warrant a test;
- several declines contradict their own reasoning: why_next describes a test, and one decline reason says a test
  could settle the question;
- the one kept design varies only the message on two landing pages at the same price.

The structured format fixed the truncation: 1 answer was still too long after one shortening, against 4 of 7 cut in
pilot 3. But it shifted the teacher toward declining.

**Stop rule applied.** The experiment family has now failed two successive targeted attempts (pilot 3's instructions
and pilot 4's structure), so it is not expanded. The threshold in section 9 requires experiment design among at least
30 strong examples, and the pool has none rated strong. The numbers/recovery batch has no experiment states, so it
cannot change this. **The V2 training attempt stops; version 1 stays.** The batch is still reviewed and reported. Work
moves to the evidence-verification layer (docs/VERIFY_EVAL_PLAN.md).
