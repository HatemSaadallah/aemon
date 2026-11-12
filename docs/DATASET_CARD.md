---
license: cc-by-nc-4.0
language:
- en
pretty_name: aemon strategy-investigation agent data
task_categories:
- text-generation
tags:
- agentic
- tool-use
- distillation
- strategy
- agenttune
- auditkit
size_categories:
- 1K<n<10K
configs:
- config_name: v1_rows
  default: true
  data_files:
  - split: train
    path: training/rows.jsonl
- config_name: v3_deepseek_rows
  data_files:
  - split: train
    path: training/v3_deepseek_rows.jsonl
  - split: validation
    path: training/v3_deepseek_validation_rows.jsonl
- config_name: correction_rows
  data_files:
  - split: train
    path: training/correction_rows.jsonl
---

# Dataset Card: Strategic Opportunity-Analysis Demonstrations (training and evaluation data for aemon)

Team Two-eyed Ravens | Lexsi AI Hackathon Track 3 (Agentic Fine-Tuning) | November 2026

## 1. Dataset Summary

This dataset contains multi-turn, tool-grounded demonstration trajectories designed to train a compact language model ([`CohereLabs/tiny-aya-global`](https://huggingface.co/CohereLabs/tiny-aya-global)) to conduct scientific strategic opportunity investigations for manufacturing companies exploring consumer market adjacencies.

The investigation task is inspired by the scientific approach to management and strategic decision-making formulated by Camuffo, Gambardella, and Pignataro (2024). Rather than generating generic consulting text or ungrounded SWOT lists, an agent must:
1. Frame the strategic problem and consider alternatives beyond the initial proposal (including declining to expand).
2. Gather evidence through guarded tools, requiring verbatim quotations from an authoritative dossier.
3. Formulate at least two distinct causal theories of value (identifying target customers, behavioral drivers, and value capture mechanisms).
4. Actively search for evidence that could disconfirm its favored theory.
5. Propose a discriminating, feasible experiment with a threshold-based decision rule (or decline a test with a specific reason if further information is not worth its cost).
6. Update its beliefs appropriately when exposed to hypothetical new evidence shocks.

Every row in the training dataset is distilled from a permitted teacher model running through an identical guarded stage controller: **Command A+** (open weights) for version 1 of the adapter, and **DeepSeek V4-Pro** (through its API) for the rows added in version 3. Trajectories are verified through deterministic tool replay and audited against an append-only provenance manifest.

### What Is Published (release of 2026-11-11)

This release replaces the one of 2026-11-08. That release cut every third-party excerpt to one short quote (its first sentence, at most 25 words) wherever it appeared. **This one publishes the excerpts as they are**: the dossier is byte for byte the file the experiments read, and the training rows, transcripts and judge packets carry the same text the models saw. It also adds the data produced since 8 November: test set 2, the version 3 rows and the teacher investigations behind them, the adapter-switching and status-check runs, and the outputs of two more judges.

| Folder | What it holds |
|---|---|
| `dossier/` | `evidence.json`: 1,958 public records (1,246 independent observations, 712 company claims) with source, URL, date and the full excerpt. `cases.json`: 207 development cases on 99 companies. `cases_heldout.json`: the 16 final-test cases (4 companies). `cases_heldout2.json`: the 24 cases of test set 2 (12 companies, split `heldout2`). `final_test_freeze.json` and `test2_freeze.json`: the two frozen test definitions. `evidence_kinds_v2.json`: a proposed, unreviewed relabelling of evidence kinds for training companies |
| `training/` | `rows.jsonl`: 4,302 rows from 174 accepted Command A+ investigations on 63 companies (3,891 rows on 57 training companies, 411 on the 6 validation companies). `correction_rows.jsonl`: 51 correction rows. `v3_deepseek_rows.jsonl`: 3,611 rows from 144 accepted DeepSeek V4-Pro investigations on 69 companies. `v3_deepseek_validation_rows.jsonl`: 262 rows from 10 more, held out for validation. `v3_rows_report.json`: the build report of the version 3 rows |
| `teacher_investigations/deepseek_v4_pro/` | The 17 DeepSeek V4-Pro runs as recorded: transcripts (`*.episodes.jsonl`: 266 investigations, 154 of them finished, and 22 harness errors), the provenance manifests (266 entries), the per-request usage logs and the runner reports |
| `evaluation/dev/`, `evaluation/final/` | As in the first release: development runs (6 companies) and the final test (16 cases × 3 attempts × 2 arms), with judge packets, the key, both judges' outputs and the reports |
| `evaluation/test2/` | Test set 2, version 1 against the base model: 24 cases × 3 attempts × 2 arms, 133 judge packets, the key, both judges' outputs and the reports |
| `evaluation/final_v3/`, `evaluation/test2_v3/` | Version 3 on both test sets (exploratory): its runs, the packets of base, version 1 and version 3 judged together (135 and 205), the keys, the outputs of the two later judges (`claudecode`, `codexsol`) and the reports |
| `evaluation/screen3/` | Version 3's development screen against version 1: both runs, 29 packets, the key and the report |
| `evaluation/switch/` | Adapter switching within a run, development only: 5 arms × 15 cases × 3 attempts, 207 packets, the key, one judge's outputs and the reports |
| `evaluation/system_test2/` | The combined system (dig then reason, with the company status check) on test set 2 and on development: the runs, 342 packets, the key, both judges' outputs and the reports |
| `evaluation/system_final/` | The same system, and dig then reason without the status check, on the final test, judged blind together with base, version 1 and version 3: the two new runs, 231 packets, the key, both judges' outputs and the reports |
| `evaluation/status_check/` | Seven runs of the company status check (Aquaporin diagnostics and development), version 1 and version 3 |
| `evaluation/judge_qualification/` | The qualification results of each judge |
| `MANIFEST.json` | Every published file with the file it was made from, and the sha256 of that original and of the published copy |

Two things differ from the private originals, and `MANIFEST.json` counts both per file: local paths and cluster identifiers are replaced by placeholders (`/home/USER`, `CLUSTER_ACCOUNT`, `CLUSTER_HOST`), and a lone surrogate (a model output cut in the middle of an emoji) is replaced by U+FFFD. Files with neither have the same sha256 as their original.

## 2. What a Row Is

Each row represents an individual supervised decision turn (`src/aemon/rows/build_rows.py`). 

### Structure
A row consists of:
* `messages`: The conversation context up to that step, formatted with the student's system prompt.
* `target_index`: The index pointing to the single assistant turn that serves as the supervision target.
* `stage`: The name of the controller stage active at that turn (`brief`, `frame`, `evidence`, `theories`, `assessment`, `challenge`, `challenge_reading`, `test`, `position`, `new_evidence`, `update`, `conclude`).
* Metadata fields: `case` (the case ID), `episode` (hash from the provenance manifest), `turn` (turn index within the episode), and `teacher_weights` (SHA-256 hash of the teacher weights; for the DeepSeek rows, which have no weights to hash, the SHA-256 of the model label).
* Correction rows carry `protocol`, `source` and `justification` instead of `turn` and `teacher_weights`.

```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "target_index": 1,
  "stage": "theories",
  "case": "moldex-base",
  "episode": "8f20345...",
  "turn": 4,
  "teacher_weights": "03cf0669f0a6f338a064f264b7c54df1bb882d16860ea513727b199c1ff05b8f"
}
```

### Context Formatting & Compact Representation
Two representations exist in the codebase:
1. **Full History**: Concatenates previous assistant turns and verbatim tool outputs. In initial experiments (`reports/strategy/pilot1/`), full history caused severe context bloat (over 8,192 tokens), dropping up to 68% of conclude stage rows.
2. **Compact State (`compact=True`)**: Replaces historical message turns with a structured JSON snapshot (`state_of()` in `src/aemon/agent/state_view.py`). The compact state mechanically tracks current budgets, the problem frame, unread results, sources read, formulated theories, completed assessments, disconfirmation searches, proposed tests, declared positions, and revisions, alongside the latest tool output. All late-stage rows fit comfortably under 6,000 tokens (median conclude length: 4,674 tokens).

### Target Reply & Loss Masking
The target is the teacher's exact JSON tool call. In `src/aemon/rows/build_rows.py:labels_for()`, loss is placed strictly on the tokens of the target reply:
* All prompt and context tokens receive label `-100`.
* The tokenizer verifies that the context token sequence forms an exact prefix of the complete prompt-plus-target sequence; any mismatch raises an immediate error.
* Rows exceeding the 8,192-token context limit raise an `Overlength` exception and are logged by stage. They are never truncated, ensuring that late-stage decision steps are not silently clipped.

## 3. The Teacher Models

The version 1 demonstrations (`training/rows.jsonl`, `training/correction_rows.jsonl`) are generated exclusively by **Command A+**, an open-weights model developed by Cohere:
* **Hugging Face Model:** `CohereForAI/c4ai-command-a-plus-05-2026`
* **GGUF Release:** `bartowski/command-a-plus-05-2026-GGUF`
* **Revision:** `a26ba921242484b5e1a8ac8519169fe7421c3ab3`
* **File Stem:** `command-a-plus-05-2026-Q4_K_M`
* **License:** Apache 2.0 (confirmed eligible for Lexsi Track 3)
* **Weights Checksum (Part 1 SHA-256):** `03cf0669f0a6f338a064f264b7c54df1bb882d16860ea513727b199c1ff05b8f` (registered in `TEACHER_WEIGHTS`, `src/aemon/common/constants/pipeline.py`)

### Teacher Runtime and Prompting
The teacher runs under `llama-server` with a 16,384-token context window (`jobs/command_a_plus.sbatch`). It operates under a stricter prompt than the student (`TEACHER` in `src/aemon/common/constants/prompts.py`), which requires:
* Naming causal mechanisms rather than marketing tactics.
* Generating measurable predictions that separate competing theories, explicitly barring generic business metrics (sales, revenue, profit, brand awareness).
* Classifying evidence directions objectively (forbidding `supports` if the excerpt only describes company capabilities rather than customer demand).
* Designing tests that measure the specific behaviors about which theories disagree.

### The Second Teacher: DeepSeek V4-Pro (version 3 rows)
The rows added for version 3 of the adapter (`training/v3_deepseek_rows.jsonl`, `training/v3_deepseek_validation_rows.jsonl`) come from whole investigations by **DeepSeek V4-Pro** (`deepseek-v4-pro`, label `deepseek-api deepseek-v4-pro DeepSeek-V4-Pro-0813`), run on 2026-11-10 and 2026-11-11 through the unchanged runner: the same teacher prompt, tools, stages and guards, context 16,384, 2,000 tokens per turn, 45 turns, temperature 0 (the API takes no seed). Its terms allow training other models on its outputs.
* 266 investigations were recorded, 154 reached an accepted finish, and every one of those replays exactly. The other 112 stopped on repeated errors and give no rows.
* 144 accepted investigations give the 3,611 training rows (69 companies); 10 give the 262 validation rows (5 companies).
* 25 of the 69 companies have no version 1 rows. Their cases were written by DeepSeek V4.1-Flash from public pages, and each quote was admitted only when found word for word on its live page, as for every dossier record.
* The transcripts, provenance manifests and request logs are in `teacher_investigations/deepseek_v4_pro/`.

Version 3 continues version 1's adapter on every row of both teachers. It failed its development screen, so **version 1 stays the submitted model** and the version 3 results in `evaluation/` are exploratory.

## 4. Provenance and Replay Verification

To prevent training data contamination and ensure repeatability:
1. **Append-Only Manifest (for the DeepSeek runs, `teacher_investigations/deepseek_v4_pro/provenance_*.jsonl` in this dataset):**
   Every completed teacher episode is recorded with its unique episode hash (`episode_id()` in `src/aemon/rows/provenance.py`), computed from the exact turn stream, the case digest, and the protocol ID.
2. **Deterministic Tool Replay:**
   `src/aemon/rows/build_rows.py` passes every recorded call sequence through the authoritative simulation environment (`src/aemon/environment/tools.py:Investigation`). Replay must consume every recorded turn, reproduce all tool outputs identically, and terminate at an accepted finish. If a call was refused or produced an error, that turn is flagged and excluded from the training target set.
3. **Strict Source Validation (`training_source()`):**
   Before a row is compiled, the manifest verifies that the episode was produced by a backend matching a verified SHA-256 hash in `TEACHER_WEIGHTS`.
4. **Exclusion of Anthropic / Claude Data:**
   Under Section D.4 of Anthropic's Commercial Terms, outputs from Claude services may not be used to train competing models. In this repository, Claude is used solely as a workflow baseline and blind evaluation judge. Claude outputs are barred by code from entering the provenance manifest or training row builders (`src/aemon/rows/provenance.py`).

## 5. Company and Case Splits

Splits are strictly partitioned by **company/cluster**, never by individual row or turn (`src/aemon/data/splits.py`), because turns within the same investigation share evidence and context.

```
Total Population: 115 Manufacturing Companies
├── Development Set (99 Companies, 207 Cases; dossier/cases.json)
│   ├── Training Split: 93 Companies (e.g., Moldex-Metric, Cotral Lab, 3M, Hilti, Cree, Gore...)
│   └── Validation Split: 6 Companies (Hellberg, Neumann, Jotun, Tanita, Deere, ACR)
├── Frozen Final-Test Set (4 Companies, 16 Cases; dossier/final_test_freeze.json)
│   └── Aquaporin A/S, Electrolux Professional Group, RATIONAL AG, Simonelli Group
└── Frozen Test Set 2 (12 Companies, 24 Cases, split heldout2; dossier/test2_freeze.json)
    └── Ansell, Belimo, Dräger, Franke Coffee Systems, Hach, Hoshizaki, Kingspan, Laerdal,
        Mettler-Toledo, Tennant, Testo, Winterhalter
```

### The Splits
* **93 Training Companies:** Sourced from diverse industrial sectors (hearing protection, respiratory gear, specialty chemicals, professional tools, agricultural systems, commercial lighting, medical instruments). Rows exist for 82 of them: 57 in the version 1 rows and 69 in the version 3 rows, 44 in both.
* **6 Validation Companies (`src/aemon/data/splits.py`):** Held out during training and used for checkpoint selection (unweighted company-balanced loss) and development evaluations. Covers 6 distinct industries and historical eras, including one case where no test is warranted (`jotun`). `training/rows.jsonl` also holds 411 teacher rows on these companies; they validate and are never trained on.
* **4 Frozen Final-Test Companies (`dossier/final_test_freeze.json`):** 
  * Aquaporin A/S (`aqp`)
  * Electrolux Professional Group (`epro`)
  * RATIONAL AG (`rational`)
  * Simonelli Group (`simo`)
  Totaling 16 cases (a base case, an irrelevant what-if and two directional what-ifs per company) and 76 evidence records (Digest: `dce26d4f11232f74a2d4e4b744a7ebc0c52a9c3cc04bb71f8994ea7f499ee77e`). These cases are strictly frozen and never inspected, prompted against, or tuned on prior to the single confirmatory evaluation.
* **12 Frozen Test-Set-2 Companies (`dossier/test2_freeze.json`):** a second held-out set of 24 cases (a base case and an irrelevant what-if per company) and 221 evidence records (Digest: `4db90205e4d6ada220edf496841d54fb4d75429d2d0aa219b1560cbddab25f37`). All are present-day cases.

### Cases Where No Test is Warranted
To prevent models from assuming an experiment is always justified, 18 development cases on 9 companies specify `test_warranted: false` (Portwest, Masimo, Statitrol, Jotun, MSA, STIHL, Texas Instruments, Osram, Perrigo), alongside the 8 final-test cases of 2 companies (Aquaporin, RATIONAL). Test set 2 has none. In these cases, the correct scientific decision is to conclude or decline testing with an explicit justification.

## 6. Evidence Sources and Licensing

The dossier (`dossier/evidence.json`, byte for byte `data/dossier/evidence.json` of the code repository) contains **1,958 public records**:
* **`verified_observation` (1,246 records):** Standards, regulations (OSHA, NIOSH, ISO, FDA), peer-reviewed research papers, clinical trial results, and dated independent trade journalism.
* **`company_claim` (712 records):** Public disclosures, annual reports, corporate catalogs, and product datasheets.

By split: 1,554 records belong to the 99 development companies (997 verified, 557 claims), 76 to the final-test companies, 221 to test set 2, and 107 are general market records (scope `market`).

The simulated what-if records (hypothetical market observations used to evaluate belief revision under controlled conditions) are written by the case authors. They are part of the case files (the `shock` field of 108 development cases, 12 final-test cases and 12 test-set-2 cases), not of `evidence.json`.

### Sourcing and Data Rights
All evidence excerpts were compiled from publicly available web sources, regulatory databases, and corporate archives. No confidential or proprietary manufacturer data was accessed. Sources are cited with complete URLs, titles, and publication dates in the dossier. Each excerpt was checked against its live source on the access date and is published in full, as the experiments read it. Quoted material belongs to its publishers and is included for research and benchmarking; the source papers and pages themselves are not part of this dataset.

## 7. Recovery Corrections (Protocol `correction-v1`)

As detailed in `docs/RECOVERY_PILOT.md`, student models trained solely on successful paths frequently fall into repetition traps when encountering refusals (e.g., repeating an identical query 67 times in Pilot 2).

To teach recovery:
1. **Harvesting Failure States:** Student trajectories from training companies are parsed for states where loops begin (a refused repeat call, a third reread of one source, or two consecutive refusals).
2. **Teacher Recovery Generation:** The state is passed to Command A+ under the `correction-v1` protocol. The teacher must provide an accepted, non-repetitive tool action advancing the stage.
3. **Token Capping:** Recovery rows are verified through the manifest and mixed into the training pool up to a maximum share of 20% of supervised target tokens (`src/aemon/training/train.py:--extra-token-share`).

## 8. Known Limitations

1. **Hindsight in Historical Cases (corrected 2026-11-10):** Certain public cases (e.g., OXO Good Grips, Tupperware, Gore-Tex) have well-known historical outcomes, and pretraining exposure cannot be ruled out. An earlier version of this card said the agent is restricted to records available at the relevant historical juncture. That is not true of the training dossiers:
   - 247 of 807 records attached to historical training cases (31%) are published after the year the case is set in;
   - the agent is not shown dates by default;
   - 74 of the 158 teacher investigations used for training cite at least one such source in their recommendation.

   Many of these later publications only describe earlier events, but some reveal outcomes. These counts describe the version 1 (Command A+) rows. The audit, with a content review, is in `reports/v1_audit/` of the code repository. The frozen test cases (final test, test set 2) are all present-day and are not affected.
2. **Corporate Claims vs. True Demand:** 712 records are company claims. The environment guards against resting a theory solely on company assertions, but desk research cannot substitute for direct customer interviews.
3. **Translation and Regional Excerpts:** Several European industrial firms (e.g., Jotun, Sievi, Cotral Lab, Simonelli) have source records translated from Norwegian, Finnish, French, or Italian, which may introduce minor stylistic variations.
4. **Analyst Assumptions:** Search budgets, test costs, and timeline limits are stylized analyst parameters designed to force prioritization, not audited corporate balance sheet figures.
5. **Teacher errors in the rows (audit 2026-11-10 of the version 1 rows, `docs/RELIABILITY_REPORT.md`):** the rows are the teacher's decisions and carry its errors. The DeepSeek rows have not had this audit.
   - **Invented numbers:** 74% of the teacher's final recommendations used for training contain a number found in no source read.
   - **Evidence kinds:** they match the dossier annotation in 38% of its weighings, and `independent_study` is often given to encyclopedia, news and company-history text.
   - **Support:** in a blind content sample of 60 weighings, 33 support the theory as stated, 20 partly and 7 not.

   The replay and guard checks verify that every row is a valid, accepted call. They do not verify that its content is correct.
6. **Evidence-kind annotation:** a blind relabelling of 60 training records agreed with the annotation on 45, with 5 more defensible. It found 3 likely errors, and 44 records use kinds the tool cannot express. The annotation is unchanged. A guide and a proposed overlay are in the code repository (`docs/EVIDENCE_KIND_GUIDE.md`).

7. **Campaigns:** every judging campaign in this release is finished and published with its answer key, so every packet can be matched to its arm.
8. **Version 3 is exploratory:** it was run on both test sets after version 1's results were known and after it failed its development screen. Its numbers select nothing.

## 9. Dataset Statistics

Every count below is taken from the published files.

| Metric | Measured Count / Status | Source File |
|---|---|---|
| Total Manufacturing Companies | 115 (99 dev + 4 final test + 12 test set 2) | `dossier/cases*.json` |
| Development Companies / Cases | 99 / 207 | `dossier/cases.json` |
| Validation Companies | 6 | `src/aemon/data/splits.py` |
| Frozen Final-Test Companies / Cases | 4 / 16 | `dossier/final_test_freeze.json` |
| Frozen Test-Set-2 Companies / Cases | 12 / 24 | `dossier/test2_freeze.json` |
| Total Evidence Records | 1,958 (1,246 verified, 712 claims) | `dossier/evidence.json` |
| Development Evidence Records | 1,554 (997 verified, 557 claims) | `dossier/evidence.json` |
| Final-Test / Test-Set-2 Evidence Records | 76 / 221 | `dossier/evidence.json` |
| General Market Records | 107 | `dossier/evidence.json` |
| Development Cases with `test_warranted: false` | 18 (9 companies) | `dossier/cases.json` |
| Accepted Command A+ Investigations | 174 (158 on training, 16 on validation companies) | `training/rows.jsonl` |
| Version 1 Supervised Rows | 4,302 (3,891 on training, 411 on validation companies) | `training/rows.jsonl` |
| Recovery Correction Rows (`correction-v1`) | 51 (18 companies) | `training/correction_rows.jsonl` |
| Recorded / Accepted DeepSeek V4-Pro Investigations | 266 / 154 | `teacher_investigations/deepseek_v4_pro/`, `training/v3_rows_report.json` |
| Version 3 DeepSeek Rows | 3,611 training (69 companies) + 262 validation (5 companies) | `training/v3_deepseek_*.jsonl` |
| Judge Packets | dev 56, final 87, test2 133, final_v3 135, test2_v3 205, screen3 29, switch 207, system_test2 342, system_final 231 | `evaluation/*/judge_packets.jsonl` |

## 10. Evaluation Files and Results

Quality is a blind rubric of nine dimensions scored 0 to 3. Each number below is the mean of the judges named, intervals are 95% and resample whole cases. Each campaign folder holds the runs of each arm (full transcripts), the blinded judge packets, each judge's outputs (`*_predictions.jsonl`), the key that maps packets to arms where it is published, and the reports these numbers are read from.

| Campaign (folder) | Judges | Arm means | Difference, paired |
|---|---|---|---|
| Final test, version 1 vs base (`final/`) | Claude, Codex | base 0.647, version 1 1.484 | +0.832 [0.689, 0.965], 47 pairs, 16 cases |
| Test set 2, version 1 vs base (`test2/`) | Claude, Codex | base 0.572, version 1 1.090 | +0.518 [0.334, 0.703], 72 pairs, 24 cases |
| Final test, version 3 vs version 1, exploratory (`final_v3/`) | Claude Code, Codex (gpt-6-sol) | base 0.620, version 1 1.461, version 3 1.334 | -0.127 [-0.305, 0.041], 48 pairs |
| Test set 2, version 3 vs version 1, exploratory (`test2_v3/`) | Claude Code, Codex (gpt-6-sol) | base 0.562, version 1 1.058, version 3 1.479 | +0.421 [0.244, 0.601], 71 pairs |
| Test set 2, combined system vs version 1 (`system_test2/`) | Claude Code, Codex (gpt-6-sol) | combined 1.282, dig then reason 1.427, version 1 1.065, version 3 1.477 | +0.217 [-0.001, 0.458], 72 pairs: the primary comparison is not met |
| Final test, combined system and dig then reason vs version 1, exploratory (`system_final/`) | Claude Code, Codex (gpt-6-sol) | base 0.605, version 1 1.452, dig then reason 1.441, version 3 1.351, combined 1.320 | dig then reason −0.011 [−0.199, 0.181], combined −0.133 [−0.317, 0.052], 48 pairs each |
| Adapter switching, development (`switch/`) | Claude Code only | version 1 1.065, version 3 0.863, dig then reason 1.239 | dig then reason minus version 1: +0.173 [0.018, 0.346], 45 pairs |

Investigations finished: final test 4 of 48 (base), 28 of 48 (version 1), 37 of 48 (version 3); test set 2: 2 of 72 (base), 32 of 72 (version 1), 57 of 72 (version 3).

Four and twelve companies support only a limited claim about generalisation, and three attempts per case are not independent replications. The judges are language models; `evaluation/judge_qualification/` holds the qualification check of each one.

## 11. Licence

CC-BY-NC-4.0. The training rows contain outputs of Command A+ and of DeepSeek V4-Pro, and the fine-tuned model derives from Tiny Aya Global (CC-BY-NC-4.0). Quoted source excerpts remain their publishers'.
