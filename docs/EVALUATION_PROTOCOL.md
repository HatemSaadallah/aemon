# Aemon evaluation protocol (draft)

**Status:** Draft for Claude and Hatem to review. Not frozen; no confirmatory run or training-data generation is authorized by this document. Version 0.1, November 2, 2026.

This protocol tests Aemon, a strategic opportunity-analysis agent for manufacturers exploring consumer markets. It describes an evaluation of investigation quality under automated judging. It cannot establish that a recommendation is commercially correct or improves business outcomes.

## 1. Question and claims

**Primary question:** On the same cases, evidence, tools, limits and inference settings, does supervised fine-tuning of Tiny Aya improve investigation quality over the same untrained Tiny Aya in the structured workflow?

The primary contrast is **C minus B** below. The open-workflow model (A) is a reference for the starting system, not a clean estimate of the controller's effect: prompt guidance, available actions and stage order differ. Any A–B difference is described as a combined workflow-and-prompt comparison.

| Arm | Model | Workflow | Purpose |
|---|---|---|---|
| A | Untrained Tiny Aya | Open workflow with the frozen strong prompt | Starting reference only |
| B | Untrained Tiny Aya | Frozen structured workflow | Primary baseline |
| C | Fine-tuned Tiny Aya from the same base checkpoint | Identical structured workflow to B | Primary treatment |

A stronger teacher may be reported as a descriptive reference after its access, license and hackathon eligibility are confirmed. It is not part of the B–C contrast and cannot judge its own data. Claude may be used for workflow checks or blind judging only under the applicable terms. Claude-origin outputs are not training data without express, verified approval for this exact use. Claude judge scores stay out of training-row selection in all cases; if Claude is approved as a teacher, a different judge must assess its demonstrations.

## 2. Experimental unit and matching

The unit for uncertainty estimates is the **underlying strategic case cluster**, not a transcript, arm, shock variant, or repeated generation. Pair B and C on the same frozen case, evidence dossier, shock packet, tool budget, stage rules, turn and retry limits, output limits, model precision, decoding settings, and order-independent seed plan. Randomize arm run order within each case cluster.

B and C must use the same Tiny Aya checkpoint and precision. C adds only the saved adapter and its declared training history. Record checkpoint and adapter hashes, tokenizer/template revision, runtime/build, software versions, prompt hash, tool/controller/checker hashes, generation settings, case-manifest hash, seed and full raw trace. Use separate identifiers:

- `protocol_id`: code, tools, prompt, checks, and inference settings shared by B and C;
- `suite_id`: ordered frozen case, evidence, shock, and repeat manifest;
- `model_id`: exact checkpoint/adapter, precision or quantization, tokenizer/template, and runtime build.

Record both requested and effective context limits, including the chat template and reserved output tokens. B and C share the measured 8,192-token combined input/output limit unless a different effective limit is verified and frozen before either arm runs. A context-limit stop is a model-system outcome: keep it in all-case denominators and report its count and stage separately. A valid primary pair has equal `protocol_id` and `suite_id`; `model_id` is expected to differ. A run with a missing hash, dirty unrecorded code, or unmatched manifest is excluded from the paired estimate and reported as a protocol failure. Keep Q4 development runs separate from the full-precision comparison.

## 3. Case development and held-out suite

Moldex-Metric is development and demonstration only. Cotral Lab and Hellberg Safety share the hearing-protection domain and evidence, so they are also development cases. No final-test case, source, distinctive mechanism, prompt wording, or template may be used to design the prompt, checks, teacher rows, or training examples.

Before final evaluation, freeze a manifest with at least three distinct product categories and mechanisms that do not reproduce hearing protection. For each case, record:

