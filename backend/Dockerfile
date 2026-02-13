FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create upload directory (use Python to avoid depending on /bin/sh in edge-case bases)
RUN python3 -c "import pathlib; pathlib.Path('/app/uploads').mkdir(parents=True, exist_ok=True)"

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
