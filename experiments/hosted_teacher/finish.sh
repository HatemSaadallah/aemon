#!/bin/bash
# After a round ($1 = flash or pro): join the parts, retry failed requests once (infrastructure only), export with the
# provenance, replay and split checks, and review with DeepSeek V4-Pro. Writes reviews/v2_round5/$1_kept_for_review.json.
set -euo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a
export PYTHONPATH=src CHAT_TIMEOUT=300
D=experiments/hosted_teacher; T=$1; P=$([ "$T" = pro ] && echo pro_ || echo "")
MODEL=$([ "$T" = pro ] && echo deepseek-v4-pro || echo deepseek-flash)
cat $D/provenance_${P}other.jsonl $D/provenance_${P}exp*.jsonl > $D/provenance_$T.jsonl
.venv/bin/python - "$D" "$P" "$T" <<'PY'
import json, sys
D, P, T = sys.argv[1:]
asked = [x for part in ['other', 'exp0', 'exp1', 'exp2', 'exp3'] for x in json.load(open(f'{D}/asked_{P}{part}.json'))]
failed = [x['state'] for x in asked if str(x.get('decision', '')).startswith('request failed')]
states = {(s['student_run'], s['turn']): s for f in ['other', 'exp0', 'exp1', 'exp2', 'exp3'] for s in json.load(open(f'{D}/states_{f}.json'))}
retry = [states[(s['student_run'], s['turn'])] for s in failed]
json.dump(asked, open(f'{D}/asked_{T}_first.json', 'w'), ensure_ascii=False)
json.dump(retry, open(f'{D}/states_{T}_retry.json', 'w'), ensure_ascii=False)
print(json.dumps({'answers': len(asked), 'request_failed': len(retry)}))
PY
if [ "$(python3 -c "import json;print(len(json.load(open('$D/states_${T}_retry.json'))))")" -gt 0 ]; then
  HOSTED_MODEL=$MODEL HOSTED_LOG=$D/requests_${P}retry.jsonl HOSTED_BUDGET_USD=1 .venv/bin/python -u -W ignore -m aemon.teacher.hosted_teacher ask \
    --states $D/states_${T}_retry.json --manifest $D/provenance_${T}_retry.jsonl --workers 8 --output $D/asked_${T}_retry.json > $D/run_${T}_retry.log 2>&1 || true
  cat $D/provenance_${T}_retry.jsonl >> $D/provenance_$T.jsonl 2>/dev/null || true
fi
.venv/bin/python - "$D" "$T" <<'PY'
import json, sys, os
D, T = sys.argv[1:]
first = json.load(open(f'{D}/asked_{T}_first.json'))
retry = json.load(open(f'{D}/asked_{T}_retry.json')) if os.path.exists(f'{D}/asked_{T}_retry.json') else []
done = {(x['state']['student_run'], x['state']['turn']): x for x in retry}
merged = [done.get((x['state']['student_run'], x['state']['turn']), x) if str(x.get('decision', '')).startswith('request failed') else x for x in first]
json.dump(merged, open(f'{D}/asked_{T}.json', 'w'), ensure_ascii=False)
PY
mkdir -p reviews/v2_round5
.venv/bin/python -W ignore scripts/oneoff/v2_review_export.py $D/asked_$T.json --verify $D/provenance_$T.jsonl --output reviews/v2_round5/${T}_kept_for_review 2>&1 | tail -3
HOSTED_LOG=$D/requests_review_$T.jsonl HOSTED_BUDGET_USD=2.5 .venv/bin/python -W ignore -m aemon.teacher.hosted_review review reviews/v2_round5/${T}_kept_for_review.json
