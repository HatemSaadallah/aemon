# Evidence-grounded reasoning without retraining: feasibility and one proposal (2026-11-10 17:40, not implemented)

## What the model actually sees
- **Search** (`env/dossier.py`): plain keyword ranking by shared rare words, top 3 per query. The result shows each
  hit's id, title and origin class (company claim or verified observation).
- **A read source**, in the state at every later step (`runner.state_of`): id, origin class, title and excerpt. The
  date is shown only under the opt-in `source_dates`.
- **Never shown**, although every record carries them in all splits: the curated `kind`, `does_not_establish` and
  `access_limitation`. `bears_on` is held by 94 development records and 0 final-test records.
- **Existing related code:** `mask_rereads` (recovery study B) limits rereading. Nothing selects what a search
  returns.

## Observed failures on V1's 45 development runs (as-evaluated control, code 9f107b1)
| | |
|---|---|
| search hits that are sources the run had already found | 571 of 951 (60%) |
| accepted searches that return nothing new | 106 of 317 (33%) |
| searches refused as repeats of an earlier query | 179, about 4 per run, the largest refusal category; 17 of 45 runs end on refusals |
| records surfaced per run, of about 51 in the dossier | 8.8 (read: 6.9) |
| **runs that ever weigh a source as contradicting a theory** | **2 of 45** |
| runs that never read what the company already sells | 13: 8 never surfaced it, 5 surfaced but did not read |

## The three options
| | 1. Show source metadata (dates, kind, limits) | 2. More relevant retrieval | 3. Source-to-claim grounding before the recommendation |
|---|---|---|---|
| failure addressed | wrong kinds; overstated support (in a blind sample, 27 of 60 quotes support their theory partly or not at all) | redundant results; one-sided evidence (contradictions weighed in 2 of 45 runs); missed records | recommendations that do not follow the evidence (10 of 24 finishes) |
| smallest change | add `kind`, `does_not_establish` and the date to each read source in the state | **a search returns the best-ranked records the run has not already been shown** (the same ranking, minus duplicates) | a new required field in `state_position` or `finish` mapping each claim to a source or "assumption" |
| what it changes | the state (prompt content) | **tool output only**: which ids a search returns | the tool schema and the prompt |
| refusal and completion risk | low for refusals; the state is longer (context-limit stops are 0 today) and its format is new to the model | **low**: no new refusal, guard, eligibility or flow; it reads lower-ranked, possibly less relevant sources | high: a format V1 never saw; verification and V1.1 showed V1 does not use such structure, or collides with guards |
| validity problem | **serious**: `kind` and `does_not_establish` are the curated answers. The model could copy them into `evidence_kind` and `does_not_show`, raising the checks and the judges' evidence score without better reasoning. The labels also do not exist for live web sources. Dates only matter in historical cases, not in the frozen tests or deployment. | none known: the corpus, ranking and guards are the same, and the model still chooses what to read and how to weigh it | the improvement would be measured on the structure it imposes |
| effort | about 30 minutes plus a run | **about 30 minutes code, 50 minutes for a 45-run evaluation, about $3–4 of judging** | hours, and retraining-dependent |

**Option 3 is a post-hoc structure in all but name**, and the previous two runtime experiments are direct evidence
against it. **Option 1 would improve presentation-derived scores, not reasoning**, by leaking the curated annotations.
**Option 2 is the only change that alters the evidence the model works from without telling it what to conclude.**

## Proposal (for approval): novelty-first search, experimental configuration "V1-r"
`search_evidence` and `challenge_theory` keep the same keyword ranking and budget. Each returns up to 3 of the
highest-ranked records the run has **not yet been shown**. When fewer than 3 remain, it fills with the next-best
already-shown records, as today. Nothing else changes: the repeat-query refusal, the prompt, the state, the guards and
the turn limits stay the same. It runs as a separate entry point that replaces the dossier search in its own process
(as `verify` and `grounded` did), and is refused on any split but development.

**Why it could improve evidence-grounded reasoning:**
- a challenge search would now bring new sources, which is where contradicting evidence must come from, instead of
  re-showing the favourite's support;
- each accepted search yields new material, so the same search budget covers more of the dossier, including the
  company's existing offering.

