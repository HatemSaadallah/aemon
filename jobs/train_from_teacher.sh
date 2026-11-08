#!/usr/bin/env bash
# One command from finished teacher stages to a submitted training run. NOTHING TRAINS LOCALLY.
# Usage: jobs/train_from_teacher.sh NAME STAGE_FILE... (stage files as named on the cluster, without the folder)
# Fetches the stage reports and the provenance manifest, builds rows (refused episodes are logged with reasons),
# uploads them, and submits the overfit check on 10 rows, then a first training run that starts only if it passes.
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=$1; shift
S=$HOME/.ssh/cm-lexsi
SSH="ssh -o BatchMode=yes -o ControlMaster=no -o ControlPath=$S CLUSTER_ACCOUNT@CLUSTER_HOST"
LOCAL=reports/strategy/teacher
for f in "$@"; do scp -q -o BatchMode=yes -o ControlMaster=no -o ControlPath=$S "CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/runs/teacher/$f.json" "CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/runs/teacher/$f.episodes.jsonl" $LOCAL/; done
scp -q -o BatchMode=yes -o ControlMaster=no -o ControlPath=$S CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/runs/teacher/provenance.jsonl $LOCAL/provenance_cluster.jsonl
mkdir -p reports/strategy/rows
ROWS=reports/strategy/rows/$NAME.jsonl
.venv/bin/python -W ignore -m strategy_agent.pipeline.rows --reports $(for f in "$@"; do echo $LOCAL/$f.json; done) --manifest $LOCAL/provenance_cluster.jsonl --output $ROWS
[ -s $ROWS ] || { echo "no rows, so nothing submitted"; exit 1; }
REV=$(git rev-parse --short HEAD)
$SSH "mkdir -p ~/lexsi/code_$REV ~/lexsi/rows"
git archive HEAD | $SSH "cd ~/lexsi/code_$REV && tar xf -"
scp -q -o BatchMode=yes -o ControlMaster=no -o ControlPath=$S $ROWS CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/rows/$NAME.jsonl
scp -q -o BatchMode=yes -o ControlMaster=no -o ControlPath=$S jobs/train_pilot.sbatch CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/train_pilot.sbatch
head -n 10 $ROWS > ${ROWS%.jsonl}_overfit10.jsonl
scp -q -o BatchMode=yes -o ControlMaster=no -o ControlPath=$S ${ROWS%.jsonl}_overfit10.jsonl CLUSTER_ACCOUNT@CLUSTER_HOST:lexsi/rows/${NAME}_overfit10.jsonl
$SSH "cd ~/lexsi/logs && O=\$(OUT=\$HOME/lexsi/runs/${NAME}_overfit ROWS=\$HOME/lexsi/rows/${NAME}_overfit10.jsonl REVISION=$REV STEPS=60 SAVE=20 CHECK=10 REQUIRE=8 sbatch --parsable --export=ALL ../train_pilot.sbatch) && echo overfit \$O && \
  OUT=\$HOME/lexsi/runs/${NAME}_pilot ROWS=\$HOME/lexsi/rows/$NAME.jsonl REVISION=$REV EPOCHS=3 SAVE=25 sbatch --parsable --dependency=afterok:\$O --export=ALL ../train_pilot.sbatch | sed 's/^/pilot /'"
