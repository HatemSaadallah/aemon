> Research draft: reviewed corrections are incorporated below; remaining literature claims and API assertions are provisional pending source/code review. Latest tooling evidence is in Claude PR #2.

# Research map: scientific decision agents for the Lexsi hackathon

Team: Two-eyed Ravens. Track 3, Agentic Fine-tuning. Prepared November 1, 2026 by the bounded Claude Code research session.
This is our working analysis, not a product of the Bocconi or ION labs and not endorsed by them. Companion file: `PLAN.md`.

## Claim labels

| Label | Meaning |
|---|---|
| [V] | Verified by this session against the named primary source or file. |
| [V*] | Verified only indirectly: abstract only, a search excerpt, or another agent's report. The entry says which. |
| [T] | Tested. Executed by Codex or the red-team session, with the artifact named. This session did not run any code. |
| [I] | Inferred or estimated by us. Not measured. |
| [P] | Proposal. |
| [U] | Unresolved check. |

Web pages reached this session through a fetch tool that returns a processed summary, so exact identifiers should be confirmed against checked-out code. The `tooling/factcheck.md` stream owned by the interactive Claude session should catch any error here.

**Read in full:** `sources/theory.txt` and `sources/framing.txt`.
**Read in part:** the SMJ 2024 paper, pp. 1-22 of 29 (the closing discussion is unread); Camuffo et al. 2020, pp. 1-3 (results and appendices unread).
**Not read directly:** the Beyond Black Boxes full text. INFORMS returned 403 to this session and the IRIS PDF came back empty.

---

## 1. Bottom line

**Recommendation.** Primary: **Candidate B**, a small model that reads business evidence written in prose, turns it into typed inputs for a classical planner, and then stops and commits. Fallback: **Candidate D**, reliable statistical analysis with executable checks. Candidate E's paired right/wrong cases become B's evaluation design. [P]

**Fine-tuning is not justified yet.** Nothing measured so far shows it helps. Section 9 sets the test that would justify it, and section 8.3 shows why the current simulator cannot.

### The three most consequential findings

1. **On the current simulator, fine-tuning has no job to do.** [T] Exact enumeration (`tooling/redteam/independent_check.json`, 400 scenarios per split) shows myopic VOI loses 0.0003 utility units against the exact planner on test and 0.077 on shift. "One look, then decide" loses 0.0009 on test. The optimal policy is a short deterministic function. An LLM cannot beat it and can at best imitate it, and `Session.public()` already hands the agent the posterior (`pilot.py:104`). The only roles left for a language model are reading unstructured evidence and noticing when the closed world has broken. So the project must move there or stop.

2. **Disk blocks a local real-weight run; random-weight memory checks support a small quantized pilot.** [T, V, I] The completed environment leaves 3.6 GB free, insufficient for the published 6.70 GB (6.24 GiB) Tiny Aya Global weights, before checkpoints and logs. Full bf16 training has no practical activation headroom on this 8 GB desktop GPU. Claude's shape-matched random-weight NF4/LoRA probe, independently rerun by Codex, fits 1,024 total tokens at 5,831 MiB allocated / 6,598 MiB reserved; tested 2,048-token configurations OOM. That corroborates this memory path, not exact real-checkpoint/configuration or distillation compatibility. Generation across the reported runs varied from 17.9 to 24.3 tokens/sec. Licence acceptance, token scope, disk and real-weight SFT/tool masking remain gates. No hackathon model's native tool rendering should be assumed; AgentTune's fallback protocol is required for the checked templates (`tooling/TOOLING.md`, `reviews/reproduction/README.md`).

3. **"Train an LLM to do Bayesian experimental design" already exists.** [V] ASIG (arXiv 2607.03426, July 2026) and AR-BED (arXiv 2610.20832, October 2026) amortize expected information gain into LLM policies with GRPO. So the original starting hypothesis is not new. What remains open in our search: both train on information, not decision utility; neither uses an exact planner as teacher; neither targets a business decision with stopping. Those gaps are narrow, and section 7 states them as "closest known work", not as novelty.

---

## 2. Evidence matrix

