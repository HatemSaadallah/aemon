# Training pilot design

Designed from the untrained baseline on November 1, 2026, and revised on November 2. Nothing here has been trained.

**The question:** does teacher-guided fine-tuning improve Tiny Aya's investigation quality beyond what the stage controller and a strong prompt already achieve?

**Order:** finish the workflow comparison, establish teacher quality, freeze the evaluation protocol, generate verified trajectories, run the bounded pilot, evaluate, then polish the demo.

## What the runs show so far

The current table is in `SUMMARY.md`. These are small development runs. Causes are suspected, not proven.

| Failure | What we saw | Suspected cause |
|---|---|---|
| Stalling on theories | 10 of 15 structured runs stopped repeating an earlier theory | Skill, and possibly a rigid count of three |
| Quitting early, without the controller | Open runs finish with one theory and no test | Skill |
| Weak evidence | Most support rests on company claims | Skill, and search returning company pages |
| No separating experiment | Tests are generic surveys, even from the teacher | Skill |

Framing is good once prompted, so it is not a training target.

## Data

Training data comes from a teacher through agentic distillation. A larger model is not automatically a useful teacher, so this has to be shown. Aya Expanse 32B was tried and rejected for weak reasoning (`reviews/teacher_review/`). Command A+ is the current candidate, held in node memory during a job because it exceeds the 50 GB quota.

**Teacher quality comes first.** Run it through the identical stage controller on development cases. Check that its trajectories hold distinct causal explanations, supported inferences and experiments that separate the alternatives. Passing the guards is necessary, not sufficient. Hatem authorised generating data without further approval once the teacher is good enough, Codex has reviewed, and the protocol is frozen. That does not cover the pilot.

**Every row must come from a real run.** Targets are the teacher's actual tool calls, executed through the guarded tools, never polished afterwards. Rejected trajectories are kept with their rejection reasons.

**Claude is never a data source.** Anthropic's commercial terms (D.4) bar using the service to train competing models, except as expressly approved by Anthropic. Lexsi has said using Anthropic is fine under the hackathon rules, which covers the harness test and judging, and Claude may do those. Its output cannot reach a training row, and its scores cannot decide which rows are kept. `strategy.claude_control.training_source` refuses such runs, and row selection uses the guards only.

| Source | Use | Label |
|---|---|---|
| Teacher runs on Cotral and Hellberg, with real evidence | Train | Real evidence, teacher reasoning |
| Teacher runs on other product categories, built before training | Train, for variety | Real evidence where it exists, otherwise synthetic and never evidence of demand |
| Moldex cases | Development and demonstration only | Excluded from training, and not a clean test, because we developed on them |
| Held-out companies and product categories, frozen before any run | **Final test** | Real evidence |

Moldex cannot be the final test: the prompt, checks and reference run were all developed on it. Hearing-protection evidence is also shared between companies, so memorised quotes are a leakage risk. New companies alone are not enough if their strategic problem copies Moldex, so held-out cases need different products and different mechanisms.

**Variety:** the same case type must show theories rejected as often as kept, stopping early when evidence suffices, and an honest "the evidence cannot say".

## Where it runs

The laptop stays the default for development. Training and large evaluations run on the Bocconi HPC cluster, through Slurm, on A100 slices of 40 to 80 GB. A five-minute GPU check passed on November 1. Student jobs are limited to 2 GPUs, 12 CPUs and 1 day. Nothing heavy runs on the login node.

The VPN drops full-size packets, so uploads stall unless they go through `tooling/hpc_proxy.py`, which caps the packet size. Use one persistent SSH connection for everything.

Long runs must survive that limit:

- **Resumable:** save the adapter, optimizer state, step count and random state on a fixed schedule, and again when Slurm warns that time is nearly up. A new job continues from the latest complete checkpoint. A resume must give the same data order, so nothing is trained twice or skipped.
- **Storage:** adapters only, not full model copies. Keep the latest few checkpoints, write each to a temporary name, and rename it once complete. Check the quota before each job starts.
- **Memory and time:** record peak GPU and CPU memory and seconds per step in the first short run, then size the job from those numbers. Stop cleanly before the limit, with time left to save.

## Training rows

