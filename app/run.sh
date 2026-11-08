#!/usr/bin/env bash
# Start the Strategy Lab on http://127.0.0.1:8000. Needs fastapi and uvicorn. Set PY to use another interpreter.
# "Try it" also needs llama-server on port 8091 serving Tiny Aya. Everything else works without it.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PY:-$here/../.venv/bin/python}"
port="${PORT:-8000}"
# Build the React frontend once if Node is installed (~/.local/node or on PATH); without it the plain pages in app/static are served.
export PATH="$HOME/.local/node/bin:$PATH"
if [ ! -f "$here/web/dist/index.html" ] && command -v npm >/dev/null; then npm --prefix "$here/web" ci && npm --prefix "$here/web" run build; fi
echo "Strategy Lab: open http://127.0.0.1:$port"
exec "$PY" -m uvicorn server:app --host 127.0.0.1 --port "$port" --app-dir "$here" --log-level warning
