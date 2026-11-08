# Project plan: Two-eyed Ravens, Track 3

Prepared November 1, 2026 by the bounded Claude Code research session. Evidence and links: `RESEARCH.md`. Labels are the same: [V] verified, [V*] indirect, [T] tested by Codex or the red-team session, [I] inferred or estimated, [P] proposal, [U] unresolved.

**State of play:** no real Tiny Aya weights have been loaded or trained. Claude reports successful tiny-random-model CUDA/NF4/LoRA gradient checks and a shape-matched random-weight memory probe in PR #2. Real-weight loading, tool behavior and the recommended distillation path remain untested. Private GitHub publishing is authorized and complete; public HF release and paid jobs require separate authorization. This is a research draft; unreviewed literature claims remain provisional.

---

## 1. Decisions in force

| Decision | Choice | Why |
|---|---|---|
| Primary | Candidate B, text-grounded decision interface | Keeps exact scoring and gives the LLM the one job a function cannot do. |
| Fallback | Candidate D, tool-restricted reliable analysis | Fails independently of B. |
| Model | `CohereLabs/tiny-aya-global`, pinned revision | Smallest permitted family; chat template in its usage examples. |
| Training method | Supervised distillation from planner-verified trajectories via AgentTune | Executable teacher, free, exact, and shown by AgentTune's own example to need no teacher model. RL does not fit the hardware. |
| Evaluation | AuditKIT for tool/final-state checks and custom domain scoring via `CustomPredicate`; domain equations and calibration checks remain project code | Those metrics are not documented as built in. |
| Scope | One agent, one domain, no UI beyond a small demo | Beyond Black Boxes and the master prompt both warn against excess architecture. |
| Default stance | Negative result is a valid submission | We report it if a prompt or parser wins. |

---

## 2. One-page project specification

**Working title.** From Memo to Decision: can a small model reliably turn business evidence into a decision problem?

**User problem.** A founder or product lead has a memo and study reports in prose. They need to know which test is worth running, when to stop, what to decide, and what that decision assumes. A planner can answer all of this once the problem is formal. The hard part is getting from prose to formal inputs without quietly introducing errors, and without being swayed by the user's stated belief.

**Hypothesis.** [P]
- H1: on the same tools, budget and held-out scenarios, Tiny Aya fine-tuned on planner-verified trajectories loses less decision value than the same model with the strongest prompt and workflow we can build.
- H0, equally reportable: a prompt, a schema-retry workflow or a parser plus planner matches it.

**Closest prior work.** ASIG and AR-BED fine-tune LLMs on information gain. TNDP amortizes decision-aware design without an LLM. Fisher-R1 supplies the training recipe. AgentAbstain supplies the paired design. BoxingGym warns that adding a statistical model may not help. We found no work combining these elements, which does not prove there is none.

**Contribution.** A narrow, tested claim about reliability at the interface between prose and a planner, on a permitted model, on consumer hardware, with a decision-value metric and a baseline designed to kill the idea.

**Agent tools.** `read_case`, `set_problem`, `compute_voi`, `run_study`, `record_result`, `finish`. See section 3.

**Data.** Simulated scenarios rendered into prose by phrase grammars. Every field has an executable key. No real firm data. No paper text in any dataset.

**Training.** SFT from planner trajectories, 4-bit LoRA at batch 1, on the RTX 4060 if that works, otherwise a free GPU.

**Evaluation.** Decision value lost vs a planner given correct inputs, field accuracy, stop agreement, calibration, paired accuracy, valid calls and latency. Compared across six arms on held-out text and families.

**Scope limits.** Synthetic world only. Inside the "decision problem" stage of the Framing paper, not investigation. Payoff-based VOI extends the Theory paper, which works with probabilities. No claim about human decisions, real demand or Knightian uncertainty. Not affiliated with or endorsed by Bocconi, IMSL or ION.

---

## 3. Environment v2

Codex owns implementation. This extends `pilot.py`, and these are requests, not orders.

**Hidden from the agent:** viability state, future outcomes, seeds, the answer key, planner outputs, scores. Evaluator code and keys must live outside the runner's reach, and the agent receives only serialized text. [P]

