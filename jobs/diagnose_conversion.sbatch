#!/bin/bash
#SBATCH --job-name=conversion-diag
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:4g.40gb:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --output=%x-%j.out
# READ-ONLY ARTIFACT DIAGNOSIS. Owner submits through the existing persistent SSH connection. No training/selection.
set -euo pipefail
: "${REVISION:?diagnostic code revision required}"
: "${ADAPTER:?native PEFT adapter folder required}"
: "${GGUF:?existing matching converted adapter required}"
: "${REFERENCE_REPORT:?original conversion JSON required}"
: "${ROWS:?archived source row file required}"
: "${NAME:?diagnostic label required}"
L=$HOME/lexsi
export PYTHONPATH=$L/code_$REVISION/src
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
cd "$L/code_$REVISION"
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh  # a job submitted with env -i has no module function
module load cuda/12.8
OUT=$L/runs/conversion_diagnosis
mkdir -p "$OUT"
TAG=$OUT/${NAME}_${SLURM_JOB_ID}
G=$L/models/tiny-aya-global-bf16.gguf
PORT=$((20000 + SLURM_JOB_ID % 20000))
PY=$L/env/bin/python
$PY -m aemon.evaluation.conversion.diagnose summarize --reports "$REFERENCE_REPORT" --output "$TAG.saved.json"
$PY -m aemon.evaluation.conversion.diagnose audit-tensors --adapter "$ADAPTER" --gguf "$GGUF" \
 --base-config "$L/models/tiny-aya-global/config.json" --output "$TAG.tensors.json"
sha256sum "$L/llama.cpp/convert_lora_to_gguf.py" "$L/llama.cpp/build/bin/llama-server" > "$TAG.exporter-runtime.sha256"
git -C "$L/llama.cpp" rev-parse HEAD > "$TAG.llama-commit.txt"
SERVER=
trap '[ -z "$SERVER" ] || kill "$SERVER" 2>/dev/null || true' EXIT
$L/llama.cpp/build/bin/llama-server -m "$G" --lora "$GGUF" --lora-init-without-apply -ngl 99 -c 12288 --parallel 1 \
 --host 127.0.0.1 --port "$PORT" --no-webui > "$TAG.server.log" 2>&1 &
SERVER=$!
for i in $(seq 1 120); do
 curl -sf http://127.0.0.1:$PORT/health > /dev/null && break
 kill -0 "$SERVER" || { echo 'diagnostic server died'; exit 1; }
 sleep 5
done
curl -sf http://127.0.0.1:$PORT/health > /dev/null || exit 1
EXTRA=()
# Only set this when the original archive is identified and accepting its weaker prompt identity is recorded.
[ "${ACK_RECONSTRUCTED:-0}" != 1 ] || EXTRA+=(--ack-reconstructed)
$PY -m aemon.evaluation.conversion.diagnose replay --model "$L/models/tiny-aya-global" --adapter "$ADAPTER" --gguf "$GGUF" \
 --base-gguf "$G" --server-pid "$SERVER" --reference-report "$REFERENCE_REPORT" --rows "$ROWS" \
 --url http://127.0.0.1:$PORT --tokens 32 --full-logprobs "${EXTRA[@]}" --output "$TAG.replay.json"
echo "Diagnostic only; no model qualifies from this run. Small JSON evidence is under $TAG; arrays remain archived on the cluster."
