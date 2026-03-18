# Tasks: Performance Problem Simulator (Python)

**Input**: Design documents from `/specs/001-perf-simulator-python/`
**Prerequisites**: plan.md ✅, spec.md ✅

**Tests**: Tests are included as this is an educational tool where correctness is critical.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story (US1-US6) - only for user story phases
- Exact file paths included in descriptions

## Path Conventions

- **Single project structure** per plan.md
- Source: `src/`
- Tests: `tests/`
- Static files: `src/static/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and tooling configuration

- [X] T001 Create project directory structure per plan.md (src/, tests/, docs/, .github/workflows/)
- [X] T002 Create pyproject.toml with project metadata, dependencies (fastapi, uvicorn, pydantic, pydantic-settings, psutil, websockets, python-multipart), and tool configurations (black, ruff, mypy, pytest)
- [X] T003 [P] Create requirements.txt with production dependencies
- [X] T004 [P] Create requirements-dev.txt with development dependencies (pytest, pytest-asyncio, pytest-cov, httpx, black, ruff, mypy)
- [X] T005 [P] Create .env.example with environment variable template (LOG_LEVEL)
- [X] T006 [P] Create Dockerfile for containerized deployment with Python 3.11 base image
- [X] T007 [P] Create .github/workflows/ci.yml for lint, type check, format check, and test on PR
- [X] T008 [P] Create .github/workflows/deploy.yml for Azure deployment via OIDC
- [X] T009 Create src/__init__.py and tests/__init__.py package markers
- [X] T010 Create tests/conftest.py with pytest fixtures (test client, async client)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T011 Create src/config/__init__.py and src/config/settings.py with Pydantic Settings class (LOG_LEVEL)
- [X] T012 Create src/models/__init__.py package marker
- [X] T013 [P] Create src/models/entities.py with SimulationType enum, SimulationState dataclass, AllocatedMemoryBlock dataclass
- [X] T014 [P] Create src/models/requests.py with Pydantic request models (CpuStressRequest, MemoryAllocateRequest, BlockingRequest, SlowRequest, CrashRequest, FailedRequestsRequest)
- [X] T015 [P] Create src/models/responses.py with Pydantic response models (HealthResponse, MetricsResponse, SimulationResponse, ErrorResponse)
- [X] T016 Create src/services/__init__.py package marker
- [X] T017 Create src/services/simulation_tracker.py with SimulationTracker class to manage active simulations (add, remove, list, get_by_id)
- [X] T018 Create src/services/event_log_service.py with EventLogService class to record simulation events with timestamps
- [X] T019 Create src/services/metrics_service.py with MetricsService class using psutil (get_cpu_percent, get_memory_info, get_process_info)
- [X] T020 Create src/middleware/__init__.py package marker
- [X] T021 [P] Create src/middleware/error_handler.py with global exception handler returning structured JSON errors
- [X] T022 [P] Create src/middleware/request_logger.py with request logging middleware using Python logging module
- [X] T023 Create src/routers/__init__.py package marker
- [X] T024 Create src/app.py with FastAPI app configuration, middleware registration, router includes, static file mounting
- [X] T025 Create src/main.py as uvicorn entry point (uvicorn.run with reload for dev)
- [X] T026 Create src/websocket/__init__.py package marker
- [X] T027 Create src/websocket/metrics_broadcaster.py with ConnectionManager class (connect, disconnect, broadcast) for WebSocket real-time updates

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - CPU Stress Training (Priority: P1) 🎯 MVP

**Goal**: Trigger controlled CPU stress, observe in monitoring tools, health endpoint for status

**Independent Test**: Start simulator, call POST /api/cpu/start, verify CPU spike in top/htop or Azure metrics

### Tests for User Story 1

- [X] T028 [P] [US1] Create tests/unit/services/__init__.py package marker
- [X] T029 [P] [US1] Create tests/unit/services/test_metrics_service.py with unit tests for MetricsService (test_get_cpu_percent_returns_float, test_get_memory_info_returns_dict)
- [X] T030 [P] [US1] Create tests/unit/services/test_simulation_tracker.py with unit tests for SimulationTracker (test_add_simulation, test_remove_simulation, test_list_active)
- [X] T031 [P] [US1] Create tests/unit/routers/__init__.py package marker
- [X] T032 [P] [US1] Create tests/unit/routers/test_health.py with unit tests for health endpoint (test_health_returns_200, test_health_includes_metrics)
- [X] T033 [P] [US1] Create tests/integration/__init__.py package marker
- [X] T034 [US1] Create tests/integration/test_cpu_api.py with integration tests (test_start_cpu_stress, test_stop_cpu_stress, test_cpu_stress_stacking)

### Implementation for User Story 1

- [X] T035 [US1] Create src/services/cpu_stress_service.py with CpuStressService class using multiprocessing.Process for CPU-bound work (start_stress, stop_stress, stop_all)
- [X] T036 [US1] Create tests/unit/services/test_cpu_stress_service.py with unit tests (test_start_creates_process, test_stop_terminates_process)
- [X] T037 [US1] Create src/routers/health.py with GET /api/health endpoint returning HealthResponse with status and basic metrics
- [X] T038 [US1] Create src/routers/metrics.py with GET /api/metrics endpoint returning current CPU, memory, and active simulations
- [X] T039 [US1] Create src/routers/cpu.py with POST /api/cpu/start (duration, intensity params), POST /api/cpu/stop, POST /api/cpu/stop-all endpoints
- [X] T040 [US1] Add CPU stress control section to event log service (log start/stop events)
- [X] T041 [US1] Register health, metrics, cpu routers in src/app.py

**Checkpoint**: US1 complete - CPU stress can be triggered via API, health endpoint operational

---

## Phase 4: User Story 2 - Real-Time Metrics Dashboard (Priority: P2)

**Goal**: Visual dashboard with live metrics, simulation controls, sidebar navigation, charts

**Independent Test**: Open browser to /, verify metrics update in real-time, trigger simulation via control panel

### Tests for User Story 2

- [X] T042 [P] [US2] Create tests/integration/test_websocket.py with WebSocket connection tests (test_connect, test_receive_metrics, test_reconnect_on_disconnect)
- [X] T043 [P] [US2] Create tests/integration/test_static_files.py with static file serving tests (test_index_html_served, test_css_served, test_js_served)

### Implementation for User Story 2

- [X] T044 [US2] Create src/static/favicon.svg with Python-themed icon (blue/yellow snake or similar)
- [X] T045 [US2] Create src/static/css/styles.css with shared CSS matching Node.js/.NET Core versions (CSS variables, header, sidebar drawer, side panel, metric tiles, charts, event log styles)
- [X] T046 [US2] Create src/static/js/websocket-client.js with WebSocket connection management (connect, exponential backoff reconnect with base 1s delay and max 5 retries, message handling, connection status display showing disconnected/reconnecting/connected states)
- [X] T047 [US2] Create src/static/js/charts.js with Chart.js integration (CPU/Memory trend chart, Latency chart, initialization and update functions)
- [X] T048 [US2] Create src/static/js/dashboard.js with dashboard logic (sidebar toggle, panel toggle, simulation form handlers, metric tile updates, event log updates, active simulations display)
- [X] T049 [US2] Create src/static/index.html with full dashboard structure:
  - Fixed header (hamburger btn, title, SKU badge, panel toggle, connection status)
  - Left sidebar drawer (Application: Dashboard; Documentation: Docs, Azure Diagnostics, Deploy to Azure; External: GitHub repo)
  - Right side panel with simulation control sections (CPU, Memory, Blocking, Slow, Failed, Crash)
  - Main content with metric tiles, charts section, active simulations, event log
  - Warning banner for non-production use
- [X] T050 [US2] Add WebSocket endpoint /ws/metrics in src/app.py for real-time metrics streaming
- [X] T051 [US2] Implement background task in src/app.py to broadcast metrics via WebSocket every 500ms
- [X] T052 [US2] Mount static files directory in src/app.py at root path

**Checkpoint**: US2 complete - Dashboard displays real-time metrics, controls work, navigation functional

---

## Phase 5: User Story 3 - Memory Pressure Simulation (Priority: P3)

**Goal**: Allocate/release memory on demand, observe memory growth in dashboard

**Independent Test**: Call POST /api/memory/allocate with sizeMb=200, verify memory metric increases by ~200MB

### Tests for User Story 3

- [X] T053 [P] [US3] Create tests/unit/services/test_memory_pressure_service.py with unit tests (test_allocate_creates_block, test_release_frees_memory, test_allocation_limit_enforced)
- [X] T054 [P] [US3] Create tests/integration/test_memory_api.py with integration tests (test_allocate_memory, test_release_memory, test_memory_stacking, test_exceeds_limit_returns_error)

### Implementation for User Story 3

- [X] T055 [US3] Create src/services/memory_pressure_service.py with MemoryPressureService class (allocate_memory using bytearray, release_memory, release_all, get_allocated_blocks)
- [X] T056 [US3] Create src/routers/memory.py with POST /api/memory/allocate (sizeMb param), POST /api/memory/release, POST /api/memory/release-all endpoints
- [X] T057 [US3] Add memory pressure control section event logging
- [X] T058 [US3] Register memory router in src/app.py
- [X] T059 [US3] Update dashboard.js to handle memory allocation/release form submissions

**Checkpoint**: US3 complete - Memory can be allocated/released via API and dashboard

---

## Phase 6: User Story 4 - Synchronous/Async Blocking Simulation (Priority: P4)

**Goal**: Demonstrate synchronous blocking (thread pool starvation) and async blocking (event loop blocking)

**Independent Test**: Trigger blocking, observe response latency spike for concurrent requests

### Tests for User Story 4

- [X] T060 [P] [US4] Create tests/unit/services/test_blocking_service.py with unit tests (test_sync_blocking_delays, test_async_blocking_delays)
- [X] T061 [P] [US4] Create tests/integration/test_blocking_api.py with integration tests (test_sync_blocking_increases_latency, test_async_blocking_delays_all_requests)

### Implementation for User Story 4

- [X] T062 [US4] Create src/services/blocking_service.py with BlockingService class:
  - sync_block(duration_seconds) - uses time.sleep() in thread pool to demonstrate synchronous blocking
  - async_block(duration_seconds) - uses time.sleep() in async context to demonstrate async blocking
  - chunked_block(duration_seconds, chunk_ms) - blocks in chunks with yields for dashboard updates
- [X] T063 [US4] Create src/routers/blocking.py with:
  - POST /api/blocking/sync (duration, count params) - triggers synchronous blocking
  - POST /api/blocking/async (duration, chunk_ms params) - triggers async blocking
  - POST /api/blocking/stop - stops active blocking simulations
- [X] T064 [US4] Add blocking control section event logging
- [X] T065 [US4] Register blocking router in src/app.py
- [X] T066 [US4] Update dashboard.js to handle blocking simulation form submissions

**Checkpoint**: US4 complete - Thread and async blocking can be triggered and observed

---

## Phase 7: User Story 5 - Slow Requests & Crash Simulation (Priority: P5)

**Goal**: Generate slow responses and trigger application crashes for diagnostic practice

**Independent Test**: Request slow endpoint with 5s delay, verify response arrives after 5s; trigger crash, verify process terminates

### Tests for User Story 5

- [X] T067 [P] [US5] Create tests/unit/services/test_slow_request_service.py with unit tests (test_slow_response_delays_correctly)
- [X] T068 [P] [US5] Create tests/unit/services/test_crash_service.py with unit tests (test_crash_types_defined)
- [X] T069 [P] [US5] Create tests/integration/test_slow_api.py with integration tests (test_slow_request_timing, test_slow_request_generator)
- [X] T070 [P] [US5] Create tests/integration/test_failed_requests_api.py with integration tests (test_generate_500_errors)

### Implementation for User Story 5

- [X] T071 [US5] Create src/services/slow_request_service.py with SlowRequestService class:
  - slow_response(delay_seconds) - uses asyncio.sleep for non-blocking delay
  - start_slow_generator(interval, max_requests, delay) - generates periodic slow requests
  - stop_slow_generator() - stops the generator
- [X] T072 [US5] Create src/services/crash_service.py with CrashService class:
  - trigger_crash(crash_type) - supports: 'exception', 'stackoverflow', 'oom', 'sigabrt'
  - exception: raises unhandled RuntimeError
  - stackoverflow: triggers infinite recursion exceeding sys.getrecursionlimit()
  - oom: allocates memory in loop until system kills process
  - sigabrt: sends SIGABRT signal via os.abort()
  - Comments explaining each crash type and its diagnostic signature
- [X] T073 [US5] Create src/routers/slow.py with:
  - GET /api/slow (delay param) - returns response after delay
  - POST /api/slow/start (interval, max_requests, delay params) - starts slow request generator
  - POST /api/slow/stop - stops slow request generator
- [X] T074 [US5] Create src/routers/crash.py with:
  - POST /api/crash (crash_type param) - triggers specified crash type
  - Includes prominent warning comments about production use
- [X] T075 [US5] Create src/routers/admin.py with:
  - POST /api/failed-requests (count param) - generates HTTP 500 errors
  - POST /api/admin/reset - releases all memory, stops all simulations
  - GET /api/admin/stats - returns detailed application statistics
- [X] T076 [US5] Register slow, crash, admin routers in src/app.py
- [X] T077 [US5] Update dashboard.js to handle slow requests, failed requests, and crash form submissions with crash warning confirmation

**Checkpoint**: US5 complete - Slow requests, failed requests, and crashes can be triggered

---

## Phase 8: User Story 6 - Documentation & Azure Diagnostic Guides (Priority: P6)

**Goal**: Built-in documentation pages with API reference and Azure diagnostic guidance

**Independent Test**: Access /docs.html, verify all simulation types documented with Azure diagnostic steps

### Implementation for User Story 6

- [X] T078 [P] [US6] Create src/static/docs.html with documentation page:
  - Same header/sidebar structure as dashboard
  - Table of contents sidebar (right side)
  - API reference sections for each endpoint group
  - Simulation explanations with educational content about each anti-pattern
- [X] T079 [P] [US6] Create src/static/azure-diagnostics.html with Azure diagnostics guide:
  - App Service Diagnostics walkthrough
  - Application Insights integration
  - Kudu SSH access and commands
  - py-spy, cProfile usage in Azure
- [X] T080 [P] [US6] Create src/static/azure-deployment.html with deployment guide:
  - GitHub Actions workflow explanation
  - OIDC authentication setup steps
  - Azure resource provisioning (App Service, App Registration)
  - Environment configuration
- [X] T081 [P] [US6] Create docs/README.md with project overview and quickstart instructions
- [X] T082 [P] [US6] Create docs/azure-diagnostics.md with detailed Azure diagnostic tools guide (markdown version)
- [X] T083 [P] [US6] Create docs/linux-tools.md with Linux CLI diagnostic tools guide (top, htop, py-spy, cProfile)
- [X] T084 [P] [US6] Create docs/simulations/ directory with individual simulation guides:
  - docs/simulations/cpu-stress.md
  - docs/simulations/memory-pressure.md
  - docs/simulations/thread-blocking.md
  - docs/simulations/async-blocking.md
  - docs/simulations/slow-requests.md
  - docs/simulations/crash-simulation.md

**Checkpoint**: US6 complete - All documentation pages accessible and complete

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final refinements affecting multiple user stories

- [X] T085 [P] Add comprehensive docstrings to all services in src/services/
- [X] T086 [P] Add comprehensive docstrings to all routers in src/routers/
- [X] T087 [P] Add inline comments explaining anti-patterns in cpu_stress_service.py, memory_pressure_service.py, blocking_service.py
- [X] T088 ~~Add DISABLE_PROBLEM_ENDPOINTS environment variable check~~ (REMOVED - not needed)
- [X] T089 [P] Create README.md at repository root with project overview, quickstart, and links to documentation
- [X] T090 Run black formatter on all Python files
- [X] T091 Run ruff linter and fix any issues
- [X] T092 Run mypy type checker and fix any type errors
- [X] T093 Run full pytest suite and ensure all tests pass
- [X] T094 Verify dashboard works end-to-end (start app, open browser, trigger each simulation type)
- [ ] T095 Test deployment workflow locally using act or similar tool

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational) ──── BLOCKS ALL USER STORIES
    │
    ├──────────────────────────────────────────────────┐
    │                                                  │
    ▼                                                  ▼
Phase 3 (US1: CPU)                             Phase 4 (US2: Dashboard)
    │                                                  │
    │ (US2 needs US1 for CPU controls)                │
    └─────────────► ◄──────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
Phase 5         Phase 6         Phase 7
(US3: Memory)   (US4: Block)    (US5: Slow/Crash)
    │               │               │
    └───────────────┼───────────────┘
                    │
                    ▼
            Phase 8 (US6: Docs)
                    │
                    ▼
            Phase 9 (Polish)
```

