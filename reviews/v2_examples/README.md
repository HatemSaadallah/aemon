# Version 2 experiment-design examples: review

`v2_accepted_examples_for_review.{md,json}`: the 17 teacher answers (of 54) that passed the correction checks and the
version 2 gates, with exact states, source dates, raw replies and acceptance reasons.

Three independent **advisory** reviews against Hatem's criteria (mechanism versus messaging, proportionate decision
rule, period consistency, other misleading features). The keep or drop decision is Hatem's; no model selects training
data.

| | sound | weak | unsound |
|---|---|---|---|
| Claude reviewer A | 0 | 3 (1, 9, 17) | 14 |
| Claude reviewer B | 0 | 3 (1, 9, 17) | 14 |
| Gemini (Antigravity CLI, read-only, examples inline) | 0 | 8 (1, 4, 5, 8, 9, 14, 15, 17) | 9 |

Shared findings: all 17 measure stated preference and none a real commitment; most vary only the message on an
identical product; nearly every rule goes from a survey gap to building; several rules are logically broken (3, 11,
15) or confounded (7); online methods in the 1970, 1983, 1989 and 1991 cases; hindsight from sources dated after the
case (2, 3, 4, 14, 15, 16, 17); decision rules cut off at the 240-character schema limit (15 of 17). Gemini's full text is
`advisory_review_gemini.txt`; the two Claude reviews are summarised here.
