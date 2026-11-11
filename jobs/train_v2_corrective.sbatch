#!/bin/bash
#SBATCH --job-name=train-v2c
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:4g.40gb:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --output=%x-%j.out
# Version 2 corrective adapter (docs/V2_CORRECTIVE_PLAN.md): a short continuation of version 1 on the examples Nour marked
# Keep, mixed with version 1's own teacher rows. Version 1 (runs/final_pilot) is read, never written.
# Refuses to start without $L/reviews/V2_APPROVED, a file Nour creates after reviewing the examples and this plan.
# Set REVISION, NAME and MIX: the continuation set built by scripts/oneoff/v2_training_set.py from the rows that
# scripts/oneoff/v2_reviewed_rows.py rebuilt from the reviewed batches (plan section 7), with its .manifest.json beside it.
set -euo pipefail
L=$HOME/lexsi
[ -f $L/reviews/V2_APPROVED ] || { echo "no approval file: the examples and the plan have not been approved, nothing trains"; exit 2; }
[ -s "${MIX:-}" ] && [ -s "${MIX%.jsonl}.manifest.json" ] || { echo "MIX or its manifest is missing"; exit 2; }
export PYTHONPATH=$L/code_${REVISION:-unset}/src
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh
module load cuda/12.8
cd $L/code_$REVISION
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CODE_REVISION=$REVISION
OUT=$L/runs/${NAME:-v2_corrective}
[ -e $OUT ] && { echo "$OUT exists; results are never overwritten"; exit 2; }
echo "mix: $(wc -l < $MIX) rows, sha256 $(sha256sum $MIX | cut -c1-16)"; grep -E '"(corrective_rows|corrective_share_of_target_chars|output_sha256)"' ${MIX%.jsonl}.manifest.json
# Settings fixed in docs/V2_CORRECTIVE_PLAN.md (sections 2 and 7) before any example was approved: continue version 1's
# adapter, one pass over the mix (each corrective row twice, 20% of supervised target tokens), low learning rate,
# validation on the same six development companies version 1 held out.
$L/env/bin/python -W ignore -m aemon.training.train --model $L/models/tiny-aya-global --rows $MIX \
  --init-adapter $L/runs/final_pilot/adapter \
  --learning-rate ${LR:-2.5e-5} --epochs 1 --warmup 0.1 --save-steps 25 --max-length 8192 --seed 7 \
  --validation-cases hellberg neumann jotun tanita deere acr --out $OUT
echo "training done $(date +%T); evaluate with jobs/eval_adapter.sbatch (plan section 3), never on a frozen test set first"