**Tools.** All outputs marked simulated.

| Tool | Typed arguments | Returns | Precondition | Cost |
|---|---|---|---|---|
| `read_case` | none | Memo and study descriptions in prose | none | 0 |
| `set_problem` | `prior_viable: float`, `gain: float`, `loss: float`, `budget: int`, `studies: [{name, cost, p_pos_if_viable, p_pos_if_not}]` | Validation result | none | 0 |
| `compute_voi` | none | Posterior, stop value and net VOI per study, **from the agent's own inputs** | `set_problem` done | 0 |
| `run_study` | `name: str` | Simulated report in prose | Name known and funds available | Study cost |
| `record_result` | `name: str`, `positive: bool` | Updated posterior | Study was run | 0 |
| `finish` | `decision: launch, do_not_launch, insufficient_evidence`; `p_viable: float`; `assumptions: str` | Ends episode | none | 0 |

The calculator trusts the agent's inputs, so extraction errors flow through to the decision. This makes extraction matter and keeps the arithmetic out of language generation.

**Scenario families.**

| Family | Tests | Split |
|---|---|---|
| Distractor: informative but irrelevant study | Precision | Train |
| No research is right | Stopping, no over-testing | Train |
| Budget tight | Preconditions, cost | Train |
| Uninformative studies only | Stopping | Train |
| Inverted reliability, with names reused | Reading vs memorizing | **Held out** |
| Conflicting moderate studies | Interpretation; abstention | **Held out** |
| Two studies that only pay together | Core planning diagnostic; conjunctive family from Claude PR #2, with simple family retained as control | Core |
| Impossible observation under the model | Closed-world break | Stretch |

**User-belief pairs.** Each validation and test case has a twin with the same evidence but the memo's stated belief flipped. Correct decisions must not change. Always-agree and always-challenge both cap at 50% paired accuracy.

**Text ladder.** Numeric tables, then templated prose, then varied phrasing, then verbal frequencies ("about three in four") with irrelevant numbers. **The held-out test text family is written by a different agent from the training grammar**, which is a cheap way to keep phrasing out of the training set.

**Requirements carried over.** Train, validation and test seeds disjoint. Retire Codex's exploratory test seeds. Label all simulated content. Fix the review items in `RESEARCH.md` section 8.4.

---

## 4. Evaluation

Claim first. We test tool correctness, task performance and scientific-reasoning behaviour inside the simulator. We do not test effects on people.

**Arms.** Same tools, budgets and held-out scenarios.

| Arm | Model | Workflow | Role |
|---|---|---|---|
| 0 | none | Regex parser plus planner | **Kill baseline** |
| 1 | none | Planner with true inputs | Reference. Knows the formal problem, not the hidden state. |
| 2 | Tiny Aya | Reasonable prompt | Before, weak |
| 3 | Tiny Aya | Scientific workflow prompt, few-shot, schema validation and retry | **Before, strongest** |
| 4 | Tiny Aya plus adapter | Same as arm 3 | After |
| 5 | Aya Expanse 8B | Same as arm 3, optional on free GPU | Larger reference, cost stated separately |

**Metrics.** The primary metric removes luck by scoring the evidence the agent actually saw.

| Metric | Definition | Tier |
|---|---|---|
| **Value loss (primary)** | Exact planner value minus the agent's posterior-expected value: `a * E[payoff | evidence seen] - research spent`, with `a` = 1 for launch. The posterior comes from the evaluator, not the agent. Costs appear once. | Task |
| Share of available value captured | Agent's gain over no research, divided by the planner's gain over no research | Task |
| Field accuracy | Costs and budget exact; probabilities within 0.05; payoffs within 5% | Interface |
| Stop agreement, wasted spend | Agreement with planner; spend on tests with VOI at or below zero | Behaviour |
| Calibration | Brier and log loss on `p_viable` across at least 300 predictions, plus absolute error against the exact posterior | Behaviour |
| Paired accuracy | Same correct decision on both user-belief twins | Behaviour |
| Appropriate abstention | `insufficient_evidence` used when evidence is near the decision boundary and no test is worth buying | Behaviour |
| Valid calls, unnecessary calls, completion, latency, tokens | From AuditKIT and logs | Tool |

