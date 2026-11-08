# Why the trained agent fails the mechanical checks on the final test

Written 2026-11-08, after the frozen final test (`docs/DECISIONS.md`, 2026-11-08). This is a post-hoc diagnosis of
the 48 trained-arm runs (`reports/judge/final/final_test_trained_adapter.json`). It changes no result and selects
nothing; anything it motivates is future work, evaluated on new data.

## Headline

28 of 48 trained runs finished, and 1 passed every check. The teacher passed every check in 1 of its 223 finished
investigations, on the training cases. The two figures come from different case distributions: they show that
all-checks success is rare in both datasets, not that the student matches the teacher or that 1 in 48 is a ceiling on
what training could reach. Several of the failures trace to behaviour the training data never showed.

## Finished runs (28): which checks fail

| check | fails | main reason |
|---|---|---|
| experiment | 23 (82%) | 17: proposed a test where the case says more information is not worth its cost; 6: the theories' predictions barely differ |
| evidence_classes | 13 (46%) | a theory's support rests only on company claims |
| evidence_kinds | 11 (39%) | fewer than 70% of assessments label the kind of evidence as the dossier annotates it |
| no_invented_numbers | 6 (21%) | the recommendation uses numbers found in no source read |
| revision | 6 (21%) | after a supporting or undermining what-if result, it revised the wrong theories |
| existing_offering | 2 (7%) | never read what the company already sells |

Each finished run fails 1 to 4 checks (most often 2 or 3).

### 1. It never declines a test, but the label needs checking case by case

- In training, **no row targets `decline_test`**. 15 of the 111 training cases have `test_warranted: false`, and in all
  15 the teacher proposed a test anyway; those investigations were accepted, because acceptance does not require the
  experiment check to pass.
- In the final test, aqp and rational (8 of 16 cases, 24 of 48 runs) have `test_warranted: false`, so every finished run
  on those companies fails `experiment`. The teacher failed `experiment` in 39% of its finished investigations.
- **Whether declining is right is not settled by the label.** As with the Masimo example earlier, a case author's
  intended answer can be unjustified, so each was checked against its brief and dossier:
  - **Aquaporin:** declining follows from the evidence. The dossier holds the company's withdrawal of its offering,
    its resolution to start insolvency proceedings and the bankruptcy order of 2 February 2026 (`aqp-insolvency-2026`,
    `aqp-strategic-review-failed`, `aqp-trustee-appointed`). The brief says its current position is unknown and to find
    out. **No run, trained or base, read any of these records**, and all 11 finished trained runs recommend investing
    in a consumer proposition. The failure here is the search that missed the decisive fact, not a missing refusal.
  - **Rational:** the brief states no constraint that rules a test out. The label rests on the case author's judgement
    (physical drain, power and space requirements, and the cost of diverting effort from professional kitchens). A
    12-week, 20,000-euro test of home-cook demand is not obviously worthless, so proposing one is defensible and this
    label is contestable.
- So the experiment failures do not justify training automatic refusal to satisfy a label. What the data lacked is
  examples that weigh proposing against declining, with either decision allowed when the evidence warrants it.

### 2. Little training on evidence that matters

- Training cases by what-if evidence: 58 none, 58 irrelevant, 4 undermining, 2 supporting. Teacher investigations on
  training companies: 103 irrelevant, 94 none, **6 undermining, 2 supporting**.
- On irrelevant evidence the student is right in all 8 finished runs (changes nothing). On aqp's supporting and
  undermining maintenance pairs, all 6 finished runs fail revision: it responds about theories the evidence does not
  bear on. On epro and rational's pairs it mostly held no affected theory (check not applicable).
- 8 unfinished runs (simo's pair 3 + 3, one epro, one rational) end on repeated `finish` calls that cite only the
  simulated record as evidence, which the harness refuses ("a simulated result cannot support a recommendation about
  real demand"), until four errors in a row stop the run.

### 3. The same checks in the teacher's data (different cases)

| check | teacher fails (223 finished) | student fails (28 finished) |
|---|---|---|
| evidence_kinds | 83% | 39% |
| no_invented_numbers | 70% | 21% |
| experiment | 39% | 82% (see 1: half the final cases are labelled no-test) |
| evidence_classes | 27% | 46% |
| existing_offering | 26% | 7% |

The teacher's rates are on the training cases and the student's on the four held-out companies, so the columns are not
a matched comparison. They show which weaknesses were already common in the training data (evidence kinds, invented
numbers), not that the student is better or worse than the teacher on them. The higher `evidence_classes` rate may
reflect the held-out dossiers' mix of company claims; not checked.

## Unfinished runs (20)

- **Turn limit (9):** rereading. In 8 of the 9, `read_source` is called 19 to 30 times for 4 to 10 distinct sources,
  so most turns go to sources already read, and the run reaches 45 calls around the challenge stage (5 of the 9 are
  rational). Rereads are accepted calls, so they never trip the error limit. This is the loop the compact state change
  (`SOURCES_NOTE`, read calls in `already_tried`) was meant to reduce; it reduced it, but not on these dossiers.
- **Repeated errors (11):** 8 are the refused finish citing only the simulated result (above); the rest are repeated
  searches (70 refusals "you already ran that search") and repeated assessments (32) in a row.

## A subsequent version: what to change, and how to know

The training data lacked behaviours the evaluation required, so more ordinary investigations would not address the
gap. In priority order:

1. **Justified propose-versus-decline examples**, where the decision follows from explicit constraints and the value
   of the information, allowing either decision when warranted; labels reviewed case by case, as above.
2. **Balanced supporting and contradicting what-if evidence**, explicitly linked to the theory it bears on (currently 8
   of 205 teacher investigations).
3. **Recovery from simulated-only citations**: separating a hypothetical update to belief from the real evidence that
   supports a recommendation.
4. **Recovery from rereading**: using the information already gathered to advance the investigation.

And on Aquaporin's evidence: searching for the company's current position before building theories about it.

These patterns should be confirmed on development cases before any new training examples are selected. Any future
performance claim needs fresh evaluation cases: these four companies have now informed this diagnosis, so they can no
longer serve as an untouched test. The frozen final-test scores stand as reported; none of this changes them.
