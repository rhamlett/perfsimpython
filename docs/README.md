# Performance Problem Simulator - Python Edition

An educational web application that intentionally creates performance problems for practicing Azure App Service diagnostics. This tool helps Azure support engineers and developers learn to identify and diagnose common performance issues using Azure's monitoring tools.

## ⚠️ Warning

**This application is for educational purposes ONLY.** It intentionally creates performance problems including:
- High CPU usage
- Memory pressure  
- Thread pool starvation
- Event loop blocking
- Slow responses
- Application crashes

**Do NOT deploy to production environments or shared infrastructure.**

## Quick Start

### Prerequisites

- Python 3.14+
- pip

### Local Development

```bash
# Clone the repository
git clone https://github.com/azure-support/perf-simulator-python.git
cd perf-simulator-python

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn src.main:app --reload

# Open http://localhost:8000
```

### Using Docker

```bash
# Build the image
docker build -t perf-simulator-python .

# Run the container
docker run -p 8000:8000 perf-simulator-python
```

## Features

### Performance Simulations

| Simulation | Description | Diagnostic Signature |
|------------|-------------|---------------------|
| CPU Stress | Multiprocessing workers doing floating-point math | High CPU in metrics, visible in py-spy |
| Memory Pressure | Byte array allocations | Memory growth, tracemalloc shows allocations |
| Sync Blocking | Thread pool starvation via time.sleep() | Increased latency, thread pool exhaustion |
| Async Blocking | Event loop blocking (anti-pattern) | All requests slow simultaneously |
| Slow Requests | Artificial delays | Latency spikes in App Insights |
| Crashes | Various crash types | Different exit codes and logs |

### Real-Time Dashboard

- Live metrics via WebSocket (500ms updates)
- CPU and memory charts
- Simulation controls
- Event log

### API Endpoints

All endpoints are prefixed with `/api`. See the [API Documentation](/docs.html) for details.

- `GET /api/health` - Health check
- `GET /api/metrics` - Current metrics
- `POST /api/cpu/start` - Start CPU stress
- `POST /api/memory/allocate` - Allocate memory
- `POST /api/blocking/sync` - Trigger sync blocking
- `GET /api/slow` - Slow response
- `POST /api/crash` - Trigger crash (requires confirmation)

## Project Structure

```
├── src/
│   ├── config/          # Settings and configuration
│   ├── models/          # Pydantic models and entities
│   ├── routers/         # API endpoint handlers
│   ├── services/        # Business logic
│   ├── middleware/      # Request logging and error handling
│   ├── websocket/       # WebSocket connection management
│   ├── static/          # Dashboard HTML/CSS/JS
│   ├── app.py           # FastAPI application factory
│   └── main.py          # ASGI entry point
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── docs/                # Documentation
├── .github/workflows/   # CI/CD pipelines
├── Dockerfile           # Container build
├── pyproject.toml       # Project metadata
└── requirements.txt     # Dependencies
```

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/production) | development |
| `LOG_LEVEL` | Logging level | INFO |

## Documentation

- [API Reference](docs.html)
- [Azure Diagnostics Guide](azure-diagnostics.html)
- [Deployment Guide](azure-deployment.html)

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black src tests

# Lint
ruff check src tests

# Type check
mypy src
```

## Deployment

See the [Deployment Guide](azure-deployment.html) for detailed instructions on deploying to Azure App Service with GitHub Actions and OIDC authentication.

## License

MIT License - See LICENSE file

## Contributing

This is an educational tool for Azure support engineers. Contributions that improve the diagnostic scenarios or educational content are welcome.