| Source (primary link) | Type and date | Actual contribution | Limitations | Artifacts | Relevance |
|---|---|---|---|---|---|
| Camuffo, Gambardella, Pignataro, Theory-Driven Strategic Management Decisions. https://doi.org/10.1287/stsc.2024.0173 | Theoretical model. Strategy Science 9(4):382-396, online Nov 1, 2024. [V] | Theories as restrictions on a parameter space. Two-theory stopping model. Value of experimenting rises with number and uncertainty of theories. Superadditivity. | Normative, no data. Works with probabilities, not payoffs. Conditional on Bayes plausibility. No account of where theories come from. | CC BY 4.0 article. No code. | High. |
| Camuffo, Gambardella, Pignataro, Framing Strategic Decisions in the Digital World. https://www.sdabocconi.it/en/faculty-research/research/ion-management-science-lab/output/ | Conceptual. Manuscript Nov 2021; catalogue lists Strategic Management Review 2023, 4:127-160. [V] | Investigation vs decision problem. Better framing as advantage. Growth of knowledge as purpose. | Conjectures, no data. Our copy is the manuscript. | No code. Rights to redistribute the manuscript not established. | High. |
| Camuffo, Gambardella, Kazemi, Pandey, Beyond Black Boxes. https://doi.org/10.1287/stsc.2025.0432 | Design study plus RCT. Strategy Science 11(1):137-156. Online Feb 20, 2026 per Crossref. [V] | N = 976 managers across Aristotle, GPT-4o and human-only arms. Heterogeneous effects. User-system-problem fit. | Short-run theory ratings, not profits. Lean three-agent version only. Full text not read here. | Online appendix. Eval repo below. | Highest. See section 4. |
| Camuffo, Cordova, Gambardella, Spina, A Scientific Approach to Entrepreneurial Decision Making. https://doi.org/10.1287/mnsc.2018.3249 | RCT. Management Science 66(2):564-586, online Aug 8, 2019. [V] | 116 Italian startups. Both arms get 10 sessions; treated firms are taught frameworks and rigorous tests. | Small sample, one setting. Human training. | Data files noted on the article. | Medium. |
| Camuffo, Gambardella, Messinese, Novelli, Paolucci, Spina, Large-scale replication. https://doi.org/10.1002/smj.3580 | Four RCTs. SMJ 2024, open access CC BY. [V] | 759 firms. More termination. Fewer extreme pivot counts. Mechanisms: efficient search, methodic doubt. | First RCT is included, so not an independent replication. Revenue is highly skewed. Human, firm-level outcomes. | Public data via faculty-page link. Tresorit viewer could not be inspected. [U] | High for the action space and stop logic. |
| Bayesian Entrepreneurship (eds. Agrawal et al.). https://mitpress.mit.edu/9780262052153/bayesian-entrepreneurship/ | Edited book, April 14, 2026 per listings. [V*] MIT Press page returned 403. | Priors, Knightian uncertainty, learning, pedagogy (partial contents only). | Not read. Open-access edition reported but unconfirmed. | Possible OA PDF. [U] | Medium, background. |
| Camuffo, Gambardella, Kazemi, Internal initial conditions and path dependence. https://doi.org/10.1093/icc/dtaf051 | Two human RCTs plus synthetic AI runs. ICC 34(6):1280-1308, Dec 2025. [V] | Awareness plus optimism raises choice of the better layout (0.194, p = 0.021). Synthetic agents responded more strongly than humans. | Vignette task. Synthetic results are not human evidence. | Article. | Medium. A warning against synthetic evidence. |
| Camuffo, Espinosa, Gambardella, Pignataro, CEO Succession Under Anticipatory Awareness Misalignment. https://doi.org/10.1287/orsc.2025.20384 | Theoretical model. Organization Science 37(4):1559-1577, 2026. [V] | Closed-form results on pay, effort and dismissal under belief gaps. | Theory. No evidence an agent helps. | None found. | Low. Inspires candidate only. |
| IMSL systems: Aristotle, AutoAri, Peirce, Socrates, Leonardo, Copernicus. https://imsl.unibocconi.it/aristotle/architecture | Product descriptions. Checked Nov 1, 2026. [V] | Problem, Theory and Experiment agents with an orchestrator. Peirce is an abductive pipeline. | Request-only access. The pages report no effectiveness results. | None public. | High overlap. Do not claim to be first. |
| Evaluation repo. https://github.com/abhinavbocconi/AI-TheoryBasedDecisions_LLMEvaluation | Evaluation code. [V] | 1,962 theories, 981 participants, 2 periods. Claude-4-Sonnet and GPT-o4-mini run 10 times each. Rubrics in prompts. Chat analysis. | 981 vs 976 unexplained. Aristotle not included. README says MIT, but GitHub reports no license ([V*] logged by the interactive session). | CSV and scripts. | Medium. Do not reuse data until licensed. |
| BoxingGym. https://arxiv.org/abs/2501.01540 | Benchmark, Jan 2025, rev. Oct 2025. [V] | 10 environments. EIG and explanation-based metrics. GPT-4o struggles; adding an explicit statistical model does not reliably help. | Science domains. Needs PyMC and API keys. Nested Monte Carlo EIG. | MIT. https://github.com/kanishkg/boxing-gym | High as caution and design reference. |
| Fisher-R1 and P-Bench. https://arxiv.org/abs/2608.07437 | Preprint, Aug 2026. [V] | SFT from 3,851 QC-filtered teacher trajectories, then RL. Verified reward. Backbones Qwen2.5-Coder 7B and 14B. | 14B RL took about 36 hours on an H200 node. Single test per task. Method choice not rewarded directly. | Code, weights, benchmark. Licence not stated. https://github.com/jmu27/FisherR1 | High for method. Fallback's closest work. |
| ASIG. https://arxiv.org/abs/2607.03426 | Preprint, July 2026. [V] | Multi-turn GRPO with an EIG reward. More than doubles 20 Questions success of a 7B base. | EIG only. Code release unconfirmed. | Paper. | Closest prior work. |
| AR-BED. https://arxiv.org/abs/2610.20832 | Preprint, Oct 2026. [V] | GRPO on reasoning with EIG reward on Gemma-4-E4B. 94.7% vs 90.5% on MediQ dermatology. About 61x faster than BED-LLM per game. | GPT-5 oracle. Sensitive to hypothesis coverage. Short horizon. Some single-seed results. | Paper. | Closest prior work. |
| BED-LLM. https://arxiv.org/abs/2508.21184 | Preprint, 2025-26. [V] | Runtime EIG question selection. | Slow per game. No weight training described. | Paper. | High. |
| Deep Adaptive Design. https://arxiv.org/abs/2103.02438 and TNDP. https://proceedings.neurips.cc/paper_files/paper/2024/hash/c59f05d7ab3638b138cc61f32e1a7cd1-Abstract.html | ICML 2021; NeurIPS 2024. [V*] search-level | Amortized design policies. TNDP adds decision-aware objectives. | Not LLMs or text. | Papers. | High conceptually. TNDP is the nearest VOI-like amortization. |
| AgentAbstain. https://arxiv.org/abs/2607.10059 | Preprint, July 2026. [V] | 263 paired tasks. Best paired accuracy 59.5%. Always-act or always-refuse cannot exceed 50%. | Evaluation only. No training. | https://github.com/AntiQuality/agentabstain | High for evaluation design. |
| The Judge Knows When It Knows. https://arxiv.org/abs/2608.07517 | Preprint, submitted July 2026. [V] | 330 real A/B tests. kappa 0.14. Judges agree with each other far more than with outcomes. | Screenshot prediction, a different task. | Paper. | Warning: consensus is not evidence. |
| Google Co-Scientist. https://docs.cloud.google.com/gemini/enterprise/docs/co-scientist | Product docs, Preview. [V] | Generate, rank and refine hypotheses. | Restricted access. | None downloadable. | Low. Reference only. |
| The Agentic Scientist. https://github.com/SakanaAI/AI-Scientist-v3 | Oct 2026. Apache-2.0. [V] | Orchestrates coding agents. Evidence maps and audits. | Orchestration, not policy training. | Code. | Low. Evidence-handling ideas. |
| Agent Laboratory. https://github.com/SamuelSchmidgall/AgentLaboratory | MIT. Latest dated item seen is March 2025. [V] | Research workflow with human feedback. | Too broad for two weeks. | Code. | Low. |

