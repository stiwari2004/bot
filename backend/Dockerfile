# Build from repo root to include discovery-agent (agent.tar.gz / agent.zip endpoints):
#   docker build -f backend/Dockerfile -t backend .
# Without discovery-agent, /api/v1/tenant-admin/discovery/agent.tar.gz returns 404.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# When context is repo root (recommended): copy backend and discovery-agent
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY discovery-agent /app/discovery-agent

# Create upload directory (use exec form so no /bin/sh required)
RUN ["python3", "-c", "import pathlib; pathlib.Path('/app/uploads').mkdir(parents=True, exist_ok=True)"]

# Create non-root user for security (MF-8) — exec form so no /bin/sh required
RUN ["useradd", "-m", "-u", "1000", "appuser"]
RUN ["chown", "-R", "appuser:appuser", "/app"]
RUN ["chown", "-R", "appuser:appuser", "/app/uploads"]

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
