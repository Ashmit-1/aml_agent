# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev dependencies)
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the application code
COPY app/ app/
COPY main.py ./

# Install the project itself
RUN uv sync --frozen --no-dev

# ── Stage 2: Production ─────────────────────────────────────────────────────
FROM python:3.12-slim AS production

# Install runtime dependencies for native extensions (numpy, xgboost, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtual environment and application from the builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY --from=builder /app/main.py /app/main.py

# Make the venv available on PATH
ENV PATH="/app/.venv/bin:$PATH"

# Set default environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

# Run with uvicorn (no --reload in production)
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