Seen but not read, for later: "Does a Theory-of-Value Add Value?" (lab catalogue, working paper); Csaszar et al., https://doi.org/10.1287/stsc.2024.0190; Moscarini and Smith (2001), cited by the Theory paper and not read here.

Lab facts [V]: https://imsl.unibocconi.it/about lists Gambardella, Camuffo and Pignataro as founding directors and describes IMSL as part of SDA Bocconi. https://baffi.unibocconi.eu/research-units/ai-and-strategic-decision-making-aidec lists Gambardella as AIDEC director and does not mention ION or IMSL. Keep these bodies distinct.

---

## 3. The two foundational papers in plain language

### 3.1 Theory-Driven Strategic Management Decisions

When there is no past data, a manager cannot compute the odds of an action. So the paper says the first choice is which theory to believe, and experiments select among theories before anyone commits. A theory picks some variables ("attributes"), asserts causal links between them, and thereby rules out some parameter values. Luxottica's theory is P(high demand | fashion design) > P(high demand | no fashion design).

| Starting interpretation | Verdict | Evidence and correction |
|---|---|---|
| Strategic decisions may lack sufficient data. | Confirmed | Abstract and section 1. |
| A central task is building and selecting theories before choosing actions. | Confirmed, with a limit | Abstract. But section 5 says the paper gives no theory of how people identify and combine attributes. Theory generation is left open. |
| A theory makes assumptions, variables and relationships explicit; experiments select and revise. | Mostly confirmed | Definition C.5: a theory is a family of distributions with a restricted parameter set. Selecting is formal. Revising is only updating the distribution and the prior on the theory. |
| Separates outcome uncertainty from parameter uncertainty and beliefs. | Confirmed, and there are more layers | Layers are states (X), parameters under a distribution (mu), the prior that the theory is right (omega), and alternative theories on different state spaces (Q). |
| Results about uncertainty and surprise depend on assumptions. | Confirmed | Needs EV' = V and E omega' = omega, a cost c, a discount rho, and "decreasing information gains". Testing surprising theories is qualified by "as long as the expected values are not drastically different" (section 4.3). |

Six details that matter for any simulator:

1. **The model has no payoffs.** V and Q are probabilities, and endnote 11 says decision makers learn about plausibility "rather than making a full comparison of expected utilities". Section 3.6 says including payoffs would need a different approach such as bandits. So our VOI objective **extends** the paper. It does not implement it. [V]
2. **V and Q can concern different events.** An alternative theory has its own state space and its own state of interest (section 4.2). A simulator with one outcome variable narrows this. [V]
3. **"There is no objective reality to discover"** (section 4.2). Any simulator with a hidden true state steps outside the framework's stance. Regret measures performance in a world we defined, not in theirs. [V]
4. **Doing no research can be correct inside the model.** When V is far from Q, decision makers commit without experimenting (Figure A.1). So the no-research baseline is not a strawman. [V]
5. **Biased experiments test the frame itself.** When an unbiased experiment would say "commit", decision makers may still run one built to kill or strongly support the theory, testing omega (section 4.4). A closed-world planner assuming EV' = V never does this. This is the paper's clearest hook for agent behaviour that a planner lacks. [V, I]
6. **omega moves only past a threshold** (section 4.1, equation 7, after Ortoleva 2012). That is a departure from plain Bayesian updating. [V]

Reading note: the prose in section 5 and Appendix A says experiments continue "till" their value exceeds the alternatives, which reads backwards. Equation A.1 is the clear statement: experiment while VE exceeds the best alternative. Use the equation. [I]

### 3.2 Framing Strategic Decisions in the Digital World

Algorithms take over frequent, low-impact decisions. That frees attention for rare, high-impact ones, where the skill that matters is framing the problem. The paper argues for three complementary conditions: a scientific approach, embracing uncertainty, and owners as strategists. It proposes growth of knowledge (DK) as the firm's ultimate purpose. All of this is argued, not measured.

| Starting interpretation | Verdict | Evidence and correction |
|---|---|---|
| Automation frees attention for strategic choices. | Confirmed, conditional | Sections 2 and 7. Redeployment is an explicit open question and depends on incentives. |
| Framing, theory and evidence are central. | Confirmed | Sections 3.2 and 4.1. |
| Human judgment matters for goals, problem definition and the unfamiliar. | Confirmed, stronger than stated | "Cannot and will not be fully delegated" (section 2). Yet section 7 asks whether such decisions may be routinized through playbooks, and threshold D moves over time. |
| Knowledge growth is central; investigation can change the decision space. | Confirmed | Domain, map and framing "co-evolve" (section 4.1). |

The most important passage for this project is in section 4.1. Moving from investigation to a decision problem is a **fictitious** reduction of uncertainty. Decision makers "pretend" they can list contingencies and compute probabilities, because that is what makes experiments possible. **A finite simulator lives entirely inside this pretence.** It can test behaviour within a decision problem. It says nothing about investigation.

Section 5.1 gives direct warrant for the experiment-choice focus: "the key strategic choice" is "which experiment to run rather than what to do given the experiment". Section 5.2 names two sources of better framing. **Precision** (choosing payoff-relevant scenarios) is what a distractor study tests. **Generality** (experiments informing many options) is not captured by our design.

Citation note: section "6. Verticals" has subsections numbered 5.1 to 5.4 in our manuscript. Cite them by title.

### 3.3 Concepts mapped to agent behaviour

| Concept | Source | Candidate agent behaviour | Prototype status [P] |
|---|---|---|---|
| Bayes-plausible experiment and stopping | Theory 4.3, App. A | Run a test only while its net value is positive | Core, via tool |
| Precision | Framing 5.2 | Ignore informative but irrelevant tests | Core, distractor family |
| Commit, pivot, terminate | SMJ 7.2 | Terminal action | Core, binary first |
| Efficient search, methodic doubt | SMJ 7.3 | Test the best idea early; demand evidence | Measured through stop behaviour |
| Attributes, state of interest | Theory 3.2 | Extract target and variables from a memo | Partly, from text |
| Decision problem as "fictitious" | Framing 4.1 | State assumptions in the final output | Core, as disclosure only |
| Prior on the theory, omega | Theory 3.5 | Keep a probability that the model is wrong | Stretch |
| Biased experiment | Theory 4.4 | Run a kill test when the model says commit | Stretch |
| Alternative theory Q | Theory 4.2 | Compare two theories | Later family |
| User-system-problem fit | Beyond Black Boxes | Keep one small agent | Design rule |
| Generality, investigation, Knightian uncertainty, owners and clubs, goal-setting | Framing | None | **Out of scope** |

