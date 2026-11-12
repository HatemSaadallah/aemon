#!/bin/bash
# Third arm (DECISIONS 2026-11-12 05:10): the loop guards plus the budget guard, same cases, seeds and server.
set -uo pipefail
cd "$(dirname "$0")/../.."
OUT=experiments/loop_guards
CASES=$(grep -o 'CASES=[^ ]*' $OUT/screen.sh | head -1 | cut -d= -f2)
ROUTE=default=3,brief=0,frame=0,evidence=0 F=no_repeats,quote_menu,resample_repeats,budget
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -W ignore -m aemon.agent.run_investigations --url http://127.0.0.1:8091 --prompt compact \
  --cases $CASES --split development --context 12288 --max-tokens 520 --max-turns 45 --attempts 3 --lora-route $ROUTE --recovery $F \
  --model-label "tiny-aya-global Q4 (laptop) route $ROUTE recovery $F" --output $OUT/guarded_budget.json > $OUT/guarded_budget.log 2>&1 || { echo "failed: $(tail -3 $OUT/guarded_budget.log)"; exit 1; }
.venv/bin/python -c "import json; s=json.load(open('$OUT/guarded_budget.json'))['summary']; print('guarded_budget', json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))"
