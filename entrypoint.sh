#!/usr/bin/env bash
set -euo pipefail

# ---- env defaults ----
: "${OLLAMA_MODEL:=qwen2.5:0.5b-instruct}"
: "${OLLAMA_PREPULL:=qwen2.5:0.5b-instruct}"
: "${OLLAMA_HOST:=0.0.0.0}"

echo "[entrypoint] python: $(python3 --version || true)"
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

# ---- wait for Ollama HTTP ready ----
echo -n "[entrypoint] waiting for ollama"
for i in $(seq 1 120); do
  if curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null; then
    echo " ✓"
    break
  fi
  echo -n "."
  sleep 0.5
done

# ---- build list of models to ensure available ----
# 1) All models in OLLAMA_PREPULL (comma-separated)
# 2) The primary OLLAMA_MODEL
MODEL_SET=()

# Add from OLLAMA_PREPULL
IFS=',' read -ra PREPULL_MODELS <<< "$OLLAMA_PREPULL"
for m in "${PREPULL_MODELS[@]}"; do
  m_trimmed="$(echo "$m" | xargs)"   # trim spaces
  if [ -n "$m_trimmed" ]; then
    MODEL_SET+=("$m_trimmed")
  fi
done

# Add OLLAMA_MODEL if not already present
if [ -n "$OLLAMA_MODEL" ]; then
  already=0
  for m in "${MODEL_SET[@]}"; do
    if [ "$m" = "$OLLAMA_MODEL" ]; then
      already=1
      break
    fi
  done
  if [ $already -eq 0 ]; then
    MODEL_SET+=("$OLLAMA_MODEL")
  fi
fi

# ---- ensure those models are present ----
for m in "${MODEL_SET[@]}"; do
  if [ -n "$m" ]; then
    echo "[entrypoint] ensuring model present: $m"
    if ! ollama list | awk '{print $1}' | grep -qx "$m"; then
      ollama pull "$m" || echo "[entrypoint] WARN: failed to pull $m; continuing"
    fi
  fi
done

# ---- Python app startup (no venv, deps are in system env) ----
echo "[entrypoint] starting FastAPI (uvicorn) on :8000"
exec uvicorn server:app \
  --host 0.0.0.0 --port 8000 \
  --access-log --log-level info
