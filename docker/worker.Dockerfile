FROM python:3.13-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:/root/.local/bin:${PATH}"

# Same runtime libs as the backend so the worker can render WeasyPrint PDFs.
# `procps` provides `pgrep`, used by the HEALTHCHECK below.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    procps \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*


FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv venv /opt/venv && \
    uv sync --frozen --no-install-project || uv sync --no-install-project


FROM base AS runtime

RUN groupadd --system --gid 1001 app && \
    useradd --system --uid 1001 --gid 1001 --home-dir /app --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app . /app

RUN mkdir -p /app/var/keys /app/var/documents && chown -R app:app /app/var

USER app

# Liveness via arq's own health check: the worker writes a health key to Redis
# every health_check_interval (30s); `arq --check` reads it and exits non-zero
# when the job loop is stalled — a real liveness signal, not just "process alive".
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD arq --check src.shared.worker.WorkerSettings || exit 1

CMD ["arq", "src.shared.worker.WorkerSettings"]
