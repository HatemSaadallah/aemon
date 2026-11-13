#!/bin/bash
# Resume the gpt-6-sol judging of a screen whose Claude Code judging is done, then merge and report.
# Usage: sol_resume.sh OUT_DIR KEY RESULTS_DIR COMPARE...   e.g. experiments/grounded KEY RES B,A
set -uo pipefail
cd "$(dirname "$0")/../.."
O=$1 K=$2 R=$3; shift 3
want=$(grep -c . $O/packets_new.jsonl)
for round in 1 2 3 4 5 6; do
  if [ -d $R/codexsol ]; then A=$R/codexsol_archived_$(date +%s)_r$round; mkdir -p $A; for d in $R/codexsol/*/; do [ -f $d/result.json ] && ! grep -q '"judgment"' $d/result.json && mv $d $A/; done; [ -f $R/codexsol/predictions.jsonl ] && mv $R/codexsol/predictions.jsonl $A/; fi
  .venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend codexsol --packets $O/packets_new.jsonl --output $R/codexsol \
    --qualification reports/judge/codexsol_score_qualification.json --workers 4 > $O/codexsol_resume_round$round.log 2>&1
  n=$(.venv/bin/python -c "import json; print(sum(1 for l in open('$R/codexsol/predictions.jsonl') if json.loads(l).get('judgment')))" 2>/dev/null || echo 0)
  echo "sol resume round $round: $n of $want judged $(date +%T)"
  [ "$n" -ge "$want" ] && break; sleep 3600
done
for j in claudecode codexsol; do cat $O/${j}_reused.jsonl $R/$j/predictions.jsonl > $O/${j}_predictions.jsonl; done
for c in "$@"; do .venv/bin/python -W ignore -m aemon.evaluation.judging.report --key $K --judge claudecode=$O/claudecode_predictions.jsonl \
  --judge codexsol=$O/codexsol_predictions.jsonl --compare $c --output $O/report_both_${c/,/_vs_}.json > /dev/null; done
cp $K $O/key.jsonl
echo "judged $(date +%T)"
