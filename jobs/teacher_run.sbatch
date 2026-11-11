#!/bin/bash
#SBATCH --job-name=teacher-run
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:4g.40gb:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:30:00
#SBATCH --output=%x-%j.out
# Aya Expanse 32B through the identical staged harness. NO TRAINING. Set CASES, NAME and REVISION in the environment,
# and optionally PROMPT, ATTEMPTS and TEMPERATURE.
# Same context, reply limit and controller as the student, so only the model differs.
set -euo pipefail
PORT=$((20000 + SLURM_JOB_ID % 20000))  # each job its own port, so two jobs on one node never share a server
L=$HOME/lexsi
export PYTHONPATH=$L/code_${REVISION:-unset}/src  # the package, from this job's own copy of the code
GGUF=$L/models/aya-expanse-32b-gguf/aya-expanse-32b-Q4_K_M.gguf
OUT=$L/runs/teacher
mkdir -p $OUT
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh  # a job submitted with env -i has no module function
module load cuda/12.8
$L/llama.cpp/build/bin/llama-server -m $GGUF -ngl 99 -c 12288 --parallel 1 --jinja --reasoning-format none --host 127.0.0.1 --port $PORT --no-webui > $OUT/$NAME.server.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for i in $(seq 1 180); do
  curl -sf http://127.0.0.1:$PORT/health > /dev/null && break
  kill -0 $SERVER || { echo 'server died'; tail -5 $OUT/$NAME.server.log; exit 1; }
  sleep 5
done
echo "server ready $(date +%T), code $REVISION, $(cat $GGUF.provenance)"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
cd $L/code
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export CODE_REVISION=$REVISION
$L/env/bin/python -W ignore -m aemon.agent.run_investigations --url http://127.0.0.1:$PORT --prompt "${PROMPT:-staged}" --attempts "${ATTEMPTS:-1}" --temperature "${TEMPERATURE:-0}" --cases "$CASES" --context 12288 --max-tokens 520 --max-turns 45 \
  --model-label "aya-expanse-32b-Q4_K_M 3acdc28 code $REVISION" --weights-sha256 47eed19801ed865fabad06f7c0eb4b079b874281a8caac486f99300c7bf525f9 --output $OUT/$NAME.json > $OUT/$NAME.log 2>&1
echo "run exit $? $(date +%T)"
grep -E 'tokens per second|eval time' $OUT/$NAME.server.log | tail -2 | cut -c1-110 || true
