#!/bin/bash
#SBATCH --job-name=train-pilot
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:4g.40gb:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=23:30:00
#SBATCH --signal=B:USR1@600
#SBATCH --output=%x-%j.out
# LoRA training through AgentTune. Resubmit the same command to continue from the latest checkpoint.
# Set OUT, REVISION and either ROWS or FIXTURE in the environment, and optionally STEPS, SAVE, MINUTES and CHECK.
set -euo pipefail
L=$HOME/lexsi
export PYTHONPATH=$L/code_${REVISION:-unset}/src  # the package, from this job's own copy of the code
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh  # a job submitted with env -i has no module function
module load cuda/12.8
cd $L/code_$REVISION
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
SOURCE=$([ -n "${FIXTURE:-}" ] && echo "--fixture-rows $FIXTURE" || echo "--rows $ROWS")
# Real rows are validated on the companies in strategy/splits.py unless VALIDATION says otherwise; fixtures need none
[ -z "${FIXTURE:-}" ] && VALIDATION=${VALIDATION:-$($L/env/bin/python -m aemon.data.splits)}
echo "start $(date +%T), code $REVISION, $(lquota 2>/dev/null | grep USED)"
$L/env/bin/python -W ignore -m aemon.training.train --model $L/models/tiny-aya-global $SOURCE --out $OUT --max-steps "${STEPS:-0}" --epochs "${EPOCHS:-3}" --save-steps "${SAVE:-25}" \
  --minutes "${MINUTES:-1370}" --check "${CHECK:-0}" --require "${REQUIRE:-0}" ${VALIDATION:+--validation-cases $VALIDATION} &
PID=$!
trap 'kill -USR1 $PID 2>/dev/null' USR1
wait $PID || wait $PID
echo "end $(date +%T)"
