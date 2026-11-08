# Teacher review: first three runs

Aya Expanse 32B, Q4_K_M, code `fc9cee2`, on the identical stage controller. Three development cases, read in full by Claude Code, so this is one reader's judgment on a tiny sample. It uses no blind judge, and it says nothing about Aya Expanse in general. Raw runs are in `tooling/real_model/strategy/teacher/first_three_b.*`.

An earlier job, `first_three` on the cluster, is a harness failure: the end token broke the server's reply parser, and no turn was taken.

**Verdict: useful for workflow discipline, not yet useful for reasoning. All three are rejected as training data.**

| Measure | Result |
|---|---|
| Finished | 3 of 3, about 22 calls each |
| Looping | None. Refusals were 8 misquotes and 2 argument errors |
| Cleared every guard | 0 of 3 |
| Time | About 2.5 minutes per run, 22 tokens per second |

## What it does well

It moves through every stage, recovers from refusals and does not loop, which Tiny Aya has not yet managed under the first controller. Its three theories differ in subject.

## Rejections

| Case | Reasons |
|---|---|
| `moldex-new-evidence-looks` | Marks a generic line about Moldex's expertise as `supports` for a theory about remote workers, while its own limit note admits the quote does not address that. Quotes one source for all three theories. Recommends on "strong market demand" with no evidence of demand. Its test measures attenuation in decibels, which cannot separate who would buy. Missed the existing consumer offering. Revised a remote-work theory because of a result about appearance |
| `cotral-new-evidence-irrelevant` | Revised T2 on a warehouse printer result that bears on no theory, reasoning that it "highlights operational efficiency". Supporting evidence is company claims only. T1 and T2 predict business outcomes, not behaviour that separates them. The test method is "online survey and product testing", with a vague decision rule |
| `hellberg-base` | Quotes a children's product page for all three theories, and marks it `supports` for a theory about adult hobbyists. Predictions are sales, loyalty and market share. T3 is a marketing tactic, not a causal explanation |

## Across all three

- Theories are plausible business ideas more than competing causal explanations. Few state a mechanism that a test could separate.
- Predictions are mostly business results, which follow from every theory.
- Evidence is thin. It reads enough to pass the minimum, then reuses one source.
- Confidence stayed `medium`, whatever the evidence.

## What the guards missed

`experiment` passed a test that cannot separate the theories, and `evidence_use` passed quotes that do not bear on the theory. The `supports` label is unchecked, so an exact quote can carry a false inference. These need the blind judges.

One guard erred the other way: `framing` failed `hellberg-base`, which offers "Maintain the status quo", because its pattern does not recognise that wording.

## Next

Distilling these runs would teach Tiny Aya the workflow and also teach these reasoning habits. Before any trajectories are generated, try to improve the teacher, with Claude taking no part in choosing rows:

1. A teacher prompt with stricter rules on what counts as support, and on predictions that separate theories. The teacher's prompt may differ from the student's, because rows are its actual tool calls.
2. Several attempts per case, keeping only those that pass the guards and a review by a judge that is not Claude.
3. If that fails, Q6_K (26.5 GB, which fits the quota) or a fallback teacher.

## Update: the stricter teacher prompt

Nine more runs (`prompt_a`) on the same three cases, three attempts each at temperature 0.5, code `7e056ea`.

**Verdict: all nine rejected, and Aya Expanse 32B is not a good enough teacher for reasoning.** This is still one reader's judgment on a small sample.

- **Better:** it largely stopped claiming false support, and mostly marks company pages neutral. Where evidence bears on a theory, it now sometimes says so.
- **Unchanged:** predictions are still sales, market share and loyalty, despite a direct rule against them. Tests are generic surveys. Most runs still quote one source for every theory.
- **Worse in one way:** with almost nothing marked as support, it still recommends a direction at medium confidence, so its conclusions do not follow from its own assessments. One run stated high confidence on survey-free reasoning.
- **A hard limit:** the model is capped at 8,192 tokens, whatever the server is told, and two runs ended there. Long investigations cannot fit.

Next is a stronger teacher: Command A+, tested under the same controller with the same prompt.

## Command A+, first real runs

Command A+ Q4_K_M (Apache 2.0, revision `a26ba92`), code `b9cd4a6`, teacher prompt, on the same three cases with the current controller. Files are `tooling/real_model/strategy/teacher/cap_b.*`. One reader on three runs. **These are evaluation-only until the organizers confirm an out-of-list teacher.** The earlier `cap_first_three` job is a harness failure, because the parser rejected the thinking block before each valid call.

**Verdict: the first teacher whose reasoning is worth learning from, pending the gates.**

| Measure | Result |
|---|---|
| Finished | 3 of 3, 26 to 33 calls each |
| Refusals | 3 misquotes, 3 over budget, and no repeats |
| Time | About 29 minutes per run, reasoning before every call |

- **Theories** name mechanisms. For example, musicians adopt protection that keeps sound quality, while home-office workers want connectivity. Each has its own cause.
- **Predictions** describe behaviour that separates the theories, such as choice share against a standard product, willingness to pay, and stated purchase drivers.
- **Evidence:** independent studies support the theories (`couth-2022-musicians`, `bockstael-2015-looks`, `bogoch-2005-appearance`), a company page is marked neutral for demand, and limits are specific.
- **Tests** are choice experiments with a prediction per theory and numeric decision rules. Two of three separate the theories. The Hellberg test's predictions differed too little, which the guard caught.
- **New evidence:** it revised the fashion theory after the appearance result, and kept its theory after the irrelevant warehouse result, explaining why it bears on nothing.
- **Recommendations** say "test before investing", with stated uncertainty. One Cotral position said "invest" on a single study rated likely, which is the most overconfident moment here.

**Weaknesses:** test thresholds reappear in the recommendation, which `no_invented_numbers` flags. Theory predictions carry analyst thresholds, such as €45. One test does not discriminate.

**Before any row is used:** the organizers must confirm an out-of-list teacher, and the protocol's row screener must be qualified. At about 29 minutes a run, one cluster day gives about 48 runs, so a pilot of 50 to 100 investigations is feasible.
