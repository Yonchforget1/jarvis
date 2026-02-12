# Jarvis AI Agent - Production Docker Image
# Serves FastAPI backend with built-in chat UI on port 3000

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
COPY agent.py config.yaml CLAUDE.md ./

# Create data directories
RUN mkdir -p api/data/sessions memory/vector_db memory

# Environment
ENV PYTHONUNBUFFERED=1
ENV PORT=3000

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:3000/api/health || exit 1

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "3000"]
