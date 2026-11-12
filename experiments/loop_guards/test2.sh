#!/bin/bash
# Loop guards on test set 2 (DECISIONS 2026-11-12 05:20), exploratory: plain and guarded dig then reason on the laptop
# server, all 24 cases x 3 attempts, the same seeds; judged together blind by the Claude Code judge (Sol separately
# through experiments/codex_judge/run.py loop_guards_test2). The key stays outside the repository while judging.
set -uo pipefail
cd "$(dirname "$0")/../.."
OUT=experiments/loop_guards/test2 KEY=$HOME/lexsi-backup/judge_keys/loop_guards_test2_key.jsonl RES=$HOME/lexsi-backup/judge_results/loop_guards_test2/claudecode
ROUTE=default=3,brief=0,frame=0,evidence=0
mkdir -p $OUT $RES
until [ -s experiments/loop_guards/arm3.out ]; do sleep 60; done  # the third development arm holds the server until then
arm() {
  [ -s $OUT/$1.json ] && { echo "$1 already done"; return; }
  PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -W ignore -m aemon.agent.run_investigations --url http://127.0.0.1:8091 --prompt compact \
    --split heldout2 --context 12288 --max-tokens 520 --max-turns 45 --attempts 3 --lora-route $ROUTE ${2:+--recovery $2} \
    --model-label "tiny-aya-global Q4 (laptop) route $ROUTE${2:+ recovery $2}" --output $OUT/$1.json > $OUT/$1.log 2>&1 || { echo "$1 failed: $(tail -3 $OUT/$1.log)"; exit 1; }
  .venv/bin/python -c "import json; s=json.load(open('$OUT/$1.json'))['summary']; print('$1', json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))"
}
echo "start $(date +%T)"
arm plain ""
arm guarded no_repeats,quote_menu,resample_repeats
.venv/bin/python -W ignore -m aemon.evaluation.judging.packets --split heldout2 --report plain=$OUT/plain.json --report guarded=$OUT/guarded.json --packets $OUT/packets.jsonl --key $KEY
.venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend claudecode --packets $OUT/packets.jsonl --output $RES \
  --qualification reports/judge/claudecode_score_qualification.json --workers 4 > $OUT/claudecode_run.log 2>&1 || { echo "judging stopped: $(tail -2 $OUT/claudecode_run.log)"; exit 1; }
cp $RES/predictions.jsonl $OUT/claudecode_predictions.jsonl
.venv/bin/python -W ignore -m aemon.evaluation.judging.report --key $KEY --judge claudecode=$OUT/claudecode_predictions.jsonl --compare guarded,plain --output $OUT/report_claudecode_guarded_vs_plain.json
echo "judged $(date +%T)"
