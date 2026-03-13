# Azure Diagnostics Guide

This guide covers using Azure diagnostic tools to identify and troubleshoot the performance problems created by this simulator.

## Problem Identification Matrix

| Symptom | Likely Cause | First Azure Tool to Check |
|---------|--------------|---------------------------|
| High response times, all requests | Event loop blocking | App Service Diagnostics > CPU Analysis |
| High response times, some requests | Slow requests or sync blocking | Application Insights > Performance |
| Gradual slowdown | Memory pressure | App Service Diagnostics > Memory Analysis |
| Sudden unresponsiveness | CPU stress | Azure Monitor Metrics > CPU Percentage |
| Random 500 errors | Crashes | Application Insights > Failures |
| Periodic issues | Resource exhaustion | Log Analytics > Custom queries |

## Azure App Service Diagnostics

### Accessing Diagnostics

1. Navigate to your App Service in Azure Portal
2. Select **Diagnose and solve problems** from the left menu
3. Choose a diagnostic category:
   - **Availability and Performance** - For response time issues
   - **High CPU Usage** - For CPU-bound problems
   - **High Memory Usage** - For memory pressure

### CPU Analysis

When you suspect CPU issues:

1. Go to **Diagnose and solve problems** > **High CPU Usage**
2. Select a time range when problems occurred
3. Review the **CPU Overview** for:
   - Overall CPU percentage
   - Per-instance breakdown
   - Correlation with deployments

### Memory Analysis

For memory pressure:

1. Go to **Diagnose and solve problems** > **High Memory Usage**
2. Review:
   - Memory usage percentage over time
   - Memory by process
   - Potential memory leaks

## Application Insights

### Enabling Application Insights

If not already configured:

```bash
# Via Azure CLI
az monitor app-insights component create \
  --app perf-simulator-insights \
  --location eastus \
  --resource-group perf-simulator-rg \
  --kind web

# Get the instrumentation key
az monitor app-insights component show \
  --app perf-simulator-insights \
  --resource-group perf-simulator-rg \
  --query instrumentationKey
```

### Performance Blade

1. Navigate to your Application Insights resource
2. Select **Performance** from the left menu
3. Review:
   - **Operations** - Overall request performance
   - **Dependencies** - External call latency
   - **Roles** - Multi-instance breakdown

### Investigating Slow Requests

1. In the Performance blade, click on a slow operation
2. Review the **Drill into samples** section
3. Click on a specific request to see:
   - Full request timeline
   - Dependencies called
   - Custom events logged
   - Exception details (if any)

### Live Metrics

For real-time monitoring:

1. Go to **Live Metrics** in Application Insights
2. This shows:
   - Request rate
   - Response times
   - Failure rates
   - Server health

Use this while triggering simulations to see immediate impact.

### Failures Blade

For crash investigation:

1. Navigate to **Failures** in Application Insights
2. Filter by:
   - Time range
   - Exception type
   - Operation name
3. Click through to see full stack traces

## Log Analytics Queries (KQL)

### Connecting to Log Analytics

1. Open your Application Insights resource
2. Select **Logs** from the left menu
3. Run Kusto Query Language (KQL) queries

### Useful Queries

#### High Latency Requests

```kql
requests
| where timestamp > ago(1h)
| where duration > 5000  // Over 5 seconds
| summarize count() by name, bin(timestamp, 5m)
| render timechart
```

#### CPU Correlation

```kql
performanceCounters
| where name == "% Processor Time"
| summarize avg(value) by bin(timestamp, 1m)
| join kind=inner (
    requests
    | where timestamp > ago(1h)
    | summarize avgDuration = avg(duration) by bin(timestamp, 1m)
) on timestamp
| render timechart
```

#### Exception Patterns

```kql
exceptions
| where timestamp > ago(1h)
| summarize count() by type, outerMessage
| order by count_ desc
```

#### Memory Growth

```kql
performanceCounters
| where name == "Available Bytes" or name == "Private Bytes"
| summarize avg(value) by name, bin(timestamp, 5m)
| render timechart
```

## Kudu Console (Advanced)

### Accessing Kudu

