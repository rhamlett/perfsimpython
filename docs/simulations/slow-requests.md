# Slow Requests Simulation

This simulation creates artificial latency to practice diagnosing slow response issues without resource exhaustion.

## Overview

| Property | Value |
|----------|-------|
| Endpoint | `GET /api/slow` |
| Default Delay | 5 seconds |
| Max Delay | 300 seconds (5 minutes) |
| Impact | Individual request latency |

## How It Works

The endpoint uses `asyncio.sleep()` to add artificial delay without blocking other requests. This is the correct async pattern - the event loop remains free to handle other work.

```python
@router.get("/")
async def slow_request(delay_seconds: float = 5.0) -> SlowResponse:
    """Generate a slow response with configurable delay."""
    start_time = datetime.utcnow()
    
    # Non-blocking sleep
    await asyncio.sleep(delay_seconds)
    
    end_time = datetime.utcnow()
    actual_delay = (end_time - start_time).total_seconds()
    
    return SlowResponse(
        message="Slow response completed",
        requested_delay=delay_seconds,
        actual_delay=actual_delay,
        started_at=start_time,
        completed_at=end_time
    )
```

### Why Not Blocking?

Unlike the async blocking simulation, this uses `await asyncio.sleep()` which:
- Yields control to the event loop
- Allows other requests to be processed
- Only delays this specific request

## API Usage

### Simple Slow Request

```bash
# Default 5 second delay
curl http://localhost:8000/api/slow

# Custom delay via query parameter
curl "http://localhost:8000/api/slow?delay_seconds=30"
```

**Response:**
```json
{
  "message": "Slow response completed",
  "requested_delay": 30.0,
  "actual_delay": 30.001,
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:30:30Z"
}
```

### Multiple Concurrent Requests

```bash
# All these run concurrently (different from blocking!)
curl "http://localhost:8000/api/slow?delay_seconds=10" &
curl "http://localhost:8000/api/slow?delay_seconds=10" &
curl "http://localhost:8000/api/slow?delay_seconds=10" &
wait
# All complete around the same time (~10s total, not 30s)
```

## Diagnostic Signatures

### Observable Pattern

- Individual requests are slow
- Other requests continue normally
- Dashboard keeps updating
- Throughput not significantly impacted

### Azure Application Insights

- **Performance blade**: Shows operation-specific latency
- **End-to-end transaction**: Request duration matches delay
- **Dependencies**: No external dependency delays
- **Sampling**: May miss short delays if sample rate is low

### Comparison with Resource Issues

| Symptom | Slow Request | CPU Stress | Memory Pressure |
|---------|--------------|------------|-----------------|
| Other requests | Normal | All slow | Normal initially |
| Resource usage | Normal | High CPU | High memory |
| Pattern | Predictable | Sustained | Growing |
| Recovery | Immediate | After stop | After release |

## Observing the Impact

### Setup

1. Open dashboard - confirm updates working
2. Open Application Insights Live Metrics
3. Prepare multiple terminals

### Execute

```bash
# Terminal 1: Make slow request
time curl "http://localhost:8000/api/slow?delay_seconds=30"

# Terminal 2: During the slow request, check health
time curl http://localhost:8000/api/health
# Response: ~200ms (normal!)
```

### Observe

- Dashboard continues updating during slow request
- Health checks respond normally
- Only the slow request is delayed
- Application Insights shows one slow transaction

## Diagnostic Exercise

### Objective
Practice identifying slow endpoints vs systemic issues.

### Steps

1. **Establish Baseline**
   - Record typical endpoint response times
   - Note Application Insights performance baseline

2. **Trigger Slow Requests**
   ```bash
   # Multiple slow requests
   for i in {1..10}; do
     curl "http://localhost:8000/api/slow?delay_seconds=20" &
   done
   ```

3. **Verify System Health**
   ```bash
   # Should respond quickly
   curl http://localhost:8000/api/health
   curl http://localhost:8000/api/metrics
   ```

4. **Analyze in Application Insights**
   - Go to Performance blade
   - Find `/api/slow` operation
   - Click to see transaction details
   - Note: No dependencies, just server time

5. **Compare with Real Slow Endpoints**
   - Real slow endpoints usually have:
     - Database query time
     - External API calls
     - File I/O
   - This simulation has only server processing time

6. **Document the Pattern**
   - Slow request ≠ system problem
   - Look for correlation with dependencies
   - Check if specific operation or all operations

## Use Case Scenarios

### Simulating Database Latency

```bash
# Simulate a slow database query
curl "http://localhost:8000/api/slow?delay_seconds=5"
```

In real applications, you'd see this as:
- Application Insights dependency showing database call
- SQL profiler showing slow query
- Database metrics showing high DTU/CPU

### Simulating External API Latency

```bash
# Simulate slow third-party API
curl "http://localhost:8000/api/slow?delay_seconds=10"
```

In real applications:
- Dependency showing HTTP call duration
- Network insights showing latency to endpoint
- Possible timeout errors

### SLA Testing

```bash
# Test behavior at different latencies
for delay in 1 2 5 10 30; do
  echo "Testing ${delay}s delay..."
  time curl -s "http://localhost:8000/api/slow?delay_seconds=$delay" > /dev/null
done
```

## Variations

### Quick Response

```bash
curl "http://localhost:8000/api/slow?delay_seconds=0.5"
```

Half-second delay - tests millisecond precision.

### Timeout Testing

```bash
# Test client timeout behavior
curl --max-time 10 "http://localhost:8000/api/slow?delay_seconds=30"
# Will timeout after 10 seconds
```

### Load with Latency

```bash
# Many concurrent slow requests
for i in {1..100}; do
  curl "http://localhost:8000/api/slow?delay_seconds=10" &
done
wait
```

Should all complete around the same time (async handling).

## Real-World Analogies

This simulation mimics:

- **Slow database queries** (missing indexes, complex joins)
- **External API latency** (third-party services)
- **File system operations** (large file reads)
- **Network latency** (distant services)
- **Queue processing** delays
- **Rate limiting** backoff periods

## Investigating Real Slow Requests

### Application Insights Approach

1. **Performance blade** > Find slow operation
2. **Drill into samples** > Select a slow request
3. **End-to-end transaction** > See timeline:
   - Server receive time
   - Processing time
   - Dependency calls
   - Response time

### Common Causes

| Cause | AI Signature | Fix |
|-------|--------------|-----|
| Slow DB query | Long SQL dependency | Add indexes, optimize query |
| External API | Long HTTP dependency | Add caching, circuit breaker |
| Large response | Transfer time high | Pagination, compression |
| Processing | Server time high | Optimize code, async |

### KQL Query for Slow Requests

```kql
requests
| where timestamp > ago(1h)
| where duration > 5000  // Over 5 seconds
| project timestamp, name, duration, resultCode
| order by duration desc
| take 20
```

## Troubleshooting

### Delay Not Matching Request

- Check for request queuing
- Verify server time vs total time
- Consider network latency

### Other Requests Also Slow

- This shouldn't happen with this endpoint
- If it does, check for event loop blocking elsewhere
- Verify using correct `/api/slow` endpoint

## Related

- [Thread Blocking Simulation](thread-blocking.md)
- [Async Blocking Simulation](async-blocking.md)
- [Azure Diagnostics Guide](../azure-diagnostics.md)
