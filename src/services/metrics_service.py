"""Metrics service for system and process monitoring.

Uses psutil to collect CPU, memory, and process metrics
for display in the dashboard and health endpoints.
"""

import os
from dataclasses import dataclass

import psutil


@dataclass
class SystemMetrics:
    """System-level metrics for WebSocket broadcasting.

    Attributes:
        cpu_percent: System-wide CPU usage percentage.
        memory_percent: System memory usage percentage.
        memory_available_bytes: Available memory in bytes.
        memory_total_bytes: Total system memory in bytes.
    """

    cpu_percent: float
    memory_percent: float
    memory_available_bytes: int
    memory_total_bytes: int


@dataclass
class BroadcastProcessMetrics:
    """Process metrics for WebSocket broadcasting.

    Attributes:
        cpu_percent: Process CPU usage percentage.
        memory_rss_bytes: Process resident set size in bytes.
        threads: Number of threads.
    """

    cpu_percent: float
    memory_rss_bytes: int
    threads: int


@dataclass
class MemoryMetrics:
    """System memory metrics.

    Attributes:
        total_mb: Total system memory in megabytes.
        available_mb: Available memory in megabytes.
        used_mb: Used memory in megabytes.
        percent: Memory usage as a percentage.
    """

    total_mb: float
    available_mb: float
    used_mb: float
    percent: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_mb": round(self.total_mb, 2),
            "available_mb": round(self.available_mb, 2),
            "used_mb": round(self.used_mb, 2),
            "percent": round(self.percent, 2),
        }


@dataclass
class ProcessMetrics:
    """Current process metrics.

    Attributes:
        pid: Process ID.
        memory_mb: Process memory usage in megabytes.
        cpu_percent: Process CPU usage percentage.
        threads: Number of threads.
        open_files: Number of open file descriptors.
    """

    pid: int
    memory_mb: float
    cpu_percent: float
    threads: int
    open_files: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "pid": self.pid,
            "memory_mb": round(self.memory_mb, 2),
            "cpu_percent": round(self.cpu_percent, 2),
            "threads": self.threads,
            "open_files": self.open_files,
        }


class MetricsService:
    """Collects system and process metrics using psutil.

    This service provides methods to retrieve current CPU, memory,
    and process information for monitoring and diagnostics.
    """

    def __init__(self) -> None:
        """Initialize the metrics service."""
        self._process: psutil.Process | None = None
        # Initialize CPU percent tracking (first call always returns 0)
        psutil.cpu_percent(interval=None)

    @property
    def process(self) -> psutil.Process:
        """Get or create the current process reference."""
        if self._process is None:
            self._process = psutil.Process(os.getpid())
        return self._process

    def get_cpu_percent(self) -> float:
        """Get current system CPU usage percentage.

        Returns:
            CPU usage as a percentage (0-100).
        """
        return psutil.cpu_percent(interval=None)

    def get_cpu_count(self) -> int:
        """Get the number of CPU cores.

        Returns:
            Number of logical CPU cores.
        """
        return psutil.cpu_count() or 1

    def get_memory_info(self) -> MemoryMetrics:
        """Get current system memory information.

        Returns:
            MemoryMetrics with current memory state.
        """
        mem = psutil.virtual_memory()
        return MemoryMetrics(
            total_mb=mem.total / (1024 * 1024),
            available_mb=mem.available / (1024 * 1024),
            used_mb=mem.used / (1024 * 1024),
            percent=mem.percent,
        )

    def get_process_info(self) -> ProcessMetrics:
        """Get current process information.

        Returns:
            ProcessMetrics with current process state.
        """
        proc = self.process
        try:
            # Get memory info
            mem_info = proc.memory_info()
            memory_mb = mem_info.rss / (1024 * 1024)

            # Get CPU percent (process-specific), normalized to 0-100% of total CPU
            # psutil returns cumulative % across cores (e.g., 400% on 4 cores)
            cpu_count = psutil.cpu_count() or 1
            cpu_percent = proc.cpu_percent(interval=None) / cpu_count

            # Get thread count
            threads = proc.num_threads()

            # Get open files count (may fail on some OSes)
            try:
                open_files = len(proc.open_files())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                open_files = 0

            return ProcessMetrics(
                pid=proc.pid,
                memory_mb=memory_mb,
                cpu_percent=cpu_percent,
                threads=threads,
                open_files=open_files,
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Return default values if process info unavailable
            return ProcessMetrics(
                pid=os.getpid(),
                memory_mb=0.0,
                cpu_percent=0.0,
                threads=1,
                open_files=0,
            )

    def get_all_metrics(self) -> dict:
        """Get all metrics in a single call.

        Returns:
            Dictionary containing all system and process metrics.
        """
        return {
            "cpu_percent": round(self.get_cpu_percent(), 2),
            "cpu_count": self.get_cpu_count(),
            "memory": self.get_memory_info().to_dict(),
            "process": self.get_process_info().to_dict(),
        }

    def get_system_metrics(self) -> SystemMetrics:
        """Get system-level metrics for WebSocket broadcasting.

        Returns:
            SystemMetrics with CPU and memory information.
        """
        cpu = self.get_cpu_percent()
        mem = psutil.virtual_memory()
        return SystemMetrics(
            cpu_percent=cpu,
            memory_percent=mem.percent,
            memory_available_bytes=mem.available,
            memory_total_bytes=mem.total,
        )

    def get_process_metrics(self) -> BroadcastProcessMetrics:
        """Get process metrics for WebSocket broadcasting.

        Returns:
            BroadcastProcessMetrics with current process state.
        """
        proc = self.process
        try:
            mem_info = proc.memory_info()
            # Normalize CPU to 0-100% of total capacity
            cpu_count = psutil.cpu_count() or 1
            cpu = proc.cpu_percent(interval=None) / cpu_count
            threads = proc.num_threads()
            return BroadcastProcessMetrics(
                cpu_percent=cpu,
                memory_rss_bytes=mem_info.rss,
                threads=threads,
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return BroadcastProcessMetrics(
                cpu_percent=0.0,
                memory_rss_bytes=0,
                threads=1,
            )


# Global singleton instance
metrics_service = MetricsService()
