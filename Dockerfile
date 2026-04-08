# Performance Problem Simulator - Python Edition
# Using Microsoft Container Registry (MCR) Oryx image

FROM mcr.microsoft.com/oryx/python:3.14

# Add labels for container identification
LABEL org.opencontainers.image.title="Performance Problem Simulator"
LABEL org.opencontainers.image.description="Educational tool for simulating performance problems"
LABEL org.opencontainers.image.source="https://github.com/azure-support/perf-simulator-python"

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

# Configure Oryx to run our app directly (bypasses nginx)
ENV DISABLE_ORYX_BUILD=true
ENV STARTUP_COMMAND="python -m uvicorn src.app:app --host 0.0.0.0 --port 8000"

# Expose the application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Override the oryx entrypoint and run the application directly
ENTRYPOINT []
CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
