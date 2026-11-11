#!/bin/bash
#SBATCH --job-name=eval-switch
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:4g.40gb:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=03:00:00
#SBATCH --output=%x-%j.out
# Development only (DECISIONS 2026-11-11, adapter switching): one server holds both converted, gated adapters, version 1
# as id 0 and version 3 as id 1, and ROUTE decides which one writes each turn (runner --lora-route), for example
# 'default=1,stuck=0' (version 3, handing a turn to version 1 after two refusals in a row). Every arm, the single-adapter
# ones included, runs on this same two-adapter server, so arms differ only in the route. Set NAME, ROUTE, CASES, REVISION.
# STATUS_CHECK=1 adds the company_status step; SPLIT=heldout is for the labelled Aquaporin diagnostic only.
set -euo pipefail
L=$HOME/lexsi
G=$L/models/tiny-aya-global-bf16.gguf
OUT=$L/runs/eval
V1=$OUT/final_test_trained_adapter.gguf
V3=$OUT/final_test_v3_adapter.gguf
PORT=$((20000 + SLURM_JOB_ID % 20000))
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh
module load cuda/12.8
# the evaluated adapters must be the gated ones
echo "41794b5756b9e0f87c58dd14e451756d15c897d595886dee9921181298fdb9d1  $V1" | sha256sum -c
echo "ea9193807fe9d5132878021bdf73de40ee84e2486f6688db9b3c3e29e04e1443  $V3" | sha256sum -c
export PYTHONPATH=$L/code_$REVISION/src
WEIGHTS=$(sha256sum $G | cut -d' ' -f1)
$L/llama.cpp/build/bin/llama-server -m $G --lora $V1 --lora $V3 --lora-init-without-apply -ngl 99 -c 12288 --parallel 1 --jinja --reasoning-format none \
  --host 127.0.0.1 --port $PORT --no-webui > $OUT/${NAME}.server.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for i in $(seq 1 120); do curl -sf http://127.0.0.1:$PORT/health > /dev/null && break; kill -0 $SERVER || { echo "server died"; tail -5 $OUT/${NAME}.server.log; exit 1; }; sleep 5; done
curl -s http://127.0.0.1:$PORT/lora-adapters; echo
cd $L/code_$REVISION
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 CODE_REVISION=$REVISION $L/env/bin/python -W ignore -m aemon.agent.run_investigations --url http://127.0.0.1:$PORT --prompt compact --cases "$CASES" --split ${SPLIT:-development} ${STATUS_CHECK:+--status-check} \
  --context 12288 --max-tokens 520 --max-turns 45 --attempts ${ATTEMPTS:-3} --lora-route "$ROUTE" --model-label "tiny-aya-global bf16 af89d21 route $ROUTE" --weights-sha256 $WEIGHTS \
  --manifest $OUT/provenance.jsonl --output $OUT/${NAME}.json > $OUT/${NAME}.log 2>&1
$L/env/bin/python -c "import json; s=json.load(open('$OUT/${NAME}.json'))['summary']; print('$NAME', json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))"
echo "done $(date +%T)"
