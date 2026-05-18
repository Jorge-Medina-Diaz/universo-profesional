FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:/root/.local/bin:${PATH}"

# WeasyPrint system dependencies (Cairo, Pango, gdk-pixbuf) + build tools for asyncpg/psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    (mv /root/.local/bin/uvx /usr/local/bin/uvx || true)

WORKDIR /app

# Install deps into /opt/venv (outside /app so docker-compose bind-mount doesn't shadow them)
COPY pyproject.toml uv.lock* ./
RUN uv venv /opt/venv && \
    uv sync --frozen --no-install-project || uv sync --no-install-project

# App source is bind-mounted in dev; copied for prod images
COPY . /app

# Create var directory for keys + documents
RUN mkdir -p /app/var/keys /app/var/documents

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
