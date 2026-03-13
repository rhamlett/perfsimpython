# Asynchronous (Event Loop) Blocking Simulation

This simulation demonstrates a critical anti-pattern: blocking the event loop in async code, which causes ALL concurrent requests to stall simultaneously.

## ⚠️ Anti-Pattern Warning

**This is an anti-pattern demonstration.** Never block the event loop in production code. This simulation exists to help you recognize the diagnostic signatures of this common mistake.

## Overview

| Property | Value |
|----------|-------|
| Endpoint | `POST /api/blocking/async` |
| Default Duration | 10 seconds |
| Impact | All requests blocked |
| Pattern | **Anti-pattern** - DO NOT USE |

## How It Works

The endpoint uses `time.sleep()` directly in an async function instead of `asyncio.sleep()`. This blocks the entire event loop, preventing all other async operations from proceeding.

```python
@router.post("/async")
async def async_blocking(request: BlockingRequest) -> BlockingResponse:
    """
    Async blocking - BAD PATTERN.
    Blocks the event loop, affecting ALL concurrent requests.
    """
    # WRONG: This blocks the event loop!
    time.sleep(request.duration_seconds)
    
    return BlockingResponse(
        message="Async blocking completed",
        blocked_for=request.duration_seconds
    )
```

### The Correct Pattern

```python
@router.post("/async-correct")
async def async_non_blocking(request: BlockingRequest) -> BlockingResponse:
    """Correct pattern using asyncio.sleep()."""
    await asyncio.sleep(request.duration_seconds)
    return BlockingResponse(message="Completed", blocked_for=request.duration_seconds)
```

## API Usage

### Trigger Event Loop Blocking

```bash
# Default 10 second block
curl -X POST http://localhost:8000/api/blocking/async

# Custom duration
curl -X POST http://localhost:8000/api/blocking/async \
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
  "message": "Async blocking completed",
  "blocked_for": 30,
  "blocking_type": "async"
}
```

## Diagnostic Signatures

### Observable Pattern

The key signature is **all requests become slow simultaneously**:

- Request A blocks for 30s
- Requests B, C, D arrive during the block
- ALL of them wait until A completes
- Then B, C, D complete quickly (unless they also block)

### Azure Application Insights

- **Live Metrics**: Sudden drop to zero throughput
- **Performance**: All operations show similar high latency
- **Server requests**: Flat response time across the board

### Dashboard Behavior

