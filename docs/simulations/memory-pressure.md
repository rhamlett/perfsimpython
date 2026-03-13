# Memory Pressure Simulation

This simulation creates memory pressure by allocating large byte arrays that are held in memory until explicitly released.

## Overview

| Property | Value |
|----------|-------|
| Allocate Endpoint | `POST /api/memory/allocate` |
| Release Endpoint | `POST /api/memory/release/{id}` |
| Release All Endpoint | `POST /api/memory/release-all` |
| Status Endpoint | `GET /api/memory/status` |
| Default Allocation | 100 MB |
| Impact | Increasing memory usage |

## How It Works

The simulation allocates byte arrays using Python's `bytearray` type. Each allocation:

1. Creates a `bytearray` of the specified size
2. Fills it with random data (prevents OS optimization)
3. Stores a reference to prevent garbage collection
4. Records metadata (ID, size, timestamp)

```python
def allocate(self, size_mb: int) -> AllocatedMemoryBlock:
    """Allocate a block of memory."""
    size_bytes = size_mb * 1024 * 1024
    
    # Create and fill the array
    data = bytearray(size_bytes)
    for i in range(0, len(data), 4096):
        data[i] = i % 256  # Touch each page
    
    block = AllocatedMemoryBlock(
        id=str(uuid4()),
        size_mb=size_mb,
        allocated_at=datetime.utcnow()
    )
    
    self._allocations[block.id] = data
    return block
```

### Memory Retention

The byte arrays are stored in a dictionary, preventing Python's garbage collector from reclaiming them. Memory is only released when:
- Explicitly released via API
- Application restarts
- Container is recycled

## API Usage

### Allocate Memory

```bash
# Allocate default 100 MB
curl -X POST http://localhost:8000/api/memory/allocate

# Allocate specific amount
curl -X POST http://localhost:8000/api/memory/allocate \
  -H "Content-Type: application/json" \
  -d '{"size_mb": 500}'
```

**Request Body:**
```json
{
  "size_mb": 500  // Size in megabytes (1-2048)
}
```

**Response:**
```json
{
  "block_id": "550e8400-e29b-41d4-a716-446655440000",
  "size_mb": 500,
  "allocated_at": "2024-01-15T10:30:00Z",
  "message": "Memory block allocated"
}
```

### Check Status

```bash
curl http://localhost:8000/api/memory/status
```

**Response:**
```json
{
  "total_allocated_mb": 1500,
  "allocation_count": 3,
  "allocations": [
    {
      "id": "block-1-uuid",
      "size_mb": 500,
      "allocated_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": "block-2-uuid",
      "size_mb": 500,
      "allocated_at": "2024-01-15T10:31:00Z"
    },
    {
      "id": "block-3-uuid",
      "size_mb": 500,
      "allocated_at": "2024-01-15T10:32:00Z"
    }
  ],
  "system_memory": {
    "total_mb": 8192,
    "available_mb": 4096,
    "percent_used": 50.0
  }
}
```

### Release Single Block

```bash
curl -X POST http://localhost:8000/api/memory/release/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "message": "Memory block released",
  "block_id": "550e8400-e29b-41d4-a716-446655440000",
  "size_mb": 500
}
```

### Release All Memory

```bash
curl -X POST http://localhost:8000/api/memory/release-all
```

**Response:**
```json
{
  "message": "All memory blocks released",
  "blocks_released": 3,
  "total_mb_freed": 1500
}
```

## Diagnostic Signatures

### Azure Monitor Metrics

- **Memory Percentage** steadily increasing
- Step pattern if allocating in increments
- Doesn't decrease without explicit release

### Application Insights

- No specific operation slowdown initially
- May see OOM exceptions at high usage
- GC pressure may cause latency spikes

### Linux Memory Tools

```bash
# Memory overview
free -h

# Process memory
ps aux --sort=-%mem | head -5

# Detailed process memory
cat /proc/$(pgrep -f uvicorn)/status | grep -E 'VmRSS|VmSize'
```

### Python Memory Profiling

