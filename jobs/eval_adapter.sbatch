#!/bin/bash
#SBATCH --job-name=eval-adapter
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:4g.40gb:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --output=%x-%j.out
# Development evaluation, B against C: the same bf16 Tiny Aya in the same llama.cpp build, first alone, then with the trained
# adapter, on the same cases, controller and settings, after checking the converted adapter against the PEFT one. Set ADAPTER, NAME, CASES and REVISION, and PROMPT to match the
# rows the adapter was trained on (compact for compact rows). Both arms use it. Not the final test.
set -euo pipefail
L=$HOME/lexsi
export PYTHONPATH=$L/code_${REVISION:-unset}/src  # the package, from this job's own copy of the code
G=$L/models/tiny-aya-global-bf16.gguf
OUT=$L/runs/eval
PORT=$((20000 + SLURM_JOB_ID % 20000))
mkdir -p $OUT
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh  # a job submitted with env -i has no module function
module load cuda/12.8
export PYTHONPATH=$L/llama.cpp/gguf-py
LORA=$OUT/${NAME}_adapter.gguf
if [ -n "${SKIP_ADAPTER:-}" ]; then ADAPTER=; fi  # SKIP_ADAPTER=1: the base arm only, for a second base prompt
[ -z "${ADAPTER:-}" ] || $L/env/bin/python $L/llama.cpp/convert_lora_to_gguf.py --base $L/models/tiny-aya-global --outtype bf16 --outfile $LORA $ADAPTER 2>&1 | tail -3 | cut -c1-160
[ -z "${ADAPTER:-}" ] || sha256sum $LORA | tee $OUT/${NAME}_adapter.gguf.sha256  # which converted adapter this evaluation ran, to match against the gated one
export PYTHONPATH=$L/code_${REVISION:-unset}/src
WEIGHTS=$(sha256sum $G | cut -d' ' -f1)
SERVER=
trap '[ -n "$SERVER" ] && kill $SERVER 2>/dev/null || true' EXIT
arm() {  # name, extra server arguments
  [ -n "$SERVER" ] && kill $SERVER 2>/dev/null && sleep 5
  $L/llama.cpp/build/bin/llama-server -m $G $2 -ngl 99 -c 12288 --parallel 1 --jinja --reasoning-format none --host 127.0.0.1 --port $PORT --no-webui > $OUT/${NAME}_$1.server.log 2>&1 &
  SERVER=$!
  for i in $(seq 1 120); do curl -sf http://127.0.0.1:$PORT/health > /dev/null && break; kill -0 $SERVER || { echo "server died"; tail -5 $OUT/${NAME}_$1.server.log; exit 1; }; sleep 5; done
  echo "arm $1 server ready $(date +%T)"
  cd $L/code_$REVISION
  PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 CODE_REVISION=$REVISION $L/env/bin/python -W ignore -m strategy_agent.agent.runner --url http://127.0.0.1:$PORT --prompt ${PROMPT:-staged} --cases "$CASES" --split ${SPLIT:-development} \
    --context 12288 --max-tokens 520 --max-turns 45 --attempts ${ATTEMPTS:-1} --model-label "tiny-aya-global bf16 af89d21 $1" --weights-sha256 $WEIGHTS --manifest $OUT/provenance.jsonl \
    --output $OUT/${NAME}_$1.json > $OUT/${NAME}_$1.log 2>&1 || true
  echo "arm $1 finished $(date +%T)"
  $L/env/bin/python -c "import json; s=json.load(open('$OUT/${NAME}_$1.json'))['summary']; print('$1', json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))"
}
if [ -n "${SKIP_ADAPTER:-}" ]; then arm base ""; echo "evaluation done $(date +%T)"; exit 0; fi
# Before any arm: does the converted adapter behave like the PEFT adapter? Same token ids on both sides, adapter on and off.
$L/llama.cpp/build/bin/llama-server -m $G --lora $LORA --lora-init-without-apply -ngl 99 -c 12288 --parallel 1 --host 127.0.0.1 --port $PORT --no-webui > $OUT/${NAME}_conversion.server.log 2>&1 &
SERVER=$!
for i in $(seq 1 120); do curl -sf http://127.0.0.1:$PORT/health > /dev/null && break; sleep 5; done
(cd $L/code_$REVISION && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $L/env/bin/python -W ignore -m strategy_agent.evaluation.conversion_check --model $L/models/tiny-aya-global --adapter $ADAPTER \
  --url http://127.0.0.1:$PORT --rows ${ROWS:-$L/rows/$NAME.jsonl} --output $OUT/${NAME}_conversion.json 2>&1 | tail -2 | sed 's/^/conversion check /') || true  # the verdict is read from the JSON below
if [ "$($L/env/bin/python -c "import json; print(json.load(open('$OUT/${NAME}_conversion.json'))['summary']['passed'])" 2>/dev/null)" != True ]; then
  # DIAGNOSTIC=1 runs the arms anyway, for development only: every output of this run is marked, and it never selects a model
  [ -n "${DIAGNOSTIC:-}" ] || { echo "conversion gate not passed: the arms do not run, because their results could not be read"; exit 3; }
  echo "conversion gate failed; DIAGNOSTIC=1, so the arms run as a development diagnostic that selects nothing" | tee $OUT/${NAME}_DIAGNOSTIC_conversion_gate_failed.txt
fi
kill $SERVER 2>/dev/null; sleep 5; SERVER=
# SKIP_BASE=1 reuses an earlier base arm run on the same base model, build, cases, prompt and settings
[ -n "${SKIP_BASE:-}" ] || arm base ""
arm adapter "--lora $LORA"
echo "evaluation done $(date +%T)"
