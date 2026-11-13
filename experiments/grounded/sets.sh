#!/bin/bash
# D (app default + grounded_beliefs + evidence_first) on test set 2 or the final test (DECISIONS 2026-11-12 21:55),
# judged blind by both judges with that set's app-default run; judgments of identical packets are reused.
# Usage: sets.sh JOB SPLIT NAME DEFAULT_REPORT REUSE_DIR    e.g. 759075 heldout final experiments/loop_guards/final/guarded_budget.json experiments/loop_guards/final
set -uo pipefail
cd "$(dirname "$0")/../.."
JOB=$1 SPLIT=$2 NAME=$3 DEF=$4 REUSE=$5
O=experiments/grounded/$NAME K=$HOME/lexsi-backup/judge_keys/evfirst_${NAME}_key.jsonl R=$HOME/lexsi-backup/judge_results/evfirst_$NAME
SSHO="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false"
mkdir -p $O $R
active() { local s; s=$(python3 scripts/cluster/cluster.py status 2>/dev/null) || { echo 1; return; }; echo "$s" | grep -E "^$JOB " | grep -c "RUNNING\|PENDING"; }
sleep 300; until [ "$(active)" -eq 0 ]; do sleep 300; done
echo "job ended $(date +%T)"
for try in 1 2 3; do rsync -az -e "$SSHO" CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/runs/eval/evfirst_$NAME.json $O/D.json && break; sleep 600; done
[ -s $O/D.json ] || { echo "no report"; exit 1; }
.venv/bin/python -c "import json; s=json.load(open('$O/D.json'))['summary']; print('D', json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))"
cp $DEF $O/default.json
.venv/bin/python -W ignore -m aemon.evaluation.judging.packets --split $SPLIT --report default=$O/default.json --report D=$O/D.json --packets $O/packets.jsonl --key $K
.venv/bin/python - $O $REUSE <<'PY'
import json, sys, glob
O, reuse = sys.argv[1], sys.argv[2]
ids = {json.loads(l)['packet_id'] for l in open(f'{O}/packets.jsonl')}
for j in ('claudecode', 'codexsol'):
    seen = {}
    for f in glob.glob(f'{reuse}/{j}_predictions.jsonl'):
        for l in open(f):
            seen.setdefault(json.loads(l)['packet_id'], l)
    open(f'{O}/{j}_reused.jsonl', 'w').writelines(v for k, v in seen.items() if k in ids)
    new = [l for l in open(f'{O}/packets.jsonl') if json.loads(l)['packet_id'] not in seen]
    open(f'{O}/packets_new_{j}.jsonl', 'w').writelines(new)
    print(json.dumps({'judge': j, 'packets': len(ids), 'reused': len(ids) - len(new), 'new': len(new)}))
PY
judge() {  # backend, qualification
  local b=$1 want n; want=$(grep -c . $O/packets_new_$b.jsonl)
  [ "$want" -eq 0 ] && { mkdir -p $R/$b; : > $R/$b/predictions.jsonl; return; }
  for round in 1 2 3 4 5 6; do
    if [ -d $R/$b ]; then local A=$R/${b}_archived_$(date +%s)_r$round; mkdir -p $A; for d in $R/$b/*/; do [ -f $d/result.json ] && ! grep -q '"judgment"' $d/result.json && mv $d $A/; done; [ -f $R/$b/predictions.jsonl ] && mv $R/$b/predictions.jsonl $A/; fi
    .venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend $b --packets $O/packets_new_$b.jsonl --output $R/$b \
      --qualification reports/judge/${b}_score_qualification.json --workers 4 > $O/${b}_run_round$round.log 2>&1
    n=$(.venv/bin/python -c "import json; print(sum(1 for l in open('$R/$b/predictions.jsonl') if json.loads(l).get('judgment')))" 2>/dev/null || echo 0)
    echo "$b round $round: $n of $want judged $(date +%T)"
    [ "$n" -ge "$want" ] && return; sleep 1800
  done
}
judge claudecode & judge codexsol & wait
for j in claudecode codexsol; do cat $O/${j}_reused.jsonl $R/$j/predictions.jsonl > $O/${j}_predictions.jsonl; done
.venv/bin/python -W ignore -m aemon.evaluation.judging.report --key $K --judge claudecode=$O/claudecode_predictions.jsonl \
  --judge codexsol=$O/codexsol_predictions.jsonl --compare D,default --output $O/report_both_D_vs_default.json > /dev/null
cp $K $O/key.jsonl
echo "judged $(date +%T)"