---

## 4. Beyond Black Boxes

**What was randomized.** [V] Published abstract: 976 managers, three arms: a lean three-agent version of Aristotle, general AI (GPT-4o), and human-only. [V*] Search excerpts of the publisher text say recruitment was on Prolific. The IRIS abstract says participants were trained in the theory-based approach. The evaluation repo implies a food-waste challenge: its success measure is the probability of a 50% food-waste reduction in five years.

**What was measured.** [V*] Theory quality rated by experts and LLMs, subjective probability of success, and confidence, plus AI aversion, automation bias and chat behaviour. The repo's LLM rubric has novelty, feasibility and scalability, environmental impact, financial impact and quality (each 1-5), plus success probability (0-100) and confidence (1-7).

**Results.**

- [V] Published abstract: "experienced managers achieve quality improvements without confidence inflation, whereas highly educated managers exhibit confidence gains without corresponding quality improvements." The abstract gives no average effect for either AI arm.
- [V*] Average effects: Codex reports reading the publisher's introduction, which distinguishes modest average general-AI quality gains from no average agentic quality gain (`COORDINATION.md`, 15:32). A search excerpt independently returned "modest but reliable gains in expert-rated quality and probability of success on average" for general AI. So the master prompt's account stands, with this caveat: this session did not read the table.
- [V*] Search excerpts also give: automation bias +0.371 (general, p<0.01) and +0.183 (agentic, p<0.05); algorithmic aversion -0.344 (general, p<0.01); PhD holders in the agentic arm at 34% vs 22% autopilot and 36% vs 41% copilot; experienced managers at 36% vs 26% copilot. Confirm against Table 1 before quoting. [U]

**Conflict to keep visible.** The IRIS record's abstract says both AI types raised confidence but not quality or success probability, plus complacency and "cognitive miserliness". The Crossref, RePEc and Semantic Scholar abstract does not. That IRIS text and the search excerpt on general AI cannot both describe the average quality result. Our working guess is that IRIS holds an earlier abstract. [I] Do not quote the IRIS wording as the published finding.

**What it does not show.** Long-run profits, the fuller Aristotle, or anything about an agent's own calibration. Theory ratings and subjective success probabilities are short-run proxies. [V]

**What it changes for us.** [I]

1. **Architecture has to earn its place.** As reported above, the purpose-built system showed no average quality gain where general AI showed a modest one. Whether the two arms differ significantly from each other is unknown to us. It is the same question as ours: does fine-tuning beat a good prompt?
2. **Calibrated agent is not calibrated user.** Improving an agent's probabilities says nothing about a human's confidence. That would need a separate human study, which we are not running.
3. **Confident output is a hazard, not a neutral feature.** Automation bias rose in both AI arms. Our outputs must show assumptions and what would change the decision.
4. **Prefer executable checks.** Their outcomes rely on expert and LLM ratings. Ours can use simulator truth, and we should use LLM judges nowhere we can avoid it.

**Evaluation repo.** 1,962 theories and 981 participants vs 976 in the paper is unresolved. [U] Treat the licence as absent, and do not reuse counts or data.

---

## 5. RCT evidence, what it does and does not say

All of this is human training with firm-level outcomes. It motivates hypotheses about an AI system and does not transfer to an LLM. [I]

- **2020 RCT.** [V] 116 startups, four-month programme. The abstract reports better performance, more pivoting, and no greater dropout than control in the early stages.
- **SMJ 2024, full sample.** [V] 759 firms: Milan 2016 (116), Milan 2017 (250), Turin 2018 (132), London 2019 (261).
  - Termination +9.8 points (p = .001), about 2.7 weeks earlier (p = .009).
  - Number of radical pivots: no linear effect, -0.053 (p = .486).
  - Pivoting exactly once +8.3 points (p = .003); more than twice -3.7 points (p = .001).
  - Revenue +EUR 6,999 (p = .030), with a mean of EUR 15,753 and SD of about 83,052, so the mean is not typical.
- **Do not simplify.** "More pivots is better" and "all treated firms did better" are both wrong. The 2020 pivot result did not replicate as a linear effect. In the SMJ re-estimate, RCT1 termination is 0.035 (p = .647), so the 2020 sample could not show what the larger sample shows.
- **Use for design.** SMJ section 7.2 gives a threshold rule for commit, pivot and terminate that maps directly to terminal actions. [V]

---

## 6. Verified hackathon rules

Source: https://hackathon.lexsi.ai, fetched November 1, 2026. Direct requests for `/rules`, `/tracks` and `/faqs` returned 404, so these come from the main page. The master prompt's snapshot held up. Items marked **new** were not in it.

