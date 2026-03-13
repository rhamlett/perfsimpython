# Implementation Plan: Performance Problem Simulator

**Branch**: `001-perf-simulator-python` | **Date**: 2026-03-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-perf-simulator-python/spec.md`

## Summary

Build an educational Python application that intentionally triggers controllable performance
problems (CPU stress, memory pressure, synchronous blocking, async blocking, slow requests, crashes)
to help Azure support engineers practice diagnostics. The application includes a REST API for
triggering simulations, a real-time WebSocket-powered dashboard for observing metrics, and
built-in documentation for Azure diagnostic tools.

## Technical Context

**Language/Version**: Python 3.11+ with type hints throughout  
**Primary Dependencies**: FastAPI (HTTP server + WebSocket), Uvicorn (ASGI server), Pydantic (validation), Chart.js (frontend charts)  
**Storage**: N/A (in-memory only, no persistence required per spec)  
**Testing**: pytest with pytest-asyncio for async tests, pytest-cov for coverage  
**Target Platform**: Azure App Service Linux (Python 3.11 blessed image)  
**Project Type**: Single project with embedded static frontend (no build step for frontend)  
**Performance Goals**: Dashboard metrics update within 2 seconds; API responses within 2 seconds  
**Constraints**: Maximum 10 concurrent dashboard users; no simulation duration limits (intentional for stress testing)  
**Scale/Scope**: Single principal user (support engineer) in sandboxed test environment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Plan Compliance | Status |
|-----------|-------------|-----------------|--------|
| I. Code Quality & Readability | Descriptive names, single responsibility, no magic numbers | All services will have clear names (cpu_stress_service, metrics_collector); constants in config module | ✅ Pass |
| II. Documentation-First | Docstrings for all exports, README files | Every service/router gets docstrings; README at root and /docs for guides | ✅ Pass |
| III. TDD (Encouraged) | Tests before implementation when practical | Unit tests for services; integration tests for API endpoints | ✅ Pass |
| IV. Simplicity & YAGNI | Minimal abstractions, standard library when possible | No ORM (no DB), minimal dependencies, vanilla JS frontend | ✅ Pass |
| V. Defensive Programming | Parameter validation, error handling, type hints | Pydantic models for validation, type hints throughout, structured logging | ✅ Pass |

**Technology Standards Compliance**:
- Python 3.11+ with type hints: ✅ Will use throughout
- Black + Ruff: ✅ Will configure in pyproject.toml
- pytest for testing: ✅ Selected with pytest-asyncio
- FastAPI: ✅ Selected for async support and automatic OpenAPI

**Gate Result**: ✅ PASS - No violations requiring justification

## Project Structure

### Documentation (this feature)

```text
specs/001-perf-simulator-python/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI spec)
│   └── openapi.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── main.py                         # Application entry point (uvicorn target)
├── app.py                          # FastAPI app configuration
├── config/
│   ├── __init__.py
│   └── settings.py                 # Environment and default configuration (Pydantic Settings)
├── routers/
│   ├── __init__.py
│   ├── health.py                   # Health check endpoints
│   ├── metrics.py                  # System metrics endpoints
│   ├── cpu.py                      # CPU stress simulation endpoints
│   ├── memory.py                   # Memory pressure endpoints
│   ├── blocking.py                 # Thread/async blocking endpoints
│   ├── slow.py                     # Slow request simulation
│   ├── crash.py                    # Crash simulation endpoints
│   └── admin.py                    # Admin/status endpoints
├── services/
│   ├── __init__.py
│   ├── metrics_service.py          # System metrics collection (psutil-based)
│   ├── cpu_stress_service.py       # CPU stress simulation logic
│   ├── memory_pressure_service.py  # Memory allocation/release logic
│   ├── blocking_service.py         # Thread/async blocking logic
│   ├── slow_request_service.py     # Configurable delay logic
│   ├── crash_service.py            # Crash trigger logic
│   ├── simulation_tracker.py       # Track active simulations
│   └── event_log_service.py        # Simulation event logging
├── models/
│   ├── __init__.py
│   ├── requests.py                 # Pydantic request models
│   ├── responses.py                # Pydantic response models
│   └── entities.py                 # Domain entities
├── middleware/
│   ├── __init__.py
│   ├── error_handler.py            # Global exception handling
│   └── request_logger.py           # Request logging middleware
├── websocket/
│   ├── __init__.py
│   └── metrics_broadcaster.py      # WebSocket connection manager
└── static/
    ├── index.html                  # Dashboard HTML (main page)
    ├── docs.html                   # Documentation page (API reference & guides)
    ├── azure-diagnostics.html      # Azure diagnostics guide page
    ├── azure-deployment.html       # Deploy to Azure guide (GitHub Actions + OIDC)
    ├── favicon.svg                 # Application favicon
    ├── css/
    │   └── styles.css              # Dashboard styles (shared CSS matching Node/.NET versions)
    └── js/
        ├── dashboard.js            # Dashboard logic (vanilla JS)
        ├── charts.js               # Chart.js integration
        └── websocket-client.js     # WebSocket client

