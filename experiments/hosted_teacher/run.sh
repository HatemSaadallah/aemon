#!/bin/bash
# The DeepSeek corrective round (DECISIONS 2026-11-10 19:30 UTC): the non-experiment families with 8 requests at once,
# and the experiment family (one state at a time in its own code) split over 4 processes. Separate manifests, joined after.
set -euo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a
export PYTHONPATH=src CHAT_TIMEOUT=240
D=experiments/hosted_teacher
run() { HOSTED_LOG=$D/requests_$1.jsonl HOSTED_BUDGET_USD=$2 .venv/bin/python -u -W ignore -m aemon.teacher.hosted_teacher ask \
  --states $D/states_$1.json --manifest $D/provenance_$1.jsonl --workers $3 --output $D/asked_$1.json > $D/run_$1.log 2>&1; }
run other 2.0 8 &
for i in 0 1 2 3; do run exp$i 0.8 1 & done
wait
echo "all done $(date -u +%T)"