Conversations reach about 7,000 tokens. The laptop's measured limit of about 1,024 per step no longer decides the design, because the cluster has far more memory. Long rows are still costly, and an agent that needs a shorter context is cheaper to run, so we compare two forms:

- **Whole episodes,** if they fit.
- **Per turn:** a compact state summary kept by the harness, the latest tool result, and the next tool call as target. Each row must keep what is needed to choose the action, such as the open theories, what was read, and what is unassessed.

Either way, tool outputs are context, never targets.

**Plumbing tests are not results.** The resume test trained on 12 scripted fixture rows, written by code from the Moldex development cases with no model involved. It tests resuming, masking and saving, and it is not a training experiment. Its outputs never enter the pilot, validation or evaluation.

**Overfitting and leakage.** 107 of 142 evidence records are shared market sources visible to all three development companies, so a company split still shares about three quarters of the evidence pool. Validation on these cases is not independent, and only new product categories can be. Report source overlap between the training and validation sides. Training loss may also overstate learning, because stage guidance names the next step, so some targets can be copied from the context. Hold whole companies out as validation, never single rows, because turns from one investigation are near copies of each other. Report training and held-out loss together, as a diagnostic, and keep the checkpoint with the lowest held-out loss. Lower held-out loss means better prediction of the teacher, not better investigation, so compare checkpoints on complete investigations from development cases, never the final test. Final-test cases never appear in training or validation.

## Gates, in order

| Step | Pass condition | Needs |
|---|---|---|
| 0. Before training | Workflow comparison done, teacher shown useful, evaluation protocol and held-out cases frozen | In progress |
| 1. Real checkpoint | **Passed November 2.** Loads, forward pass and tool call work | Done |
| 2. One optimizer step through AgentTune | **Passed.** Finite loss, real gradients, saved adapter reloads exactly (`tooling/real_model/checkpoint_gate.json`) | Done |
| 3. Loss masking | **Passed, through our own labels** in AgentTune's `trainer_factory` hook: 478 of 3,735 tokens carry loss. AgentTune's own fields are not read | Done |
| 4. System prompt survives | **Passed** in the rendered training row | Done |
| 5. Overfit a tiny set | The model reproduces about 10 teacher trajectories | Steps 3 and 4 |
| 6. Bounded pilot | A few hundred verified teacher rows, on the cluster, with Hatem's go-ahead | Step 5 |

## Comparison

| Condition | What it establishes |
|---|---|
| A. Untrained Tiny Aya, open workflow | Starting performance |
| B. Untrained Tiny Aya, stage controller | The effect of structure |
| C. Fine-tuned Tiny Aya, same stage controller | The further effect of training |

B and C keep the same checkpoint and precision, controller, cases, evidence, budgets, turn and retry limits, stop rules and inference settings. Report total calls, tokens and cost, with harness overhead counted apart from the model. A quantized teacher against a full-precision student is never a training effect.

The Q4 runs find failures. Rerun B at the precision C will use before comparing them.

**Quality.** No human reviews this, so results are executable checks, paired behavioural tests and blind LLM judges. Freeze the rubric first, hide model and condition, randomize order, use judges distinct from the teacher, report disagreement, and test sensitivity to output length and presentation. Include fixed anchor packets, such as the nonsense pass, a clipped quote, an incomplete run and a solid reference. The claim this supports is improved performance under automated evaluation. It is not proven managerial judgment.

**The evaluation protocol is `docs/EVALUATION_PROTOCOL.md`, and it takes precedence over this section.**

**Revision.** Deliver supporting, contradicting and irrelevant evidence at the same point in each run, right after a stated position. Record separately whether it was read, understood, and acted on. The right response may be lower confidence, a narrower theory or another experiment with the same recommendation, so a model that changes its answer whenever evidence arrives must fail. Simulated evidence is a what-if: the model is told so, reasons as if it were real, and keeps it out of what it cites.

**Coverage.** Beside every pass count, report how many runs that check applied to and how many reached it. Avoiding a check is not passing it.

**Stop and rethink if:** structure and prompting close the gaps without training, the teacher is not useful, the overfit step fails, checks improve while judged quality does not, or scores rise on training companies but not on held-out ones.

No result here could show better business outcomes. That needs a real-world study.
