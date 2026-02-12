# Jarvis AI Agent v2 - Production Docker Image
# Multi-stage build: Node.js for frontend, Python for backend

# ---- Stage 1: Build Next.js frontend ----
FROM node:20-slim AS frontend

WORKDIR /web
COPY web/package.json web/package-lock.json* ./
RUN npm ci --production=false
COPY web/ ./
RUN npm run build

# ---- Stage 2: Python backend + static frontend ----
FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY jarvis/ jarvis/
COPY api/ api/
COPY plugins/ plugins/
COPY agent.py config.yaml .env.example CLAUDE.md ./

# Copy built Next.js output as static files (optional fallback)
COPY --from=frontend /web/.next/static api/static/_next/static/

# Create data directories
RUN mkdir -p api/data/sessions api/data/usage api/data/webhooks \
    api/data/uploads api/data/schedules \
    memory/vector_db memory/plans logs

# Environment
ENV PYTHONUNBUFFERED=1
ENV PORT=3000
ENV JARVIS_LOG_LEVEL=INFO

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:3000/api/health || exit 1

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "3000"]
