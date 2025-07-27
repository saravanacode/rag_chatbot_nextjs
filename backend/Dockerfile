# Use a minimal Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Improve pip reliability
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_RETRIES=5

# Copy requirements.txt and install Python packages
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-deps torch==2.1.0+cpu torchvision==0.16.0+cpu torchaudio==2.1.0+cpu \
        --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt

# Copy application code (everything in backend including app/)
COPY . .

# Set user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose Flask port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Start Flask app using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "app.backend_server:app"]