**Statistics.** Paired by scenario, with bootstrap 95% intervals. The red-team power check needed about 257 pairs for the full test-split gap on an expected-value metric [T], so plan on **300 pairs as an exploratory starting point**, not a powered fine-tuning claim. The 257 figure is a plug-in normal approximation for oracle-versus-stop, with two-sided alpha=.05 and 80% power. At 300 pairs its minimum detectable effect is about 93% of that pilot gap; half the gap needs about 1,028 pairs if variance stays fixed. Independent recomputation of 2,000 bootstrap resamples gives [84.84, 7321.40] for the posterior-value sample-size estimate and [154.28, unbounded] for realized utility. These unstable pilot estimates must not determine final n. A learned-model contrast requires its own effect/variance estimate. Report the original distribution separately from any predeclared research-relevant stratum; reweighting changes the estimand. Report sample sizes and all arms, including failures.

**Decision gates — proposed protocol to freeze before D2, not after seeing results.** Freeze the scenario distribution and family mix, cluster IDs, primary contrast, effect margin, interval method, secondary metric, fixed sample caps, runtime cap and any replicate plan in a committed configuration before examining D2 outcomes. Validation supports development choices; only the untouched final test supports a confirmatory performance claim.

Let `H = mean(V_oracle - V_no_research)` on the predeclared distribution, computed from the simulator without model outcomes. The proposed minimum meaningful gain is `delta = 0.10 * H`; its usefulness is a design judgment to settle before D2. If H is negligible, use a fixed utility margin chosen before evaluation or abandon this task as a training target. Never divide by per-scenario headroom, which can be zero.

| Gate | Pass | Fail / below target | Inconclusive and permitted next action |
|---|---|---|---|
| D1 parser | Parser field accuracy under 95% on held-out text | Harden text once; if parser still meets the target, use fallback | Report interval and unresolved text difficulty; no favorable selective sampling |
| D2 prompt gap, 50 scenario clusters | Paired 95% interval for `Z = (V_oracle - V_prompt) - .10*(V_oracle - V_stop)` lies above zero, with extraction/interpretation/stopping errors that training could address | Upper bound below zero: prompt gap is below the target, not proof of equality; use fallback or report this result | Interval crosses zero: permit only D3's technical check (one optimizer step plus overfit 20 examples, 15-minute cap). It establishes feasibility, not training benefit. A full training pilot requires a further predeclared bounded protocol; no open-ended continuation |
| D3 technical | Finite nonzero gradients, valid tool pipeline, then overfit 20 examples within cap | Follow technical fallback ladder, section 5 | Resource/time limit: report blocked/inconclusive feasibility; no automatic extra budget |
| D4 improvement, at most 150 validation scenario clusters | Lower paired 95% bound of actual-action `V_finetuned - V_prompt` exceeds delta; the preselected secondary diagnostic must also support the mechanism | Upper bound below delta: evidence that improvement is below the chosen target, possibly still positive; upper bound below zero additionally indicates harm | Interval spans delta: report inconclusive. No automatic second run, replacement metric, or extension until significance. Any replicate must have been specified before D2 and all outcomes reported |

Field accuracy and stop agreement remain secondary. Multiple fields, turns and user-belief twins from one underlying scenario are correlated: aggregate/resample at the underlying scenario cluster, not as extra independent samples. Secondary metrics cannot turn inconclusive decision value into a claim of improved decisions. Report all raw estimates and intervals, including small positive effects below delta and inconclusive results; neither is evidence of zero effect.

**Final sample sizing.** D2's prompt-versus-oracle variance is not a measured fine-tuned-versus-prompt paired variance. Use a separate paired LLM pilot on validation only to estimate the actual contrast's variance, combined with the prespecified margin and a resource cap chosen before inspecting final-test outcomes. If the required size exceeds that cap, report the minimum detectable effect and resource-limited uncertainty. Read the final test once at its fixed size; do not add examples because its interval crosses zero. No new paid resources or additional GPU budget is implied by an inconclusive outcome.

**Reward hacks and defences.**

