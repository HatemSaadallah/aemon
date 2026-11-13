# Model Card: aemon, a Strategic Opportunity-Analysis Agent (Tiny Aya Fine-Tuned)

*weigh what is known. test what is not.*

Team Two-eyed Ravens: Hatem Saadallah and Nour Jennane | Lexsi AI Hackathon Track 3 (Agentic Fine-Tuning) | November 2026

**[Live demo](https://huggingface.co/spaces/HatemSaadallah/aemon)** ·
**[Full write-up and code](https://github.com/HatemSaadallah/aemon)** ·
**[Article](https://huggingface.co/blog/HatemSaadallah/aemon)** ·
[Dataset](https://huggingface.co/datasets/two-eyed-ravens/aemon) ·
[Collection](https://huggingface.co/collections/two-eyed-ravens/aemon-a-strategy-investigation-agent-6af71da6a81fe397ad0b38dd) ·
[Paper](https://github.com/HatemSaadallah/aemon/blob/main/docs/PAPER.pdf)

> On four companies it never saw, this adapter scored **1.48** against the best-prompted base model's **0.65** on a
> 0–3 blind rubric (mean of two judges; **+0.83, 95% interval 0.69 to 0.97**). A second frozen test on twelve more
> companies gave **+0.52 [0.33, 0.70]**.

## Which file is which

| | Files on this page | What they are for | Numbers |
|---|---|---|---|
| **Version 1, the evaluated adapter** | `adapter_model.safetensors` + `adapter_config.json` (PEFT); `tiny-aya-global-strategy-lora-bf16.gguf` (llama.cpp; the exact file evaluated) | the results in sections 5 and 6: one adapter on Tiny Aya Global, distilled from Command A+ | +0.83 and +0.52, frozen tests run once |
| **Version 3, the final system's reasoner** | `v3_adapter.gguf` | the app and the [live demo](https://huggingface.co/spaces/HatemSaadallah/aemon): version 1 gathers the evidence, version 3 reasons, with decoding-time guards the app sets (`app/server.py`) | +1.02 and +1.11 over the base model on the same cases, measured after the tests (the two sections at the end) |

To run the final system, follow [Run it](https://github.com/HatemSaadallah/aemon#run-it) in the repository; with
only version 1's file present the app runs version 1 alone. Both adapters derive from Tiny Aya Global, so both are
CC-BY-NC 4.0 (non-commercial).

## 1. Model Details

* **Model Name:** aemon, a Strategic Opportunity-Analysis Agent (Fine-Tuned Tiny Aya Global)
* **Base Model:** [`CohereLabs/tiny-aya-global`](https://huggingface.co/CohereLabs/tiny-aya-global) (pinned commit `af89d21`)
* **Base Architecture:** Compact multilingual autoregressive transformer
* **Base Model License:** CC-BY-NC-4.0 (Non-Commercial)
* **Post-Training Method:** Supervised distillation via Parameter-Efficient Fine-Tuning (PEFT LoRA) through AgentTune
* **Teacher Model:** Command A+ (`command-a-plus-05-2026-Q4_K_M`, Apache 2.0)
* **Evaluation Framework:** AuditKIT episode replay and double-blind LLM rubric evaluation
* **Training job:** an NVIDIA A100 GPU, Slurm job 744559, code revision 20d3610; adapter sha256 740c4a9b…, converted GGUF sha256 41794b57…

## 2. Intended Use

### Primary Intended Use
The model is trained to act as an agentic strategy analyst for manufacturers exploring new consumer market opportunities. Following the scientific approach to strategic decision-making (Camuffo, Gambardella & Pignataro, 2024), the agent interacts with an environment of twelve guarded tools to:
1. **Frame the Strategic Problem:** Clarify company capabilities, boundary constraints, and alternative paths (including declining expansion).
2. **Retrieve Grounded Evidence:** Query and cite public regulatory standards, clinical studies, and corporate filings verbatim, avoiding ungrounded claims.
3. **Construct Competing Causal Theories:** Propose at least two distinct causal mechanisms explaining who benefits, why their behavior changes, and how the firm captures value.
4. **Conduct Disconfirmation Searches:** Actively seek evidence that could prove its favored theory wrong.
5. **Design Discriminating Experiments:** Specify affordable, feasible tests with measurable behavioral metrics and threshold-based decision rules (or explicitly decline a test if further information is not cost-justified).
6. **Revise Beliefs Under Evidence Shocks:** Update its confidence ratings rationally when exposed to new market signals.

### Target Audience
Researchers, strategy analysts, and students studying AI agent workflows, scientific decision-making, and agentic fine-tuning.

## 3. Out-of-Scope Use & Limitations

* **Fabricated Evidence:** The model must not invent customer interviews, market size statistics, or test outcomes.
* **Commercial Exploitation:** The base model is governed by CC-BY-NC-4.0; commercial use, resale, or commercial deployment is prohibited by the base model license.
* **Real-World Business Impact:** Improved automated evaluation scores indicate better adherence to a scientific reasoning protocol; they do not prove that recommendations are commercially profitable or viable.

## 4. Training Procedure & Hyperparameters

Training is executed via `src/aemon/training/train.py` using AgentTune's distillation trainer (`agenttune.agentic.distill_trainer.create_distill_trainer`).

### LoRA Configuration
* **Target Modules:** `all-linear` (all linear projection layers in attention and MLP blocks)
* **LoRA rank (r):** 16
* **LoRA alpha (α):** 32
* **LoRA Dropout:** 0.05
* **Task Type:** `CAUSAL_LM`

### Hyperparameters
* **Precision:** `bfloat16`
* **Optimizer:** AdamW
* **Learning Rate:** 1 × 10⁻⁴
* **Learning Rate Schedule:** Linear warmup over 5% of steps, cosine decay
* **Per-Device Batch Size:** 1
* **Gradient Accumulation Steps:** 4 (Effective batch size: 4)
* **Epochs:** 2.0 (1,971 optimizer steps on 3,942 rows: 3,891 teacher rows from 158 investigations on 57 training companies, plus 51 correction rows)
* **Max Sequence Length:** 8,192 tokens
* **Loss Masking:** Supervised loss is computed strictly on target reply tokens (`labels_for()` in `src/aemon/rows/build_rows.py`). Context tokens are assigned label `-100`. Rows exceeding 8,192 tokens are refused and logged, never truncated.

### Checkpoint Selection
Validation is conducted per company across six held-out validation companies (`src/aemon/data/splits.py`: Hellberg, Neumann, Jotun, Tanita, Deere, ACR), capped at 40 evenly spaced rows per company. The retained checkpoint is the one with the lowest validation loss; in the final run that was the last checkpoint (step 1,971, validation loss 0.7125, down from 1.045 at the start).

### Pre-Training and Conversion Gates
1. **Overfit Gate (`--check 10 --require 8`):** Before launching the full training job, an overfit run on 10 demonstration rows must reproduce at least 8 target replies greedily; otherwise, the job aborts.
2. **Adapter Conversion Gate v2 (`src/aemon/evaluation/conversion/gate.py`):** the converted GGUF adapter is
   replayed against its PEFT original on the same token inputs. On every replayed point the adapter's effect must have
   cosine at least 0.99 with the PEFT effect over the full vocabulary and a probability-weighted residual at most 0.15,
   and the weight-file audit must find every factor pair equal to its expected BF16 cast. The final adapter passed
   (11 points, lowest cosine 0.9990, largest residual 0.080), and the GGUF evaluated is byte-identical to the one gated.

## 5. Evaluation Design

The plan (`docs/FINAL_EVAL_PLAN.md`) and every choice (`docs/DECISIONS.md`) were fixed before the final test, which
ran once.

### Arms
* **Base:** untrained Tiny Aya Global under the same stage controller, tools, evidence and limits, with the prompt
  chosen on development data (`staged`, over `compact`).
* **Trained:** the same model with this adapter, chosen on development data over an earlier adapter.

### Measures
1. **Blind LLM judging** by two judges that are neither the student nor the teacher (Claude `claude-opus-5-5` and
   Codex `gpt-6-astra`), each qualified on 20 matched sound/flawed pairs, on nine dimensions scored 0 to 3: problem
   framing, causal mechanism, distinct theories, assumptions and predictions, evidence judgement, seeking challenge,
   experiment design, revision, recommendation. A dimension never reached counts 0. Packets carry no model name.
2. **Mechanical checks and AuditKIT diagnostics:** finished, the executable checks in `src/aemon/environment/checks.py`,
   refused and repeated calls, tool validity, redundant calls and loop detection.
3. **What-if evidence:** each held-out company has a case with no new evidence, one with irrelevant evidence, and a
   matched pair with a supporting and an undermining simulated result.

### Held-out test (`docs/final_test_freeze.json`, digest dce26d4f…)
Four companies (Aquaporin A/S, Electrolux Professional Group, RATIONAL AG, Simonelli Group), 16 cases, 76 records,
three attempts per case and arm: 96 runs. No case was used for prompt development, teacher data or training.

## 6. Evaluation Results

### Final test (run once on 7 November 2026, judged on 8 November)

| | Base | Trained | Trained minus base, paired, 95% case-cluster bootstrap |
|---|---|---|---|
| Claude | 0.56 | 1.20 | +0.64 [0.51, 0.77] |
| Codex | 0.74 | 1.77 | +1.03 [0.87, 1.18] |
| **Mean of judges** | **0.65** | **1.48** | **+0.83 [0.69, 0.97]** |
| Finished investigations | 4 of 48 | 28 of 48 | |
| Passed every mechanical check | 1 of 48 | 1 of 48 | |

Higher at every company under both judges (mean of judges: Aquaporin +1.10, Simonelli +0.98, RATIONAL +0.66,
Electrolux Professional +0.60) and for every kind of new evidence. AuditKIT replay mismatches: 0 in every run.
Reports: `reports/judge/final/`.

Two robustness checks (`reports/judge/robustness.json`): resampling whole companies instead of cases gives +0.83 [0.63,
1.05] by bootstrap or [0.44, 1.23] by a cluster-robust t interval (4 companies, so rough); and since 25 of the base
model's 48 runs stop at the context limit and an unreached stage scores 0, comparing each pair only on the dimensions
both runs reached gives +0.92 [0.83, 1.01]. On test set 2 the same checks give [0.29, 0.75] / [0.25, 0.78] and
+0.90 [0.81, 0.99].

### Second frozen test (12 new companies, 24 cases, 3 attempts; `docs/test2_freeze.json`)
| | Base, staged prompt | This adapter | Difference, paired, 95% case-cluster bootstrap |
|---|---|---|---|
| Claude | 0.48 | 0.89 | +0.41 [0.24, 0.57] |
| Codex | 0.66 | 1.29 | +0.63 [0.43, 0.84] |
| **Mean of the two judges** | **0.57** | **1.09** | **+0.52 [0.33, 0.70]** |
| Finished investigations | 2 of 72 | 32 of 72 | |
| Passed every mechanical check | 1 of 72 | 4 of 72 | |

The adapter is higher for 10 of 12 companies on the mean of judges, which rank the runs alike (Spearman 0.95).
Reports: `reports/judge/test2/`.

### Development (6 validation companies, 15 cases)
Base 0.14 (compact prompt) and 0.43 (staged); earlier adapter 1.09; this adapter 1.29, mean of judges. Finished: 0, 0,
6 and 7 of 15. Reports: `reports/judge/dev/`.

### Known failures (`docs/FINAL_TEST_DIAGNOSIS.md`)
20 of 48 trained runs stop before a recommendation (rereading to the turn limit; finishes citing only simulated
evidence, refused until the error limit). Finished runs miss checks mainly because the model never declines a test
(no training example declines one), mishandles supporting and undermining what-if evidence (rare in training), and
leans on company claims. On Aquaporin no run of either arm read the company's insolvency records in its dossier, and every
finished trained run recommends investing: treat its recommendations as practice output, not advice.

### Evidence reliability audit (2026-11-10, `docs/RELIABILITY_REPORT.md`)
The training data comes from the teacher, Command A+, and carries its weaknesses. The model reproduces some of them:
- **Invented numbers:** 74% of the teacher recommendations it was trained on use a number found in no source. The
  model does so in 21% (final test) and 31% (test set 2) of its finished recommendations.
- **Evidence kinds:** they match the dossier's annotation in 38% of the teacher's weighings, and in 58% and 46% of the
  model's. Encyclopedia, news and company-history text is often labelled `independent_study`. The annotation itself
  matches a blind relabelling on 75% of records (83% counting defensible alternatives).
- **Hindsight in historical training cases:** in 74 of the teacher's 109 historical cases (68%; 47% of all 158
  investigations) the recommendation cites a source published after the case date. In a content sample, about half of those quotes reveal later outcomes. The frozen tests
  are present-day cases, so their scores are unaffected.
- **Lenient experiment check:** most tests that the check accepts fail stricter design screens on development.

Three runtime fixes were tried on development without retraining. None measurably improved reliability, and none is
part of this model's configuration:
- a step-budget guard: quality +0.006;
- an evidence-verification review before the final recommendation: 19 unsupported recommendations against 20;
- a constrained, evidence-consistent position: half as many finishes, rejected.

Corrective distillation from this teacher did not reach the registered threshold of reviewed examples. A version 2
trained on a second teacher's corrections (DeepSeek) finished 0 of 15 development screen runs against this model's 7
and was stopped. Better training data, from
a stronger or human-corrected teacher for evidence judgement, is the open direction. It was not tested.

### What these results do not show

- **Broad generalisation.** The final test covers four held-out companies (Aquaporin, Simonelli, RATIONAL, Electrolux
  Professional), all business-to-business manufacturers asked the same family of question: whether to build a proposition
  for individual buyers. Four companies support only a limited claim. Other industries, other kinds of strategic question,
  and companies outside the dossier's style are untested. The four have since informed the failure diagnosis, so they no
  longer count as unseen for any later claim.
- **Independent replications.** Each case was run three times, but at temperature 0 (0.4 only on a retry after a refused
  call), so the attempts are close to repeats. The effective sample is nearer 16 cases than 48 runs; the intervals
  resample whole cases for that reason. The cases are 4 companies with 4 variants of one question, so resampling
  companies is stricter still (above).
- **Human expert judgement.** Quality was scored by two LLM judges (Claude and Codex), each qualified first on 20 matched
  sound and flawed investigations. They agree closely on the order of runs (Spearman 0.94) but not on the level (on the
  same fine-tuned runs, problem framing 1.62 from Claude and 2.90 from Codex), so absolute scores mean little. They can
  share biases, for example towards structure or length, and no strategy expert has scored the runs.
- **Good absolute quality.** The fine-tuned agent averages 1.48 on a 0 to 3 rubric. 20 of its 48 final-test runs ended
  before a recommendation (11 after repeated refused calls, 9 at the turn limit, 8 of them rereading sources), and its
  weakest dimensions remain the recommendation, revision after new evidence, experiment design and judging evidence.
- **Better than a closed model.** It is not. Claude Haiku 5.5, run on both test sets through the same environment and
  judged blind with this model, version 1's base and the final system, scores 2.28 and 2.30 against the final system's
  1.62 and 1.67 (final system minus Haiku −0.67 [−0.79, −0.52] and −0.63 [−0.75, −0.52]; Codex alone −0.43), at about
  $0.008 per investigation through the API against $0.03 self-hosted. What this model offers is local, offline use with
  open weights (CC-BY-NC 4.0, non-commercial) and the case data kept on the machine. The teacher (Command A+) was not run on the test sets for
  quality.
- **Calibrated confidence.** Beliefs are the agent's own five-step verbal scale within one run, not probabilities. The
  belief check tests direction only (undermining evidence should not raise the affected theory, supporting evidence should
  not lower it), and aemon's confidence score summarises the run's own judgement and the sources it weighed.
- **Real-world sources.** Evaluation used a fixed, curated dossier (1,334 records for the final test and 221 more for test set 2, with short excerpts) and simulated
  what-if results written by the case authors. The open web was never used in evaluation; with live web search the
  agent reads unchecked pages, and its behaviour may differ.
- **Business outcomes.** No recommendation was checked against what a company later did, and no proposed test was run.
  The results measure the quality of the investigation, not whether its advice would have paid off.
- **Robustness of training.** One training run, one data set and one seed. Variance across training runs is not measured.
  The training data has a known defect: constrained generation cut short text fields at 240 characters, so 132 of the 158
  test-design targets have a decision rule that stops mid-sentence.
- **Negative controls on the final test.** The scripted always-keep and always-revise policies could not run on the
  held-out cases (they were written for the original earplug cases), so they are reported for development only.
- **aemon's settings.** The app adds a reread limit, help after refused steps, more allowed steps, draft
  answers when a run stops early, memory, attachments and web search. None of these were part of the evaluated setup;
  the reported numbers apply to the evaluated settings (45 turns, 4 refusals in a row). By default the app also runs
  the two-adapter system (this adapter gathers the evidence, version 3 reasons) with decoding-time guards; see the
  final system sections below.
- **Exact reproduction from the public data.** Since 11 November the public dossier is byte-identical to the one the
  evaluated runs read (the release of 8 November had cut excerpts to one short quote).

## The final system: the version 3 adapter (`v3_adapter.gguf`)

A second adapter, continued from this one on rows from a second teacher (DeepSeek V4-Pro; 3,611 rows from 144
replay-exact investigations). On its own it did not pass its development adoption rule; as the reasoner of dig then reason it did (+0.17 [0.02,
0.35] over version 1 on development), and that is how the final system uses it. It is
published so the two-adapter system described in the write-up ("dig then reason": this card's adapter gathers the
evidence, version 3 reasons) can be run by others. File: GGUF for llama.cpp, sha256 `ea919380…e1443`, the conversion
the final system's runs used. Blind scores, mean of two judges (Claude Code and Codex `gpt-6-sol`), base / version 1 /
version 3: test set 2 0.56 / 1.06 / 1.48; final test 0.62 / 1.46 / 1.33. Dig then reason, mean of the same two judges in the five-arm re-judging (which moves each arm by up to 0.02): test set 2 1.43 (version 1 1.07); final test 1.44 (version 1 1.45, −0.01 [−0.20, 0.18]), so it is level with this adapter on the final test. Same licence as the base model, CC-BY-NC-4.0.

## The final system: decoding-time guards (the app's default)

They change what the model can produce at each step, not its weights; the version 1 numbers above use none of
them. They were built after both frozen tests, partly from the failures in their runs (the loop guards from the
refused calls of the final-test runs), and measured on the same cases, so version 1's numbers stay the run-once
result. Against the base model, the final system scores +1.02 [0.92, 1.10] on the first test's cases and +1.11
[1.01, 1.20] on the second's, judged by the same two judges in separate batches. With the two-adapter system ("dig then reason"):
- **Loop guards**: a source already weighed for a theory and a search already run are not offered again, a quote is
  picked from the source's own sentences, an exact repeat is drawn again before it counts, and a step-budget guard.
  Finished runs: development 28 → 45 of 45, test set 2 43 → 69 of 72, final test 27 → 45 of 48. Blind quality, mean of
  Claude Code and Codex `gpt-6-sol`: +0.19 [0.10, 0.30], +0.21 [0.09, 0.33] and +0.12 [0.00, 0.25].
- **Evidence first, with grounded beliefs**: when weighing a source the quote and what it does not show come before
  the evidence kind (a company claim can only be a company assertion), and 'likely' is offered only for a theory that
  a real weighed source supports. Over the loop guards: +0.07 [0.03, 0.11], +0.03 [−0.00, 0.06] and +0.06 [0.00, 0.11];
  evidence judgement rises for both judges on every set, the recommendation barely moves, and on test set 2 four fewer
  runs finish (65 of 72).

Code: `src/aemon/agent/recovery.py` (`--recovery no_repeats,quote_menu,resample_repeats,budget,grounded_beliefs,evidence_first`).