| Topic | Verified content [V] |
|---|---|
| Registration | **New:** closes Nov 5 end of day AoE. Free. Teams of 1-3, one team each. At least one member must join Discord. |
| Build period | Nov 1-14, online. "Projects must be developed during the hackathon." |
| Submission | "End of day on Nov 14", AoE (kickoff slide 22), which is 12:59 CET on Nov 15. Only the final submission before the deadline counts. Late or incomplete work may not be considered. |
| After submission | Judging Nov 15-16. **New:** up to 20 teams shortlisted Nov 16. Prove-your-thesis Nov 16-21. Demo Day Nov 22, no time given. |
| Track 3 repos | AgentTune, AuditKIT. "at least 2 repos from the track, used together (except Track 3)". Preferred: 3 or more. No stated minimum for Track 3. |
| Track 3 topics | Reliable tool calling; efficient trajectories; agentic distillation; RAG fine-tuning; synthetic multi-hop data; data and database agents; business workflow and decision agents; self-healing; reward design and reward-hacking defences. Ideas outside the list are allowed if within the rules; validation via Discord #report-issues is recommended. |
| Permitted models | Dense, open-weights Cohere Labs LLM: Tiny Aya Base, Global, Fire, Water, Earth; Aya Expanse 8B, 32B. |
| Required outputs | All created artifacts on Hugging Face (models, adapters, logs, datasets). Public deployment by the deadline. More than one before/after metric. Write-up on metrics, approach, data, tasks, model, and practical improvement. HF Article; HF Space "if relevant". |
| ROI | **New detail:** optional, preferred. Self-hosting cost vs closed-source token billing, using sample volume, GPU hours, GPU hourly price and estimated tokens per second. |
| Judging | Kickoff slide 30: a validity check first (public artifacts, write-up, checklist, no duplicates), then double-blind scores for Write-up clarity /10, Practical usefulness /10, Code/notebook quality /10 and Overall review /100. Normalized averages pick 10 to 20 teams. How the four combine is not stated. Our section 11 rubric is our own working tool, not this one. |
| HF article | Kickoff slide 29 lists nine sections, with full details still to come. See `TRACK3.md`. |
| Credits | $20 HF credits for up to 800 teams, if the HF username matches the form; a payment method may be requested; credits expire 30 days after redemption. **New:** $200 for up to 20 shortlisted teams. Do not assume either. |
| Originality | Work must be your own. Open libraries and public data allowed where permitted. Teams retain ownership. |

**Rule-driven risks.** [I]

- The hard cutoff is 12:59 CET on Sunday Nov 15. We keep Nov 14 as a one-day buffer. See `PLAN.md` section 6.
- Publishing is a required step and is not yet authorized. It needs an explicit go-ahead.
- A planner as teacher is not literally "a stronger teacher model". An earlier draft said this fits three problem statements cleanly, which overstated it: "reliable tool calling" specifies reinforcement learning, and "business workflow and decision agents" requires rules, approvals and a full audit trail. `TRACK3.md` has the fit against the full wording. Whether it counts as "agentic distillation" is a question for Discord, which only Hatem can ask.
- **The ROI framing collides with the licence.** Tiny Aya is CC-BY-NC, so a self-hosting saving is hypothetical without a commercial licence from Cohere. Any ROI must say so.

---

## 7. Tooling compatibility and closest prior work

### 7.1 Compatibility matrix

"Inferred" means nobody has run it. Interactive-session results in `tooling/` supersede this table when they exist.

| Item | Finding | Status |
|---|---|---|
| Smallest permitted model | Tiny Aya family, 3.35B. Global has a chat template in its usage examples; Base's card uses plain prompts. Use Global. | [V] https://huggingface.co/CohereLabs/tiny-aya-global |
| Access and licence | Gated, CC-BY-NC with an acceptable use addendum. Weights not downloadable without accepting. Unauthenticated config access returned 401; Claude reports authenticated `403 GatedRepo` and a possible missing gated-repo token scope in PR #2. Access remains unresolved; no token values are recorded. | [V] |
| Tool format | "None of the Cohere hackathon models ... ships a chat template that renders `tools`." AgentTune falls back to schemas in the system prompt and returns results as user turns. Cohere's native action format is parsed if emitted. | [V] AgentTune README |
| Model list mismatch | AgentTune counts Aya Vision and North Micro Vision as hackathon models; the hackathon page does not. Use only the listed models. | [V] |
| Environment | Python >=3.12. torch==2.11.0, transformers>=5.15,<6, trl==1.7.1. Heavy base dependencies. The shared `.venv` was being installed with Python 3.12.13 and torch 2.11.0+cu128 when last read. Claude subsequently reports completed installation and AgentTune 1.1.3 in PR #2; see its reproducibility notes. | [V] pyproject; [U] install |
| Quantization | `bitsandbytes>=0.41.0` is a base dependency, but neither the README nor `agentic_distillation_real.py` uses it. A custom `trainer_factory` is the likely route. Claude subsequently reports tiny-random-model NF4/LoRA GRPO routing and a shape-matched memory probe. The real-checkpoint distillation factory and masking remain untested. | [V] dependency; [I] route; [U] works |
| Distillation path | `Project`, `EventLog(tier="full")`, `add_trajectory`, `sft_dataset`, `distill(STUDENT, trainer_factory=...)`. The real example loads no teacher model: its "teacher" is hand-written demonstrations. **That is the precedent for an executable planner as teacher.** | [V] example; [I] fit |
| Student size | Docs say students are small, "<3B". Tiny Aya is 3.35B. Advisory or enforced? | [U] |
| EventLog | Training rows need the full tier and weight tool calls 2.0, text 1.0, tool results 0.0. `from_eval_dict` loses step interleaving, so do not use it for sequential evaluation. | [V] docs |
| RL | GRPO, PPO, DPO, RLOO, BCO via `create_agentic_trainer`. Agentic tool training is Python API only; the CLI has no `--tools` flag. vLLM is optional, Linux and CUDA only. | [V] |
| Silent failures | `DistilledJudge` returns all-zero rewards if `transformers` is missing or its checkpoint fails. `extract_dpo_pairs` and `extract_bco_labels` return empty against real logs. `run_eval` records only tool names, so it cannot check arguments. | [V] known issues, README |
| AuditKIT agent evaluation | `auditkit.agent_eval`: `AgentCase`, `FinalStateAssertion`, `episode_from_openai_messages`, `AgentEvalSpec(mode="recorded", scorers=["tool_call_f1","tool_call_validity"])`, `AgentEvalRunner`. Verified outcome is the headline; tool, trace and judge scores are diagnostics. The docs site omits this; the GitHub README has it. | [V] |
| AuditKIT statistics | `ExperimentDB`, MLflow, bootstrap significance, `compare_models()`. Core install has zero required dependencies. | [V] |
| Domain metrics | Regret, VOI, Brier and belief-update checks are not documented as built in. Compute them ourselves. Decision correctness can go through `FinalStateAssertion`. `auditkit.agent_eval.CustomPredicate` exists and Claude reports successful threshold checks in PR #2. Domain formulas remain our responsibility; runnable predicate/eventlog evidence has been requested. | [I], [U] |
| Licences of tools | AgentTune LSAL v1.1: noncommercial, keep notices, no Lexsi or AgentTune branding. **Section 4 requires re-evaluating safety-relevant behaviour before deploying a post-trained user-facing or agentic model.** AuditKIT LSAL v1.2: free for academic research and teaching; organizations need written acknowledgement. Whether trained adapters count as derivative works is not stated. | [V] AgentTune LICENSE; [V] AuditKIT README; [U] adapters |

