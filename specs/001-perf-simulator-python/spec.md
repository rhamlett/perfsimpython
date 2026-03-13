# Feature Specification: Performance Problem Simulator

**Feature Branch**: `001-perf-simulator-python`  
**Created**: 2026-03-13  
**Status**: Draft  
**Input**: User description: "Create a Performance Problem Simulator for Python applications running on Azure App Service Linux"

## Overview

An educational tool that intentionally triggers controllable performance problems in a Python
application, allowing developers, DevOps engineers, and support engineers to practice diagnosing
issues using Azure diagnostics tools and standard Linux profiling utilities.

**Target Users**: Developers, DevOps engineers, and support engineers learning to diagnose
Python performance issues on Azure App Service Linux.

**Problem Statement**: Diagnosing performance issues in production is challenging because real
problems are unpredictable, stressful, and rarely allow time for learning. This simulator
provides a safe environment to trigger known problems and practice using diagnostic tools
before facing real incidents.

> ⚠️ **Important**: This application deliberately implements "bad" code patterns. It is intended
> **only** for demonstration, testing, and learning in non-production environments.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CPU Stress Training (Priority: P1) 🎯 MVP

As a support engineer learning Azure diagnostics, I want to trigger a controlled CPU stress
condition so that I can observe how CPU saturation appears in Azure monitoring tools and
practice diagnosing the root cause.

**Why this priority**: High CPU is the most common and visible performance problem. It affects
all requests and is easily observable in Azure metrics, making it ideal for initial learning.
This story establishes the core simulation infrastructure and delivers immediate learning value.

**Independent Test**: Can be fully tested by starting the simulator, triggering CPU stress via
API call, and verifying the CPU spike is visible in system monitoring tools (top, htop, or
Azure metrics).

**Acceptance Scenarios**:

1. **Given** the simulator is running, **When** I trigger a CPU stress simulation with 80% target
   load for 30 seconds, **Then** CPU usage increases to approximately 80% and returns
   to baseline after 30 seconds.

2. **Given** a CPU stress simulation is active, **When** I issue a stop command, **Then** the
   simulation ends immediately and CPU usage returns to baseline.

3. **Given** the simulator is running, **When** I request health status, **Then** I receive
   confirmation that the service is operational along with basic system metrics.

4. **Given** a CPU simulation is running, **When** I start another CPU simulation,
   **Then** both simulations run concurrently (stacking) and the response confirms the new
   simulation was added.

---

### User Story 2 - Real-Time Metrics Dashboard (Priority: P2)

As a developer practicing diagnostics, I want a visual dashboard showing live system metrics
and simulation controls so that I can observe the impact of simulations in real-time and
easily trigger different problem scenarios.

**Why this priority**: While the API provides core functionality, a visual dashboard dramatically
improves the learning experience by showing metrics changes as they happen, making cause-and-effect
relationships immediately visible.

**Independent Test**: Can be tested by opening the dashboard in a browser, triggering simulations,
and verifying metrics update in real-time without page refresh.

**Acceptance Scenarios**:

1. **Given** I access the dashboard URL, **When** the page loads, **Then** I see current CPU
   percentage, memory usage, active threads, and request latency updating in real-time.

2. **Given** the dashboard is open, **When** I trigger a CPU stress simulation using the control
   panel, **Then** I see the CPU metric rise and can observe a visual chart of CPU over time.

3. **Given** a simulation is active, **When** I click the stop button, **Then** the simulation
   stops and the dashboard reflects the change immediately.

4. **Given** multiple simulation events occur, **When** I view the event log section, **Then**
   I see a chronological list of simulation start/stop events with timestamps.

5. **Given** I am on the dashboard, **When** I click the hamburger menu, **Then** a left sidebar
   drawer slides out with navigation links to Documentation, Azure Diagnostics, Deploy to Azure,
   and GitHub Repository.

6. **Given** I am on the dashboard, **When** I click "Simulation Controls", **Then** a right
   side panel slides out with all simulation control forms.

