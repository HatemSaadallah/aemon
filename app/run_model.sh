#!/usr/bin/env bash
# Serves Tiny Aya on this laptop for Try it: the quantized base, plus every trained adapter present, in a fixed order.
# Adapters are loaded but not applied; each request switches on at most one, so every choice shares one base and runtime.
set -euo pipefail
B=$HOME/.cache/lexsi/llama-b12032
M=$HOME/.cache/huggingface/hub/models--CohereLabs--tiny-aya-global-GGUF/snapshots/a602ea7eeec3a4ad6f77a1b8cf6a53512824922b/tiny-aya-global-q4_k_m.gguf
A=$HOME/.cache/lexsi/adapters
EXTRA=()
for name in first_adapter.gguf second_adapter.gguf; do
  [ -f "$A/$name" ] && EXTRA+=(--lora "$A/$name") && echo "with adapter $name"
done
[ ${#EXTRA[@]} -gt 0 ] && EXTRA+=(--lora-init-without-apply)
# 12288 because the first adapter runs with full history; compact runs stay under about 6,000 tokens.
cd $B && LD_LIBRARY_PATH=$B exec ./llama-server -m $M "${EXTRA[@]}" -ngl 99 -c 12288 --parallel 1 --jinja --reasoning-format none --host 127.0.0.1 --port 8091 --no-webui