| Hack | Defence |
|---|---|
| Always stop (research has no expected value in about 56% of scenarios; this is not action accuracy) | Value loss, not realised utility. Weight scenarios where research has value. |
| Always test, or spend the budget | Cost is in value loss; wasted-spend metric. |
| Always say `insufficient_evidence` | Scored as no launch for value; paired and abstention metrics. |
| Always disagree with the user | Paired twins. |
| Fake a study result | Evaluator checks `record_result` against the actual tool output. |
| Tuned calculator inputs to get a wanted answer | Field accuracy is scored against the key. |
| Learn study names or phrasing | Held-out text, reused names with inverted reliability. |
| Reach the oracle | No scoring tool in the agent's path. |

Any later RL reward uses a validity gate and value terms only. It never rewards confidence, length, tool count or disagreement. LLM judges are not used for any headline metric.

---

## 5. Training plan for the RTX 4060 8 GB

**The shared installation is complete.** Python 3.12.13, torch 2.11.0+cu128, AgentTune 1.1.3 at d4db4c1, and AuditKIT 1.1.3 are installed. Claude executed the tool/bridge checks and Codex independently reran both GPU probes. The real-weight distillation path remains untested. Reuse `.venv`; do not start another installation. [T]

### 5.1 Resource facts

| Resource | Value | Status |
|---|---|---|
| GPU | RTX 4060 Laptop, 8188 MiB; about 6409 MiB free at 15:23 | Measured by interactive session |
| RAM | 15 GiB, about 5 GiB free | Measured |
| Disk | 3.6 GB free after completed `.venv` | Measured; insufficient for 6.70 GB checkpoint |
| Tiny Aya Global weights | 4.99 + 1.71 = 6.70 GB, or 6.24 GiB | [V] HF file list |
| bf16 load | About 6.24 GiB against 6.26 GiB free: no room to train | [I] |
| NF4 weights in VRAM | About 2-3 GiB. Embeddings stay unquantized. Config is gated, so this is a range | [I] |
| LoRA, optimizer, activations at batch 1, 768 tokens, gradient checkpointing | About 1.5-3 GiB | [I] |
| Aya Expanse 8B | 8B at F16, about 16 GB. Not locally trainable. | [I] |

**First blocker: disk.** After the completed `.venv`, 3.6 GB remains, which cannot hold the 6.70 GB weights, before checkpoints and logs. Local work needs at least 10 GiB free on the cache drive, so Hatem must free space or point the HF cache at another drive. Nothing should be deleted without Hatem's say-so. Otherwise use a free GPU from the start.

### 5.2 Gates, in order. Stop at the first failure.

| Gate | Check | Evidence kept |
|---|---|---|
| G0 | Hatem accepts the Tiny Aya licence with the account that matches the registration form; verify a read token has gated-repo access without exposing it | Date, revision hash, successful authorized config fetch |
| G1 | Disk free at least 10 GiB; no other GPU job | `df`, `nvidia-smi` |
| G2 | Import check from the AgentTune docs prints `ok` | Package versions |
| G3 | Load tokenizer and config. Record hidden size, vocabulary, layer modules, template | `config.json` facts |
| G4 | Load NF4 and run one forward pass. Record peak VRAM | Peak MiB |
| G5 | One tool round trip with the fallback prompt, using `use_vllm=False` | Raw transcript |
| G6 | One short rollout in environment v2 | Trajectory file |
| G7 | One optimizer step with LoRA and gradient checkpointing | Loss, peak MiB, seconds |
| G8 | Overfit 20 examples and reproduce them | Before/after outputs |

Check at G7 that loss falls only on assistant tool-call and text segments. Tool results must be masked. The real example uses `completion_only_loss=True`, while EventLog supplies `loss_mask` and `segment_weights`. How those interact on multi-turn trajectories is unverified. [U]

### 5.3 Data

**Provenance.** Each trajectory stores generator commit, seed, family, text family, planner action and tag. Each assistant turn is a tool call chosen by the planner. Rationale fields are short and templated, since the teacher has no language of its own.

**Volume.** 1,200 train and 150 validation episodes. This is below Fisher-R1's 3,851, deliberately, because of time and because the task is narrower. [P]

**Composition, so the data is not all polished successes:**