- WebSocket updates **stop** (can't process frames)
- Charts freeze
- Events stop appearing
- Entire UI becomes unresponsive

### Comparison with Sync Blocking

| Symptom | Sync Blocking | Async Blocking |
|---------|---------------|----------------|
| Some requests fast? | Yes | No |
| WebSocket works? | Yes | No |
| Health checks? | Usually work | Also blocked |
| Latency pattern | Bimodal | Uniform high |

## Observing the Impact

### Setup

1. Open the dashboard in a browser
2. Watch the real-time metrics charts
3. Note the event log updating

### Execute

```bash
# Terminal 1: Block the event loop
curl -X POST http://localhost:8000/api/blocking/async \
  -d '{"duration_seconds": 30}'
```

### Observe

**During the block:**
- Dashboard charts **freeze**
- No new events appear
- WebSocket reconnection may occur
- In another terminal: health check hangs

```bash
# Terminal 2: This will hang!
time curl http://localhost:8000/api/health
# ... waits until blocking completes...
```

**After the block:**
- Dashboard updates resume
- Queued requests complete
- System returns to normal

## Diagnostic Exercise

### Objective
Learn to recognize event loop blocking as distinct from thread pool issues.

### Steps

1. **Establish Baseline**
   - Open dashboard, confirm real-time updates
   - Note health check response time
   - Watch charts updating

2. **Block the Event Loop**
   ```bash
   curl -X POST http://localhost:8000/api/blocking/async \
     -d '{"duration_seconds": 60}'
   ```

3. **Observe Total Freeze**
   - Dashboard stops updating immediately
   - Try health check - it hangs
   - Try metrics endpoint - hangs
   - Everything stops

4. **Compare with Sync Blocking**
   After recovery, try:
   ```bash
   curl -X POST http://localhost:8000/api/blocking/sync \
     -d '{"duration_seconds": 60}'
   ```
   Notice: dashboard keeps updating!

5. **Document the Difference**
   - Event loop blocking = total freeze
   - Thread blocking = partial impact

## Why This Happens

### Single-Threaded Event Loop

Python's asyncio uses a single-threaded event loop:

```
Event Loop (Single Thread)
├── Handle request A
├── Handle request B
├── Process WebSocket frame
├── Run scheduled callback
└── ... more tasks ...
```

When you call `time.sleep()`:

```
Event Loop (BLOCKED)
├── time.sleep(30)  <-- Blocks everything
│   └── Cannot proceed until done
├── Request B - WAITING
├── WebSocket - WAITING
└── Everything else - WAITING
```

### Async Cooperative Multitasking

`asyncio.sleep()` is cooperative:

```
Event Loop (Running)
├── await asyncio.sleep(30) - suspended
│   └── Control returns to event loop
├── Handle request B - can run
├── WebSocket frame - can process
├── Timer fires - callback runs
└── After 30s, A resumes
```

## Common Causes in Real Code

### 1. Synchronous HTTP Libraries

```python
# WRONG
async def get_data():
    response = requests.get("http://api.example.com")  # Blocks!
    return response.json()

# RIGHT
async def get_data():
    async with aiohttp.ClientSession() as session:
        async with session.get("http://api.example.com") as response:
            return await response.json()
```

### 2. Synchronous Database Drivers

```python
# WRONG
async def query_db():
    conn = psycopg2.connect(...)  # Blocks!
    cursor = conn.cursor()
    cursor.execute("SELECT ...")
    return cursor.fetchall()

# RIGHT
async def query_db():
    async with asyncpg.create_pool(...) as pool:
        async with pool.acquire() as conn:
            return await conn.fetch("SELECT ...")
```

### 3. File I/O

```python
# WRONG
async def read_file():
    with open("data.json") as f:
        return json.load(f)  # Blocks!

# RIGHT
async def read_file():
    async with aiofiles.open("data.json") as f:
        content = await f.read()
        return json.loads(content)
```

### 4. CPU-Bound Operations

```python
# WRONG
async def process_image():
    return heavy_computation(image)  # Blocks!

# RIGHT
async def process_image():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, heavy_computation, image)
```

## Detection Tools

### py-spy

When the event loop is blocked:

```bash
py-spy top --pid <pid>
```

Shows `time.sleep` (or blocking function) at 100%.

### asyncio Debug Mode

```python
import asyncio

# Enable debug mode
asyncio.get_event_loop().set_debug(True)

# Logs slow callbacks
# WARNING:asyncio:Executing <Task...> took 30.001 seconds
```

### Application Insights

Look for:
- Sudden uniform latency increase
- Zero throughput periods
- All endpoints affected equally

## Variations

### Brief Block

```bash
curl -X POST http://localhost:8000/api/blocking/async \
  -d '{"duration_seconds": 2}'
```

Brief freeze - might miss it if not watching closely.

### Long Block

```bash
curl -X POST http://localhost:8000/api/blocking/async \
  -d '{"duration_seconds": 120}'
```

Extended freeze - mimics severe production incident.

### Repeated Blocks

```bash
# Multiple sequential blocks
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/blocking/async \
    -d '{"duration_seconds": 10}'
done
```

## Troubleshooting Real Applications

### Identifying the Culprit

1. **Check for sync libraries**: requests, psycopg2, etc.
2. **Review recent changes**: New dependencies?
3. **Profile with py-spy**: Find blocking calls
4. **Add async debugging**: Enable asyncio debug mode

### Fixes

1. **Replace sync with async libraries**
2. **Use run_in_executor() for blocking code**
3. **Implement proper async patterns**
4. **Add timeouts to prevent indefinite blocks**

## Related

- [Thread Blocking Simulation](thread-blocking.md)
- [Slow Requests Simulation](slow-requests.md)
- [Azure Diagnostics Guide](../azure-diagnostics.md)
