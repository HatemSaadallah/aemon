#!/usr/bin/env bash
# Runs every test suite. Uses no GPU, no model, and no network.
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
.venv/bin/python -W ignore -m pytest tests -q --no-header -p no:cacheprovider
(cd app && ../.venv/bin/python -W ignore -m pytest test_api.py test_auth.py -q --no-header -p no:cacheprovider)
echo "All suites passed."
