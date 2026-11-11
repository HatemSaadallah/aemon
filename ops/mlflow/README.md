# MLflow tracking

Every training run, evaluation run and judged comparison, browsable at http://127.0.0.1:5000.

```bash
uv pip install --python .venv/bin/python -r ops/mlflow/requirements.txt   # once
./ops/mlflow/run.sh                                                         # the UI, this laptop only
.venv/bin/python ops/mlflow/backfill.py                                     # load or refresh; already-logged files are skipped
```

The cluster has no route to this laptop, so jobs don't log directly. Their outputs are fetched as before, and the
backfill reads them: `trainer_state.json` and `adapter_config.json` for training (copied to
`~/lexsi-backup/cluster/training_states/`), runner reports and judge reports under `reports/`. The store (SQLite and
artifacts) lives in `~/lexsi-backup/mlflow`, outside the repository.

| Experiment | One run per | Metrics |
|---|---|---|
| aemon-training | adapter training | loss, eval_loss, grad_norm, mean_token_accuracy, learning_rate per step |
| aemon-evaluation | runner report | finished, refusals, stop reasons, calls; each judge's mean score where judged |
| aemon-comparisons | judge report (A minus B) | each arm's mean, the paired difference and its 95% interval, per judge and mean of judges |

Models (Models tab of aemon-evaluation): aemon-v1, aemon-v2, aemon-v3, aemon-third and tiny-aya-global-base, each linked to its training run and carrying the metrics of the evaluations it ran. Registry `aemon-adapter`: versions 1-3 are v1-v3, alias `submitted` = 1, `exploratory` = 3. Weights stay on the cluster and Hugging Face; the models record their sha256.
