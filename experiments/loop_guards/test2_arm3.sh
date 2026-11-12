#!/bin/bash
# Test set 2, third arm (DECISIONS 2026-11-12 06:40): guards + budget on the same laptop server and seeds, after the
# guarded arm; then both judges on every packet, packets already judged reused (identical runs share a packet).
set -uo pipefail
cd "$(dirname "$0")/../.."
O=experiments/loop_guards/test2 R=$HOME/lexsi-backup/judge_results/loop_guards_test2 K=$HOME/lexsi-backup/judge_keys
ROUTE=default=3,brief=0,frame=0,evidence=0 F=no_repeats,quote_menu,resample_repeats,budget
until [ -s $O/guarded.json ]; do sleep 120; done
echo "arm3 start $(date +%T)"
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -W ignore -m aemon.agent.run_investigations --url http://127.0.0.1:8091 --prompt compact \
  --split heldout2 --context 12288 --max-tokens 520 --max-turns 45 --attempts 3 --lora-route $ROUTE --recovery $F \
  --model-label "tiny-aya-global Q4 (laptop) route $ROUTE recovery $F" --output $O/guarded_budget.json > $O/guarded_budget.log 2>&1 || { echo "arm3 failed: $(tail -3 $O/guarded_budget.log)"; exit 1; }
.venv/bin/python -c "import json; s=json.load(open('$O/guarded_budget.json'))['summary']; print('guarded_budget', json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))"
until [ -s $O/packets.jsonl ]; do sleep 60; done
.venv/bin/python -W ignore -m aemon.evaluation.judging.packets --split heldout2 --report guarded_budget=$O/guarded_budget.json --packets $O/packets_arm3.jsonl --key $K/loop_guards_test2_arm3_key.jsonl
.venv/bin/python - <<'PY'
import json
O = 'experiments/loop_guards/test2'
old = {json.loads(l)['packet_id'] for l in open(f'{O}/packets.jsonl')}
new = [l for l in open(f'{O}/packets_arm3.jsonl') if json.loads(l)['packet_id'] not in old]
open(f'{O}/packets_arm3_new.jsonl', 'w').writelines(new)
print('new packets', len(new))
PY
cat $K/loop_guards_test2_key.jsonl $K/loop_guards_test2_arm3_key.jsonl > $K/loop_guards_test2_all_key.jsonl
.venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend claudecode --packets $O/packets_arm3_new.jsonl --output $R/claudecode_arm3 \
  --qualification reports/judge/claudecode_score_qualification.json --workers 4 > $O/claudecode_arm3_run.log 2>&1 || echo "claude arm3 judging stopped"
.venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend codexsol --packets $O/packets_arm3_new.jsonl --output $R/codexsol_arm3 \
  --qualification reports/judge/codexsol_score_qualification.json --workers 4 > $O/codexsol_arm3_run.log 2>&1 || echo "sol arm3 judging stopped"
echo "arm3 judged $(date +%T)"
