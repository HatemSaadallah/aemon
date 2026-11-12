#!/bin/bash
#SBATCH --job-name=train-v4
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:7g.80gb:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=%x-%j.out
# Version 4 (DECISIONS 2026-11-12 01:10, step 3): continue version 3's adapter (runs/v3/adapter, read, never written)
# on version 3's own DeepSeek rows plus the kept Command A+ recovery corrections (experiments/v4_recovery), one pass,
# version 3's learning rate and seed. Corrections are at most 20% of rows: if there are more, an evenly spaced subset
# is kept here, before training (the trainer's own cap is by target tokens and is left open at 0.95, as in version 3).
# Validation: version 3's DeepSeek validation rows. A stopped job resumes from its latest checkpoint when resubmitted.
# Set REVISION and optionally NAME (default v4), CORRECTIONS, DEEPSEEK, VALROWS. Conversion gate v2 runs after, as for
# every adapter.
set -euo pipefail
L=$HOME/lexsi
NAME=${NAME:-v4}
DEEPSEEK=${DEEPSEEK:-$L/rows/v3_deepseek_train.jsonl}
CORRECTIONS=${CORRECTIONS:-$L/rows/v4_corrections.jsonl}
VALROWS=${VALROWS:-$L/rows/v3_deepseek_val.jsonl}
[ -s "$DEEPSEEK" ] && [ -s "$CORRECTIONS" ] && [ -s "$VALROWS" ] || { echo "DEEPSEEK, CORRECTIONS or VALROWS is missing"; exit 2; }
echo "a4845f4cf4f48ee687b2a3dc9ff9117ebe37701f61a52762a45b8ba2bc2adac5  $DEEPSEEK" | sha256sum -c  # the rows version 3 trained on
echo "a802b5f3aa1fe67153a68d5a2de64ca756de08b2cfa863d91eeb1a85d0ec39d8  $VALROWS" | sha256sum -c
export PYTHONPATH=$L/code_${REVISION:-unset}/src
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh
module load cuda/12.8
cd $L/code_$REVISION
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CODE_REVISION=$REVISION
OUT=$L/runs/$NAME
mkdir -p $OUT
# corrections <= 20% of all rows, so at most a quarter of the DeepSeek row count; evenly spaced, so no choice by content
$L/env/bin/python - "$DEEPSEEK" "$CORRECTIONS" "$OUT/corrections_used.jsonl" <<'PY'
import sys
base = sum(1 for _ in open(sys.argv[1]))
rows = open(sys.argv[2]).readlines()
cap = base // 4
used = rows if len(rows) <= cap else [rows[round(i * len(rows) / cap)] for i in range(cap)]
open(sys.argv[3], 'w').writelines(used)
print(f'DeepSeek rows {base}, corrections {len(rows)}, used {len(used)} ({len(used) / (base + len(used)):.1%} of rows, cap 20%)')
PY
echo "corrections sha256 $(sha256sum $CORRECTIONS | cut -c1-16), used $(sha256sum $OUT/corrections_used.jsonl | cut -c1-16), validation rows $(wc -l < $VALROWS)"
$L/env/bin/python -W ignore -m aemon.training.train --model $L/models/tiny-aya-global --rows $DEEPSEEK \
  --extra-rows $OUT/corrections_used.jsonl --extra-token-share 0.95 --validation-rows $VALROWS \
  --init-adapter $L/runs/v3/adapter \
  --learning-rate ${LR:-2.5e-5} --epochs 1 --warmup 0.1 --save-steps 25 --max-length 8192 --seed 7 --minutes 700 \
  --validation-cases hellberg neumann jotun tanita deere acr --out $OUT
echo "training done $(date +%T)"