### 7.2 Closest prior work

| Work | How close | Key difference from Candidate B |
|---|---|---|
| ASIG, AR-BED | Closest. They fine-tune LLMs for sequential experimental design. | They reward information. They need a large oracle or generative model and GRPO at scale, and their tasks are games and clinical dialogue. Ours would use a decision-utility value, a verified planner as teacher, and a 3.35B student on a laptop GPU. |
| BED-LLM | Runtime EIG question selection. | Computes at inference. We separate computation into a tool. |
| TNDP (Huang et al.) | Closest on objective: amortized design for downstream decisions. | Not an LLM and not text. |
| Fisher-R1 | Closest on recipe: synthetic executable tasks, verified reward, SFT then RL. | Single test per task, 7-14B backbones, H200-class compute. |
| BoxingGym | Closest on environment design. | Adding an explicit statistical model did not reliably help GPT-4o. That is a direct warning for B. |
| AgentAbstain | Closest on paired design. | Evaluation only. Conflicting evidence was its hardest category (about 28%). |
| Aristotle family | Closest on domain. | Multi-agent product for humans, request-only, no published policy training. We do not compete with it. |

**Gap statement.** [I] Our searches found no paper that trains a small LLM with a decision-utility objective on business experiment selection with stopping, or that uses an exact planner as the teacher for tool-calling trajectories. This identifies the closest known work and does not prove novelty.

**Check before claiming the gap:** with ASIG and AR-BED this recent, re-search in the week of the write-up. [U]

---

## 8. What the pilot found

Codex's `pilot.py` is a synthetic launch decision: four hypotheses (viability crossed with an irrelevant attribute), four binary studies, budget 6. All values are simulated utility units. The results below were produced by Codex and the red-team session. This session reviewed code and JSON and did not re-run them.

### 8.1 Realised outcomes, 200 scenarios per split [T] `results/pilot.json`, `BASELINE.md`

| Policy, test split | Net utility | Research cost | Decision regret | Brier |
|---|---:|---:|---:|---:|
| no_research | 2.437 | 0.000 | 3.976 | 0.208 |
| random | 0.246 | 2.790 | 3.377 | 0.186 |
| information_gain (no stop) | -1.294 | 6.000 | 1.707 | 0.105 |
| myopic_voi | 2.925 | 0.920 | 2.567 | 0.174 |
| optimal | 2.915 | 0.930 | 2.567 | 0.174 |

Paired net gain of myopic VOI over no research: 0.488 [-0.252, 1.229] on test, 2.179 [1.306, 3.051] on shift.

### 8.2 Exact value, 400 scenarios per split [T] `tooling/redteam/independent_check.json`

This independent evaluator walks every outcome branch, so per-scenario differences carry no sampling noise. Regret below is against the exact Bayes value, not a clairvoyant oracle.

| Policy | Test value | Test regret | Shift value | Shift regret |
|---|---:|---:|---:|---:|
| Exact Bayes | 2.533 | 0 | 3.746 | 0 |
| myopic VOI | 2.532 | 0.0003 | 3.670 | 0.077 |
| one look, then decide | 2.532 | 0.0009 | 3.468 | 0.278 |
| no research | 2.034 | 0.499 | 1.951 | 1.795 |
| IG on viability, utility-free stop | 0.560 | 1.972 | 3.603 | 0.144 |
| plain IG, utility-free stop | -0.851 | 3.384 | 3.603 | 0.144 |
| IG, no stop (as in pilot) | -1.606 | 4.139 | 0.041 | 3.705 |

Research has any value in 43.75% of test scenarios and 97% of shift scenarios.

### 8.3 What this means

- **The research headroom on test is real but small, and realised outcomes hide it.** The whole gap is about 0.50 units. Plug-in estimates are 980 pairs on realised utility and 257 on posterior expected value, but their bootstrap intervals are [154, unbounded] and [85, 7321]. These do not fix a reliable evaluation size, nor estimate a fine-tuning effect (`power_test_split_200_pairs`). Expected-value scoring integrates hidden-state noise while retaining the action actually taken. [T]
- **EIG is not simply worse.** The stopping rule tested is utility-free (stop when viability leaves 0.1-0.9). IG with it is worse than doing nothing on test, yet close to VOI on shift. The result depends on the structure and on a distractor that was built in. Do not report it as "EIG fails". [T, I]
- **Long-horizon planning adds almost nothing here.** Do not sell a sophisticated planner on this evidence. [T]
- **Always stopping is an important baseline and a possible poorly designed reward exploit.** Research has no expected value in about 56% of test scenarios (not action accuracy), and on realised utility it is not separable from optimal at this sample size. [T, I]

### 8.4 Review notes for Codex [I]

From reading the code, in addition to the red-team results:

1. **`Session.public()` returns the posterior** (`pilot.py:104`). This removes belief updating from the agent's task. Make it a tool, or require the agent to record results.
2. **Seed aliasing.** `scenario()` and `rollout()` both seed with the same integer (`pilot.py:31`, `138`), so the random policy's first draw (`:147`) equals the draw behind `prior` (`:32`). It stops at the first opportunity exactly when prior < 0.35. This only touches a weak comparator, but it is an artifact. Derive `policy_rng` from a salted seed.
3. **Every policy shares a hard-coded terminal decision** (`pilot.py:160`). Final-decision skill is untested. An LLM arm must make that call itself.
4. **`shift` changes only public numbers.** That is a good test of reading the table vs memorizing that `market_trial` is the best study. It is not causal novelty, and `BASELINE.md` says so correctly.
5. **HANDOFF.md says full text was accessible** while this session and the interactive session got 403. Both can be true, but Table 1 values should be pasted into the repo as a checked excerpt so that the claim is auditable.

---

## 9. Is fine-tuning warranted?

