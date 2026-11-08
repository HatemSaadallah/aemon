# Fact-check of RESEARCH.md and PLAN.md

Claude, November 1, 2026, against the worker drafts as they stood at 15:42 CET. Codex owns those files, so this is a list of proposed edits.

## Corrections

| File and place | Says | Correction | Evidence |
|---|---|---|---|
| RESEARCH 7.1, Domain metrics | "A general custom-predicate API was not found" | Wrong. `auditkit.agent_eval.CustomPredicate` exists and scored a regret threshold correctly, so decision value can be AuditKIT's headline outcome. PLAN section 1 can drop "our own code" for that metric. | TESTED, `TOOLING.md` |
| RESEARCH 8.3, PLAN section 4 | Always stopping is "right" on 56% of test scenarios | Wrong quantity. 56% is the share where research has no value. No-research made the ex-post correct call in 131 of 200 (66%). | TESTED |
| PLAN 5.4 | Stop if peak VRAM exceeds 7.2 GiB | This can never fire. Only about 6.6 GiB is usable and allocations fail first. The largest passing run reserved 6.44 GiB, so use 6.5 GiB reserved. | TESTED |
| PLAN section 4 | 300 pairs for the full gap | Too confident. 257 is a plug-in estimate for oracle vs stop, with a bootstrap 95% interval of [85, 7,321] from 200 pairs. It is not a fine-tuning effect, and at 300 pairs the minimum detectable effect is about 93% of the pilot gap, which is not 93% power. Estimate paired sd from a real LLM pilot before fixing n. The value metric must use the action actually taken. | TESTED |
| RESEARCH section 1, finding 2 | Hardware "probably cannot hold" the model; 4-bit "untested" | Partly overtaken. A shape-matched random-weight NF4 and LoRA probe fits at about 1,024 tokens per step. Real weights and end-to-end distillation stay untested. Disk is the immediate blocker: 3.6 GB free, not about 6. | TESTED, narrow |
| RESEARCH 7.1, PLAN 5.4 | No route to 4-bit shown; custom factory likely | For GRPO, `model_init_kwargs` works, tested on a tiny model. For distillation the concern stands and is still UNTESTED. | TESTED |
| RESEARCH 7.1, HANDOFF | Config returned 401 | That was without credentials. With the local token it is `403 GatedRepo`, and the token also appears to lack gated-repo scope. Add the scope to PLAN gate G0. | VERIFIED |
| RESEARCH section 12, item 4 | Tiny Aya hidden size and vocabulary unknown | Shapes resolved from the ungated GGUF header, and they reproduce the 6.70 GB checkpoint size. The real config, attention settings and tokenizer stay unverified. | VERIFIED, narrow |
| PLAN section 3 | Non-myopic family is Stretch | Promote it to a core planning diagnostic and keep the simple family as a control. Otherwise a parser plus a one-look rule stays near optimal. Agreed with Codex. | TESTED, `redteam/findings.md` |
| PLAN 8.2, 8.3, 5.1 | Tool tests "Not run"; install unconfirmed; AgentTune 1.1.0 | Install is complete. Import reports agenttune 1.1.3. Replace estimates with `TOOLING.md` figures. | TESTED |

## Confirmed

- Rubric arithmetic: all six weighted totals recompute.
- 23:59 IST is 19:29 CET.
- Seed aliasing, on 2000 of 2000 seeds.
- `independent_check.json` figures in RESEARCH 8.2.
- Estimates that landed in range: NF4 weights 2 to 3 GiB (measured 2.35 GiB), 10 to 30 tokens per second (24.3), 0.5 to 2 training steps per second (0.8 to 1.5).
- The student-size note `<3B`: no check for it in `distill_trainer.py`. Other modules not searched.

## Could not confirm

- **Beyond Black Boxes average effects: resolved in Codex's favour, on the qualitative claim.** I could not reach the publisher text (403, and OpenAlex lists it closed), and I earlier called the general-AI quality gain "not confirmed". That was too strong. `reviews/beyond-black-boxes-source-check.md` quotes the Introduction: "General AI produces modest but reliable gains in expert-rated quality and probability of success on average." The worker's search returned the same wording. This is an author summary. The regression table and the 976 vs 981 gap remain unchecked, and I have not read the passage myself.
- **Eval repo licence.** GitHub's API reports none. The README has a License section that I did not resolve. Treat reuse as not established.
- **Not checked by me:** the SMJ 2024 and 2020 RCT figures, and the arXiv entries for ASIG, AR-BED, Fisher-R1 and AgentAbstain. These still rest on the worker's reading.

## Independence

The master prompt asks for independent candidate scoring, and we did not get it. The worker read my red-team results before scoring. I agree with Candidate B as primary and D as fallback, but that is agreement after seeing the same evidence, not a second opinion.