| Field | Required entry |
|---|---|
| Case ID and cluster ID | Stable IDs; all shocks and repeats link to one cluster |
| Company and product category | Named manufacturer and the consumer opportunity being investigated |
| Mechanism | Why a specific customer would change behavior and how the maker could capture value; materially different from the Moldex mechanisms |
| Evidence dossier | Source IDs, URLs, access dates, exact excerpts, access limits, evidence classes, and a content hash |
| Design classification | Case author's pre-run hypothesis: more evidence is worth its cost, or a decision/stop is already justified; include rationale and uncertainty |
| Shock packet | Supporting, contradicting, or irrelevant what-if, target mechanism, strength, and expected direction; hash and delivery point |
| Leakage check | Confirmation that company, product, evidence, and mechanism were absent from development and training |

The manifest is a required freeze gate. It is currently unpopulated, so the held-out suite is **not ready** and no confirmatory claim can be made yet. Case-author labels about whether research is worthwhile are design assumptions, not objective truth. For real public-evidence cases, a judge scores reasoning and uncertainty; we do not claim a known correct business decision. Only controlled synthetic shocks have a predeclared signal direction, and each is labelled as hypothetical in the episode.

Use cases that exercise both choices: continue investigating when a discriminating test is worth its cost, and stop or recommend a bounded next step when more information is not worth the cost. Freeze the case mix before evaluation. Do not infer correctness from the number of tools used or tests proposed.

## 4. Workflow and decision latitude

The controller may enforce valid tool calls, evidence provenance, budget limits, and a transparent minimum structure. It must not select sources, invent or repair theories, write evidence interpretations, or manufacture a favorable finish. Record every refusal and harness action separately from model actions.

Use **two distinct causal theories as the minimum** for a theory comparison; a third is optional. Do not require a proposed experiment in every case. Once the model has enough context to make a reasoned choice, allow it to finish with a recommendation to stop, test, or gather a specific piece of evidence, and require a brief reason when it declines a test. A test is scored for discrimination and feasibility when proposed. A failure to propose one is not automatically a failure when the case does not warrant more research.

These are study design choices, not rules claimed to come from the source paper. Freeze them before collecting confirmatory outputs. If the three-theory or mandatory-test workflow is retained for a separate capability study, report it as conditional investigation quality and do not claim that the agent chose whether to investigate.

Allow the model to reread any previously surfaced source at no additional search cost. Keep the event log clear about first reads and rereads. Treat the forced post-position update step as a measurement intervention: report that it tests the quality of a response to delivered evidence, not whether the agent independently chose to revisit its position.

### Optional Socratic coach

Begin with fixed, bounded questions about the objective, constraints, rival explanations and evidence that would contradict a theory. A user-facing coach may ask the person these questions in the UI. Inside a model investigation, even a question supplies a scaffold: its contribution must be measured and disclosed.

Keep the coach disabled in the primary B/C comparison unless development results justify adopting it before the protocol freezes. If adopted, B and C share exactly the same deterministic triggers, templates, question cap and budget. Log each coach prompt as a harness action and count its tokens and latency. A coach may request reflection but may not select a theory/source, interpret evidence, provide a missing answer or suggest the next recovery action. A dynamic model coach is a separate treatment requiring a matched comparison. No coach configuration is chosen using final-test outcomes.

A bounded action-explanation field is likewise an inference treatment. If adopted, it is identical in B/C and emitted by the model itself. Do not equate it with native model thinking or rewrite native thinking into supervised targets after generation.

## 5. Controlled revision packets

For each revision case, capture the model's position immediately before evidence delivery and after it has read the packet. The same packet and delivery point are used for all arms. Include:

1. a supporting signal;
2. a contradicting signal, with both strong and non-decisive examples across the suite; and
3. an irrelevant signal.

The model is told that the result is simulated, reasons about the stated what-if, and must not cite it as real-world evidence. Do not require a recommendation flip after every contradicting signal: a weak result may rationally narrow the theory or leave the decision unchanged. Score whether the response targets the affected theory, cites the packet, explains its limits, and moves the position in a way consistent with the signal's predeclared strength. Include scripted **always keep** and **always change** policies on the same packets as negative controls. They should demonstrate that the procedure does not reward either reflex.

