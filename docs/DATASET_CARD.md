# Dataset Card: Strategic Opportunity-Analysis Demonstrations

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

Every row in the training dataset is distilled from a permitted, open-weights teacher model—**Command A+**—running through an identical guarded stage controller. Trajectories are verified through deterministic tool replay and audited against an append-only provenance manifest.

## 2. What a Row Is

Each row represents an individual supervised decision turn (`src/strategy_agent/pipeline/rows.py`). 

### Structure
A row consists of:
* `messages`: The conversation context up to that step, formatted with the student's system prompt.
* `target_index`: The index pointing to the single assistant turn that serves as the supervision target.
* `stage`: The name of the controller stage active at that turn (`brief`, `frame`, `evidence`, `theories`, `assessment`, `challenge`, `challenge_reading`, `test`, `position`, `new_evidence`, `update`, `conclude`).
* Metadata fields: `case` (the case ID), `episode` (hash from the provenance manifest), `turn` (turn index within the episode), and `teacher_weights` (SHA-256 hash of the teacher weights).

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
2. **Compact State (`compact=True`)**: Replaces historical message turns with a structured JSON snapshot (`state_of()` in `src/strategy_agent/agent/runner.py`). The compact state mechanically tracks current budgets, the problem frame, unread results, sources read, formulated theories, completed assessments, disconfirmation searches, proposed tests, declared positions, and revisions, alongside the latest tool output. All late-stage rows fit comfortably under 6,000 tokens (median conclude length: 4,674 tokens).

### Target Reply & Loss Masking
The target is the teacher's exact JSON tool call. In `src/strategy_agent/pipeline/rows.py:labels_for()`, loss is placed strictly on the tokens of the target reply:
* All prompt and context tokens receive label `-100`.
* The tokenizer verifies that the context token sequence forms an exact prefix of the complete prompt-plus-target sequence; any mismatch raises an immediate error.
* Rows exceeding the 8,192-token context limit raise an `Overlength` exception and are logged by stage. They are never truncated, ensuring that late-stage decision steps are not silently clipped.

## 3. The Teacher Model

Demonstrations are generated exclusively by **Command A+**, an open-weights model developed by Cohere:
* **Hugging Face Model:** `CohereForAI/c4ai-command-a-plus-05-2026`
* **GGUF Release:** `bartowski/command-a-plus-05-2026-GGUF`
* **Revision:** `a26ba921242484b5e1a8ac8519169fe7421c3ab3`
* **File Stem:** `command-a-plus-05-2026-Q4_K_M`
* **License:** Apache 2.0 (confirmed eligible for Lexsi Track 3)
* **Weights Checksum (Part 1 SHA-256):** `03cf0669f0a6f338a064f264b7c54df1bb882d16860ea513727b199c1ff05b8f` (registered in `src/strategy_agent/pipeline/provenance.py:TEACHER_WEIGHTS`)

### Teacher Runtime and Prompting
The teacher runs under `llama-server` with a 16,384-token context window (`jobs/command_a_plus.sbatch`). It operates under a stricter prompt than the student (`TEACHER` in `src/strategy_agent/agent/runner.py`), which requires:
* Naming causal mechanisms rather than marketing tactics.
* Generating measurable predictions that separate competing theories, explicitly barring generic business metrics (sales, revenue, profit, brand awareness).
* Classifying evidence directions objectively (forbidding `supports` if the excerpt only describes company capabilities rather than customer demand).
* Designing tests that measure the specific behaviors about which theories disagree.

## 4. Provenance and Replay Verification

To prevent training data contamination and ensure repeatability:
1. **Append-Only Manifest (`runs/teacher/provenance.jsonl`):**
   Every completed teacher episode is recorded with its unique episode hash (`episode_id()` in `src/strategy_agent/pipeline/provenance.py`), computed from the exact turn stream, the case digest, and the protocol ID.
2. **Deterministic Tool Replay:**
   `src/strategy_agent/pipeline/rows.py` passes every recorded call sequence through the authoritative simulation environment (`src/strategy_agent/env/tools.py:Investigation`). Replay must consume every recorded turn, reproduce all tool outputs identically, and terminate at an accepted finish. If a call was refused or produced an error, that turn is flagged and excluded from the training target set.
3. **Strict Source Validation (`training_source()`):**
   Before a row is compiled, the manifest verifies that the episode was produced by a backend matching the verified SHA-256 hash in `TEACHER_WEIGHTS`.
4. **Exclusion of Anthropic / Claude Data:**
   Under Section D.4 of Anthropic's Commercial Terms, outputs from Claude services may not be used to train competing models. In this repository, Claude is used solely as a workflow baseline and blind evaluation judge. Claude outputs are barred by code from entering the provenance manifest or training row builders (`src/strategy_agent/pipeline/provenance.py`).

## 5. Company and Case Splits

Splits are strictly partitioned by **company/cluster**, never by individual row or turn (`src/strategy_agent/pipeline/splits.py`), because turns within the same investigation share evidence and context.

```
Total Population: 68 Manufacturing Companies
├── Development Set (64 Companies, 137 Cases)
│   ├── Training Split: 58 Companies (e.g., Moldex-Metric, Cotral Lab, 3M, Hilti, Cree, Gore...)
│   └── Validation Split: 6 Companies (Hellberg, Neumann, Jotun, Tanita, Deere, ACR)
└── Frozen Final-Test Set (4 Companies, 8 Cases; docs/final_test_freeze.json)
    └── Aquaporin A/S, Electrolux Professional Group, RATIONAL AG, Simonelli Group
```

