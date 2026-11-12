#!/bin/bash
# Loop guards screen (DECISIONS 2026-11-12 02:50), development only, on the laptop's model server (4-bit base, the app's
# runtime; v1 is adapter 0 and v3 adapter 3 there). Both arms run on the same server, cases and seeds; only --recovery
# differs. Then both are judged together blind by the Claude Code judge. The key stays outside the repository.
set -uo pipefail
cd "$(dirname "$0")/../.."
OUT=experiments/loop_guards KEY=$HOME/lexsi-backup/judge_keys/loop_guards_key.jsonl RES=$HOME/lexsi-backup/judge_results/loop_guards/claudecode
CASES=hellberg-base,hellberg-new-evidence-looks,hellberg-new-evidence-comfort,hellberg-new-evidence-favours-looks,hellberg-new-evidence-irrelevant,neumann-base,neumann-new-evidence-irrelevant,jotun-base,jotun-new-evidence-irrelevant,tanita-base,tanita-new-evidence-irrelevant,deere-base,deere-new-evidence-irrelevant,acr-base,acr-new-evidence-irrelevant
ROUTE=default=3,brief=0,frame=0,evidence=0
mkdir -p $(dirname $KEY) $RES
arm() {  # name, recovery features
  [ -s $OUT/$1.json ] && { echo "$1 already done"; return; }
  PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -W ignore -m aemon.agent.run_investigations --url http://127.0.0.1:8091 --prompt compact \
    --cases $CASES --split development --context 12288 --max-tokens 520 --max-turns 45 --attempts 3 --lora-route $ROUTE ${2:+--recovery $2} \
    --model-label "tiny-aya-global Q4 (laptop) route $ROUTE${2:+ recovery $2}" --output $OUT/$1.json > $OUT/$1.log 2>&1 || { echo "$1 failed: $(tail -3 $OUT/$1.log)"; exit 1; }
  .venv/bin/python -c "import json; s=json.load(open('$OUT/$1.json'))['summary']; print('$1', json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))"
}
echo "start $(date +%T)"
arm plain ""
arm guarded no_repeats,quote_menu,resample_repeats
.venv/bin/python -W ignore -m aemon.evaluation.judging.packets --split development --report plain=$OUT/plain.json --report guarded=$OUT/guarded.json --packets $OUT/packets.jsonl --key $KEY
.venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend claudecode --packets $OUT/packets.jsonl --output $RES \
  --qualification reports/judge/claudecode_score_qualification.json --workers 4 > $OUT/claudecode_run.log 2>&1 || { echo "judging stopped: $(tail -2 $OUT/claudecode_run.log)"; exit 1; }
.venv/bin/python -W ignore -m aemon.evaluation.judging.report --key $KEY --judge claudecode=$RES/predictions.jsonl --compare guarded,plain --output $OUT/report_guarded_vs_plain.json
echo "judged $(date +%T)"