| Option | On pilot v1 | On a text-grounded version | Evidence |
|---|---|---|---|
| Stronger prompt | The model would need correct arithmetic. | Must be tried first. | [U] |
| Fixed workflow: code runs extract, compute, decide, with schema validation and retry | Leaves almost no decisions to the model. | Likely removes most tool-format gains. | [I] |
| Classical myopic VOI | Near-optimal. | Equally good if inputs are right. | [T] |
| One-look rule | Near-optimal on test, weaker on shift. | Same. | [T] |
| Exact planner | Reference. Tractable in pure Python. | Needs correct inputs. | [T] |
| Regex or template parser plus planner | Not applicable. | **The kill baseline.** If it works, the LLM has no job. | [P] |
| Fine-tuned model | No role. | Conditional, below. | [U] |

**Verdict.** On v1, no. A short function solves it, with no model at all.

**Three conditions must all hold before training is justified.** [P]

1. Decision inputs exist only in unstructured text, and held-out phrasing defeats a parser.
2. The strongest prompt and schema-retry workflow on the same Tiny Aya still leaves a measurable gap.
3. The failures are of a kind planner-verified trajectories can teach, not arithmetic that a tool already handles.

**Keep two warnings in mind.** First, valid-call rate is a weak success metric, because a schema-validation retry loop can raise it with no training. A fine-tuning win has to show up in decision value, not just format. Second, the honest ceiling is parity: the model plus tools can at best match planner plus perfect parsing. The defensible claim is reliability at a narrow interface, never better reasoning than exact Bayes. If the conditions fail, we report that and narrow or switch.

---

## 10. Candidates

Compute needs below are estimates. [I] Non-LLM baselines exist or are easy for all but F.

### A. Closed-world experiment selection

| Field | Content |
|---|---|
| User | Founder or product lead with a formal decision problem. |
| Decision | Which test next, when to stop, launch or not. |
| Tools | `list_studies`, `run_study`, `voi`, `finish`. |
| Multi-step task | Compare tests, run some, stop, decide. |
| Trainable behaviour | Tool order, stopping. |
| Data | Simulator trajectories. |
| Verifiable outcome | Exact value and regret. |
| Closest prior work | ASIG, AR-BED, TNDP. |
| Feasible contribution | Decision-aware rather than information-based target, on a small model. |
| Failure modes | A short function already solves it. |
| Compute | CPU for baselines; 4-bit LoRA for the model. |
| Minimal demo | Run a scenario next to the planner. |

### B. Text-grounded decision interface (primary)

| Field | Content |
|---|---|
| User | Same user, but the evidence is memos and study reports in prose. |
| Decision | Same, plus reporting assumptions and whether evidence is insufficient. |
| Tools | `read_case`, `set_problem`, `compute_voi`, `run_study`, `record_result`, `finish` (`PLAN.md` section 3). |
| Multi-step task | Read prose, extract typed inputs, compute, test, interpret a prose result, stop, commit. |
| Trainable behaviour | Faithful extraction, correct tool use, reading results, stopping without pressure from the user's stated belief. |
| Data | Simulated scenarios rendered into text by phrase grammars with an executable answer key. Held-out text written by a different author. |
| Verifiable outcome | Field accuracy, posterior-expected value vs planner, paired accuracy. |
| Closest prior work | ASIG, AR-BED, BED-LLM, Fisher-R1 recipe, AgentAbstain design. |
| Feasible contribution | A reliable interface between prose and a planner on a permitted small model, tested against a kill baseline. |
| Failure modes | Regex wins. Strong prompt wins. Self-authored text is too easy. Tiny Aya cannot extract numbers. Training teaches phrases. |
| Compute | 4-bit LoRA at batch 1 on the 4060, or free T4. |
| Minimal demo | A messy memo, the extracted problem, the VOI table, a stop, and the assumptions shown, labeled simulated. |

### C. Hypothesis revision

| Field | Content |
|---|---|
| User | Same, when the frame may be wrong. |
| Decision | Keep the model, or flag it and revise. |
| Tools | B's tools plus `flag_model_break`, `propose_hypothesis`. |
| Multi-step task | Detect an observation that no hypothesis explains, run a kill test, expand. |
| Trainable behaviour | Detecting misspecification and proposing from a library. |
| Data | Scenarios with a planted missing hypothesis. |
| Verifiable outcome | Detection rate, false alarms, value after revision. |
| Closest prior work | Peirce (described), Karni and Vierø (cited in Theory), BoxingGym model discovery. |
| Feasible contribution | Tests the paper's biased-experiment idea. |
| Failure modes | A Bayesian catch-all hypothesis may solve it. The evaluator knows the "unknown" hypothesis, so this is anticipated misspecification and **not** Knightian uncertainty. |
| Compute | As B, plus more data. |
| Minimal demo | The agent stops trusting its model when an impossible result appears. |

### D. Reliable analysis (fallback)

| Field | Content |
|---|---|
| User | Analyst with a small dataset and a business question. |
| Decision | Which test, whether assumptions hold, what can be concluded. |
| Tools | `describe_data`, `check_assumption`, `run_test` from a fixed registry, `finish`. |
| Multi-step task | Inspect, choose, run, interpret, bound the recommendation. |
| Trainable behaviour | Method selection, assumption checks, not overclaiming. |
| Data | Synthetic tasks with an executable key, modelled on Fisher-R1. |
| Verifiable outcome | Method match, p-value closeness, reject decision, abstention. |
| Closest prior work | Fisher-R1 and P-Bench. |
| Feasible contribution | A cheap, tool-restricted version on a 3.35B model. Fisher-R1 itself leaves method-selection reward open. |
| Failure modes | A rule tree solves it. Heavy prior art. Weak link to theory selection. |
| Compute | As B. No code execution by the model, which lowers risk. |
| Minimal demo | Same dataset, wrong test vs right test, recommendation changes. |

### E. Evidence challenger

