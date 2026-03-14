# Performance Problem Simulator - Python Edition
# Multi-stage build for optimal image size
# Using Microsoft Container Registry (MCR) blessed image

# Stage 1: Build dependencies
FROM mcr.microsoft.com/oryx/python:3.12 as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM mcr.microsoft.com/oryx/python:3.12

# Add labels for container identification
LABEL org.opencontainers.image.title="Performance Problem Simulator"
LABEL org.opencontainers.image.description="Educational tool for simulating performance problems"
LABEL org.opencontainers.image.source="https://github.com/azure-support/perf-simulator-python"

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY src/ ./src/
COPY docs/ ./docs/

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_ENV=production
ENV PORT=8000

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
