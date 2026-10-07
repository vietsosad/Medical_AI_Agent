# ---- Stage 1: Build ----
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Stage 2: Production ----
FROM python:3.11-slim

WORKDIR /app

# Unicode font required by ReportLab for professional Vietnamese SBAR exports.
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Security: create non-root user first
RUN useradd -m appuser

# Copy installed packages from builder to appuser's home directory
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code with ownership
COPY --chown=appuser:appuser . .

# Create data directory with correct ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Shell form so ${PORT} expands: Cloud Run/Render/Railway inject PORT and
# expect the container to listen on it instead of a fixed 8000.
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", 8000)}/health')" || exit 1

# `exec` replaces the shell process so SIGTERM reaches uvicorn directly,
# letting the app's lifespan shutdown (DB pool disposal) run instead of
# being force-killed after the shell swallows the signal.
CMD exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