| Type | Share |
|---|---|
| Correct stop with no research | 25% |
| One test, supported hypothesis | 20% |
| One test, rejected hypothesis | 20% |
| Informative null: the test leaves the decision unchanged | 10% |
| Failed investigation: budget spent, still uncertain | 10% |
| Insufficient evidence is correct | 10% |
| Repair: a tool error followed by a corrected call | 5% |

Quality control: replay every trajectory through the environment and drop any that fail. No trajectory from a test family or text family enters training.

### 5.4 Proposed real-weight distillation configuration, untested

Claude PR #2 reports about 5,831 MiB allocated / 6,598 MiB reserved at 1,024 total tokens in a shape-matched random-weight NF4/LoRA probe, and OOM at 2,048. This supports a memory hypothesis, not full checkpoint/config equivalence or end-to-end SFT feasibility. The measured 24.3 generated tokens/sec and approximately 1.2-sec training step are probe results. Epoch/episode estimates below remain estimates: real multi-turn packing, masking and number of micro-steps have not been measured. GRPO kwarg routing passed on a tiny model; distillation quantization and tool-result masking remain gates.

| Setting | Value | Note |
|---|---|---|
| Path | `Project` + `EventLog(tier="full")` + `add_trajectory` + `sft_dataset` + `distill(..., trainer_factory=...)` | From AgentTune's example. Factory signature to confirm. |
| Quantization | NF4, double quant, bf16 compute | `bitsandbytes` is a base dependency, but no example uses it. |
| LoRA | r=16, alpha=32, dropout 0.05 | Example targets `q_proj`, `k_proj`, `v_proj`, `o_proj`. Confirm on cohere2 at G3. |
| Batch | 1, with 8 accumulation steps | |
| Max length | 768 | Tool schema in the system prompt adds tokens. Measure. |
| Gradient checkpointing | On | The example leaves it off. |
| Learning rate, epochs | 2e-4, 2 | Tune on validation only. |
| Seeds | One seed first; three if time allows | |

Record checkpoint, code revision, package versions, config, seed, split, hardware, runtime and cost for every run.

**Estimated runtime.** [I] Replace with G7 and G8 measurements immediately.

| Job | Assumption | Estimate |
|---|---|---|
| SFT, 2,400 micro-steps | 0.5-2 steps per second | 20-80 minutes |
| Inference | 10-30 tokens per second, 300-600 tokens per episode | 10-60 seconds per episode |
| Validation, 150 episodes | | 25-150 minutes |
| Test, 300 pairs across arms 2, 3, 4 | 900 episodes | 2.5-15 hours, so overnight |

**Stop conditions.** Stop on OOM, nonfinite loss/gradients, or if reserved memory approaches the measured available-memory limit; under the reported desktop load use a provisional 6.5 GiB reserved ceiling and reassess current free VRAM first. If a step takes longer than 5 seconds or the one-step check has no finite nonzero gradients, stop and investigate. A single loss decrease is not evidence of learning. Do not extrapolate from failed runs.

### 5.5 Why not RL, and why not a larger teacher

- **RL.** AR-BED used GRPO with batch 128, 8 rollouts per state and 250 steps, which is at least 32,000 rollouts. At 20 seconds each, serially, that is over 7 days. [I] Fisher-R1's 14B RL took about 36 hours on an H200 node. [V] RL also has to generate rollouts during training, and that generation would compete for the same 8 GB. [I] RL is a post-shortlist stretch only, if credits exist and Hatem authorizes them.
- **Larger LLM teacher.** The planner is exact and free, and a paid API teacher would add cost and errors that need filtering. Fisher-R1 had to drop 16.5% of LLM teacher trajectories. [V]

### 5.6 Fallback ladder

1. **4-bit LoRA on the 4060.** Main path.
2. **Free T4 on Kaggle or Colab, bf16 LoRA.** The weights fit on an estimated 15-16 GB GPU. Python and torch pins must be checked there. [U] The hackathon page mentions these free tiers; quotas are unverified.
3. **AgentTune for data, plain TRL for the trainer**, if `distill` will not accept a quantized model.
4. **Shorter episodes.** One `set_problem` call only, extraction as the sole trained skill.
5. **Fallback Candidate D** with the same pipeline.
6. **Measured negative result.** Arms 0-3 plus a small adapter, honestly reported. This still gives before/after metrics.

