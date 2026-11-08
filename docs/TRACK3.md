# Track 3: what is asked, and how we fit

Sources: https://hackathon.lexsi.ai and https://hackathon.lexsi.ai/kickoff-slides/ , read November 1, 2026. Wording in the first section is quoted.

## The two required tools

- **AgentTune:** "A library for post-training agents for better tool calls, syntax, and efficiency to reduce redundant or incorrect tool calls and to improve reliability." https://agenttune.lexsi.ai/
- **AuditKIT:** "An evaluation suite with a collection of benchmarks and metrics and diagnosis." https://auditkit.lexsi.ai/

The slides say to use at least 2 repos as one connected system. The website exempts Track 3. We use both either way: `src/strategy_agent/training/train.py` trains through AgentTune's `create_distill_trainer`, and `src/strategy_agent/evaluation/audit.py` replays complete episodes into AuditKIT.

## Problem statements

- **Reliable tool calling:** Train an agent with reinforcement learning on real tool-calling rollouts to choose the right tool, pass well-formed arguments and call tools in the right order.
- **Efficient trajectories:** Cut redundant, looping or failed tool calls and the number of steps per task, without lowering the success rate.
- **Agentic distillation:** Distill a stronger teacher's agent trajectories into a small student model that is cheap to run or runs locally.
- **Fine-tuning for retrieval-augmented generation:** Train a model that decides when and what to retrieve, grounds its answers in the retrieved text and ignores distracting documents.
- **Synthetic multi-hop training data:** Turn a document corpus into grounded, difficulty-graded multi-hop questions and use them to train a research or search agent.
- **Data and database agents:** Train an agent that answers business questions by querying databases or APIs (finance, operations, analytics), rewarded on verified results.
- **Business workflow and decision agents:** Automate a multi-step process with rules and approvals, such as claims handling, KYC checks, ticket triage or compliance review, with a full audit trail.
- **Self-healing agents:** Detect failing runs, classify why they failed, generate corrective training examples, retrain, and gate redeployment on measured accuracy.
- **Reward design and reward-hacking defences:** Design rewards (process rewards, LLM judges, groundedness checks) that raise real task success without being gamed.

## How Candidate B fits (our judgement)

| Problem statement | Fit | Why |
|---|---|---|
| Efficient trajectories | Strong | Buying no unnecessary studies is the task. AuditKIT's `redundant_tool_calls` and `agent_loop_detection` apply directly. "Without lowering the success rate" gives us a ready constraint. |
| Reward design and reward-hacking defences | Strong | We already have findings: `decision_regret` would reward over-testing, always-stop is a live hack, and rare sign errors can dominate. |
| Reliable tool calling | Partial | It specifies reinforcement learning. Our plan is supervised. A small GRPO pilot would be needed to claim this one. |
| Agentic distillation | Unclear | A planner is not literally "a stronger teacher's agent". This is the question for a private ticket. |
| Business workflow and decision agents | Weak so far | It requires rules, approvals and a full audit trail, and we have none of those yet. |

## How we are judged (kickoff slide 30)

An internal team first checks validity: public artifacts, write-up, checklist, no duplicates. Double-blind judges then score Write-up clarity /10, Practical usefulness /10, Code/notebook quality /10 and Overall review /100. Normalized averages decide the 10 to 20 teams at Demo Day. How the four scores combine is not stated.

## The Hugging Face article (kickoff slide 29, "complete details will be shared soon")

1. Problem statement and approach, in brief
2. Hackathon repos used: which ones, for what, and which features
3. Models used and their licenses
4. Datasets and benchmarks used and their licenses
5. Model artifacts (weights, adapters) public, as an HF collection
6. Data artifacts (datasets, logs, benchmarks) public, as an HF collection
7. Experiments run, findings and what else was tested
8. With more credits: your approach, before and after results
9. Teammates tagged

Everything public must come from a separate clean repository, because this one holds the papers in its history.