### The Splits
* **58 Training Companies:** Sourced from diverse industrial sectors (hearing protection, respiratory gear, specialty chemicals, professional tools, agricultural systems, commercial lighting, medical instruments).
* **6 Validation Companies (`src/strategy_agent/pipeline/splits.py`):** Held out during training and used for checkpoint selection (unweighted company-balanced loss) and development evaluations. Covers 6 distinct industries and historical eras, including one case where no test is warranted (`jotun`).
* **4 Frozen Final-Test Companies (`docs/final_test_freeze.json`):** 
  * Aquaporin A/S (`aqp`)
  * Electrolux Professional Group (`epro`)
  * RATIONAL AG (`rational`)
  * Simonelli Group (`simo`)
  Totaling 8 cases and 76 evidence records (Digest: `a228c6fc694028b458ad528e4d5e3accb6f02ac3798088fbc7776d888035297d`). These cases are strictly frozen and never inspected, prompted against, or tuned on prior to the single confirmatory evaluation.

### Cases Where No Test is Warranted
To prevent models from assuming an experiment is always justified, 9 development cases specify `test_warranted: false` (Portwest, Masimo, Statitrol, Jotun, MSA, STIHL, Texas Instruments, Osram, Perrigo), alongside 2 held-out test cases (Aquaporin, RATIONAL). In these cases, the correct scientific decision is to conclude or decline testing with an explicit justification.

## 6. Evidence Sources and Licensing

The development dossier (`data/dossier/evidence.json`) contains **1,334 public records** across 64 companies:
* **`verified_observation` (935 records):** Standards, regulations (OSHA, NIOSH, ISO, FDA), peer-reviewed research papers, clinical trial results, and dated independent trade journalism.
* **`company_claim` (399 records):** Public disclosures, annual reports, corporate catalogs, and product datasheets.
* **`synthetic` (what-if shock packets):** Hypothetical market observations generated to evaluate belief revision under controlled conditions.

### Sourcing and Data Rights
All evidence excerpts were compiled from publicly available web sources, regulatory databases, and corporate archives. No confidential or proprietary manufacturer data was accessed. Sources are cited with complete URLs, titles, and publication dates in the dossier. Excerpts are brief factual quotations used strictly for academic evaluation and benchmarking.

## 7. Recovery Corrections (Protocol `correction-v1`)

As detailed in `docs/RECOVERY_PILOT.md`, student models trained solely on successful paths frequently fall into repetition traps when encountering refusals (e.g., repeating an identical query 67 times in Pilot 2).

To teach recovery:
1. **Harvesting Failure States:** Student trajectories from training companies are parsed for states where loops begin (a refused repeat call, a third reread of one source, or two consecutive refusals).
2. **Teacher Recovery Generation:** The state is passed to Command A+ under the `correction-v1` protocol. The teacher must provide an accepted, non-repetitive tool action advancing the stage.
3. **Token Capping:** Recovery rows are verified through the manifest and mixed into the training pool up to a maximum share of 20% of supervised target tokens (`src/strategy_agent/training/train.py:--extra-token-share`).

## 8. Known Limitations

1. **Hindsight Bias in Historical Cases:** Certain public cases (e.g., OXO Good Grips, Tupperware, Gore-Tex) possess well-known historical outcomes. While the agent is restricted to public records available at the relevant historical or current juncture, pretraining exposure cannot be entirely ruled out.
2. **Corporate Claims vs. True Demand:** 399 records are company claims. The environment guards against resting a theory solely on company assertions, but desk research cannot substitute for direct customer interviews.
3. **Translation and Regional Excerpts:** Several European industrial firms (e.g., Jotun, Sievi, Cotral Lab, Simonelli) have source records translated from Norwegian, Finnish, French, or Italian, which may introduce minor stylistic variations.
4. **Analyst Assumptions:** Search budgets, test costs, and timeline limits are stylized analyst parameters designed to force prioritization, not audited corporate balance sheet figures.

## 9. Dataset Statistics

| Metric | Measured Count / Status | Source File |
|---|---|---|
| Total Manufacturing Companies | 68 (64 dev + 4 frozen test) | `cases.json`, `cases_heldout.json` |
| Development Companies | 64 | `data/dossier/cases.json` |
| Training Companies | 58 | `src/strategy_agent/pipeline/splits.py` |
| Validation Companies | 6 | `src/strategy_agent/pipeline/splits.py` |
| Frozen Held-out Test Companies | 4 | `docs/final_test_freeze.json` |
| Total Development Evidence Records | 1,334 (935 verified, 399 claims) | `data/dossier/evidence.json` |
| Held-out Evidence Records | 76 | `data/dossier/cases_heldout.json` |
| Development Cases with `test_warranted: false` | 9 | `data/dossier/cases.json` |
| Accepted Teacher Investigations | TBD | Final teacher queue output |
| Total Compiled Supervised Rows | TBD | Final `rows.jsonl` build |
| Total Supervised Target Tokens | TBD | Final training report |
| Recovery Correction Rows (`correction-v1`) | TBD | Final `rows.jsonl` build |
