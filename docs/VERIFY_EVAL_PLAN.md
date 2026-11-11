# Evidence verification for version 1: evaluation plan (fixed 2026-11-10 12:10, before any run)

**Question:** does the verification layer (`aemon.agent.experimental.verify`, verify-v1) make V1's recommendations more
trustworthy without simply blocking them?

**Arms.** Both arms use the same code revision (9f107b1), bf16 runtime, llama.cpp build, adapter (41794b57), prompt
(compact) and settings (45 turns, 4 refusals, 520 tokens, temperature 0 with 0.4 on a retry). Both are run fresh in
parallel jobs, on the same 15 development cases × 3 attempts as stage 2.
- **V1:** the evaluated runner, unchanged.
- **V1 + verify:** the same, with one review of the first proposed finish.

No frozen test set is used.

**Measures**, reported separately, per arm and as paired differences:
1. **Supported claims:** `numbers_cited`, `no_invented_numbers` (original), and `follows_evidence`, all on finished
   runs. Finishes citing a source dated after the case's year are also counted.
2. **Evidence classification:** `evidence_kinds` (original) and `evidence_kinds_v2` (development overlay).
3. **Experiment design:** `experiment` (original) and `experiment_v2` (development; the original passes 8 of 9 tests
   that fail the design screens).
4. **Validated completion:** finished with every non-diagnostic guard cleared.
5. **Abstention:** finishes whose recommendation begins "Insufficient evidence:". Each one is listed with the
   verification findings that preceded it, so whether it was appropriate can be read case by case.
6. **Unsupported recommendations:** finished runs failing `follows_evidence` or `numbers_cited`, plus finishes citing
   a late source.
7. **Runtime and cost:** calls per run, verification turns, wall time per run.
8. **Blind-judged quality:** Claude, judge-v1 unchanged, arm hidden. Recommendation dimension and the mean.

**Known false positives, read before the results.** The `experiment` check is lenient
(docs/V2_CORRECTIVE_PLAN.md §6). `no_invented_numbers` counts any digit string not found in a read source or the
brief, so a year or a rounded restatement can count as invented. The original checks are reported unchanged, and the
development measures sit beside them, never in their place.

**Success rule** (all four required; a finding, not an adoption of a new default):
1. Fewer unsupported recommendations (measure 6) with V1 + verify than with V1.
2. Finishes not lower by more than 2 of 45, counting an "Insufficient evidence" finish as a finish. Abstentions are
   reported separately, so blocking cannot pass for reliability.
3. Blind quality not lower: mean difference ≥ −0.05, and the recommendation dimension not lower.
4. Validated completion not lower.

If all four hold, verification is offered in Aemon as a labelled option, and the result is reported as a
development finding. Otherwise it is reported as tried, with its numbers. One configuration, one run, no tuning after
the results.

## Result (2026-11-10 15:20; jobs 751713 and 751714, code 9f107b1, 45 paired runs per arm)
The control arm reproduces stage 2 exactly (24 finished, 3 validated), a check that the runtime is stable.

| | V1 | V1 + verify |
|---|---|---|
| finished (abstentions) | 24 (0) | 23 (0) |
| validated completion | 3 | 3 |
| **unsupported recommendations** (measure 6) | 20 | 19 |
| finishes citing a source dated after the case | 9 | 8 |
| `no_invented_numbers` failures / finished | 11/24 | 9/23 |
| `numbers_cited` failures | 9/24 | 7/23 |
| `follows_evidence` failures | 13/24 | 13/23 |
| `evidence_kinds`, `experiment`, `experiment_v2` failures | 26/33, 18/27, 26/27 | 26/33, 18/27, 26/27 |
| stopped by repeated refusals | 17 | 17 |
| mean calls | 32.0 | 31.9 (+1 review turn in 27 runs) |

**What the model did with the review.** Of 27 reviews, 26 were followed at once by another finish with some fields
changed, and 1 run ended. Not one review was followed by weighing a source, reading the existing offering, or an
"Insufficient evidence" finish. Most findings survived the revision:
- late sources: 29 of 31;
- missing support: 13 of 16;
- uncited numbers: 7 of 10;
- unread offering: 5 of 6;
- company-only support: 4 of 4.

One run finished in V1 and not under verify (deere-new-evidence-irrelevant #2).

**Against the success rule:**
1. Fewer unsupported recommendations: 19 against 20, one run.
2. Finishes −1: within the allowed margin.
3. Blind quality: not judged. With 42 of 45 runs the same in length and outcome and the mechanical effect at one run,
   the about $5 of judging could not change the conclusion, so the remaining budget is kept for the Codex and
   submission judging.
4. Validated completion: equal.

**Conclusion:** the layer does not make V1 meaningfully more reliable. V1 rewrites the text but does not change the
evidence behind it. Acting on verification feedback is a behaviour the model was never trained on, and the corrective
teacher data that could have taught it did not pass review (docs/V2_CORRECTIVE_PLAN.md §§9–10). The layer is not
adopted and not offered as a model improvement. Its findings remain useful to a reader: Aemon shows them on
the answer as "check before relying", which discloses the problem and changes nothing in the run.
