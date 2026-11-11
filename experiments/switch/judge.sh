#!/bin/bash
# Adapter switching, development only (DECISIONS 2026-11-11): submit the fifth arm when the per-user job limit allows,
# wait for all five, fetch them, judge all five arms together blind with the Claude Code judge, and report each
# switching arm against version 1 and version 3. The key stays outside the repository while judging.
set -uo pipefail
cd "$(dirname "$0")/../.."
SSHO="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false"
CASES=hellberg-base,hellberg-new-evidence-looks,hellberg-new-evidence-comfort,hellberg-new-evidence-favours-looks,hellberg-new-evidence-irrelevant,neumann-base,neumann-new-evidence-irrelevant,jotun-base,jotun-new-evidence-irrelevant,tanita-base,tanita-new-evidence-irrelevant,deere-base,deere-new-evidence-irrelevant,acr-base,acr-new-evidence-irrelevant
OUT=reports/judge/switch KEY=$HOME/lexsi-backup/judge_keys/switch_key.jsonl RES=$HOME/lexsi-backup/judge_results/switch/claudecode_switch
ARMS="v1 v3 v3_rescue v1_rescue dig_then_reason"
mkdir -p $OUT $HOME/lexsi-backup/judge_keys $HOME/lexsi-backup/judge_results/switch
echo "all arms ended $(date +%T)"
REPORTS=()
for a in $ARMS; do
  rsync -az -e "$SSHO" CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/runs/eval/switch_$a.json $OUT/ || { echo "no report for $a"; continue; }
  .venv/bin/python -c "import json; s=json.load(open('$OUT/switch_$a.json'))['summary']; print('$a', json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))"
  REPORTS+=(--report $a=$OUT/switch_$a.json)
done
.venv/bin/python -W ignore -m aemon.evaluation.judging.packets --split development "${REPORTS[@]}" --packets $OUT/packets.jsonl --key $KEY
.venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend claudecode --packets $OUT/packets.jsonl --output $RES \
  --qualification reports/judge/claudecode_score_qualification.json --workers 4 > $OUT/claudecode_run.log 2>&1 || { echo "judging stopped: $(tail -2 $OUT/claudecode_run.log)"; exit 1; }
for c in v3_rescue,v1 v3_rescue,v3 v1_rescue,v1 v1_rescue,v3 dig_then_reason,v1 dig_then_reason,v3 v3,v1; do
  .venv/bin/python -W ignore -m aemon.evaluation.judging.report --key $KEY --judge claudecode=$RES/predictions.jsonl --compare $c --output $OUT/report_${c/,/_vs_}.json
done
cp $KEY $OUT/key.jsonl; cp $RES/predictions.jsonl $OUT/claudecode_predictions.jsonl
echo "judged $(date +%T)"
