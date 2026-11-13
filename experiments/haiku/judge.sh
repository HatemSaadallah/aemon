#!/bin/bash
# Judge the Haiku baseline blind with the base model, version 1 and the final system on one test set (DECISIONS
# 2026-11-13). Judgments of packets already judged by the same two judges are reused; only new packets are judged.
# Usage: judge.sh NAME SPLIT     e.g. judge.sh final heldout   or   judge.sh test2 heldout2
set -uo pipefail
cd "$(dirname "$0")/../.."
NAME=$1 SPLIT=$2
O=experiments/haiku/$NAME K=$HOME/lexsi-backup/judge_keys/haiku_${NAME}_key.jsonl R=$HOME/lexsi-backup/judge_results/haiku_$NAME
if [ "$NAME" = final ]; then SYS=reports/judge/system_final; G=experiments/grounded/final; BASE=reports/judge/final/final_test_base_base.json; V1=reports/judge/final/final_test_trained_adapter.json
else SYS=reports/judge/system_test2; G=experiments/grounded/test2; BASE=reports/judge/test2/test2_base_base.json; V1=reports/judge/test2/test2_trained_adapter.json; fi
mkdir -p $O $R
.venv/bin/python -W ignore -m aemon.evaluation.judging.packets --split $SPLIT --report base=$BASE --report v1=$V1 \
  --report final_system=$G/D.json --report haiku=experiments/haiku/${NAME}_merged.json --packets $O/packets.jsonl --key $K
.venv/bin/python - $O $SYS $G <<'PY'
import json, sys
O, *reuse = sys.argv[1:]
ids = {json.loads(l)['packet_id'] for l in open(f'{O}/packets.jsonl')}
for j in ('claudecode', 'codexsol'):
    seen = {}
    for d in reuse:
        for l in open(f'{d}/{j}_predictions.jsonl'):
            p = json.loads(l)
            if p.get('judgment'):
                seen.setdefault(p['packet_id'], l)
    open(f'{O}/{j}_reused.jsonl', 'w').writelines(v for k, v in seen.items() if k in ids)
    new = [l for l in open(f'{O}/packets.jsonl') if json.loads(l)['packet_id'] not in seen]
    open(f'{O}/packets_new_{j}.jsonl', 'w').writelines(new)
    print(json.dumps({'judge': j, 'packets': len(ids), 'reused': len(ids) - len(new), 'new': len(new)}))
PY
judge() {  # backend
  local b=$1 want n; want=$(grep -c . $O/packets_new_$b.jsonl)
  [ "$want" -eq 0 ] && { mkdir -p $R/$b; : > $R/$b/predictions.jsonl; return; }
  for round in 1 2 3 4 5 6; do
    if [ -d $R/$b ]; then local A=$R/${b}_archived_$(date +%s)_r$round; mkdir -p $A; for d in $R/$b/*/; do [ -f $d/result.json ] && ! grep -q '"judgment"' $d/result.json && mv $d $A/; done; [ -f $R/$b/predictions.jsonl ] && mv $R/$b/predictions.jsonl $A/; fi
    .venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend $b --packets $O/packets_new_$b.jsonl --output $R/$b \
      --qualification reports/judge/${b}_score_qualification.json --workers 4 > $O/${b}_run_round$round.log 2>&1
    n=$(.venv/bin/python -c "import json; print(sum(1 for l in open('$R/$b/predictions.jsonl') if json.loads(l).get('judgment')))" 2>/dev/null || echo 0)
    echo "$NAME $b round $round: $n of $want judged $(date +%T)"
    [ "$n" -ge "$want" ] && return; sleep 900
  done
}
judge claudecode & judge codexsol & wait
for j in claudecode codexsol; do cat $O/${j}_reused.jsonl $R/$j/predictions.jsonl > $O/${j}_predictions.jsonl; done
for c in final_system,haiku v1,haiku haiku,base; do
  .venv/bin/python -W ignore -m aemon.evaluation.judging.report --key $K --judge claudecode=$O/claudecode_predictions.jsonl \
    --judge codexsol=$O/codexsol_predictions.jsonl --compare $c --output $O/report_both_${c/,/_vs_}.json > /dev/null
done
cp $K $O/key.jsonl
echo "$NAME judged $(date +%T)"
