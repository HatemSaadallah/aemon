*Code, data and every run: [github.com/HatemSaadallah/aemon](https://github.com/HatemSaadallah/aemon). Try it: [huggingface.co/spaces/HatemSaadallah/aemon](https://huggingface.co/spaces/HatemSaadallah/aemon).*

*weigh what is known. test what is not.*

**Teaching a 3B model to investigate a strategy question, with AgentTune and AuditKIT.**
Team Two-eyed Ravens · Lexsi AI Hackathon, Track 3 (Agentic Fine-Tuning) · November 2026

> **Result in one line.** On four companies it never saw, with the same environment, tools, stage controller and
> budgets for both arms, the fine-tuned Tiny Aya agent scored **1.48** against the best-prompted base model's **0.65**
> on a 0–3 blind rubric (mean of two LLM judges; **+0.83, 95% interval 0.69 to 0.97**), and was higher at every
> company. A second frozen test on twelve more companies gave **+0.52 [0.33, 0.70]**. These are version 1's
> run-once results. The final system, built after both tests by adding a second adapter and decoding-time guards,
> scores **+1.02** over the base model on the first test's cases and **+1.11** on the second's, and finishes **46 of
> 48** and **65 of 72** investigations (the base model 4 and 2). Claude Haiku 5.5, a closed model run through the same
> environment, scores higher still (**2.28** against the final system's 1.62) at a quarter of the cost; what aemon offers
> instead is a small open model that runs offline, with the case data kept on the machine.

| | |
|---|---|
| **Live demo** | **[huggingface.co/spaces/HatemSaadallah/aemon](https://huggingface.co/spaces/HatemSaadallah/aemon)** (pick any username to sign in, no password; it runs the final system on two CPU cores and sleeps when idle, so the first page takes a moment; finished investigations open at once, a new one takes a while, and it runs one at a time for everyone) |
| Model | [HatemSaadallah/tiny-aya-global-strategy-agent](https://huggingface.co/HatemSaadallah/tiny-aya-global-strategy-agent) |
| Dataset | [HatemSaadallah/strategy-agent-investigations](https://huggingface.co/datasets/HatemSaadallah/strategy-agent-investigations) |
| Collection | [aemon: a strategy-investigation agent](https://huggingface.co/collections/HatemSaadallah/strategy-investigation-agent-6af0d2ab19339ae58d020326) |
| Paper | [docs/PAPER.pdf](https://github.com/HatemSaadallah/aemon/blob/main/docs/PAPER.pdf) |
| Every test run, browsable | [first test](https://github.com/HatemSaadallah/aemon/blob/main/docs/replays/final/README.md) (96 runs) and [second test](https://github.com/HatemSaadallah/aemon/blob/main/docs/replays/test2/README.md) (144 runs), base and fine-tuned side by side, no GPU needed |
| Every decision, dated | [docs/DECISIONS.md](https://github.com/HatemSaadallah/aemon/blob/main/docs/DECISIONS.md) |

**Version 1, frozen tests run once**

| **+0.83** | **+0.52** | **$0.03** |
|:---:|:---:|:---:|
| blind quality over the best-prompted base model on the first frozen test (0–3 scale, 95% interval 0.69 to 0.97) | on a second frozen test, 12 more unseen companies (0.33 to 0.70) | per investigation, self-hosted on one A100 slice, with the case data kept on the machine; 26× faster than its teacher |

**Final system, built after both tests and measured on the same cases**

| **+1.02** | **46 of 48** | **6× fewer** |
|:---:|:---:|:---:|
| blind quality over the base model on the first test's cases (95% interval 0.92 to 1.10; +1.11 on the second test's) | investigations finished with an accepted recommendation (65 of 72 on the second test), against 4 of 48 for the base model | tool calls per finished investigation (39 against 242); 7.5% of calls refused, against 29% |

![Blind quality score on the final test: base model 0.65, fine-tuned 1.48 (mean of two judges)](https://raw.githubusercontent.com/HatemSaadallah/aemon/main/docs/figures/quality-light.png)

![The reasoning map of one investigation: question, rival hypotheses, the evidence weighed for each, the challenge, the proposed test and the recommendation](https://raw.githubusercontent.com/HatemSaadallah/aemon/main/docs/figures/ui/redesign/after/map.png)

**A judge's 60-second view**
1. Open the [first test's run gallery](https://github.com/HatemSaadallah/aemon/blob/main/docs/replays/final/README.md): every case, base and fine-tuned side by side, with
   how each run ended and its blind scores.
2. Click the filter "fine-tuned finished, base did not" (25 of 48 pairs) and open any pair.
3. Read one investigation end to end: [RATIONAL, by the final system](https://github.com/HatemSaadallah/aemon/blob/main/docs/replays/system_rational-new-evidence-irrelevant_2.md)
   weighs fifteen sources, says what each quote does not show, and recommends a test before any commitment. Every
   tool call is there, with what the environment refused and why.
4. Section 7 has the full results, what still fails, and why.

**Paired, case by case.** On the first test the fine-tuned agent scored higher than the base model on all **16 of 16
cases** and in 44 of 47 paired runs (exact sign test, p = 2.5e-10); on the second test on 20 of 24 cases and 49 of 72
runs (`reports/judge/*/paired_counts.json`, mean of two judges).

**In brief**
- **What it is.** A small open model (3.35B) that runs a strategy investigation as an auditable procedure, locally:
  it frames the decision, states rival causal explanations, weighs evidence for and against each, designs a test with
  a decision rule, and recommends. The environment checks every step: a quote that is not word for word in its source
  is refused, rival explanations must differ, and a simulated result cannot stand in for real evidence. It gives an
  analyst a traceable first pass, every claim linked to its source, rather than a finished answer.
- **How it was made.** A stronger teacher (Command A+) ran investigations through the same tools; only runs that
  replay exactly became training rows; AgentTune distilled them into a LoRA adapter; AuditKIT replays every
  evaluation run.
- **What was measured.** Two frozen, run-once tests on 16 unseen companies, scored blind by two LLM judges that first
  had to rank sound investigations above flawed ones. The gain holds under stricter checks: resampling whole
  companies instead of cases, and comparing each pair only on the stages both runs reached (+0.92).
- **Fewer wasted calls.** The fine-tuned agent makes more calls per run than the base model (35 against 20) because it
  gets much further: per finished investigation it needs **61 calls against 242**, and the share of refused calls
  halves (14% against 29%). The final system, with decoding-time guards, finishes **46 of 48** runs on the first test
  with **39 calls** each (65 of 72 on the second test), and refused calls fall to **7.5%**.
- **What it costs.** About $0.03 and 66 seconds per investigation on one A100 slice, 8 times less than the Claude Opus
  run we measured and 26 times faster than its teacher per GPU.
- **Against a closed model.** Claude Haiku 5.5, run through the same environment, scores higher than the final system
  (2.28 against 1.62 on the first test, 2.30 against 1.67 on the second) and costs less ($0.009 per investigation
  through the API). What a small open model offers instead: it runs offline on one GPU or a laptop, the case data never
  leaves the machine, and the weights can be audited and changed.
- **It learns the procedure; judgement is the next step.** The largest gains are in framing the decision and stating
  distinct causal theories. The recommendation is where the judges score it lowest, and the audit of its teacher shows
  why: a student inherits its teacher's habits (section 7).
- **The final system ([docs/FINAL_SYSTEM.md](https://github.com/HatemSaadallah/aemon/blob/main/docs/FINAL_SYSTEM.md)).** Two adapters ("dig then reason": version 1
  gathers the evidence, version 3, trained further on a second teacher's runs, reasons) with decoding-time guards that
  remove failing actions: no repeated calls, quotes picked from the source, a step budget, and the quote written before
  the evidence label. It was built after both frozen tests, partly from the failures in their runs, and measured on
  the same cases: +1.02 and +1.11 over the base model. Version 1's +0.83 and +0.52 remain the run-once result. The app
  runs the final system.

The name is a nod to Maester Aemon, a counsellor known for sound judgement in unusual
situations.

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
a full audit trail), and *efficient trajectories*: per finished investigation the fine-tuned agent needs 61 tool calls
against the base model's 242, and a refused call is half as common (14% of calls against 29%). Per run it makes more
calls (35 against 20) because it gets much further before it stops. The final system, with decoding-time guards, needs
39 calls per finished investigation and finishes 46 of 48 runs.

**The question we test:** can agentic fine-tuning teach that procedure to a small model, beyond what a stage controller
and the best prompt already achieve?

**The framework behind the procedure.** Camuffo, Gambardella and Pignataro (2024) formalise a theory as a restriction
on beliefs: stating that one thing causes another rules out parameter values, which raises or lowers the expected
value of acting, and an experiment is worth running only while the theory's value is close to its rival's. The paper
([docs/PAPER.pdf](https://github.com/HatemSaadallah/aemon/blob/main/docs/PAPER.pdf), section 2) works through their example.

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
| DeepSeek V4-Pro (`deepseek-v4-pro`) | second teacher, for version 3 (the final system's reasoner) | hosted API | proprietary; its investigations pass the same replay checks |
| Claude Code (`claude-opus-5-5`) and Codex (`gpt-6-sol`) | blind judges for the final system's comparisons | CLI, no tools, no repository access | proprietary; evaluation only; each qualified separately (19 of 20 and 20 of 20) |
| Claude Haiku 5.5 (`claude-haiku-5-5`) | closed-model baseline on both test sets | API, effort medium, the same environment and limits as every arm | proprietary; evaluation only; **never training data** |

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
- **Training data**: 174 accepted teacher investigations gave 4,302 rows. Training used the 3,891 rows from 158
  investigations on 57 training companies, plus 51 correction rows (the teacher showing a valid next step from a state
  where the student had looped); the 411 rows on validation companies were kept out. Other totals below count
  different sets: 223 is every finished teacher investigation, 205 those on training companies.
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
  tests, version 3, adapter switching, the combined system, the loop guards and evidence first;
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
trained arm. The final adapter scored above the earlier one (+0.20), though not by a clear margin.

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

![Blind quality score on the final test, base model and fine-tuned, per judge](https://raw.githubusercontent.com/HatemSaadallah/aemon/main/docs/figures/quality-light.png)

![Fine-tuned minus base by kind of new evidence, with 95% intervals](https://raw.githubusercontent.com/HatemSaadallah/aemon/main/docs/figures/difference-light.png)

![Score per rubric dimension, base and fine-tuned](https://raw.githubusercontent.com/HatemSaadallah/aemon/main/docs/figures/dimensions-light.png)

**How each run ended** (48 runs per arm; a run is refused a call when it breaks a rule, and stops after repeated
refusals, at the context limit or at the turn limit):

| | Base, staged prompt | Fine-tuned |
|---|---|---|
| Finished with an accepted recommendation | 4 | 28 |
| Stopped after repeated refused calls | 19 | 11 |
| Stopped at the context limit | 25 | 0 |
| Stopped at the turn limit (45) | 0 | 9 |
| Mean calls per run | 20.2 | 35.4 |
| Calls per finished investigation | 242 | **61** |
| Refused calls, all runs | 279 | 242 |
| Share of calls refused | 29% | **14%** |

**Do beliefs move the right way when a what-if arrives?** In the 36 runs per arm whose case delivers a simulated
what-if result, the base model reached it in 11 and the fine-tuned model in 28. A direction check compares the
affected theory's five-point belief before and after: undermining evidence should not raise it, supporting evidence
should not lower it. Of the fine-tuned runs where both beliefs were stated, 6 of 6 moved in the allowed direction (3
undermining, 3 supporting), and in 2 a belief was missing before or after; none moved the wrong way. The base model
stated no before-and-after pair. This is a direction check only, not a quality score: a weak result may rationally
change nothing, and the blind judges score revision as part of the rubric.

**Two stricter checks** (`scripts/release/robustness.py`, `reports/judge/robustness.json`; from the saved judgments,
no new runs or judging):
- **Resampling whole companies.** The 16 cases are 4 companies with 4 variants each, so cases of one company are not
  independent. Resampling companies instead of cases, the interval stays above zero on both tests (from +0.44 on the
  first, +0.25 on the second), and all 16 cases and all 4 companies of the first test are higher.
- **Comparing only the stages both runs reached.** 25 of the base model's 48 runs stop at the context limit (it reads
  the full transcript, the fine-tuned agent the compact state; each arm uses the prompt it scored best with on
  development), and a stage never reached scores 0. Scored only on the rubric dimensions both runs reached, the
  difference grows to **+0.92 [0.83, 1.01]** on the first test and **+0.90 [0.81, 0.99]** on the second: the base model
  is weaker even on the stages it reaches.

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
| **Claude Haiku 5.5, measured on both test sets** (120 investigations; $1.06 in all with the runs lost to API errors; effort medium, with caching) | **$0.0084** | **$84** |

- Self-hosting costs about **8 times less than the measured Opus run** and 8 to 17 times less than Sonnet or Opus at
  the same token volume. Per finished investigation (28 of 48) it is about $0.056.
- **Claude Haiku 5.5 costs less than self-hosting, and scores higher** (measured on both test sets, next section but
  one): about $0.008 per investigation, a quarter of the self-hosted cost. Against it, the case for self-hosting is
  running offline, with the case data kept local and weights that can be audited and changed, not price.
- Opus and Sonnet were not run on the test cases, so their rows compare cost, not quality.
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

Few runs pass every mechanical check (1 of 48, as rare as in the teacher's own runs: 1 of 223), and 20 of 48 stop
before a recommendation. One check is itself flawed: in five of six predictions-overlap failures it treated
contrasting predictions as identical; the frozen numbers are reported as computed. Most failures trace to behaviour
the training data never showed:
- **Never declining a test.** No training example declines one. The labels need care: for Aquaporin, declining
  follows from its insolvency and bankruptcy, recorded in the dossier, yet **no run of either arm read those records**
  and every finished trained run recommends investing. For RATIONAL the no-test label is the case author's judgement
  and is contestable. *Since then: a [company status check](https://github.com/HatemSaadallah/aemon/blob/main/docs/FINAL_SYSTEM.md#a-company-status-check-the-aquaporin-failure) makes every run read those records.*
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
mistakes with the same teacher, it made them again ([corrective distillation](https://github.com/HatemSaadallah/aemon/blob/main/docs/FINAL_SYSTEM.md#corrective-distillation-and-two-runtime-attempts-10-november)).
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

- The fine-tuned agent is higher for 10 of 12 companies on the mean of judges.
- Every rubric dimension is higher under both judges, most of all problem framing, revision and distinct theories;
  the recommendation (0.03 → 0.44), experiment design (0.22 → 0.53) and judging evidence (0.35 → 0.47) gain least.
- The two judges rank the runs alike (Spearman 0.95 over all 144).

### The final system
The final system is what the app runs: two adapters ("dig then reason") with decoding-time guards. **It was built
after both frozen tests had been run and read.** The loop guards came from the refused calls in the final-test runs (most
were the model repeating itself), and evidence first from the judges' lowest-scored dimension in them. Each part was
compared with the system before it, with its adoption rule registered in [docs/DECISIONS.md](https://github.com/HatemSaadallah/aemon/blob/main/docs/DECISIONS.md) before
it ran, on development and on the same two test sets, judged blind by Claude Code and Codex (`gpt-6-sol`). Because the
test cases were no longer unseen, **version 1's +0.83 and +0.52 remain the run-once result**; the numbers below are the
final system's own. The full write-up, with every table, is in **[docs/FINAL_SYSTEM.md](https://github.com/HatemSaadallah/aemon/blob/main/docs/FINAL_SYSTEM.md)**.

**Quality against the base model** (mean of the same two judges, same instrument, base and final system judged in
separate batches; `scripts/release/final_system_vs_base.py`): **1.62 against 0.61, +1.02 [0.92, 1.10]** on the first
test's 48 runs, and **1.67 against 0.56, +1.11 [1.01, 1.20]** on the second's 72, higher at every company (4 of 4 and
12 of 12); each judge alone is above +0.76.

**How it runs** (first test, 48 runs each, same cases, settings and seeds; Claude Haiku 5.5 for reference, next section):

| | Base model | Version 1 | **Final system** | Claude Haiku 5.5 |
|---|---|---|---|---|
| Investigations finished | 4 | 28 | **46** | 44 |
| Investigations finished, second test (of 72) | 2 | 32 | **65** | 63 |
| Tool calls per run | 20.2 | 35.4 | 37.8 | 22.2 |
| Tool calls per finished investigation | 242 | 61 | **39** | 24 |
| Share of calls refused | 28.8% | 14.3% | **7.5%** | 13.9% |

**What each part adds** (mean of two judges; intervals in [docs/FINAL_SYSTEM.md](https://github.com/HatemSaadallah/aemon/blob/main/docs/FINAL_SYSTEM.md)):

| Part | First test | Second test | Development |
|---|---|---|---|
| [Dig then reason](https://github.com/HatemSaadallah/aemon/blob/main/docs/FINAL_SYSTEM.md#switching-adapters-during-a-run-development-then-test-set-2): version 1 gathers the evidence, [version 3](https://github.com/HatemSaadallah/aemon/blob/main/docs/FINAL_SYSTEM.md#version-3-a-second-teacher) reasons | level with version 1 | **+0.36** over version 1 | +0.17 (one judge) |
| [Loop guards](https://github.com/HatemSaadallah/aemon/blob/main/docs/FINAL_SYSTEM.md#loop-guards-on-development-test-set-2-and-the-final-test): no repeated calls, quotes picked from the source, a step budget | +0.12 [0.00, 0.25]; finished 27 → 45 | **+0.21**; finished 43 → 69 | +0.19; finished 28 → 45 |
| [Evidence first](https://github.com/HatemSaadallah/aemon/blob/main/docs/FINAL_SYSTEM.md#evidence-first-how-a-source-is-weighed): the quote and what it does not show, before the evidence label | +0.06; judged evidence 0.46 → 0.98 | +0.03; finished 69 → 65 | +0.07 |

What worked: changes that remove a failing action from what the model can produce. Advice to the model did not, and
we also tried, and did not adopt, a company status check, corrective distillation, a recovery controller and a
verification layer ([docs/FINAL_SYSTEM.md](https://github.com/HatemSaadallah/aemon/blob/main/docs/FINAL_SYSTEM.md)).

### Against a closed model: Claude Haiku 5.5 (`experiments/haiku/`)
Registered before it ran ([DECISIONS](https://github.com/HatemSaadallah/aemon/blob/main/docs/DECISIONS.md), 13 November): Claude Haiku 5.5, the cheapest current closed
model, on both test sets through the same environment, tools, stage controller and limits, with the base model's best
prompt (the full transcript; Haiku's context is large enough that it never reaches a limit), effort medium, 3 attempts
per case. Judged blind with the base model, version 1 and the final system by the same two judges. 29 of the 120 runs
were lost to Anthropic API errors (HTTP 500) and rerun; 5 Haiku runs have no Claude Code judgment (rejected by the
instrument's validity check) and are left out of the pairs. Haiku's outputs are never training data.

| Mean of judges (0–3) | Base model | Version 1 | Final system | **Claude Haiku 5.5** | Final system minus Haiku |
|---|---|---|---|---|---|
| First test (48 runs each) | 0.61 | 1.45 | 1.62 | **2.28** | −0.67 [−0.79, −0.52] |
| Second test (72 runs each) | 0.56 | 1.07 | 1.67 | **2.30** | −0.63 [−0.75, −0.52] |

- **Haiku is better on this task.** It scores higher at every company on both sets and on all nine rubric dimensions,
  most of all on the recommendation (1.95 against 1.06 on the first test) and on stating the causal mechanism (2.83
  against 1.97). Both judges agree: Codex alone gives −0.43 on both sets; the Claude Code judge, scoring a Claude model,
  gives −0.90 and −0.86.
- **It is also cheaper and quicker to a finish**: $0.008 per investigation through the API, 24 tool calls per finished
  investigation against the final system's 39.
- **What the fine-tuning bought.** It takes a 3B open model from 0.61 to 1.62, about 60% of the way to Haiku's 2.28 from
  the same starting point. What a small open model offers is not quality or price but control: it runs offline on one
  GPU or a laptop, the case data never leaves the machine, and its weights can be inspected and trained further.
- Tables: `scripts/release/haiku_table.py` (`experiments/haiku/summary.json`).

### Limits
- **The mechanical experiment check is too lenient**: 8 of the 9 tests it accepts on development fail stricter
  design screens. The frozen numbers use the original check; later comparisons also report a stricter one.
- **Evidence-kind labels are 75% exact, 83% counting defensible alternatives**, by a blind relabelling of 60
  training records.
- **No human scores.** Every quality number comes from two LLM judges, qualified by ranking sound investigations above
  flawed ones. They agree on the order of runs (Spearman 0.94 on the final test) but not on the level: on the same
  fine-tuned runs Claude scores problem framing 1.62 and Codex 2.90. Read the scores as comparisons between arms, not
  as absolute grades; a strategy researcher's ratings would be the most useful addition.
- **One kind of question.** Every case asks whether a maker of professional equipment should build a consumer
  proposition. "Generalises" here means new companies, not new kinds of strategy question.

Details: [docs/RELIABILITY_REPORT.md](https://github.com/HatemSaadallah/aemon/blob/main/docs/RELIABILITY_REPORT.md) and
[docs/EVIDENCE_KIND_GUIDE.md](https://github.com/HatemSaadallah/aemon/blob/main/docs/EVIDENCE_KIND_GUIDE.md).

### Lessons
- The controller, the guards and replay made the teacher's data trustworthy, and the same machinery made every
  evaluation run auditable.
- Measuring with two qualified blind judges, a frozen plan and a one-shot test kept us from reading noise: several
  development differences that looked real were not.
- Most remaining failures are gaps in the training data, not in the amount of it.
- At run time, removing a failing action from what the model can produce worked (the loop guards, evidence first);
  telling the model about its mistake did not. Better judgement in the conclusion has to come from better training
  data.
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
5. Searching for the company's current position before theorising (the Aquaporin failure). The [status check](https://github.com/HatemSaadallah/aemon/blob/main/docs/FINAL_SYSTEM.md#a-company-status-check-the-aquaporin-failure)
   does this at run time; training it in should remove its cost in finished runs.

More teacher runs of the same kind would not address these gaps; more of these specific cases would, from a stronger
or human-corrected teacher for evidence judgement, since a teacher's errors pass to the student and cannot be filtered
out afterwards. Before and after would be measured exactly as here: the same frozen judges and rule, on new held-out
companies. What we already tried beyond the final system is in [docs/FINAL_SYSTEM.md](https://github.com/HatemSaadallah/aemon/blob/main/docs/FINAL_SYSTEM.md).

## 9. Team

Team Two-eyed Ravens: Hatem Saadallah and Nour Jennane, Master's students in artificial intelligence and AI
researchers.

Built with AgentTune, AuditKIT and CuratorKIT (Lexsi Labs), Tiny Aya and Command A+ (Cohere), PEFT, TRL and llama.cpp,
on NVIDIA A100 GPUs (40 GB and 80 GB slices, Slurm). Claude (Anthropic) and Codex (OpenAI) served as blind judges and as coding assistants.

---

## The app

Try it at the [live demo](https://huggingface.co/spaces/HatemSaadallah/aemon), or run it yourself:
`./app/run.sh` starts the interface at http://127.0.0.1:8000. Pick a company, ask a question, and watch the
investigation step by step, then read the report, the reasoning map and the sources. By default it runs the
two-adapter system with the loop guards and evidence first (section 7).

**What it is for.** A first pass that an analyst can check, not a verdict. Every claim in the report links to a
quote that the environment verified word for word against its source; rival explanations are set side by side with
the evidence for and against each; and where the evidence runs out, the report proposes a test with a decision rule.
It runs on a laptop or one small GPU, so the case material never leaves the machine.

![A finished report: the recommendation, the confidence the checks support, and what the evidence did and did not show](https://raw.githubusercontent.com/HatemSaadallah/aemon/main/docs/figures/ui/redesign/after/report.png)

## See an investigation without a GPU

[docs/replays/](https://github.com/HatemSaadallah/aemon/blob/main/docs/replays/README.md) renders every run of both frozen tests as pages you can read here on GitHub
(96 runs of the first test, 144 of the second), base and fine-tuned side by side, with filters: every tool call, what
the environment accepted or refused and why, the recommendation, and the blind judges' scores. Six are picked out at
the top: a finished run for each company of the first test, the Aquaporin run that misses the insolvency, a run that
stops on refusals, and the untrained base model on the same case. They come straight from the saved reports
(`reports/judge/final/`, `reports/judge/test2/`); `python scripts/release/replay_markdown.py` regenerates them, with
no model or GPU.

## Licence

Code: Apache 2.0. The adapter derives from Tiny Aya Global and is CC-BY-NC-4.0.
