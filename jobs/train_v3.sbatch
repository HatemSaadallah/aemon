#!/bin/bash
#SBATCH --job-name=train-v3
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:7g.80gb:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=%x-%j.out
# Version 3 (DECISIONS 2026-11-10 23:25 UTC): continue version 1's adapter on all of version 1's rows plus every
# replay-exact DeepSeek V4-Pro investigation row, one pass. Validation: the six development companies' Command A+ rows
# and six training companies' DeepSeek rows, as a universal loss weighting both teachers equally. Version 1
# (runs/final_pilot) is read, never written. A stopped job resumes from its latest checkpoint when resubmitted.
# Set REVISION, NAME, EXTRA (DeepSeek training rows) and VALROWS (DeepSeek validation rows).
set -euo pipefail
L=$HOME/lexsi
[ -s "${EXTRA:-}" ] && [ -s "${VALROWS:-}" ] || { echo "EXTRA or VALROWS is missing"; exit 2; }
export PYTHONPATH=$L/code_${REVISION:-unset}/src
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh
module load cuda/12.8
cd $L/code_$REVISION
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CODE_REVISION=$REVISION
OUT=$L/runs/${NAME:-v3}
echo "base rows $(wc -l < $L/rows/final.jsonl), DeepSeek rows $(wc -l < $EXTRA) (sha256 $(sha256sum $EXTRA | cut -c1-16)), validation rows $(wc -l < $VALROWS)"
$L/env/bin/python -W ignore -m aemon.training.train --model $L/models/tiny-aya-global --rows $L/rows/final.jsonl \
  --extra-rows $EXTRA --extra-token-share 0.95 --validation-rows $VALROWS \
  --init-adapter $L/runs/final_pilot/adapter \
  --learning-rate ${LR:-2.5e-5} --epochs 1 --warmup 0.1 --save-steps 25 --max-length 8192 --seed 7 --minutes 700 \
  --validation-cases hellberg neumann jotun tanita deere acr --out $OUT
echo "training done $(date +%T)"