Do not add a harness-computed Bayesian update to this pilot. Record the model's own confidence per theory before and after evidence on a five-point anchored ordinal scale (very unlikely, unlikely, uncertain, likely, very likely). This is a within-episode response signal, not a calibrated probability. If the model reports 0–100 integers instead, accept only 0, 25, 50, 75, or 100 and analyze them as the same five ordered bins. Do not claim calibration from these values.

## 6. Outcomes and judging

### Primary outcome

Use the frozen strategy rubric's nine dimensions, each scored 0–3. The dimensions applicable to each case are fixed before runs (for example, revision does not apply to a case without a shock). The primary per-episode score is the unweighted mean over those fixed applicable dimensions (0–3), assigning zero to an applicable stage that was not reached while retaining its not-reached tag; reached-stage quality is reported separately. Unfinished and context-limited episodes remain in this all-case score. The primary effect is the paired C-minus-B mean within case clusters. Report all nine dimension effects and red flags beside the composite so a gain in completion cannot hide worse evidence or theory quality. Report the two arms' absolute scores, not only the difference.

### Blind LLM judges

No human reviewers are planned. Use two LLM judges that are neither the student nor the training teacher, with the same frozen rubric, prompt, model version, and settings for every arm. Remove arm/model names, setup IDs, and cost metadata from judge packets; randomize packet and pair order. Preserve the full episode chronology and tool results, since reasoning and evidence use must be judged. Keep every raw judgment and report each judge separately, their mean, and disagreements. Do not resolve disagreement by selectively rerunning only unfavorable packets.

Score fixed anchors in each judge batch: a deliberately nonsensical investigation, a clipped/misleading quote, an incomplete run, and a strong reference. Anchors check whether the instrument distinguishes obvious quality differences; they are not ground truth and do not establish commercial correctness. Also report sensitivity to presentation and response length. If judges fail the anchor contrast or show strong order/presentation sensitivity, the quality result is inconclusive; report executable behavior only.

Final-evaluation judges may not tune prompts/checks or select training rows. Teacher qualification and row-level quality screening are separate procedures on development/training data: if a permitted, teacher-distinct screener passes a frozen reliability check, it may screen rows with predeclared criteria, saving every acceptance/rejection and rationale. Claude scores remain outside row selection under the current policy. Guard passage alone establishes mechanical validity, not sound reasoning. The outcome supports wording such as “higher scores under this blind LLM rubric,” not “better strategy” or improved business outcomes.

### Executable and operational outcomes

Report every guard's passed, failed, not-evaluated, and not-applicable counts, with both applicable and reached denominators. Do not headline an all-checks-pass total. Keep AuditKIT replay results, accepted/rejected calls, harness calls, recoveries, completion, cost, latency, and token counts separate. The full event log is replayed; model-attribution metrics exclude harness-authored actions but retain model refusals.

A guard is a mechanical diagnostic, not a quality measure. In particular, evidence-class and evidence-kind labels can be ambiguous; report their raw counts and do not let them outweigh the blind rubric. A “demand remains unknown” conclusion can be sound even when independent demand evidence is absent. Exact quotes and replay correctness do not establish that an inference is sound.

## 7. Analysis and reporting

Freeze the case manifest, protocol IDs, primary contrast, judge prompt/settings, scoring rule, analysis code, and resource/sample cap before opening final-test outputs. Development runs and the teacher-quality gate cannot be included in the final estimate. Resample at the case-cluster level; repeated episodes, arms, and shock variants within one case are not independent samples. Report paired effect estimates and 95% cluster-bootstrap intervals, individual judge results, all exclusions, missing runs, and all negative-control outcomes.

The available development runs are too small and guard definitions changed after seeing them. They are for design and failure discovery only. A final sample size and any minimum effect of interest must be selected before final outcomes are inspected; if the resource cap cannot support a useful interval, report the result as exploratory or inconclusive. Do not extend the sample, change the rubric, redefine a guard, or substitute a more favorable metric after looking at final results.

