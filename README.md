# aemon

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/figures/aemon-wordmark-dark.png">
  <img alt="aemon: weigh what is known. test what is not." src="docs/figures/aemon-wordmark.png" width="420">
</picture>

*weigh what is known. test what is not.*

**Teaching a 3B model to investigate a strategy question, with AgentTune and AuditKIT.**
Team Two-eyed Ravens · Lexsi AI Hackathon, Track 3 (Agentic Fine-Tuning) · November 2026

> **Result in one line.** On four companies it never saw, in the same environment with the same tools, stage
> controller and budgets (each arm with the prompt format it does best with), the fine-tuned Tiny Aya agent scored **1.48** against the best-prompted base model's **0.65** on a 0–3 blind LLM rubric (mean of two judges;
> difference **+0.83, 95% interval 0.69 to 0.97**), and was higher at every company. A second frozen test on twelve
> more companies gave **+0.52 [0.33, 0.70]**. Sixteen companies support only a limited claim about generalisation,
> and nothing here is about business outcomes.

| | |
|---|---|
| **Live demo** | **[saadallah-r-hatem--aemon-serve.us-east.modal.run](https://saadallah-r-hatem--aemon-serve.us-east.modal.run/)** (sign in with the test account from our submission; it runs on CPU and sleeps when idle, so the first page takes a moment; finished investigations open at once, a new one takes about 15 minutes, and it runs one at a time for everyone) |
| Model | [HatemSaadallah/tiny-aya-global-strategy-agent](https://huggingface.co/HatemSaadallah/tiny-aya-global-strategy-agent) |
| Dataset | [HatemSaadallah/strategy-agent-investigations](https://huggingface.co/datasets/HatemSaadallah/strategy-agent-investigations) |
| Collection | [aemon: a strategy-investigation agent](https://huggingface.co/collections/HatemSaadallah/strategy-investigation-agent-6af0d2ab19339ae58d020326) |
| Paper | [docs/PAPER.pdf](docs/PAPER.pdf) |
| Every test run, browsable | [first test](docs/replays/final/README.md) (96 runs) and [second test](docs/replays/test2/README.md) (144 runs), base and fine-tuned side by side, no GPU needed |
| Every decision, dated | [docs/DECISIONS.md](docs/DECISIONS.md) |

| **+0.83** | **+0.52** | **28 of 48** | **$0.03** | **26×** |
|:---:|:---:|:---:|:---:|:---:|
| blind quality over the best-prompted base model on the first frozen test (0–3 scale, 95% interval 0.69 to 0.97) | on a second frozen test, 12 more unseen companies (0.33 to 0.70) | investigations finished with an accepted recommendation, against 4 of 48 for the base model | per investigation, self-hosted on one A100 slice: about 8 times less than the closed model we measured | faster than its teacher per GPU |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/figures/quality-dark.png">
  <img alt="Blind quality score on the final test: base model 0.65, fine-tuned 1.48 (mean of two judges)" src="docs/figures/quality-light.png" width="720">
</picture>

![The reasoning map of one investigation: question, rival hypotheses, the evidence weighed for each, the challenge, the proposed test and the recommendation](docs/figures/ui/redesign/after/map.png)

**A judge's 60-second view**
1. Open the [first test's run gallery](docs/replays/final/README.md): every case, base and fine-tuned side by side, with
   how each run ended and its blind scores.
2. Click the filter "fine-tuned finished, base did not" (25 of 48 pairs) and open any pair.
3. Read one fine-tuned investigation end to end, for example [Simonelli](docs/replays/trained_simo-base_1.md): every
   tool call, what the environment refused and why, and the recommendation. It shows both halves of the result: every
   step of the procedure is there, and at step 23 a quote saying cafés offer what a home cannot is counted as support
   for a home machine, from a blog post labelled an independent study.
4. Then the filter "fine-tuned scored lower than base" (3 of 47 pairs), and section 7 for what still fails.

**Paired, case by case.** On the first test the fine-tuned agent scored higher than the base model on all **16 of 16
cases** and in 44 of 47 paired runs (exact sign test, p = 2.5e-10); on the second test on 20 of 24 cases (3 lower, 1
equal) and 49 of 72 runs (`reports/judge/*/paired_counts.json`, mean of two judges).

**In brief**
- **What it is.** A 3.35B-parameter open model that investigates a strategy question step by step inside an
  environment that checks its work: every quote must match a source, rival explanations must differ, and a simulated
  result cannot stand in for real evidence.
- **How it was made.** A stronger teacher (Command A+) ran investigations through the same tools; only runs that
  replay exactly became training rows; AgentTune distilled them into a LoRA adapter; AuditKIT replays every
  evaluation run.
- **What was measured.** Two frozen, run-once tests on 16 unseen companies, scored blind by two LLM judges that first
  had to rank sound investigations above flawed ones. The gain holds when whole companies are resampled (+0.83, 95%
  interval 0.44 to 1.23 on the first test, a rough interval with 4 companies) and grows when each pair is compared only
  on the stages both runs reached (+0.92), so the base model is not losing only by running out of context.
- **It learns the procedure, not yet the judgement.** The largest gains are in framing the decision and stating
  distinct causal theories. But on the first test every finished recommendation scored 1 of 3 from both judges (all
  28 fine-tuned, and the base model's 4): the agent now reaches a conclusion by a sound route far more often, and the
  conclusion itself is still weak. Part of the ceiling is the teacher's: 74% of the recommendations it was trained on
  use a number from no source.
- **What it costs.** About $0.03 and 66 seconds per investigation on one A100 slice, roughly 8 times less than the
  closed model we measured.
- **What does not work yet.** As evaluated, version 1 stops before a recommendation in 20 of 48 runs on the first test
  and 40 of 72 on the second, and almost none pass every mechanical check. Section 7 says why.
- **After the tests (exploratory, [docs/LATER_WORK.md](docs/LATER_WORK.md)).** A two-adapter system ("dig then
  reason": version 1 gathers the evidence, a second adapter trained with another teacher reasons) is above version 1 on
  the second test (+0.36 [0.22, 0.51]) and level on the first. Decoding-time guards on top of it finish far more runs
  (45 of 48 and 69 of 72) and add +0.12 to +0.21; steering how a source is weighed raises the evidence scores. None of
  it improves the conclusion itself. The app runs this system; version 1 is the result we stand behind.

The agent is Tiny Aya Global fine-tuned on a teacher's investigations to work through a strategy question the way a
careful analyst would. The name is a nod to Maester Aemon, a counsellor known for sound judgement in unusual
situations.

**Contents:** [1 Problem and approach](#1-problem-and-approach) · [2 Hackathon repositories used](#2-hackathon-repositories-used) ·
[3 Models and licences](#3-models-and-licences) · [4 Data, cases and licences](#4-data-cases-and-licences) ·
[5 Model artifacts](#5-model-artifacts) · [6 Data artifacts](#6-data-artifacts) ·
[7 Experiments and findings](#7-experiments-and-findings) · [8 With more credits](#8-with-more-credits) ·
[9 Team](#9-team) · [Run it](#run-it) · [Reproduce](#reproduce)

---

## 1. Problem and approach

Asked whether a manufacturer should take its technology into a new market, language models tend to produce
consulting prose: lists of factors, confident market sizes with no source, and evidence collected only for the answer
they started with. Strategy research describes a better habit (Camuffo, Cordova, Gambardella and Spina, 2020, *A Scientific
Approach to Entrepreneurial Decision Making*, Management Science; Camuffo, Gambardella and Pignataro, 2024,
*Theory-driven strategic management decisions*, Strategy Science): frame the decision and its real alternatives; state rival causal
theories of who would change their behaviour and why; derive predictions that tell the theories apart; look for
evidence against the favoured theory; design a test with a decision rule when information is worth its cost; and
revise when new evidence arrives.

**Track 3 problem statements addressed:** mainly *agentic distillation* (a stronger teacher's agent trajectories
distilled into a small local student), with *workflow and decision agents* (a multi-step investigation with rules and
a full audit trail). It does not make trajectories shorter: the fine-tuned agent makes more calls per run than the
base model (35 against 20), because it gets much further before it stops.

**The question we test:** can agentic fine-tuning teach that procedure to a small model, beyond what a stage controller
and the best prompt already achieve?

**The framework behind the procedure.** Camuffo, Gambardella and Pignataro (2024) formalise a theory as a restriction
on beliefs: stating that one thing causes another rules out parameter values, which raises or lowers the expected
value of acting, and an experiment is worth running only while the theory's value is close to its rival's. The paper
([docs/PAPER.pdf](docs/PAPER.pdf), section 2) works through their example.

**How the agent carries this out.** The agent follows these steps in words, with tools and evidence; neither it nor
the harness computes a Bayesian update, because that would need an invented network and invented numbers, and assumed
ratios could create the very revision we want to measure. Instead, when it states its position and again after a
what-if result, the agent rates each theory on a five-point scale (very unlikely, unlikely, uncertain, likely, very
likely). The scale is a signal within one run, not a calibrated probability.

**The setup.**
- **An investigation environment** with twelve tools (`read_brief`, `frame_problem`, `search_evidence`, `read_source`,
  `add_theory`, `assess_evidence`, `challenge_theory`, `propose_test`, `decline_test`, `state_position`,
  `revise_theory`, `finish`) over a dossier of public records (1,334 when version 1 was trained and first tested; 1,958 now). Quotes must match a source exactly; theories must
  give distinct causal explanations; a simulated what-if result may change beliefs but cannot support a recommendation
  about real demand. Refused calls return the reason.
- **A stage controller** that offers the tools of the current stage: brief, frame, read, theories, assessment,
  challenge, test, position, new evidence, conclusion.
- **A teacher**, Command A+ (Apache 2.0), run with llama.cpp on an NVIDIA A100 (80 GB) through the same tools. Every teacher
  investigation is replayed against the environment, and only investigations that replay exactly and reach an
  accepted finish become training data.
- **The student**, Tiny Aya Global, fine-tuned with AgentTune (LoRA) on the teacher's tool calls, then evaluated with
  AuditKIT, executable checks and two blind LLM judges.

## 2. Hackathon repositories used

**AgentTune** (`src/aemon/training/train.py`, `training/masking_gate.py`)
- `agenttune.agentic.distill_trainer.create_distill_trainer` builds the distillation trainer (TRL SFT with PEFT LoRA)
  from our rows; `agenttune.agentic.events` (`Event`, `EventLog`) is the format each evaluated run is converted to
  for AuditKIT.
- Loss is computed only on the target tool call; the context is masked. A masking gate checks this on real rows before
  any training run.

**AuditKIT** (`src/aemon/evaluation/diagnostics/audit.py`)
- `AgentEvalRunner`, `AgentCase`, `AgentEvalSpec` and `episode_from_eventlog` run every evaluation episode through
  AuditKIT; a `CustomPredicate` replays the full event log through our environment and requires every tool result to
  reproduce.
- Diagnostic scorers on every run: `tool_call_validity`, `redundant_tool_calls`, `agent_loop_detection`,
  `tool_permission`. Every development and final report carries an `auditkit` block; all 22 run reports in `reports/judge/` show 0 replay mismatches.

**CuratorKIT** (`src/aemon/rows/curate.py`)
- Decides which training rows to keep and never rewrites one: exact deduplication on (state, target call) and its
  secrets gate, with its run record (manifest, provenance, checksums). On version 1's rows it keeps 3,958 of 4,302;
  all 344 dropped rows are exact duplicates. It was added after the evaluated adapters were trained, for the next
  training run, so the results below do not depend on it.

The three connect: AgentTune trains on rows built from teacher runs that replay exactly in our environment; every
evaluated run is converted to AgentTune's event-log format and replayed by AuditKIT against the same environment; and
CuratorKIT filters the rows.

## 3. Models and licences

| Model | Role | Version | Licence |
|---|---|---|---|
| Tiny Aya Global (CohereLabs) | student | `CohereLabs/tiny-aya-global`, revision af89d21; bf16 GGUF for evaluation | CC-BY-NC-4.0 |
| Command A+ (Cohere) | teacher | Q4_K_M GGUF (about 135 GB), weights sha256 recorded in every row | Apache 2.0 |
| Claude (Anthropic, `claude-opus-5-5`) | blind judge; earlier, a workflow control | API | proprietary; **no Claude output is ever training data** (provider terms), enforced by the provenance checks |
| Codex (OpenAI, `gpt-6-astra`, codex-cli 0.166.0) | blind judge | CLI, sandboxed, no repository access | proprietary; evaluation only |
| DeepSeek V4-Pro (`deepseek-v4-pro`) | second teacher, for the exploratory version 3 only | hosted API | proprietary; its investigations pass the same replay checks |
| Claude Code (`claude-opus-5-5`) and Codex (`gpt-6-sol`) | blind judges for the exploratory comparisons | CLI, no tools, no repository access | proprietary; evaluation only; each qualified separately (19 of 20 and 20 of 20) |

## 4. Data, cases and licences

- **Dossier** (`data/dossier/evidence.json`): public records, each with its URL, date and an excerpt. Version 1 was
  trained and first tested on 1,334 of them (935 independent observations, such as standards, regulatory filings,
  studies and trade press; 399 company claims, kept apart so a theory cannot rest only on what a company says about
  itself). With the second test's companies and the later training cases it now holds 1,958 (1,246 and 712). Records
  written after a decision date are flagged.
- **Cases**: when version 1 was trained, 137 development cases on 64 companies, plus 16 held-out cases on 4 companies
  (207 development cases on 99 companies now, after the cases written for version 3). Each case is a company and a
  question with search and test budgets, and some deliver a what-if result after the agent states a position
  (irrelevant, supporting or undermining). Every case declares in advance whether a test is worth its cost.
- **Splits by company**: for version 1, 58 training companies, 6 validation companies (Hellberg, Neumann, Jotun, Tanita, Deere, ACR)
  for the development choices, and 4 final-test companies (Aquaporin, Electrolux Professional, RATIONAL, Simonelli),
  frozen by digest (`docs/final_test_freeze.json`, dce26d4f…) before any model ran on them.
- **Training data**: 174 accepted teacher investigations, giving 4,302 rows (other teacher totals below count different
  sets: 223 is every finished teacher investigation, 205 those on training companies); training used the 3,891 rows from 158
  investigations on 57 training companies, plus 51 correction rows (a teacher showing a valid next step from a state
  where the student had looped). The 411 validation rows were kept out.
- **Second test set**: 24 cases on 12 further companies, frozen by digest (`docs/test2_freeze.json`) before any run.
- **Rights**: excerpts are short quotations from public sources (median 24 words, at most 100), each with its
  publisher and link. The dossier is published in full, so anyone can rerun what the evaluated runs read.

## 5. Model artifacts

Collection: [aemon: a strategy-investigation agent](https://huggingface.co/collections/HatemSaadallah/strategy-investigation-agent-6af0d2ab19339ae58d020326).
Model: [HatemSaadallah/tiny-aya-global-strategy-agent](https://huggingface.co/HatemSaadallah/tiny-aya-global-strategy-agent)
(a derivative of Tiny Aya, so CC-BY-NC-4.0):
- the LoRA adapter (`adapter_model.safetensors`, `adapter_config.json`; sha256 740c4a9b…);
- the converted GGUF adapter for llama.cpp (`tiny-aya-global-strategy-lora-bf16.gguf`, sha256 41794b57…), the exact
  file evaluated on the final test;
- the tokenizer, chat template and model card. Training and evaluation configurations and the job scripts are in the
  code repository.

## 6. Data artifacts

Dataset: [HatemSaadallah/strategy-agent-investigations](https://huggingface.co/datasets/HatemSaadallah/strategy-agent-investigations)
(in the same collection):
- the training rows: 4,302 from the Command A+ teacher, 51 correction rows, and 3,611 (plus 262 for validation) from
  the DeepSeek V4-Pro teacher, each bound to its teacher episode;
- the dossier in full (1,958 records, byte-identical to the one in this repository) and every case: 207 development,
  16 final-test and 24 second-test cases, with both freeze files;
- the second teacher's investigations (transcripts, provenance, request logs);
- evaluation runs, blinded judge packets, judge outputs and reports for every campaign: development, both frozen
  tests, version 3, adapter switching and the combined system;
- `MANIFEST.json`, with the sha256 of each private original and of its published copy.

## 7. Experiments and findings

### Early development (small runs, diagnostic only)
- **The untrained model cannot do the task.** In an open workflow it quit after a step or two; under the stage
  controller it stalled, mostly by repeating a theory or search it had already made.
- **Full chat histories did not fit.** Late-stage rows exceeded 8,192 tokens and were refused rather than truncated, so
  most conclusion rows were lost. We replaced the history with a compact state (theories, quotes, tests and revisions in
  full, everything else summarised), which kept every row.
- **Loops at temperature 0.** The first fine-tuned runs went much deeper but repeated refused calls. We added
  correction rows and made the state say plainly that rereading a source returns the same text.
- **A better teacher.** Aya Expanse 32B followed the workflow but reasoned weakly and was rejected as a teacher;
  Command A+ replaced it.

### Controls that the result rests on
- **Conversion check.** Every evaluated adapter was converted to GGUF and replayed against the PEFT adapter on the GPU:
  effect cosine at least 0.99 and probability-weighted residual at most 0.15 on every point, plus a weight-file audit.
  The final adapter passed (cosine 0.9990, residual 0.080), and the evaluated file is byte-identical to the gated one.
- **Judges.** Each judge first scored 20 matched pairs of investigations, sound and flawed, and had to rank the sound
  one higher in at least 17. Claude did so in 20 of 20 (after its output limit was raised and it was requalified),
  Codex in 20 of 20. Packets carry no model name; the key stays outside the judges' reach.

### Development (6 validation companies, 15 cases, one attempt each)

| Arm | Finished | Quality, mean of two judges |
|---|---|---|
| Base, compact prompt | 0 of 15 | 0.14 |
| Base, staged prompt | 0 of 15 | 0.43 |
| Earlier adapter | 6 of 15 | 1.09 |
| **Final adapter** | 7 of 15 | **1.29** |

By the preregistered rule (higher mean judge score) the staged prompt became the base and the final adapter the
trained arm. The two adapters were not distinguishable (+0.20, interval −0.09 to 0.53).

### Final test (4 held-out companies, 16 cases, 3 attempts, 96 runs, run once)

| | Base, staged prompt | Fine-tuned | Difference, paired, 95% case-cluster bootstrap |
|---|---|---|---|
| Claude | 0.56 | 1.20 | +0.64 [0.51, 0.77] |
| Codex | 0.74 | 1.77 | +1.03 [0.87, 1.18] |
| **Mean of judges** | **0.65** | **1.48** | **+0.83 [0.69, 0.97]** |
| Finished investigations | 4 of 48 | 28 of 48 | |

- Every company is higher under both judges (mean of judges: Aquaporin +1.10, Simonelli +0.98, RATIONAL +0.66,
  Electrolux Professional +0.60), and every kind of new evidence (no new evidence +0.84, irrelevant +0.87, supporting
  +0.86, undermining +0.76).
- The judges agree on the ordering (Spearman 0.94 over 95 runs scored by both).
- The largest gains are in distinct theories, framing, causal mechanism, and assumptions and predictions; the weakest
  dimensions for the trained agent remain the recommendation, revision, experiment design and judging evidence.

![Blind quality score on the final test, base model and fine-tuned, per judge](docs/figures/quality-light.png)

![Fine-tuned minus base by kind of new evidence, with 95% intervals](docs/figures/difference-light.png)

![Score per rubric dimension, base and fine-tuned](docs/figures/dimensions-light.png)

**How each run ended** (48 runs per arm; a run is refused a call when it breaks a rule, and stops after repeated
refusals, at the context limit or at the turn limit):

| | Base, staged prompt | Fine-tuned |
|---|---|---|
| Finished with an accepted recommendation | 4 | 28 |
| Stopped after repeated refused calls | 19 | 11 |
| Stopped at the context limit | 25 | 0 |
| Stopped at the turn limit (45) | 0 | 9 |
| Mean calls per run | 20.2 | 35.4 |
| Refused calls, all runs | 279 | 242 |

**Do beliefs move the right way when a what-if arrives?** In the 36 runs per arm whose case delivers a simulated
what-if result, the base model reached it in 11 and the fine-tuned model in 28. A direction check compares the
affected theory's five-point belief before and after: undermining evidence should not raise it, supporting evidence
should not lower it. Of the fine-tuned runs where both beliefs were stated, 6 of 6 moved in the allowed direction (3
undermining, 3 supporting), and in 2 a belief was missing before or after; none moved the wrong way. The base model
stated no before-and-after pair. This is a direction check only, not a quality score: a weak result may rationally
change nothing, and the blind judges score revision as part of the rubric.

**How robust is this?** (`scripts/release/robustness.py`, `reports/judge/robustness.json`; from the saved judgments, no
new runs or judging)
- **Cases of one company are not independent.** The registered interval resamples the 16 cases, but each company's 4
  cases share the company and its question and differ only in the what-if. Resampling whole companies instead, the
  final test is +0.83 [0.63, 1.05] by bootstrap and [0.44, 1.23] by a cluster-robust t interval (3 degrees of freedom);
  test set 2 is +0.52 [0.29, 0.75] and [0.25, 0.78]. With 4 companies any interval on the final test is rough; the
  steadier evidence there is that all 16 cases and all 4 companies are higher.
- **The base model is not losing only because it runs out of room.** 25 of its 48 runs stop at the context limit: it
  reads the full transcript, while the fine-tuned agent reads the compact state (each arm uses the prompt it scored
  best with on development). A run's score counts every stage it never reached as 0, so we also compared each pair only
  on the rubric dimensions both runs were scored on. The difference grows: **+0.92 [0.83, 1.01]** on the final test
  (5.6 shared dimensions on average) and **+0.90 [0.81, 0.99]** on test set 2 (3.6 shared, mostly the early stages).
  The base model is weaker even on the stages it reaches.

### Cost: the fine-tuned agent against a closed model (`reports/cost/roi.json`)

Measured on the final test, one investigation by the fine-tuned agent reads about 121,700 prompt tokens and writes about
2,900 over 35 tool calls, in **66 seconds on one A100 slice**, one investigation at a time: about 54 an hour.

| | per investigation | per 10,000 investigations |
|---|---|---|
| **Fine-tuned Tiny Aya, self-hosted** (A100 40 GB, Oct 2026 median $1.76/h; range $0.89-$3.67) | **$0.032** ($0.016-$0.068) | **$324** (184 GPU hours; $164-$676) |
| Claude Opus 5.5, measured on our earlier control run (15 investigations, $3.73) | $0.25 | $2,483 |
| Claude Opus 5.5, the same token volume at list price, no caching ($4 / $20 per million) | $0.54 | $5,442 |
| Claude Sonnet 5.5, the same token volume ($2 / $10) | $0.27 | $2,721 |
| Claude Haiku 5.5, the same token volume ($0.10 / $0.50) | $0.014 | $136 |

- Self-hosting costs about **8 times less than the measured Opus run** and 8 to 17 times less than Sonnet or Opus at
  the same token volume. Per finished investigation (28 of 48) it is about $0.056.
- **Haiku 5.5 at list price is cheaper than renting a GPU for this agent**, and we did not measure its quality on this
  task; the case for self-hosting against it rests on running offline and keeping the case data local, not on price.
- The closed models are not quality-matched: Claude finished all 15 control investigations on the earlier harness,
  against the fine-tuned agent's 28 of 48 here.
- The teacher shows the other side of distillation: Command A+ took 5,188 seconds for 3 investigations on a full A100
  (80 GB), about 29 minutes each (`reports/strategy/teacher/cap_b.json`), so the student, on a smaller 40 GB slice, runs
  roughly **26 times faster**.
- Not measured: running several investigations at once on one GPU, which llama.cpp supports and would lower the
  self-hosted cost further.

Prices: Anthropic list prices as of October 2026; GPU prices from aggregator snapshots (amcompute.com, October 2026;
gpu-cost.pages.dev, June 2026), which change often.

### What still fails, and why (`docs/FINAL_TEST_DIAGNOSIS.md`)
*This is the diagnosis of version 1 on the first frozen test, written on 8 November right after it. What we did about
each failure since then is noted in italics.*

Only 1 of 48 trained runs passes every mechanical check (all-checks success was also rare in the teacher's training
data, 1 of 223, on other cases), and 20 of 48 stop before a recommendation. One check is itself flawed: five of six predictions-overlap
failures involved contrasting predictions that the checker incorrectly treated as identical. This does not establish
that the experiments were otherwise sound. The frozen numbers are reported as computed. Several failures trace to behaviour the
training data never showed:
- **Never declining a test.** No training example declines one. The labels need care: for Aquaporin, declining
  follows from its insolvency and bankruptcy, recorded in the dossier, yet **no run of either arm read those records**
  and every finished trained run recommends investing. For RATIONAL the no-test label is the case author's judgement
  and is contestable. *Since then: a [company status check](docs/LATER_WORK.md#a-company-status-check-the-aquaporin-failure) makes every run read those records.*
- **Little what-if evidence that matters.** Only 8 of 205 teacher investigations had supporting or undermining
  results; the student handles irrelevant evidence correctly and revises the wrong theory on Aquaporin's pair. *Still
  open: it needs new training examples.*
- **Simulated-only finishes.** Eight runs try to finish citing only the simulated result and are refused; seven repeat
  it until the error limit, and one reaches the turn limit. *Still open.*
- **Rereading.** Nine runs reach the turn limit; in eight of them the agent rereads the same few sources. *Since
  then: the app refuses a third read of one source; the evaluated setup is unchanged.*

### The ceiling is the teacher's (`docs/RELIABILITY_REPORT.md`)
An audit of the 158 teacher investigations that trained version 1 found the same weaknesses the judges score lowest in
the student:
- 74% of the teacher's recommendations use a number from no source (the student: 21% of its finished recommendations
  on the final test, 31% on test set 2);
- 38% of its evidence kinds match the dossier's annotation;
- in 74 of its 109 historical cases (68%; 47% of all 158 investigations) the recommendation cites a source published
  after the case date, and about half of those quotes reveal later outcomes. The frozen tests are present-day cases, so
  their scores are unaffected.

Distillation passed on the procedure and the teacher's judgement with it. When we tried to correct the teacher's
mistakes with the same teacher, it made them again ([corrective distillation](docs/LATER_WORK.md#corrective-distillation-and-two-runtime-attempts-10-november)).
A student can be filtered for following the rules, not for judging well; that needs a better or human-corrected
teacher.

### Second frozen test (12 new companies, 24 cases, 3 attempts, 144 runs, run once; `docs/test2_freeze.json`)
A second test on companies never used for training, development or the diagnosis above. It was frozen before any run,
under the same judges, rubric and rule.

| | Base, staged prompt | Fine-tuned | Difference, paired, 95% case-cluster bootstrap |
|---|---|---|---|
| Claude | 0.48 | 0.89 | +0.41 [0.24, 0.57] |
| Codex | 0.66 | 1.29 | +0.63 [0.43, 0.84] |
| **Mean of the two judges** | **0.57** | **1.09** | **+0.52 [0.33, 0.70]** |
| Finished investigations | 2 of 72 | 32 of 72 | |
| Finished and passing every check | 1 | 4 | |

- The fine-tuned agent is higher for 10 of 12 companies on the mean of judges. Franke Coffee (−0.05) and Hoshizaki
  (−0.10) are slightly lower.
- The gain is smaller than on the first test (+0.83 there on the mean of judges). The two judges rank the runs alike
  (Spearman 0.95 over all 144).
- The weakest dimensions are the same as before: the recommendation (0.03 → 0.44), experiment design (0.22 → 0.53) and
  judging evidence (0.35 → 0.47).

### After the tests (exploratory)
Everything in this section came after both frozen results were known, so it selects nothing, and version 1's numbers
above are the result we stand behind. Each change had its rule registered in [docs/DECISIONS.md](docs/DECISIONS.md)
before it ran, and each comparison was judged blind by Claude Code and Codex (`gpt-6-sol`). The full write-up, with
every table, is in **[docs/LATER_WORK.md](docs/LATER_WORK.md)**.

| What we tried | What happened (mean of two judges, 95% case-cluster interval) |
|---|---|
| [Corrective distillation](docs/LATER_WORK.md#corrective-distillation-and-two-runtime-attempts-10-november) (version 2): teacher examples at version 1's own mistakes | The teacher made the same errors it was meant to correct; version 2 finished 0 of 15 development runs and was stopped |
| [Version 3](docs/LATER_WORK.md#version-3-a-second-teacher-exploratory-version-1-stays-the-evaluated-model): continued on a second teacher's runs (DeepSeek V4-Pro) | Above version 1 on test set 2 (+0.42 [0.24, 0.60]), not distinguishable on the final test (−0.13 [−0.31, 0.04]) |
| [Dig then reason](docs/LATER_WORK.md#switching-adapters-during-a-run-development-then-test-set-2): version 1 gathers the evidence, version 3 reasons | Above version 1 on test set 2 (+0.36 [0.22, 0.51]), level on the final test (−0.01 [−0.20, 0.18]) |
| [Company status check](docs/LATER_WORK.md#a-company-status-check-the-aquaporin-failure) (the Aquaporin insolvency every run missed) | Every run now reads it; costs finished runs; with dig then reason, not shown better than version 1 ([combined system](docs/LATER_WORK.md#the-combined-system-on-test-set-2-a-system-built-after-the-frozen-results), +0.22 [−0.00, 0.46]) |
| [Loop guards](docs/LATER_WORK.md#loop-guards-on-development-test-set-2-and-the-final-test-exploratory): repeats masked, quotes picked from the source, a step budget | Finished runs 28 → 45 of 45, 43 → 69 of 72, 27 → 45 of 48; quality +0.19 [0.10, 0.30], +0.21 [0.09, 0.33], +0.12 [0.00, 0.25] |
| [Evidence first](docs/LATER_WORK.md#evidence-first-how-a-source-is-weighed-exploratory): quote and its limits before the label | Evidence judgement up on every set; overall +0.07, +0.03 [−0.00, 0.06], +0.06; the recommendation barely moves |
| [Recovery controller](docs/LATER_WORK.md#a-recovery-controller-does-not-fix-the-remaining-failures), a verification layer, two runtime constraints | No quality gain; advice to the model changed the text, not the evidence behind it |

The app runs dig then reason with the loop guards and evidence first. The pattern across all of it: changes that remove
a failing action from what the model can produce helped the procedure; nothing we tried at run time improved the
conclusion itself.

### Limits of our own checks
- **The mechanical experiment check is too lenient**: 8 of the 9 tests it accepts on development fail stricter
  design screens. The frozen numbers use the original check; later comparisons also report a stricter one.
- **Evidence-kind labels are 75% exact, 83% counting defensible alternatives**, by a blind relabelling of 60
  training records.
- **No human scores.** Every quality number comes from two LLM judges, qualified by ranking sound investigations above
  flawed ones. They agree on the order of runs (Spearman 0.94 on the final test) but not on the level: on the same
  fine-tuned runs Claude scores problem framing 1.62 and Codex 2.90. The comparisons rest on the order, which both
  judges share; the absolute scores mean little, and a strategy researcher's ratings would be the most useful addition.
- **One kind of question.** Every case asks whether a maker of professional equipment should build a consumer
  proposition. "Generalises" here means new companies, not new kinds of strategy question.

Details: [docs/RELIABILITY_REPORT.md](docs/RELIABILITY_REPORT.md) and
[docs/EVIDENCE_KIND_GUIDE.md](docs/EVIDENCE_KIND_GUIDE.md).

### Lessons
- The controller, the guards and replay made the teacher's data trustworthy, and the same machinery made every
  evaluation run auditable.
- Measuring with two qualified blind judges, a frozen plan and a one-shot test kept us from reading noise: several
  development differences that looked real were not.
- Most remaining failures are gaps in the training data, not in the amount of it.
- Guards that remove a failing action from what the model can produce worked; advice to the model did not. They
  help the procedure most: steering how evidence is weighed lifted the judged evidence scores on every set, and the
  conclusion barely moved, so judgement is the part training still has to supply.
- Results did not transfer cleanly between sets: version 3 and the switching rule each looked different on
  development, test set 2 and the final test. One set would have misled us in either direction.

## 8. With more credits

The diagnosis gives a concrete plan, each part confirmed on development cases before new training examples are chosen,
and measured on fresh evaluation cases, since the four final-test companies have now informed the diagnosis:
1. Justified propose-versus-decline examples, where the decision follows from explicit constraints and the value of
   the information, allowing either decision when warranted.
2. Balanced supporting and contradicting what-if evidence, explicitly linked to the theory it bears on.
3. Recovery from simulated-only citations, separating a hypothetical belief update from the real evidence behind a
   recommendation.
4. Recovery from rereading, using the information already gathered.
5. Searching for the company's current position before theorising (the Aquaporin failure). The [status check](docs/LATER_WORK.md#a-company-status-check-the-aquaporin-failure)
   does this at run time; training it in should remove its cost in finished runs.

More teacher runs of the same kind would not address these gaps; more of these specific cases would. Before and after
would be measured exactly as here: the same frozen judges and rule, on new held-out companies.

What we tried after the tests, and what each attempt showed, is in [docs/LATER_WORK.md](docs/LATER_WORK.md).

The lesson for distillation: a teacher's errors pass to the student, and they cannot be filtered out afterwards. A
stronger or human-corrected teacher for evidence judgement is the next step, not more of the same data.

## 9. Team

Team Two-eyed Ravens: Hatem Saadallah and Nour Jennane, Master's students in artificial intelligence and AI
researchers.

Built with AgentTune, AuditKIT and CuratorKIT (Lexsi Labs), Tiny Aya and Command A+ (Cohere), PEFT, TRL and llama.cpp,
on NVIDIA A100 GPUs (40 GB and 80 GB slices, Slurm). Claude (Anthropic) and Codex (OpenAI) served as blind judges and as coding assistants.

---

## The app

Try it at the [live demo](https://saadallah-r-hatem--aemon-serve.us-east.modal.run/), or run it yourself: `./app/run.sh` starts the interface at http://127.0.0.1:8000: pick a company, ask a question, and watch the
investigation step by step, then read the report, the reasoning map and the sources. It runs the two-adapter system
described in section 7 by default.

![A finished report: the recommendation, the confidence the checks support, and what the evidence did and did not show](docs/figures/ui/redesign/after/report.png)

## Repository layout

```
src/aemon/environment/   the twelve guarded tools, the stage controller, the cases and the dossier search
src/aemon/agent/         the runner, tool schemas, adapter routing, model clients
src/aemon/teacher/       teacher investigations (Command A+ locally, DeepSeek V4-Pro hosted)
src/aemon/rows/          row building, provenance, coverage checks, CuratorKIT curation
src/aemon/training/      AgentTune distillation training, the masking gate
src/aemon/evaluation/    AuditKIT replay and diagnostics, the conversion gate, blind judging
data/dossier/            the public-source dossier the agent searches and quotes
app/                     the interface (FastAPI and React)
deploy/                  the hosted demo (Modal) and the Hugging Face pages
ops/                     MLflow tracking of runs, metrics and adapters
tests/                   the test suites (./run_tests.sh)
jobs/                    Slurm job scripts for every stage
scripts/                 cluster helpers and the release builders (public repository, Hugging Face, replay pages)
reports/                 every result: teacher runs, evaluations, judge packets, outputs and reports
experiments/             the exploratory work after the frozen tests: runs, packets, judgments and reports
paper/                   the paper's LaTeX source (built to docs/PAPER.pdf)
docs/                    the decisions log, plans frozen before each test, model and dataset cards
```

## See an investigation without a GPU

[docs/replays/](docs/replays/README.md) renders every run of both frozen tests as pages you can read here on GitHub
(96 runs of the first test, 144 of the second), base and fine-tuned side by side, with filters: every tool call, what
the environment accepted or refused and why, the recommendation, and the blind judges' scores. Six are picked out at
the top: a finished run for each company of the first test, the Aquaporin run that misses the insolvency, a run that
stops on refusals, and the untrained base model on the same case. They come straight from the saved reports
(`reports/judge/final/`, `reports/judge/test2/`); `python scripts/release/replay_markdown.py` regenerates them, with
no model or GPU.

## Run it

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt \
  --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match
./run_tests.sh
```

The app looks for the model and the adapters in fixed places and by fixed names (`app/run_model.sh`), so fetch them
like this (Linux; on macOS `brew install llama.cpp` replaces the llama.cpp step):

```bash
# llama.cpp, the release the evaluated runs used
mkdir -p ~/.cache/lexsi/llama-b12032 ~/.cache/lexsi/adapters
curl -L https://github.com/ggml-org/llama.cpp/releases/download/b12032/llama-b12032-bin-ubuntu-x64.tar.gz \
  | tar -xz -C ~/.cache/lexsi/llama-b12032 --strip-components=1   # or the vulkan/cuda build for a GPU

# the 4-bit base model, at the revision the app expects
.venv/bin/hf download CohereLabs/tiny-aya-global-GGUF tiny-aya-global-q4_k_m.gguf \
  --revision a602ea7eeec3a4ad6f77a1b8cf6a53512824922b

# the adapters, saved under the names the app loads
.venv/bin/hf download HatemSaadallah/tiny-aya-global-strategy-agent tiny-aya-global-strategy-lora-bf16.gguf \
  exploratory/v3_adapter.gguf --local-dir /tmp/aemon-adapters
cp /tmp/aemon-adapters/tiny-aya-global-strategy-lora-bf16.gguf ~/.cache/lexsi/adapters/final_adapter.gguf   # version 1
cp /tmp/aemon-adapters/exploratory/v3_adapter.gguf ~/.cache/lexsi/adapters/v3_adapter.gguf                  # version 3

./app/run_model.sh                                        # the model server, port 8091
.venv/bin/python app/users.py add yourname hellberg       # an account (asks for a password); every page needs sign-in
./app/run.sh                                              # the app, at http://127.0.0.1:8000 (needs Node once, to build)
```

With only version 1's adapter present the app runs version 1 alone. One investigation from the command line, against
the same server:

```bash
.venv/bin/python -m aemon.agent.run_investigations --url http://127.0.0.1:8091 --lora-route default=0 \
  --prompt compact --cases hellberg-base --output run.json   # default=0 is version 1
```

PDF reports need Chrome or Chromium.

## Reproduce

The job scripts in `jobs/` run each stage on a Slurm cluster with A100 GPUs; set `REVISION` to a copy of this code.

1. Teacher investigations: `jobs/command_a_plus.sbatch` (Command A+ Q4_K_M with llama.cpp).
2. Rows and training: `NAME=final COMPACT=1 ROW_PROMPT=compact EPOCHS=2 SAVE=50 sbatch jobs/train_after_teacher.sbatch`.
3. Conversion check: the GGUF adapter is replayed against the PEFT adapter (`jobs/diagnose_conversion.sbatch`,
   `src/aemon/evaluation/conversion/gate.py`).
4. Evaluation: `jobs/eval_adapter.sbatch` with `SPLIT=heldout ATTEMPTS=3`, once with the adapter (`PROMPT=compact`) and
   once without (`PROMPT=staged`).
   The trained arm needs `DIAGNOSTIC=1`: the job still runs the first conversion check, retired on 6 November, which
   the final adapter fails on one threshold, so without the flag it exits with code 3 and with it the outputs carry a
   `DIAGNOSTIC_conversion_gate_failed` marker. The adopted check is the second one (step 3), which the adapter passed
   (`reports/conversion/final_gate_v2.json`). `docs/DECISIONS.md` has both entries.
5. Judging: `python -m aemon.evaluation.judging.packets`, `src/aemon/evaluation/judging/judge_v1/run_campaign.py`,
   `python -m aemon.evaluation.judging.report`. All reports are in `reports/judge/`.

The dossier in this repository is the one the evaluated runs read: each record keeps its source, URL and date with
the excerpt the agent quotes from.

## Licence

Code: Apache 2.0. The adapter derives from Tiny Aya Global and is CC-BY-NC-4.0.
