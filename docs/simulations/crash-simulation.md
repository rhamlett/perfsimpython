# Crash Simulation

This simulation demonstrates various application crash scenarios to practice analyzing crash dumps, logs, and automated recovery in Azure App Service.

## ⚠️ Safety Warning

**These endpoints will terminate the application process.** Azure App Service will automatically restart the container, but:
- Ongoing requests will be lost
- WebSocket connections will disconnect
- In-memory state will be lost

The endpoint requires explicit confirmation to prevent accidental crashes.

## Overview

| Property | Value |
|----------|-------|
| Endpoint | `POST /api/crash` |
| Confirmation Required | Yes (`confirm: "yes"`) |
| Available Types | exception, exit, segfault, oom |
| Impact | Process termination |

## Crash Types

### 1. Unhandled Exception

```bash
curl -X POST http://localhost:8000/api/crash \
  -H "Content-Type: application/json" \
  -d '{"type": "exception", "confirm": "yes"}'
```

**Behavior:**
- Raises an unhandled `RuntimeError`
- Error propagates through middleware
- Logged as 500 error
- Process may continue (FastAPI catches it)

**Diagnostic Signatures:**
- Application Insights: Exception event logged
- Logs: Full stack trace
- No process restart (usually)

### 2. Forced Exit

```bash
curl -X POST http://localhost:8000/api/crash \
  -H "Content-Type: application/json" \
  -d '{"type": "exit", "confirm": "yes"}'
```

**Behavior:**
- Calls `sys.exit(1)` with error code
- Process terminates immediately
- Container orchestrator restarts

**Diagnostic Signatures:**
- Exit code: 1
- Logs: "Exit requested via API"
- App Service: Restart event logged
- Short downtime window

### 3. Segmentation Fault

```bash
curl -X POST http://localhost:8000/api/crash \
  -H "Content-Type: application/json" \
  -d '{"type": "segfault", "confirm": "yes"}'
```

**Behavior:**
- Uses ctypes to trigger segfault
- Immediate process termination
- Core dump generated (if enabled)

**Diagnostic Signatures:**
- Exit code: -11 (SIGSEGV)
- Logs: May be truncated
- Core dump in `/home/LogFiles/`
- App Service: Crash restart logged

### 4. Out of Memory (OOM)

```bash
curl -X POST http://localhost:8000/api/crash \
  -H "Content-Type: application/json" \
  -d '{"type": "oom", "confirm": "yes"}'
```

**Behavior:**
- Rapidly allocates memory until OOM
- Killed by OOM killer
- Container restarted

**Diagnostic Signatures:**
- Exit code: 137 (SIGKILL)
- Logs: "Killed" message
- App Service: Memory limit hit
- Azure Monitor: Memory spike then drop

## API Usage

### Request Body

```json
{
  "type": "exception",  // exception, exit, segfault, oom
  "confirm": "yes"      // Required confirmation
}
```

### Response (before crash)

For crash types that allow a response:
```json
{
  "message": "Crash initiated",
  "crash_type": "exit",
  "warning": "Process will terminate"
}
```

**Note:** For immediate crashes (segfault, oom), you may not receive a response.

### Missing Confirmation Error

```bash
curl -X POST http://localhost:8000/api/crash \
  -H "Content-Type: application/json" \
  -d '{"type": "exit"}'
```

```json
{
  "error": "Crash not confirmed",
  "message": "Set confirm='yes' to proceed"
}
```

## Diagnostic Signatures Summary

| Crash Type | Exit Code | Logs | AI Exception | Restart |
|------------|-----------|------|--------------|---------|
| exception | N/A | Full stack trace | Yes | No |
| exit | 1 | Clean exit message | No | Yes |
| segfault | -11 (139) | Truncated | No | Yes |
| oom | -9 (137) | "Killed" | No | Yes |

## Observing the Impact

### Setup

1. Open App Service in Azure Portal
2. Navigate to Diagnose and solve problems
3. Open Application Insights > Failures
4. Have terminal ready for curl commands

### Execute Exception Crash

```bash
curl -X POST http://localhost:8000/api/crash \
  -d '{"type": "exception", "confirm": "yes"}'
```

**Observe:**
- 500 response returned
- Exception in Application Insights
- Process typically continues

### Execute Exit Crash

```bash
curl -X POST http://localhost:8000/api/crash \
  -d '{"type": "exit", "confirm": "yes"}'
```

**Observe:**
- Connection may hang then fail
- Dashboard disconnects
- App Service restarts container
- Service recovers in ~10-30 seconds

## Diagnostic Exercise

### Objective
Practice crash analysis and understand recovery mechanisms.

### Steps

1. **Prepare Monitoring**
   - Open Azure Portal > App Service
   - Open Application Insights > Failures
   - Open Log Analytics with this query ready:
     ```kql
     AppExceptions
     | where timestamp > ago(1h)
     | order by timestamp desc
     ```

