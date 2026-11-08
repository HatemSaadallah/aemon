# Guard changes during development

Why this exists: guards were changed after seeing Claude's control runs, which is how a standard quietly drops. Each change below keeps its old behaviour, the example that triggered it, the reason, and what must still fail. Every run used to make these changes is development data. Nothing here is a validation.

The old code is in git at `5c41acf`. `compare.py` scores recorded runs under old and new guards, and `compare.json` lists every verdict that changed.

**Status: reviewed by Codex on PR #17, with its changes applied below. Not frozen.**

**The result to check first.** Verdicts that changed between the old and current guards, on the recorded runs:

| Runs | Episodes | Fail to pass | Pass to fail | Other |
|---|---|---|---|---|
| open arm | 12 | 0 | 0 | 0 |
| first controller | 12 | 0 | 0 | 1 |
| corrected controller | 15 | 1 | 0 | 0 |
| Claude control | 12 | 8 | 0 | 0 |
| Claude smoke | 1 | 1 | 0 | 0 |
| Claude, corrected controller | 15 | 8 | 0 | 1 |
| Aya Expanse | 3 | 0 | 1 | 1 |
| Aya Expanse, stricter prompt | 9 | 4 | 0 | 0 |

The loosening mostly helps runs that get far enough to be judged, and Claude most of all. That is what a lowered standard would look like, and it is also what fixing a checker that only a capable run could reach would look like. Each flip needs reading before these changes are accepted. `compare.json` lists them.

## Loosened: these need the hardest look

### `no_invented_numbers` (a7187b9)

- **Old:** every number in the final text must appear in a source read, or in the brief.
- **New:** claims about the world still must. The next action and `would_change_if` may also repeat numbers from the run's own proposed test.
- **Trigger:** `tooling/real_model/strategy/control/smoke_moldex_looks.json`. It was flagged for 10, 18000, 80, 1 and 6, and all five are in its proposed test X1. They are a plan, not claims.
- **Must still fail:** `test_a_test_cost_cannot_launder_a_number`, `test_a_claim_about_the_world_cannot_borrow_a_test_design_number`, `test_a_plan_cannot_bring_in_a_number_of_its_own`, `test_disguised_invented_numbers_fail`, `test_invented_numbers_fail`.
- **Known hole:** a model can still launder a number by writing it into a test and repeating it in its next action.

### `revision` (e886561)

- **Old:** evidence against a held theory passed only if that theory was revised or rejected.
- **New:** it passes when the model read the evidence and recorded a response citing it, including `kept`, unless it rejected every theory or still favours one it rejected. Any change on irrelevant evidence fails. Rejecting a theory after favourable evidence still fails.
- **Trigger:** `moldex-new-evidence-looks` in the Claude control. It kept T2, reasoning that a simulated result is not real and touched only a side point. Outside feedback then said holding a recommendation can be right, and that always changing must fail.
- **Must still fail:** `test_rejecting_a_theory_the_evidence_favoured_fails`, `test_a_change_on_irrelevant_evidence_fails`, `test_rejecting_everything_on_one_result_fails`, `test_keeping_a_rejected_theory_as_favourite_fails`, `test_revising_without_citing_the_new_evidence_fails`.
- **Risk:** a model can now pass by writing `kept` every time. The guard cannot see that, so the paired conditions and judges must. A policy of always keeping has to be measured before final evaluation.

### `evidence_kinds` applies only with annotations (d467a4e)

- **Old:** with no annotated records it returned no verdict, which counted as a pass.
- **New:** it does not apply on such a dossier. The real dossier is fully annotated, so this affects only test fixtures.

## Tightened

- **`guards_cleared` (d467a4e).** A check that applies but was never evaluated no longer counts as a pass. Codex asked for this.
- **Affected theories (d467a4e).** Judged on a theory's first claim, so revising it cannot hide that it was affected.

## Changed after Codex's review

- **`revision`.** Two holes were found. Silence on favourable evidence passed, and a response about an unrelated theory passed. Every direction now needs a cited response, and supporting or undermining evidence needs a response to an affected theory. Must still fail: `test_silence_on_favourable_evidence_does_not_pass`, `test_the_wrong_theory_check_uses_what_was_addressed`.
- **Diagnostics, reported but not gating:** `causal_form`, `testable_predictions`, `evidence_kinds` and `evidence_classes`. Each measures a real concern with a rule too blunt to gate on, and Claude cleared none of its 15 runs under them. Their counts stay in every report, and judges score these things. This is a further loosening, made on Codex's recommendation, so it needs the same scrutiny.
- **`causal_form`:** now only "should" and "ought to". "Must" can describe a cause, and "opportunity" is not advice.
- **`theories`:** two distinct theories, with a third optional.
- **`experiment`:** declining a test is allowed, and scored against what the case declares as warranted before any run. A proposed test on a case that does not warrant one fails.
- **`no_invented_numbers`:** unchanged. Test figures are now labelled analyst assumptions in the tool result.

## Negative controls

`strategy/fixed_policies.py` runs scripted policies through the paired cases, and `tooling/real_model/strategy/fixed_policies.json` holds the results.

| Policy | Undermining | Supporting | Irrelevant |
|---|---|---|---|
| Always keep | 6 of 6 pass `revision` | 3 of 3 pass | 3 of 3 pass |
| Always revise | 6 of 6 pass | 3 of 3 pass | 0 of 3 pass |
| Always reject | 6 of 6 pass | 0 of 3 pass | 0 of 3 pass |

So the guard cannot see an always-keep policy, or a revision that goes the wrong way. The paired conditions and blind judges have to catch those.

## Schema limits

Per-turn schemas may reject what does not exist. They must not choose for the model. Two limits in `e886561` went further, hiding simulated results from `finish` and offering only challenged theories to `state_position`. Both were reverted in `c3eb171`, and those mistakes are refused on the record again.

Rereads are now open at no search cost. The update stage still opens only `revise_theory`, so it is reported as a measurement intervention: it tests the quality of a response to delivered evidence, not whether a model chose to revisit its view.

## Run versions

Scores from different setups are never combined. The first structured run is a diagnostic, because harness faults contributed to its result. It stays visible, labelled as such. A planned second version of that run never started, because a wait loop matched its own command line. The corrected run is `base_q4_structured_v3`. Runs from `c3eb171` carry a setup id, and runs after this review carry separate protocol, suite and model ids.