---

### User Story 3 - Memory Pressure Simulation (Priority: P3)

As a DevOps engineer, I want to simulate memory pressure conditions so that I can practice
identifying memory leaks and high memory usage using Azure diagnostics and profiling tools.

**Why this priority**: Memory issues are common and often harder to diagnose than CPU issues.
This adds a distinct problem type that requires different diagnostic approaches.

**Independent Test**: Can be tested by triggering memory allocation, observing heap growth in
metrics, and verifying memory is released when the simulation stops.

**Acceptance Scenarios**:

1. **Given** the simulator is running, **When** I trigger memory pressure to allocate 200MB,
   **Then** process memory usage increases by approximately 200MB and remains elevated.

2. **Given** memory has been allocated, **When** I trigger a memory release, **Then** the
   previously allocated memory is freed and memory usage decreases accordingly.

3. **Given** the simulator is running, **When** I request memory allocation exceeding available
   memory, **Then** I receive an error message before the allocation rather than crashing.

---

### User Story 4 - Synchronous/Async Blocking Simulation (Priority: P4)

As a Python developer, I want to simulate synchronous blocking and async blocking so that I can
practice identifying these Python-specific performance problems and understand their symptoms.

**Why this priority**: Thread pool exhaustion and blocking the async event loop are common
issues in Python web applications. Understanding these patterns is essential for Python developers
working with FastAPI, Flask, or other async frameworks.

**Independent Test**: Can be tested by triggering blocking, observing response latency increase,
and verifying that concurrent requests experience delays during the block.

**Acceptance Scenarios**:

1. **Given** the simulator is running, **When** I trigger synchronous blocking for 5 seconds,
   **Then** concurrent requests to the application are delayed until worker threads become available.

2. **Given** the simulator is running with async endpoints, **When** I trigger async blocking,
   **Then** all async operations are delayed and response times increase dramatically.

3. **Given** blocking is active, **When** I make concurrent requests, **Then** those
   requests queue and respond only after the blocking operation completes.

---

### User Story 5 - Slow Requests & Crash Simulation (Priority: P5)

As a support engineer, I want to simulate slow HTTP responses and application crashes so that
I can practice diagnosing latency issues and understanding crash recovery behavior.

**Why this priority**: Slow responses and crashes are important failure modes, but they're
simpler to understand than the previous scenarios. Grouping them maintains focus on higher-value
learning scenarios first.

**Independent Test**: Can be tested by requesting a slow endpoint with configurable delay and
verifying the response takes the expected time; crash simulation can be verified by observing
process restart behavior.

**Acceptance Scenarios**:

1. **Given** the simulator is running, **When** I request a slow response with a 5-second delay,
   **Then** the response arrives after approximately 5 seconds.

2. **Given** the simulator is running, **When** I trigger a crash via unhandled exception,
   **Then** the process terminates and a crash can be observed in diagnostic logs.

3. **Given** the simulator is running, **When** I trigger a crash via memory exhaustion (OOM),
   **Then** the process terminates due to out-of-memory condition.

4. **Given** the simulator is running, **When** I trigger a crash via stack overflow,
   **Then** the process terminates due to recursion limit exceeded.

5. **Given** the simulator is running, **When** I trigger a crash via SIGABRT signal,
   **Then** the process terminates abnormally and a core dump may be generated.

---

### User Story 6 - Documentation & Azure Diagnostic Guides (Priority: P6)

As a learner using the simulator, I want built-in documentation explaining each simulation
type and how to observe problems in Azure tools so that I can learn effective diagnostic
techniques alongside triggering problems.

**Why this priority**: Documentation enhances learning but the simulator provides value even
without it. Users can learn by experimentation, so documentation is an enhancement rather than
a core requirement.

**Independent Test**: Can be tested by accessing the documentation endpoint and verifying all
simulation types have explanations and Azure diagnostic guidance.

