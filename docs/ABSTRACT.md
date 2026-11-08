# Abstract

**Teaching a 3B model to investigate a strategy question: agentic distillation with AgentTune and AuditKIT.**
Team Two-eyed Ravens, Lexsi hackathon Track 3 (agentic distillation; efficient trajectories; workflow and decision agents).

Asked whether a manufacturer should take its technology to a new market, language models tend to write consulting
prose: unsourced numbers and evidence gathered only for the answer they started with. We built an investigation
environment in which an agent must work like a scientist: frame the decision, state rival causal theories, assess
quoted evidence from a dossier of 1,334 public records, look for evidence against its favourite, propose a test with a
decision rule (or decline one), revise when a what-if result arrives, and recommend. Twelve guarded tools and a stage
controller enforce the procedure; every call is replayable.

Command A+ served as the teacher. Its investigations were replayed through the environment, and only those that
reproduced exactly and reached an accepted finish became training data: 174 investigations, 3,891 rows on 57 training
companies, plus 51 correction rows. We fine-tuned Tiny Aya Global with AgentTune's distillation trainer (LoRA, two
epochs) and evaluated with AuditKIT replay and diagnostics, executable checks, and two blind LLM judges (Claude and
Codex), each qualified on 20 matched sound/flawed pairs. Six validation companies chose the base prompt and the
adapter; a frozen final test then ran once on four companies never used for anything else: 16 cases, three attempts,
96 runs. Every converted adapter had to match its PEFT original before evaluation, and the evaluated file is the gated
one.

On the final test the fine-tuned agent scored **1.48** against the best-prompted base model's **0.65** on the 0-3
rubric (mean of the two judges; **+0.83, 95% case-cluster interval 0.69 to 0.97**), higher at every company under both
judges and for every kind of new evidence. It finished 28 of 48 investigations against 4 of 48. Self-hosted, an
investigation takes 66 seconds on one A100 slice, about $0.03 at a median rental price, against $0.25 measured for
Claude Opus 5.5.

What still fails is specific: only 1 of 48 runs passes every mechanical check, and 20 stop before recommending.
Several failures trace to behaviour the training data never showed: no example declines a test, few what-if results
bear on a theory, and there is no recovery from rereading or from citing simulated evidence. On one company no run
found the insolvency recorded in its dossier. Four companies support only a limited claim about generalisation; the
improvement plan targets these gaps, to be measured on fresh companies.

Code: https://github.com/HatemSaadallah/lexsi-strategy-agent. Models, data and traces: Hugging Face collection
(link to follow).
