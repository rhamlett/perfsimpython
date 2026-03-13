# Linux Diagnostic Tools Guide

This guide covers using Linux command-line tools to diagnose performance issues in Python applications running on Azure App Service (Linux containers) or any Linux environment.

## Accessing the Shell

### Azure App Service SSH

1. Azure Portal > App Service > **SSH** (under Development Tools)
2. Or Kudu: `https://<your-app>.scm.azurewebsites.net/webssh/host`

### Docker Container

```bash
# Get container ID
docker ps

# Execute shell
docker exec -it <container_id> /bin/bash
```

## Process Monitoring

### top - System Overview

```bash
# Basic top view
top

# Sort by CPU (default)
top -o %CPU

# Sort by memory
top -o %MEM

# Batch mode (one snapshot, useful for logging)
top -b -n 1

# Filter by user
top -u www-data
```

**Key Metrics:**
- `%CPU` - CPU utilization per process
- `%MEM` - Memory utilization
- `VIRT` - Virtual memory (total addressable)
- `RES` - Resident memory (actually used)
- `SHR` - Shared memory

### htop - Interactive Process Viewer

```bash
# Install if needed
apt-get install htop

# Run htop
htop

# Show tree view
htop -t
```

**htop Advantages:**
- Color-coded
- Mouse support
- Process tree view
- Easier sorting (F6)
- Kill processes (F9)

### ps - Process Status

```bash
# Find Python processes
ps aux | grep python

# Detailed Python process info
ps -p $(pgrep -f uvicorn) -o pid,ppid,cmd,%cpu,%mem,rss,vsz

# Show all threads
ps -eLf | grep python

# Tree view
ps axjf
```

## Memory Analysis

### free - Memory Overview

```bash
# Human-readable
free -h

# Show in megabytes
free -m

# Continuous monitoring (every 2 seconds)
free -h -s 2
```

**Interpreting Output:**
```
              total        used        free      shared  buff/cache   available
Mem:          7.7Gi       2.1Gi       3.2Gi       256Mi       2.4Gi       5.1Gi
Swap:         2.0Gi          0B       2.0Gi
```

- `available` is what matters for new allocations
- `buff/cache` can be reclaimed if needed

### Memory Maps

```bash
# Process memory map
cat /proc/$(pgrep -f uvicorn)/maps

# Memory summary
cat /proc/$(pgrep -f uvicorn)/status | grep -E 'Vm|Rss|Threads'

# Detailed memory breakdown
pmap -x $(pgrep -f uvicorn)
```

## CPU Analysis

### mpstat - CPU Statistics

```bash
# Install sysstat if needed
apt-get install sysstat

# CPU stats per second
mpstat 1

# Per-CPU breakdown
mpstat -P ALL 1
```

### Tracking High CPU

```bash
# Find top CPU consumers
ps aux --sort=-%cpu | head -10

# Watch CPU over time
while true; do ps aux --sort=-%cpu | head -5; sleep 2; done
```

## Python-Specific Tools

### py-spy - Sampling Profiler

```bash
# Install
pip install py-spy

# Real-time top view
py-spy top --pid $(pgrep -f uvicorn)

# Record profile (30 seconds) to flamegraph
py-spy record -o profile.svg --pid $(pgrep -f uvicorn) --duration 30

# Sample rate (default 100Hz)
py-spy top --rate 200 --pid $(pgrep -f uvicorn)

# Include native frames (C extensions)
py-spy top --native --pid $(pgrep -f uvicorn)
```

**py-spy Output Interpretation:**
```
  %Own   %Total  OwnTime  TotalTime  Function (filename:line)
 45.00%  45.00%    0.45s     0.45s   _do_work (cpu_stress_service.py:42)
 20.00%  65.00%    0.20s     0.65s   stress_cpu (cpu_stress_service.py:30)
```

- `%Own` - Time in this function only
- `%Total` - Time in this function + callees
- High `%Own` = optimization target

### cProfile - Built-in Profiler

```python
# In code
import cProfile
import pstats

# Profile a function
with cProfile.Profile() as pr:
    result = function_to_profile()

stats = pstats.Stats(pr)
stats.sort_stats(pstats.SortKey.CUMULATIVE)
stats.print_stats(20)

# From command line
python -m cProfile -s cumulative script.py
```

### memory_profiler - Line-by-Line Memory

```bash
# Install
pip install memory_profiler

# Profile a script
python -m memory_profiler script.py
```

```python
# Decorator usage
from memory_profiler import profile

@profile
def my_func():
    a = [1] * 1000000
    del a
    return
```

### tracemalloc - Memory Tracing

```python
import tracemalloc

# Start tracing
tracemalloc.start()

# ... allocate memory ...

# Take snapshot
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

# Show top allocations
for stat in top_stats[:10]:
    print(stat)

# Compare snapshots
snapshot1 = tracemalloc.take_snapshot()
# ... more allocations ...
snapshot2 = tracemalloc.take_snapshot()

top_stats = snapshot2.compare_to(snapshot1, 'lineno')
for stat in top_stats[:10]:
    print(stat)
```