```python
import tracemalloc
tracemalloc.start()

# ... allocations ...

snapshot = tracemalloc.take_snapshot()
for stat in snapshot.statistics('lineno')[:10]:
    print(stat)
```

Shows `memory_pressure_service.py` as top allocator.

## Observing the Impact

1. **Check baseline memory** via dashboard or `free -h`
2. **Allocate sequentially**:
   ```bash
   curl -X POST http://localhost:8000/api/memory/allocate -d '{"size_mb": 200}'
   # Repeat 5 times
   ```
3. **Watch memory chart** - See step increases
4. **Check status** - Review allocation breakdown
5. **Continue until pressure** - System memory becomes constrained
6. **Release all** - Memory returns to baseline

## Diagnostic Exercise

### Objective
Practice identifying memory leaks and pressure using Azure and Linux tools.

### Steps

1. **Establish Baseline**
   - Note memory percentage in Azure Monitor
   - SSH and run `free -h`

2. **Simulate Memory Leak**
   ```bash
   # Allocate 200MB every 10 seconds
   for i in {1..10}; do
     curl -X POST http://localhost:8000/api/memory/allocate \
       -d '{"size_mb": 200}'
     sleep 10
   done
   ```

3. **Observe Growth**
   - Azure Monitor > Metrics > Memory Percentage
   - Watch dashboard memory chart
   - App Service Diagnostics > High Memory Usage

4. **Investigate Source**
   - SSH into container
   - Run `ps aux --sort=-%mem | head -5`
   - Check `/proc/<pid>/status`

5. **Use Python Profiling**
   ```python
   # If you can modify code
   import tracemalloc
   tracemalloc.start()
   ```

6. **Correlate with Application**
   - Check `/api/memory/status` to see allocations
   - Match allocation times with memory growth

7. **Resolution**
   ```bash
   curl -X POST http://localhost:8000/api/memory/release-all
   ```

8. **Verify**
   - Confirm memory drops in Azure Monitor
   - `free -h` shows memory released

## Memory Pressure Levels

### Light Pressure (< 50% used)

- Application performs normally
- Good baseline for comparison
- OS has comfortable headroom

### Moderate Pressure (50-70% used)

- May see increased GC activity
- Slight latency variations
- Still within safe limits

### High Pressure (70-90% used)

- Significant GC pressure
- Noticeable latency increases
- Swap may be utilized
- Container may be warned

### Critical Pressure (> 90% used)

- Application may become unresponsive
- OOM killer may terminate process
- Container likely to be recycled
- Data loss possible

## Variations

### Gradual Growth

```bash
# Small allocations over time
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/memory/allocate \
    -d '{"size_mb": 10}'
  sleep 5
done
```

Simulates slow memory leak, harder to detect immediately.

### Large Single Allocation

```bash
curl -X POST http://localhost:8000/api/memory/allocate \
  -d '{"size_mb": 1024}'
```

Simulates loading a large dataset or cache.

### Near-OOM Condition

```bash
# Get available memory first, then allocate ~80%
total=$(free -m | awk '/^Mem:/{print $7}')
allocate=$((total * 80 / 100))
curl -X POST http://localhost:8000/api/memory/allocate \
  -d "{\"size_mb\": $allocate}"
```

⚠️ Use with caution - may trigger OOM killer.

## Real-World Analogies

This simulation mimics:

- **Memory leaks** from unclosed resources
- **Cache without eviction** policies
- **Large data loading** without streaming
- **Session data** accumulation
- **Unbounded collections** growth
- **Reference cycles** preventing GC

## Troubleshooting

### Allocation Fails

- Check available memory (`/api/memory/status`)
- Reduce allocation size
- Release existing allocations first

### Memory Not Decreasing After Release

- Python may not immediately return memory to OS
- Force GC: `import gc; gc.collect()`
- Container may need restart for full release

### OOM Errors

If application crashes:
1. App Service will auto-restart
2. Check logs for OOM messages
3. Reduce allocation sizes in future tests
4. Consider container memory limits

## Related

- [CPU Stress Simulation](cpu-stress.md)
- [Azure Diagnostics Guide](../azure-diagnostics.md)
- [Linux Tools Guide](../linux-tools.md)
