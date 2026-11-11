# Recorded investigations

Six runs from the frozen final test (four companies the model never saw), readable without a GPU. Each page shows every tool call, what the environment accepted or refused, and the recommendation.

| Run | Model | Ended | Judge score |
|---|---|---|---|
| [Electrolux Professional: a finished investigation](trained_epro-base_1.md) | Aemon | finished | 1.62 |
| [RATIONAL: a finished investigation](trained_rational-base_0.md) | Aemon | finished | 1.56 |
| [Simonelli: a finished investigation](trained_simo-base_1.md) | Aemon | finished | 1.44 |
| [Aquaporin: finished, well scored, and it misses the insolvency (the main limitation)](trained_aqp-base_1.md) | Aemon | finished | 1.88 |
| [Electrolux Professional: a run that stops after four refusals in a row](trained_epro-base_0.md) | Aemon | repeated errors | 1.19 |
| [Electrolux Professional: the untrained base model, for contrast](base_epro-base_1.md) | base | repeated errors | 0.50 |

Regenerate with `python scripts/release/replay_markdown.py`. All 96 final-test runs are in `reports/judge/final/final_test_*.json`.
