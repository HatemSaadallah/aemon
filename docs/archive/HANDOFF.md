# Handoff, November 2, 2026

## Objective changed, night of November 1

**Read `docs/SPEC.md` first.** The project is now a strategic opportunity-analysis agent for manufacturers entering consumer markets. The notes below describe the earlier launch-decision work, which is kept as infrastructure.

**Current state, November 2:** the prototype runs end to end under a stage controller on verified evidence, and Moldex-Metric is the approved development and demonstration case. No model has been trained. Claude reviews nothing and teaches nothing: it is a workflow control and a blind judge, for the reasons in `docs/TRAINING_PILOT.md`.

**Next:** the order and open items are in `TODO.md`.

## Earlier state, evening of November 1

**Brief:** `/home/USER/Downloads/business_analysis_agent_build_prompt.txt`. One product-launch agent with six tools, fine-tuned with AgentTune and compared in AuditKIT with the strongest prompted base model.

**Ownership:** Codex stopped on November 1, and its handover is the last comment on PR #9. Claude owns everything until it returns.

**Measured:** real untrained Tiny Aya (Q4 GGUF) runs here. With all six tools, enforced JSON and the planner available, on 36 validation scenarios it finished 18, produced no fully correct problem, and followed the planner 19 of 19 times. Launch payoffs were right in 0 of 21 accepted readings. See `SUMMARY.md`. See `tooling/real_model/README.md`.

**Next:**

1. Try a stronger prompt for rule logic.
2. Add held-out wording to development, so the model can be compared fairly with the regex.
3. Hatem: licence and token scope, for real training. Disk is clear.
4. One real optimizer step, a tiny overfit test, then a bounded pilot aimed at the failures found.

Older notes follow.

User requested execution of the supplied master prompt in cooperation with Claude. Existing prompt and attachments preserved. Work lives in this directory. Claude Code subscription session launched with read/web/write permissions and assignment restricted to RESEARCH.md and PLAN.md; its final response is captured in claude_collaboration.log. A separate interactive Claude session owns tooling verification and the app. Hatem requires one folder, so both agents share this checkout and announce branch switches on GitHub.

## Decisions and completed work

Codex built `pilot.py`, a standard-library synthetic finite-horizon Bayesian decision environment and five policies. Five unit checks pass, including analytic perfect-test value, irrelevant-test stopping, invalid/budget-exhausted calls, repeatability and cost accounting. Smoke and bounded pilot run. Results are in `results/pilot.json`, with source hash, Python version, seeds, runtime and uncertainty. BASELINE.md interprets them. The tests found and fixed enumeration of impossible observation branches in the exact planner.

Classical myopic VOI is a strong baseline. Proceed provisionally with testing learned *tool selection and stopping*, rather than claiming a new strategic reasoning algorithm. Fine-tuning is not justified until a prompted permitted base model exhibits a reproducible gap that supervised trajectories can address. Fallback: reliable statistical analysis with executable correctness checks.

## Verified external checks by Codex

- Official rules and deadline inspected Nov 1: https://hackathon.lexsi.ai/ ; initial submission November 14 end of day, AoE per kickoff slide 22, which is 12:59 CET on Nov 15; Track 3 exempt from the two-repository minimum. Public HF artifacts and multiple before/after metrics required. Keep a one-day submission buffer. Other rules summarized in Claude's research document.
- Beyond Black Boxes publisher full text accessible: https://pubsonline.informs.org/doi/10.1287/stsc.2025.0432 . Published Feb 20, 2026, 976-manager trial; heterogeneous quality and confidence outcomes. No proof of profit or model-policy training effectiveness.
- Permitted candidate card accessible: https://huggingface.co/CohereLabs/tiny-aya-global ; CC-BY-NC-4.0 indicated. Actual config/tokenizer downloads returned HTTP 401 without HF authentication; Claude subsequently reports authenticated 403 GatedRepo and a possible gated-repo scope issue in PR #2. Architecture, native tool template and training compatibility therefore remain unverified locally. Do not imply model weights are available.
- AgentTune official repository accessible: https://github.com/Lexsi-Labs/AgentTune . End-to-end training not executed.

## Next actions

1. Read Claude's RESEARCH.md and PLAN.md; reconcile its candidate choice with measured BASELINE.md.
2. Resolve authorized Hugging Face gated access without logging tokens. Verify exact checkpoint revision, model size, tokenizer tool format and license conditions; choose explicit JSON action protocol if native tool support is absent.
3. Inspect actual AgentTune APIs and Cohere architecture support in an isolated environment with a Python version supported by the dependencies. Pin code revisions and packages.
4. Validate a forward pass, serialized public-state/tool round trip, short rollout and one optimizer step before estimating a longer run. 8GB VRAM is a constraint, not evidence QLoRA works.
5. Build text-grounded tool tasks where structured JSON must be selected/executed correctly. Compare reasonable prompt, strong workflow, planner and fine-tuned same model/tools/budget. Keep oracle/evaluator outside the runner's accessible filesystem.
6. Reserve new final test seeds and additional mechanism families; existing pilot results are exploratory. Add conflicting evidence, hypothesis-right/wrong pairs and calibrated insufficient-evidence decisions.

A private GitHub repository was created and pushed at the user’s explicit request: https://github.com/HatemSaadallah/lexsi-ai-hackathon . Subsequent work uses codex/* and claude/* branches and PRs. No model training, human study, paid GPU job, public artifact release, researcher contact, AgentTune/AuditKIT integration or ROI saving is claimed. The supplied PDFs and extracts are kept in this private repository at Hatem's request. They remain private working materials: they must not be republished by default, and this repository's history must not be made public. No API credential values were recorded.
