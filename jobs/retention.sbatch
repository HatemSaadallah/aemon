#!/bin/bash
#SBATCH --job-name=retention
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:3g.40gb:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=%x_%j.log
# General-capability retention check: base Tiny Aya (bf16 GGUF, the evaluated file) against the same server with the
# version 1 adapter at scale 1, and the version 3 adapter at scale 1, on the sampled MMLU and ARC-Challenge items.
set -euo pipefail
L=$HOME/lexsi
B=$L/bench
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh
module load cuda/12.8
PORT=$((20000 + SLURM_JOB_ID % 20000))
G=$L/models/tiny-aya-global-bf16.gguf
V1=$L/runs/eval/final_test_trained_adapter.gguf   # sha256 41794b57..., the file evaluated on the frozen tests
V3=$L/runs/eval/final_test_v3_adapter.gguf
sha256sum $G $V1 $V3 | cut -c1-16,66- | tee $B/retention_${SLURM_JOB_ID}.sha
$L/llama.cpp/build/bin/llama-server -m $G --lora $V1 --lora $V3 --lora-init-without-apply -ngl 99 -c 4096 --parallel 1 \
  --jinja --reasoning-format none --host 127.0.0.1 --port $PORT --no-webui > $B/retention_${SLURM_JOB_ID}.server.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for i in $(seq 1 120); do curl -sf http://127.0.0.1:$PORT/health > /dev/null && break; kill -0 $SERVER || { echo "server died"; tail -5 $B/retention_${SLURM_JOB_ID}.server.log; exit 1; }; sleep 5; done
echo "server ready $(date +%T)"
curl -s http://127.0.0.1:$PORT/lora-adapters; echo
$L/env/bin/python -W ignore $B/retention.py --url http://127.0.0.1:$PORT --items $B/retention_items.jsonl \
  --arms base= v1=0 v3=1 --out $B/retention_${SLURM_JOB_ID}.json
echo "done $(date +%T)"
