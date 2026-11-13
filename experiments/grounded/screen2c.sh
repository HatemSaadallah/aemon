#!/bin/bash
# Evidence first screen: the gpt-6-sol half and the reports, started as soon as Claude Code had judged C and D.
set -uo pipefail
cd "$(dirname "$0")/../.."
O=experiments/grounded/screen2 K=$HOME/lexsi-backup/judge_keys/grounded_screen2_key.jsonl R=$HOME/lexsi-backup/judge_results/grounded_screen2
R1=$HOME/lexsi-backup/judge_results/grounded_screen
SSHO="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false"
mkdir -p $O $R
# judged earlier: A and B by both judges in the 18:15 screen (gpt-6-sol may still be running there)
reuse() {  # judge, files...
  .venv/bin/python - "$@" <<'PY'
import json, sys
j, files = sys.argv[1], sys.argv[2:]
O = 'experiments/grounded/screen2'
ids = {json.loads(l)['packet_id'] for l in open(f'{O}/packets.jsonl')}
seen = {}
for f in files:
    try:
        for l in open(f):
            p = json.loads(l)
            if p.get('judgment') or p.get('response'): seen.setdefault(p['packet_id'], l)
    except FileNotFoundError: pass
open(f'{O}/{j}_reused.jsonl', 'w').writelines(v for k, v in seen.items() if k in ids)
new = [l for l in open(f'{O}/packets.jsonl') if json.loads(l)['packet_id'] not in seen]
open(f'{O}/packets_new_{j}.jsonl', 'w').writelines(new)
print(json.dumps({'judge': j, 'packets': len(ids), 'reused': len(ids) - len(new), 'new': len(new)}))
PY
}
reuse codexsol experiments/grounded/codexsol_predictions.jsonl
want=$(grep -c . $O/packets_new_codexsol.jsonl)
for round in 1 2 3 4 5 6; do
  if [ -d $R/codexsol ]; then A=$R/codexsol_archived_$(date +%s)_r$round; mkdir -p $A; for d in $R/codexsol/*/; do [ -f $d/result.json ] && ! grep -q '"judgment"' $d/result.json && mv $d $A/; done; [ -f $R/codexsol/predictions.jsonl ] && mv $R/codexsol/predictions.jsonl $A/; fi
  .venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend codexsol --packets $O/packets_new_codexsol.jsonl --output $R/codexsol \
    --qualification reports/judge/codexsol_score_qualification.json --workers 4 > $O/codexsol_run_round$round.log 2>&1
  n=$(.venv/bin/python -c "import json; print(sum(1 for l in open('$R/codexsol/predictions.jsonl') if json.loads(l).get('judgment')))" 2>/dev/null || echo 0)
  echo "sol round $round: $n of $want judged $(date +%T)"
  [ "$n" -ge "$want" ] && break; sleep 3600
done
for j in claudecode codexsol; do cat $O/${j}_reused.jsonl $R/$j/predictions.jsonl > $O/${j}_predictions.jsonl; done
for c in C,A D,B D,A; do .venv/bin/python -W ignore -m aemon.evaluation.judging.report --key $K --judge claudecode=$O/claudecode_predictions.jsonl \
  --judge codexsol=$O/codexsol_predictions.jsonl --compare $c --output $O/report_both_${c/,/_vs_}.json > /dev/null; done
cp $K $O/key.jsonl
echo "judged $(date +%T)"
