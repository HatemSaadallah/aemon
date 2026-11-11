#!/bin/bash
#SBATCH --job-name=command-a-plus
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:7g.80gb:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=200G
#SBATCH --time=23:30:00
#SBATCH --output=%x-%j.out
# Command A+ (Apache 2.0) as a candidate teacher, through the identical staged harness. NO TRAINING.
# 135 GB exceeds the 50 GB quota, so the model lives in node memory for this job only and is removed at the end.
# Set CASES, NAME and REVISION in the environment, and optionally PROMPT, ATTEMPTS and TEMPERATURE. STATUS_CHECK=1 adds the
# company_status step (DECISIONS 2026-11-11, Aquaporin).
set -euo pipefail
PORT=$((20000 + SLURM_JOB_ID % 20000))  # each job its own port, so two jobs on one node never share a server
L=$HOME/lexsi
export PYTHONPATH=$L/code_${REVISION:-unset}/src  # the package, from this job's own copy of the code
OUT=$L/runs/teacher
REPO=bartowski/command-a-plus-05-2026-GGUF
REVISION_HF=a26ba921242484b5e1a8ac8519169fe7421c3ab3
STEM=command-a-plus-05-2026-Q4_K_M
D=/dev/shm/lexsi-$SLURM_JOB_ID
mkdir -p $D $OUT
SERVER=
cleanup() {  # if this node fails, the remote harness still finishes its work first
  [ -n "${REMOTE_PID:-}" ] && { echo "waiting for the remote worker before exit"; wait $REMOTE_PID || true; }
  [ -n "$SERVER" ] && kill $SERVER 2>/dev/null || true; rm -rf "$D"; }
trap cleanup EXIT
echo "node $(hostname), $(df -h /dev/shm | tail -1 | awk '{print $4}') free in memory, start $(date +%T)"
cat > $D/sums <<SUMS
03cf0669f0a6f338a064f264b7c54df1bb882d16860ea513727b199c1ff05b8f  $STEM-00001-of-00004.gguf
97c859c036a6a8a4cd02e4d57aaea7fed94642058ba714ab7ccce95acfff0fa5  $STEM-00002-of-00004.gguf
9ffbedb12dc63f09b84e9e85636607e26f95426fd10947d582ab89e5f0e05e7c  $STEM-00003-of-00004.gguf
b429a070fb15f53e2b6e1417942c507fc03958db6e6a547846277b60ac2012e2  $STEM-00004-of-00004.gguf
SUMS
cd $D
fetch() {  # a dropped transfer resumes where it stopped, and repeated failure stops the job
  for attempt in 1 2 3 4 5 6 7 8 9 10 11 12; do
    curl -fsSL -C - -o "$1" "https://huggingface.co/$REPO/resolve/$REVISION_HF/$STEM/$1" && return 0
    echo "retrying $1, attempt $attempt"
    sleep 20
  done
  return 1
}
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh  # a job submitted with env -i has no module function
module load cuda/12.8
BIN=$L/llama.cpp/build/bin
BUILDER=
if [ -n "${REBUILD:-}" ]; then
  # The first build ran on a node with no GPU, so CUDA code was not compiled for the GPU it runs on. That mismatch makes the
  # mixture-of-experts kernel fail on decode batches of about 5 to 7 (llama.cpp issue 30524), which is why parallel slots
  # crashed. Build the same source for this GPU, in its own folder, while the download runs, so a running job is untouched.
  CC=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | awk 'NR==1 {gsub(/\./, ""); print}')  # awk reads all input: head could end the pipe early and kill the job with SIGPIPE under pipefail
  BUILD=$L/llama.cpp/build-sm$CC
  if [ ! -x $BUILD/bin/llama-server ]; then
    ( export PATH=$L/tools/cmake/bin:$PATH PYTHONPATH=$L/tools/cmake; cd $L/llama.cpp && flock $L/llama.cpp/.build.lock bash -c \
      "cmake -B $BUILD -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=$CC -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF -DBUILD_SHARED_LIBS=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON -DCMAKE_BUILD_TYPE=Release \
       && cmake --build $BUILD --target llama-server -j 6" ) > $OUT/$NAME.build.log 2>&1 &
    BUILDER=$!
  fi
