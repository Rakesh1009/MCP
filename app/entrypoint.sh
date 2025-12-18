#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] python: $(python --version)"
echo "[entrypoint] starting FastAPI on :8000"

exec uvicorn main:app --host 0.0.0.0 --port 8000
