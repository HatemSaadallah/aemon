# Failure-aware recovery experiment (pre-registered 2026-11-09, before any model run)

Question: how much of version 1's unreliability can a failure-aware controller fix without retraining, without weakening
any guard and without lowering quality, and which failures need a better learned policy?

Branch `claude/failure-recovery`. Nothing here changes version 1, the evaluated runner defaults, either frozen test set
or their results. All new artifacts live in `experiments/recovery/`.

## A. Architecture audit (verified in code, not assumed)

**Lifecycle** (`agent/runner.py: play`): system prompt `compact` + "A new investigation is ready. Call read_brief." →
each turn: `schema_for(run)` builds a JSON schema admitting one call to a tool open in `current_stage(run)`
(`env/stages.py`), with ids narrowed by `_narrow` to those that exist → the model replies under that schema →
`parse_call` → `Investigation.call` (`env/tools.py`) applies guards: accepted calls update the state, refused calls
return `{'error'}` and are logged with a category and change nothing → the next observation is `state_of(run)` plus the
stage's guidance (`next`, `open_tools`, searches left) and the last result. Stops: `finish` accepted ("finished");
`max_errors`=4 refusals in a row ("repeated errors"); `max_turns`=45 ("turn limit"); context full; server refusal.
Decoding: temperature 0; 0.4 with seed `sum(ord(case id)) + 1000·attempt + errors` while the last call was refused.
Replay: `prefix` turns are re-executed and must return their recorded results exactly.

**Mechanisms that cause loops or dead ends**
1. `read_source` stays open outside the evidence step and offers every surfaced id (`_narrow`): rereads are accepted, add
   nothing, and are not refused, so they burn turns (turn-limit deaths).
2. Repeats (same search, same theory-source assessment) are refused; the refusal text says what was wrong but not what
   can succeed; four in a row end the run.
3. The `finish` schema offers every read id as a citation, including the simulated what-if, which the tool then refuses
   (`synthetic_as_evidence`): the schema invites a call the guard must refuse.
4. The observation shows the stage instruction but no measure of progress and no remaining-turn count against what the
   stage still requires.
5. At the test step, the look-further tools (search, read, assess, add_theory, challenge) stay open beside
   propose/decline, so the step can be avoided indefinitely.

**Intervention points without retraining**: the schema (`schema_for` / `_narrow`), the observation (`shown` dict
added to the state), and nothing else. Guards, stage transitions and termination are not touched.

**Validity risks**: (i) a resumed checkpoint must keep its refusal count and remaining turns, which `play` did not
support (added: `errors_at_start`, default 0); (ii) the laptop runtime (Q4 base) differs from the evaluated bf16
runtime, so baseline continuations are not byte-identical to the recorded ones, only comparable across configurations
on the same runtime; (iii) checkpoints are dead ends of runs that failed, so recovery rates are conditional on failure.

## B. Failure taxonomy (`evaluation/failures.py`)
A repeated source read · B repeated invalid call · C missing prerequisite · D simulated-evidence misuse · E six calls
without progress in one step · F turn limit · G refused finish without finishing · H context or schema. Progress =
a change in the accepted state (brief, frame, sources read, theories, theory–source assessments, challenges, test or
decline, position, revisions, final); searches, rereads and refusals are not progress. Earliest cause, later causes and
termination are recorded separately; recovery after a refusal (progress within 3 calls) is counted.

On the 122 version 1 runs on training companies (75 unfinished): earliest failure E 50, B 25, all at the theories step;
any failure B 75, E 67, A 47, F 29, D 1. Dead ends (state after the last progress): theories 38 (30 refusals, 8 turn
limit), test 30 (18 turn limit, 12 refusals), 7 elsewhere. Simulated-evidence dead ends occur only in development cases
with a what-if (3 in the 45 as-evaluated development runs).

