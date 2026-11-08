# Project specification

Current objective, set by Hatem on November 1, 2026. It replaces the launch-decision agent as the project's goal.

## The project

Build and fine-tune a **strategic opportunity-analysis agent for manufacturers exploring new consumer markets**.

The inspiration is Camuffo, Gambardella and Pignataro's work on scientific strategic decision-making, illustrated by Del Vecchio's theory that eyewear could create value as fashion (see `papers/`).

**First demonstrator:** "We manufacture industrial hearing protection. Should we enter the consumer market? For which customers, with what value proposition, and what should we investigate before investing?"

Loop Earplugs is a reference case. Repeating its story is not our contribution. We need an unresolved question for a real manufacturer, grounded in verified public sources. We have no company partner, so everything is external analysis, and it is labelled that way.

## What the agent must learn

1. Clarify the company's objective, capabilities, constraints and available evidence.
2. Frame the strategic problem, including alternatives beyond the suggested solution.
3. Construct several plausible causal theories of value.
4. State the assumptions and observable predictions behind each theory.
5. Gather evidence through tools, including evidence that could contradict a favoured theory.
6. Design practical experiments that distinguish the theories.
7. Update, reject or revise theories when new evidence arrives.
8. Recommend a next action, explaining uncertainty and what would change the recommendation.

A theory must explain the mechanism: who benefits, why they would change behaviour, and how that creates value for the manufacturer. Generic SWOT lists and confident consulting prose are failures.

## Scope correction

We were optimising a measurable failure, deriving payoff tables from business rules, because it was measurable. That is a supporting skill at most. The main evaluation now covers strategic investigation, not only numerical correctness and following a planner.

| Existing work | Status |
|---|---|
| Guarded-tool pattern, authoritative logs, replay | **Reused** for the investigation tools |
| Model harness: llama.cpp, enforced JSON, step guidance, crash-safe saving | **Reused** |
| AuditKIT replay of complete episodes, strict call counting | **Reused** |
| AgentTune path, GPU stack, token limits, loss-masking findings | **Reused** for training |
| Decision Lab | **Replaced** by the Strategy Lab in `app/`. |
| `schema_v2.py` planner, `benchmark_v2.py`, `parser_v2.py`, launch cases | **Removed** on November 3, 2026, with the rest of the launch-decision code. They remain in git history. |
| Payoff-derivation target | **Dropped as the central target.** Possibly a supporting capability. |

## Required technology

Track 3, Agentic Fine-tuning. A permitted Cohere model. AgentTune for the actual fine-tuning, AuditKIT over complete episodes with custom checks, and the strongest prompted base model as the main comparison. A prompt-based workflow alone does not complete the project.

Aristotle and similar systems already address related strategic workflows. Our work is a focused application and a training experiment. We do not claim to have invented AI strategy analysis.

## Evidence

Every record states its source URL, access date, excerpt and access limitations, and has one of these classes:

| Class | Meaning |
|---|---|
| `verified_observation` | Independently checkable: a standard, a regulation, a peer-reviewed finding, dated reporting |
| `company_claim` | What a company says about itself |
| `analyst_assumption` | Our own working assumption |
| `proposed_hypothesis` | A theory to test, never a fact |
| `synthetic` | Controlled training or test content, always labelled, never evidence of real demand |

We never invent customer interviews, market statistics, experiment results, company intentions or causal evidence.

## Training data

Episodes are built around observable decisions and tool actions: framing, searching, assessing evidence, comparing theories, proposing tests, revising conclusions. Historical cases can illustrate the method, but hindsight and memorised outcomes must not stand in for reasoning. Synthetic episodes give controlled tests, stay labelled, and cannot establish real-world demand.

## Evaluation

Compare the strongest prompted base model with the fine-tuned same model, with matched tools, evidence access and budgets, and matched inference settings.

| Dimension | How it is checked |
|---|---|
| Accurate use and citation of evidence | Executable: quotes must match the source word for word |
| Explicit, testable assumptions | Executable structure, then rubric |
| Distinct, plausible competing theories | Executable distinctness, then rubric |
| Discriminating, feasible experiments | Executable structure, then rubric |
| Appropriate revision when evidence changes | Executable, on labelled synthetic shocks |
| Tool correctness, cost, completion | Executable |

Open-ended strategy quality uses a documented rubric and blind LLM judges, because Hatem decided on November 2 against human reviewers. Those scores do not show that a recommendation is commercially sound, so results are described as improved performance under automated evaluation. We claim no improved business outcome without a real-world study.

## Limits

No publishing, contacting companies, spending money, or substantial training jobs without authorisation. The repository stays private.