**Honest expectation:** a modest effect at best. V1 still decides what to read and how to weigh it, and it may keep
repeating queries.

## Predeclared evaluation (fixed before any run)
- **Arms:** the existing V1 control (job 751713; identical, run for run, to stage 2) and V1-r, on the 15 development
  cases × 3 attempts. Same adapter 41794b57, bf16 runtime, prompt, settings and seeds. No frozen test set is used.
- **Primary, evidence quality** (not satisfied by construction):
  1. blind quality (Claude, judge-v1 unchanged, arm hidden): the mean and the evidence-judgement, seeking-challenge
     and recommendation dimensions, with paired differences and a company-cluster bootstrap 95% interval;
  2. runs with at least one weighing that contradicts a theory;
  3. `disconfirmation` (original check);
  4. `existing_offering` (original check);
  5. validated completion.
- **Guard rails:** finishes, runs stopped by refusals, repeat-query refusals, `numbers_cited` and
  `follows_evidence` failures, and calls per run.
- **Descriptive:** distinct sources surfaced and read per run. These are by construction higher and never counted as an
  improvement.

**V1-r is adopted as the submitted runtime only if all of these hold:**
1. Blind mean V1-r − V1 ≥ +0.05, with the interval's lower bound ≥ −0.02.
2. Evidence-judgement and recommendation dimensions are not lower.
3. Runs with a contradicting weighing increase by at least 3.
4. Validated completion is not lower.
5. At most 2 fewer finishes, and at most 2 more runs stopped by refusals.

Otherwise V1 stays frozen as evaluated, and V1-r is reported as tried. One configuration, one run, no tuning. Even if it
passes, the claim is a development result: the frozen test numbers belong to V1 as evaluated.

**Cost and time:** about 2 hours end to end and about $3–4 of judging; $16.44 is left under the cap.

## Addendum, 2026-11-10 17:48, after approval and before any V1-r run (Nour's points of attention)
These are descriptive measures added to the report. The adoption criteria above are unchanged.
- **Relevance against diversity:** for each accepted search, the keyword score of each returned record as a share of
  that query's top score. Reported as the mean and the share of hits below half the top score, in both arms.
- **Whether it reads and weighs more relevant evidence:** sources read and weighed per run. The number of weighed
  sources whose `bears_on` or `premise` annotation marks them as decision-relevant is reported where the annotation
  exists. These annotations are never shown to the agent.

## Result (2026-11-10 18:35; job 752546, code ec0d865, 45 paired runs; `experiments/verify/report_v1r.json`)
| | V1 | V1-r |
|---|---|---|
| finished | 24 | 22 |
| **validated completion** | **3** | **0** |
| stopped by repeated refusals | 17 | 16 |
| repeat-query refusals | 179 | 161 |
| **runs with a contradicting weighing** | **2** | **2** |
| `disconfirmation` / `existing_offering` passed | 24/24, 18/24 | 22/22, 15/22 |
| `numbers_cited` failures | 9 | 10 |
| per run: surfaced / read / weighed / decision-relevant weighed | 8.8 / 6.9 / 3.0 / 1.3 | 17.4 / 7.1 / 2.2 / 1.0 |
| hits: mean share of the query's top score; share below half | 0.81; 13% | 0.65; 28% |

V1-r doubled the sources surfaced, which is true by construction. The agent still read about 7 sources and weighed
fewer: 2.2 against 3.0 per run, and 1.0 against 1.3 decision-relevant. It weighed a contradicting source in the same 2
runs. Relevance fell: 28% of hits scored below half the query's top score, against 13%. So the extra diversity came
at the cost of relevance, and the agent did not use it.

`follows_evidence` failures fell from 13 to 0. That measure is a guard rail, not a criterion, and the cause is
unexplored. It is not counted as an improvement: the criteria that bear on evidence quality did not move or fell.

**Decision under the fixed criteria.** Criterion 3 (at least 3 more runs with a contradicting weighing: 2 against 2)
and criterion 4 (validated completion not lower: 0 against 3) fail. **V1-r is rejected and V1 stays the submission
configuration.** Blind judging was not run, because it could not change the decision. No follow-up variant is run.
