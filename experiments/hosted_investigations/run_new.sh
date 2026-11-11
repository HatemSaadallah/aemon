#!/bin/bash
# Pro investigations of the 70 new DeepSeek-written training cases (DECISIONS 2026-11-10 23:30 UTC), one attempt each,
# 8 parts of 2 at a time. The client stops below a $5 balance.
set -uo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a
export PYTHONPATH=src CHAT_TIMEOUT=300 HOSTED_MODEL=deepseek-v4-pro HOSTED_MIN_BALANCE=5 HOSTED_BUDGET_USD=3
D=experiments/hosted_investigations
for i in 0 1 2 3 4 5 6 7; do
  HOSTED_LOG=$D/requests_new$i.jsonl .venv/bin/python -u -W ignore -m aemon.teacher.hosted_investigations \
    --first-attempt 10 --attempts 1 --workers 2 --cases "$(cat $D/cases_new$i.txt)" \
    --manifest $D/provenance_new$i.jsonl --output $D/new$i.json > $D/new$i.log 2>&1 &
done
wait
echo "new cases done $(date -u +%T)"