**Acceptance Scenarios**:

1. **Given** I access the documentation endpoint, **When** I view the CPU stress section,
   **Then** I see an explanation of the simulation, expected symptoms, and how to observe
   the problem in App Service Diagnostics.

2. **Given** I access the documentation endpoint, **When** I view any simulation type,
   **Then** I see guidance for at least three diagnostic approaches (Azure portal, command
   line, and Application Insights where applicable).

3. **Given** I access the documentation, **When** viewing the blocking section,
   **Then** I see Python-specific diagnostic tips for both synchronous blocking and async blocking (py-spy, cProfile, asyncio debug mode).

---

### Edge Cases

- What happens when multiple simulations of the same type are triggered simultaneously?
  (System should allow stacking - multiple simulations run concurrently)
- How does the system behave when maximum duration limits are exceeded?
  (Simulations should automatically stop at the configured maximum)
- How does memory simulation behave when approaching system memory limits?
  (Should fail gracefully with an error rather than crashing the system)
- What happens when the WebSocket connection drops while viewing the dashboard?
  (Dashboard MUST attempt reconnection using exponential backoff: base delay 1s, max 5 retries, doubling each attempt. Connection status indicator MUST show disconnected/reconnecting/connected states)

## Requirements *(mandatory)*

### Functional Requirements

**Core Problem Simulators**

- **FR-001**: System MUST provide an endpoint to trigger sustained high CPU usage for a configurable duration (default: 30 seconds, no maximum limit)
- **FR-002**: System MUST provide an endpoint to allocate a configurable amount of memory that persists until explicitly released (default: 100 MB, no maximum limit)
- **FR-003**: System MUST provide an endpoint to release previously allocated memory
- **FR-004**: System MUST provide an endpoint that demonstrates synchronous blocking with configurable concurrency (default: 4) and delay (default: 5s) parameters
- **FR-005**: System MUST provide an endpoint that demonstrates async blocking with configurable duration (default: 5s)
- **FR-006**: System MUST allow multiple problem types to be active simultaneously
- **FR-007**: System MUST provide an endpoint to generate HTTP 5xx errors with configurable count

**Observability & Feedback**

- **FR-008**: System MUST expose current CPU usage percentage via an endpoint
- **FR-009**: System MUST expose current memory usage (RSS, heap) via an endpoint
- **FR-010**: System MUST expose thread/worker statistics via an endpoint
- **FR-011**: System MUST provide a web-based dashboard with real-time WebSocket updates that displays all metrics
- **FR-012**: System MUST log all problem-trigger operations with timestamps and parameters

**User Interface Requirements**

- **FR-020**: Dashboard MUST include a fixed header with hamburger menu, title, SKU badge, panel toggle button, and connection status indicator
- **FR-021**: Dashboard MUST include a left sidebar drawer (activated by hamburger menu) with navigation links organized into sections: Application (Dashboard), Documentation (Docs, Azure Diagnostics, Deploy to Azure), and External (GitHub Repository)
- **FR-022**: Dashboard MUST include a right slide-out panel for simulation controls, containing grouped control sections for each simulation type (CPU, Memory, Blocking, Slow Requests, Failed Requests, Crash)
- **FR-023**: Dashboard MUST display metric tiles with visual progress bars for CPU, Memory, and other key metrics
- **FR-024**: Dashboard MUST include real-time charts showing CPU/Memory trends and Request Latency over time using Chart.js
- **FR-025**: Dashboard MUST display an Active Simulations section showing currently running simulations
- **FR-026**: Dashboard MUST display an Event Log section with chronological simulation events
- **FR-027**: Dashboard MUST match the visual design language of the Node.js and .NET Core versions (CSS variables, color scheme, component styling)
- **FR-028**: System MUST provide a Documentation page with API reference and guides
- **FR-029**: System MUST provide an Azure Diagnostics page explaining how to diagnose issues in App Service
- **FR-030**: System MUST provide a Deploy to Azure page with GitHub Actions + OIDC setup instructions

