# Minimal, from Ubuntu, with uv + Ollama; app code is bind-mounted at runtime.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OLLAMA_HOST=0.0.0.0

# base system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    python3 python3-venv python3-pip \
    tini \
 && rm -rf /var/lib/apt/lists/*

# install uv (fast py manager/venv)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# install Ollama (CPU/GPU handled by host runtime libs)
RUN curl -fsSL https://ollama.com/install.sh | sh

# working dir; code will be bind-mounted here by compose
WORKDIR /app

# expose FastAPI and Ollama
EXPOSE 8000 11434

# use tini for clean signals; entrypoint does uv venv + pip install + serve
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/entrypoint.sh"]
