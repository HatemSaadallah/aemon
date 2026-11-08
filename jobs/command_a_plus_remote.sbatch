#!/bin/bash
#SBATCH --job-name=teacher-remote
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --gres=gpu:7g.80gb:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=200G
#SBATCH --time=23:30:00
#SBATCH --chdir=/tmp
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
# Command A+ served from a node that cannot see the home filesystem. NO TRAINING, and nothing here reads or writes home.
# Slurm keeps this script; the model, the llama.cpp source and cmake come from the internet into node memory, and CUDA from
# /software. llama.cpp is built here for this GPU: the official binaries need glibc 2.38, and the cluster has 2.34.
# Each step is posted as this job's Slurm comment (squeue -o %k), the only status channel, since there is no log.
# The harness runs in another job and reaches this server over the cluster network with KEY. PORT can be fixed so a
# harness already waiting finds it. The server stops itself after IDLE minutes with no requests.
# Submit with: KEY=... PORT=... sbatch --nodelist=gnode04 --export=ALL command_a_plus_remote.sbatch
set -uo pipefail
PORT=${PORT:-$((20000 + SLURM_JOB_ID % 20000))}
D=/dev/shm/lexsi-remote-$SLURM_JOB_ID  # the model: data only. /dev/shm is mounted noexec on these nodes
X=/tmp/lexsi-remote-$SLURM_JOB_ID      # cmake and the build: programs must run from the node's own disk
REPO=bartowski/command-a-plus-05-2026-GGUF
REVISION_HF=a26ba921242484b5e1a8ac8519169fe7421c3ab3
STEM=command-a-plus-05-2026-Q4_K_M
CUDA=/software/cuda/12.8
mkdir -p $D $X
cleanup() { kill $(jobs -p) 2>/dev/null; rm -rf "$D" "$X"; }
trap cleanup EXIT
say() { scontrol update JobId=$SLURM_JOB_ID Comment="$(date +%H:%M) $(echo "$*" | tr -c 'A-Za-z0-9.:,=_/ -' '_' | cut -c1-180)" 2>/dev/null || true; }
fail() { say "FAILED: $*"; sleep 900; exit 1; }  # Slurm drops the comment once the job ends, so it stays readable for 15 minutes
say "started on $(hostname), port $PORT"
[ -x $CUDA/bin/nvcc ] || fail "no CUDA at $CUDA"
nvidia-smi > /dev/null 2>&1 || fail "no GPU visible"
printf '#!/bin/sh\necho ok\n' > $X/probe && chmod +x $X/probe && [ "$($X/probe 2>/dev/null)" = ok ] || fail "cannot run programs from $X"
cat > $D/sums <<SUMS
03cf0669f0a6f338a064f264b7c54df1bb882d16860ea513727b199c1ff05b8f  $STEM-00001-of-00004.gguf
97c859c036a6a8a4cd02e4d57aaea7fed94642058ba714ab7ccce95acfff0fa5  $STEM-00002-of-00004.gguf
9ffbedb12dc63f09b84e9e85636607e26f95426fd10947d582ab89e5f0e05e7c  $STEM-00003-of-00004.gguf
b429a070fb15f53e2b6e1417942c507fc03958db6e6a547846277b60ac2012e2  $STEM-00004-of-00004.gguf
SUMS
cd $D
fetch() {  # url, file: a dropped transfer resumes where it stopped
  for attempt in $(seq 12); do curl -fsSL -C - -o "$2" "$1" && return 0; sleep 20; done
  return 1
}
PIDS=
for i in 1 2 3 4; do fetch "https://huggingface.co/$REPO/resolve/$REVISION_HF/$STEM/$STEM-0000$i-of-00004.gguf" $STEM-0000$i-of-00004.gguf & PIDS="$PIDS $!"; done
(  # built while the model downloads: the same source as the other node, for compute capability 8.0, linked statically
  cd $X && fetch https://github.com/Kitware/CMake/releases/download/v3.30.5/cmake-3.30.5-linux-x86_64.tar.gz cmake.tar.gz && tar -xzf cmake.tar.gz \
  && fetch https://github.com/ggml-org/llama.cpp/archive/refs/tags/b12032.tar.gz src.tar.gz && tar -xzf src.tar.gz \
  && export PATH=$X/cmake-3.30.5-linux-x86_64/bin:$CUDA/bin:$PATH LD_LIBRARY_PATH=$CUDA/lib:${LD_LIBRARY_PATH:-} \
  && cd llama.cpp-b12032 && cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=80 -DBUILD_SHARED_LIBS=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF \
       -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF -DCMAKE_BUILD_TYPE=Release > $D/cmake.log 2>&1 \
  && cmake --build build --target llama-server -j 6 > $D/build.log 2>&1
) &
BUILDER=$!
say "downloading the model and building llama.cpp"
wait $BUILDER || fail "build: $(tail -2 $D/build.log $D/cmake.log 2>/dev/null | tr '\n' ' ' | cut -c1-150)"
say "built llama.cpp, waiting for the model download"
SERVER_BIN=$X/llama.cpp-b12032/build/bin/llama-server
[ -x $SERVER_BIN ] || fail "no llama-server after the build"
for pid in $PIDS; do wait $pid || fail "model download"; done
sha256sum -c sums > /dev/null 2>&1 || fail "model checksum"
SLOTS=${WORKERS:-4}
start_server() {
  LD_LIBRARY_PATH=$CUDA/lib $SERVER_BIN -m $D/$STEM-00001-of-00004.gguf --fit on -c $((${CONTEXT:-16384} * SLOTS)) -t 6 --parallel $SLOTS --reasoning-budget ${THINK:-1024} \
    --jinja --reasoning-format none --host 0.0.0.0 --port $PORT --api-key "$KEY" --no-webui >> $D/server.log 2>&1 &
  SERVER=$!
  for i in $(seq 720); do curl -sf http://127.0.0.1:$PORT/health > /dev/null && break; kill -0 $SERVER || { say "server died: $(grep -m1 -i 'error\|fail' $D/server.log | cut -c1-120)"; return 1; }; sleep 5; done
  say "ready with $SLOTS slots on port $PORT, weights $REVISION_HF, built b12032 sm80"
}
start_server || { SLOTS=1; start_server || fail "server would not start with one slot"; }
LAST=$(date +%s)
while true; do  # stop once the harness has been silent for IDLE minutes, so the GPU is never held for nothing
  sleep 60
  if ! kill -0 $SERVER 2>/dev/null; then  # a crash with parallel slots: one restart with one slot, which the harness reads from /props
    [ $SLOTS -gt 1 ] && { SLOTS=1; say "server stopped, restarting with one slot"; start_server && { LAST=$(date +%s); continue; }; }
    fail "server stopped: $(grep -m1 'CUDA error\|ggml_abort' $D/server.log | cut -c1-120)"
  fi
  N=$(grep -c "launch_slot_" $D/server.log)
  [ "$N" != "${SEEN:-0}" ] && { SEEN=$N; LAST=$(date +%s); }
  [ $(( $(date +%s) - ${SAID:-0} )) -ge 600 ] && { SAID=$(date +%s); say "serving: ${SEEN:-0} requests so far, $SLOTS slots"; }  # every 10 minutes, to spare the controller
  [ $(( $(date +%s) - LAST )) -gt $(( ${IDLE:-45} * 60 )) ] && { say "idle for ${IDLE:-45} minutes, stopped"; break; }
done
