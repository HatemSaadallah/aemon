# To do

Updated November 2, 2026. The objective is in `docs/SPEC.md`, the plan in `docs/TRAINING_PILOT.md`. Submission closes at 12:59 CET on Sunday November 15. Our target is November 14.

## Hatem

- [x] Approve Moldex-Metric as the development and demonstration case
- [x] Accept the Aya Expanse 32B licence
- [x] Send the support questions and join the Discord
- [x] Confirm registration
- [ ] Go-ahead for the bounded pilot, and later for anything public

The credits coupon is not expected, and nothing depends on it.

## 1. Workflow comparison (now)

- [x] Stage controller, with replay and coverage reporting
- [x] Harness actions, refused finishes and unevaluated checks counted separately
- [x] Claude positive control of the workflow, never training data
- [x] Finish A and B on Tiny Aya Q4, and read the results
- [x] Fix the harness faults they showed
- [x] Report calls, tokens and cost for each arm

## 2. Teacher quality

- [x] Pinned Q4_K_M teacher on the cluster, with its checksum verified
- [x] Build llama-server there, and run the teacher through the identical controller on development cases
- [x] Read its theories, inferences and experiments, not just the guards
- [x] Keep rejected trajectories with their reasons (`reviews/teacher_review/`)
- [x] Try a stricter teacher prompt and several attempts: labels improved, reasoning did not, so Aya Expanse is rejected
- [ ] Test Command A+ under the same controller, and read its runs
- [ ] Decide acceptance of rows: guards plus a judge that is not Claude

## 3. Evaluation protocol, Codex leading

- [x] Draft the protocol (`docs/EVALUATION_PROTOCOL.md`, PR #18)
- [x] Fix `revision`, split protocol, suite and model ids, add provenance and negative controls
- [ ] Freeze held-out companies, product categories, questions, evidence packages, scoring rules and run limits, with mechanisms that differ from Moldex
- [ ] Add strong and non-decisive contradicting evidence to the revision packets
- [ ] Design the Socratic coach with Codex, before freezing: question-only, identical in every arm, counted as harness actions
- [ ] Blind LLM judging: frozen rubric, hidden condition, randomized order, anchor packets, disagreement, sensitivity to length
- [ ] Attribution and shock-delivery tests

## 4. Training

- [x] Real checkpoint, one AgentTune step, masked loss, system prompt, adapter reload
- [x] Environment and verified Tiny Aya weights on the cluster, with no token stored there
- [ ] Generate verified teacher trajectories, with no Claude output in any row
- [ ] Row format matches run format, and whole-episode and per-turn rows are compared
- [ ] Rerun the base at the precision the trained model will use
- [ ] Overfit a tiny set
- [ ] Make training resumable across the 1-day limit, and test it
- [ ] Bounded pilot, with failed runs kept

## 5. Evaluate and submit

- [ ] Final evaluation of A, B and C, including negative results and cases where training hurts
- [ ] Base and trained agents side by side in the Strategy Lab
- [ ] Clean public repository without the papers, model card, dataset card
- [ ] On Hugging Face: the adapter (required), plus merged weights, a GGUF quant and the adapters from each experiment (preferred)
- [ ] Nine-section Hugging Face article (see `docs/TRACK3.md`)
- [ ] Hatem's go-ahead before publishing anything
- [x] Remove the launch-decision code (November 3)
- [ ] Claim no business outcome
