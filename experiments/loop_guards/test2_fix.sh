#!/bin/bash
# Corrected rerun of guards + budget on test set 2 after the quote-menu fix (DECISIONS 2026-11-12 11:35), job 756932,
# code 4573c82. Judged blind with the existing plain and guards + budget arms; packets identical to ones already judged
# (system_test2 and the 10:35 loop-guard campaign) keep those judgments; the rest go to both judges.
set -uo pipefail
cd "$(dirname "$0")/../.."
O=experiments/loop_guards/test2_fix K=$HOME/lexsi-backup/judge_keys R=$HOME/lexsi-backup/judge_results/loop_guards_test2_fix
SSHO="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false"
mkdir -p $O $R
# a failed status read (master down) counts as still running, never as ended
active() { local s; s=$(python3 scripts/cluster/cluster.py status 2>/dev/null) || { echo 1; return; }; echo "$s" | grep -E "^756932 " | grep -c "RUNNING\|PENDING"; }
sleep 600; until [ "$(active)" -eq 0 ]; do sleep 600; done
echo "job ended $(date +%T)"
for try in 1 2 3; do rsync -az -e "$SSHO" CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/runs/eval/lg_test2_guarded_budget_fix.json $O/guarded_budget_fix.json && break; sleep 1200; done
[ -s $O/guarded_budget_fix.json ] || { echo "no report"; exit 1; }
.venv/bin/python -c "import json; s=json.load(open('$O/guarded_budget_fix.json'))['summary']; print('fix', json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))"
cp experiments/loop_guards/test2/plain.json experiments/loop_guards/test2/guarded_budget.json $O/
.venv/bin/python -W ignore -m aemon.evaluation.judging.packets --split heldout2 --report plain=$O/plain.json --report guarded_budget=$O/guarded_budget.json \
  --report guarded_budget_fix=$O/guarded_budget_fix.json --packets $O/packets.jsonl --key $K/loop_guards_test2_fix_key.jsonl
.venv/bin/python - <<'PY'
import json
O = 'experiments/loop_guards/test2_fix'
packets = [l for l in open(f'{O}/packets.jsonl')]
ids = {json.loads(l)['packet_id'] for l in packets}
judged = {}
for j in ('claudecode', 'codexsol'):
    judged[j] = {}
    for f in (f'reports/judge/system_test2/{j}_predictions.jsonl', f'experiments/loop_guards/test2/{j}_predictions.jsonl'):
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
  for round in 1 2 3 4 5 6; do  # Sol: retried across usage limits
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
for c in guarded_budget_fix,plain guarded_budget_fix,guarded_budget; do
  .venv/bin/python -W ignore -m aemon.evaluation.judging.report --key $K/loop_guards_test2_fix_key.jsonl --judge claudecode=$O/claudecode_predictions.jsonl \
    --judge codexsol=$O/codexsol_predictions.jsonl --compare $c --output $O/report_both_${c/,/_vs_}.json > /dev/null
done
cp $K/loop_guards_test2_fix_key.jsonl $O/key.jsonl
echo "judged $(date +%T)"
