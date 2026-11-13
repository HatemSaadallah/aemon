#!/bin/bash
# Grounded beliefs, development screen (DECISIONS 2026-11-12 18:15): arm A (app default) and arm B (+ grounded_beliefs)
# as two jobs side by side; judged blind by both judges, reusing judgments of identical packets from the loop-guard
# development campaign; report B minus A with the registered rule. Usage: screen.sh JOB_A JOB_B
set -uo pipefail
cd "$(dirname "$0")/../.."
JA=${1:?} JB=${2:?}
O=experiments/grounded K=$HOME/lexsi-backup/judge_keys/grounded_screen_key.jsonl R=$HOME/lexsi-backup/judge_results/grounded_screen
SSHO="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false"
mkdir -p $O $R
active() { local s; s=$(python3 scripts/cluster/cluster.py status 2>/dev/null) || { echo 1; return; }; echo "$s" | grep -E "^($JA|$JB) " | grep -c "RUNNING\|PENDING"; }
sleep 600; until [ "$(active)" -eq 0 ]; do sleep 600; done
echo "jobs ended $(date +%T)"
for a in A B; do
  for try in 1 2 3; do rsync -az -e "$SSHO" CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/runs/eval/grounded_$a.json $O/$a.json && break; sleep 1200; done
  [ -s $O/$a.json ] || { echo "no report for $a"; exit 1; }
  .venv/bin/python -c "import json; s=json.load(open('$O/$a.json'))['summary']; print('$a', json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))"
done
.venv/bin/python -W ignore -m aemon.evaluation.judging.packets --split development --report A=$O/A.json --report B=$O/B.json --packets $O/packets.jsonl --key $K
.venv/bin/python - <<'PY'
import json
O = 'experiments/grounded'
packets = open(f'{O}/packets.jsonl').readlines()
ids = {json.loads(l)['packet_id'] for l in packets}
judged = {}
for j in ('claudecode', 'codexsol'):
    judged[j] = {}
    for f in (f'experiments/loop_guards/arm3/{j}_predictions_all.jsonl', f'experiments/loop_guards/{j}_predictions.jsonl'):
        for l in open(f):
            judged[j].setdefault(json.loads(l)['packet_id'], l)
    open(f'{O}/{j}_reused.jsonl', 'w').writelines(v for k, v in judged[j].items() if k in ids)
new = [l for l in packets if any(json.loads(l)['packet_id'] not in judged[j] for j in judged)]
open(f'{O}/packets_new.jsonl', 'w').writelines(new)
print(json.dumps({'packets': len(packets), 'new': len(new)}))
PY
if [ -s $O/packets_new.jsonl ]; then
  .venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend claudecode --packets $O/packets_new.jsonl --output $R/claudecode \
    --qualification reports/judge/claudecode_score_qualification.json --workers 4 > $O/claudecode_run.log 2>&1 || echo "claude judging stopped: $(tail -2 $O/claudecode_run.log)"
  want=$(grep -c . $O/packets_new.jsonl)
  for round in 1 2 3 4 5 6; do
    # failed results and the aggregate that lists them are moved aside, or the next round skips them (as codex_judge/run.py)
    if [ -d $R/codexsol ]; then A=$R/codexsol_archived_r$round; mkdir -p $A; for d in $R/codexsol/*/; do [ -f $d/result.json ] && ! grep -q '"judgment"' $d/result.json && mv $d $A/; done; [ -f $R/codexsol/predictions.jsonl ] && mv $R/codexsol/predictions.jsonl $A/; fi
    .venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend codexsol --packets $O/packets_new.jsonl --output $R/codexsol \
      --qualification reports/judge/codexsol_score_qualification.json --workers 4 > $O/codexsol_run_round$round.log 2>&1
    n=$(.venv/bin/python -c "import json; print(sum(1 for l in open('$R/codexsol/predictions.jsonl') if json.loads(l).get('judgment')))" 2>/dev/null || echo 0)
    echo "sol round $round: $n of $want judged"
    [ "$n" -ge "$want" ] && break; sleep 3600
  done
else
  mkdir -p $R/claudecode $R/codexsol; : > $R/claudecode/predictions.jsonl; : > $R/codexsol/predictions.jsonl
fi
for j in claudecode codexsol; do cat $O/${j}_reused.jsonl $R/$j/predictions.jsonl > $O/${j}_predictions.jsonl; done
.venv/bin/python -W ignore -m aemon.evaluation.judging.report --key $K --judge claudecode=$O/claudecode_predictions.jsonl \
  --judge codexsol=$O/codexsol_predictions.jsonl --compare B,A --output $O/report_both_B_vs_A.json > /dev/null
cp $K $O/key.jsonl
echo "judged $(date +%T)"