tests/
├── __init__.py
├── conftest.py                     # pytest fixtures
├── unit/
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── test_metrics_service.py
│   │   ├── test_cpu_stress_service.py
│   │   ├── test_memory_pressure_service.py
│   │   ├── test_blocking_service.py
│   │   └── test_simulation_tracker.py
│   └── routers/
│       ├── __init__.py
│       └── test_health.py
└── integration/
    ├── __init__.py
    ├── test_api.py                 # Full API endpoint tests
    └── test_websocket.py           # WebSocket connection tests

docs/
├── README.md                       # Project overview and quickstart
├── azure-diagnostics.md            # Azure diagnostic tools guide
├── linux-tools.md                  # Linux CLI diagnostic tools
└── simulations/
    ├── cpu-stress.md
    ├── memory-pressure.md
    ├── thread-blocking.md
    ├── async-blocking.md
    ├── slow-requests.md
    └── crash-simulation.md

# GitHub Actions workflows
.github/
└── workflows/
    ├── ci.yml                      # Lint, type check, test on PR
    └── deploy.yml                  # Deploy to Azure via OIDC

# Root configuration files
pyproject.toml                      # Project config (dependencies, tools)
requirements.txt                    # Production dependencies
requirements-dev.txt                # Development dependencies
Dockerfile                          # Container build
.env.example                        # Environment variable template
```

**Structure Decision**: Single project structure selected because the application is a monolithic
Python server with an embedded static frontend. No separate frontend build process is required
(vanilla JavaScript), aligning with the Constitution's Simplicity principle.

## Complexity Tracking

> No violations identified. Constitution gates passed without justification needed.

## Constitution Check (Post-Design Re-evaluation)

*Re-evaluated after Phase 1 design completion.*

| Principle | Design Compliance | Status |
|-----------|-------------------|--------|
| I. Code Quality & Readability | Services have single responsibilities (cpu_stress_service, memory_pressure_service, etc.); Types defined with Pydantic; Constants centralized in config/ | ✅ Pass |
| II. Documentation-First | OpenAPI spec auto-generated by FastAPI; data-model.md provides Pydantic models with docstrings; quickstart.md provides onboarding guide | ✅ Pass |
| III. TDD (Encouraged) | Test structure defined (tests/unit/, tests/integration/); Tests planned for all services and API endpoints | ✅ Pass |
| IV. Simplicity & YAGNI | No ORM (in-memory only); vanilla JS frontend (no build step); single project structure; minimal dependencies | ✅ Pass |
| V. Defensive Programming | Pydantic models provide automatic validation; type hints throughout; structured logging with Python logging module | ✅ Pass |

**Post-Design Gate Result**: ✅ PASS - Design adheres to all constitution principles.

## Implementation Phases

### Phase 1: Foundation
- FastAPI server setup with type hints
- Health endpoint (`GET /api/health`)
- Configuration module (Pydantic Settings for environment variables)
- Metrics collection service using psutil (CPU, memory, process info)
- Basic project tooling (pyproject.toml with Black, Ruff, mypy, pytest)
- Dockerfile for containerization

### Phase 2: Core Simulations
- CPU stress service (multiprocessing or threading for computation)
- Memory pressure service (bytearray allocation with tracking)
- Synchronous blocking service (time.sleep in thread pool)
- Async blocking service (blocking the event loop)
- Simulation tracker service (manage active simulations)

### Phase 3: Real-Time Dashboard
- WebSocket integration for metrics broadcasting
- Static HTML dashboard with vanilla JavaScript matching Node.js/.NET Core visual design:
  - Fixed header with hamburger menu, title, SKU badge, panel toggle, connection status
  - Left sidebar drawer navigation (hamburger-activated) with sections:
    - Application: Dashboard link
    - Documentation: Docs, Azure Diagnostics, Deploy to Azure links
    - External: GitHub Repository link (https://github.com/rhamlett/perfsimpython)
  - Right slide-out panel for simulation controls with grouped sections
  - Metric tiles with visual progress bars (CPU, Memory, RSS, Latency)
  - Active Simulations display section
  - Event Log display section
- Chart.js for CPU/memory trend visualization and latency charts
- CSS styling matching the shared design language (CSS variables, Segoe UI font, color scheme)
- Request latency monitor with probe visualization

### Phase 4: Additional Features
- Slow request service (asyncio.sleep-based delays)
- Crash simulation service (unhandled exception, memory exhaustion)
- Admin endpoints for status and configuration
- Request logging middleware

### Phase 5: Documentation & Polish
- In-app documentation page (docs.html) with:
  - API reference for all endpoints
  - Simulation type explanations
  - Table of contents sidebar navigation
- Azure Diagnostics guide page (azure-diagnostics.html):
  - App Service Diagnostics walkthrough
  - Application Insights integration
  - Kudu SSH access and commands
- Deploy to Azure page (azure-deployment.html):
  - GitHub Actions workflow setup
  - OIDC authentication configuration
  - Azure resource provisioning steps
- Linux/Python tools guide (py-spy, cProfile, top, htop)
- README with quickstart instructions
- Input validation refinement and error handling
- Ensure all pages share common sidebar navigation and styling

## UI Design System

The Python version MUST match the visual design of the Node.js and .NET Core versions to provide
a consistent user experience across all three simulator applications.

### Color Scheme (Python Version)

```css
:root {
  /* Primary theme - Python blue/yellow inspired */
  --color-primary: #306998;         /* Python blue */
  --color-primary-dark: #1e4a6e;
  --color-success: #107c10;
  --color-warning: #ffb900;
  --color-danger: #d13438;
  
  /* Backgrounds */
  --color-bg: #e8f4f8;              /* Light blue-gray */
  --color-card: #ffffff;
  --color-text: #323130;
  --color-text-muted: #605e5c;
  
  /* Metric colors */
  --color-cpu: #0078d4;
  --color-memory: #107c10;
  --color-threads: #8764b8;
  --color-latency: #ffb900;
}
```

### Shared UI Components

| Component | Description | Behavior |
|-----------|-------------|----------|
| Header | Fixed position, gradient background | Contains hamburger, title, SKU badge, panel toggle, connection status |
| Sidebar Drawer | 280px width, slides from left | Activated by hamburger, overlay dims background |
| Side Panel | 380px width, slides from right | Activated by panel toggle button |
| Metric Tiles | Card with icon, label, value, progress bar | Real-time updates via WebSocket |
| Chart Cards | Card containing Chart.js canvas | CPU/Memory over time, Latency |
| Event Log | Scrollable list of timestamped events | Color-coded by event type |
| Control Sections | Grouped form controls in side panel | Each simulation type has dedicated section |

### Page Structure

| Page | URL | Purpose |
|------|-----|---------|
| Dashboard | `/` or `/index.html` | Main metrics and simulation controls |
| Documentation | `/docs.html` | API reference and simulation guides |
| Azure Diagnostics | `/azure-diagnostics.html` | How to diagnose issues in App Service |
| Deploy to Azure | `/azure-deployment.html` | GitHub Actions + OIDC setup guide |

### Sidebar Navigation Structure

```
Application
├── 🎮 Dashboard (/)
│
Documentation  
├── 📚 Documentation (/docs.html)
├── ☁️ Azure Diagnostics (/azure-diagnostics.html)
├── 🚀 Deploy to Azure (/azure-deployment.html)
│
External
└── 🐙 GitHub Repository (https://github.com/rhamlett/perfsimpython)
```

### Simulation Control Panel Sections

1. **🔥 CPU Stress** - Duration (s), Intensity dropdown, Trigger/Stop buttons
2. **📊 Memory Pressure** - Size (MB), Allocate/Release buttons
3. **🧵 Thread/Async Blocking** - Duration, Chunk size, Trigger button
4. **🐌 Slow Requests** - Duration, Interval, Max requests, Start/Stop buttons
5. **❌ Failed Requests** - Error count, Generate button
6. **💥 Application Crash** - Crash type dropdown, Trigger button (with warning)

## Key Python-Specific Considerations

### CPU Stress Implementation
- Python's GIL means CPU-bound work in threads won't truly parallelize
- Use `multiprocessing` module for true multi-core CPU stress
- Alternative: Use `concurrent.futures.ProcessPoolExecutor`
- For single-core stress, tight loops with computation work fine

### Memory Allocation
- Use `bytearray` for predictable memory allocation
- Store references in a list to prevent garbage collection
- Monitor with `psutil.Process().memory_info()`
- Be aware of Python's memory allocator behavior

### Async Blocking
- FastAPI runs on an async event loop (asyncio)
- Blocking the event loop demonstrates async anti-patterns
- Use `time.sleep()` in async context to show the problem
- Proper async uses `await asyncio.sleep()`

### Synchronous Blocking Behavior
- FastAPI uses `anyio` thread pool for sync endpoints
- Blocking all threads shows thread starvation (synchronous blocking)
- Default thread pool size is typically 40 threads
- Configure via `ANYIO_BACKEND` and related settings

## Dependencies

### Production
```
fastapi>=0.100.0
uvicorn[standard]>=0.22.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
psutil>=5.9.0
python-multipart>=0.0.6
websockets>=11.0
```

### Development
```
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
httpx>=0.24.0  # For async test client
black>=23.0.0
ruff>=0.0.270
mypy>=1.0.0
```

## Source Control & CI/CD

**Repository**: https://github.com/rhamlett/perfsimpython  
**Branch**: `main`  
**Deployment**: GitHub Actions with OIDC authentication to Azure

### GitHub Actions Workflows

**CI Workflow** (`.github/workflows/ci.yml`):
- Triggers on: Pull requests to `main`, pushes to `main`
- Jobs: Lint (ruff), Type check (mypy), Format check (black), Test (pytest)
- Python version: 3.11

**Deploy Workflow** (`.github/workflows/deploy.yml`):
- Triggers on: Push to `main` (after CI passes), manual dispatch
- Authentication: OIDC (OpenID Connect) - no secrets stored in GitHub
- Steps: Build, Package, Deploy to Azure App Service
- Requires: Azure service principal with federated credentials configured

### OIDC Setup Requirements

1. Azure AD App Registration with federated credential for GitHub Actions
2. Service principal with Contributor role on target resource group
3. GitHub repository secrets/variables:
   - `AZURE_CLIENT_ID` - App registration client ID
   - `AZURE_TENANT_ID` - Azure AD tenant ID
   - `AZURE_SUBSCRIPTION_ID` - Target subscription

## Azure Deployment Considerations

- Use Azure App Service Linux with Python 3.11
- Configure startup command: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.main:app`
- Alternative: Use container deployment with provided Dockerfile
- Application Insights integration via `opencensus-ext-azure` or `azure-monitor-opentelemetry`
- Set `WEBSITE_RUN_FROM_PACKAGE=1` for faster cold starts
