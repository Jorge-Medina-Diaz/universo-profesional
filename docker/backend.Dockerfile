FROM python:3.13-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:/root/.local/bin:${PATH}"

# WeasyPrint system deps (Cairo, Pango, gdk-pixbuf) + curl for healthcheck.
# Build-essential goes only in the builder stage so the runtime image stays slim.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*


# ---------- Builder ----------
FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    (mv /root/.local/bin/uvx /usr/local/bin/uvx || true)

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv venv /opt/venv && \
    uv sync --frozen --no-install-project || uv sync --no-install-project


# ---------- Runtime ----------
FROM base AS runtime

# Create a non-root user and give it ownership of the writable paths. The
# UID is fixed (1001) so file ownership stays predictable when volumes are
# mounted from the host.
RUN groupadd --system --gid 1001 app && \
    useradd --system --uid 1001 --gid 1001 --home-dir /app --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# App source. In dev, docker-compose bind-mounts over this; in prod it's
# part of the immutable image.
COPY --chown=app:app . /app

# /app/var is the only writable runtime dir — JWT keys + document storage.
# In prod we mount a persistent volume here.
RUN mkdir -p /app/var/keys /app/var/documents && chown -R app:app /app/var

USER app

EXPOSE 8000

# Container-native healthcheck used by docker-compose. Fly.io / K8s probes
# use /readyz directly via HTTP — this is the local-dev convenience.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
