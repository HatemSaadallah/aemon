#!/usr/bin/env bash
# The MLflow UI for aemon's results, on this laptop only (127.0.0.1:5000). Data lives outside the repository, in
# ~/lexsi-backup/mlflow (SQLite store and artifacts). Load or refresh it with: .venv/bin/python ops/mlflow/backfill.py
set -euo pipefail
cd "$(dirname "$0")/../.."
H=$HOME/lexsi-backup/mlflow
mkdir -p $H/artifacts
export MLFLOW_DISABLE_AGENT_HINT=1
exec .venv/bin/mlflow server --backend-store-uri sqlite:///$H/mlflow.db --default-artifact-root file://$H/artifacts \
  --host 127.0.0.1 --port ${PORT:-5000} --workers 1
