#!/bin/bash
# Loop guards on test set 2 (DECISIONS 2026-11-12 05:20 and 06:40), exploratory, on the cluster (bf16, the evaluated
# runtime). The plain arm is the existing dig-then-reason run of test set 2 (reports/judge/system_test2/system_test2_dig.json,
# same route, settings and seeds); the two guard arms are jobs 756273 and 756274. The laptop attempt was stopped when the
# laptop ran out of memory (laptop_aborted_*). Packets identical to ones already judged keep those judgments.
set -uo pipefail
cd "$(dirname "$0")/../.."
O=experiments/loop_guards/test2 K=$HOME/lexsi-backup/judge_keys R=$HOME/lexsi-backup/judge_results/loop_guards_test2
SSHO="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false"
mkdir -p $O $R
active() { python3 scripts/cluster/cluster.py status 2>/dev/null | grep -E "^75627[34] " | grep -c "RUNNING\|PENDING"; }
sleep 600; until [ "$(active)" -eq 0 ]; do sleep 600; done
echo "jobs ended $(date +%T)"
for a in guarded guarded_budget; do
  rsync -az -e "$SSHO" CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/runs/eval/lg_test2_$a.json $O/$a.json || { echo "no report for $a"; exit 1; }
  .venv/bin/python -c "import json; s=json.load(open('$O/$a.json'))['summary']; print('$a', json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))"
done
cp reports/judge/system_test2/system_test2_dig.json $O/plain.json
.venv/bin/python -W ignore -m aemon.evaluation.judging.packets --split heldout2 --report plain=$O/plain.json --report guarded=$O/guarded.json --report guarded_budget=$O/guarded_budget.json \
  --packets $O/packets.jsonl --key $K/loop_guards_test2_key.jsonl
.venv/bin/python - <<'PY'
import json
O = 'experiments/loop_guards/test2'
judged = {}
for j in ('claudecode', 'codexsol'):
    judged[j] = {json.loads(l)['packet_id']: l for l in open(f'reports/judge/system_test2/{j}_predictions.jsonl')}
packets = [l for l in open(f'{O}/packets.jsonl')]
new = [l for l in packets if json.loads(l)['packet_id'] not in judged['claudecode'] or json.loads(l)['packet_id'] not in judged['codexsol']]
open(f'{O}/packets_new.jsonl', 'w').writelines(new)
for j in judged:  # judgments already made for identical packets
    ids = {json.loads(l)['packet_id'] for l in packets}
    open(f'{O}/{j}_reused.jsonl', 'w').writelines(v for k, v in judged[j].items() if k in ids)
print(json.dumps({'packets': len(packets), 'new': len(new)}))
PY
.venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend claudecode --packets $O/packets_new.jsonl --output $R/claudecode \
  --qualification reports/judge/claudecode_score_qualification.json --workers 4 > $O/claudecode_run.log 2>&1 || echo "claude judging stopped: $(tail -2 $O/claudecode_run.log)"
for round in 1 2 3 4 5 6; do  # Sol: retried across usage limits
  .venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend codexsol --packets $O/packets_new.jsonl --output $R/codexsol \
    --qualification reports/judge/codexsol_score_qualification.json --workers 4 > $O/codexsol_run_round$round.log 2>&1
  n=$(grep -c . $R/codexsol/predictions.jsonl 2>/dev/null || echo 0); bad=$(grep -c '"judgment": null\|infra' $R/codexsol/predictions.jsonl 2>/dev/null || echo 0)
  echo "sol round $round: $n predictions, $bad without a judgment"
  [ "$bad" -eq 0 ] && break; sleep 3600
done
for j in claudecode codexsol; do cat $O/${j}_reused.jsonl $R/$j/predictions.jsonl > $O/${j}_predictions.jsonl; done
for c in guarded,plain guarded_budget,plain guarded_budget,guarded; do
  .venv/bin/python -W ignore -m aemon.evaluation.judging.report --key $K/loop_guards_test2_key.jsonl --judge claudecode=$O/claudecode_predictions.jsonl \
    --judge codexsol=$O/codexsol_predictions.jsonl --compare $c --output $O/report_both_${c/,/_vs_}.json > /dev/null
done
echo "judged $(date +%T)"
