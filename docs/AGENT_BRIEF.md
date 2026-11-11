# Brief for the agents working on this repository

Updated 2026-11-04 by Claude. Read this first, then `docs/SPEC.md`, `docs/DECISIONS.md` and `SUMMARY.md`.

## Goal and scope

Aemon, a strategic opportunity-analysis agent for manufacturers: Tiny Aya Global fine-tuned with AgentTune on teacher
investigations, evaluated with AuditKIT. Submission closes 12:59 CET on 15 November; our target is 14 November.
Scope (Hatem): one final training run and one credible evaluation, not more pilots.

## Who does what

| Agent | Owns | Branch |
|---|---|---|
| Claude | Cluster jobs, teacher data, corrections, final training and evaluation, `strategy/`, `tooling/`, `app/` | `claude/strategy-agent` |
| Codex | Evaluation protocol, judge package (PR #24), held-out shocks (PR #23, rebase to include RATIONAL), reviews | its own worktree branches, as before |
| agy | Dataset card, model card and the Hugging Face article draft (below) | `claude/strategy-agent`, its own files only |

**Never switch branches in this folder.** It is shared, so a checkout moves everyone: on 2026-11-04 a switch to `agy/docs` put other agents' commits on the wrong branch. Commit only your own files to the branch that is checked out, `claude/strategy-agent`, and push it. Merges to `main` go through review.

## Rules that apply to everyone

- Training data is only provenance-verified, replay-valid demonstrations from the permitted teacher, Command A+
  (`src/aemon/pipeline/provenance.py` `TEACHER_WEIGHTS`, the manifest, `src/aemon/pipeline/rows.py`). **Claude (Anthropic) outputs
  are never training data**, under Anthropic's commercial terms. Never generate, label or relabel training rows outside
  this pipeline, and never hide where any data came from.
- The four final-test companies (`data/dossier/cases_heldout.json`, frozen in `docs/final_test_freeze.json`) are
  never opened for development, prompts or examples. The six validation companies are in `src/aemon/pipeline/splits.py`.
- Do not start, stop or change cluster jobs, and do not edit files under `strategy/` or `tooling/` without asking Claude.
- Numbers come from files in the repository, with the file named. Anything not yet measured is written as "TBD", never
  estimated. No claim of better strategy: today's defensible claim is in `docs/DECISIONS.md` ("how results are worded").
- No secrets in files or messages: no API keys, tokens or `.env` contents.

## Current state

- About 72 accepted teacher investigations; teacher queue running on the Bocconi cluster (corrections, then first
  attempts on every company, then second attempts). Collection continues toward about 200 replay-accepted
  investigations; the latest safe training start is Saturday 7 November, 18:00 CET, whatever the count.
- 64 development companies (58 training, 6 validation) plus 4 frozen final-test companies; 9 cases where no test is
  warranted.
- Two development pilots and their reports: `reports/strategy/pilot1/`, `pilot2/`, measured with
  `src/aemon/evaluation/progress.py`. Neither shows a trained model investigating better.

## agy's tasks

1. `docs/DATASET_CARD.md`: what a row is (`src/aemon/pipeline/rows.py`), the teacher (Command A+ Q4_K_M, Apache 2.0, revision and
   sha256 in `jobs/command_a_plus.sbatch`), provenance and replay, the company splits, the evidence sources and their
   licences (each batch README under the dossier history and `data/dossier/evidence.json`), recovery corrections
   (`docs/RECOVERY_PILOT.md`, protocol `correction-v1`), known limits (hindsight sources, company claims, non-English
   excerpts), and counts as TBD where the final build will supply them.
2. `docs/MODEL_CARD.md`: base model (Tiny Aya Global, CC-BY-NC-4.0), LoRA settings (`src/aemon/training/train.py`),
   intended use and out-of-scope use, the evaluation design (`docs/EVALUATION_PROTOCOL.md`), results as TBD.
3. `docs/ARTICLE_DRAFT.md`: the nine-section Hugging Face article listed in `docs/TRACK3.md`, written from the repo,
   with every result marked TBD until the final evaluation.

Write plainly. Ask Claude or Hatem when something is unclear rather than guessing.
