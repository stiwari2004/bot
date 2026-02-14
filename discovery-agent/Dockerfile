# Customer-facing discovery agent image. Dependencies are installed at build time;
# at runtime the container only runs discovery (no pip, no venv).
# Build (from repo root): docker build -f discovery-agent/Dockerfile -t resolvify-discovery-agent discovery-agent
# Or: cd discovery-agent && docker build -t resolvify-discovery-agent .
#
# Run (customer passes ingest URL and token; license activation is handled by your backend):
#   docker run --rm -e DISCOVERY_INGEST_URL=https://your-app/api/v1/tenant-admin/discovery/ingest -e DISCOVERY_TOKEN=YOUR_TOKEN resolvify-discovery-agent
#
# For network discovery (ping sweep) from inside the container, use host network on Linux:
#   docker run --rm --network host -e DISCOVERY_INGEST_URL=... -e DISCOVERY_TOKEN=... resolvify-discovery-agent
# Or add capability: --cap-add=NET_RAW (slim image may still need ping installed; prefer --network host for jump-server use).

FROM python:3.11-slim

WORKDIR /app

# Dependencies installed at build time (no runtime install)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Agent code (no .venv or __pycache__ - see .dockerignore)
COPY . .

# Default: auto-scan (ping sweep + fingerprint + full inventory when run on jump server)
ENV DISCOVERY_AUTO_SCAN=1

# Customer provides DISCOVERY_INGEST_URL and DISCOVERY_TOKEN at run time
ENTRYPOINT ["python", "run.py"]
