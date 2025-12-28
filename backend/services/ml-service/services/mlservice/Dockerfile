FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY ../../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module
COPY ../../shared ./shared

# Copy service code
COPY . ./services/mlservice

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run the service
CMD ["uvicorn", "services.mlservice.main:app", "--host", "0.0.0.0", "--port", "8000"]
