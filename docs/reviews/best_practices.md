# Best practices review, November 2, 2026

A research agent compared the project with published agent-distillation work and practitioner guides. These are the conclusions we act on. The full source list is at the end.

## What it changes

- **Scale and claims.** Published small-model agent distillation used 500 to 5,000 teacher trajectories (FireAct 500; SWE-Gym 491; AgentTuning 1,866; SWE-smith 2,000 to 5,016), and FireAct's Llama models did not learn the format at 100 or 200. With 20 to 50 investigations, the overfit and pilot steps are **feasibility tests**, and any result is exploratory. Grow by distinct cases first, then several teacher runs per case at different temperatures, capped at three.
- **LoRA on all linear layers**, not attention only. Done in `tooling/train_pilot.py`.
- **Record the config and git hash for every training run.** Done.
- **Mix in general data**, so the model keeps general ability, and test it before and after. To do.
- **Recovery rows from Tiny Aya's own stall points**, with a teacher continuation, are the first data to add after the overfit. Its main failure is repetition. To do, after the row-builder fixes.
- **Whole-episode rows where they fit:** about 1/N of the compute of per-turn rows, for the same signal. To do.
- **A few-shot baseline:** the base model prompted with one teacher example, so training is compared with prompting. To do, if it fits in 8,192 tokens.
- **Written thresholds for each gate, and a dated compute schedule to November 14.** To do.
- **Check the judges against about 30 human pass/fail labels.** Recommended, but it reverses the no-human-review decision, so it is Hatem's call.

## What it confirms

Provenance and licensing, separating plumbing tests from results, staged gates, held-out companies, coverage counts, and recording negative results are all in line with good practice. Freezing the held-out set is the highest-value open item.

## Sources

FireAct (arXiv 2310.05915), AgentTuning (2310.12823), Agent-FLAN (2403.12881), SWE-Gym (2412.21139), SWE-smith (2504.21798), AgentRefine (2501.01702, summary only), Thinking Machines "LoRA Without Regret", ReST-EM (2312.06585), DAgger (1011.0686), Distilling step-by-step (2305.02301), LLM-as-judge (2306.05685), Hamel Husain on LLM judges, Anthropic on agent evals and effective agents, Karpathy's training recipe, and Google's Rules of ML. Single-source claims are noted as such in the agent's report. AgentRefine, DAgger, ReST-EM and LLM-as-judge were read as abstracts only.
