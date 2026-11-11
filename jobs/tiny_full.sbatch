#!/bin/bash
#SBATCH --job-name=tiny-full
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:4g.40gb:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH --output=%x-%j.out
# Untrained Tiny Aya at full bf16 precision under the corrected controller. NO TRAINING.
# Shows how much of the Q4 stalling comes from quantization, and is the runtime an adapter would later use.
set -euo pipefail
PORT=$((20000 + SLURM_JOB_ID % 20000))  # each job its own port, so two jobs on one node never share a server
L=$HOME/lexsi
export PYTHONPATH=$L/code_${REVISION:-unset}/src  # the package, from this job's own copy of the code
G=$L/models/tiny-aya-global-bf16.gguf
OUT=$L/runs/base
mkdir -p $OUT
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh  # a job submitted with env -i has no module function
module load cuda/12.8
export PYTHONPATH=$L/llama.cpp/gguf-py
if [ ! -f $G ]; then
  $L/env/bin/python $L/llama.cpp/convert_hf_to_gguf.py $L/models/tiny-aya-global --outtype bf16 --outfile $G.part 2>&1 | tail -4 | cut -c1-140
  mv $G.part $G
fi
ls -la $G | awk '{print $5}'
export PYTHONPATH=$L/code_${REVISION:-unset}/src
$L/llama.cpp/build/bin/llama-server -m $G -ngl 99 -c 12288 --parallel 1 --jinja --reasoning-format none --host 127.0.0.1 --port $PORT --no-webui > $OUT/$NAME.server.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for i in $(seq 1 120); do
  curl -sf http://127.0.0.1:$PORT/health > /dev/null && break
  kill -0 $SERVER || { echo 'server died'; tail -6 $OUT/$NAME.server.log | cut -c1-170; exit 1; }
  sleep 5
done
echo "server ready $(date +%T), code $REVISION"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
cd $L/code_$REVISION
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CODE_REVISION=$REVISION
WEIGHTS=$(sha256sum $G | cut -d' ' -f1)
echo "weights $WEIGHTS"
$L/env/bin/python -W ignore -m aemon.agent.run_investigations --url http://127.0.0.1:$PORT --prompt "${PROMPT:-staged}" --cases all --context 12288 --max-tokens 520 --max-turns 45 \
  --model-label "tiny-aya-global bf16 af89d21 code $REVISION" --weights-sha256 $WEIGHTS --manifest $OUT/provenance.jsonl --output $OUT/$NAME.json > $OUT/$NAME.log 2>&1 && echo "run exit 0 $(date +%T)" || echo "run exit $? $(date +%T)"
