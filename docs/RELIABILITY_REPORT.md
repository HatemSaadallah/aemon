# Reliability audit, verification layer and the V2 decision (2026-11-10)

**Central question:** can V1's recommendations be made substantially more trustworthy, by verification or by corrective
training? **Answer: not with what we have.** Neither approach produced a measurable improvement. V1, as evaluated, is
the system to submit, with the disclosures below.

## 1. Did the teacher's weaknesses affect V1's training data and evaluation?
**Training data: yes.** The audit covered the 158 teacher investigations whose rows trained V1
(`scripts/oneoff/audit_v1_evidence.py`, `reports/v1_audit/mechanical.json`), plus a blind content review of 60 weighings
(`reports/v1_audit/assessment_sample_review.json`).

| | teacher training data | V1, development (45 runs) | V1, final test (48) | V1, test set 2 (72) |
|---|---|---|---|---|
| finishes citing a source dated after the case's year | 74 / 158 | 9 / 24 | n/a (present-day cases) | n/a |
| weighings on such sources | 122 / 491 | 36 / 148 | n/a | n/a |
| weighings whose kind matches the annotation | 188 / 491 (38%) | 84 / 148 (57%) | 78 / 134 (58%) | 66 / 143 (46%) |
| independent_study used where the annotation says otherwise | 190 / 225 | 60 / 73 | 32 / 47 | 69 / 69 |
| finishes failing `no_invented_numbers` | 117 / 158 (74%) | 11 / 24 | 6 / 28 | 10 / 32 |

Content review, 30 weighings on later-dated sources and 30 others:
- **Hindsight:** 14 of 30 later-dated quotes reveal information not knowable at the case date. That is about 12% of
  all teacher weighings.
- **Support:** 33 of 60 quotes support their theory as stated; 20 do so only partly and 7 do not.
- **Evidence kind:** 20 of 60 kinds are correct and 13 defensible.

**Evaluation: the frozen results stand as computed.** All 40 frozen-test cases are set in the present, so no source
can postdate them. Their scores, judges and rules are unchanged. Invented numbers and kind errors in the teacher data
were already disclosed (`docs/FINAL_TEST_DIAGNOSIS.md`: 70% and 83%).

Not disclosed before, and now corrected:
- hindsight-bearing sources in historical training cases;
- the dataset card's claim that the agent only sees records available at the case date.

## 2. Reliability failures confirmed
1. **Invented numbers:** 21–46% of V1's finished recommendations, depending on the set.
2. **Evidence kind:** "independent_study" is applied to encyclopedia, news and company-history text.
3. **Experiment design:** the original check passes 9 of 27 development tests, but only 1 clears the stricter design
   screens.
4. **Support:** 13 of 24 development finishes cite no source weighed as supporting the favoured theory.
5. **Refusal loops:** 17 of 45 development runs stop after four refusals in a row.
6. **Hindsight:** only in historical training data, not in the frozen tests.

Two of our own instruments have limits, and both are now disclosed:
- the experiment check is lenient;
- the evidence-kind annotation is about 80% reliable on a blind relabelling (`reports/annotation_audit/`).

## 3. Did any verification intervention improve outcomes?
**No** (`docs/VERIFY_EVAL_PLAN.md`, fixed before the run). Each arm had 45 paired development runs; the control arm
reproduced stage 2 exactly.
- **Unsupported recommendations:** 20 for V1, 19 with verification.
- **Validated completion:** 3 and 3.
- **Abstentions:** none.

After 26 of the 27 reviews, V1 immediately rewrote its finish without new evidence work, and most findings survived:
late sources 29 of 31, missing support 13 of 16. The small model does not act on feedback it was never trained on.

The step-budget controller studied earlier also left quality unchanged (+0.006, `docs/RECOVERY_REPORT.md`). The
verification findings are shown to readers in aemon as "check before relying". That is disclosure, not an
improvement.

## 4. Does the corrective dataset qualify for V2?
**No** (`docs/V2_CORRECTIVE_PLAN.md` §§9–10). The registered threshold was at least 30 strong examples, in at least 3
families, including experiment design.
- **Rounds 3 and 4:** of 90 accepted examples, the advisory review rated 3 keep and 10 borderline. Spot checks
  confirmed its reasons.
- **Experiment design:** this family failed two successive targeted attempts. Pilot 4 was 0 of 8 sound: it mostly
  declined tests the cases warrant.
- **The teacher's own errors:** the teacher (Command A+) makes the same kind, date and support errors as the student.
  Gates filter its answers; they cannot make them good.

The numbers/recovery batch was cancelled once it could no longer change the decision, so it is not reported as a
result. The V2 training attempt is stopped, as the brief requires.

## 5. What to submit
**V1** (adapter `41794b57`; GGUF as published) on the evaluated runtime:
- bf16 Tiny Aya Global under llama.cpp;
- the compact prompt;
- the as-evaluated controller (45 turns, 4 refusals, 520 tokens, temperature 0 with 0.4 on a retry).

The headline results are the frozen final test and test set 2. Test set 2 is Claude-only until the Codex judging is
done. The recovery guard and the verification layer stay off by default; the guard is opt-in and labelled in the
aemon.

## 6. Limitations that must be disclosed
1. **Training data:** V1's training data contains hindsight sources (about 12% of weighings), invented numbers (74% of
   teacher finishes) and frequent evidence-kind errors. V1 reproduces the latter two.
2. **Validated completion is low:** 1 of 48 on the final test, 4 of 72 on test set 2. The quality gains are measured
   by blind LLM judges, not by mechanical validity.
3. **Our own checks:** the experiment check is lenient, and the evidence-kind labels are about 80% reliable.
4. **Two failed corrections:** neither a controller (recovery, verification) nor corrective distillation from this
   teacher fixed the remaining failures. A better teacher or human-written corrections would be needed.
5. **Test set 2's headline is pending** until the second judge has scored it.