### User Story Dependencies

| Story | Can Start After | Dependencies |
|-------|-----------------|--------------|
| US1 (CPU) | Phase 2 complete | None - MVP, first to implement |
| US2 (Dashboard) | Phase 2 complete | Needs US1 for CPU controls to work |
| US3 (Memory) | Phase 2 complete | Independent, but UI needs US2 |
| US4 (Blocking) | Phase 2 complete | Independent, but UI needs US2 |
| US5 (Slow/Crash) | Phase 2 complete | Independent, but UI needs US2 |
| US6 (Docs) | US1-US5 complete | Documents all features |

### Recommended Execution Order

**Sequential (single developer)**:
1. Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5-7 (US3-5 in any order) → Phase 8 (US6) → Phase 9

**Parallel (multiple developers)**:
- Developer A: Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2)
- Developer B (after Phase 2): Phase 5 (US3) → Phase 6 (US4)
- Developer C (after Phase 2): Phase 7 (US5) → Phase 8 (US6)
- All: Phase 9 (Polish)

### Parallel Opportunities per Phase

| Phase | Parallel Tasks |
|-------|----------------|
| Phase 1 | T003, T004, T005, T006, T007, T008 |
| Phase 2 | T013, T014, T015, T021, T022 |
| Phase 3 | T028-T034 (all tests), T029-T032 (unit tests) |
| Phase 4 | T042, T043 |
| Phase 5 | T053, T054 |
| Phase 6 | T060, T061 |
| Phase 7 | T067, T068, T069, T070 |
| Phase 8 | T078, T079, T080, T081, T082, T083, T084 (all) |
| Phase 9 | T085, T086, T087, T089 |

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 95 |
| **Setup Phase** | 10 tasks |
| **Foundational Phase** | 17 tasks |
| **US1 (CPU - MVP)** | 14 tasks |
| **US2 (Dashboard)** | 11 tasks |
| **US3 (Memory)** | 7 tasks |
| **US4 (Blocking)** | 7 tasks |
| **US5 (Slow/Crash)** | 11 tasks |
| **US6 (Docs)** | 7 tasks |
| **Polish Phase** | 11 tasks |

### MVP Scope

**Minimum Viable Product (US1 only)**: Phases 1-3 (41 tasks)
- Project setup and tooling
- Core infrastructure (config, models, services)
- Health endpoint
- CPU stress simulation (start/stop)
- Basic metrics endpoint

**Recommended First Release (US1 + US2)**: Phases 1-4 (52 tasks)
- Everything in MVP
- Full dashboard with real-time metrics
- WebSocket updates
- Visual controls for CPU simulation
