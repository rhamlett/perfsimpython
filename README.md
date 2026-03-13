# Performance Problem Simulator - Python Edition

[![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An educational web application that intentionally creates performance problems in Python/FastAPI applications for practicing Azure App Service diagnostics. Built for Azure support engineers and developers learning to diagnose real-world performance issues.

## ⚠️ Warning

**This application is for educational purposes ONLY.** It intentionally creates:
- High CPU usage via multiprocessing workers
- Memory pressure through byte array allocations
- Thread pool starvation via synchronous blocking
- Event loop blocking (async anti-pattern demonstration)
- Slow responses and application crashes

**Do NOT deploy to production environments or shared infrastructure.**

## 🚀 Quick Start

### Prerequisites

- Python 3.14 or higher
- pip (Python package manager)

### Local Development

```bash
# Clone the repository
git clone https://github.com/azure-support/perf-simulator-python.git
cd perf-simulator-python

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn src.main:app --reload

# Open http://localhost:8000 in your browser
```

### Using Docker

```bash
# Build the image
docker build -t perf-simulator-python .

# Run the container
docker run -p 8000:8000 perf-simulator-python

# Open http://localhost:8000
```

## 📊 Features

### Dashboard

The real-time dashboard provides:
- Live CPU and memory metrics via WebSocket (500ms updates)
- Interactive charts using Chart.js
- Simulation control panel
- Event log for tracking operations

### Performance Simulations

| Simulation | API Endpoint | Diagnostic Signature |
|------------|--------------|---------------------|
| CPU Stress | `POST /api/cpu/start` | High CPU %, visible in py-spy |
| Memory Pressure | `POST /api/memory/allocate` | Growing memory, tracemalloc |
| Sync Blocking | `POST /api/blocking/sync` | Thread pool exhaustion |
| Async Blocking | `POST /api/blocking/async` | Event loop freeze (anti-pattern) |
| Slow Requests | `GET /api/slow?delay_seconds=5` | Latency spikes |
| Crashes | `POST /api/crash` | Process termination |

### Documentation

- `/docs.html` - Complete API reference
- `/azure-diagnostics.html` - Azure diagnostic tools guide
- `/azure-deployment.html` - Deployment instructions

## 🏗️ Project Structure

```
├── src/
│   ├── config/          # Settings with env var support
│   ├── models/          # Pydantic models and entities
│   ├── routers/         # API endpoint handlers
│   ├── services/        # Business logic and simulations
│   ├── middleware/      # Error handling, logging
│   ├── websocket/       # Real-time metrics broadcast
│   ├── static/          # Dashboard HTML/CSS/JS
│   ├── app.py           # FastAPI application factory
│   └── main.py          # ASGI entry point
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── docs/                # Documentation files
│   └── simulations/     # Per-simulation guides
├── .github/workflows/   # CI/CD pipelines
├── Dockerfile           # Container configuration
├── pyproject.toml       # Project metadata
└── requirements.txt     # Dependencies
```

## ⚙️ Configuration

Environment variables (can be set in `.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/production) | development |
| `LOG_LEVEL` | Logging verbosity | INFO |
| `HOST` | Server bind address | 0.0.0.0 |
| `PORT` | Server port | 8000 |

## 🧪 Development

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html --cov-report=term

# Unit tests only
pytest tests/unit/

# Integration tests only
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

## ☁️ Azure Deployment

This application is designed for deployment to Azure App Service for educational diagnostics practice.

### GitHub Actions (Recommended)

The repository includes CI/CD workflows for automated deployment using Azure OIDC (no secrets required):

1. Create an Azure App Service
2. Set up Workload Identity Federation
3. Configure repository secrets
4. Push to trigger deployment

See [Deployment Guide](src/static/azure-deployment.html) for detailed instructions.

### Manual Deployment

```bash
# Deploy using Azure CLI
az webapp up \
  --runtime "PYTHON:3.14" \
  --name your-app-name \
  --resource-group your-rg
```

## 📚 Documentation

### Online (in app)
- Dashboard: http://localhost:8000/
- API Docs (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Documentation: http://localhost:8000/docs.html

### Markdown Documentation
- [Project Overview](docs/README.md)
- [Azure Diagnostics Guide](docs/azure-diagnostics.md)
- [Linux Tools Guide](docs/linux-tools.md)
- Simulation Guides:
  - [CPU Stress](docs/simulations/cpu-stress.md)
  - [Memory Pressure](docs/simulations/memory-pressure.md)
  - [Thread Blocking](docs/simulations/thread-blocking.md)
  - [Async Blocking](docs/simulations/async-blocking.md)
  - [Slow Requests](docs/simulations/slow-requests.md)
  - [Crash Simulation](docs/simulations/crash-simulation.md)

## 🔧 Diagnostic Practice

### Recommended Workflow

1. **Deploy to Azure App Service** with Application Insights enabled
2. **Establish baseline** - Record normal metrics
3. **Trigger a simulation** - Use the dashboard or API
4. **Investigate in Azure Portal**:
   - App Service Diagnostics
   - Application Insights Performance
   - Azure Monitor Metrics
5. **Correlate findings** with the simulation
6. **Document the diagnostic path** for team training

### Azure Tools Covered

- **App Service Diagnostics** - Built-in problem detection
- **Application Insights** - APM, distributed tracing, Live Metrics
- **Azure Monitor** - Metrics, alerts, Log Analytics
- **Kudu** - SSH access, process explorer, log streaming
- **py-spy** - Python profiler for production use
- **tracemalloc** - Memory allocation tracking

## 🤝 Contributing

This is an educational tool for Azure support engineers. Contributions that improve diagnostic scenarios or educational content are welcome.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

**Note**: This application is part of the Azure Support engineering training materials. For questions or issues, contact the Azure Support Tools team.
