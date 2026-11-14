#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/python ops/refresh_local.py
elif [ ! -d frontend/dist ]; then
  .venv/bin/python ops/refresh_local.py
fi
exec .venv/bin/python ops/start_local.py "$@"
