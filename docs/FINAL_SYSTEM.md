# The final system: how it was built, and what was not adopted

The final system builds on version 1. Everything here came after version 1's two frozen results were known, and some
of it was designed from the failures in those runs, so the test cases were no longer unseen: version 1 on the
[first](../README.md#final-test-4-held-out-companies-16-cases-3-attempts-96-runs-run-once) and
[second](../README.md#second-frozen-test-12-new-companies-24-cases-3-attempts-144-runs-run-once-docstest2_freezejson)
frozen tests is the run-once result. Each change below had its rule written in [DECISIONS.md](DECISIONS.md) before it
ran, was measured on development and on the same two test sets, and each comparison was judged blind by two LLM judges
(Claude Code and Codex on `gpt-6-sol`) unless stated. Against the base model, the final system scores +1.02 [0.92,
1.10] on the first test's cases and +1.11 [1.01, 1.20] on the second's (`scripts/release/final_system_vs_base.py`). The [README](../README.md#the-final-system) has the summary.

**Contents:** [Corrective distillation](#corrective-distillation-and-two-runtime-attempts-10-november) ·
[Version 3](#version-3-a-second-teacher) ·
[Switching adapters](#switching-adapters-during-a-run-development-then-test-set-2) ·
[Status check](#a-company-status-check-the-aquaporin-failure) ·
[Combined system](#the-combined-system-on-test-set-2-a-system-built-after-the-frozen-results) ·
[Loop guards](#loop-guards-on-development-test-set-2-and-the-final-test) ·
[Evidence first](#evidence-first-how-a-source-is-weighed) ·
[Recovery controller](#a-recovery-controller-does-not-fix-the-remaining-failures) ·
[What else we tested](#what-else-we-tested)

## Corrective distillation and two runtime attempts (10 November)
Full report: [RELIABILITY_REPORT.md](RELIABILITY_REPORT.md).

- **Corrective distillation.** We built teacher examples at states where version 1 itself went wrong: invented numbers,
  experiment design, evidence kind, and recovery after refusals.
  - Each was checked for provenance, exact replay and split, then reviewed against substantive criteria.
  - Of 90 examples the mechanical checks accepted, an advisory review rated 3 strong, and spot checks confirmed its
    reasons.
  - The teacher (Command A+) makes the same errors it was meant to correct: it calls encyclopedia and news text
    "independent study", relies on sources published after the case date, and designs tests that vary only the message.
  - A structured format fixed its truncated test designs, but then it declined tests the cases warrant.
  - We had fixed a threshold of 30 strong examples, including experiment design, before training. Command A+ did not
    meet it. A hosted teacher (DeepSeek V4-Pro, with V4.1-Flash) then did (105 corrective rows), so version 2 was
    trained on top of version 1; on its development screen it finished 0 of 15 runs against version 1's 7, and it was
    stopped there.
- **An evidence-verification layer, without retraining.** Before the final recommendation, the agent was shown what its
  evidence did not support, and could revise or answer "insufficient evidence". On 45 paired development runs this gave
  19 unsupported recommendations against 20, the same validated completion, and no abstention. The 3B model rewrote the
  text but not the evidence behind it. The app shows these findings to the reader instead.
- **Two more runtime attempts, both rejected under rules fixed in advance.**
  - Constraining the favoured theory to those the agent's own weighings support collided with an existing guard and
    cut finishes from 24 to 14.
  - Novelty-first search doubled the sources the agent was shown, but it weighed fewer of them, found contradicting
    evidence in the same 2 of 45 runs, and finished with every check cleared in 0 runs against 3.

## Version 3: a second teacher
After both tests we trained another adapter, version 3, by continuing version 1 on everything from both teachers: version 1's rows
plus 3,611 rows from 144 replay-exact DeepSeek V4-Pro investigations on 69 companies (10 more, on the validation
companies, give 262 validation rows). On its development screen it
did not pass the adoption rule fixed in advance (blind quality 0.83 against version 1's 1.05), so it was not adopted on
its own; it became the reasoner in dig then reason (below). We ran it on both test sets, with base, version 1 and version 3 rejudged together
blind by two judges qualified for this purpose (Claude Code and Codex on `gpt-6-sol`).

| Mean of the two judges | Base | Version 1 | Version 3 | Version 3 minus version 1 |
|---|---|---|---|---|
| Test set 2 (72 runs per arm) | 0.56 | 1.06 | 1.48 | +0.42 [0.24, 0.60] |
| Final test (48 runs per arm) | 0.62 | 1.46 | 1.33 | −0.13 [−0.31, 0.04] |

- (These final-test numbers come from the re-judging with base, version 1 and version 3; the combined-system section
  below re-judged five arms together, which moves each arm by up to 0.02.)
- The two test sets disagree: version 3 is clearly higher on test set 2 and not distinguishable from version 1 on the
  final test, where most of the gap is one company (Aquaporin, −0.41).
- Version 3 makes fewer calls and, on test set 2, far fewer refused ones (305 against 584; 230 against 242 on the
  final test), but it learned the second teacher's direct style without
  its recovery: when a call is refused it repeats it. Its theories are also thinner.
- Because these runs were decided after version 1's results were known, they select nothing.

## Switching adapters during a run (development, then test set 2)
The two adapters fail differently, so one llama.cpp server holds both and the runner picks one per turn from the stage
and the count of refusals in a row; it never sees a judge or the case. On the 15 development cases (3 attempts, 45 runs
per arm, Claude Code judge):

| Arm | Blind quality | Finished of 45 |
|---|---|---|
| Version 1 | 1.06 | 24 |
| Version 3 | 0.86 | 19 |
| Version 3, a stuck turn goes to version 1 | 1.17 | 33 |
| Version 1, a stuck turn goes to version 3 | 1.20 | 26 |
| **Dig then reason**: version 1 gathers the evidence, version 3 reasons | **1.24** | 33 |

Dig then reason was higher than both single adapters on development (+0.17 [0.02, 0.35] over version 1, +0.38
[0.13, 0.62] over version 3), so it was the rule taken to a test.

## A company status check (the Aquaporin failure)
On the first frozen test no run of either arm read Aquaporin's insolvency records (0 of 24 Aquaporin runs; the base
runs were shown the announcement's title in search results), and every finished trained run recommended investing. We added one step after framing: a fixed search for the company's own current position
(records that name the company, newest first), and a required `company_position` text in the final answer. With it
every run reads those records. On Aquaporin, version 3 with the check finished 3 of 12 runs and all three said "do not
commit"; without it, it finished 9 of 12 and all nine said "invest", although 4 of those 12 runs had read the insolvency
announcement. The check costs finished runs: on development,
version 1 finished 14 of 45 with it against 24 without. These Aquaporin numbers are a diagnostic of the fix, not a
test, because that company informed the design.

## The combined system on test set 2 (a system built after the frozen results)
The system: version 1 for the brief, frame, status and evidence stages, version 3 for every later stage, with the
status check on. The plan was fixed before any run: test set 2, five arms judged together blind by both judges (342
packets from 360 runs, none missing), primary comparison the combined system minus version 1. Nothing in the system
was selected on test set 2, but that set had been run before.

| Arm (72 runs each) | Mean of judges | Claude Code | gpt-6-sol | Finished |
|---|---|---|---|---|
| Base, staged prompt | 0.56 | 0.48 | 0.63 | 2 |
| Version 1 | 1.07 | 0.87 | 1.26 | 32 |
| Combined system (dig then reason, with the status check) | 1.28 | 1.07 | 1.49 | 37 |
| Dig then reason, without the status check | 1.43 | 1.16 | 1.70 | 43 |
| Version 3 | 1.48 | 1.21 | 1.74 | 57 |

- **Primary comparison, combined minus version 1: +0.22 [−0.00, 0.46].** The interval includes zero, so the combined
  system is not shown to be better than version 1. It is uneven: higher at 7 of 12 companies (Hoshizaki +1.19, Franke
  Coffee +0.94, Belimo +0.82) and lower at 5.
- Dig then reason without the check is clearly higher than version 1 (+0.36 [0.22, 0.51]) and level with version 3
  alone (1.43 against 1.48), so on this set the switching adds nothing over version 3.
- The status check costs about 0.15 (combined minus dig −0.15 [−0.35, 0.06]) and six finished runs.
- The two judges rank the runs alike (Spearman 0.90 over 360 runs).
- **On the final test the gain disappears** (secondary and labelled, since Aquaporin informed the status check; 48
  runs per arm, 231 packets, both judges, none missing; Spearman 0.82 between them):

  | Arm (48 runs each) | Mean of judges | Claude Code | gpt-6-sol |
  |---|---|---|---|
  | Base, staged prompt | 0.61 | 0.54 | 0.67 |
  | Version 1 | 1.45 | 1.18 | 1.72 |
  | Dig then reason | 1.44 | 1.13 | 1.76 |
  | Version 3 | 1.35 | 1.06 | 1.64 |
  | Combined system | 1.32 | 1.03 | 1.61 |

  No later arm is distinguishable from version 1 there: dig then reason −0.01 [−0.20, 0.18], version 3 −0.10
  [−0.27, 0.05], combined −0.13 [−0.32, 0.05]. Every trained arm stays far above the base (version 1 +0.85
  [0.68, 1.00] in this re-judging, dig then reason +0.84 [0.69, 0.96], combined +0.71 [0.53, 0.91]). Aquaporin is the
  largest part of the gaps for version 3 (−0.40) and combined (−0.51).
- **Reading across both sets:** version 1 is the frozen, evaluated model, and no later system beats it on the final
  test. Dig then reason is the most consistent of the later systems: clearly higher than version 1 on test set 2 and
  on development, level with it on the final test (both judges), and not higher than version 3 alone on test set 2 (1.43 against
  1.48). The status check fixes what it was built for and costs finished runs.

## Loop guards on development, test set 2 and the final test
The last thing we built, after every frozen result. In the final-test runs of dig then reason, 233 of 274 refused
calls were the model repeating itself: the same search again (130) or weighing a source it had already weighed for that
theory (103). Four refusals in a row end a run, so these loops were most of the unfinished runs. Three guards act only
on decoding, with no retraining and no guard of the environment changed (`agent/recovery.py`, `agent/loop.py`):
- **no repeats**: the tool schema offers, per theory, only the sources not yet weighed for it;
- **quote menu**: a quote is chosen from the source's own sentences, so it cannot be misquoted;
- **redraw repeats**: a call refused as an exact repeat changed nothing, so the same state is sampled again (at most
  3 times) before the refusal counts. Every refused draw stays in the record and in the refusal count.

With the repeats gone, 12 runs fell into a new loop (weighing every source "neutral" instead of proposing a test), so a
third arm added the step-budget guard from our earlier recovery study. Development screen, dig then reason on the
laptop runtime, 15 cases × 3 attempts per arm, same seeds, judged blind by both judges; each rule registered in
[docs/DECISIONS.md](DECISIONS.md) before its result:

| Arm (45 runs each) | Finished | Refused calls per run | Finished with no invented number | Mean of judges | Claude Code | gpt-6-sol |
|---|---|---|---|---|---|---|
| Dig then reason, as evaluated | 28 | 5.2 | 13 | 1.42 | 1.13 | 1.72 |
| + loop guards | 33 | 3.1 | 20 | 1.52 | 1.17 | 1.86 |
| + loop guards + budget guard | **45** | 3.1 | **26** | **1.62** | 1.27 | 1.97 |

- **Guards + budget minus as evaluated: +0.19 [0.10, 0.30]**, and above zero for each judge alone (Claude Code
  +0.14 [0.06, 0.22], gpt-6-sol +0.25 [0.13, 0.39]); higher or level at all six companies.
- It became the app's default (with evidence first added later, below). On version 1 alone the budget guard did not change quality ([recovery controller](#a-recovery-controller-does-not-fix-the-remaining-failures)); with the
  loop guards and the version 3 reasoner it does, on development.

**Test set 2**, on the cluster's bf16 runtime, 24 cases × 3 attempts. The
plain arm is the existing dig-then-reason run of test set 2 (same route, settings and seeds); the two guarded arms
were run once each, and all three were judged together blind by both judges (packets identical to already-judged
ones kept their judgments):

| Arm (72 runs each) | Finished | Refused calls per run | Finished with no invented number | Experiment check passed | Mean of judges | Claude Code | gpt-6-sol |
|---|---|---|---|---|---|---|---|
| Dig then reason, as evaluated | 43 | 6.1 | 34 | 14 | 1.43 | 1.16 | 1.70 |
| + loop guards | 62 | 3.5 | 53 | 29 | 1.58 | 1.28 | 1.89 |
| + loop guards + budget guard | 63 | 3.5 | 50 | 26 | 1.59 | 1.28 | 1.90 |
| + loop guards + budget guard, quote picker fixed (rerun) | **69** | 3.2 | 55 | 28 | **1.64** | 1.32 | 1.95 |

- **Guards + budget minus as evaluated: +0.16 [0.05, 0.27]** (Claude Code +0.12 [0.02, 0.22], gpt-6-sol +0.20
  [0.07, 0.33]); the guards alone: +0.16 [0.05, 0.27]. The gain is in the late stages that stalled runs never reached
  (experiment design, recommendation, revision).
- The budget guard adds nothing here (+0.006 [−0.010, 0.022]): few guarded runs on test set 2 reached the turn limit.
- Not everywhere: both judges score Testo lower with the guards (−0.32), Kingspan is level, and judge agreement on these
  runs is lower than on the final test (Spearman 0.65).
- **A bug in the quote picker, found in these runs and fixed.** All 6 Belimo runs of each guarded arm stopped: the
  picker offered a dateline ('DANBURY, Conn.') that the environment's quote rule refuses, and the model chose it four
  times in a row. The picker now offers only quotes the environment accepts. We registered a rerun of the guards +
  budget arm before running it ([DECISIONS](DECISIONS.md), 12 November 11:35): 66 of 72 runs reproduced call for
  call, and the 6 Belimo runs all finished. **Corrected guards + budget minus as evaluated: +0.21 [0.09, 0.33]**
  (Claude Code +0.16 [0.05, 0.28], gpt-6-sol +0.26 [0.12, 0.40]); against the run before the fix, +0.05 [0.00, 0.13],
  all of it Belimo. The first result stays in the table; test set 2 has now also been used to find a bug.

**The final test** (registered before the run,
[DECISIONS](DECISIONS.md), 12 November 16:30). The guards + budget arm with the fixed quote picker, 16 cases × 3
attempts, judged blind by both judges with the final-test dig-then-reason run as evaluated (same route, settings and
seeds):

| Arm (48 runs each) | Finished | Refused calls per run | Finished with no invented number | Experiment check passed | Mean of judges | Claude Code | gpt-6-sol |
|---|---|---|---|---|---|---|---|
| Dig then reason, as evaluated | 27 | 5.7 | 25 | 9 | 1.44 | 1.13 | 1.76 |
| + loop guards + budget guard | **45** | 2.9 | 37 | 11 | **1.56** | 1.21 | 1.91 |

- **Guards + budget minus as evaluated: +0.12 [0.00, 0.25]**: the interval reaches zero. Claude Code +0.08 [−0.01,
  0.19], gpt-6-sol +0.16 [0.01, 0.33].
- Most of it is one company (SIMO +0.39); AQP, EPRO and RATIONAL are within ±0.04. Finishing a run is not by itself
  better analysis: 18 more runs finish here, for a much smaller gain in judged quality than on the other two sets.
- Judge agreement on these runs is low (Spearman 0.42).
- Across the three sets, the guards finish more runs every time, cut refused calls by about half, and never score lower
  on average; the quality gain is clear on development and test set 2 and uncertain on the final test.
- Experiment folder: [experiments/loop_guards/](../experiments/loop_guards/) (the test set 2 rerun is in `test2_fix/`,
  the final test in `final/`).

## Evidence first: how a source is weighed
With the loop guards in place, the lowest judged dimension on the app default's final-test runs was evidence
judgement (Claude Code 0.46, gpt-6-sol 0.96 of 3). The judges' reasons repeat two patterns: a quote counted as support
for a theory it does not address, and a company's own estimate labelled as independent evidence. Two more changes act
only at decoding, each registered with its adoption rule before it ran ([DECISIONS](DECISIONS.md), 12 November
18:15 and 19:55):
- **evidence first**: when weighing a source, the model writes the quote and what the quote does not show before it
  picks the evidence kind and the direction (llama.cpp keeps the schema's field order in its grammar), and for a source
  the environment marks as a company claim the only kind offered is a company assertion;
- **grounded beliefs**: the conclusion can rate a theory 'likely' or 'very likely' only if a real source the run
  weighed supports it, and the run's own weighings per theory are shown at the position, update and conclude steps.

On development (15 cases × 3, four arms side by side, both judges), grounded beliefs alone changed the conclusions as
designed (a strong belief in 33 of 44 finished runs against 40 of 43; 10 recommendations to test first, none before)
but not the scores (−0.01 [−0.05, 0.03]), so it was not taken forward on its own. Evidence first passed its rule with
and without grounded beliefs, and the arm with both was run once on each test set against the app default (same route, settings
and seeds, judged blind together):

| Set | Mean of judges, app default → evidence first | Difference | Claude Code | gpt-6-sol | Evidence judgement (Claude Code / gpt-6-sol) | Recommendation (Claude Code / gpt-6-sol) | Finished | Runs with a number found nowhere (failing the check) |
|---|---|---|---|---|---|---|---|---|
| Development (45 runs per arm) | 1.56 → 1.63 | **+0.07 [0.03, 0.11]** | +0.05 [0.01, 0.09] | +0.08 [0.02, 0.14] | 0.62 → 0.91 / 1.07 → 1.20 | 1.05 → 1.05 / 1.07 → 1.16 | 43 → 43 | 9 → 8 (13 → 20) |
| Test set 2 (72 runs per arm) | 1.64 → 1.67 | **+0.03 [−0.00, 0.06]** | +0.02 [−0.01, 0.06] | +0.04 [−0.01, 0.09] | 0.56 → 0.82 / 1.06 → 1.21 | 1.03 → 1.12 / 1.16 → 1.18 | 69 → 65 | 7 → 7 (14 → 32) |
| Final test (48 runs per arm) | 1.56 → 1.62 | **+0.06 [0.00, 0.11]** | +0.10 [0.02, 0.17] | +0.03 [−0.05, 0.10] | 0.46 → 0.98 / 0.96 → 1.31 | 1.00 → 1.04 / 1.16 → 1.17 | 45 → 46 | 3 → 2 (8 → 16) |

- **Higher on all three sets, by a little.** Mean of judges +0.07 [0.03, 0.11] on development, +0.03 [−0.00, 0.06]
  on test set 2 and +0.06 [0.00, 0.11] on the final test; higher at 6 of 6, 9 of 12 and 4 of 4 companies. Each gain is
  smaller than the loop guards' on the same set, and on test set 2 the interval touches zero.
- **It improves the judgement of evidence, not the conclusion.** Evidence judgement rises for both judges on every set
  (Claude Code 0.46 → 0.98 on the final test); the recommendation moves by 0.00 to 0.09. The conclusion is still the
  weakest part of an investigation.
- **Four fewer runs finish on test set 2** (65 of 72 against 69). Five runs stop that finished with the guards alone:
  three run out of room in the final answer (a 'would change if' text over its 300-character limit, or a finish cut
  off by the per-turn token limit), one does not challenge its favoured theory before stating it, one reaches the turn
  limit; one run that had stopped now finishes. The same refusals occur without evidence first; no guard prevents them.
- **Now the app default**, under a rule registered before the second judge scored test set 2 (mean-of-judges
  difference at least 0; [DECISIONS](DECISIONS.md), 13 November 00:10).
- **The numbers check fails more often, and the extra failures are the check's.** Splitting each failure by where its
  numbers come from: runs with a number found nowhere, not even in the run's own test design, do not rise on any set
  (last column). The extra failures are recommendations that restate the run's own test thresholds ("run X; if
  purchase intent reaches 35%…"), which the check reads as claims because they sit in the recommendation. The check
  is unchanged and both counts are reported.
- Experiment folder: [experiments/grounded/](../experiments/grounded/) (`screen2/` the development screen, `test2/` and
  `final/` the two test sets); the table comes from `scripts/release/evidence_first_table.py`.

## A recovery controller does not fix the remaining failures
We tested five controller-side recovery aids on development cases under a pre-registered rule (masking rereads,
progress notes, step-budget awareness, citation repair, and all four). The best, step-budget awareness, rescued 15 of
28 stuck runs against 6, but end to end it changed 8 of 45 runs and left blind quality unchanged (+0.006
[−0.017, 0.031]): the extra finishes rush a templated test. More finishes are not better investigations; the
remaining failures need training, not a controller. Full report: [docs/RECOVERY_REPORT.md](RECOVERY_REPORT.md).
That was version 1 alone; combined with the loop guards and the version 3 reasoner, the same budget guard is part of
the arm that finished every development run and scored higher ([Loop guards](#loop-guards-on-development-test-set-2-and-the-final-test)).

## What else we tested
Specialist adapters per stage (proposed; the data per stage was too thin), a Socratic coach (proposed, not built), more teacher data
versus the clearer state (inconclusive), and scripted always-keep and always-revise policies as negative controls on
the development cases (they could not run on the held-out cases, which we report as a deviation).

Tooling, tested for a later training run that was not made: **Unsloth** (the same rows, LoRA and seed through
AgentTune's trainer, 60 steps: 23% faster per step, 8.1 GB peak memory against 11.6, losses within 0.003) and
**CuratorKIT** row curation ([README](../README.md#2-hackathon-repositories-used), section 2). A further teacher run with the status check was started and stopped before it
produced data. A version 4, recovery training for the reasoner from a free teacher (Command A+ on the cluster), was
registered and then stopped (`docs/DECISIONS.md`, 12 November 16:30): the loop guards had already removed the failure it
targeted, and one day of teacher time gave 30 usable corrections, too few to move a 45-run screen. No version 4 was
trained. Runs, metrics and adapters are tracked in MLflow (`ops/mlflow/`).
