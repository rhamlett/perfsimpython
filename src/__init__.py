"""Performance Problem Simulator - Python Edition.

An educational application for simulating common performance problems
to help Azure support engineers practice diagnostics.

Simulation Types:
- CPU Stress: Trigger controlled CPU spikes
- Memory Pressure: Allocate and release memory blocks
- Blocking: Demonstrate sync/async blocking patterns
- Slow Requests: Generate configurable response delays
- Crash Simulation: Trigger various crash types

Usage:
    uvicorn src.main:app --reload

For more information, see the documentation at /docs.html
"""

from datetime import datetime, timezone

__version__ = "1.0.0"
__author__ = "Azure Support Engineering"

# Capture build time at module load (matches Java pattern)
BUILD_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") + " UTC"
