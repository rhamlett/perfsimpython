# Synchronous (Thread) Blocking Simulation

This simulation demonstrates thread pool starvation by using `time.sleep()` in synchronous code paths, which is the correct way to handle blocking operations in async frameworks when using thread pools.

## Overview

| Property | Value |
|----------|-------|
| Endpoint | `POST /api/blocking/sync` |
| Default Duration | 10 seconds |
| Impact | Thread pool exhaustion |
| Pattern | Correct pattern for sync work |

## How It Works

When handling blocking operations in an async framework like FastAPI, the correct approach is to use `run_in_executor()` to offload blocking work to a thread pool. This endpoint demonstrates what happens when the thread pool becomes exhausted.

```python
@router.post("/sync")
async def sync_blocking(request: BlockingRequest) -> BlockingResponse:
    """Synchronous blocking - uses thread pool correctly."""
    loop = asyncio.get_event_loop()
    
    # Run blocking code in thread pool
    await loop.run_in_executor(
        None,  # Default executor
        lambda: time.sleep(request.duration_seconds)
    )
    
    return BlockingResponse(
        message="Sync blocking completed",
        blocked_for=request.duration_seconds
    )
```

### Thread Pool Behavior

- FastAPI uses a default thread pool for executor operations
- Each `run_in_executor()` call occupies one thread
- Default pool size is typically `min(32, os.cpu_count() + 4)`
- When exhausted, new requests queue waiting for threads

## API Usage

### Trigger Sync Blocking

```bash
# Default 10 second block
curl -X POST http://localhost:8000/api/blocking/sync

# Custom duration
curl -X POST http://localhost:8000/api/blocking/sync \
  -H "Content-Type: application/json" \
  -d '{"duration_seconds": 30}'
```

**Request Body:**
```json
{
  "duration_seconds": 30  // Blocking duration (1-300)
}
```

**Response:**
```json
{
  "message": "Sync blocking completed",
  "blocked_for": 30,
  "blocking_type": "sync"
}
```

## Diagnostic Signatures

### Observable Pattern

- **Some** requests complete quickly
- **Some** requests are slow (waiting for threads)
- Bimodal latency distribution
- Throughput limited by thread pool size

### Azure Application Insights

- Performance blade shows varied response times
- No all-requests-slow pattern (unlike async blocking)
- Dependency calls show normal timing
- Server response time correlates with thread availability

### Metrics

- Request queue grows when pool exhausted
- CPU may be low (threads sleeping)
- Memory stable
- No clear single bottleneck

### Log Patterns

```
Request 1: 30050ms (blocked full duration)
Request 2: 30002ms (blocked full duration)
Request 3: 60010ms (waited for thread, then blocked)
Request 4: 60005ms (waited for thread, then blocked)
```

## Observing the Impact

### Setup

1. Open multiple terminal windows
2. Have dashboard open in browser
3. Prepare concurrent requests

### Execute

```bash
# Terminal 1-4: Send concurrent blocking requests
for i in {1..4}; do
  curl -X POST http://localhost:8000/api/blocking/sync \
    -d '{"duration_seconds": 30}' &
done

# Terminal 5: Try to access health endpoint
time curl http://localhost:8000/api/health
```

### Observe

- First N requests (up to thread pool size) start immediately
- Excess requests queue
- Health check still responds (different thread pool or route)
- Response times vary based on thread availability

## Diagnostic Exercise

### Objective
Learn to identify thread pool starvation patterns.

### Steps

1. **Establish Baseline**
   - Make several health check requests
   - Note typical response times

2. **Exhaust Thread Pool**
   ```bash
   # Send more requests than thread pool size
   for i in {1..40}; do
     curl -X POST http://localhost:8000/api/blocking/sync \
       -d '{"duration_seconds": 60}' &
   done
   ```

3. **Observe Queuing**
   - In Application Insights, watch Live Metrics
   - See request queue building
   - Note bimodal latency pattern

4. **Test Other Endpoints**
   - Try health checks
   - Try metrics endpoint
   - Some may still work (async endpoints)

5. **Wait for Completion**
   - After 60s, first batch completes
   - Queued requests start executing
   - Pattern repeats until all done

6. **Analyze Logs**
   - Look for request timing patterns
   - Identify queued vs immediate requests

## Comparison: Sync vs Async Blocking

| Aspect | Sync Blocking | Async Blocking |
|--------|---------------|----------------|
| Mechanism | Thread pool | Event loop |
| Impact Scope | Requests using threads | ALL requests |
| Latency Pattern | Bimodal | Uniform high |
| CPU Usage | Low | Very low |
| Proper Pattern? | Yes (with limits) | No (anti-pattern) |
| Recovery | Automatic (thread frees) | Automatic (but worse) |

## Thread Pool Configuration

### Default Behavior

```python
# Python's default thread pool
import concurrent.futures
executor = concurrent.futures.ThreadPoolExecutor()
# Size: min(32, os.cpu_count() + 4)
```

### Custom Thread Pool

```python
# In application setup
from concurrent.futures import ThreadPoolExecutor

custom_executor = ThreadPoolExecutor(max_workers=50)

# Use in handler
await loop.run_in_executor(custom_executor, blocking_function)
```

### Monitoring Thread Pool

```python
executor._work_queue.qsize()  # Queued items
len(executor._threads)         # Active threads
```

## Variations

### Light Load

```bash
# Few requests, short duration
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/blocking/sync \
    -d '{"duration_seconds": 5}' &
done
```

Should complete without queuing issues.

### Heavy Load

```bash
# More requests than threads, long duration
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/blocking/sync \
    -d '{"duration_seconds": 60}' &
done
```

Demonstrates severe thread pool exhaustion.

### Mixed Workload

```bash
# Combine with other requests
for i in {1..20}; do
  curl -X POST http://localhost:8000/api/blocking/sync \
    -d '{"duration_seconds": 30}' &
  curl http://localhost:8000/api/health &
done
```

Shows impact on mixed traffic.

## Real-World Analogies

This simulation mimics:

- **Database queries** without connection pooling
- **File I/O operations** that block
- **External HTTP calls** using synchronous libraries
- **Legacy library** integration
- **Subprocess execution** blocking
- **Hardware device** communication

## Best Practices for Real Applications

### Do

- Use `run_in_executor()` for blocking operations
- Configure appropriate thread pool sizes
- Monitor thread pool metrics
- Use async libraries when possible
- Implement timeouts for blocking calls

### Don't

- Call blocking functions directly in async handlers
- Assume default thread pool is sufficient
- Ignore thread pool exhaustion warnings
- Use sync libraries for high-concurrency scenarios

## Troubleshooting

### Requests Never Complete

- Check for deadlocks
- Verify thread pool isn't completely blocked
- Consider timeout implementation

### Unexpected Timeouts

- Thread pool may be exhausted
- Increase pool size or reduce blocking duration
- Check for thread leaks

### Performance Degradation Over Time

- Monitor thread creation/destruction
- Check for thread pool exhaustion patterns
- Review connection pool settings

## Related

- [Async Blocking Simulation](async-blocking.md)
- [Slow Requests Simulation](slow-requests.md)
- [Azure Diagnostics Guide](../azure-diagnostics.md)