1. Navigate to: `https://<your-app>.scm.azurewebsites.net`
2. Or: Azure Portal > App Service > **Advanced Tools** > Go

### Process Explorer

1. In Kudu, go to **Process Explorer**
2. Find the Python process (usually `python` or `gunicorn`/`uvicorn`)
3. View:
   - CPU usage
   - Memory consumption
   - Thread count
   - Handle count

### SSH Console

1. Go to **SSH** in Kudu (for Linux containers)
2. Run diagnostic commands:

```bash
# Process status
ps aux | grep python

# Real-time CPU/Memory
top -b -n 1

# Memory details
free -h

# Open file descriptors
ls -l /proc/$(pgrep -f uvicorn)/fd | wc -l
```

## Profiling Python Applications

### Using py-spy (In Container)

```bash
# Install py-spy
pip install py-spy

# Sample the running process
py-spy top --pid <python_pid>

# Generate a flame graph
py-spy record -o profile.svg --pid <python_pid> -- sleep 30
```

### Using cProfile

Add temporary profiling to code:

```python
import cProfile
import pstats
from io import StringIO

pr = cProfile.Profile()
pr.enable()

# ... code to profile ...

pr.disable()
s = StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats(20)
print(s.getvalue())
```

### Memory Profiling with tracemalloc

```python
import tracemalloc

tracemalloc.start()

# ... code that might leak memory ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

print("[ Top 10 memory consumers ]")
for stat in top_stats[:10]:
    print(stat)
```

## Diagnostic Scenarios

### Scenario 1: High CPU

**Simulation:** `POST /api/cpu/start`

**Detection Path:**
1. Azure Monitor shows CPU > 80%
2. App Service Diagnostics > High CPU Usage
3. Application Insights > Performance shows all operations slow
4. Kudu Process Explorer shows Python process at high CPU
5. py-spy shows CPU-bound functions in `_do_work()`

**Resolution:** `POST /api/cpu/stop`

### Scenario 2: Memory Pressure

**Simulation:** `POST /api/memory/allocate` (multiple times)

**Detection Path:**
1. Azure Monitor shows memory growing
2. App Service Diagnostics > High Memory Usage
3. Application Insights may show OOM exceptions
4. Kudu shows increasing private bytes
5. tracemalloc shows large allocations

**Resolution:** `POST /api/memory/release-all` or app restart

### Scenario 3: Thread Blocking

**Simulation:** `POST /api/blocking/sync`

**Detection Path:**
1. Application Insights > Performance shows high latency
2. Some requests succeed quickly, others are very slow
3. Thread pool exhaustion visible
4. Live Metrics shows request queue building

**Resolution:** Wait for blocking to complete

### Scenario 4: Event Loop Blocking

**Simulation:** `POST /api/blocking/async`

**Detection Path:**
1. ALL requests become slow simultaneously
2. Application Insights shows uniform latency spike
3. WebSocket connections may timeout
4. Dashboard stops updating

**Explanation:** This is an anti-pattern. The async endpoint uses `time.sleep()` which blocks the event loop, affecting all concurrent requests.

### Scenario 5: Application Crash

**Simulation:** `POST /api/crash`

**Detection Path:**
1. Application Insights > Failures shows sudden spike
2. App Service automatically restarts
3. Logs show the crash type
4. Exit code varies by crash type

## Best Practices

1. **Always set up Application Insights** before deploying diagnostic workloads
2. **Use resource tags** to organize diagnostic resources
3. **Create alerts** for key metrics before testing
4. **Save diagnostic queries** in Log Analytics for reuse
5. **Document baseline metrics** for comparison
6. **Use deployment slots** for safer testing
7. **Clean up test resources** after sessions

## Related Resources

- [Azure App Service Diagnostics Documentation](https://learn.microsoft.com/en-us/azure/app-service/overview-diagnostics)
- [Application Insights for Python](https://learn.microsoft.com/en-us/azure/azure-monitor/app/opencensus-python)
- [KQL Quick Reference](https://learn.microsoft.com/en-us/azure/data-explorer/kql-quick-reference)
- [Kudu Wiki](https://github.com/projectkudu/kudu/wiki)