2. **Trigger Exception**
   ```bash
   curl -X POST http://localhost:8000/api/crash \
     -d '{"type": "exception", "confirm": "yes"}'
   ```

3. **Analyze Exception**
   - Check Application Insights > Failures
   - Find the RuntimeError exception
   - Review full stack trace
   - Note: Process didn't restart

4. **Trigger Exit**
   ```bash
   curl -X POST http://localhost:8000/api/crash \
     -d '{"type": "exit", "confirm": "yes"}'
   ```

5. **Observe Restart**
   - Watch App Service > Overview for restart
   - Check logs for exit message
   - Time the recovery period

6. **Trigger Segfault (Advanced)**
   ```bash
   curl -X POST http://localhost:8000/api/crash \
     -d '{"type": "segfault", "confirm": "yes"}'
   ```

7. **Analyze Core Dump**
   - SSH into container via Kudu
   - Look for core dump files
   - Check exit code in logs

8. **Trigger OOM (Advanced)**
   ```bash
   curl -X POST http://localhost:8000/api/crash \
     -d '{"type": "oom", "confirm": "yes"}'
   ```

9. **Analyze OOM**
   - Check Azure Monitor memory metrics
   - See spike then sudden drop
   - Verify SIGKILL in logs

## Recovery Mechanisms

### Azure App Service Auto-Healing

App Service automatically:
1. Detects process crash
2. Waits briefly for clean shutdown
3. Starts new container instance
4. Routes traffic to new instance

Configure custom rules in:
**App Service > Diagnose and solve problems > Auto-Heal**

### Health Check Integration

```json
// In App Service configuration
{
  "healthCheckPath": "/api/health",
  "healthCheckInterval": 30
}
```

Failed health checks trigger restart.

### Multiple Instances

With scaling enabled:
- Other instances handle traffic during restart
- Single crash doesn't cause downtime
- Load balancer routes around failed instance

## Exit Codes Reference

| Code | Signal | Meaning |
|------|--------|---------|
| 0 | - | Clean exit |
| 1 | - | Application error |
| 137 | SIGKILL (9) | Killed (OOM killer) |
| 139 | SIGSEGV (11) | Segmentation fault |
| 143 | SIGTERM (15) | Graceful termination |

### Interpreting Exit Codes

```bash
# Linux exit code formula
# If killed by signal: 128 + signal_number
# SIGKILL (9): 128 + 9 = 137
# SIGSEGV (11): 128 + 11 = 139
```

## Log Analysis

### App Service Logs

```bash
# Via Kudu SSH
cat /home/LogFiles/docker/*.log | tail -100
```

### KQL Queries

**Recent Exceptions:**
```kql
exceptions
| where timestamp > ago(1h)
| summarize count() by type, outerMessage
| order by count_ desc
```

**Crash Correlation:**
```kql
traces
| where timestamp > ago(1h)
| where message contains "exit" or message contains "crash"
| project timestamp, message, severityLevel
| order by timestamp desc
```

## Variations

### Exception with Custom Message

Modify the crash service to include custom data in the exception.

### Delayed Crash

```python
# Internal implementation variant
async def delayed_crash():
    await asyncio.sleep(5)
    sys.exit(1)
```

### Crash Recovery Testing

```bash
# Script to test recovery time
start_time=$(date +%s)
curl -X POST http://localhost:8000/api/crash \
  -d '{"type": "exit", "confirm": "yes"}' || true
while ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; do
  sleep 1
done
end_time=$(date +%s)
echo "Recovery time: $((end_time - start_time)) seconds"
```

## Real-World Analogies

These crash types mimic:

| Crash Type | Real-World Cause |
|------------|------------------|
| exception | Unhandled null reference, validation failure |
| exit | Config error on startup, fatal assertion |
| segfault | C extension bug, memory corruption |
| oom | Memory leak, large data processing |

## Best Practices

### For This Simulation

1. Only use in isolated test environments
2. Inform team before triggering crashes
3. Have monitoring ready before testing
4. Document all observations

### For Production

1. Implement proper exception handling
2. Use health checks
3. Enable auto-healing
4. Configure alerts for crash patterns
5. Use multiple instances for redundancy

## Troubleshooting

### Crash Doesn't Trigger

- Verify confirmation is "yes" (exact string)
- Check crash type is valid
- Review error response for details

### Recovery Takes Too Long

- Check auto-healing configuration
- Review container startup time
- Consider warm-up configuration

### No Logs After Crash

- Severe crashes may truncate logs
- Check earlier log entries
- Enable diagnostic settings for better capture

## Related

- [Memory Pressure Simulation](memory-pressure.md) - Gradual OOM
- [Azure Diagnostics Guide](../azure-diagnostics.md) - Crash analysis tools
- [Linux Tools Guide](../linux-tools.md) - Log analysis commands