Report the three arms separately. B–C is the training contrast. A is descriptive because its workflow differs. Do not pool Q4 and full-precision results or attribute B–C differences to training if any controller, case, evidence, precision, prompt, budget, retry, or decoding setting differs.

## 8. Teacher, provenance, and data gates

No training rows are generated until all of these are true:

1. The teacher is permitted by the hackathon rules and its license/access terms, and its exact artifact and runtime are pinned.
2. Development trajectories show useful causal reasoning, evidence judgments, and discriminating experiments under blind review; completion and guard passage alone are insufficient.
3. Claude has reviewed the source and training-row boundary. Claude-origin outputs remain excluded unless Anthropic's express approval for this exact distillation use is verified and the dataset/model scope is documented. Claude judge scores may never select training rows; an approved Claude teacher must be evaluated by a different judge.
4. The protocol and held-out manifest are frozen, and the project has not exposed the teacher to held-out case packets during prompt tuning, demonstrations, or training-data generation. Prior exposure in model pretraining is unknown and must be acknowledged.
5. Each training row links to an append-only episode manifest with source backend, model/artifact hash, run and code hashes, episode/call-log hash, teacher prompt, seed/settings where supported, evidence provenance, and replay result. A display label or `training_eligible` Boolean is not sufficient provenance.
6. Rejected teacher runs remain recorded with reasons. Do not polish tool calls after generation or select rows using the teacher's own judge scores. Use the separately qualified row screener described above for reasoning quality; until one exists, label rows mechanically validated rather than verified reasoning.

Aya Expanse 32B runs recorded to date were rejected for weak reasoning. Command A+ is outside the currently listed permitted models and remains evaluation-only until Hatem confirms its use with the organizers. The quoted Anthropic approval recorded in `docs/DECISIONS.md` is not yet independently verified there. Until those approvals and the teacher-quality gate are resolved, there is no approved teacher dataset and no training claim.

### Training-row integrity and recovery examples

Bind the exact supervised reply text, tool results, case/dossier identity, source protocol and full action sequence to the episode manifest. Replay the complete reply stream against that authoritative sequence, including refused calls. A completion requirement is satisfied only by an accepted finish reached during replay, not by the report's `final` metadata. Reject a truncated stream or text added after collection even when its parsed tool call is unchanged.

Per-turn rows may retain the full preceding conversation while applying loss only to the next accepted model reply. Verify the actual student tokenizer's prefix token IDs before creating label masks; separate prefix/full tokenizations must not silently mask part of the target or train on context. Report token lengths and overlength rejection counts by stage, including late recommendations and revisions. Never silently truncate targets or select only early stages because they fit.

Recovery training may use actual student failure prefixes followed by a real teacher continuation. Preserve the student prefix, source model and raw outputs, refused actions, replayed state, teacher identity, and continuation boundary. Such rows have mixed provenance; they are not clean teacher-generated episodes. Use development/training cases only and qualify recovery targets through the same permitted screening procedure. Count investigation clusters and stage coverage as well as row count, because many per-turn rows from one run are correlated.

## 9. Freeze checklist

Before confirmatory evaluation, record the frozen commit and complete all items:

- [ ] held-out case manifest populated, source-verified, hashed, and disjoint from development/training;
- [ ] two-theory minimum and optional-test behavior implemented consistently in B and C;
- [ ] revision guard requires an explicit cited response to an affected theory where applicable; silent and wrong-theory negative controls fail;
- [ ] `protocol_id`, `suite_id`, and `model_id` validation rejects unmatched B/C pairs;
- [ ] teacher permission, exact artifact provenance, and teacher quality reviewed;
- [ ] training-source provenance binds rows to raw episode traces and excludes Claude-origin episodes;
- [ ] blind judge prompt/settings, anchors, packet randomization, and sensitivity checks frozen;
- [ ] primary score, cluster-bootstrap code, sample cap, and claim wording frozen;
- [ ] all results are reproducible from saved model, code, case, and episode hashes.

Until these boxes are complete, results are development diagnostics only.
