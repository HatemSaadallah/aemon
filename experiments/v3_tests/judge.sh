#!/bin/bash
# Version 3 on both test sets, exploratory (DECISIONS 2026-11-11): for each set, wait for its version 3 job, fetch it,
# then judge base, version 1 and version 3 together, blind and shuffled, with the Claude Code judge (claudecode, same
# model, prompt and rubric as the API judge, on the subscription), so every arm is scored by the same judge. Report:
# version 3 minus version 1, and each minus base. The key stays outside the repository while judging.
set -uo pipefail
cd "$(dirname "$0")/../.."
SSHO="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false"
one() {  # set, job, split, v1 folder, v1 prefix
  local SET=$1 JOB=$2 SPLIT=$3 V1=$4 PRE=$5
  local OUT=reports/judge/${SET}_v3 KEY=$HOME/lexsi-backup/judge_keys/${SET}_v3_key.jsonl RES=$HOME/lexsi-backup/judge_results/${SET}_v3/claudecode_${SET}_v3
  mkdir -p $OUT $HOME/lexsi-backup/judge_keys
  until python3 scripts/cluster/cluster.py status 2>/dev/null | grep -q "^$JOB .*\(COMPLETED\|FAILED\|CANCELLED\|TIMEOUT\)"; do sleep 300; done
  rsync -az -e "$SSHO" CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/runs/eval/${PRE}_v3_adapter.json $OUT/ || { echo "$SET: no version 3 report"; return 1; }
  .venv/bin/python -c "import json; s=json.load(open('$OUT/${PRE}_v3_adapter.json'))['summary']; print('$SET v3', json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))"
  .venv/bin/python -W ignore -m aemon.evaluation.judging.packets --split $SPLIT --report base=$V1/${PRE}_base_base.json \
    --report v1=$V1/${PRE}_trained_adapter.json --report v3=$OUT/${PRE}_v3_adapter.json --packets $OUT/packets.jsonl --key $KEY
  .venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend claudecode --packets $OUT/packets.jsonl --output $RES \
    --qualification reports/judge/claudecode_score_qualification.json --workers 4 > $OUT/claudecode_run.log 2>&1 || { echo "$SET judging stopped: $(tail -2 $OUT/claudecode_run.log)"; return 1; }
  for c in v3,v1 v1,base v3,base; do
    .venv/bin/python -m aemon.evaluation.judging.report --key $KEY --judge claudecode=$RES/predictions.jsonl --compare $c --output $OUT/report_claudecode_${c/,/_vs_}.json
  done
  cp $KEY $OUT/key.jsonl; cp $RES/predictions.jsonl $OUT/claudecode_predictions.jsonl
  echo "$SET judged $(date -u +%T)"
}
one final 754420 heldout reports/judge/final final_test
one test2 754421 heldout2 reports/judge/test2 test2
