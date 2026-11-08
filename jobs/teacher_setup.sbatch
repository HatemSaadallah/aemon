#!/bin/bash
#SBATCH --job-name=teacher-setup
#SBATCH --partition=stud
#SBATCH --qos=stud
#SBATCH --account=CLUSTER_ACCOUNT
#SBATCH --cpus-per-task=6
#SBATCH --mem=24G
#SBATCH --time=03:00:00
#SBATCH --output=%x-%j.out
# Fetches the quantized teacher and builds llama-server for CUDA. NO TRAINING, and no token needed:
# this GGUF is an ungated third-party quantization of the official weights, pinned by revision and hash.
set -euo pipefail
L=$HOME/lexsi
export PYTHONPATH=$L/code_${REVISION:-unset}/src  # the package, from this job's own copy of the code
REVISION=3acdc2838db0bc64d2371f6b7d0eafab50fdbb0f
FILE=aya-expanse-32b-Q4_K_M.gguf
WANT=47eed19801ed865fabad06f7c0eb4b079b874281a8caac486f99300c7bf525f9
mkdir -p $L/models/aya-expanse-32b-gguf $L/tools
cd $L/models/aya-expanse-32b-gguf
if [ ! -f $FILE.provenance ]; then
  echo "node $(hostname), download starts $(date +%T)"
  curl -fL --retry 8 --retry-delay 20 -C - -o $FILE "https://huggingface.co/bartowski/aya-expanse-32b-GGUF/resolve/$REVISION/$FILE"
  echo "$WANT  $FILE" | sha256sum -c -
  echo "$REVISION $WANT" > $FILE.provenance
fi
type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh  # a job submitted with env -i has no module function
module load cuda/12.8
$L/env/bin/python -m pip install --quiet --target $L/tools/cmake cmake
export PATH=$L/tools/cmake/bin:$PATH PYTHONPATH=$L/tools/cmake
cmake --version | head -1
cd $L
[ -d llama.cpp ] || git clone --quiet --depth 1 --branch b12032 https://github.com/ggml-org/llama.cpp llama.cpp
cd llama.cpp
echo "llama.cpp $(git rev-parse --short=9 HEAD)"
rm -rf build
cmake -B build -DGGML_CUDA=ON -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF -DBUILD_SHARED_LIBS=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON -DCMAKE_BUILD_TYPE=Release > $L/logs/llama-cmake.log 2>&1
cmake --build build --target llama-server -j 6 > $L/logs/llama-build.log 2>&1
ls -la build/bin/llama-server
echo "setup finished $(date +%T)"
