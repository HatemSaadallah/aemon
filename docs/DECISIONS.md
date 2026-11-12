# Decisions

Paths in entries before 2026-11-05 refer to the old layout (`strategy/`, `tooling/`, `run_agent.py`). The README maps them to `src/strategy_agent/`, `jobs/`, `scripts/`, `data/` and `reports/`.

Choices that shape the experiment, with what was considered. Change one here, openly, or not at all.

## Teacher: Aya Expanse 32B, not Claude

Decided November 2, 2026.

**Options considered.** Aya Expanse 32B, a fallback Cohere model, or Claude. Hatem offered Claude as the teacher and said it was probably the better teacher. An outside reviewer also proposed it, with a provenance record in place of the block.

**Decision.** Claude is not the teacher. Aya Expanse 32B was tried first, and its runs were rejected: it follows the workflow, but its reasoning stayed weak even with a stricter prompt (`reviews/teacher_review/`). Hatem asked for another teacher if it was bad, so Command A+ is now under test. It is a Cohere model, Apache 2.0, and not on the permitted list. Lexsi confirmed on November 2 that it is allowed, as Hatem reported.

**Why not Claude.** Anthropic's commercial terms, section D.4, say the customer may not "access the Services to build a competing product or service, including to train competing AI models or resell the Services except as expressly approved by Anthropic" (https://www.anthropic.com/legal/commercial-terms, read November 2, 2026). Training a published language model on Claude's trajectories falls within that on the plain reading. Whether a small adapter truly "competes" is arguable, but that is Anthropic's to answer.

**Two separate questions.** Whether to use a model is Hatem's decision. Whether its licence or service terms allow training on its output is checked here, because that is what this project's code does.

**What the organizers said.** Hatem reported Lexsi's reply on November 2 as "they said using antrhopic is ok", and later "lexsi said we can use claude". The question he sent asked about Claude for evaluation and harness tests only, with none of its output used for training, so the reply covers that use.

**Where each candidate stands.** Claude: eligible for evaluation, and excluded from training by its provider terms, a question Hatem has closed. Aya Expanse 32B: eligible as a listed model, licence CC-BY-NC, rejected on quality. Command A+: licence Apache 2.0, so its provider terms allow it, and Hatem confirmed on November 2 that it may be used. It is the chosen teacher, subject to the behavioural review and the protocol gates.

**What the weights hash does.** It identifies which checkpoint produced a run, so a label cannot launder an episode. It does not grant permission: permission is recorded here, and `TEACHER_WEIGHTS` only enforces it. An API teacher would need its model version, prompts, request ids and outputs recorded instead.

**Reported approval.** On November 2 Hatem reported an email from Anthropic saying this use is fine, because the model is neither commercial nor competing. He then pasted this text:

> In this scenario, you may use Claude to generate teacher demonstrations for fine-tuning Tiny Aya Global for your Lexsi hackathon project, subject to the applicable service terms. Please document the origin of the generated demonstrations and evaluate the resulting model independently.

**Status: dropped by Hatem on November 2, so the policy is unchanged.** The paste has no sender, date or signed name, so its origin cannot be confirmed from it. It is subject to the service terms, which include D.4, it does not mention D.4 or competing models, and it does not cover publishing the adapter or dataset.

**What Claude does instead.** It tests that the workflow can be completed, and it can judge transcripts. Its output cannot reach a training row, and its scores cannot decide which rows are kept. `strategy.claude_control.training_source` enforces this from an append-only manifest, identifying a teacher by the hash of its weights rather than a label.

**What would change this.** Written approval from Anthropic. The judging plan would then need revisiting, because judges must be distinct from the teacher.

## No human reviewers

Decided by Hatem on November 2, 2026, on cost. Quality comes from executable checks, paired behavioural tests and blind LLM judges. Results are described as improved performance under automated evaluation, not as proven judgment.

## Moldex-Metric is for development only

Approved by Hatem on November 2, 2026, as the development and demonstration case. The prompt, checks and reference were tuned on it, so it can never be the final test.

## The papers inspire the agent, and do not specify it

The aim of selecting among causal theories through experiments comes from Camuffo, Gambardella and Pignataro. The stages, minimums and guards are this project's own design, so public writing says "inspired by", never "implements". The differences are listed in `reviews/guard_changes/README.md`.

## Structure: the harness fixes order, the model decides content

Adopted November 2, 2026. The harness sets the stage order and minimum work. The model chooses what to search, which theories to hold, what to test and what the evidence means. Constraints may reject what does not exist. They must not choose evidence, repair an argument or write a missing theory, because that would supply what is being measured. Every refusal is logged, and the harness repairs nothing.

## No Bayesian network or belief ledger in this pilot

Decided November 2, 2026. Hatem asked for Bayesian updating if applicable. A full network would need an invented structure and probabilities. A harness-calculated ledger was proposed, and Codex argued against it, because assumed ratios could create the apparent revision we want to measure. Instead the model rates each theory on a five-point scale (very unlikely, unlikely, uncertain, likely, very likely) before and after new evidence. That is a within-run signal, not a calibrated probability. A ledger could be studied later as a separate treatment.

## Two theories, and a test only when warranted

Agreed with Codex on November 2, 2026, before freezing. Two distinct theories are the minimum and a third is optional, because the source paper compares a theory with an alternative. A model may decline a test with a reason, because committing without research can be right. Each case declares in advance whether more information is worth its cost. These are study design choices, not rules from the paper.

## Proposed: a Socratic coach

Hatem asked on November 2, 2026, for an agent like Socrates that coaches by asking questions. **Not designed yet.** It only asks and never answers. It could act inside an investigation, for example when the model loops, and in the Strategy Lab to coach the person. Inside an investigation it is part of the treatment, so it must run identically in every arm, must not supply theories, evidence choices or interpretations, and must be frozen before the final test. Its questions count as harness actions.

## 2026-11-03: the final test is frozen before more teacher data

The final test is four held-out companies, eight cases: Electrolux Professional, Aquaporin, Simonelli and RATIONAL.
RATIONAL was added to training the same day, then moved to the final test before any teacher run touched it,
because it is the same industry and mechanism as Electrolux Professional and Simonelli (professional food-service
equipment offered to home cooks). Keeping it in training would have let the final test reward a near copy.
Its case is also one where no test is warranted, which the final test lacked.

`strategy/freeze.py` digests the held-out cases and all 76 of their evidence records into
`docs/final_test_freeze.json`. The tests fail if that digest changes, if a development case can see held-out
evidence, or if a company is on both sides. No held-out case id appears in any teacher report, episode log or
row file on the cluster (checked 2026-11-03). Hellberg is development, not unseen: its loss chose the checkpoint.
Changing the final test needs a new freeze, recorded here with the reason.

## 2026-11-03: first paired pilot, and two repairs before the second

Development pilot, not a test: 10 cases from two companies (5 Moldex, 5 Hellberg), the same bf16 GGUF, controller,
prompt, tools, budgets and settings in both arms; only `--lora` differs. Base: 1 of 10 finished, mostly stopped by
repeating accepted calls early in the investigation. First adapter: 0 of 10 finished. 8 runs never left the reading
stage: the model kept searching after the budget refusal. 2 Hellberg runs reached position or revision and then hit
the context limit. Reports are in `tooling/real_model/strategy/pilot1/`. Hellberg chose the checkpoint, so it is
not unseen.

Repairs, applied identically to every arm from now on:
1. **The search count.** Each search result said `searches_left` including the search held back for
   `challenge_theory`, so at "1 left" the next search was refused. The teacher hit this 30 times and the student
   learned the habit without the recovery. The guidance now reports `searches_left` without the held-back search, plus
   `kept_for_challenge`. Guidance is added when shown and is not part of the recorded result, so recordings still replay.
2. **Stage coverage.** Rows over 8,192 tokens are refused, and full history kept only 17 of 53 conclude rows (32%), with
   update at 56% and position at 71%. The compact state now carries theories, assessments with quotes and limits, tests
   and revisions in full. Built compact, every row is kept (conclude median 4,674 tokens, maximum 5,640), and no target
   names an id missing from its context, measured by `tooling/row_coverage.py` in `row_coverage_first.json`.
   The second pilot trains on compact rows and runs every arm compact.

## Proposed 2026-11-03: specialist adapters, tested one at a time against the shared adapter

Idea (Hatem, with outside review): one Tiny Aya base with separate LoRA adapters for problem framing, theory work and
experiments, chosen by the controller per stage. Not assumed to help: each step is a comparison against the shared
adapter on the same source investigations, company split, harness, prompt and inference budget, with training compute
reported separately.

Checked before planning:
- llama.cpp b12032 holds several adapters and switches per request with no carry-over (two adapters loaded, base output
  restored exactly after a switch). `strategy.run --lora-route default=0,test=1` routes by stage, and
  `tooling/train_pilot.py --stages test` trains and validates a specialist on one stage's rows.
- Data is thin per specialist. From the 45 accepted episodes, compact: problem 90 rows (45 framings), theory 881, test
  stage 121 rows but only 45 are test designs, conclude 53. No episode declines a test, so a specialist trained now
  would learn that a test is always warranted. The first declines come from the no-test companies now in the queue.
- The "12 of 12 framed" figure is an old mechanical check on the untrained model, not a framing quality score.
- The compact state hands every stage the theories, predictions, quoted assessments, tests and revisions in full, so a
  specialist does not work from a short summary. It does not recover dropped rows by itself; compact building did that.

Order:
1. The shared compact adapter (second pilot) is the comparison.
2. An experiment specialist, trained on test-stage rows only, after the new teacher batches add declined tests.
3. Shared against shared-plus-experiment, two ways: full investigations, and test-stage prefixes, where each arm
   continues a held-out-company teacher episode replayed to the test stage. The prefixes separate test-design quality
   from earlier failures, which today stop most runs before the test stage.
4. Problem and theory specialists only if step 3 justifies them.

Responsibility: revision after a simulated result goes back to the theory adapter, and the conclusion stays with the
shared adapter unless a comparison shows otherwise.

## 2026-11-03: second paired pilot, compact in both arms

Same 10 Moldex and Hellberg cases and bf16 runtime as the first pilot; both arms run compact, and the adapter learned
from the same 45 teacher investigations built compact, so no rows were dropped (held-out loss 0.92 to 0.689, best at the
last step). Base: 0 of 10 finished, every run stopped in the evidence stage after about 7 calls. Second adapter: 1 of 10
finished, 6 reached theory building or later, mean 31 calls. Reports are in `tooling/real_model/strategy/pilot2/`.

