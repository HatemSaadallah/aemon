#!/usr/bin/env bash
# Start Aemon on http://127.0.0.1:8000. Needs fastapi and uvicorn. Set PY to use another interpreter.
# "Try it" also needs llama-server on port 8091 serving Tiny Aya. Everything else works without it.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PY:-$here/../.venv/bin/python}"
port="${PORT:-8000}"
# Build the React frontend once; it needs Node (~/.local/node or on PATH)
export PATH="$HOME/.local/node/bin:$PATH"
if [ ! -f "$here/web/dist/index.html" ]; then
  command -v npm >/dev/null || { echo "Aemon needs Node.js to build its interface once: install it, then run this again." >&2; exit 1; }
  npm --prefix "$here/web" ci && npm --prefix "$here/web" run build
fi
echo "Aemon: open http://127.0.0.1:$port"
exec "$PY" -m uvicorn server:app --host 127.0.0.1 --port "$port" --app-dir "$here" --log-level warning