## Network Diagnostics

### netstat/ss - Network Connections

```bash
# Active connections
netstat -tuln

# Connections to port 8000
netstat -an | grep 8000

# Using ss (modern replacement)
ss -tuln

# Connection states
ss -s
```

### lsof - Open Files/Sockets

```bash
# Files opened by Python
lsof -p $(pgrep -f uvicorn)

# Network connections by Python
lsof -i -p $(pgrep -f uvicorn)

# Count open files
lsof -p $(pgrep -f uvicorn) | wc -l
```

### File Descriptor Limits

```bash
# Current limits
ulimit -n

# Per-process FD usage
ls -l /proc/$(pgrep -f uvicorn)/fd | wc -l

# System-wide FD usage
cat /proc/sys/fs/file-nr
```

## I/O Analysis

### iostat - Disk I/O

```bash
# Basic I/O stats
iostat

# Extended stats, every 2 seconds
iostat -x 2

# Specific device
iostat -x sda 1
```

### iotop - Per-Process I/O

```bash
# Install
apt-get install iotop

# Run (requires root)
iotop

# Show only active processes
iotop -o
```

## Log Analysis

### journalctl - System Logs

```bash
# Follow logs
journalctl -f

# Filter by unit
journalctl -u <service-name>

# Since last boot
journalctl -b

# Time range
journalctl --since "2024-01-01" --until "2024-01-02"
```

### Application Logs

```bash
# Follow Python app logs
tail -f /var/log/app.log

# Last 100 lines
tail -100 /var/log/app.log

# Search for errors
grep -i error /var/log/app.log

# Count errors by type
grep -o "ERROR.*" /var/log/app.log | sort | uniq -c | sort -rn
```

## Strace - System Call Tracing

```bash
# Trace a running process
strace -p $(pgrep -f uvicorn)

# Trace specific calls
strace -e open,read,write -p $(pgrep -f uvicorn)

# Summary of calls
strace -c -p $(pgrep -f uvicorn)

# Follow child processes
strace -f -p $(pgrep -f uvicorn)
```

## Diagnostic Scripts

### Quick Health Check

```bash
#!/bin/bash
echo "=== System Overview ==="
uptime
echo ""
echo "=== Memory ==="
free -h
echo ""
echo "=== CPU ==="
mpstat 1 1 2>/dev/null || echo "mpstat not available"
echo ""
echo "=== Top Processes ==="
ps aux --sort=-%cpu | head -5
echo ""
echo "=== Python Processes ==="
ps aux | grep python
echo ""
echo "=== Network Connections ==="
ss -tuln | head -10
```

### Memory Leak Detection

```bash
#!/bin/bash
PID=$(pgrep -f uvicorn)
echo "Monitoring PID: $PID"
while true; do
    RSS=$(ps -p $PID -o rss= 2>/dev/null)
    if [ -z "$RSS" ]; then
        echo "Process ended"
        break
    fi
    echo "$(date '+%H:%M:%S') RSS: ${RSS}KB"
    sleep 5
done
```

### CPU Spike Capture

```bash
#!/bin/bash
PID=$(pgrep -f uvicorn)
THRESHOLD=80

while true; do
    CPU=$(ps -p $PID -o %cpu= 2>/dev/null)
    CPU=${CPU%.*}  # Remove decimal
    
    if [ "$CPU" -gt "$THRESHOLD" ]; then
        echo "HIGH CPU DETECTED: ${CPU}%"
        py-spy record -o "profile_$(date +%s).svg" --pid $PID --duration 10 &
    fi
    sleep 2
done
```

## Azure App Service Specifics

### Container Environment

```bash
# Environment variables
env | sort

# Container metadata
cat /etc/os-release

# Mounted volumes
df -h

# Container limits (if cgroups v2)
cat /sys/fs/cgroup/memory.max
cat /sys/fs/cgroup/cpu.max
```

### Kudu Environment

```bash
# Web app root
cd /home/site/wwwroot

# Log files
ls -la /home/LogFiles/

# App Service logs
cat /home/LogFiles/docker/*.log
```

## Best Practices

1. **Always record baseline** - Know normal before diagnosing abnormal
2. **Use multiple tools** - Cross-reference findings
3. **Profile in production** - py-spy has minimal overhead
4. **Correlate with app metrics** - Combine Linux tools with Application Insights
5. **Script recurring diagnostics** - Automate data collection
6. **Consider security** - Some tools require elevated privileges
7. **Document findings** - Keep notes for future reference

## Tool Installation Summary

```bash
# Debian/Ubuntu
apt-get update && apt-get install -y \
    htop \
    sysstat \
    iotop \
    lsof \
    strace

# Python tools
pip install \
    py-spy \
    memory_profiler
```
