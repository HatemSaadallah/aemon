#!/bin/bash
# Retry rejected judgments straight away (no wait: the failures are the instrument's validity check, not rate
# limits), up to 3 rounds per judge and set, all in parallel; then assemble predictions and the three reports.
set -uo pipefail
cd "$(dirname "$0")/../.."
one() {  # NAME judge
  local N=$1 b=$2 O=experiments/haiku/$1 R=$HOME/lexsi-backup/judge_results/haiku_$1 want n
  want=$(grep -c . $O/packets_new_$b.jsonl)
  for round in 1 2 3; do
    n=$(cat $R/$b/*/result.json 2>/dev/null | grep -c '"judgment"')
    [ "$n" -ge "$want" ] && break
    local A=$R/${b}_archived_$(date +%s)_f$round; mkdir -p $A
    for d in $R/$b/*/; do [ -f $d/result.json ] && ! grep -q '"judgment"' $d/result.json && mv $d $A/; done
    [ -f $R/$b/predictions.jsonl ] && mv $R/$b/predictions.jsonl $A/
    .venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend $b --packets $O/packets_new_$b.jsonl \
      --output $R/$b --qualification reports/judge/${b}_score_qualification.json --workers 4 > $O/${b}_finish_round$round.log 2>&1
    n=$(.venv/bin/python -c "import json; print(sum(1 for l in open('$R/$b/predictions.jsonl') if json.loads(l).get('judgment')))" 2>/dev/null || echo 0)
    echo "$N $b finish round $round: $n of $want judged $(date +%T)"
  done
}
one final claudecode & one final codexsol & one test2 claudecode & one test2 codexsol & wait
for N in final test2; do
  O=experiments/haiku/$N R=$HOME/lexsi-backup/judge_results/haiku_$N K=$HOME/lexsi-backup/judge_keys/haiku_${N}_key.jsonl
  for j in claudecode codexsol; do cat $O/${j}_reused.jsonl $R/$j/predictions.jsonl > $O/${j}_predictions.jsonl; done
  for c in final_system,haiku v1,haiku haiku,base; do
    .venv/bin/python -W ignore -m aemon.evaluation.judging.report --key $K --judge claudecode=$O/claudecode_predictions.jsonl \
      --judge codexsol=$O/codexsol_predictions.jsonl --compare $c --output $O/report_both_${c/,/_vs_}.json > /dev/null
  done
  cp $K $O/key.jsonl
done
echo "assembled $(date +%T)"
