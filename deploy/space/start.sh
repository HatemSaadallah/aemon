#!/usr/bin/env bash
# Starts llama.cpp (base model, version 1 and version 3 adapters loaded but not applied) and the app on port 7860.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
export CODE_REVISION="$(cat REVISION 2>/dev/null || echo unknown)"
/opt/llama/llama-server -m /opt/model/tiny-aya-global-q4_k_m.gguf \
  --lora adapters/final_adapter.gguf --lora adapters/v3_adapter.gguf --lora-init-without-apply \
  -c 12288 --parallel 1 --jinja --reasoning-format none --host 127.0.0.1 --port 8091 --no-webui \
  -t "${LLAMA_THREADS:-$(nproc)}" > /tmp/llama-server.log 2>&1 &
echo "aemon demo: model server starting, app on port ${PORT:-7860}"
exec /opt/venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port "${PORT:-7860}" --app-dir app --log-level warning
