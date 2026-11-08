# Model Card: Strategic Opportunity-Analysis Agent (Tiny Aya Fine-Tuned)

Team Two-eyed Ravens | Lexsi AI Hackathon Track 3 (Agentic Fine-Tuning) | November 2026

## 1. Model Details

* **Model Name:** Strategic Opportunity-Analysis Agent (Fine-Tuned Tiny Aya Global)
* **Base Model:** [`CohereLabs/tiny-aya-global`](https://huggingface.co/CohereLabs/tiny-aya-global) (pinned commit `af89d21`)
* **Base Architecture:** Compact multilingual autoregressive transformer
* **Base Model License:** CC-BY-NC-4.0 (Non-Commercial)
* **Post-Training Method:** Supervised distillation via Parameter-Efficient Fine-Tuning (PEFT LoRA) through AgentTune
* **Teacher Model:** Command A+ (`command-a-plus-05-2026-Q4_K_M`, Apache 2.0)
* **Evaluation Framework:** AuditKIT episode replay and double-blind LLM rubric evaluation
* **Training job:** Bocconi HPC, Slurm job 744559, code revision 20d3610; adapter sha256 740c4a9b…, converted GGUF sha256 41794b57…

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

* **Commercial Decision-Making:** This model must NOT be used to make actual capital allocation, corporate acquisition, product launch, or investment decisions without human expert validation and primary empirical data.
* **Fabricated Evidence:** The model must not invent customer interviews, market size statistics, or test outcomes.
* **Commercial Exploitation:** The base model is governed by CC-BY-NC-4.0; commercial use, resale, or commercial deployment is prohibited by the base model license.
* **Real-World Business Impact:** Improved automated evaluation scores indicate better adherence to a scientific reasoning protocol; they do not prove that recommendations are commercially profitable or viable.

## 4. Training Procedure & Hyperparameters

Training is executed via `src/strategy_agent/training/train.py` using AgentTune's distillation trainer (`agenttune.agentic.distill_trainer.create_distill_trainer`).

### LoRA Configuration
* **Target Modules:** `all-linear` (all linear projection layers in attention and MLP blocks)
* **LoRA Rank ($r$):** 16
* **LoRA Alpha ($\alpha$):** 32
* **LoRA Dropout:** 0.05
* **Task Type:** `CAUSAL_LM`

### Hyperparameters
* **Precision:** `bfloat16`
* **Optimizer:** AdamW
* **Learning Rate:** $1\times 10^{-4}$
* **Learning Rate Schedule:** Linear warmup over 5% of steps, cosine decay
* **Per-Device Batch Size:** 1
* **Gradient Accumulation Steps:** 4 (Effective batch size: 4)
* **Epochs:** 2.0 (1,971 optimizer steps on 3,942 rows: 3,891 teacher rows from 158 investigations on 57 training companies, plus 51 correction rows)
* **Max Sequence Length:** 8,192 tokens
* **Loss Masking:** Supervised loss is computed strictly on target reply tokens (`labels_for()` in `src/strategy_agent/pipeline/rows.py`). Context tokens are assigned label `-100`. Rows exceeding 8,192 tokens are refused and logged, never truncated.

### Checkpoint Selection
Validation is conducted per company across six held-out validation companies (`src/strategy_agent/pipeline/splits.py`: Hellberg, Neumann, Jotun, Tanita, Deere, ACR), capped at 40 evenly spaced rows per company. The retained checkpoint is the one with the lowest validation loss; in the final run that was the last checkpoint (step 1,971, validation loss 0.7125, down from 1.045 at the start).

### Pre-Training and Conversion Gates
1. **Overfit Gate (`--check 10 --require 8`):** Before launching the full training job, an overfit run on 10 demonstration rows must reproduce at least 8 target replies greedily; otherwise, the job aborts.
2. **Adapter Conversion Gate v2 (`src/strategy_agent/evaluation/conversion_gate.py`):** the converted GGUF adapter is
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
2. **Mechanical checks and AuditKIT diagnostics:** finished, the executable checks in `src/strategy_agent/env/checks.py`,
   refused and repeated calls, tool validity, redundant calls and loop detection.
3. **What-if evidence:** each held-out company has a case with no new evidence, one with irrelevant evidence, and a
   matched pair with a supporting and an undermining simulated result.

### Held-out test (`docs/final_test_freeze.json`, digest dce26d4f…)
Four companies (Aquaporin A/S, Electrolux Professional Group, RATIONAL AG, Simonelli Group), 16 cases, 76 records,
three attempts per case and arm: 96 runs. No case was used for prompt development, teacher data or training.

## 6. Evaluation Results

### Final test (run once, 2026-11-08)

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

### Development (6 validation companies, 15 cases)
Base 0.14 (compact prompt) and 0.43 (staged); earlier adapter 1.09; this adapter 1.29, mean of judges. Finished: 0, 0,
6 and 7 of 15. Reports: `reports/judge/dev/`.

### Known failures (`docs/FINAL_TEST_DIAGNOSIS.md`)
20 of 48 trained runs stop before a recommendation (rereading to the turn limit; finishes citing only simulated
evidence, refused until the error limit). Finished runs miss checks mainly because the model never declines a test
(no training example declines one), mishandles supporting and undermining what-if evidence (rare in training), and
leans on company claims. On Aquaporin no run of either arm found the company's insolvency in its dossier, and every
finished trained run recommends investing: treat its recommendations as practice output, not advice.

### What these results do not show
Four companies support only a limited claim about generalisation; three attempts per case are not independent
replications; the judges are LLMs; nothing here is about business outcomes. The scripted negative controls could not
run on the held-out cases.