The dominant failure in both arms is new: repeating an identical search after it was refused (41 of the base's 41
refusals, 67 of the adapter's 113). In compact mode the context after a refusal is almost the one before it, so at
temperature 0 the model writes the same call again, although the state lists what it already tried. The adapter still
searches into the held-back challenge search (33 refusals) despite the corrected count.

Test-stage prefixes, on the laptop's Q4 model, 6 Hellberg teacher prefixes: base proposed a test and left the stage in
5 of 6, the second adapter in 2 of 6; it went back to reading sources. Test-stage teacher rows are mostly reading and
assessing (76 of 121), which is a likely cause. Small, one company, Q4: a warning, not a conclusion.

No trained model is yet shown to investigate better. The second adapter is the strongest trained one and is the live
model in the Strategy Lab, labelled as a development model.

## 2026-11-03: 200 investigations, validated on six companies never trained on

Hatem's goal: about 200 accepted teacher investigations to train from, and evidence that the agent generalises.
Splits are by company, in `strategy/splits.py`. Validation is six companies never trained on: Hellberg, Neumann, Jotun,
Tanita, Deere and ACR, across six industries and including a case where no test is warranted. They set the held-out
loss, choose the checkpoint, and are the cases for every development eval and prefix test from now on. The two pilots
so far scored Moldex, which the model trained on, so they measure fitting, not generalisation. The final test stays the
four frozen companies, opened once. A gap between training-company and validation-company results is read as
memorisation. The same six are the companies in the Strategy Lab demo, so what is tried there is unseen.

## 2026-11-03: how results are worded, after outside review

- Training data is "provenance-verified, replay-valid teacher demonstrations". Replay proves authenticity and tool
  consistency, not that the teacher's theories, tests or recommendations are good.
- "No validation-loss increase observed over two epochs" on the validation rows, not "no overfitting". Validation loss is
  reported per company and as an unweighted company mean, which now chooses the checkpoint.
- Rows are counted as candidates, length refusals and rows used, for training and validation separately. The first run's
  101 refusals were 73 training rows (30 of them conclusion rows) and 28 validation rows; it trained on 902 of 975
  candidates and validated on 142 of 170. The second used all 975 and 170.
- Prefix results describe performance from a supplied teacher history. They locate weaknesses and cannot show that the
  student reaches that stage, or forms those theories, on its own.
- A converted adapter is checked numerically against its PEFT original in every eval job before results are read.
- "Got further" is replaced by `strategy/progress.py`: highest stage completed, refused and repeated calls, sources read
  and used. The pilots are inconclusive: 1 of 10 against 0 of 10, reversed between pilots.
- The defensible claim today: the pipeline learns teacher responses, and compact state prevents length-based exclusions.
  Improved autonomous strategic investigation is unproven.
- The next experiment is the recovery-data pilot in `docs/RECOVERY_PILOT.md`, compared with the second adapter before
  the full batch, once Hatem and Codex approve it.

## 2026-11-04: two teachers on 40 GB slices, one with a smaller thinking budget

gnode04 cannot run our programs (compute nodes allow-list binaries; a downloaded build gets "Operation not permitted"),
and gnode02's 80 GB slice is held by other users' CPU use until about 15:05 on 5 November. Command A+ therefore runs on
two 4g.40gb slices on gnode03, sharing the queues. Measured on a 40 GB slice with 4 slots: 19 tokens per second reading,
1.4 per second writing per slot. To speed collection up, the second teacher uses a 512-token reasoning budget instead
of 1024. Which batches used which budget is fixed by their file prefix: `cap9_*` (job 737962) used 1024, `cap8_*` (job
737966) used 512; every earlier prefix (`cap1` to `cap5`) used 1024. Acceptance, guards and progress are compared by
prefix before the final build; if the 512 batches are clearly worse, they are reported and can be excluded. The data
cutoff is no longer fixed: collection continues until about 200 accepted investigations or until the schedule needs
training to start.
Update, 21:25: on investigations the 1024-budget teacher finished none of four in 90 minutes (single turns of about
1,150 tokens at 1.5 per second, about 13 minutes each), while the 512-budget teacher finished three of four in 103
minutes, each with two rival theories, a discriminating test with a threshold, and a reasoned revision where a what-if
applied. Both teachers now run at 512 (`cap8_*` and `cap6_*`). Every manifest entry since then records its budget.

## 2026-11-05: teacher prompt v2, after a substantive review of seven accepted investigations

Seven replay-valid teacher investigations (Masimo, Statitrol, Gore, Nalgene, Tupper, SIGVARIS, Technogym) shared three
judgement flaws: evidence of a product, price, certification or marketing line scored as support for a customer
motivation; tests that contrast messages and measure stated intent; and occasionally a weak rival theory. Replay proves
authenticity and tool consistency, not quality. Masimo's base investigation is excluded from training
(`data/review/excluded_episodes.json`, with the reason); its original stays recorded.

The teacher prompt is revised to `teacher-v2` (`src/strategy_agent/common/constants/prompts.py`): numbers presented as
observed must come from a source while proposed design numbers are allowed when labelled; predictions must differ
between rivals under the same conditions (no blanket metric ban); each rival needs a credible mechanism and bearing
evidence; evidence direction is judged against a specific claim, distinguishing capability, motivation, purchasing
behaviour and value capture; tests explain why they distinguish mechanisms, name alternative explanations and prefer
consequential behaviour without requiring it. The shared number rule changes in the student prompt too. Every new
manifest entry records `prompt_version`; earlier demonstrations keep their original version and protocol id.

The third-adapter comparison keeps its frozen dataset (episodes collected before v2, minus the Masimo exclusion) so it
still measures the effect of more data. A screener from the judge package will flag substantive weaknesses with recorded
reasons; a high score is not proof of correctness, and valid investigations need not reach the same recommendation.
Known limitation: historical cases include sources written after the decision date (flagged in each record); they can
reveal outcomes, so hindsight is not evidence that a recommendation was right, and the screener is asked to flag its use.

## 2026-11-05: conversion gate measured against the no-adapter baseline

The second adapter's conversion check (eval job 738581) failed only on the absolute rule "top-10 log-probability gap at
most 0.15": worst gap 0.245, with the first token agreeing on 8 of 8 prompts and 25.2 of 32 greedy tokens. The check also
measures each prompt with the adapter off, and the base model alone, with no adapter, differed by up to 0.19 between
Transformers and llama.cpp at 4K-token contexts. An absolute 0.15 therefore failed the base conversion itself and
measured kernel differences, not the adapter conversion. The adapter's own effect was 7.9 to 19.3 on the same scale.

New rule, before any evaluation result exists: on each prompt the converted adapter may add at most 0.15 to that
prompt's gap without the adapter (worst observed: 0.074), and no gap may exceed 0.5. The first-token, greedy-agreement
and adapter-effect rules are unchanged. This loosens a gate after it failed, so it is recorded here, the failing JSON is
kept at `runs/eval/val_second_conversion.json` on the cluster, and Codex is asked to review it before the freeze.

The third adapter's job (738584) crashed with a division by zero because its correction share was set to 0 for the
data-quantity comparison; a share of 0 now means teacher rows only.

## 2026-11-05: data-quantity diagnostic, and targeted corrections

The third adapter (82 accepted investigations, frozen report list `rows/third_reports.txt`, no corrections) failed the
conversion gate narrowly (mean greedy agreement 23.4 of 32 against 24; one prompt added 0.158 against 0.15; first token
8 of 8). Its validation run was made as a labelled diagnostic (`DIAGNOSTIC=1`), which selects nothing. On the 15
validation cases, one attempt each, mechanical measures only: the second adapter finished 2, stopping otherwise in
theories (10), assessment (1) and conclude (2); the third finished none, stopping in theories (8) or looping in the
test stage after completing the challenge (7, all 117 of its test-stage repeats). This does not show that more data
improved completion, and with conversion unresolved it cannot show that the larger dataset made the agent worse.
Recovery from loops is a plausible remedy, not a proven one.

Codex is asked to diagnose the conversion (a real error against greedy changes at near-ties) and to set tolerances
that apply to every adapter, the second included, with the 2026-11-05 baseline-relative rule under review. Test-stage
correction states come only from the third adapter's runs on 24 training-company base cases; no validation trajectory
becomes a demonstration. The schedule is unchanged: v2 collection continues, then conversion, targeted corrections and
the final training by Saturday 7 November, 18:00 CET.

Test-stage corrections: each state carries the student's adapter and runtime identity, including the failed conversion
check, because the loop may come from training, conversion or their interaction. A correction from a test-stage state
counts only if it proposes a test with different predictions for at least two theories, a numeric decision rule and a
why_next that names the theories it separates, or declines a test with a reason; a valid, non-repeated call alone is
refused. No further batch is collected to reach a count: the final run uses the valid corrections available and reports
their actual share of supervised tokens. Once Codex resolves conversion, the same check is applied to the second and
third adapters; if a real conversion bug is found, the repaired third adapter is re-run on the existing development
cases before its earlier behaviour is interpreted. The latest training start stays Saturday 7 November, 18:00 CET.

## 2026-11-05: the compact state lists reads, and says an excerpt is everything the dossier holds

The 16 test-stage correction states were answered by Command A+ (batch correct5): 14 replies re-read a source, 9 of them
exact repeats. Only 1 of 16 passes the test-stage rule (kes: a discriminating test). In the festool state the teacher
reasoned that a 93-character excerpt "only shows a snippet; its full content may reveal" more, and read it again. 602 of
1,334 dossier excerpts are under 150 characters; rereading is free and unmarked in `read_source`; and the compact
state's `already_tried`, the list the prompt says not to repeat, held searches and challenges but never reads. Teacher
rows teach the loop little: 51 of 2,083 training rows are rereads, 2 of them in the test stage. The teacher's stated
reason and the short-excerpt counts make the interface a plausible contributor to the loop. They do not measure how
much it contributes, and they do not show that training or corrections cannot help.

Change, Hatem's choice of three options: only the compact state changes. `already_tried` now includes `read_source`
calls (the last 12 entries instead of 8), and a `sources_note` says each excerpt in `sources_read` is everything the
dossier holds for that source. Tool results are unchanged, so all 114 collected teacher episodes still replay
(checked), and the running teachers, whose prompt shows full history rather than the compact state, are unaffected.
Training rows and every later evaluation, both arms, use the new state; correction rows rebuild their context by replay
in the same format. The longest compact row was 5,890 tokens against the 8,192 limit, so the few added entries fit; the
training job's row-coverage gate checks this again. Earlier development results were made under the old state and are
not compared directly with later ones. Codex reviews this as a protocol change before the freeze.

Wording: an excerpt is everything the dossier holds for a source, not the whole original source; `SOURCES_NOTE` says
exactly that, and the commit title of ebdeca7 ("the whole source") is imprecise. The change removes an observed
ambiguity; it is not shown to reduce loops, and the next matched evaluation measures that. Short excerpts still limit
what an investigation can establish: making their completeness clear stops futile retrieval but supplies no missing
context and justifies no stronger conclusion. Results made before ebdeca7 (the second-adapter and third-adapter
development runs, protocol d8c0295994fd, and the 24 training-company student runs) are kept as a separate protocol
version; the runner's protocol id changes with the state, so later runs are told apart automatically. The final rows,
the correction contexts and both arms of every later evaluation use the new state. Surviving corrections are used even
if their share of supervised tokens falls well below 20%, and the training report gives the actual share.

Corrections asked before ebdeca7 (Codex's review of ebdeca7, option a): the teacher answered the old state, so its
reply is not turned into a row under the new one. `corrections rows` now keeps a correction only if the context the
teacher was sent equals the context replay gives today, and skips any other. The 23 corrections that survive the
current judge (12 from cap8_correct0, 10 from cap9_correct1, 1 from correct5) are asked again on the new state as batch
correct6, first in the queue; the queued batches correct2 to correct4 were rebuilt in the new format before any
teacher took them (originals in `queue/states/old/`). Old replies and their manifest entries stay as they were. New
corrections should also bind the exact outgoing request when #25's source bindings are ported; the old ones lack it.

## 2026-11-06: training data accounting before the freeze, and when the final run starts

Built at 12:40 with the training job's own steps (code 20d3610, compact state of ebdeca7) from the 49 teacher reports
and 7 correction files on the cluster, while collection continues:

- 158 replay-accepted investigations: 142 from training companies and 16 from validation companies (hellberg 6, and 2
  each from tanita, neumann, deere, acr and jotun). 27 did not replay to an accepted finish and Masimo is excluded on review.
- 3,895 teacher rows: 3,484 from 58 training companies and 411 from the 6 validation companies, which are used only for
  the company-balanced validation loss. None comes from the 4 frozen final-test companies (aqp, epro, rational, simo).
- Corrections: 80 provisionally kept replies, of which 51 become rows; none is from a validation company. The rest
  failed re-judging (6, all test-stage) or were asked under the old state and re-asked as correct6 (23). No test-stage
  correction survives: 49 rows are in theories, 1 in assessment, 1 in conclude.
- Supervised tokens, training companies only (validation rows excluded): 354,220 from the 3,484 teacher rows and 1,251
  from the 51 corrections, so 0.35% of training tokens (1.44% of training rows). Each correction
  is used once; none is duplicated to approach the 20% budget.
- Gates: row coverage (compact) refuses 0 rows for length and finds 0 targets naming something missing from their
  context; the longest row is 6,011 of 8,192 tokens. Every row passes the loss-mask prefix check. The split test
  passes. The model-level masking gate (`training/masking_gate.py`) passed in the pilots and is not re-run; the
  training job's overfit gate runs before the full run.

Collection closes when the queued batches are done (about 03:00 on Saturday): replacement teachers take over when the
running ones reach their 22 hours. The final training (NAME=final, code 20d3610, compact rows, 2 epochs, checkpoints
every 50 steps, corrections capped at 20%) then starts by Slurm dependency, with no further pilot or collection target,
and the job's decisions and coverage files record the frozen report list and final counts. Conversion stays separate:
it must be resolved before converted-model evaluations are interpreted or that format is released, not before
training. If it is still unresolved at evaluation time, the PEFT adapter is evaluated against the base in the same
Transformers runtime, if that fits the schedule, and the converted demo stays labelled as unverified.

Submission: the final training is submitted by Slurm, not by a chat session. The replacement teacher 741931
(`~/lexsi/teacher_then_train.sbatch`, behind 740314) submits it when it finds the queue empty, with a dependency on the
other replacement 741924 if that still runs. A check from the login node submits it earlier if a job slot opens, with
dependencies on both. The marker `rows/final.submitted` records the job id and stops a second submission. Submitting
from inside a compute-node job is not yet tested on this cluster.

Submitted: job 742209, from the login node at 15:48:49 on 2026-11-06, with `--dependency=afterany:741924:741931`, so it
starts when both replacement teachers have emptied the queue. Before that, the gnode01 teacher (739879) hit its Slurm
time limit at 15:38 partway through batch again1, which went back to the front of the queue; its partial episodes
wrote no report, so nothing is counted twice.

What the run tests: mainly more teacher demonstrations (142 training-company investigations against the third adapter's
72; its 82 accepted included 10 from validation companies) together with the clearer compact state. Corrections are 0.35% of training tokens and none is from the test stage,
so it is not a substantial test of recovery training, and its results are not presented as one.

## 2026-11-06: two blind judges, Claude through the API and Codex

PR #24 (judge-v1: nine-dimension rubric, prompt, six anchors, 40-packet blinded qualification set, 14 offline probes
passing, hashes matching `config_v1.json`) is merged. Hatem chose the two judges: Claude through the existing API key,
which is approved for judging only and capped by the spending ledger, and Codex (OpenAI, through the Codex CLI on
Hatem's ChatGPT account). Neither is the student or the teacher, as FINAL_EVAL_PLAN requires. An earlier version of
this entry (289cee4) said one judge; it was written before Hatem's answer was complete and is superseded.

Codex wrote the rubric, the anchors and the qualification set with its answer keys. So the Codex judge is a fresh,
isolated run that receives only the judge prompt and one packet: no repository, no keys, no session memory. The same
applies to Claude. Each judge must pass the qualification set under `config_v1.json`'s rule before it scores any
evaluation episode, with its exact model id and settings recorded. Arm names are removed and packet order is
randomised. Each judge is reported separately, with their agreement. Judge output never selects or filters training
data.

The question the evaluation answers: under the same new compact state, does the trained agent produce better
investigations than the base, judged on credible, distinct causal theories (causal_mechanism, distinct_theories),
evidence that supports the specific claim made (evidence_judgement), tests that distinguish those theories
(experiment_design), and justified revisions and recommendations (revision, recommendation), alongside the mechanical
progress measures. The claim follows the results.

## 2026-11-06: how a judge qualifies for evaluation scoring (written before it is computed)

The Claude judge (claude-opus-5-5) ran the 40-packet qualification under config_v1 and is `not_qualified` there: 20 of
20 flawed packets rejected, 9 of the 12 sound packets with valid output accepted, and 8 outputs invalid (7 calling a
trajectory suitable for training while listing a critical red flag, 1 API error). That rule qualifies a training-data
screener on a binary suitability decision. Evaluation uses only the 0 to 3 dimension scores, so Hatem chose a separate
rule for scoring, recorded here before anyone computes it for any judge:

- For scoring, an output is valid if its response parses as JSON and its dimension block passes judge.validate's
  dimension checks: every dimension present, status scored, not_reached or not_applicable as the packet's applicability
  requires, integer scores 0 to 3 only when scored, event ids that exist in the packet, a reason for each. The screening
  fields (suitable_for_training, red_flags, screen_reason) are ignored for scoring.
- An invalid output is retried once, the retry recorded beside the original. After the retry, at most 4 of the 40
  outputs (10%) may be invalid.
- A packet's score is the mean over its applicable dimensions, with not_reached counted as 0.
- Each of the 20 clusters pairs a sound and a flawed version of one case. The judge qualifies for scoring if the sound
  version scores strictly higher in at least 17 of the 20 clusters. A tie, or a cluster with an invalid output, counts
  as a failure.
- The frozen config_v1 screener rule is unchanged and still governs any use of a judge as a screener. No judge
  screens training data.

## 2026-11-06: six investigations at once on the second replacement teacher

To try to speed up collection, Hatem chose to run the second replacement teacher with 6 parallel slots instead of 4 (a
smaller teacher quantisation was ruled out). With most of Command A+ in node memory, a step's cost is dominated by
reading the weights, so more slots may raise total throughput; more KV cache could instead push layers to the CPU, so
it is measured, not assumed. Because a batch's investigations run in parallel and most batches hold 4 cases, that
teacher (job 742354, replacing 741931 and 742352 before they started) takes merged batches first from its own queue
`teacher_six.txt`: six0 (again4 and again6), six1 (again5 and again10), six2 (again7 and again11) and six3 (energyagain0
and energyagain1, 8 cases). Then it falls back to the shared queue, which keeps 6 four-case batches for the 4-slot
teacher 741924. The original queue is kept at `queue/old/teacher_later.before-six.txt`. Teacher settings, cases and
seeds are unchanged; the server records its slot count in every manifest entry. The final training (742209) now
waits on 741924 and 742354. If 6 slots turn out slower, the remaining six-case batches go back to the shared queue and
the next teacher uses 4.

Qualification results (2026-11-06). Claude (claude-opus-5-5): qualified for scoring, with 19 of 20 clusters ordered and
1 of 40 invalid after one retry (a response cut at max_tokens). Not qualified as a screener: 20/20 flawed rejected,
9/12 sound accepted, 8 invalid screening outputs. Codex (gpt-6-astra, codex-cli 0.166.0, an isolated ephemeral
read-only run per packet): qualified both as a screener (20/20 sound accepted, 20/20 flawed rejected, no errors) and
for scoring (20 of 20 ordered, 0 invalid). Its run was interrupted twice by the ChatGPT usage limit and once by a
failed cloud-config fetch; those infrastructure failures were archived (`results/codex_archived_*`) and only they were
judged again, never a valid judgment. Caveat for the report: Codex wrote the qualification packets and keys. Each judge
call saw only the prompt and the packet, but a judge may still score its own author's examples more consistently, so
the qualification is weaker evidence for Codex than for Claude. Neither judge screens training data.

Six slots, outcome (2026-11-06, 22:30): withdrawn. The six-slot teacher (742354) finished six0 (6 investigations, 5
finished) and was then killed for running out of memory during six1: the 135 GB model held in node memory plus six
slots of context exceeded the job's 200 GB limit. six1 produced no episodes and its report holds no records, so
nothing from it enters the rows. six1 and the unstarted six2 and six3 went back to the shared queue as their original
4- and 2-case batches, and a 4-slot replacement teacher (742871) was submitted. The final training (742209) now waits
on 741924 and 742871. Correction: the 7.4 and 7.7 tokens per second per slot I reported for the six- and four-slot
teachers came from the prompt-reading lines of the server log, not generation. Generation is about 1.2 to 1.3 tokens
per second per slot in both, so the "about 40% more output" figure was unsupported, and no speed-up was shown.

## 2026-11-06: conversion gate v2, from the diagnosis (registered before the final adapter exists)

Codex's read-only diagnosis (job 742630, code 12fdae7, greedy set explicitly in both backends) on the second and
third adapters, 8 prompts each: the converted adapter reproduces the PEFT adapter's effect over the full 262,144-token
vocabulary with effect cosine 0.9975 or more (mostly above 0.9999), and the probability-weighted residual is at most
0.142. Rounding the PEFT factors to BF16 leaves that residual unchanged, so factor precision is not the cause; the
remainder is backend arithmetic. With the adapter off, the base alone diverged between Transformers and llama.cpp on 4
of the third adapter's 8 prompts. Where adapted greedy traces parted, PEFT's top-1/top-2 margin was 0.0 (second
adapter), 0.125 and 0.75 (third), against 12 to 14 elsewhere; several earlier 'disagreements' were one side stopping
at an end token. No conversion defect was found. A near-tie flip can still change a trajectory, so converted-model
results are read with that caveat.

Gate v2, for every adapter (the second and third included): on every replayed point, effect cosine at least 0.99 and
probability-weighted effect residual at most 0.15; the tensor audit status `factor_pair_matches_expected_cast`. Greedy
divergences are reported with their margins and with whether the base alone diverges on the same prompt, and do not
by themselves fail the gate. These thresholds were proposed after seeing the second and third adapters' diagnostics
(both pass) and are fixed here before the final adapter exists; Codex reviews them. The final adapter gets the same
diagnosis inside the training job, on its GPU, right after training. Gate v1 (fe0db0a and its predecessors) is retired.
Applied: the second adapter passes gate v2 (9 points, lowest cosine 0.9997, largest residual 0.073; one greedy
divergence at PEFT margin 0.0) and so does the third (12 points, 0.9975, 0.142; one divergence at margin 0.125, on a
prompt where the base alone also diverged). Results: `reports/conversion/{second,third}_gate_v2.json`. The final
training was resubmitted as job 742970 (replacing 742209 before it started, same dependencies on 741924 and 742871)
so that it runs gate v2 on the final adapter on its own GPU before submitting the evaluations.

## 2026-11-07: final training is job 744559

Collection closed at 14:25: teacher 742871 stopped at 04:47 after its batch again7 failed its check (1 of 4 finished,
the job stops by design), and teacher 741924 ran the rest of the queue, its last batch ingragain2 ending at 14:25.
Job 742970 then started and failed at its first command (`module: command not found`, exit 127): it had been submitted
with `env -i`, which drops the exported `module` function, and the development evaluations it submits use `env -i` too.
Fix bc7bd6c loads `/etc/profile.d/modules.sh` when `module` is missing, in every job script, and changes nothing else.
The final training was resubmitted at 14:36 as **job 744559** with the same settings (NAME=final, REVISION=20d3610,
GATE_REVISION=bc7bd6c, COMPACT=1, ROW_PROMPT=compact, EPOCHS=2, SAVE=50), no dependency, without `env -i`. It built
4,302 rows, 51 of them correction rows, from 54 teacher stage reports; the accepted-investigation, token and
coverage counts are recorded at the freeze.
Job 744559 finished training at 19:14 (1,971 steps, two passes; best held-out loss about 0.713 at the last checkpoint,
which is the adapter kept) and submitted the three development evaluations: dev_final 745203, dev_second_newstate
745204, dev_base_staged 745205. Its gate v2 step did not run: the diagnosis was called with `NAME=${NAME}_final` before
`REFERENCE_REPORT=...${NAME}...` on one line, and bash expands prefix assignments in order, so it looked for
`final_final_gate_check.json`. The conversion check itself (`final_gate_check.json`) and the converted adapter exist,
so the diagnosis runs on its own as job 745209 with the right paths, and gate v2 is applied to its output. The step
is fixed in the job script (paths computed before NAME changes) for any later run.
At 19:25 the cluster home reached its 50 GB quota (50.5 GB used), and 11 of the 15 base-arm episodes of dev_final
failed in the harness with `Disk quota exceeded`; the other four and the adapter arms ran on a full disk. Those runs are
invalid and were moved, not deleted, to `runs/eval/invalid_quota_20261107/`; 745203 and 745204 were cancelled. With
Hatem's approval the unused Aya Expanse 32B teacher model (19.8 GB, replaced by Command A+; its provenance is kept at
`runs/aya-expanse-32b-Q4_K_M.provenance.removed-2026-11-07`) was deleted, leaving 30 of 50 GB used. The final adapter
had been written at 19:14 and is complete (504 tensors, size matching its header). The evaluations were resubmitted
unchanged: dev_final 745247, dev_second_newstate 745248; dev_base_staged 745205 and the diagnosis 745209 had been held and then released. Final held-out loss 0.7125 (epoch 1.999).
Gate v2 on the final adapter (diagnosis 745209, applied on the laptop with conversion_gate.py): **passed**. 11 points,
lowest effect cosine 0.9990, largest probability-weighted residual 0.080, tensor audit as expected; one greedy
divergence (hellberg-new-evidence-irrelevant, theories stage, offset 21) where PEFT's top-two margin was 0.0 and the
base alone also diverged. Result: `reports/conversion/final_gate_v2.json`. The development evaluation of the converted
final adapter is therefore readable; its outputs still carry the DIAGNOSTIC marker from the retired v1 gate.

## 2026-11-07: development judging, and the Claude judge's output limit

The blinded development packets were built from the four development arms (base_compact, base_staged, second, final;
15 runs each): 56 distinct packets for 60 runs, four base runs being identical. The key is kept outside the repository
while the judges run. Both judges run under the evaluation-scoring qualification (`run_campaign.py` now accepts
`qualified_for_scoring`, the rule registered on 2026-11-06, as well as the stricter screener status).
The first Claude attempts failed: once on a missing `anthropic` module (system Python; no call was made), then five
packets ended with `max_tokens` (cost USD 0.29), because evaluation packets are longer than the qualification ones.
Claude's output limit is raised from 3,000 to 8,000 tokens (`backends_v1.json`, version judge-v1-two-backends-2) before
any development packet was scored. Nothing else changes; every qualification judgment finished under 3,000 tokens
(largest 2,728), so the qualification result is unaffected. The failed attempts are archived, not reused.

## 2026-11-07: development results (6 validation companies, 15 cases, one attempt each)

Both judges scored all 56 packets validly (0 invalid, 0 missing). Episode score: mean of the applicable dimensions,
0-3, not_reached counted 0. They agree closely on ordering (Spearman 0.95 over 60 episodes, mean absolute difference
0.27); Codex scores higher throughout.

| arm | finished | Claude | Codex | mean of judges |
|---|---|---|---|---|
| base, compact prompt | 0/15 | 0.12 | 0.16 | 0.14 |
| base, staged prompt | 0/15 | 0.35 | 0.52 | 0.43 |
| second adapter, compact state | 6/15 | 0.88 | 1.31 | 1.09 |
| final adapter, compact state | 7/15 | 1.09 | 1.49 | 1.29 |

Paired differences, mean of judges, 95% case-cluster bootstrap: final minus base compact +1.15 [0.87, 1.42]; final
minus base staged +0.86 [0.61, 1.11]; final minus second +0.20 [-0.09, 0.53]; base staged minus base compact +0.30
[0.18, 0.42]. Each judge alone gives the same signs and the same intervals' relation to zero. Read: on these
validation companies the final adapter scores clearly above the base model under either prompt, and is not
distinguishable from the second adapter. 15 cases from 6 companies, one attempt each; Jotun shows almost no gain
(+0.21). Claude judging cost USD 4.46 (ledger 9.75 -> 14.21). Reports: `reports/judge/dev/`.

## 2026-11-07: choices from development, and the freeze

**Choices** (FINAL_EVAL_PLAN rule: higher mean blind-judge score on the validation cases, completion breaking a tie):
- Base prompt for the final test: **staged** (mean of judges 0.43 against compact's 0.14).
- Trained arm: **the final adapter** (`runs/final_pilot/adapter`, job 744559, gate v2 passed; mean of judges 1.29
  against the second adapter's 1.09). The second adapter is not used.

**The final test campaign, frozen here before any final-test output exists:**
- Cases: all 8 in `data/dossier/cases_heldout.json` (aqp, epro, rational, simo; base and irrelevant-evidence each). PR #23
  is not merged, so its packets are not included. The held-out digest matches `docs/final_test_freeze.json`, and no
  training row (`rows/final.jsonl`, 4,302 rows, 63 companies) mentions a held-out company.
- Arms: base = Tiny Aya bf16 GGUF, staged prompt, no adapter; trained = the same GGUF with the final adapter, compact
  prompt. Same llama.cpp build, context 12,288, 520 tokens per turn, 45 turns, 4 errors in a row, temperature 0
  (0.4 only on a retry straight after a refused call).
- Three attempts per case and arm (attempts 0, 1, 2; `ATTEMPTS=3` in `jobs/eval_adapter.sbatch`), 48 runs. Runner code
  revision 20d3610, the same as development.
- Infrastructure retries only (harness or server failure, same seed, at most twice, logged); never for model behaviour.
- Judging: the judge-v1 package, backends version judge-v1-two-backends-2, both judges under the scoring
  qualification; packets by `judge_packets.py` (seed 20261106), key kept outside the repository while judging; report
  by `judge_report.py`. Primary result: trained minus base, mean of the two judges, paired by case and attempt, 95%
  case-cluster bootstrap; each judge separately, each company separately, all missing runs. Negative controls:
  `fixed_policies.py` on the same cases. Mechanical measures from the runner summary.
- Claim wording as in FINAL_EVAL_PLAN: at most "on four companies it never saw ... scored X against the prompted
  base's Y under a blind LLM rubric", with per-company results; four companies support only a limited claim.
After this entry nothing in the campaign or its analysis changes.

## 2026-11-07: correction (Codex's review), and the freeze is not yet in force

- **My claim was wrong.** I wrote that every Claude qualification judgment finished under 3,000 tokens and that the
  qualification is therefore unaffected by raising the limit. One qualification packet (0e3184f1b3aa2234, sound q09) hit
  `max_tokens` on both its first call and its retry; it was the one invalid output in the receipt. The claim held only
  for the outputs that finished. The same wrong sentence is in the `max_tokens_change` note of `backends_v1.json`; that
  file is left unchanged because its digest binds the Claude development judgments and the requalification, and this
  entry is the correction. The old receipt (`reports/judge/claude_score_qualification.json`, under 3,000 tokens) is kept.
- **Claude is requalified** on the same frozen 40 packets under the 8,000-token configuration, with the same rule
  (one retry for invalid outputs, at most 4 of 40 invalid, sound above flawed in at least 17 of 20). Until it passes,
  the Claude development scores are provisional and the choices are not final. Receipts now record the digest of the
  configuration their results were produced under, and `run_campaign.py` refuses a judge whose receipt does not match
  its current settings.
- **The freeze recorded above is withdrawn** until these are closed: the Claude requalification; the held-out scope
  (Hatem chose to include PR #23's supporting and undermining what-if pairs, so the final test has 16 cases and 96
  runs after review, merge and refreeze); the conversion evidence that the evaluated GGUF matches the one gated; and an
  exclusion manifest for the quota-failed runs. No final-test output exists.
- Neither the 0.20 [-0.09, 0.53] final-minus-second interval nor any other development result shows the two adapters
  are equivalent; the second adapter is the specified fallback, not shown interchangeable.
- The 56 packets are the 60 development runs with four identical runs sharing one judgment; every analysis uses all 60
  key rows, and the bootstrap resamples cases, not packets.


## 2026-11-04: reviewed pre-evaluation shock amendment

PR #23 was rebased on the published final-run branch after RATIONAL moved out of training. Its base and irrelevant cases remain, and each of the four held-out companies now also has a matched supporting/undermining hypothetical packet. RATIONAL's packets concern installation coordination among eligible homes; they do not erase physical requirements or the case's no-test-warranted assumption. Its stale split=training tags are corrected to heldout. Sixteen variants remain four company/question clusters and are exploratory. No held-out actor model runs were used by Codex to write or select these packets.

The preceding freeze digest was `a228c6fc694028b458ad528e4d5e3accb6f02ac3798088fbc7776d888035297d`. The deliberately regenerated digest is `dce26d4f11232f74a2d4e4b744a7ebc0c52a9c3cc04bb71f8994ea7f499ee77e` over the same 76 held-out evidence records. Regeneration used `python -m strategy_agent.pipeline.freeze > docs/final_test_freeze.json` in an isolated copy of the current freeze module/data, preserving the shared checkout. This pre-final-run amendment requires review before final evaluation; it adds no training data and grants no teacher or publication permissions. Prior freeze records remain in Git history.

2026-11-05: ported to src/data layout on main29c91f1. Packet bytes and the recorded content freeze digest are unchanged; no actor outputs inspected.

## 2026-11-07: the freeze (supersedes the withdrawn entry above)

Closed before the freeze: Claude requalified under the 8,000-token configuration on the frozen 40 packets
(`reports/judge/claude_score_qualification_8000.json`: sound above flawed in 20 of 20 clusters, 0 invalid, no retry
needed; bound to manifest judge-v1-two-backends-2, judge config sha256 14a9fc0e...; cost USD 2.59), so the Claude
development scores stand under the configuration they were produced with. Codex's receipt is re-issued bound to the
manifest its results were produced under (`reports/judge/codex_score_qualification_bound.json`; its settings are
unchanged). PR #23 is merged (16 held-out cases, digest dce26d4f...). The evaluated GGUFs match the gated ones
(`reports/conversion/evaluated_gguf_hashes.json`, compact replay beside it). The quota-failed runs are excluded
(`reports/eval/dev_quota_exclusions.json`).

**Choices, from development only:** base prompt **staged** (0.43 against compact 0.14, mean of judges); trained arm
**the final adapter** (1.29 against the second adapter's 1.09). Not shown equivalent to the second adapter.

**Final test campaign:**
- Cases: the 16 in `data/dossier/cases_heldout.json` at digest dce26d4f11232f74a2d4e4b744a7ebc0c52a9c3cc04bb71f8994ea7f499ee77e
  (per company: base, irrelevant evidence, and a supporting and an undermining what-if result). Four companies.
- Arms: base = Tiny Aya bf16 GGUF, `staged` prompt, no adapter (job NAME final_test_base, SKIP_ADAPTER=1); trained =
  the same GGUF with the final adapter (`runs/final_pilot/adapter`, converted GGUF expected sha256 41794b57...), `compact`
  prompt (final_test_trained, SKIP_BASE=1, DIAGNOSTIC=1 because the retired v1 check still runs and is marked). Both:
  SPLIT=heldout, ATTEMPTS=3 (attempts 0-2), runner code d3aa608 (identical to development's 20d3610 except the split
  option), job script `jobs/eval_adapter.sbatch` at 0377eae, same llama.cpp build, context 12,288, 520 tokens per turn,
  45 turns, 4 errors in a row, temperature 0 with 0.4 only on a retry after a refused call. 96 runs.
- Infrastructure retries only, as in FINAL_EVAL_PLAN: a whole failed job is rerun with the same configuration, logged with
  cause and times; never because of model behaviour; nothing is filled in case by case.
- Judging: both judges under the receipts above, unchanged instrument; packets by `judge_packets.py --split heldout`
  (seed 20261106), key kept outside the repository while judging; `judge_report.py`. Primary result: trained minus base,
  mean of the two judges, paired by case and attempt, 95% case-cluster bootstrap. Also each judge separately, each
  company separately, by evidence direction (supporting, undermining, irrelevant, base), all missing runs, the
  mechanical measures, and the negative controls (`fixed_policies.py --heldout`).
- Claim wording as in FINAL_EVAL_PLAN. Three attempts per case are not independent replications, and four companies
  support only a limited claim about generalisation.
Nothing in the campaign or its analysis changes after this entry.
Final test submitted at 21:00 on 2026-11-07 after Hatem's go: trained arm job 745481 (final_test_trained), base arm
job 745482 (final_test_base), both from `~/lexsi/eval_adapter.sbatch` (0377eae) with REVISION=d3aa608, SPLIT=heldout,
ATTEMPTS=3 and the 16 held-out ids.
Deviation from the freeze, found while the judges ran: `fixed_policies.py --heldout` cannot run on the held-out
cases. Its scripted policies search with fixed hearing-protection queries ('earplugs comfort', ...) and reach the
assessment step with no source read (IndexError on the empty read set), because they were written for the original
earplug cases. The negative controls are therefore not reported for the held-out set; writing a new scripted policy
now would change the analysis after the freeze, so it is not done. The development-case negative controls stand as
recorded before. This affects no model run and no judgment.
Infrastructure failures during final judging (not judge behaviour, handled as in the qualification campaigns): Codex
hit the account's usage limit partway through ("You've hit your usage limit. Try again at 11:38 PM"), so 51 packets
failed before a model turn and one more timed out in the sandbox; 35 judgments are valid. After the reset the failed
attempts are moved to `codex_archived_usage_limit/` (kept) and only those packets are judged again under the same
instrument, packets and receipt. One Claude call ended in an APITimeoutError with no response; it gets the same
treatment after Claude's campaign ends. No valid judgment is redone or replaced.
The first Codex retry (23:41) still met the usage limit: the CLI's "11:38 PM" is an hour behind local time, as with
the earlier 17:33 reset. It was stopped after 16 more failures; those and the two attempts interrupted by stopping it
are archived in `codex_archived_usage_limit_2/`. A retry from 00:45 stops itself on two usage-limit failures, archives
them, and tries again every 30 minutes, at most four rounds. Claude's two connection failures (one timeout, one
connection error) were re-judged validly under the same instrument; its third invalid output (JSON with trailing text)
is the judge's own response and stays missing, since no retry for judge output was declared.

## 2026-11-08: final test result (four held-out companies, frozen campaign)

All 96 runs completed with no infrastructure failure. Codex judged all 87 packets validly after the usage-limit
retries (round 3, 00:43-00:55, 52 of 52 valid); Claude judged 86 of 87 (one judge-invalid output, so one base run,
simo-new-evidence-irrelevant, has no Claude score and is reported missing). The judges agree closely on ordering
(Spearman 0.94 over 95 episodes, mean absolute difference 0.38); Codex scores higher throughout.

Mechanical: base finished 4 of 48 (1 passing every check); trained finished 28 of 48 (1 passing every check).

| | base (staged prompt) | trained (final adapter) | trained minus base, paired, 95% case-cluster bootstrap |
|---|---|---|---|
| Claude | 0.56 | 1.20 | +0.64 [0.51, 0.77] |
| Codex | 0.74 | 1.77 | +1.03 [0.87, 1.18] |
| **mean of judges (primary)** | **0.65** | **1.48** | **+0.83 [0.69, 0.97]**, 47 pairs, 16 cases |

By company (mean of judges): aqp +1.10, epro +0.60, rational +0.66, simo +0.98; every company positive under both
judges. By evidence (mean of judges): base case +0.84 [0.71, 0.98]; irrelevant +0.87 [0.39, 1.33]; supporting
+0.86 [0.68, 1.02]; undermining +0.76 [0.58, 1.01]. Largest dimension gains (Codex): distinct theories 0.98 -> 2.56,
framing 1.00 -> 2.90, causal mechanism 1.15 -> 2.63, revision 0.03 -> 0.81; weakest for the trained arm: recommendation
0.58, revision 0.81, experiment design 1.08, evidence judgement 1.17.

Claim, in the frozen wording: on four companies it never saw, under the same investigation setup, the fine-tuned agent
scored 1.48 against the prompted base's 0.65 on a 0-3 blind LLM rubric (mean of two judges; +0.83, 95% interval 0.69
to 0.97), higher at every company. Four companies support only a limited claim about generalisation; three attempts per
case are not independent replications; 20 of 48 trained runs still stop before a recommendation, and the negative
controls could not be run on these cases (deviation above). Nothing about business outcomes. Reports:
`reports/judge/final/`.

## 2026-11-08: diagnosis of the mechanical failures (post hoc)

`docs/FINAL_TEST_DIAGNOSIS.md`: why 20 of 48 trained runs stop and 27 of the 28 finished ones miss at least one check.
Main causes: no training row ever declines a test (the teacher proposed one in all 15 training cases that warrant
none, and half the final cases warrant none); only 8 of 205 teacher investigations on training companies had
supporting or undermining what-if evidence; finishes citing only the simulated record are refused until the error
limit; rereading sources exhausts the turn limit, mostly on rational. The teacher passed every check in 1 of 223
finished investigations. This is diagnosis only; it changes no result and selects nothing.
Revised after review the same day: the "no test warranted" labels were checked against the cases. For Aquaporin,
declining follows from dossier evidence (withdrawal of its offering, insolvency, bankruptcy order of 2 February 2026)
that no run of either arm ever read; all 11 finished trained runs recommend investing, so the failure is the search,
not a missing refusal. For Rational the label rests on the case author's judgement and is contestable. The teacher's
1 of 223 and the student's 1 of 48 come from different case distributions and show only that all-checks success is
rare in both. The improvement plan is reordered (justified propose-or-decline, balanced directional evidence linked
to the affected theory, recovery from simulated-only citations and from rereading), to be confirmed on development
cases before any new examples are selected; a future claim needs fresh evaluation cases, since these four companies
now informed the diagnosis. The frozen scores stand.

## 2026-11-08: public repository and release policy

At Hatem's request the code is public at https://github.com/HatemSaadallah/lexsi-strategy-agent (Apache 2.0), made by
`scripts/build_public_repo.py` from this repository: no history, no copies of the source papers (`papers/`,
`sources/`), every dossier excerpt cut to its first sentence of at most 25 words wherever it appears (Hatem's policy;
the agent's own exact-sentence quotes stay), and the cluster account, login host and home folder replaced by
placeholders. Its tests pass (206, plus the held-out digest test skipped, since the digest covers the full excerpts).
This repository stays private. The Hugging Face release (`scripts/build_release.py`, same redaction) waits for the team
organisation and Hatem's go.

## 2026-11-08: version 2 registered (`docs/V2_PLAN.md`)

A short continuation of the final adapter on 100-200 targeted single-decision examples (experiment design, belief
revision, evidence judgment, recovery), mixed with existing teacher rows at about 30% of supervised tokens, every target
passing a skill check fixed in code before generation. Development confirmed experiment design (4 of 7 finished runs),
evidence judgment (5 of 7 mislabel kinds) and recovery (3 of 8 unfinished reread); revision on directional evidence
could not be confirmed on development (3 such cases). Version 1 and its final-test result are untouched; a version 2
generalisation claim needs fresh held-out companies.
Revised the same day after an independent critique (a stand-in reviewer, since Codex was unavailable): reduced to
experiment design and refused-finish recovery, budget variants dropped (they cannot replay: `read_brief` returns the
budget), stricter gates on the new item only, a gentler mix (15-20% targeted, learning rate 2e-5 to 3e-5, about 100-150
steps), and a selection rule fixed in advance: 3 attempts x 15 validation cases for both versions, version 2 preferred
only at a mean-of-judges gain of at least +0.10 with a 95% lower bound above 0 and no more than 2 fewer finished of 45.
Timeboxed to three days; development result only. See `docs/V2_PLAN.md`.

## 2026-11-08: the experiment check misreads opposite predictions

Inspecting the version 2 gate on development outputs (Hatem's request) showed that the environment's experiment check
treats opposite comparisons as near-identical predictions, because it compares word overlap. Recounted, 5 of the 6
final-test runs it flagged "predictions barely differ" predict opposite outcomes (development: 1 of 2 and 3 of 4).
The frozen final-test numbers are unchanged and reported as computed; the diagnosis and article now say five of six
predictions-overlap failures involved contrasting predictions the checker treated as identical, which does not
establish that those experiments were otherwise sound. The version 2 gate recognises opposite comparisons (`targeted.mirrored`) and
two-branch decision rules; on development outputs it now keeps 12 of 17 proposals, and the rejections inspected were
identical predictions or rules without a number or second branch. Launch settings: the teacher's recorded reasoning
budget of 512 tokens and prompt version teacher-v2, 4 slots, as in collection.
The comparison test in the version 2 gate (`targeted.mirrored`) is a heuristic for structural screening only: it
recognises swapped terms without reading direction, so "A is lower than B" against "B is higher than A" (the same
outcome) can pass as different. Accepted examples are therefore inspected in a sample for substantive
discrimination; the aim is better teacher actions, not a higher acceptance rate. Version 2 is evaluated with the same
checks as version 1, and checker changes are reported separately from changes in model behaviour.
Version 2 teacher job 746017 died at start (exit 13, SIGPIPE): `nvidia-smi | head -1` under `set -o pipefail`, where
`head` can close the pipe before nvidia-smi has written everything; earlier jobs escaped the race. Found with a traced
debug job (746087 passed, 746088 reproduced it); fixed by reading the first line with awk (9924355). The teacher was
resubmitted as job 746091 with the recorded collection settings (reasoning budget 512, teacher-v2, 4 slots); the queued
batch was untouched.
Version 2 narrowed to experiment design (Hatem, 2026-11-08): 81 of the 82 collected states are at the test step and
only 1 is a refused simulated-only finish, which rarely occurs on training companies. `docs/V2_PLAN.md`, third revision.
Job 746091 then downloaded the model but its server never started: it was submitted without `NAME`, which the script
needs for its log files under `set -u` (earlier teacher jobs set it). Resubmitted with NAME=capv2; settings unchanged.
First version 2 teacher batch (746123, 28 states): 28 valid answers, **0 accepted**. Two errors of mine, not of the
teacher: the states were the student's first call in the test stage, where it was still reading sources (24 of 28),
and the teacher was given the loop-recovery instructions ("do not move to a later step before the evidence is in
place"), so it chose `read_source` in 26 of 28. Fixed (238781f): states are taken where the student itself proposed or
declined its test (53 states on 36 companies, plus the one recovery state), and the teacher gets experiment-design
instructions (`targeted.EXPERIMENT_ASK`). The rejected answers stay in the manifest. Job 746123 was cancelled before its
second batch, which had the same flaw; the teacher was relaunched as job 746236.
Version 2 examples under review (Hatem, 2026-11-08): the 17 accepted are exported with their exact states, source
dates, raw teacher replies and acceptance reasons (`reviews/v2_examples/`). Two independent Claude agents and Gemini
(through Hatem's Antigravity CLI, read-only) assess them against Hatem's criteria; their assessments are **advisory
only**, and every keep or drop decision is Hatem's (Claude and Gemini select no training data). Training is paused
until that review. The 37 rejections each have exactly one reason; an earlier summary of mine miscounted them as 38.

## 2026-11-08: tool fields cut at 240 characters (found by the version 2 reviews)

The tool schema caps short text fields at 240 characters (`_TEXT` in `agent/runner.py`), and generation constrained by
that schema stops the text at the cap mid-sentence. In version 1's training data, 132 of the 158 `propose_test` targets
have a `decision_rule` at the cap (and 108 a `method`), so the model was trained on decision rules that are mostly cut
off; on the final test 23 of the trained arm's 37 accepted test proposals have a rule at the cap. This is a data-quality
limitation of version 1 and a plausible contributor to its weak experiment-design and recommendation scores; it does not
change any frozen number. The version 2 gates passed truncated rules, and 15 of the 17 accepted version 2 examples have
one. A future version needs longer limits for these fields (or a rule that must be complete) before any data is made.
Hatem chose one documented fix-and-regenerate round for version 2: longer limits for the test-design and reasoning
fields, teacher instructions that ask for mechanism-separating tests, proportionate and complete rules and staying inside
the case's time, three structural gates (complete rule, no pre-1995 online method, no source dated after the case), each
of the same 54 states asked once, and Hatem's review before any training. Details in `docs/V2_PLAN.md`, fourth revision.

## 2026-11-08: the rereading loop, fixed two ways (Hatem chose both)

A manual Try it run stalled at the test step rereading the same sources until the turn limit, the failure seen in 9 of
48 final-test runs; in 36 of 122 version 1 runs on training cases the model also reread a source a third time in the
test stage. The test stage offers the reading tools besides propose_test, and a reread is never refused.
- **Model:** the 35 distinct states where version 1 first reread a source a third time in the test stage (training
  companies, 27 of them) are added to the version 2 round as experiment-design states (origin "reread"): the teacher
  answers each once under the same instructions, the same gates apply, and Hatem reviews them with the rest.
- **Environment:** an opt-in reread limit (`Investigation(reread_limit=)`, runner `--reread-limit`) refuses a third
  read of one source, saying its text is already in the state. It is recorded in each episode's settings, so every
  earlier episode replays unchanged. Try it uses it by default (REREAD_LIMIT=2) and says so on the page. It is a
  harness change: version 1's reported results stay as evaluated, and any dev comparison runs both versions under the
  same setting, reported separately from model changes.
- Fixed with it: the tool refused a method or decision rule over 600 characters while the schema now allows 900, so
  in the running round answers between 601 and 900 characters are refused by the tools. The tool now accepts 900
  (old runs never exceeded 240, so replay is unaffected), and the round's answers are re-checked offline with the fix:
  the same single answers, no new sampling.
Try it's turn budget is raised from 45 to 60 (MAX_TURNS, labelled on the page; Hatem's suggestion). Of the 9
final-test runs that hit 45 turns, 8 were rereading, which the reread limit now stops, so the extra turns go to real
steps after a correction. A harness change like the reread limit: version 1's results stay at 45; for the version 2
development comparison the setting is fixed before it runs, and both versions run under it.
Try it gains a **live web research** toggle (Hatem, 2026-11-08), experimental and never part of an evaluation: a
`LiveDossier` (`env/live.py`) replaces the fixed dossier with DuckDuckGo search (the `ddgs` package), every result page
is fetched once and saved as a snapshot (URL, retrieval time, sha256 of the text, the excerpt shown), and quotes are
checked against that excerpt. Pages on the company's own site are company claims; other pages get a new class,
`web_page`, which says no analyst checked them. Live runs are never cached and are marked in the history and the label.
Checked end to end on the laptop: four live searches, six live pages read, sixteen snapshots saved.

## 2026-11-08: the offline re-check of the round's answers

`targeted regate` judges saved teacher replies again with the current code and samples nothing: every reply is
re-judged, including those the old 600-character tool limit refused, and each answer keeps its `decision_at_generation`
next to the new decision. Training rows are still made only from answers kept after the re-check and Hatem's review.
Tried first on the earlier batch (54 answers, 17 kept then): 1 is kept now. Of the 16 no longer kept, 15 fail the new
complete-rule gate (rules stopped at exactly 240 characters by the old schema) and one proposes an online method in a
case set in 1983; four answers rejected then are rejected now for the incomplete rule instead (20 decisions changed).
The one still kept showed a hole: its rule was cut at 240 characters right after "p<0.", which ends in a full stop.
Constrained generation stops a field exactly at its schema limit, so a new gate (`cut_off`) refuses any prose field of a
test, or any of the teacher's reasoning fields, that is at its limit, or at exactly 240 characters (the limit the first
batches were made under; an answer written to 240 by chance is lost, which is accepted). With it, none of that batch
is kept: 18 cut rules, 2 cut samples, 1 cut measure. The gates only confirm what the reviews found; that batch is not
used. The new round's answers are exported in full for Hatem's review by `scripts/v2_review_export.py` (the flags in
it are keyword aids, select nothing, and Hatem's choice is recorded in its `keep` field).
Third batch (54 states, the round's experiment states): 53 valid replies, 1 request timeout; 5 kept at generation, 18
refused only by the old 600-character tool limit. After the offline re-check, 5 are kept: 4 of the 5 (one has its
"learned" field cut at 700 characters) and 1 the old limit had refused. The case-date pattern of the in-period gates
knew only "It is [early/mid-/late] YEAR" and missed 16 dated cases ("It is March 2016", "It is March 1991", "It is
spring 2021"); it now reads them, and the re-check was run with it (the kept set did not change). The five are in
`reviews/v2_round2/targeted3_kept_for_review.md` for Hatem's decision.

## 2026-11-08: development comparison of the environment fixes (recorded before the runs end)

Version 1 (the final adapter, compact prompt) on the 15 development cases, 3 attempts each (45 runs per configuration),
code 1303fca / 9c30e1a, one GPU job per configuration:
- **as evaluated** (747625): 45 turns, 4 refusals in a row, no reread limit, no source dates, no stuck help;
- **fixed** (747626): 60 turns, reread limit 2, source dates in the state, stuck help after two refusals in a row;
- **fixed + weigh 3** (747636): the same, and each theory needs 3 weighed sources (or as many as were read) before
  the investigation moves on.
Measured mechanically on every run: finished, stop reasons, refused calls, sources weighed per theory, and the
confidence score out of five. Rule, fixed now: a configuration replaces the one before it in the Strategy Lab if it
finishes more runs and does not lower the mean confidence score; ties keep the simpler one. These are environment
changes, reported apart from any model change, and never applied to the reported final test. Blind judging of the
winner against "as evaluated" is optional and would use the frozen judge configuration.
Confidence on the final test's 28 finished runs, under the score out of five: 24 at 2/5, 2 at 3/5, 2 at 4/5 (no High).

## 2026-11-08: version 2, third teacher round (recorded before running)

After three advisory reviews found template answers in the second round (none of its 5 kept answers sound):
- **Instructions** (EXPERIMENT_ASK, third revision): test arms must differ in the product, its price or how it is sold,
  with the presentation otherwise the same (a message-only test needs a same-price control); the currency and methods of
  the case's time; each source shows its date (source dates in the state), only sources dated on or before the case,
  named by id; both theories kept credible; every outcome of the rule leads to a bounded next step.
- **Checks** (screens, so kept answers are still inspected): message-only arms with no product or price difference and
  no control; a rule that jumps to developing a product line with no bounded step; euros before 1999. On the second
  round's 5 kept answers they refuse Cree, Embrace and Black & Decker.
- **New skill, weigh**: the 81 states where version 1 left the weighing step after at most one source per theory with
  three or more real sources read, replayed with min_assessed 3 so the state asks for more; the teacher weighs one more
  source (assess_evidence, a read source, no repeat).
- **States**: 170 from version 1's runs on training companies (48 companies): 53 test design, 35 rereading, 81 weigh,
  1 recovery; all with source dates.
- **Sampling**: 2 answers per state at temperature 0.7; the code checks keep the first that passes, so at most one row
  per state; every answer is hashed into the manifest.
- **Server**: Command A+ Q4_K_M, 2 slots of 12,288 tokens (so the model fits on the GPU instead of offloading to the
  CPU, the cause of the earlier 1.5 tokens per second), prompt version teacher-v3.
Rows train only after Hatem's review. Cut-off as agreed: without about 60 approved examples by 11 November, version 2
stops and version 1 stays the submission.
Hatem's review of the second round (2026-11-08): of the 6 answers still passing every check, kept Superior and
Technogym; dropped Andis, Cotral, ARRI and Hilti. Two reasons in the pasted notes were corrected beside them (the
600-character refusal was the environment bug since fixed). The screens then had three holes, now closed: a single
price for the whole test counted as a price difference; "develop ... propositions" in the plural slipped past; and a
"pilot launch" of a product line or sub-brand counted as bounded. With them closed the screens agree with all six of
Hatem's decisions; they were tuned on these six, so this is a consistency check, not evidence that they generalise.
The third round's answers are re-checked offline with these screens before review.
Result (2026-11-08, 45 development runs each, rebuilt offline from the saved episodes because the job's AuditKIT step
failed on the new stuck_help setting; replay now passes the environment only the settings it takes):
- as evaluated (747625): 24 finished, 17 repeated refusals, 4 turn limit; 294 refused calls (245 repeats, 35 misquotes);
  mean confidence 2.21 of 5.
- fixed (747626): 23 finished, 22 repeated refusals, 0 turn limit; 350 refused calls (334 repeats, 7 misquotes); mean
  confidence 2.17.
Under the rule, "fixed" does not replace "as evaluated": it finishes one fewer run and does not raise confidence. The
reread limit turned rereading loops into refused calls, which end runs after 4 in a row, and stuck help did not rescue
enough of them. Misquotes fell from 35 to 7 (source dates in the state are the likely cause; not separately tested).
A fourth configuration, recorded before it runs: **dates + help** (60 turns, source dates, stuck help, no reread limit),
same 45 runs and rule, code b021891.

## 2026-11-08: test set 2, frozen before any run

Why: the final test's four companies support only a limited claim and have since informed the diagnosis, so a new claim
needs new companies (Hatem: "we need more data").
- **Companies (12)**, researched from public sources by four research agents and admitted only through our verifier
  (each quote found word for word on its live page): Ansell, Belimo, Drägerwerk, Franke Coffee Systems, Hach, Hoshizaki,
  Kingspan, Laerdal Medical, Mettler-Toledo, Tennant, Testo, Winterhalter. 221 verified records (14 dropped: 10 pages
  unreachable or blocking, 4 quotes not found). Each company: a base case and an irrelevant-what-if case, 24 cases;
  supporting and undermining what-ifs were not written for them. All marked test warranted. Premise records filtered to
  verified ones; Dräger's three missing premise records are replaced by its one verified company record.
- **Separation**: `data/dossier/cases_heldout2.json`, split `heldout2`; development and the final test cannot see its
  evidence (tests/test_test2_freeze.py); frozen digest 4db90205... in `docs/test2_freeze.json`. The final test's digest
  is unchanged (dce26d4f...).
- **Arms**: base (Tiny Aya bf16, staged prompt, no adapter) and version 1 (the final adapter, GGUF 41794b57..., compact
  prompt), exactly the final test's settings: context 12,288, 520 tokens per turn, 45 turns, 4 refusals in a row,
  temperature 0 with 0.4 only on a retry; 3 attempts; 144 runs. A version 2 adapter may be added as a third arm only if
  it is adopted on development by 11 November under its own rule, run with the same settings, and before any per-case
  look at test set 2; no failure analysis of test set 2 happens until every arm has run.
- **Judging**: the frozen judge package and configuration (judge-v1-two-backends-2). Claude now; Codex from 11 November
  (unavailable until then). Primary result: version 1 minus base, mean of the two judges, paired by case and attempt,
  95% case-cluster bootstrap (4,000 resamples, seed 20261106). A Claude-only result may be reported earlier, labelled as
  such. Also: each judge, each company, base against irrelevant what-if, finished counts and the mechanical measures.
- **Reporting**: both test sets side by side, test set 2 never pooled into the frozen final-test result.
Deviations, 2026-11-08 evening: the third teacher round's first job (747708) failed before any answer (the server,
without the rebuild flag, crashed with a CUDA error on its first requests; 0 of 340 requests answered). It was
resubmitted (747857) with the llama.cpp rebuild and 1 slot of 12,288 tokens instead of 2, because 2 slots still did not
fit on the GPU; instructions, states, checks and sampling are unchanged. The "dates + help" development job (747811)
was cancelled to free the GPUs for test set 2 (747855 version 1, 747856 base) and will be resubmitted unchanged.
Result of the third configuration (747636, 45 runs, rebuilt offline from the saved episodes): **fixed + weigh 3**
finished 25 (19 repeated refusals, 1 context limit), weighed 4.69 sources per run (3.29 as evaluated), mean confidence
3.12 of 5 (22 runs at 3, 3 at 4, none at 2). Under the rule it replaces "as evaluated" in the Strategy Lab: it finishes
more and raises confidence. Caveats: one more finished run of 45 is within noise, and part of the confidence rise is
built in, since one of the five checks counts three weighed sources, which the setting now requires. The Strategy Lab
now runs with source dates, the reread limit, stuck help and three weighed sources per theory. The frozen final test and
test set 2 keep the evaluated settings.

## 2026-11-10 01:40: test set 2, Claude-only result (frozen protocol unchanged; Codex from 11 November)

Claude judged all 133 packets (144 runs, 72 per arm) under the frozen judge-v1 package. Labelled Claude-only; the
primary result (mean of both judges) waits for Codex. Never pooled with the final test.

| | base (staged prompt) | version 1 (final adapter) | version 1 minus base, paired, 95% case-cluster bootstrap |
|---|---|---|---|
| Claude | 0.48 | 0.89 | **+0.41 [0.24, 0.57]**, 72 pairs, 24 cases |

10 of 12 companies positive (Mettler +1.00, Kingspan +0.89, Tennant +0.81, Ansell +0.57 … Dräger +0.16); Franke Coffee
−0.17 and Hoshizaki −0.15. By dimension (version 1 against base): problem framing 1.88 vs 1.03, revision 1.00 vs 0.11,
distinct theories 0.92 vs 0.40, recommendation 0.44 vs 0.03, experiment design 0.50 vs 0.22, evidence judgement 0.39
vs 0.28. Mechanical: finished 32 vs 2 of 72; passing every check 4 vs 1. The effect is smaller than on the final test
(Claude +0.64 [0.51, 0.77]) and evidence judgement and experiment design stay low, the weaknesses the corrective
families target.
Infrastructure: the Mac's network dropped during the first pass (108 connection errors, 1 timeout, 3 refused by the
ledger cap because of the held reservations); as for the final test, those attempts were archived
(`reports/judge/test2/claude_test2_archived_infra/`) and only they were judged again, never a valid judgment; two
later timeouts were retried once. The unbilled reservations of the 108 connection errors were released in the ledger
with a note. Actual cost $11.44 (approved about $10).

## 2026-11-10 03:55: corrective pilot 1 result, instructions changed for pilot 2
Pilot 1 (job 750511, code 1e00c09, 51 states from training companies): 15 kept, all 15 rebuild from the manifest and
today's replay. Per family kept/asked: numbers 0/10, experiment 1/10, classify 2/10, unstick 2/10, simulated 0/1,
revise 10/10. Main causes: 11 of 30 numbers/experiment/classify answers made a different call than the state is about
(mostly read_source); 11 answers named no id from the state; 4 finishes cited sources read but never assessed; 3 tests
again varied only the message. Two of the 5 non-revise kept answers are weak on inspection (cotral unstick: why_next
says add a theory, the call reads a source; arri experiment: a message survey), so review stays necessary.
Changes (5b8f271), gates unchanged: the teacher is offered only the tools of the decision the family is about (finish;
propose_test/decline_test; assess_evidence), every family is told to write exact ids and act on one it names, the
finish instruction says only assessed sources count and no numbers in a next action without a proposed test. Pilot 2
(job 750894): 32 states not used in pilot 1, 8 each of numbers, experiment, classify, unstick; revise is dropped from
pilots because the student already passes its gate (22/22). The full batch waits for pilot 2.

## 2026-11-10 11:05: corrective pilots 2 and 3, export for review
Pilot 2 (750894, 5b8f271, 32 states): 9 kept (unstick 6/8, classify 3/8, numbers 0/8 with 6 citing unassessed
sources, experiment 0/8). Pilot 3 (751211, 528dc19, 24 states): 7 kept (numbers 4/8, experiment 1/8, classify 2/8).
Pilot 3 numbers rejections are real invented figures (a "$25" price floor, ages 25-55); experiment rejections are
mostly fields cut at the length limit (4 of 7). Classify stays low because the evidence-kind annotation is inconsistent
for press articles (the same kind of trade article is market_fact in one case, customer_observation in another), so a
correct reading can fail; the check and annotations are frozen and unchanged, noted for a later audit. The
review exporter now re-judges corrective answers by their own family gate (it had used the round-3 gate). 31 kept
answers from 107, all passing provenance, replay and split, are on the Review page (reviews/v2_round4). Nothing trains.

## 2026-11-10 19:30 UTC: a hosted teacher (DeepSeek) for the corrective families, and an LLM reviewer (registered before any result)
Why: the V2 stop decision (V2_CORRECTIVE_PLAN section 10) is a finding about the teacher. Command A+ made the student's
own errors (evidence kinds, dates, message-only tests) and could not write a sound experiment design in two attempts.
Hatem asked to try a stronger teacher, and to build on version 1 rather than start again.

**Teacher.** DeepSeek V4.1-Flash (API model `deepseek-flash`, DeepSeek-V4.1-Flash-1017). The weights are MIT, and
DeepSeek's Open Platform terms allow using outputs to train other models, distillation included (copy of the terms in
`docs/terms/`). Called through `pipeline/hosted_teacher.py`, a separate entry point. The corrective pipeline's states,
families, instructions and gates are unchanged (`pipeline/corrective.py` at this commit). The evaluated runner, the
Strategy Lab and the Command A+ jobs are unchanged.

Differences from the llama.cpp teacher, fixed now:
- Strict tool calling replaces the JSON-schema grammar. The reply is checked against the original schema, and up to
  two repair turns name the exact limits broken. A reply that still breaks them is refused, as a reply cut off by the
  grammar was.
- Thinking mode is on (the API default), with up to 16,000 tokens. The API takes no seed, so a rerun is not
  bit-identical; every reply is hashed into the manifest as before.
- Every request is logged with its model, fingerprint, usage and cost.

**States.** `experiments/v2_corrective/all_states_v3.json`: 244 states from version 1's runs on training companies
(unstick 69, experiment 53, classify 53, numbers 46, revise 22, simulated 1). One answer each. No development,
final-test or test-set-2 company, as before.

**Reviewer (Hatem's decision, replacing the human Keep/Drop review).** DeepSeek V4-Pro (`deepseek-v4-pro`,
DeepSeek-V4-Pro-0813). It is a different model from the teacher, and it reviews the exported examples with a written
rubric (`pipeline/hosted_review.py`, built from the earlier human reviews and section 9's criteria).

Qualification rule, fixed now:
- Before it reviews anything, it reviews the 6 examples Hatem decided (2 Keep, 4 Drop).
- It qualifies only if it agrees on at least 5 of 6 and keeps both of Hatem's Keeps.
- If it fails, the examples go to human review as before.
- Claude's advisory verdicts are not used, because Claude's output never decides training data.

How its decisions are recorded and checked:
- They are written as `review_source: llm`.
- A human decision is never overwritten.
- The model card and paper will say that the examples were selected by an LLM reviewer.
- A human spot check of 10 randomly chosen LLM keeps is recommended before training. If Hatem drops more than 2 of
  the 10, the LLM review is not used.

**What follows, unchanged from V2_CORRECTIVE_PLAN:**
- the threshold of section 9: at least 30 keeps in at least 3 families, with experiment design among them;
- the training mix of section 7, continuing version 1's adapter;
- the screen of section 8;
- the adoption rule of section 6.

The training job's approval file is created only by a human. Neither test set is used.

**Budget.** At most $10 of DeepSeek credit for this round. Each process stops at its own cap (`HOSTED_BUDGET_USD`).

**Later, not registered here.** About 200 new full investigations by the same teacher on training companies, if this
round shows the teacher is better. That will be registered before it runs.

## 2026-11-10 18:35 UTC: reviewer qualification result, and no human review (Hatem's decision, before any batch is reviewed)
Qualification (`experiments/hosted_teacher/reviewer_qualification.json`): DeepSeek V4-Pro agreed with Hatem on 4 of 6.
It dropped all 4 of his Drops, for the same reasons he gave, and also dropped both of his Keeps:
- Superior: the arms mix proposition with price (€45 against €55) and have no same-price control;
- Technogym: the variants differ in positioning only.

It is therefore **not qualified** under the rule registered above (at least 5 of 6, with both Keeps kept). Its errors
on this sample are all in one direction, dropping rather than keeping.

Hatem's decision: no manual review. The unqualified V4-Pro reviewer is used as a strict filter, unchanged:
- only examples it keeps can train;
- the rubric is not edited after seeing the qualification, and there is no human spot check;
- this replaces the human review and spot check registered above.

Disclosure, in the model card and paper: the corrective examples were selected by gates plus an LLM reviewer that
failed its qualification against human decisions, because it was stricter. The rest of the plan is unchanged: section
9's threshold, section 7's mix, section 8's screen and section 6's adoption rule. The training job's approval file is
created on Hatem's explicit instruction.

## 2026-11-10 18:30 UTC: a second hosted teacher, DeepSeek V4-Pro, on the same 244 states (Hatem's decision, before any result)
The same entry point, states, instructions, gates, repair turns and reviewer as the V4.1-Flash round, with
`HOSTED_MODEL=deepseek-v4-pro` (DeepSeek-V4-Pro-0813). It runs until the credit runs out. States not answered for
lack of credit are reported as such and never filled in.

The reviewer stays V4-Pro with the rubric unchanged, so both teachers are filtered alike. For the Pro answers this is a
model reviewing its own model's answers; that is disclosed. Comparison: on identical states, the share kept by the
gates and then by the reviewer, per family, for Command A+ (pilots 1-4, regated by today's gates), V4.1-Flash and
V4-Pro. Where both DeepSeek answers to one state are kept, the Pro answer is used (the stronger model, fixed now).

## 2026-11-10 18:55 UTC: a second shortening turn for experiment answers refused only for length (before it runs)
Flash's experiment family: 0 of 53 kept, and 20 of them were refused only because a field was still over its limit
after experiment_design's single shortening turn. Pro's experiment family shows the same pattern so far.

The change (`hosted_teacher.py reshorten`):
- Applies only to answers refused with "still over the length limit after one shortening".
- The same conversation gets one more turn with the exact counts (experiment_design.shorten_note), so the shortened
  text is still the teacher's own.
- That reply goes through the same compose, limits and family gate as before. Every reply is hashed into the manifest.
- Every other refusal stands. No answer is rewritten by code.
- For both teachers. The answers kept this way go through the export checks and the same reviewer.

## 2026-11-10 19:05 UTC: the experiment family is judged by the reviewer, not by the keyword screens (before it runs)
The keyword design screens refuse sound designs. Example: Pro's Sealed Air answer, a same-price test of poppable
against pop-less wrap (a real product attribute), refused as "differs only in wording". Nour's plan already noted that
these screens have errors of their own (V2_CORRECTIVE_PLAN section 6).

**What changes, for the experiment family only** (`pipeline/hosted_experiment.py`):
- These screens no longer decide: targeted.gate_mechanism, gate_test and gate_decline.
- An answer goes to the unchanged DeepSeek V4-Pro reviewer if it passes the mechanical checks:
  - the call is accepted and grounded;
  - no field is cut off or over its limit;
  - it stays inside the case's period and currency, and cites no later source;
  - it proposes or declines as the case's own `test_warranted` says;
  - it is from a training case;
  - its replies are in the manifest, and its composition rebuilds.
- The reviewer's rubric already drops message-only tests without a same-price control, non-discriminating predictions,
  jumps to a launch, trivial commitments and declines that contradict themselves.

**Which answers:** Flash's and Pro's experiment answers. Where a state has a second-shortening answer, that one is used.

**What stays the same:**
- Every other family keeps its gate.
- The evaluation's `experiment_v2` measure (V2_CORRECTIVE_PLAN section 6) still uses the screen, unchanged and the
  same for both arms.

## 2026-11-10 19:15 UTC: the DeepSeek round's result, the threshold met, and v2 training (Hatem's instruction to train on top of v1)
On the 244 states, the DeepSeek V4-Pro reviewer kept (Command A+'s 27 gate-passed pilot answers, reviewed alike: 4):

| Teacher | Main families | Experiment | Total |
|---|---|---|---|
| V4.1-Flash | 67 | 4, of 10 passing the mechanical checks | 71 |
| V4-Pro | 78 | 8, of 15 passing the mechanical checks | 86 |

Both teachers often declined tests the case warrants: Flash 18 times, Pro 19.

**Training rows:** where both DeepSeek teachers have a kept answer for the same state, Pro's is used (48 Flash keeps
superseded). This gives 109 approved rows, all rebuilt exactly from the manifests.

**Continuation set** (`scripts/v2_training_set.py`, unchanged):
- 105 corrective rows (numbers 9, classify 18, unstick 56, revise 10, experiment 12; 1 duplicate dropped, revise
  capped), each presented twice;
- 1,707 of version 1's own rows;
- 411 validation rows;
- a corrective share of 0.20; output sha256 4e06896d.

**Threshold (section 9):** met. At least 30 keeps: 105. At least 3 families: 5. Experiment design among them: 12.

**Training:** `jobs/train_v2_corrective.sbatch` unchanged. It continues version 1's adapter, one epoch, learning rate
2.5e-5, seed 7. The approval file is created on Hatem's instruction ("train on top of command A+"). Then the section 8
screen and the section 6 adoption rule. Version 1 stays the submission unless v2 passes them.
Jobs (2026-11-10, code 6c9b182):
- v2 training: 752833.
- Section 8 screen: 752835 for V1, 752836 for V2, the latter after 752833 succeeds.
- Both screen arms: the 15 development cases, one attempt, the compact prompt, the as-evaluated controller,
  SKIP_BASE=1 and DIAGNOSTIC=1 as for the final test.
Infrastructure retry (2026-11-10 19:25 UTC): screen arm 752835 failed before any episode because the code copy lacked
`data/dossier`. I had shipped only src, jobs and scripts. The case files of the same revision were added, and V1 was
resubmitted unchanged as screen_v1b. 752836 (V2) reads the same copy.

## 2026-11-10 22:40 UTC: v2 screen result, stopped under section 8; version 1 stays
Training 752833 completed: 480 steps, loss 0.61. Screen, 15 development cases, one attempt, the same code and settings:

| | V1 (752848) | V2 (752836) |
|---|---|---|
| Finished | 7 | 0 |
| Valid completion | 1 | 0 |
| Turn limit | 4 | 10 |
| Repeated refusals | 4 | 5 |
| Refused calls | 128 | 146 |
| read_source | 156 | 299 |
| Rereads | 64 | 186 |
| assess_evidence | 91 | 40 |
| propose_test | 8 | 0 |
| finish | 12 | 0 |

Section 8, condition 2 fails: V2 has 7 fewer finishes, against at most 2 allowed. **Stop: V1 stays.** The screen is the
reported result. It was not judged, because the rule does not need quality to decide this, and judging would cost
money without changing the decision.

Likely cause (post hoc):
- The corrective set was dominated by unstick (56 of 105), whose kept answers are mostly read_source.
- Each row was presented twice at 20% of the target tokens.
- So the continuation taught rereading over weighing and finishing.

Single-step corrections skew the action distribution in a way whole investigations do not. Any further DeepSeek data
should be whole investigations, or corrections balanced by action, registered before it runs.

## 2026-11-10 22:55 UTC: whole investigations by DeepSeek V4-Pro (Hatem's decision, registered before any run)
Why: single-step corrections skewed the action mix (V2's screen). Whole investigations carry the procedure's own mix.

**Teacher and runner:**
- DeepSeek V4-Pro (`deepseek-v4-pro`) through `pipeline/hosted_investigations.py`, which points the unchanged runner's
  chat at the hosted client.
- Teacher prompt, tools, stages and guards as for the Command A+ investigations: context 16,384, 2,000 tokens per
  turn, 45 turns, temperature 0 (the API takes no seed).
- The strict-schema conversion now also handles a tool with no arguments (placeholder) and a map keyed by ids (a list
  of key/value pairs, turned back before the original schema is checked).

**Cases:** the 111 training cases of version 1's rows (57 companies, no development company), at attempt 10, then 11,
and so on, so the seeds and labels differ from earlier runs. 16 investigations at a time.

**Budget:** Hatem's rule is to keep $5. The client reads the real balance every minute and refuses new requests below
$5 (`HOSTED_MIN_BALANCE=5`). An investigation cut off by the floor is recorded as a harness failure and never used.
The balance was $31.51 before the pilot.

**Pilot first:** 2 investigations, to check the pipeline and measure the cost per investigation.

**Rows** (registered now, applied after generation):
- The standard pipeline (`pipeline/rows.py`): replay-exact episodes, the same filters as version 1's rows.
- The hosted label's hash is added to `TEACHER_WEIGHTS` for this teacher only.
- Before any training:
  - the share of each action in the new rows is reported against version 1's;
  - a mix whose read_source share is more than 1.5 times version 1's is not trained.

**Training:** continue version 1 once, not twice. The new rows are at most 30% of target characters, with the rest
from version 1's rows. Then the section 8 screen and the section 6 rule, as for the first v2. Version 1 stays unless
the new adapter passes them.

## 2026-11-10 23:05 UTC: validation mixes both teachers (Hatem's request, before any DeepSeek investigation row exists)
The trainer's held-out loss currently uses only Command A+ rows from the six development companies.

The change:
- The DeepSeek investigations of six training companies are held out for validation only and never trained on:
  diatek, illumina, perrigo, resmed, sensirion and sievi. They were drawn with `random.Random(20261110)` from the 57
  companies in version 1's rows.
- Validation is then the development companies' Command A+ rows plus these companies' DeepSeek rows.
- Held-out loss is reported per teacher, so it shows whether the adapter fits each teacher's investigations, not only
  Command A+'s.
- Those six companies' Command A+ rows stay in training as before, so version 1's own data is unchanged.

## 2026-11-10 23:10 UTC: a universal held-out loss, and teacher-free selection (Hatem's request, before any DeepSeek investigation row exists)
A loss on one teacher's held-out text measures imitation of that teacher, not quality for a human reader. So:

1. **Monitoring.** The trainer's held-out loss is reported as one universal number: the mean of the Command A+ and
   DeepSeek validation losses, weighted equally, so neither teacher's style dominates. The per-teacher losses are
   reported beside it as diagnostics only. No loss selects or rejects an adapter.
2. **Selection** stays teacher-free, as in V2_CORRECTIVE_PLAN sections 6 and 8. An adapter is judged only by what it
   does on development cases:
   - the environment's checks: finished, valid completion, no invented numbers, `experiment_v2`;
   - the blind score on the frozen nine-dimension rubric, written for a human reader, from the qualified judge with
     the adapter hidden.
   No teacher text is involved.

## 2026-11-10 23:30 UTC: new training cases written by DeepSeek from verified public sources (Hatem: "generate more cases")
Claude may not author training data, and a case's question and brief are in every training row. So new training cases
are written by DeepSeek V4.1-Flash (`pipeline/hosted_cases.py`), whose terms allow training other models on its outputs.

**Steps:**
- DeepSeek proposes manufacturers absent from every dossier file, and from the same groups.
- Web searches (ddgs) return pages, fetched as the verifier fetches them.
- DeepSeek copies 8 to 12 exact quotes, with their metadata, and writes one or two sentences on what the company makes
  and for whom.

**What a case can contain:**
- The verifier admits only quotes found word for word on their live page, as for every dossier record.
- A company with fewer than 4 verified records is dropped.
- The question and the rest of the brief are the existing template, word for word.
- `add_cases --split training` adds the base case and its irrelevant-what-if variant.

**Excluded from every test:** these companies are training only, and neither frozen test set changes.

**Cancelled:** the third pass of investigations, so the leftover credit can write these cases. Their own Pro
investigations need more credit, kept above the $5 floor.
Implementation (2026-11-10 23:20 UTC), `training/train.py`:
- `--validation-rows` adds the held-out DeepSeek rows.
- Each validation row is grouped by teacher and company (`ds_` prefix for DeepSeek).
- `eval_loss` is then the universal loss, the mean of the two teachers' company-balanced means. It is logged with
  `eval_teacher_commanda_loss` and `eval_teacher_deepseek_loss`.
- The trainer's existing best-checkpoint choice within a run uses this universal loss. Adopting the adapter still
  depends only on the teacher-free screen.
- The split check compares case and teacher, so the Command A+ rows of the six companies stay in training.
- Without DeepSeek rows, behaviour is exactly as before (version 1 reproducible).

## 2026-11-10 23:25 UTC: all the data from both teachers (Hatem's decision, before any row is built)
Asked how much DeepSeek data to mix in, Hatem chose: "use all the data that is available from both". This replaces the
registered cap of DeepSeek at most 30% of target characters.

**The continuation:**
- every row of version 1's set (`rows/final.jsonl`; the six development companies held out for validation, as before);
- every replay-exact row of the DeepSeek V4-Pro investigations, except the six validation companies' DeepSeek rows,
  which validate only;
- one pass, continuing version 1's adapter, learning rate 2.5e-5, warmup 10%, seed 7;
- universal validation loss, as registered.

**Unchanged:**
- The action-mix check: the mix is not trained if its read_source share exceeds 1.5 times version 1's.
- The section 8 screen and the section 6 adoption rule.

**Compute:** about 7,500 to 8,000 rows. A full A100 (7g.80gb), a 12-hour limit, and checkpoints every 25 steps so a
stopped job resumes. Job script: `jobs/train_v3.sbatch`.

## 2026-11-11 00:05 UTC: generation ended, version 3 training submitted
**Investigations:** 288 DeepSeek V4-Pro investigations (216 on the old training cases, 70 on the new cases, 2 in the
pilot), 154 of them finished. Hatem stopped the run at that point ("ok enough").

**Rows** (`experiments/hosted_investigations/v3_rows_report.json`):
- 154 investigations accepted: every finished one replays exactly; 112 never reached an accepted finish;
- 3,611 training rows from 69 companies, and 262 DeepSeek validation rows;
- read_source share 1.16 times version 1's, inside the 1.5 limit;
- training rows sha256 a4845f4c, the same locally and on the cluster.

**Jobs:** training 753357 (full A100, code 1d725b1); screen arms 753358 (V1) and 753360 (V3, after training).

**Deviation:** the $5 balance floor was overshot by $0.48 (the balance ended at $4.52). Each process read the balance
only once a minute, and requests already in flight kept billing. The client now reads it every 20 seconds and stops
new work $1.50 above the floor.

## 2026-11-11 09:30 UTC: version 3 screen result, stopped under section 8; version 1 stays
Training 753357 completed: 1,876 steps in 4.7 h. Best checkpoint 1876; universal held-out loss 0.913 (Command A+
0.717, DeepSeek 1.110).

Screen: the 15 development cases, one attempt, code 1d725b1. V1 is 753358, V3 is 753360.

| | V1 | V3 |
|---|---|---|
| Finished | 7 | 7 |
| Valid completion | 2 | 1 |
| Repeated refusals | 6 | 8 |
| Turn limit | 2 | 0 |
| Refused calls | 125 | 68 |
| Mean calls | 35.0 | 23.6 |
| Finished runs failing no_invented_numbers | 2 | 1 |
| Finished runs failing evidence_classes | 1 | 5 |

Of V3's refusals just before it stopped, 24 of 32 were a repeated search ("you already ran that search").

Blind Claude judging (judge-v1 unchanged; 29 packets, all valid; run `claude_screen3`): V1 1.049, V3 0.832. V1 minus V3
is +0.217 [−0.178, 0.633] over 15 pairs. By company: Hellberg +1.01, Neumann +0.40, ACR +0.06, Deere −0.12, Tanita
−0.24, Jotun −0.99.

**Decision:**
- Condition 1 is met: fewer finished runs fail no_invented_numbers.
- Condition 2 fails: blind quality V3 − V1 = −0.22, below the allowed −0.10.
- **Stop. V1 stays the submission.** V3 is reported as a development result.
- No test-set-2 arm is run for it (its rule needed adoption on development by 11 November).

**Likely cause (post hoc):**
- The DeepSeek investigations had almost no refused calls, so V3 learned their direct style but not recovery; it
  repeats a refused search until the four-refusal stop.
- Its theories are also thinner: distinct theories 0.87 against 1.47.

**Infrastructure** (no judgment lost or repeated):
- The first judging attempt was refused by the run cap.
- The second was refused by the ledger, because its output folder name `claude` reused the final test's run purpose.
- Both archived; the valid run is `claude_screen3`.

## 2026-11-11: version 3 on both test sets, exploratory only (Hatem: "run v3 anyways and we include it in the paper")

Decided after version 1's results on both test sets were known, and after version 3 failed its development screen
(entry 09:30 UTC above). So these runs **select nothing**: version 1 stays the submission and its frozen results are
unchanged; the version 3 numbers are reported in the paper as a labelled exploratory comparison only.
- Arms: version 3 only (`runs/v3/adapter`, conversion gate passed on its screen: worst gap added 0.072), compact prompt,
  `SKIP_BASE=1`, `ATTEMPTS=3`, every setting as version 1's run on each set: final test with runner code d3aa608, split
  heldout, the 16 cases (48 runs); test set 2 with runner code 2e9cbbd, split heldout2, the 24 cases (72 runs). Context
  12,288, 520 tokens per turn, 45 turns, 4 refusals in a row, temperature 0 (0.4 only on a retry).
- Judging: the same frozen judge package and configuration (judge-v1-two-backends-2), Claude first, within the $60
  ledger cap (final test first, test set 2 if the cap allows); Codex later if available. Version 3's packets are judged
  alone and compared with version 1's existing judgments of the same cases and attempts; Claude-only results are
  labelled as such.
- **Judge change (Hatem: "you can use claude code for judging instead of the api"), before any version 3 output was
  judged:** a third backend, `claudecode` (the same model claude-opus-5-5, the same frozen judge prompt as its system
  prompt, effort medium, through Claude Code print mode on the subscription login; no tools, MCP servers, settings or
  sessions, an empty folder outside the repository). Added to `reviews/judge_v1/backends_v1.json` as version
  judge-v1-three-backends-3; the claude and codex entries are unchanged, so their receipts still bind. Qualified under
  the same scoring rule on the same 40 packets (`reports/judge/claudecode_score_qualification.json`: sound above flawed
  in 19 of 20 clusters, 17 needed; 1 invalid, 4 allowed). Because it is a different instrument from the API judge,
  base, version 1 and version 3 are all rejudged together, blind and shuffled, on each test set, and only those
  same-judge numbers compare the arms (version 1 minus base under this judge also checks it against the API judge's
  +0.64 on the final test). No API spend.

## 2026-11-11: repositories renamed to aemon; history rewritten without the Claude co-author line

Hatem: "rename the repo to aemon ... both public and private, and dont include claude in the contributors". The public
repository is now https://github.com/HatemSaadallah/aemon (was lexsi-strategy-agent) and the private one
https://github.com/HatemSaadallah/aemon-dev (was lexsi-ai-hackathon); GitHub redirects the old URLs. Every commit
message on every branch and tag of both was rewritten to drop the "Co-Authored-By: Claude" line (and any "Generated
with Claude Code" line), then force-pushed. **File contents are unchanged; only commit IDs changed.** Earlier entries,
reports and run records cite the old IDs (for example the final test's runner code d3aa608, now 2fb09e7, and test set
2's 2e9cbbd, now 7e08754): `docs/history/commit_map_private.tsv` and `commit_map_public.tsv` map every old ID to its new
one. The old histories are kept as bundles outside the repository. Tags v1-freeze, v1-final-test and v1-test2 point
at the rewritten commits. Nour's clone needs `git fetch && git reset --hard origin/main` (or a fresh clone).
- **Result (exploratory; selects nothing):** base, version 1 and version 3 rejudged together, blind, by the Claude Code
  judge. Its version 1 minus base agrees with the API Claude judge's (final test +0.63 [0.48, 0.77] against +0.64;
  test set 2 +0.36 [0.19, 0.54] against +0.41), so the instrument change does not move the scale.

  | | base | version 1 | version 3 | version 3 minus version 1 | finished (v1 / v3) | every check passed (v1 / v3) |
  |---|---|---|---|---|---|---|
  | Final test (4 companies, 48 runs per arm) | 0.55 | 1.18 | 1.06 | -0.12 [-0.28, 0.03] | 28 / 37 | 1 / 3 |
  | Test set 2 (12 companies, 72 runs per arm) | 0.49 | 0.86 | 1.22 | **+0.36 [0.21, 0.51]** | 32 / 57 | 4 / 18 |

  On test set 2 version 3 is higher for 10 of 12 companies (Mettler -0.06 and Tennant -0.09 the exceptions) and on 8
  of 9 dimensions (not framing), and it makes half the refused calls (305 against 584). On the final test the gap is
  Aquaporin (-0.46); the other three companies are within 0.14. No version 3 run found Aquaporin's insolvency either;
  all 9 finished runs recommend investing. One version 1 packet on test set 2 (ansell-base) was judge-invalid and is
  reported missing. Reading: the development screen (6 companies, one attempt, 15 runs per arm) said version 3 was
  worse; the larger test set 2 says it is clearly better, and the final test cannot tell them apart. The screen was
  too small to decide. These numbers come after both test sets were used for version 1 and must be reported as an
  exploratory comparison; under the frozen plan version 1 remains the submission.

## 2026-11-11: adapter switching mid-run, development only (Hatem: "i like the idea of switching the adapter mid run ... do that and test it")

Fixed before any run. One llama.cpp server holds both gated adapters (version 1 as id 0, sha256 41794b57...; version 3
as id 1, ea919380...), and `runner --lora-route` picks the adapter for each turn from the stage and from the count of
refusals in a row the runner already keeps (new `stuck=ID`, `stuck_after=N`, default 2; it never sees a judge or the
case). Job `jobs/eval_switch.sbatch`; every arm on the same two-adapter server, compact prompt, 45 turns, 4 refusals in
a row, temperature 0 (0.4 on a retry), the 15 development cases on the 6 validation companies, **3 attempts** (45 runs
per arm; the 1-attempt screen was too small).
- `v1`: default=0. `v3`: default=1 (the single adapters, rerun on this server so every arm matches).
- `v3_rescue`: default=1,stuck=0 (version 3; a stuck turn goes to version 1).
- `v1_rescue`: default=0,stuck=1 (version 1; a stuck turn goes to version 3).
- `dig_then_reason`: default=1,brief=0,frame=0,evidence=0 (version 1 gathers evidence, version 3 does the rest).
Judging: the Claude Code judge (claudecode receipt), all five arms in one blind shuffled packet set. Reported: each
switching arm minus v1 and minus v3, paired, case-cluster bootstrap; finished runs; refusals; how often each adapter
wrote a turn. These are development numbers: they can choose a routing rule to test, never a submission. A claim
needs a test on companies neither test set used.

## 2026-11-11: company status check (Aquaporin), and a teacher run with it (Hatem: "yes do it, also ... run the teacher particularly for this")

Diagnosis, before any change: across all 144 Aquaporin final-test runs (base, version 1, version 3) the insolvency
records never appeared in a search result; every query was about the market question. Plain queries ("Aquaporin
company", "Aquaporin news 2026", "Aquaporin risks") return them in the top three. So the agent never looks at the
company's own position, and neither did the teacher it learned from.
- **Environment, opt-in `status_check`** (recorded in each episode's settings; episodes without it replay unchanged):
  a tool `company_status {}` returns the company's three most relevant records for one fixed query (its name plus
  words for a change of position: results, insolvency, bankruptcy, acquisition, profit warning, restructuring,
  funding, ...), dated ones first, newest first; it uses no search. Stages `status` (only company_status open) and
  `status_reading` (read one of its results) come right after framing. `finish` must cite a status source it read.
- **Aquaporin diagnostic** (labelled: Aquaporin is a test company, so this shows whether the fix works on the known
  failure and is no test result): version 1 and version 3 with the status check on the 4 Aquaporin cases, 3 attempts.
  Measured mechanically: runs that read an insolvency record, runs that cite it in finish, finished runs, and runs
  whose recommendation still says to invest without naming the insolvency.
- **Harm check, development:** version 1 and version 3 with the status check on the 15 development cases, 3 attempts,
  on the two-adapter server, compared with the `v1` and `v3` arms of the switching test (same server, cases, attempts),
  judged blind by the Claude Code judge.
- **Teacher (Command A+, through the same environment, status check on):** the 93 base cases of the training companies
  (the 6 validation companies and all test companies excluded); first the 17 whose status results carry a change of
  position (portwest, zarges, masimo, arri, nilfisk, tupper, microban, orasure, illumina, stihl, maglite, sma, osram,
  martek, perrigo, searle, lmericsson) at temperature 0 and again at 0.4, then the other 76. Rows only from episodes
  that replay exactly and finish accepted, as before. No Claude output is used.
Fix, 17:30, before the teacher run started (job 754912 held, then cancelled and resubmitted): with the status check,
the status sources counted toward the evidence stage's minimum of 3 sources read, so runs read the status results,
went to the theories stage with no market search, and looped on repeated searches (v1 Aquaporin: 117 repeat refusals in
12 runs; development: 1 of 15 and 0 of 12 finished before the jobs were stopped). Status sources now do not count
toward that minimum and are not offered as evidence-stage reads. Runs without the status check are unchanged. The
Aquaporin diagnostic above ran before this fix and is rerun with it; the development check is rerun too.

## 2026-11-11: adapter switching, development result (Claude Code judge, 207 of 207 packets valid, 45 pairs each)

Mean score (0 to 3) and finished runs of 45: v1 1.06 (24), v3 0.86 (19), v3_rescue 1.17 (33), v1_rescue 1.20 (26),
dig_then_reason 1.24 (33). Paired, 95% case-cluster bootstrap: dig_then_reason minus v1 +0.17 [0.02, 0.35], minus v3
+0.38 [0.13, 0.62]; v1_rescue minus v1 +0.13 [0.03, 0.24]; v3_rescue minus v1 +0.10 [-0.15, 0.38], minus v3 +0.31
[0.08, 0.54]; v3 minus v1 -0.20 [-0.53, 0.11]. In v3_rescue, version 1 wrote 102 of 1,392 turns (7%) and stepped in on
37 of 45 runs. Development numbers on 6 companies: they choose dig_then_reason (version 1 for the brief, frame and
evidence stages, version 3 after) as the routing rule to test on companies neither test set used; they are no test
result, and version 1 stays the submission.
Second fix, 17:55, before the teacher started (755028 held, then cancelled and resubmitted): on the development
companies, `finish` was refused for not citing a status source, because the fixed query's words matched other
companies' records (for Hellberg, 3M's annual report and sales), which a run reasonably does not cite; runs ended on
repeated refusals. On Aquaporin the same rule was met by appending the bankruptcy record's id without a word about it.
Now: status results keep only records that name the company (falling back to the best matches if none does), and
`finish` takes a required `company_position` text instead (the company's current position and how it bears on the
recommendation), which the grammar always lets the model write. The two status-check runs on the earlier rule were
stopped; the diagnostics are rerun on this one (status3_*).

## 2026-11-11: CuratorKIT row curation and an Unsloth smoke test, for version 4 only (Hatem: "yes")

- **CuratorKIT** (`aemon.rows.curate`, `CURATE=1` in `jobs/train_after_teacher.sbatch`): CuratorKIT decides which rows
  to keep and never rewrites one (kept rows are the original lines). Exact deduplication on (state, target call),
  since CuratorKIT's default key (instruction + output) on the target alone would merge one call made in different
  states; MinHash off, because consecutive turns of one investigation share most of their state; its secrets gate on
  with the hex-entropy detector off (7 false positives on hashes in v1's rows). On v1's rows: 4,302 -> 3,958, all 344
  dropped rows exact duplicates (172 the identical first read_brief). Applies to version 4's rows only; v1 and v3 are
  unchanged.
- **Unsloth** (`--unsloth`, `jobs/unsloth_smoke.sbatch`): Unsloth 2026.11.3 needs transformers <= 5.17, TRL 1.15 and
  torch 2.14.1 against the project's 5.22.1, 1.7.1 and 2.11, so it runs in its own environment. Smoke test: the same
  50 rows, LoRA, seed and 12 steps, trained through AgentTune both ways; compared on loss per step, seconds, peak
  memory and GGUF conversion. Version 4 trains with Unsloth only if its losses track the current trainer's and its
  adapter converts and passes the conversion gate; otherwise it trains as v1 did. Either way the software stack is
  recorded with the adapter, since a different stack is a difference between v4 and v1 beyond the data.
Unsloth smoke result (job 755202, 2026-11-11 18:56; Unsloth 2026.11.3 with torch 2.11, transformers 5.17, TRL 1.7.1 and
AgentTune and AuditKIT at the lock file's commits): the same 50 rows, LoRA, seed and 12 steps. Losses track the current
trainer to within 0.007 at every step (first 1.2156 against 1.2145, last 0.8944 against 0.8907); both adapters convert
to GGUF (60,491,936 bytes each). Unsloth took 155 s against 71 s and peaked at 8.1 GB against 11.6 GB: no speed gain here
(xformers did not load for this torch build, so plain attention; Unsloth's gradient checkpointing; compile time weighs
on 12 steps). Under the rule above, version 4 trains with the current trainer, on the same stack as versions 1 and 3.

## 2026-11-11: test set 2 result with both judges (frozen campaign, 12 held-out companies)

Codex judged all 133 packets validly (118 before its account's usage limit, 15 after the reset at about 19:00; the
failed attempts are archived, no valid judgment was redone). Both judges scored all 144 runs.

| | base (staged prompt) | trained (version 1) | trained minus base, paired, 95% case-cluster bootstrap |
|---|---|---|---|
| Claude | 0.48 | 0.89 | +0.41 [0.24, 0.57] |
| Codex | 0.66 | 1.29 | +0.63 [0.43, 0.84] |
| **mean of judges (primary)** | **0.57** | **1.09** | **+0.52 [0.33, 0.70]**, 72 pairs, 24 cases |

Agreement: Spearman 0.95 over 144 episodes, mean absolute difference 0.30. By company (mean of judges): kingspan
+1.09, mettler +1.10, tennant +1.05, ansell +0.67, laerdal +0.64, hach +0.55, winterhalter +0.50, belimo +0.30, testo
+0.29, draeger +0.19, frankecoffee -0.05, hoshizaki -0.10: higher for 10 of 12.

## 2026-11-11: a second Codex judge on gpt-6-sol, for the exploratory version 3 comparison (Hatem: "use sol")

The frozen Codex judge (gpt-6-astra) exhausts the ChatGPT Plus allowance after about 120 judgments, so the 340 version
3 judgments would take about a day of resets. A new backend `codexsol` (judge-v1-four-backends-4): gpt-6-sol through
the same pinned CLI 0.166.0, sandbox, prompt and settings (reasoning effort medium); only the model differs. Qualified
under the same scoring rule on the same 40 packets (`reports/judge/codexsol_score_qualification.json`: sound above
flawed in 20 of 20 clusters, 0 invalid, no retry). It is a different judge from `codex`: the final test and test set 2
keep their Claude and gpt-6-astra results; codexsol scores base, version 1 and version 3 together on both version 3
packet sets, and its scores are reported beside the Claude Code judge's, never mixed with gpt-6-astra's. The 50 or so
gpt-6-astra judgments already made on the test set 2 version 3 packets are kept and not used.

## 2026-11-11: dig then reason with the status check: the app default, and its test (Hatem: "make it the default in the app. combine it with the status check and test it properly")

Fixed before any run of the combination. **The system:** one server holds versions 1 and 3; version 1 writes the
brief, frame, status, status-reading and evidence stages, version 3 every later stage (route
`default=1,brief=0,frame=0,status=0,status_reading=0,evidence=0`), with the status check on (final rule of 17:55).
- **Development first** (15 cases, 3 attempts, the two-adapter server): the combination, compared with the judged
  arms of the switching test (v1, v3, dig_then_reason without the status check). A check that the combination runs,
  not a selection: the rule and the status design are already fixed.
- **Test: test set 2** (12 companies, 24 cases, 3 attempts, 72 runs per arm). No fresh held-out companies exist and
  building a third set takes about a day, so test set 2 is used, with this stated: the routing rule was chosen on
  development only and the status check was designed on development and Aquaporin (final test), so nothing in the
  system was selected on test set 2; but test set 2 has been run before (v1, base, v3), and we know v3 scores higher
  than v1 there. Arms run now: `combined` (the system) and `dig` (the route without the status check, to separate the
  two changes). Compared with the frozen base, v1 and v3 runs of the same cases and attempts.
  Primary: combined minus v1, paired, mean of the Claude Code and gpt-6-sol judges, 95% case-cluster bootstrap, all
  five arms judged together blind. Also: combined minus v3, combined minus dig, finished runs, refusals.
- **Final test, secondary and labelled:** the same two arms on the 16 cases; Aquaporin informed the status check, so
  its numbers there are a diagnostic of the fix (reads the insolvency records, what it recommends), not a test.
- Whatever the result, version 1's frozen results stand; the paper reports this as a system built after them.

## 2026-11-11: teacher run stopped; Unsloth fair-test result

- **Teacher run with the status check stopped before it produced data** (Hatem, 19:25: "no need for the new data
  generation with the teacher. stop it and let's start finalizing stuff"). Jobs 755231 (40 GB worker, still downloading
  the model) and 755090 cancelled. No version 4 is trained for the submission; the status check is evaluated at run
  time with versions 1 and 3.
- **Unsloth, 60 steps on 240 rows, same LoRA and seed (job 755239):** median seconds per step after step 10: current
  trainer 5.87; Unsloth 4.50 with its offloading checkpointing and 4.50 with standard checkpointing (23% faster).
  Peak memory 11.6 GB against 8.1 and 8.9. Losses agree to within 0.003 at the steps compared. The 12-step test above
  was dominated by start-up. A future training run can use it; none is planned before the submission.

## 2026-11-11 (22:30): version 3 on test set 2 with the gpt-6-sol judge; combined-system runs finished, judging started

- **Version 3 on test set 2, two judges (exploratory; base, v1 and v3 judged together blind, 72 runs per arm).**
  Claude Code judge: base 0.49, v1 0.86, v3 1.22. gpt-6-sol: base 0.63, v1 1.27, v3 1.74. Mean of judges: base 0.56,
  v1 1.06, v3 1.48; v3 minus v1 +0.42 [0.24, 0.60] (71 pairs, 24 cases), v3 minus base +0.92 [0.82, 1.02], v1 minus
  base +0.49 [0.29, 0.69]. Judges: Spearman 0.93 on 215 runs, mean absolute difference 0.36. v3 is higher than v1 at
  10 of 12 companies (mettler -0.10, tennant -0.07). Reports: `reports/judge/test2_v3/report_claudecode_codexsol_*.json`.
  Sol on the final-test v3 packets stands at 94 of 135 (usage limit); it continues hourly.
- **Combined system, runs done** (jobs 755268, 755269, 755270, 755289, 755347, revision 64975a1). Finished runs, before
  any judging: test set 2 combined 37 of 72, dig 43 of 72; final test combined 27 of 48, dig 27 of 48; development
  combined 20 of 45. Every combined run called the status check (72, 48 and 45). Aquaporin (diagnostic, 12 runs per
  arm): combined finished 5, 3 "do not invest" and 2 "invest"; dig finished 8, 7 "invest" and 1 "do not invest".
- **Judging as planned:** `reports/judge/system_test2` (342 packets from 360 runs) and `reports/judge/system_final`
  (231 from 240): base, v1, v3, combined and dig together, blind, keys outside the repository until both judges end.
  Claude Code judge first, then gpt-6-sol through `experiments/codex_judge/run.py system_test2 system_final`.

## 2026-11-11 (23:15): the combined system on test set 2, both judges: the primary comparison is not met

Five arms judged together blind (342 packets from 360 runs, 72 runs per arm, 24 cases), Claude Code and gpt-6-sol,
no judgment missing. Mean of judges: base 0.56, v1 1.07, combined 1.28, dig 1.43, v3 1.48 (Claude Code: 0.48, 0.87,
1.07, 1.16, 1.21; gpt-6-sol: 0.63, 1.26, 1.49, 1.70, 1.74). Spearman between judges 0.90 on 360 runs.
- **Primary, combined minus v1: +0.22 [-0.00, 0.46]**, 72 pairs. The interval includes zero: not shown better than v1.
  By company: higher at 7 of 12 (hoshizaki +1.19, frankecoffee +0.94, belimo +0.82), lower at 5 (winterhalter -0.42,
  ansell -0.24).
- Combined minus v3: -0.20 [-0.38, -0.01]. Combined minus dig: -0.15 [-0.35, 0.06]. Dig minus v1: +0.36 [0.22, 0.51].
  Combined minus base: +0.73 [0.52, 0.93].
- Reading: on test set 2 the route adds nothing over version 3 alone (dig 1.43 against v3 1.48), unlike development,
  and the status check costs about 0.15, with fewer finished runs (37 of 72 against 43). Version 1's frozen results
  stand. The final-test packets (secondary, labelled) are still being judged.
- A full disk at 23:04 (a local container build) stopped both judges; 3 gpt-6-sol and 4 Claude Code attempts written
  empty were archived as `*_archived_disk_full` and rerun. No completed judgment was affected.

## 2026-11-11 (23:40): the public repository carries the dossier as it is

Hatem: "keep them as they are and publish them". The public build (`scripts/release/build_public_repo.py`) no longer
cuts dossier excerpts to one short quote; the public dossier is byte-identical to the private one, so public runs read
what the evaluated runs read and the frozen digests apply. Personal and internal identifiers are still replaced, and the
third-party papers stay out. The Hugging Face dataset published on 2026-11-08 still has the cut excerpts.

## 2026-11-11 (23:45): the combined system on the final test, Claude Code judge (secondary, labelled; gpt-6-sol pending)

231 packets from 240 runs, all valid. Claude Code judge, 48 runs per arm: base 0.54, v1 1.18, dig 1.13, v3 1.06,
combined 1.03. Paired, 95% case-cluster bootstrap: combined minus v1 -0.15 [-0.32, 0.01] (aqp -0.48, rational -0.23,
epro -0.06, simo +0.18); dig minus v1 -0.06 [-0.23, 0.12]; combined minus v3 -0.03 [-0.18, 0.14]; combined minus dig
-0.09 [-0.30, 0.12]; v3 minus v1 -0.12 [-0.27, 0.02]; v1 minus base +0.64 [0.49, 0.78] (the API judge gave +0.64 on
the frozen campaign). gpt-6-sol stands at 68 of 231 on the Codex usage limit and retries hourly; the two-judge numbers
replace these when it ends. Reading: no later system is distinguishable from version 1 on the final test, and on test
set 2 version 3 and dig are higher; nothing built after version 1 is shown better on both sets.

## 2026-11-12: the app default is dig then reason without the status check (Hatem: "yes")

On both test sets dig then reason scored higher without the company status check than with it (test set 2, two
judges: 1.43 against 1.28; final test, Claude Code judge: 1.13 against 1.03), and it is the best later system overall
(clearly above version 1 on development and test set 2, level on the final test). The app's default `system` model
therefore runs version 1 for the brief, frame and evidence stages and version 3 after, with the status check off;
`STATUS_CHECK=1` turns it on. Applied locally and on the hosted demo. Version 1 remains the evaluated model.

## 2026-11-12 01:10: version 4, recovery distillation for the reasoner (Hatem: "explore distilling more data ... make the model reason better"; registered before any run)

Why: version 3 reasons better than version 1 when it gets there, but it learned the second teacher's direct style
without recovery: when a call is refused it repeats it (24 of 32 final refusals on its screen were a repeated search),
and about 4 in 10 runs of every trained system stop before a recommendation. Recovery is mechanically checkable, so a
free teacher (Command A+ on the cluster; no paid API, no Claude or Codex output as data) can supply it.

1. **Harvest** (training companies only; no validation, final-test or test-set-2 company): the deployed system, dig
   then reason without the status check (version 1 for brief, frame and evidence, version 3 after), on the training
   cases, one attempt, the evaluated settings (compact prompt, 45 turns, 4 refusals in a row).
2. **States and corrections** (`aemon.teacher.corrections`, protocol correction-v1, unchanged): the states that start
   a loop (a repeat refused, a third read, a second refusal in a row) in the stages version 3 writes; Command A+
   answers each; a correction is kept only if it replays as accepted, repeats nothing and names what it acts on.
3. **Version 4**: version 3 continued on its own DeepSeek rows plus the kept corrections (corrections at most 20% of
   rows), one pass, the v3 learning rate and seed. Conversion gate v2 as for every adapter.
4. **Development screen**: dig then reason with version 3 against dig then reason with version 4 as the reasoner, the
   15 development cases, 3 attempts, one server holding both, judged together blind by the Claude Code judge.
   **Adopted as the reasoner** only if all three hold: blind quality not lower (v4 minus v3 point estimate >= 0),
   refused calls per run lower, finished runs not fewer. Otherwise version 3 stays.
5. If adopted: test set 2 and the final test, labelled exploratory (both sets have been run before), both judges
   where the Codex limit allows. Version 1 stays the frozen, headline model whatever happens.

## 2026-11-12 02:00: corrections to earlier entries, found by a number audit (the entries above are left as written)

- The 11 November status-check entry says "all 144 Aquaporin final-test runs"; it is 36 (12 base, 12 v1, 12 v3). The
  insolvency announcement did appear in search results (in all 12 base runs) but no run of the first test opened it,
  and version 3 read it in 4 of 12 runs and still recommended investing. "Never appeared in a search result" and "no
  version 3 run found" are wrong; "no v1 or base run read it" is right.
- The 11 November 00:05 entry's 288 DeepSeek investigations: 266 ran, 154 finished, 112 did not, and 22 more were
  harness errors (the 288).
- Version 2 was trained (job 752833) and stopped at its screen; the reliability report predates that round.
- Several 10 November entries are out of time order in this file; their timestamps are right.

## 2026-11-12 02:10: version 4 timing cut-off (registered before any correction exists)

The teacher step may take 10 to 25 hours on the free slices. To leave time for the screen before the deadline,
version 4 trains on the corrections kept by **13 November 14:00 CET**, whatever their number (batches unfinished then
are left out and named). If fewer than 50 are kept by then, version 4 is not trained and the plan is reported as not
completed.

## 2026-11-12 02:50: loop guards at decoding time (registered before any screen run)

**Why.** In the final-test runs of the default (dig then reason), 233 of 274 refused calls are repeats (130 repeated
searches, 103 re-assessments of a pair already assessed) and 33 are misquotes; for the combined system 213 of 322
are repeats and 94 misquotes. A run stops after 4 refusals in a row, so these loops are what "repeated errors" means.
The final-test numbers were read only to find the failure; nothing below is run on either frozen test set.

**What (development only, `--recovery`, off as evaluated; `agent/recovery.py`, `agent/loop.py`):**
- `no_repeats`: assess_evidence offers, per theory, only the sources not yet assessed for that theory.
- `quote_menu`: assess_evidence's quote is one of the sentences of the chosen source, so it cannot be misquoted.
- `resample_repeats`: a call the environment refuses as an exact repeat changed nothing, so the same state is drawn
  again (temperature 0.8, new seed), at most 3 times, before the refusal counts toward the stop. Every refused draw stays
  in the record, marked `redrawn`, and in the refused-call count.
No guard, stage rule, budget or stop is changed. A replay of the 45 development dig-then-reason runs found that
withdrawing the search tool after a repeated search would also have blocked 42 accepted calls, so that variant was
dropped before any live run.

**Screen.** Laptop GPU (the 4-bit base, the app's runtime), both arms on the same server: dig then reason as it is
against dig then reason with all three guards, the 15 development cases of the switching screen, 3 attempts, judged
together blind by the Claude Code judge (Sol as well if its limit allows). **Adopted as the app default** only if all
hold: finished runs more, refused calls per run lower, blind quality not lower (guarded minus plain point estimate >= 0).
If adopted, it is run on test set 2 labelled exploratory (that set has been run before). Version 1 stays the frozen,
headline result whatever happens.

## 2026-11-12 04:05: combined system and dig then reason on the final test, both judges

The second judge (Codex, gpt-6-sol) finished the 231 final-test packets at 04:00 (five rounds across usage limits; no
packet missing). Mean of the two judges, 48 runs per arm, case-cluster bootstrap, Spearman 0.82 between the judges:
base 0.61, version 1 1.45, dig then reason 1.44, version 3 1.35, combined 1.32.
- dig then reason minus version 1: −0.01 [−0.20, 0.18]; combined minus version 1: −0.13 [−0.32, 0.05];
  version 3 minus version 1: −0.10 [−0.27, 0.05]; dig then reason minus version 3: +0.09 [−0.10, 0.27].
- Every trained arm stays far above the base: version 1 +0.85 [0.68, 1.00] (this re-judging; the frozen result is
  +0.83 [0.69, 0.97]), dig then reason +0.84 [0.69, 0.96], combined +0.71 [0.53, 0.91].
- Per judge: Claude Code ranks version 1 first (1.18 against dig 1.13), Sol ranks dig first (1.76 against 1.72).

**Decision:** the one-judge reading of 23:45 stands with both judges: no later arm is distinguishable from version 1 on
the final test. Version 1 stays the headline model; dig then reason stays the app default as the most consistent later
system (above version 1 on test set 2 and development, level on the final test). The keys of system_test2 and
system_final (and screen3) are now published, since every judge has finished.

## 2026-11-12 05:10: loop guards, a third arm (registered after the guarded runs, before any judging result)

Mechanical result of the screen (not yet judged): plain 28 of 45 finished, 17 stopped on repeated refusals, 234
refused calls; guarded 33 of 45 finished, none stopped on refusals, 12 hit the turn limit, 139 refused calls (every
one a repeat that was redrawn). In the 12 turn-limit runs the refusal loop became an assessment loop: with repeats
masked, the model weighs every source for every theory ("neutral"), 8 of them at the test step, until 45 turns.
The budget guard of the recovery study (`budget`: exploration withdrawn when turns left <= what the step still needs
+ 3) targets exactly this (stage 1: 6 of 6 test-step dead ends rescued). **Third arm:** guarded + budget, the same
cases, seeds and server, judged blind against the other two together. The registered rule (02:50) is applied to
guarded vs plain as written; guarded + budget is judged against plain under the same three conditions, labelled as
selected after seeing the guarded runs.

## 2026-11-12 05:20: loop guards adopted (development screen, Claude Code judge, blind)

guarded minus plain: **+0.036 [−0.083, 0.151]**, 45 pairs, 15 cases (plain 1.129, guarded 1.166); higher at 5 of 6
companies (ACR +0.23, Tanita +0.23, Jotun +0.23, Neumann +0.17, Deere +0.07), lower at Hellberg (−0.27). Finished 33
against 28; refused calls per run 3.1 against 5.2; finished runs with no invented number 20 of 33 against 13 of 28.
All three registered conditions hold, so **the loop guards are adopted**: on for the app's default system (LOOP_GUARDS=0
turns them off), and run on test set 2 as registered, labelled exploratory, plain and guarded on the same laptop server
with the same seeds, judged blind together. The runner now accepts exactly these three features on test set 2 and
still refuses every experimental feature on the final test. Version 1 stays the headline result.

## 2026-11-12 06:40: guards + budget, development, both judges: adopted

The third arm (registered 05:10) finished **45 of 45** runs (plain 28, guarded 33), refused calls per run 3.1 (plain
5.2), finished runs with no invented number 26 (plain 13), experiment check passed 17 (plain 12). Judged blind by both
judges: 23 of its 45 packets are byte-identical to packets already judged (the budget guard never acted in those runs),
so they keep those judgments and the 22 new packets were judged by both judges (none missing); the three arms are
reported from the merged key and predictions.
- guards + budget minus plain: **+0.194 [0.097, 0.302]** (Claude Code +0.135 [0.056, 0.219], Sol +0.252
  [0.131, 0.393]); higher or level at all six companies (Hellberg +0.01).
- guards + budget minus guards: +0.102 [0.031, 0.178]. Plain 1.42, guards 1.52, guards + budget 1.62 (mean of judges).
- The two-judge result for guarded vs plain: +0.092 [−0.052, 0.238] (Sol +0.148, Claude Code +0.036).
All three conditions hold against plain, so **guards + budget is adopted**: it becomes the app default (LOOP_GUARDS=0
turns all four off) and runs on test set 2 as a third arm, labelled exploratory and as selected after seeing the
guarded runs. The 9 November study found the budget guard alone did not raise quality on version 1 (+0.006); with the
loop guards and the v3 reasoner it does here, on development. Version 1 stays the headline result.

## 2026-11-12 07:10: loop guards on test set 2 moved to the cluster

At 06:50 the laptop ran out of memory and its model server was stopped mid-run: the plain test set 2 arm had 26 of
72 runs, 46 failed in the harness (kept as `experiments/loop_guards/test2/laptop_aborted_*`, not used). The test set 2
run moved to the cluster, the evaluated bf16 runtime: the plain arm is the existing dig-then-reason run of test set 2
(`system_test2_dig`, the same route, settings and seeds, already judged by both judges), and the two guard arms are
jobs 756273 (guards) and 756274 (guards + budget), code 731c3c5. One version 4 teacher worker (756018) was cancelled
to free the slot; its unfinished batch is requeued by the driver. Packets identical to ones already judged keep their
judgments; the rest are judged by both judges. The rules of 02:50 and 06:40 apply unchanged.

## 2026-11-12 10:35: loop guards on test set 2, both judges (exploratory)

Jobs 756273 and 756274 finished (cluster, bf16, 24 cases × 3 attempts). Of the 144 packets, 71 were byte-identical to
packets of system_test2 already judged and keep those judgments; the 73 new ones were judged blind by both judges,
none missing. The pipeline's Sol retry check miscounted (a `grep -c || echo 0` printed two zeros) and started an
unneeded hour-long wait after Sol had judged all 73, so it was stopped and the reports were written by hand with the
same commands (`experiments/loop_guards/test2/report_both_*.json`).
- Finished: plain 43, guards 62, guards + budget 63 of 72. Refused calls per run 6.1, 3.5, 3.5. Finished with no
  invented number 34, 53, 50. Experiment check passed 14, 29, 26.
- Mean of judges: plain 1.427, guards 1.584, guards + budget 1.589.
- guards + budget minus plain: **+0.162 [0.049, 0.272]** (Claude Code +0.124 [0.023, 0.223], Sol +0.200
  [0.069, 0.329]). guards minus plain: +0.157 [0.045, 0.266] (Claude Code +0.119, Sol +0.194). guards + budget minus
  guards: +0.006 [−0.010, 0.022].
- Lower at Testo for both judges (−0.317, mean of judges), level at Kingspan; judge agreement Spearman 0.65.
Reading: the development result holds on test set 2 for the guards; the budget guard's development gain does not
reappear (few guarded runs reach the turn limit here). Exploratory, since the set had been run before and the guards
were built after every frozen result. Version 1 stays the headline result; the app default is unchanged (guards + budget).

## 2026-11-12 11:35: quote-menu bug fixed; guards + budget rerun on test set 2 (registered before the run)

Reading the unfinished guarded runs of test set 2: all 6 Belimo runs of each guarded arm stopped at the assessment
stage on four `arguments` refusals in a row ("quote at least 3 words and 15 characters"). The quote menu offered every
excerpt sentence of 12 to 420 characters, so a dateline ('DANBURY, Conn.', 2 words, 14 characters) was on the menu,
the model picked it, and the environment refused it each time. This is a bug in the guard, not a model failure: the
menu was meant to hold only quotes the environment accepts. No development run was affected (0 such refusals in the
90 guarded development runs); on test set 2, 24 refusals in 6 runs per arm, every one of those runs stopped by it.

**Fix** (`agent/recovery.sentences`): the menu holds only sentences the environment accepts (at least 3 words and
MIN_QUOTE characters once normalised, at most 420). Nothing else changes.

**Run.** The guards + budget arm (the app default) again on test set 2 with the fix, same route, settings, seeds,
cases and attempts (cluster, bf16); runs whose menus did not change are expected to reproduce byte for byte and keep
their judgments; the rest are judged blind by both judges together with the existing plain arm. Reported as a corrected
rerun next to the 10:35 result, which stays in the record unchanged; labelled exploratory (test set 2 has now been used
to find this bug). Nothing is adopted or dropped on this result: the guards stay the app default either way.
A second pattern, not fixed: 2 Testo runs per arm loop between a repeated search (redrawn) and an accepted re-read of
a source until the turn limit; a reread mask was tested on 9 November and did not raise quality, so it is left alone.

## 2026-11-12 13:18: corrected guards + budget rerun on test set 2, result (exploratory)

Job 756932 (code 4573c82), as registered at 11:35. 66 of 72 runs reproduced the earlier guards + budget arm call for
call and kept their judgments; the 6 that changed are exactly the Belimo runs, all of which stopped on the dateline
before and all of which finish now. The 6 new packets were judged blind by both judges (140 packets, none missing).

| Arm (72 runs) | Finished | Refused/run | No invented number | Experiment check | Mean of judges | Claude Code | gpt-6-sol |
|---|---|---|---|---|---|---|---|
| As evaluated | 43 | 6.1 | 34 | 14 | 1.427 | 1.158 | 1.696 |
| Guards + budget (10:35) | 63 | 3.5 | 50 | 26 | 1.589 | 1.282 | 1.896 |
| Guards + budget, quote fix | 69 | 3.2 | 55 | 28 | 1.638 | 1.322 | 1.954 |

- Fixed minus as evaluated: +0.211 [0.088, 0.334] (Claude Code +0.164 [0.054, 0.279], gpt-6-sol +0.259 [0.115, 0.402]).
- Fixed minus before the fix: +0.049 [0.000, 0.129]; by company, Belimo +0.59 and every other company 0.
- Judge agreement over the 216 runs: Spearman 0.588, mean absolute difference 0.594.
- Reported next to the 10:35 result, which stays unchanged. Exploratory. Nothing adopted or dropped: the guards (with
  the fixed quote menu) were already the app default. Files: experiments/loop_guards/test2_fix/.
