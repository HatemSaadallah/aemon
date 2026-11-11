#!/bin/bash
# Whole investigations by DeepSeek V4-Pro (DECISIONS 2026-11-10 22:55 UTC): the 111 training cases, attempt 12 (the leftover credit, until the $5 floor),
# in 8 parts of 2 investigations at a time (16 at once). The client stops every part below a $5 balance.
set -uo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a
export PYTHONPATH=src CHAT_TIMEOUT=300 HOSTED_MODEL=deepseek-v4-pro HOSTED_MIN_BALANCE=5 HOSTED_BUDGET_USD=4
D=experiments/hosted_investigations
for i in 0 1 2 3 4 5 6 7; do
  HOSTED_LOG=$D/requests_pass3_part$i.jsonl .venv/bin/python -u -W ignore -m aemon.teacher.hosted_investigations \
    --cases "$(cat $D/cases_part$i.txt)" --first-attempt 12 --attempts 1 --workers 2 \
    --manifest $D/provenance_pass3_part$i.jsonl --output $D/pass3_part$i.json > $D/pass3_part$i.log 2>&1 &
done
wait
echo "all parts done $(date -u +%T)"
