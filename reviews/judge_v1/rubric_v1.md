# Strategy quality rubric

An instrument for blind LLM judges, since no human reviewers are planned. The executable checks in `strategy/checks.py` only catch mechanical failures: a deliberately nonsense investigation has passed every one of them. LLM scores add a view of the reasoning, but they do not show a recommendation is commercially sound. Describe results as improved performance under automated evaluation.

## How to score

- Read the complete investigation, not only the final recommendation. Judges never see the model, condition or order of runs.
- Freeze this rubric before final evaluation. Every condition gets the same judge prompt and settings, and judges are distinct from the teacher.
- Keep every judge output. Report disagreements, without averaging them away, and test sensitivity to output length and presentation.
- Score fixed anchor packets too: the nonsense pass, a clipped quote, an incomplete run and a solid reference. A judge that cannot separate them is not usable.
- Give the highest rung whose conditions are all met.
- Score the best theory for mechanism and assumptions, and the whole set for distinct theories.
- If an investigation never reached a stage, mark it **not reached**, not 0. Report those separately, so stopping early is not confused with poor judgement. If it finished and skipped a stage, score 0.
- Applicability is declared in the packet before the run. If an applicable update never arrived or its response was never reached, mark revision **not reached**. Use **not applicable** only when the packet declares revision outside scope.
- An invented number, customer or company intention caps its dimension at 1, however specific it makes the work look.

## Dimensions, each from 0 to 3

| Dimension | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **Problem framing** | Restates the question | Lists obvious options | Separates the objective from the suggested solution | Also finds an option or constraint a good analyst would not want missed, or corrects a false premise |
| **Causal mechanism** | Slogans or SWOT items | Names a benefit | Explains who changes behaviour and why | Traces the full chain, from behaviour change to value this manufacturer captures |
| **Distinct theories** | One theory, or copies | Rewordings of one idea | Rival explanations of the same question | Rivals that imply different products, customers or channels |
| **Assumptions and predictions** | Absent or unfalsifiable | Stated but vague | Observable | Observable, and the theory would be in trouble if they failed |
| **Evidence judgement** | Ignores or misreads it | Cites what agrees | Separates company assertions, observations, studies and analogies | States what each key source cannot establish, including date, place and whether it fits the customer group |
| **Seeking challenge** | Never looks | Looks only where it is safe | Genuinely searches against its favoured theory | Reports fairly what it found, including when it found nothing, and never forces a contradiction |
| **Experiment design** | Generic "do research", or unjustified omission | A proposed study cannot separate theories, or declining it lacks adequate reasons | Separates at least two theories, or gives a sound reason that more research is not worthwhile | Also feasible and decision-relevant, or justifies stopping with uncertainty and evidence limits |
| **Revision** | Ignores applicable new evidence | Notes it without a sound response | Gives a proportionate evidence-linked response to the affected theory, including justified retention | Also traces implications for the recommendation without overreacting |
| **Recommendation** | Confident prose | A position, unsupported | Follows from the evidence, with stated uncertainty | Commits to a next action and says what would reverse it |

## Red flags

Report these whatever the score:

- Hypotheses stated as facts
- Invented numbers, customers or company intentions
- A quote that is exact but misleading, such as one clipped to reverse its meaning
- A marketing claim treated as evidence of demand
- A contradiction manufactured to look balanced
- Reliance on hindsight about Loop or any other known outcome
- A simulated result treated as real demand
- Claims about business results that no study supports

## What a judge receives

Each packet shows the framing, searches, theories, assessments with their stated limits, tests, revisions with before and after text, and the final recommendation, in the order they happened.
