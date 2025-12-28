FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module first
COPY shared ./shared

# Copy services
COPY services ./services

# Copy artifacts if they exist (trained models)
COPY artifacts ./artifacts

# Copy data folder
COPY data ./data

# Set Python path to find modules
ENV PYTHONPATH=/app

# Expose the ML service port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the mlservice with correct port
CMD ["uvicorn", "services.mlservice.main:app", "--host", "0.0.0.0", "--port", "8003"]
