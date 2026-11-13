# Recorded investigations

Seven runs on the final test's cases (four companies the model never saw): one by the final system, six from the frozen test itself, readable without a GPU. Each page shows every tool call, what the environment accepted or refused, and the recommendation.

| Run | Model | Ended | Judge score |
|---|---|---|---|
| [RATIONAL: the final system, fifteen sources weighed, and a test before any commitment](system_rational-new-evidence-irrelevant_2.md) | aemon, final system | finished | 1.83 |
| [Electrolux Professional: a finished investigation](trained_epro-base_1.md) | aemon, version 1 | finished | 1.62 |
| [RATIONAL: a finished investigation](trained_rational-base_0.md) | aemon, version 1 | finished | 1.56 |
| [Simonelli: a finished investigation](trained_simo-base_1.md) | aemon, version 1 | finished | 1.44 |
| [Aquaporin: finished, well scored, and it misses the insolvency (the main limitation)](trained_aqp-base_1.md) | aemon, version 1 | finished | 1.88 |
| [Electrolux Professional: a run that stops after four refusals in a row](trained_epro-base_0.md) | aemon, version 1 | repeated errors | 1.19 |
| [Electrolux Professional: the untrained base model, for contrast](base_epro-base_1.md) | base | repeated errors | 0.50 |

## Every run

Every run of both frozen tests, base and fine-tuned side by side, with filters (fine-tuned finished and base did not, fine-tuned scored lower, both stopped):

- [Frozen final test (four unseen companies)](final/README.md): 96 runs; finished 4 base, 28 fine-tuned; mean of judges 0.65 base, 1.48 fine-tuned.
- [Second frozen test (twelve more unseen companies)](test2/README.md): 144 runs; finished 2 base, 32 fine-tuned; mean of judges 0.57 base, 1.09 fine-tuned.

Regenerate with `python scripts/release/replay_markdown.py`. The runner reports are `reports/judge/final/final_test_*.json` and `reports/judge/test2/test2_*.json`.
