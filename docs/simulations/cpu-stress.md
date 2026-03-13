# CPU Stress Simulation

This simulation creates sustained high CPU usage using Python multiprocessing workers that perform intensive floating-point calculations.

## Overview

| Property | Value |
|----------|-------|
| Endpoint | `POST /api/cpu/start` |
| Stop Endpoint | `POST /api/cpu/stop` |
| Status Endpoint | `GET /api/cpu/status` |
| Default Workers | Number of CPU cores |
| Default Duration | 60 seconds |
| Impact | High CPU utilization |

## How It Works

The simulation spawns multiple worker processes using Python's `multiprocessing` module. Each worker executes a tight loop performing floating-point math operations (square roots, sine/cosine, multiplication).

```python
def _do_work(duration: float) -> None:
    """CPU-intensive work function."""
    end_time = time.time() + duration
    while time.time() < end_time:
        # Floating point operations
        result = 0.0
        for i in range(100000):
            result += math.sqrt(i) * math.sin(i) * math.cos(i)
```

### Why Multiprocessing?

Python's Global Interpreter Lock (GIL) prevents true parallel execution of Python code in threads. To actually consume multiple CPU cores, we use separate processes via multiprocessing.

## API Usage

### Start CPU Stress

```bash
# Start with defaults (all cores, 60 seconds)
curl -X POST http://localhost:8000/api/cpu/start

# Custom configuration
curl -X POST http://localhost:8000/api/cpu/start \
  -H "Content-Type: application/json" \
  -d '{"workers": 4, "duration_seconds": 300}'
```

**Request Body:**
```json
{
  "workers": 4,           // Number of worker processes (1-16)
  "duration_seconds": 300 // Duration in seconds (1-3600)
}
```

**Response:**
```json
{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "workers_started": 4,
  "duration_seconds": 300,
  "started_at": "2024-01-15T10:30:00Z",
  "message": "CPU stress simulation started"
}
```

### Check Status

```bash
curl http://localhost:8000/api/cpu/status
```

**Response:**
```json
{
  "is_running": true,
  "active_workers": 4,
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "started_at": "2024-01-15T10:30:00Z",
  "running_for_seconds": 45
}
```

### Stop CPU Stress

```bash
curl -X POST http://localhost:8000/api/cpu/stop
```

**Response:**
```json
{
  "message": "CPU stress simulation stopped",
  "workers_terminated": 4
}
```

## Diagnostic Signatures

### Azure Monitor Metrics

- **CPU Percentage** > 80% sustained
- All cores show similar high utilization
- Clear correlation with simulation start/stop times

### Application Insights

- **Performance** blade shows elevated response times
- No specific operation is slower (all affected equally)
- Request rate may drop due to resource contention

### py-spy Flame Graph

```
_do_work (90% of samples)
└── math operations (sqrt, sin, cos)
```

The flame graph shows `_do_work` dominating CPU time with mathematical functions.

### Process Explorer (Kudu/htop)

- Multiple Python/python3 processes
- Each showing ~100% CPU per core
- Parent process (uvicorn) has moderate CPU

## Observing the Impact

1. **Start the simulation** with 4 workers
2. **Watch the dashboard** - CPU chart spikes
3. **Make test requests** - Response times increase slightly
4. **Check htop** - See multiple Python processes at high CPU
5. **Run py-spy** - Observe `_do_work` function dominating
6. **Stop the simulation** - CPU returns to baseline

## Diagnostic Exercise

### Objective
Practice identifying CPU-bound performance issues using Azure tools.

### Steps

1. **Establish Baseline**
   - Record normal CPU percentage in Azure Monitor
   - Note typical response times in Application Insights

2. **Trigger the Problem**
   ```bash
   curl -X POST http://localhost:8000/api/cpu/start \
     -d '{"workers": 4, "duration_seconds": 300}'
   ```

3. **Investigate in Azure**
   - Azure Monitor > Metrics > CPU Percentage
   - App Service Diagnostics > High CPU Usage
   - Application Insights > Live Metrics

4. **Deep Dive**
   - SSH into container
   - Run `htop` to see process-level CPU
   - Use `py-spy top --pid <pid>` to see hot functions

5. **Correlate and Document**
   - Screenshot metrics graphs
   - Note time correlation
   - Document the diagnostic path

6. **Resolve**
   ```bash
   curl -X POST http://localhost:8000/api/cpu/stop
   ```

7. **Verify Resolution**
   - Confirm CPU returns to baseline
   - Response times normalize

## Variations

### Single Core Stress

```bash
curl -X POST http://localhost:8000/api/cpu/start \
  -d '{"workers": 1, "duration_seconds": 120}'
```

Useful for comparing per-core vs multi-core diagnostics.

### Maximum Stress

```bash
curl -X POST http://localhost:8000/api/cpu/start \
  -d '{"workers": 16, "duration_seconds": 60}'
```

Simulates worst-case CPU exhaustion (may affect responsiveness).

### Long-Running

```bash
curl -X POST http://localhost:8000/api/cpu/start \
  -d '{"workers": 2, "duration_seconds": 3600}'
```

For extended diagnostic practice sessions.

## Real-World Analogies

This simulation mimics:

- **Machine learning inference** without proper batching
- **Image processing** operations
- **Cryptographic operations** (hashing, encryption)
- **Data compression/decompression**
- **Complex calculations** in tight loops
- **Infinite loops** (bugs)

## Troubleshooting

### Workers Don't Start

- Check if already running (`GET /api/cpu/status`)
- Verify sufficient system resources
- Check application logs for errors

### CPU Not Reaching 100%

- Container may have CPU limits
- Reduce worker count if exceeding available cores
- Check for other resource constraints

### Simulation Doesn't Stop

If normal stop fails:
```bash
# Via admin endpoint
curl -X POST http://localhost:8000/api/admin/reset \
  -H "Content-Type: application/json" \
  -d '{"confirm": "yes"}'
```

## Related

- [Memory Pressure Simulation](memory-pressure.md)
- [Azure Diagnostics Guide](../azure-diagnostics.md)
- [Linux Tools Guide](../linux-tools.md)