| Field | Content |
|---|---|
| User | Manager with a preferred strategy. |
| Decision | Endorse, challenge or request a test. |
| Tools | B's tools, plus user claims in the brief. |
| Multi-step task | Find the assumption the decision rests on, seek discriminating evidence, or endorse. |
| Trainable behaviour | Truth-seeking regardless of the user's stated view. |
| Data | Paired cases with identical evidence and flipped user claims. |
| Verifiable outcome | Paired accuracy; agreement cannot be the score. |
| Closest prior work | AgentAbstain; the Theory paper's biased experiments; SMJ's methodic doubt. |
| Feasible contribution | Sycophancy test tied to decision value. |
| Failure modes | Always challenging. Prose quality not executable. |
| Compute | As B. |
| Minimal demo | Same evidence, flipped user belief, same correct decision. |

### F. Causal-evidence agent

| Field | Content |
|---|---|
| User | Strategist reviewing literature. |
| Decision | Is a link causal, and does it need a new test? |
| Tools | Retrieval, classification, gap report. |
| Multi-step task | Retrieve, grade, identify the gap. |
| Trainable behaviour | Telling causal from correlational support. |
| Data | Would need a curated corpus. |
| Verifiable outcome | Human or LLM labels, which are weak. |
| Closest prior work | Leonardo (described). |
| Feasible contribution | Unclear. |
| Failure modes | No executable truth; overlap with Leonardo. |
| Compute | Moderate. |
| Minimal demo | Graded evidence table. |

Dropped: **stakeholder-belief agent**. It has an attractive link to the CEO-succession paper but no outcome we can verify without simulated people.

---

## 11. Rubric comparison

This is our working rubric, not an official one. Scores are 1-5. Treat each as about ±1, and do not read gaps under 0.3 as real. [P]

| Criterion (weight) | A | B | C | D | E | F |
|---|---:|---:|---:|---:|---:|---:|
| Measurable, trustworthy (20%) | 5 | 4 | 3 | 5 | 4 | 2 |
| Feasible (20%) | 4 | 3 | 2 | 3 | 3 | 2 |
| Role for fine-tuning (15%) | 1 | 3 | 3 | 3 | 3 | 2 |
| Faithful to the research (15%) | 4 | 4 | 5 | 2 | 4 | 3 |
| Practical usefulness (10%) | 2 | 3 | 3 | 4 | 3 | 3 |
| Differentiation (10%) | 2 | 3 | 4 | 2 | 3 | 1 |
| Clarity of demo (10%) | 4 | 4 | 3 | 4 | 4 | 2 |
| **Weighted** | **3.35** | **3.45** | **3.20** | **3.35** | **3.45** | **2.35** |

Rationales:

- **A:** best measured and easiest, but the role for fine-tuning is scored 1 on direct evidence (section 8). This is the only score here backed by a measurement.
- **B:** keeps A's exact scoring, gives the LLM a job only it can do, and stays linked to the papers. Fine-tuning is 3, not higher, because the role is conditional. Feasibility is 3 because 4-bit training is unproven.
- **C:** the most faithful to the Theory paper's biased experiments and the most differentiated, but "unknown" hypotheses are planted, and two weeks is tight.
- **D:** the best executable truth and direct practical value, but it is weakest on the research link and sits under Fisher-R1's shadow.
- **E:** ties B. It needs B's environment to exist.
- **F:** no trustworthy score and clear overlap with Leonardo.

**Choice.** The rubric cannot separate B and E, so structure decides: E depends on B's environment, so B goes first and E's paired cases become B's evaluation. **The fallback is D, not A or E,** even though E scores higher, because a fallback has to survive what kills the primary. E and A share B's environment. A has no role for training. D does not depend on text-to-planner extraction.

**Sensitivity.** If 4-bit training and free GPUs both fail, B drops to 3.25. If regex solves the text, B drops to 3.15 and D leads. If the fine-tuning gap proves real, B rises to 3.60.

**Finalists' riskiest assumptions and cheapest tests.** [P]

| Finalist | Riskiest assumption | Cheapest useful test |
|---|---|---|
| B | Tiny Aya with a strong prompt has a gap that training can close and a parser cannot. | Stdlib regex parser on held-out text, then 30-50 prompted episodes. No training. |
| D | A 3.35B model beats a rule tree at picking a test. | Write the rule tree and run it on 100 synthetic tasks. |

**What would reverse the recommendation.** Switch from B to D if the parser reaches about 95% field accuracy on held-out text after one hardening pass, or if the strong prompt captures about 90% of available value, or if Tiny Aya cannot extract numbers even with few-shot examples. Reconsider C only if B finishes early. Drop fine-tuning altogether and submit a measured negative result if neither B nor D shows a trainable gap by November 8.

---

## 12. Limits and open checks

**Limits that must stay visible in anything we publish.**

- Synthetic results hold within our assumptions. They say nothing about real markets.
- LLM-written or simulated interviews and reports are not evidence about customers. Every observation is labeled simulated.
- A calibrated agent does not reduce human overconfidence. That needs a human study.
- The papers motivate hypotheses about an AI system. Human training results do not transfer to an LLM.
- A finite simulator operationalizes only the decision-problem stage. Knightian uncertainty, goal-setting, framing a new domain and governance stay out of scope.
- More agents, calls or experiments are not better by themselves.
- Public code does not establish reliability, a reusable licence or compatibility.
- Search finds closest known work and cannot prove novelty.

**Unresolved.** [U]

1. Table 1 of Beyond Black Boxes, arm sizes and exact average effects.
2. 981 vs 976 participants, and the evaluation repo's licence.
3. Whether the Tiny Aya weights load, quantize, checkpoint and train under AgentTune.
4. Tiny Aya exact checkpoint configuration and tool behaviour remain gated/unverified locally. Claude reconstructed hidden size and vocabulary from an ungated GGUF header in PR #2; this supports its shape probe but does not replace checkpoint/config verification. The Tiny Aya cards also mention a "111 billion parameter model" in their terms, which conflicts with 3.35B and looks like template text.
5. Whether `<3B` is enforced, and whether a planner teacher counts as distillation.
6. Whether trained adapters are derivative works under LSAL v1.1.
7. Whether a quantized base with an adapter fits "dense".
8. The RCT data contents and reuse terms.
9. Free-tier GPU quotas and Python versions on Kaggle and Colab.
10. Disk quantity is resolved: 3.6 GB free after installation, insufficient for the 6.70 GB weights. What remains unresolved is an authorized storage/free-compute solution; no files will be deleted without authorization.
