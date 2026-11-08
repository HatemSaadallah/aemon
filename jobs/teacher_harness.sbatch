#!/bin/bash
#SBATCH --job-name=teacher-harness
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=23:30:00
#SBATCH --output=%x-%j.out
# A harness only: no GPU and no model here. It drives a teacher server running in another job (for example
# command_a_plus_remote.sbatch on a node without home) over the cluster network, taking batches from the same queues
# under the same lock as the GPU job, with the same stage checks. Set REMOTE_URL, LLAMA_API_KEY, QUEUE, NAME, REVISION.
set -euo pipefail
L=$HOME/lexsi
export PYTHONPATH=$L/code_${REVISION:-unset}/src  # the package, from this job's own copy of the code
OUT=$L/runs/teacher
cd $L/code_$REVISION
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CODE_REVISION=$REVISION CHAT_TIMEOUT=1200
eval "$(sed -n '/^stage() {/,/^}$/p; /^take() {/,/^}$/p; /^give_back() {/p' $L/code_$REVISION/jobs/command_a_plus.sbatch)"
for i in $(seq 1 480); do curl -sf $REMOTE_URL/health > /dev/null && break; sleep 30; done
curl -sf $REMOTE_URL/health > /dev/null || { echo "server never came up"; exit 1; }
echo "server ready at $REMOTE_URL $(date +%T)"
END=$(( $(date +%s) + ${HOURS:-22} * 3600 ))
while [ $(date +%s) -lt $END ]; do
  curl -sf $REMOTE_URL/health > /dev/null || { echo "server gone $(date +%T)"; break; }
  LINE=$(take)
  [ -z "$LINE" ] && { echo "queue empty $(date +%T)"; break; }
  set -- $LINE
  W=$(curl -sf -H "Authorization: Bearer $LLAMA_API_KEY" $REMOTE_URL/props | $L/env/bin/python -c "import json,sys; print(json.load(sys.stdin).get('total_slots', 1))" 2>/dev/null || echo 1)
  SLOTS=$W
  stage "$1" "$2" "$3" "$4" $REMOTE_URL $W $NAME "llama.cpp b12032 built on the serving node" || { give_back "$LINE"; echo "batch $1 failed and went back on the queue, stopping"; break; }
done
