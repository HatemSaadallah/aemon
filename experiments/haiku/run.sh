#!/bin/bash
# Claude Haiku 5.5 on both test sets (DECISIONS 2026-11-13, registered before the run): prompt staged, effort medium.
set -uo pipefail
cd "$(dirname "$0")/../.."
O=experiments/haiku
CASES_FINAL=$(.venv/bin/python -c "import json; print(json.load(open('reports/judge/final/final_test_base_base.json'))['arguments']['cases'])")
CASES_T2=$(.venv/bin/python -c "import json; print(json.load(open('reports/judge/test2/test2_base_base.json'))['arguments']['cases'])")
run() {  # split, cases, name
  .venv/bin/python -m aemon.agent.run_investigations --backend claude --claude-model claude-haiku-5-5 --prompt staged \
    --split $1 --cases "$2" --attempts 3 --workers 4 --run-cap-usd 5 --output $O/$3.json > $O/$3.log 2>&1
  echo "$3 rc=$? $(date +%T)"
}
run heldout "$CASES_FINAL" final & run heldout2 "$CASES_T2" test2 & wait