**Safety & Control**

- **FR-013**: System SHOULD provide configurable limits on parameters, but these MUST be optional and disabled by default to allow full diagnostic stress testing
- **FR-014**: System MUST provide a "reset all" endpoint that releases allocated memory and allows pending operations to complete
- **FR-015**: System MUST remain responsive to health/status endpoints even under simulated stress conditions
- **FR-016**: System MUST display a prominent warning banner on the dashboard indicating this is a testing tool not for production use
- **FR-017**: System MUST support an environment variable (e.g., `DISABLE_PROBLEM_ENDPOINTS`) that disables all problem-triggering endpoints when set

**Documentation**

- **FR-018**: System MUST include inline code comments explaining each performance anti-pattern
- **FR-019**: System MUST include documentation describing how to observe each problem type in Azure monitoring tools

### Non-Functional Requirements

- **NFR-001**: Dashboard metrics MUST update within 2 seconds of state changes
- **NFR-002**: API response time MUST be under 2 seconds for non-simulation endpoints
- **NFR-003**: Application MUST support at least 10 concurrent dashboard connections
- **NFR-004**: Application MUST run on Azure App Service Linux (Python 3.11 blessed image)
- **NFR-005**: Application MUST be deployable via GitHub Actions using OIDC authentication to Azure
- **NFR-006**: Source code MUST be hosted in GitHub repository (https://github.com/rhamlett/perfsimpython)

### Key Entities

- **Simulation Request**: Represents a request to trigger a specific performance problem, including type (CPU/Memory/Blocking), parameters (duration, size), and timestamp
- **Application Health Status**: Current state including CPU percentage, memory metrics, thread statistics, and active simulations
- **Allocated Memory Block**: Memory intentionally held by the application, including size and allocation timestamp
- **Simulation Event**: Log entry recording simulation start/stop with relevant parameters

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can trigger high CPU (>90% utilization) within 5 seconds of endpoint invocation and sustain it for the requested duration (±5 seconds accuracy)
- **SC-002**: Users can allocate memory in configurable increments with no upper limit, with actual allocation within 10% of requested amount
- **SC-003**: Synchronous blocking symptoms (response time increase >500% for unrelated requests) are observable within 30 seconds of triggering blocking with concurrent operations
- **SC-004**: Dashboard metrics refresh within 2 seconds of actual state changes
- **SC-005**: Application recovers to baseline performance within 60 seconds after stopping all problem simulations
- **SC-006**: All code implementing anti-patterns includes explanatory comments that a junior developer can understand
- **SC-007**: A learner with basic Azure knowledge can successfully trigger and observe each problem type within 15 minutes using the included documentation

## Assumptions

- Source code is hosted at https://github.com/rhamlett/perfsimpython on the `main` branch
- Deployment to Azure uses GitHub Actions with OIDC (OpenID Connect) for passwordless authentication
- The application will be deployed to Azure App Service for production demonstration, but will also run locally for development and learning
- Users have basic familiarity with web APIs and HTTP requests (e.g., can use a browser, curl, or Postman)
- Azure monitoring tools (Azure Monitor, Application Insights) are available but not required for basic functionality
- Python 3.11+ is available on the target platform
- Memory allocation limits are constrained by the App Service plan tier

## Clarifications

### Session 2026-03-13

- Q: What web framework should be used? → A: FastAPI for modern async support and automatic OpenAPI documentation
- Q: Should Application Insights integration be built-in? → A: Optional via configuration using OpenCensus or Azure Monitor OpenTelemetry
- Q: What UI approach for the dashboard? → A: Single-page application with WebSocket updates using vanilla JavaScript
- Q: What API style? → A: RESTful with action-oriented endpoints (e.g., `/api/cpu/start`, `/api/memory/allocate`)
- Q: How to handle health endpoints under stress? → A: Use a dedicated thread/worker for metrics collection
