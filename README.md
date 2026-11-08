# Two-eyed Ravens: Lexsi Track 3

A strategic opportunity-analysis agent for manufacturers exploring new consumer markets. It frames the problem, builds
competing causal theories, gathers evidence that could prove them wrong, designs discriminating experiments, and
revises its view. Tiny Aya Global (Cohere Labs) is fine-tuned with AgentTune on investigations by Command A+, and
evaluated with AuditKIT, executable checks and two blind LLM judges.

**Result.** On four companies it never saw, the fine-tuned agent scored **1.48** against the best-prompted base
model's **0.65** on a 0-3 blind LLM rubric (mean of two judges; **+0.83, 95% interval 0.69 to 0.97**), higher at every
company; it finished 28 of 48 investigations against 4 of 48. Limits and what still fails:
[docs/FINAL_TEST_DIAGNOSIS.md](docs/FINAL_TEST_DIAGNOSIS.md). The write-up is [docs/ARTICLE_DRAFT.md](docs/ARTICLE_DRAFT.md),
every choice is logged in [docs/DECISIONS.md](docs/DECISIONS.md), and [SUMMARY.md](SUMMARY.md) is the short version.

## Start here

```bash
./app/run.sh       # the Strategy Lab, at http://127.0.0.1:8000
./run_tests.sh     # every test suite
.venv/bin/ruff check && .venv/bin/ruff format --check && .venv/bin/pyright   # lint, format, types (from the dev extra)
```

If `.venv` is missing, rebuild it from the lock file:

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt \
  --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match
```

## What is where

```
src/strategy_agent/        the package (installed with `uv pip install -e .`)
├── common/                shared code: paths.py (every location), model_client.py (one llama.cpp request, tool-call parsing)
├── env/                   the agent's world: dossier and cases, the guarded tools, the stage controller, the checks
├── agent/                 runner.py (plays an investigation; prompts), claude_backend.py (positive control, never training data)
├── pipeline/              data: provenance manifest, training rows, recovery corrections, case import, splits, freeze, stage checks
├── training/              train.py (LoRA through AgentTune and TRL), masking_gate.py
└── evaluation/            progress measures, prefix evaluation, conversion check, AuditKIT replay, scripted controls
data/dossier/              evidence records and cases (development and the frozen final test)
jobs/                      Slurm jobs for the Bocconi cluster: teacher, training, evaluation
scripts/                   small utilities: the SSH proxy, the live training feed, environment probes
reports/                   results: pilot reports, teacher runs, row coverage, the live training mirror
app/                       the Strategy Lab: FastAPI backend, SQLite store, page in static/
tests/                     tests (to be expanded at the end)
docs/                      spec, decisions, evaluation protocol and final plan, cards, article draft; archive/ holds old documents
```

Run a module with `python -m`, for example `python -m strategy_agent.agent.runner --help`. Cluster jobs point `PYTHONPATH` at
`src/` in their own copy of the code.

## Reproducing the results

Everything heavy ran on the Bocconi HPC cluster under Slurm (A100 MIG slices); the job scripts are in `jobs/`, and each
records the code revision it ran (`REVISION`, a copy of the code at that commit). Job IDs, revisions and every
deviation are in `docs/DECISIONS.md`.

1. **Teacher investigations.** `jobs/command_a_plus.sbatch` serves Command A+ (Q4_K_M GGUF) with llama.cpp and plays
   the queued cases through `strategy_agent.agent.runner`; each episode is recorded in the provenance manifest with
   the weights hash (`src/strategy_agent/pipeline/provenance.py`).
2. **Training rows and training.** `jobs/train_after_teacher.sbatch` replays every finished teacher episode, keeps
   those that replay exactly and reach an accepted finish, builds compact-state rows (`pipeline/rows.py`), runs the
   overfit gate on 10 rows, then trains with AgentTune's distillation trainer (`training/train.py`). The final run:
   `NAME=final REVISION=20d3610 COMPACT=1 ROW_PROMPT=compact EPOCHS=2 SAVE=50 sbatch jobs/train_after_teacher.sbatch`
   (job 744559; LoRA r 16, alpha 32, all linear layers, learning rate 1e-4, batch 1 with 4-step accumulation).
3. **Conversion check.** The adapter is converted to GGUF with llama.cpp's `convert_lora_to_gguf.py`, replayed
   against the PEFT adapter (`jobs/diagnose_conversion.sbatch`), and gated by `evaluation/conversion_gate.py`.
4. **Evaluation.** `jobs/eval_adapter.sbatch` runs one arm on a case list with llama.cpp and writes a runner report
   with AuditKIT diagnostics. The final test:
   `NAME=final_test_trained PROMPT=compact ADAPTER=<adapter> SKIP_BASE=1 DIAGNOSTIC=1 ATTEMPTS=3 SPLIT=heldout CASES=<16 ids> sbatch jobs/eval_adapter.sbatch`
   and `NAME=final_test_base PROMPT=staged SKIP_ADAPTER=1 ATTEMPTS=3 SPLIT=heldout CASES=<16 ids> sbatch jobs/eval_adapter.sbatch`
   (revision d3aa608; pass the variables in the environment, since `sbatch --export` splits the comma-separated list).
5. **Judging.** `python -m strategy_agent.evaluation.judge_packets --split heldout --report base=... --report trained=...`
   builds blinded packets and a separate key; `reviews/judge_v1/run_campaign.py --backend claude|codex` judges them
   under a qualification receipt (`reviews/judge_v1/score_qualification.py`); `python -m strategy_agent.evaluation.judge_report`
   gives per-judge and mean scores with the case-cluster bootstrap. The reports are in `reports/judge/`.

Running the agent locally: serve `tiny-aya-global` (bf16 GGUF) with `llama-server --lora <adapter gguf>` on port 8091,
then use **Try it** in the Strategy Lab, or `python -m strategy_agent.agent.runner --prompt compact --cases <id> --output out.json`.

**Public copy.** The public repository is made by `scripts/build_public_repo.py` from the private one: no history, no
copies of the source papers, and every dossier excerpt cut to its first sentence (at most 25 words), with the record's
URL kept. Runs therefore read shorter excerpts than the ones used here, and the held-out digest test is skipped. The
cluster account, login host and home folder appear as `CLUSTER_ACCOUNT`, `CLUSTER_HOST` and `/home/USER`. The
models, data and traces are on Hugging Face, redacted the same way (`scripts/build_release.py`).

## Rules

- The private development repository holds the source papers and the full excerpts, so it stays private; publish only through `scripts/build_public_repo.py`.
- Label every simulated observation as simulated, and never give an agent the hidden state.
- Never invent interviews, statistics, experiment results, company intentions or causal evidence. Quote sources exactly.
- Publishing, paid jobs and contacting people need explicit approval.
- Every deliverable gets a usable UI in the Strategy Lab.
- Nothing Claude writes or scores reaches training data. Anthropic's commercial terms bar it, and `src/strategy_agent/pipeline/provenance.py` enforces it.
- Remove what becomes obsolete, in its own commit. Git history keeps it.
- The final-test split stays untouched until a frozen run.