## C. Benchmark (`experiments/recovery/benchmark_v1.json`, `recovery_bench build`, seed 20261109)
One checkpoint per failed episode, at the first call of its dead end, with the exact prefix turns, refusal count,
remaining turns, attempt (seed), settings and source report hashes. 28 from training companies, stratified: theories /
refusals 8, theories / turn limit 5, test / turn limit 6, test / refusals 5, other 4; plus 3 exploratory checkpoints of
the simulated-evidence dead end from development (validation) runs, analysed separately. 26 companies. No held-out or
test-set-2 case (tested).

## D. Configurations (`agent/recovery.py`, `play(recovery_features=...)`)
A baseline · B mask_rereads · C progress (structured refusals + recovery note after 3 calls without progress) ·
D budget (note and exploration withdrawn when turns left ≤ minimum required + 3) · E citations (finish cites real
sources only) · F all four. Same weights, prompt, decoding, seeds, turns left and refusal count for every configuration.

## Metrics, fixed before running
- **Valid recovery (primary)**: the continuation ends in a later controller step than the checkpoint's, or finishes.
- Completion: an accepted finish. Validated completion: finished and every non-diagnostic guard cleared (mechanical;
  blind-judge quality on stage 2 only).
- Also: progress calls, first progress, refusals by category, simulated-citation refusals, rereads, calls, tokens, time.

**Primary comparison**: F against A on the 28 training checkpoints, paired by checkpoint; difference in valid-recovery
rate with a 95% bootstrap interval resampling companies (4,000 resamples, seed 20261109). B–E against A are exploratory.
The 3 development checkpoints are reported separately, never pooled.

**Stage 2 selection rule, fixed now**: the configuration with the highest valid-recovery rate on stage 1, among those
whose validated-completion rate is not below A's, runs end to end on the 15 development cases × 3 attempts (45 runs);
it is preferred over the as-evaluated configuration only if it finishes more runs and the mean blind-judge quality is
not lower (Claude now; Codex from 11 November). Never run on either frozen test set as a new independent test.

## Adoption into Aemon (added 2026-11-09 12:50, before any result was analysed; Nour)
A configuration becomes an **optional, configurable runtime** in Aemon only if, on stage 2 (45 development
runs), it (1) finishes more runs than the as-evaluated configuration, (2) does not lower the mean blind-judge quality,
nor the validated-completion rate, (3) keeps every guard and termination rule, and (4) adds no simulated-evidence
citation. A better recovery rate on stage 1 alone is not enough. If adopted it is switchable and labelled on the page;
the frozen evaluation configuration and version 1 stay untouched. The report lists separately what was integrated,
what stays experimental and why, and which failures still need fine-tuning.

## Stage 1 result (2026-11-09 17:20; 28 training checkpoints × 6 configurations, Mac Q4 runtime)
| | A | B reread mask | C progress | D budget | E citations | F all |
|---|---|---|---|---|---|---|
| valid recovery | 6 | 11 | 5 | 15 | 6 | 17 |
| finished | 3 | 7 | 3 | 11 | 3 | 11 |
| validated completion | 1 | 1 | 0 | 2 | 1 | 0 |

Paired against A (company bootstrap, 95%): valid recovery F +0.39 [0.19, 0.62] (12 better, 1 worse), D +0.32 [0.16, 0.52]
(9 better, 0 worse), B +0.18 [0.00, 0.38]; C −0.04 and E 0.00 are null. D's gain is concentrated at the test step out of
turns (A 0/6, D 6/6). Most new finishes fail a non-diagnostic guard (D: invented numbers 7, no test 6, evidence kinds 6),
so finishing is not validated completion. Development simulated-evidence checkpoints (exploratory, n=3): A–D 0/3, E and F
3/3, none validated.

**Selection under the rule above:** F has the highest recovery but its validated completion (0) is below A's (1), so it
is excluded; **D (budget) runs stage 2.** Stage 2: jobs 749572 (as-evaluated control) and 749573 (RECOVERY=budget), same
code revision 52d4f4a, adapter, cases and seeds, development split only. The conversion gate is the known diagnostic
failure, as for every development run of this adapter, so both arms are marked DIAGNOSTIC and compared only to each other.
