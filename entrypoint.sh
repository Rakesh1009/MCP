#!/usr/bin/env bash
set -euo pipefail

# ---- env defaults ----
: "${OLLAMA_MODEL:=qwen2.5:0.5b-instruct}"
: "${OLLAMA_PREPULL:=qwen2.5:0.5b-instruct}"
: "${OLLAMA_HOST:=0.0.0.0}"

echo "[entrypoint] python: $(python3 --version)"
echo "[entrypoint] uv: $(uv --version || true)"
echo "[entrypoint] starting ollama..."
ollama serve &
OLLAMA_PID=$!

cleanup() {
  echo "[entrypoint] shutting down..."
  kill -TERM "$OLLAMA_PID" 2>/dev/null || true
  wait "$OLLAMA_PID" 2>/dev/null || true
}
trap cleanup INT TERM

# Wait for Ollama HTTP ready
echo -n "[entrypoint] waiting for ollama"
for i in $(seq 1 120); do
  if curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null; then
    echo " ✓"
    break
  fi
  echo -n "."
  sleep 0.5
done

# Pre-pull exactly one tiny model (fast!)
IFS=',' read -ra MODELS <<< "$OLLAMA_PREPULL"
for m in "${MODELS[@]}"; do
  m_trimmed="$(echo "$m" | xargs)"
  if [ -n "$m_trimmed" ]; then
    echo "[entrypoint] ensuring model present: $m_trimmed"
    if ! ollama list | awk '{print $1}' | grep -qx "$m_trimmed"; then
      ollama pull "$m_trimmed" || echo "[entrypoint] WARN: failed to pull $m_trimmed; continuing"
    fi
  fi
done

# ---- Python setup with uv venv (inside /app) ----
if [ ! -d "/app/.venv" ]; then
  echo "[entrypoint] creating venv at /app/.venv"
  uv venv /app/.venv
fi
export PATH="/app/.venv/bin:${PATH}"

if [ -f /app/requirements.txt ]; then
  echo "[entrypoint] installing python deps via uv pip"
  uv pip install -r /app/requirements.txt
fi

echo "[entrypoint] starting FastAPI (uvicorn) on :8000"
exec uvicorn server:app \
  --host 0.0.0.0 --port 8000 \
  --access-log --log-level info

