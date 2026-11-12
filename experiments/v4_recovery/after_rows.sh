#!/bin/bash
# Version 4, steps 3 and 4 (DECISIONS 2026-11-12 01:10 and 02:10), after driver.sh has built rows/v4_corrections.jsonl:
# if at least 50 corrections are kept, upload this code revision, submit jobs/train_v4.sbatch, then jobs/v4_screen.sbatch
# once it completes (gate v2, then version 3 against version 4 as the reasoner on development), fetch both arms, judge
# them together blind with the Claude Code judge and report version 4 minus version 3 with the registered adoption rule.
# The key stays outside the repository while judging. Job state is read at most every 10 minutes; a failed read counts
# as still running. Usage: nohup experiments/v4_recovery/after_rows.sh REVISION >> experiments/v4_recovery/after_rows.out 2>&1 &
set -uo pipefail
cd "$(dirname "$0")/../.."
REV=${1:?give the code revision}
D=experiments/v4_recovery
R=CLUSTER_ACCOUNT@CLUSTER_HOST
SSHO="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$HOME/.ssh/cm-lexsi -o ProxyCommand=false"
OUT=$D/screen KEY=$HOME/lexsi-backup/judge_keys/v4_screen_key.jsonl RES=$HOME/lexsi-backup/judge_results/v4_screen/claudecode
mkdir -p $OUT $HOME/lexsi-backup/judge_keys $HOME/lexsi-backup/judge_results/v4_screen
log() { echo "$(date '+%F %T') $*"; }
state() { local s; s=$(python3 scripts/cluster/cluster.py status 2>/dev/null) || { echo unknown; return; }; echo "$s" | awk -v j=$1 '$1 == j {print $3; exit}'; }
wait_job() { local s; while :; do s=$(state $1); case "$s" in RUNNING|PENDING|unknown|"") sleep 600;; *) echo "$s"; return;; esac; done; }

until grep -qE "step 3 done|stopping|failed" $D/driver.log; do sleep 600; done
grep -q "step 3 done" $D/driver.log || { log "driver stopped before rows: $(grep -E 'stopping|failed' $D/driver.log | tail -1)"; exit 1; }
KEPT=$(.venv/bin/python -c "import json; print(json.load(open('$D/corrections_summary.json'))['kept'])")
log "corrections kept: $KEPT"
[ "$KEPT" -ge 50 ] || { log "fewer than 50 corrections kept: version 4 is not trained (DECISIONS 02:10)"; exit 0; }

$SSHO $R "test -d lexsi/code_$REV" || git archive $REV src jobs scripts data/dossier | gzip | $SSHO $R "mkdir -p lexsi/code_$REV && tar -xz -C lexsi/code_$REV" || { log "code upload failed"; exit 1; }
TRAIN=$(python3 scripts/cluster/cluster.py submit jobs/train_v4.sbatch --env REVISION=$REV | grep -o "job [0-9]*" | cut -d' ' -f2)
[ -n "$TRAIN" ] || { log "train_v4 submit failed"; exit 1; }
log "train_v4 job $TRAIN, code $REV"
T=$(wait_job $TRAIN); log "train_v4 ended: $T"
[ "$T" = COMPLETED ] || { log "training did not complete; no screen (resubmit train_v4 to resume from its checkpoint)"; exit 1; }
SCREEN=$(python3 scripts/cluster/cluster.py submit jobs/v4_screen.sbatch --env REVISION=$REV | grep -o "job [0-9]*" | cut -d' ' -f2)
[ -n "$SCREEN" ] || { log "v4_screen submit failed"; exit 1; }
log "v4_screen job $SCREEN"
log "v4_screen ended: $(wait_job $SCREEN)"
for f in v4_screen_v3.json v4_screen_v4.json v4_gate_v2.json v4_gate_check.json; do
  for i in 1 2 3; do rsync -az -e "$SSHO" $R:lexsi/runs/eval/$f $OUT/ && break; sleep 1200; done
done
python3 scripts/cluster/cluster.py log $TRAIN --lines 15 > $OUT/train_v4.tail 2>&1
python3 scripts/cluster/cluster.py log $SCREEN --lines 20 > $OUT/v4_screen.tail 2>&1
[ -f $OUT/v4_screen_v3.json ] && [ -f $OUT/v4_screen_v4.json ] || { log "no screen reports: $(tail -3 $OUT/v4_screen.tail)"; exit 1; }
.venv/bin/python -W ignore -m aemon.evaluation.judging.packets --split development --report v3=$OUT/v4_screen_v3.json --report v4=$OUT/v4_screen_v4.json --packets $OUT/packets.jsonl --key $KEY
.venv/bin/python src/aemon/evaluation/judging/judge_v1/run_campaign.py --backend claudecode --packets $OUT/packets.jsonl --output $RES \
  --qualification reports/judge/claudecode_score_qualification.json --workers 4 > $OUT/claudecode_run.log 2>&1 || { log "judging stopped: $(tail -2 $OUT/claudecode_run.log)"; exit 1; }
.venv/bin/python -W ignore -m aemon.evaluation.judging.report --key $KEY --judge claudecode=$RES/predictions.jsonl --compare v4,v3 --output $OUT/report_v4_vs_v3.json
cp $KEY $OUT/key.jsonl; cp $RES/predictions.jsonl $OUT/claudecode_predictions.jsonl
.venv/bin/python - $OUT <<'PY'
import json, sys
o = sys.argv[1]
s = {a: json.load(open(f'{o}/v4_screen_{a}.json'))['summary'] for a in ('v3', 'v4')}
r = json.load(open(f'{o}/report_v4_vs_v3.json'))
d = r['judges']['claudecode']['difference']['mean_and_95_interval']
rule = {'quality not lower': d[0] >= 0, 'refused calls lower': s['v4']['refused_calls'] < s['v3']['refused_calls'], 'finished not fewer': s['v4']['finished'] >= s['v3']['finished']}
print(json.dumps({'finished': {a: s[a]['finished'] for a in s}, 'refused': {a: s[a]['refused_calls'] for a in s}, 'v4_minus_v3': d, 'rule': rule, 'adopted': all(rule.values())}))
PY
log "judged"
