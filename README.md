# Strategy-investigation agent: Tiny Aya Global fine-tuned on teacher investigations

An agent that investigates whether a manufacturer should take its technology into a new market. It frames the
decision and its alternatives, states rival causal theories, assesses quoted evidence from a dossier of public
sources, looks for evidence against its favoured theory, proposes a test with a decision rule or declines one, revises
when new evidence arrives, and makes a recommendation.

The model is [Tiny Aya Global](https://huggingface.co/CohereLabs/tiny-aya-global) with a LoRA adapter, trained with
[AgentTune](https://github.com/Lexsi-Labs/AgentTune) on investigations by Command A+ and evaluated with
[AuditKIT](https://github.com/Lexsi-Labs/AuditKIT), executable checks and two blind LLM judges.

## Results

Evaluated once on four companies never used for training, prompt development or model selection: 16 cases (each
company with no new evidence, irrelevant evidence, and a supporting and an undermining what-if result), three
attempts each, 96 runs. Quality is a blind rubric of nine dimensions scored 0 to 3 (problem framing, causal mechanism,
distinct theories, assumptions and predictions, evidence judgement, seeking challenge, experiment design, revision,
recommendation), averaged per investigation.

| | Base model (best prompt) | Fine-tuned | Difference, paired, 95% interval |
|---|---|---|---|
| Judge 1 (Claude) | 0.56 | 1.20 | +0.64 [0.51, 0.77] |
| Judge 2 (Codex) | 0.74 | 1.77 | +1.03 [0.87, 1.18] |
| **Mean of the two judges** | **0.65** | **1.48** | **+0.83 [0.69, 0.97]** |
| Investigations finished | 4 of 48 | 28 of 48 | |

Intervals resample whole cases. The two judges rank the investigations alike (Spearman 0.94).

**By company** (mean of judges): Aquaporin +1.10, Simonelli +0.98, RATIONAL +0.66, Electrolux Professional +0.60.

**By new evidence** (mean of judges): none +0.84, irrelevant +0.87, supporting +0.86, undermining +0.76.

**Largest gains by dimension** (judge 2): distinct theories 0.98 to 2.56, problem framing 1.00 to 2.90, causal
mechanism 1.15 to 2.63, revision 0.03 to 0.81.

**Scope.** Four companies support only a limited claim about generalisation, and three attempts per case are not
independent replications. The judges are LLMs, and nothing here measures business outcomes. The fine-tuned agent's
weakest dimensions remain the recommendation, revision, experiment design and evidence judgement; 20 of its 48 runs
end before a recommendation. Details: [docs/FINAL_TEST_DIAGNOSIS.md](docs/FINAL_TEST_DIAGNOSIS.md).

**Cost.** One investigation reads about 122,000 prompt tokens and writes about 2,900, in 66 seconds on one A100 slice:
about $0.03 at a median A100 rental price, against $0.25 measured for Claude Opus 5.5 on the same task
([reports/cost/roi.json](reports/cost/roi.json)).

## How it works

- **Environment** (`src/strategy_agent/env/`): twelve guarded tools over a dossier of 1,334 public records. Quotes must
  match a source exactly, theories must give distinct causal explanations, and a simulated what-if result may change
  beliefs but cannot support a recommendation. A stage controller offers the tools of the current stage.
- **Training data** (`src/strategy_agent/pipeline/`): teacher investigations replayed through the environment; only
  those that reproduce exactly and reach an accepted finish become rows. 3,891 rows from 158 investigations on 57
  companies, plus 51 correction rows.
- **Training** (`src/strategy_agent/training/train.py`): AgentTune's distillation trainer, LoRA rank 16 on all linear
  layers, two epochs, loss on the target tool call only.
- **Evaluation** (`src/strategy_agent/evaluation/`, `reviews/judge_v1/`): AuditKIT replay and diagnostics on every run;
  blinded judge packets with the key kept apart; each judge qualified first on 20 matched sound and flawed
  investigations.

## Run it

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt \
  --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match
./run_tests.sh
```

Serve the base model with the adapter (GGUF, llama.cpp), then run an investigation or open the app:

```bash
llama-server -m tiny-aya-global-bf16.gguf --lora tiny-aya-global-strategy-lora-bf16.gguf --port 8091 --jinja
python -m strategy_agent.agent.runner --prompt compact --cases hellberg-base --output run.json
./app/run.sh   # the Strategy Lab, at http://127.0.0.1:8000
```

## Reproduce

The job scripts in `jobs/` run each stage on a Slurm cluster with A100 GPUs; set `REVISION` to a copy of this code.

1. Teacher investigations: `jobs/command_a_plus.sbatch` (Command A+ Q4_K_M with llama.cpp).
2. Rows and training: `NAME=final COMPACT=1 ROW_PROMPT=compact EPOCHS=2 SAVE=50 sbatch jobs/train_after_teacher.sbatch`.
3. Conversion check: the GGUF adapter is replayed against the PEFT adapter (`jobs/diagnose_conversion.sbatch`,
   `src/strategy_agent/evaluation/conversion_gate.py`).
4. Evaluation: `jobs/eval_adapter.sbatch` with `SPLIT=heldout ATTEMPTS=3`, once with the adapter (`PROMPT=compact`) and
   once without (`PROMPT=staged`).
5. Judging: `python -m strategy_agent.evaluation.judge_packets`, `reviews/judge_v1/run_campaign.py`,
   `python -m strategy_agent.evaluation.judge_report`. All reports are in `reports/judge/`.

The dossier in this repository keeps each record's source, URL and date with a short quote (its first sentence, at
most 25 words), so runs read shorter excerpts than the originals.

## Licence

Code: Apache 2.0. The adapter derives from Tiny Aya Global and is CC-BY-NC-4.0.
