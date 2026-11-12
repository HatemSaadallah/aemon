#!/bin/bash
#SBATCH --job-name=v4-screen
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:4g.40gb:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=09:00:00
#SBATCH --output=%x-%j.out
# Version 4, steps 3 (gate) and 4 (development screen) of DECISIONS 2026-11-12 01:10, after jobs/train_v4.sbatch.
# 1. Convert runs/v4/adapter to GGUF and apply conversion gate v2 (DECISIONS 2026-11-06), the same steps as
#    train_after_teacher's conversion_gate: the checker picks the prompts, the diagnosis replays them, the gate reads
#    the diagnosis. If v4 does not pass, no arm runs.
# 2. One server holds version 1 (id 0), version 3 (id 1) and version 4 (id 2). Two arms, the same 15 development cases,
#    3 attempts, the same settings: dig then reason with version 3 as the reasoner (default=1) and with version 4
#    (default=2), version 1 writing brief, frame and evidence in both. No loop guards in either arm: the screen was
#    registered before the guards were adopted, and the guards would hide the recovery version 4 is meant to learn.
# Set REVISION.
set -euo pipefail
L=$HOME/lexsi
G=$L/models/tiny-aya-global-bf16.gguf
OUT=$L/runs/eval
V1=$OUT/final_test_trained_adapter.gguf
V3=$OUT/final_test_v3_adapter.gguf
V4=$OUT/v4_adapter.gguf
AD=$L/runs/v4/adapter
ROWS=${ROWS:-$L/rows/v3_deepseek_val.jsonl}
PORT=$((20000 + SLURM_JOB_ID % 20000))
CASES=hellberg-base,hellberg-new-evidence-looks,hellberg-new-evidence-comfort,hellberg-new-evidence-favours-looks,hellberg-new-evidence-irrelevant,neumann-base,neumann-new-evidence-irrelevant,jotun-base,jotun-new-evidence-irrelevant,tanita-base,tanita-new-evidence-irrelevant,deere-base,deere-new-evidence-irrelevant,acr-base,acr-new-evidence-irrelevant
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh
module load cuda/12.8
echo "41794b5756b9e0f87c58dd14e451756d15c897d595886dee9921181298fdb9d1  $V1" | sha256sum -c
echo "ea9193807fe9d5132878021bdf73de40ee84e2486f6688db9b3c3e29e04e1443  $V3" | sha256sum -c
[ -f $AD/adapter_config.json ] || { echo "no version 4 adapter at $AD"; exit 2; }
PYTHONPATH=$L/llama.cpp/gguf-py $L/env/bin/python $L/llama.cpp/convert_lora_to_gguf.py --base $L/models/tiny-aya-global --outtype bf16 --outfile $V4 $AD 2>&1 | tail -1 | cut -c1-160
sha256sum $V4 | tee $V4.sha256
SERVER=
trap '[ -n "$SERVER" ] && kill $SERVER 2>/dev/null || true' EXIT
up() { for i in $(seq 1 120); do curl -sf http://127.0.0.1:$PORT/health > /dev/null && return 0; kill -0 $SERVER || { echo "server died"; return 1; }; sleep 5; done; return 1; }

# 1. conversion gate v2
$L/llama.cpp/build/bin/llama-server -m $G --lora $V4 --lora-init-without-apply -ngl 99 -c 12288 --parallel 1 --host 127.0.0.1 --port $PORT --no-webui > $OUT/v4_gate_check.server.log 2>&1 &
SERVER=$!; up
(cd $L/code_$REVISION && PYTHONPATH=$L/code_$REVISION/src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $L/env/bin/python -W ignore -m aemon.evaluation.conversion.check \
  --model $L/models/tiny-aya-global --adapter $AD --url http://127.0.0.1:$PORT --rows $ROWS --output $OUT/v4_gate_check.json 2>&1 | tail -1) || true
kill $SERVER 2>/dev/null; sleep 5; SERVER=
REVISION=$REVISION ACK_RECONSTRUCTED=1 ADAPTER=$AD GGUF=$V4 REFERENCE_REPORT=$OUT/v4_gate_check.json ROWS=$ROWS NAME=v4_final \
  bash $L/code_$REVISION/jobs/diagnose_conversion.sbatch > $OUT/v4_gate_diagnosis.log 2>&1 || true
DX=$L/runs/conversion_diagnosis/v4_final_${SLURM_JOB_ID}
[ -f $DX.replay.json ] || { echo "no diagnosis replay, see $OUT/v4_gate_diagnosis.log"; tail -5 $OUT/v4_gate_diagnosis.log; exit 3; }
PYTHONPATH=$L/code_$REVISION/src $L/env/bin/python -m aemon.evaluation.conversion.gate --replay $DX.replay.json --tensors $DX.tensors.json --output $OUT/v4_gate_v2.json
[ "$($L/env/bin/python -c "import json; print(json.load(open('$OUT/v4_gate_v2.json'))['passed'])")" = True ] || { echo "version 4 does not pass conversion gate v2: no arm runs"; exit 3; }
echo "gate v2 passed $(date +%T)"

# 2. development screen, one server holding all three
export PYTHONPATH=$L/code_$REVISION/src
WEIGHTS=$(sha256sum $G | cut -d' ' -f1)
$L/llama.cpp/build/bin/llama-server -m $G --lora $V1 --lora $V3 --lora $V4 --lora-init-without-apply -ngl 99 -c 12288 --parallel 1 --jinja --reasoning-format none \
  --host 127.0.0.1 --port $PORT --no-webui > $OUT/v4_screen.server.log 2>&1 &
SERVER=$!; up
curl -s http://127.0.0.1:$PORT/lora-adapters; echo
cd $L/code_$REVISION
for arm in v3:1 v4:2; do
  N=v4_screen_${arm%%:*} ROUTE=default=${arm##*:},brief=0,frame=0,evidence=0
  PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 CODE_REVISION=$REVISION $L/env/bin/python -W ignore -m aemon.agent.run_investigations --url http://127.0.0.1:$PORT --prompt compact --cases "$CASES" --split development \
    --context 12288 --max-tokens 520 --max-turns 45 --attempts 3 --lora-route "$ROUTE" --model-label "tiny-aya-global bf16 af89d21 route $ROUTE (id 2 = version 4)" --weights-sha256 $WEIGHTS \
    --manifest $OUT/provenance.jsonl --output $OUT/$N.json > $OUT/$N.log 2>&1 || true
  $L/env/bin/python -c "import json; s=json.load(open('$OUT/$N.json'))['summary']; print('$N', json.dumps({k: s[k] for k in ('episodes', 'finished', 'end_to_end_success', 'stop_reasons', 'refused_calls', 'mean_calls')}))"
done
echo "done $(date +%T)"