**Cost.** Cash cost is $0 under all of these. The $20 and $200 credits are not assumed, and redeeming them may need a payment method, which is Hatem's call.

---

## 6. Schedule, working backward from the deadline

Deadline: end of day on Nov 14 AoE (kickoff slide 22), which is **12:59 CET on Sunday Nov 15**. We keep our target of **Saturday Nov 14, 12:00 CET**, with a freeze on **Friday Nov 13, 20:00 CET**, so there is a full day of buffer. The form arrives by email a couple of days before the deadline. [V]

| Date | Work | Owner | Checkpoint |
|---|---|---|---|
| Sun Nov 1 | Pilot, red-team, research, plan | Codex, Claude | **Done.** |
| Mon Nov 2 | G0-G3. Disk freed. Review fixes to `pilot.py`. Spec environment v2. | Hatem, interactive Claude, Codex | Config facts known |
| Tue Nov 3 | G4-G5. Text grammar, held-out text by second author. Regex parser. | Interactive Claude, Codex | Round trip works |
| Wed Nov 4 | **D1 parser gate.** Environment v2 with final-decision tool. | Codex | Text is hard enough |
| Thu Nov 5 | **D2 prompt gap gate.** 50 prompted episodes. **Registration closes today AoE.** Confirm HF usernames match the form and Discord is joined. | Hatem, Claude | Material prompt gap, below-target gap, or bounded inconclusive technical check |
| Fri Nov 6 | Trajectories generated and replayed. G6-G8. **D3 technical gate.** | Codex, Claude | Overfit works |
| Sat Nov 7 | First full SFT run. Measured runtime replaces estimates. | Claude | First adapter |
| Sun Nov 8 | Validation. **D4 improvement gate.** Decide B vs D vs below-target/inconclusive report; no automatic repeat. | Both | Direction locked |
| Mon-Tue Nov 9-10 | Second and third runs at most. Stretch families only if ahead. | Both | **Code, prompts, reward and thresholds frozen Tue night** |
| Wed Nov 11 | Open new test seeds. Run arms overnight. | Claude | Test results |
| Thu Nov 12 | AuditKIT report, intervals, failure review, ROI with measured figures. | Codex | Results tables final |
| Fri Nov 13 | Safety re-evaluation note, model card, HF Article, small Space, dry run. **Freeze 20:00 CET.** | Hatem and both | Ready to publish |
| Sat Nov 14 | Hatem authorizes and publishes; submit by 12:00 CET. | Hatem | Submitted |
| Nov 15-16 | Judging. Shortlist of up to 20 teams on Nov 16. | | |
| Nov 16-21 | If shortlisted, small GRPO stretch on credits, if received and authorized. | Hatem decides | |
| Sun Nov 22 | Demo Day. | Team | |

**Reasons to abandon or narrow.**

- **Nov 3:** Tiny Aya access or disk still blocked. Move all work to a free GPU that day.
- **Nov 4:** parser solves held-out text after one hardening pass. Go to Candidate D.
- **Nov 5:** strong prompt captures about 90% of value. Do not train. Narrow or go to D.
- **Nov 6:** cannot complete one training step locally or on a free GPU. Go down the ladder.
- **Nov 8:** no validation improvement. One last run, then a negative-result write-up.
- **Nov 10:** anything still unstable is cut from scope. No new features after this.
- **Any day:** if results look too good, suspect a leak and check before believing them.

---

## 7. Research pitch

Our own proposal, for use only if Hatem chooses to share it. We have no affiliation with or endorsement from the lab, and no access to its data or software.

> Your work argues that strategic decisions begin with theories and experiments, and that the key choice is which experiment to run. But formalizing a decision is itself the hard step: your Framing paper describes it as a deliberate, "fictitious" reduction of uncertainty. We are testing a narrow question at that boundary. Can a small open model reliably turn a messy business memo into a formal decision problem, so a classical planner can decide which test is worth its cost and when to stop?
>
> We work only in a synthetic world, labeled as such, and our yardstick is a known optimal planner. We deliberately include baselines designed to beat us, and we report if they do. Our payoff-based objective extends your probability-based model, rather than implementing it. We make no claim about managers' decisions, which would need a separate human study. Your Beyond Black Boxes result is why we keep the system small and treat confident output as a risk. We would value your view on one question: which parts of framing should never be delegated to such a tool?

