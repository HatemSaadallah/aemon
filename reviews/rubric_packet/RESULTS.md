# Blind rubric pre-screen

One LLM reviewer scored these seven investigations blind on November 1, 2026, using `docs/RUBRIC.md`. **This is a pre-screen, not independent human review**, and the rubric calls for two human reviewers. Totals are out of 24, a convenience sum the rubric does not define.

| Investigation | Source | Case | Total |
|---|---|---|---|
| 1 | plain | cotral-base | 5 |
| 2 | strong | moldex-base | 5 |
| 3 | supplied | moldex-base | 6 |
| 4 | strong | cotral-base | 8 |
| 5 | reference | moldex-base | 21 |
| 6 | plain | moldex-base | 5 |
| 7 | supplied | cotral-base | 5 |

The six model runs scored 5 to 8. Across them, the weakest dimensions were experiment design, 0 of 18, and use of evidence, 1 of 18. No model run contained a test, though one model run elsewhere in the baseline did.

The authored reference scored 21, which only shows the rubric can reward a complete investigation. It was written by the same analyst who wrote the rubric, so it is not a fair comparison. The reviewer also found real flaws in it:

- A clipped NHS quote, which drops the point that short-term use may help
- A theory left neither tested nor dismissed
- A test that measures wearing but not whether venues will pay
- About four events per arm, which looks too few for a 2-point gap
- No revision after logging contradictions

Issues raised with the rubric itself: revision did not separate strong from weak, the low rungs of "distinct theories" are unclear, an invented number can raise a score, and early-stopped runs can outscore finished ones on framing.
