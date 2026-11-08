# Lexsi hackathon: where things stand

Team Two-eyed Ravens, Track 3 (Agentic Fine-tuning). Updated November 8, 2026.

## In short

**The question:** does teacher-guided fine-tuning improve Tiny Aya's strategy investigations beyond what a stage
controller and the best prompt already achieve? Objective in `docs/SPEC.md`, the evaluation plan in
`docs/FINAL_EVAL_PLAN.md`, every choice in `docs/DECISIONS.md`.

**How:** Tiny Aya Global fine-tuned with AgentTune (LoRA, two epochs, 4,302 rows from 174 accepted Command A+
investigations on 63 companies), evaluated with AuditKIT replay checks, mechanical checks and two blind LLM judges
(Claude and Codex, each qualified on 20 sound/flawed pairs). Validation companies chose the base prompt and the
adapter; the final test ran once, frozen, on four companies never used for anything else.

## The final test (2026-11-08)

16 held-out cases (Aquaporin, Electrolux Professional, Rational, Simo; each with no new evidence, irrelevant evidence,
and a supporting and an undermining what-if result) x 3 attempts, base vs trained, 96 runs.

| | Base Tiny Aya, staged prompt | Fine-tuned |
|---|---|---|
| Blind quality, 0-3, mean of two judges | 0.65 | **1.48** |
| Finished investigations | 4 of 48 | 28 of 48 |

Trained minus base: **+0.83, 95% interval 0.69 to 0.97** (paired by case and attempt, case-cluster bootstrap). Claude
alone +0.64 [0.51, 0.77], Codex alone +1.03 [0.87, 1.18]; higher at every company under both judges (+0.60 to +1.10)
and for every kind of new evidence.

**What this does and does not show:** on four companies it never saw, under the same setup, the fine-tuned agent's
investigations score higher on a blind LLM rubric. Four companies support only a limited claim about generalisation,
and nothing here is about business outcomes. 20 of 48 trained runs still stop before a recommendation, and only 1
passes every mechanical check (all-checks success was rare in the teacher's training data too, 1 of 223 on other
cases). `docs/FINAL_TEST_DIAGNOSIS.md` traces the failures to behaviours the training data never showed: weighing a
test against declining one, what-if results that bear on a theory, and recovering from loops. On Aquaporin no run of
either arm found the company's insolvency in its dossier, and every finished trained run recommends investing. Development results and every
deviation are in `docs/DECISIONS.md`; reports in `reports/judge/dev/` and `reports/judge/final/`.

## How to see it

- `./app/run.sh`, then http://127.0.0.1:8000: the Strategy Lab compares the setups and opens any investigation step by step.
- **Try it** in that app runs one investigation live, and needs `llama-server` on port 8091.
- `./run_tests.sh` runs every suite.

## What you need to do

2. Give the go-ahead for the bounded pilot when it is ready, and later for anything public. You have already authorised generating data once the protocol and teacher gates are met.

## Dates

Submission closes at 12:59 CET on Sunday November 15. Our target is November 14.

## Rules still in force

The repository stays private. Nothing is published, no company is contacted, and no substantial training runs without your approval. The model is CC-BY-NC. We claim no business outcome without a real-world study. Claude's output does not reach training data, as `docs/DECISIONS.md` explains.

## Things that went wrong, and what changed

- **The project folder was deleted** on November 1, cause unknown, along with three other Desktop folders and the rest of the Trash, including personal documents. The repository was restored from GitHub.
- **A harness bug caused one 0 of 12.** Those runs are kept and labelled.
- **Guards were changed after seeing Claude's runs,** and so far that has helped only Claude. Each change is recorded for Codex to attack.
- **The first structured 0 of 12 was overclaimed.** Harness faults contributed, so it is only a diagnostic. It is kept and labelled.
- **Two schema limits went too far,** hiding mistakes the experiment is meant to measure. Both were reverted.
- **The first teacher job took no turns,** and still exited as a success. Server errors now fail the run.
- **Cluster connection problems:** a temporary login block, a VPN that drops full-size packets, and an SSH option that put popups on your screen. All are fixed or documented in `docs/TRAINING_PILOT.md`.
