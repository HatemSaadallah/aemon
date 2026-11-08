# Stress review of Claude PR #5

Reviewed head: `0f14f5e80a518e62bcbbf54ac701cd511a98772f`. PR #3 is merged. PR #5 is not merged by this review.

CPU only; 400 generated scenarios per family; ordinary noise .30 (prompt) and .15 (tuned). This is a sensitivity study, not an LLM result. Policy evaluation reuses Claude’s two-step planner and tree/rollout evaluator; the heavy-tail and contamination models are added by Codex. No third independent policy solver is claimed.

| Family | Error model | Tree effect | Tree paired SD | Approx. 95% interval | Rollout paired SD |
|---|---|---:|---:|---|---:|
| simple | gaussian | 0.124 | 0.455 | [0.079, 0.168] | 1.662 |
| simple | student3_equal_variance | 0.095 | 0.400 | [0.056, 0.134] | 1.839 |
| simple | sign_error_5pct_both | 0.047 | 2.057 | [-0.155, 0.249] | 2.631 |
| simple | sign_error_1pct_prompt_5pct_tuned | -0.187 | 1.625 | [-0.347, -0.028] | 2.236 |
| conjunctive | gaussian | 0.127 | 0.359 | [0.092, 0.163] | 1.940 |
| conjunctive | student3_equal_variance | 0.075 | 0.314 | [0.044, 0.106] | 1.921 |
| conjunctive | sign_error_5pct_both | 0.039 | 3.189 | [-0.274, 0.351] | 3.797 |
| conjunctive | sign_error_1pct_prompt_5pct_tuned | -0.377 | 2.541 | [-0.626, -0.128] | 3.288 |

Student-t(3) is scaled to match Gaussian input variance. Equal input variance does not fix tail frequency near action thresholds. The final utility is bounded by true payoffs and budget, so unbounded input errors do not imply unbounded score variance. Sign contamination flips extracted payoff signs, independently by arm; 5%/5% and 1%/5% are arbitrary stress assumptions. Normal intervals are exploratory, unadjusted for the multiple comparisons, and not proof of trained-model benefits or harm. One extraction is sampled per arm per scenario.

The execution counterexample uses no studies: perfect extraction scores +8 for P(viable)=.9 and +/-10 payoffs, while flipping the final decision yields zero; at P=.1, tree value is zero while a wrong launch yields -8. There is no actor-side oracle leakage in the reviewed tree scorer: true quantities are evaluator inputs. The problem is substituting a fixed future executor for the actual agent. For the same restricted policy, full-tree integration estimates the same mean return as rollout. It becomes a narrower product claim when the real LLM would instead interpret future prose and choose subsequent actions.

Additional report issue: PR #5’s single D4-effect column contains tree estimates, while rollout sample sizes use rollout means. For simple .30→.15, those are .126095 and .096599. Therefore the reported 49× sample-size ratio incorporates different estimated effect distances from the margin, not only the variance reduction. Show both effects and a common-effect sensitivity calculation.

Recommendation sent to Claude: retain actual-action whole-agent value as primary for the existing proposal, with tree extraction value as diagnostic. Rescoping to a fixed executor is possible, but must explicitly narrow the claim and reassess the trainable agent behavior. Keep the meaningful margin justified by utility, independent of which value produces a convenient conclusive result at n=300. The original 1,500-scenario PR #5 study was inspected but not fully rerun in this review.

Reproduce (source points at the reviewed PR #5 code, which is not on main yet):

```bash
python3 reviews/stress_plan_value.py --source /path/to/PR5/tooling/redteam --n 400
```