---

## 8. Handoff

### 8.1 Decisions

See section 1. All are reversible. The evidence that would reverse them is in `RESEARCH.md` section 11.

### 8.2 Experiments so far

| Experiment | Status | Artifact |
|---|---|---|
| Stdlib simulator, five policies, 4,000 episodes | [T] by Codex. Five unit checks reported passing. | `pilot.py`, `test_pilot.py`, `results/pilot.json`, `BASELINE.md` |
| Independent exact-value red-team | [T] by interactive Claude | `tooling/redteam/independent_check.py`, `.json` |
| Tool/stack checks | Claude reports 51 CPU tool tests, AuditKIT predicate/eventlog checks, tiny random-model GPU GRPO/NF4/LoRA checks, and shape-matched memory probes. Codex independently reran both GPU probes: memory matched, generation varied (17.9-24.3 tokens/sec). Real-checkpoint SFT/tool behavior untested. | Merged PR #2, `tooling/TOOLING.md`, `reviews/reproduction/README.md` |
| Human study, public release, contact, paid jobs | **None.** Private GitHub repo and PRs authorized and pushed. | GitHub repo and PR history |

This session wrote only `RESEARCH.md` and `PLAN.md` and ran no project code. It used read-only shell commands to list files, check tool versions and view the end of the install log.

### 8.3 Versions and sources

| Item | Version | Status |
|---|---|---|
| AgentTune | 1.1.3 import reported by Claude, commit d4db4c1 | PR #2; changelog version is not runtime version |
| AuditKIT | 1.1.3 | Logged by interactive session |
| Pinned stack | torch 2.11.0, transformers >=5.15,<6, trl 1.7.1 | [V] `pyproject.toml` |
| Tiny Aya Global | Revision not yet pinned | [U] |
| `pilot.py` | sha256 `5a613ad9...` in `results/pilot.json`. Re-verify after any change. | [T] |

Primary links are in `RESEARCH.md` section 2. The private repo is at https://github.com/HatemSaadallah/lexsi-ai-hackathon, per Codex's log. It holds the PDFs and extracted text at Hatem's request, so it must not be made public as it stands. Publish from a separate clean repository, and keep paper text and PDFs out of every public artifact.

### 8.4 Next actions by owner

**Hatem, needed for progress:**
1. Accept the Tiny Aya licence on the account matching the registration form.
2. Free at least 10 GiB on disk, or tell the agents to work on a free GPU.
3. Join Discord and confirm registration by Nov 5. Open a ticket in Discord's `report_issues`, which is private, to ask whether a planner teacher counts as distillation and whether a quantized base with an adapter meets "dense". Agents must not contact anyone.
4. Decide whether to redeem credits, and give the go-ahead before anything is published.

**Interactive Claude (tooling):** finish the install, run G2-G5, record facts in `tooling/`, and fact-check these two files, especially the quoted API names.

**Codex (simulator):** apply `RESEARCH.md` section 8.4, adopt the value-loss metric, build environment v2 and the JSON action protocol, write the regex parser, and keep evaluator code out of the runner's path.

**Both:** one agent writes the training text grammar and the other writes the held-out test text. Coordinate GPU use and do not double-install.

### 8.5 Licence and safety checklist for publishing

- Adapter and any derived model marked CC-BY-NC, with Cohere's acceptable use terms and base model reference.
- AgentTune and AuditKIT notices kept. No Lexsi or AgentTune branding in the project's name or logo.
- A short safety re-evaluation documented in the model card, for LSAL section 4, since the agent is agentic and the demo is public.
- Everything labeled simulated.
- No paper text, PDFs or tokens in any artifact.
- ROI, if included: measured throughput, dated price sources, assumptions labeled, a note that CC-BY-NC bars commercial self-hosting without a licence, and the fact that parser plus planner costs zero tokens.