fi
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CODE_REVISION=$REVISION CHAT_TIMEOUT=1200
# Stages share the loaded model. Each writes its own file and must pass aemon.rows.stage_check before the next
# starts, so a broken setup stops after the smoke stage instead of after hours.
stage() {  # batch, cases, first attempt, temperature, then optionally server url, parallel episodes, output prefix, label note
  local URL=${5:-http://127.0.0.1:$PORT} W=${6:-$SLOTS} P=${7:-$NAME}
  if [[ $1 == targeted* || $1 == corrective* ]]; then  # version 2 examples (docs/V2_PLAN.md; corrective*: docs/CORRECTIVE_DISTILLATION_PROPOSAL.md): $2 is a states file. Low acceptance is allowed;
    # a crash or an unreadable output is not, so the command's status is kept and the output is checked and counted.
    local RC=0
    local MODULE=targeted; [[ $1 == corrective* ]] && MODULE=corrective
    $L/env/bin/python -W ignore -m aemon.teacher.$MODULE ask --states "$2" --url $URL --workers $W --server-settings "{\"reasoning_budget\": ${THINK:-1024}, \"context_per_slot\": ${CONTEXT:-16384}, \"slots\": $W, \"prompt_version\": \"${PROMPT_VERSION:-teacher-v1}\"}" --weights-sha256 03cf0669f0a6f338a064f264b7c54df1bb882d16860ea513727b199c1ff05b8f \
      --samples ${SAMPLES:-1} --temperature ${TEMPERATURE:-0} --manifest $OUT/provenance.jsonl --output $OUT/${P}_$1.json > $OUT/${P}_$1.log 2>&1 || RC=$?
    echo "stage $P $1 ended $(date +%T), exit $RC"
    $L/env/bin/python - "$OUT/${P}_$1.json" <<'PYT' || { echo "stage $P $1: output missing or unreadable"; return 1; }
import collections, json, sys
d = json.load(open(sys.argv[1]))
failed = [x for x in d if str(x.get('decision', '')).startswith('request failed')]
valid = [x for x in d if 'reply' in x]
kept = [x for x in d if isinstance(x.get('kept'), dict)]
reasons = collections.Counter(x['decision'] for x in valid if not isinstance(x.get('kept'), dict))
print(json.dumps({'attempted': len(d), 'valid_responses': len(valid), 'accepted': len(kept), 'request_failures': len(failed),
                  'by_skill': {s: sum(x.get('skill') == s for x in kept) for s in ('experiment', 'experiment-reread', 'weigh', 'recovery')},
                  'rejections': reasons.most_common(12)}))
PYT
    return $RC
  fi
  if [[ $1 == correct* ]]; then  # a correction batch: $2 is a states file, one teacher turn per state (strategy/correct.py)
    $L/env/bin/python -W ignore -m aemon.teacher.corrections ask --states "$2" --url $URL --workers $W --server-settings "{\"reasoning_budget\": ${THINK:-1024}, \"context_per_slot\": ${CONTEXT:-16384}, \"slots\": $W, \"prompt_version\": \"${PROMPT_VERSION:-teacher-v1}\"}" --weights-sha256 03cf0669f0a6f338a064f264b7c54df1bb882d16860ea513727b199c1ff05b8f \
      --manifest $OUT/provenance.jsonl --output $OUT/${P}_$1.json > $OUT/${P}_$1.log 2>&1 || true
    echo "stage $P $1 ended $(date +%T): $(tail -1 $OUT/${P}_$1.log | cut -c1-200)"
    $L/env/bin/python -c "import json,sys; d=json.load(open('$OUT/${P}_$1.json')); k=sum(bool(x.get('kept')) for x in d); print(k, 'of', len(d), 'kept'); sys.exit(0 if d and k * 4 >= len(d) else 1)" || { echo "stage $P $1 failed its check"; return 1; }
    return 0
  fi
  $L/env/bin/python -W ignore -m aemon.agent.run_investigations --url $URL --prompt "${PROMPT:-teacher}" --attempts 1 --first-attempt $3 --workers $W --temperature $4 \
    --cases "$2" --context ${CONTEXT:-16384} --max-tokens "${MAX_TOKENS:-2000}" --max-turns 45 ${STATUS_CHECK:+--status-check} \
    --model-label "command-a-plus-05-2026-Q4_K_M a26ba92 code $REVISION${8:+ $8}" --server-settings "{\"reasoning_budget\": ${THINK:-1024}, \"context_per_slot\": ${CONTEXT:-16384}, \"slots\": $W, \"prompt_version\": \"${PROMPT_VERSION:-teacher-v1}\"}" --weights-sha256 03cf0669f0a6f338a064f264b7c54df1bb882d16860ea513727b199c1ff05b8f --manifest $OUT/provenance.jsonl \
    --output $OUT/${P}_$1.json > $OUT/${P}_$1.log 2>&1 || true
  echo "stage $P $1 ended $(date +%T)"
  $L/env/bin/python -m aemon.rows.stage_check $OUT/${P}_$1.json $OUT/provenance.jsonl || { echo "stage $P $1 failed its check"; return 1; }
}
take() {  # QUEUE may list several files separated by colons: the first that has a line gives it
  local q line
  for q in ${QUEUE//:/ }; do
    line=$(flock $q.lock bash -c "head -n1 $q; sed -i 1d $q")
    [ -n "$line" ] && { echo "$line"; return; }
  done
}
give_back() { local q=${QUEUE%%:*}; flock $q.lock bash -c "echo '$*' >> $q"; }
remote_worker() {
  # A second teacher on a node without home (jobs/command_a_plus_remote.sbatch), driven from here over the cluster
  # network. It takes batches from the same queue. A batch that fails goes back on the queue for the local worker.
  for i in $(seq 1 480); do curl -sf $REMOTE_URL/health > /dev/null && break; sleep 30; done
  curl -sf $REMOTE_URL/health > /dev/null || { echo "remote server never came up, local worker only"; return; }
  echo "remote server ready at $REMOTE_URL $(date +%T)"
  while [ $(date +%s) -lt $END ]; do
    LINE=$(take)
    [ -z "$LINE" ] && { echo "remote worker: queue empty $(date +%T)"; return; }
    set -- $LINE
    W=$(curl -sf -H "Authorization: Bearer $LLAMA_API_KEY" $REMOTE_URL/props | $L/env/bin/python -c "import json,sys; print(json.load(sys.stdin).get('total_slots', 1))" 2>/dev/null || echo 1)
    stage "$1" "$2" "$3" "$4" $REMOTE_URL $W ${REMOTE_NAME:-cap6} "official b12032 build on a second node" || { give_back "$LINE"; echo "remote batch $1 failed and went back on the queue, remote worker stopping"; return; }
  done
}
END=$(( $(date +%s) + ${HOURS:-22} * 3600 ))
REMOTE_PID=
# The remote server is often ready before this job's own download ends, and it stops after 45 idle minutes, so its
# harness starts now, before the download, from the code folder.
[ -n "${QUEUE:-}" ] && [ -n "${REMOTE_URL:-}" ] && { (cd $L/code_$REVISION && remote_worker) & REMOTE_PID=$!; }
PIDS=
for i in 1 2 3 4; do
  fetch $STEM-0000$i-of-00004.gguf &
  PIDS="$PIDS $!"
done
for pid in $PIDS; do wait $pid; done
echo "download done $(date +%T)"
sha256sum -c sums
if [ -n "${REBUILD:-}" ]; then
  [ -n "$BUILDER" ] && { wait $BUILDER || true; }
  if [ -x $BUILD/bin/llama-server ]; then BIN=$BUILD/bin; echo "using llama-server built for compute capability $CC"
  else echo "build for this GPU failed, using the old binary"; tail -3 $OUT/$NAME.build.log | cut -c1-200; fi
fi
start_server() {  # $1 = parallel slots. A fused CUDA kernel crashed with more than one slot in b12032, so fusion is off
  [ -n "$SERVER" ] && kill $SERVER 2>/dev/null && sleep 5
  GGML_CUDA_DISABLE_FUSION=1 $BIN/llama-server -m $D/$STEM-00001-of-00004.gguf --fit on -c $((${CONTEXT:-16384} * $1)) -t 6 --parallel $1 --reasoning-budget ${THINK:-1024} \
    --jinja --reasoning-format none --host 127.0.0.1 --port $PORT --no-webui >> $OUT/$NAME.server.log 2>&1 &
  SERVER=$!
  for i in $(seq 1 720); do
    curl -sf http://127.0.0.1:$PORT/health > /dev/null && break
    kill -0 $SERVER || { echo 'server died'; tail -8 $OUT/$NAME.server.log | cut -c1-180; return 1; }
    sleep 5
  done
  echo "server ready with $1 slots $(date +%T), code $REVISION, weights $REVISION_HF"
  nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
}
SLOTS=${WORKERS:-1}
start_server $SLOTS
cd $L/code_$REVISION
if [ -n "${QUEUE:-}" ]; then
  # Queue mode: the model loads once, then this job takes batches until the queue is empty or time is short.
  # Each line is: name cases first_attempt temperature. flock stops two workers taking the same line.
  # If the first batch fails, the server restarts with one slot and retries it, with no new download.
  FIRST_BATCH=1
  while [ $(date +%s) -lt $END ]; do
    LINE=$(take)
    [ -z "$LINE" ] && { echo "queue empty $(date +%T)"; break; }
    set -- $LINE
    if ! stage "$1" "$2" "$3" "$4"; then
      if [ $FIRST_BATCH = 1 ] && [ $SLOTS -gt 1 ]; then
        echo "falling back to one slot"
        SLOTS=1; start_server 1 || exit 1
        stage "$1_retry" "$2" "$3" "$4" || { echo "still failing with one slot, stopping"; break; }
      else
        echo "batch $1 failed, stopping"; break
      fi
    fi
    FIRST_BATCH=0
  done
  [ -n "$REMOTE_PID" ] && { echo "waiting for the remote worker"; wait $REMOTE_PID; } || true  # without a remote worker the test is false, which must not be the exit status
fi
