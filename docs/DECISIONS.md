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
