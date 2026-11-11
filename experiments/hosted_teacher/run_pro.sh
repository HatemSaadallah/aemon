#!/bin/bash
# The V4-Pro round (DECISIONS 2026-11-10 18:30 UTC): the same states and split as run.sh, files suffixed _pro.
set -euo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a
export PYTHONPATH=src CHAT_TIMEOUT=300 HOSTED_MODEL=deepseek-v4-pro
D=experiments/hosted_teacher
run() { HOSTED_LOG=$D/requests_pro_$1.jsonl HOSTED_BUDGET_USD=$2 .venv/bin/python -u -W ignore -m aemon.teacher.hosted_teacher ask \
  --states $D/states_$1.json --manifest $D/provenance_pro_$1.jsonl --workers $3 --output $D/asked_pro_$1.json > $D/run_pro_$1.log 2>&1 || echo "$1 failed: $(tail -1 $D/run_pro_$1.log | cut -c1-300)"; }
run other 4.5 12 &
for i in 0 1 2 3; do run exp$i 0.6 1 & done
wait
echo "all done $(date -u +%T)"
