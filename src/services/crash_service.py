"""Crash simulation service.

Provides methods to trigger various types of application crashes
for practicing crash diagnostics and recovery procedures.

Warning:
    These methods will terminate the application process!
    Only use in controlled environments for educational purposes.
"""

import logging
import os
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class CrashType(StrEnum):
    """Types of crashes that can be simulated.

    Each type has a different diagnostic signature in Azure monitoring tools.
    """

    EXCEPTION = "exception"  # Unhandled exception - appears in logs/App Insights
    STACKOVERFLOW = "stackoverflow"  # Stack overflow - appears as RecursionError
    OOM = "oom"  # Out of memory - process killed by OS
    SIGABRT = "sigabrt"  # SIGABRT signal - immediate process termination
    FAILFAST = "failfast"  # Immediate process exit with os._exit(1)


class CrashService:
    """Service for simulating application crashes.

    ⚠️ WARNING: Crash methods will terminate the application! ⚠️

    Each crash type demonstrates different failure modes and
    creates different diagnostic signatures in Azure App Service:

    - EXCEPTION: Creates stack trace in logs and Application Insights
    - STACKOVERFLOW: Deep recursion exceeds Python's recursion limit
    - OOM: Allocates memory until OS kills the process
    - SIGABRT: Sends abort signal for immediate termination
    """

    def __init__(self) -> None:
        """Initialize the crash service."""
        self._crash_info: dict[CrashType, dict[str, Any]] = {
            CrashType.EXCEPTION: {
                "type": "exception",
                "description": (
                    "Raises an unhandled RuntimeError that propagates up the call stack. "
                    "This simulates unexpected application errors in production."
                ),
                "diagnostic_signature": (
                    "Stack trace in logs, exception recorded in Application Insights, "
                    "HTTP 500 response to client."
                ),
                "azure_tools": [
                    "Application Insights > Failures",
                    "App Service Logs > Application logs",
                    "Diagnose and solve problems > Application Crashes",
                ],
            },
            CrashType.STACKOVERFLOW: {
                "type": "stackoverflow",
                "description": (
                    "Triggers infinite recursion that exceeds Python's recursion limit "
                    "(default ~1000). Simulates infinite loops or unbounded recursion."
                ),
                "diagnostic_signature": (
                    "RecursionError in logs, rapid memory growth before crash, "
                    "process may be killed by OS if memory exhausted."
                ),
                "azure_tools": [
                    "Application Insights > Failures",
                    "Diagnose and solve problems > Memory analysis",
                    "Kudu > Process explorer",
                ],
            },
            CrashType.OOM: {
                "type": "oom",
                "description": (
                    "Allocates memory in an infinite loop until the operating system "
                    "kills the process (OOM killer on Linux)."
                ),
                "diagnostic_signature": (
                    "Sudden process termination without exception, "
                    "memory metrics spike before death, exit code 137 (killed)."
                ),
                "azure_tools": [
                    "Diagnose and solve problems > Memory analysis",
                    "Metrics > Memory percentage",
                    "Kudu > Process dump",
                ],
            },
            CrashType.SIGABRT: {
                "type": "sigabrt",
                "description": (
                    "Sends SIGABRT signal to the process using os.abort(). "
                    "This is an immediate, ungraceful termination."
                ),
                "diagnostic_signature": (
                    "Immediate termination, no logs written, exit code 134, "
                    "core dump may be generated."
                ),
                "azure_tools": [
                    "Diagnose and solve problems > Container issues",
                    "Activity log for restart events",
                    "Container logs for exit codes",
                ],
            },
            CrashType.FAILFAST: {
                "type": "failfast",
                "description": (
                    "Immediately terminates the process using os._exit(1). "
                    "This bypasses all cleanup, exception handlers, and finally blocks. "
                    "Equivalent to .NET Environment.FailFast()."
                ),
                "diagnostic_signature": (
                    "Immediate process termination with exit code 1, no exception logged, "
                    "no cleanup performed, connection lost without warning."
                ),
                "azure_tools": [
                    "Diagnose and solve problems > Application Crashes",
                    "Activity log for restart events",
                    "Container logs for exit codes",
                    "Application Insights > Availability",
                ],
            },
        }

    def get_crash_info(self, crash_type: CrashType) -> dict[str, Any]:
        """Get information about a crash type.

        Args:
            crash_type: The type of crash.

        Returns:
            Dictionary with crash information.
        """
        return self._crash_info[crash_type]

    def get_all_crash_types(self) -> list[dict[str, Any]]:
        """Get information about all crash types.

        Returns:
            List of crash type information dictionaries.
        """
        return list(self._crash_info.values())

    def validate_crash_type(self, crash_type_str: str) -> bool:
        """Validate if a string is a valid crash type.

        Args:
            crash_type_str: String to validate.

        Returns:
            True if valid crash type, False otherwise.
        """
        try:
            CrashType(crash_type_str)
            return True
        except ValueError:
            return False

    def trigger_crash(self, crash_type: CrashType) -> None:
        """Trigger the specified crash type.

        ⚠️ WARNING: This will terminate the application! ⚠️

        Args:
            crash_type: The type of crash to trigger.

        Raises:
            RuntimeError: For exception crash type.
        """
        logger.critical(
            "!!! CRASH TRIGGERED !!! Type: %s - Application will terminate!",
            crash_type.value,
        )

        if crash_type == CrashType.EXCEPTION:
            self._trigger_exception()
        elif crash_type == CrashType.STACKOVERFLOW:
            self._trigger_stackoverflow()
        elif crash_type == CrashType.OOM:
            self._trigger_oom()
        elif crash_type == CrashType.SIGABRT:
            self._trigger_sigabrt()
        elif crash_type == CrashType.FAILFAST:
            self._trigger_failfast()

    def _trigger_exception(self) -> None:
        """Trigger an unhandled exception.

        This raises a RuntimeError that will propagate up and
        crash the application if not caught.
        """
        raise RuntimeError(
            "Intentional crash triggered by Performance Problem Simulator. "
            "This error simulates an unhandled exception in production."
        )

    def _trigger_stackoverflow(self) -> None:
        """Trigger a stack overflow via infinite recursion.

        This will exceed Python's recursion limit (sys.getrecursionlimit())
        and raise a RecursionError.
        """

        def recursive() -> None:
            recursive()

        recursive()

    def _trigger_oom(self) -> None:
        """Trigger out-of-memory by allocating memory indefinitely.

        This allocates large byte arrays in a loop until the OS
        kills the process. The exit code will typically be 137.
        """
        allocations: list[bytearray] = []
        chunk_size = 100 * 1024 * 1024  # 100MB chunks

        while True:
            allocations.append(bytearray(chunk_size))
            logger.info(
                "OOM: Allocated %d MB total",
                len(allocations) * 100,
            )

    def _trigger_sigabrt(self) -> None:
        """Trigger SIGABRT signal for immediate termination.

        This uses os.abort() to send SIGABRT to the process,
        causing immediate termination without cleanup.
        """
        os.abort()

    def _trigger_failfast(self) -> None:
        """Trigger immediate process termination using os._exit.

        This is equivalent to .NET's Environment.FailFast().
        The process exits immediately with code 1, bypassing all
        exception handlers, finally blocks, and cleanup routines.
        """
        # Flush stdout/stderr to ensure any pending output is written
        import sys

        sys.stdout.flush()
        sys.stderr.flush()
        # Exit immediately without cleanup
        os._exit(1)


# Global singleton instance
crash_service = CrashService()
