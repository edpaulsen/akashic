# ---- Stage 1: build frontend -------------------------------------------------
FROM node:20-bookworm-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ .
RUN npm run build

# ---- Stage 2: runtime (FastAPI + static build) -------------------------------
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps (curl for healthchecks/logging)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -ms /bin/bash appuser
WORKDIR /app

# Install Python deps (keep minimal; no requirements.txt needed)
ARG PIP_PACKAGES="fastapi uvicorn[standard] rapidfuzz python-multipart"
RUN pip install --no-cache-dir $PIP_PACKAGES

# Copy backend code and data
COPY app ./app
COPY data ./data

# Copy built frontend from Stage 1
COPY --from=frontend /app/frontend/build ./frontend/build

# Ensure permissions for runtime writes (logs, learned store, etc.)
RUN mkdir -p /app/data/logs/learned && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck (simple)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/healthz || exit 1

# Start API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
