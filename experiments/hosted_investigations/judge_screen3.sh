#!/bin/bash
# Version 3 screen (V2_CORRECTIVE_PLAN section 8): wait for both arms, fetch them, blind Claude judging (judge-v1,
# unchanged), report. The key stays outside the repository. Reopens the SSH master at most once every 20 minutes.
set -uo pipefail
cd "$(dirname "$0")/../.."
OUT=reports/judge/screen3; KEY=$HOME/lexsi-backup/judge_keys/screen3_key.jsonl; mkdir -p $OUT $HOME/lexsi-backup/judge_keys
SSHO="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false"
last_open=0
master() {
  ssh -O check -o ControlPath=$HOME/.ssh/cm-lexsi CLUSTER_ACCOUNT@CLUSTER_HOST >/dev/null 2>&1 && return 0
  [ $(( $(date +%s) - last_open )) -lt 1200 ] && return 1
  last_open=$(date +%s)
  ssh -o BatchMode=yes -o ControlMaster=yes -o ControlPath=~/.ssh/cm-lexsi -o ControlPersist=12h -o ServerAliveInterval=30 -o IPQoS=none \
    -o KexAlgorithms=curve25519-sha256 -o "ProxyCommand=python3 $HOME/Desktop/lexsi-ai-hackathon/scripts/hpc_proxy.py %h %p" -Nf CLUSTER_ACCOUNT@CLUSTER_HOST </dev/null >/dev/null 2>&1
}
while true; do
  if master; then
    s=$(python3 scripts/cluster/cluster.py status 2>/dev/null | grep -E "^(753357|753358|753360) ")
    echo "$(date -u +%H:%M) $(echo "$s" | awk '{print $1":"$3}' | tr '\n' ' ')"
    if echo "$s" | grep -q "^753360 .*\(COMPLETED\|FAILED\|CANCELLED\|TIMEOUT\)" && echo "$s" | grep -q "^753358 .*\(COMPLETED\|FAILED\|CANCELLED\|TIMEOUT\)"; then break; fi
  fi
  sleep 300
done
for arm in v1 v3; do
  rsync -az -e "$SSHO" CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/runs/eval/screen3_${arm}_adapter.json $OUT/ || { echo "screen3_$arm has no report"; exit 1; }
done
.venv/bin/python - <<'PY'
import json
for arm in ('v1', 'v3'):
    s = json.load(open(f'reports/judge/screen3/screen3_{arm}_adapter.json'))['summary']
    print(arm, json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))
PY
.venv/bin/python -W ignore -m aemon.evaluation.judging.packets --split development --report v1=$OUT/screen3_v1_adapter.json --report v3=$OUT/screen3_v3_adapter.json --packets $OUT/packets.jsonl --key $KEY
.venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend claude --packets $OUT/packets.jsonl --output $HOME/lexsi-backup/judge_results/screen3/claude --qualification reports/judge/claude_score_qualification_8000.json --run-cap 5 > $OUT/claude_run.log 2>&1 || { echo "judging stopped: $(tail -2 $OUT/claude_run.log)"; exit 1; }
.venv/bin/python -m aemon.evaluation.judging.report --key $KEY --judge claude=$HOME/lexsi-backup/judge_results/screen3/claude/predictions.jsonl --compare v1,v3 --output $OUT/report_claude_v3_vs_v1.json
echo "screen judged $(date -u +%T)"
