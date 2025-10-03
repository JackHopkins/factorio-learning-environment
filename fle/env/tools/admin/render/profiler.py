"""Performance profiling utilities for the rendering system."""

import time
import functools
import json
from typing import Dict, Optional, Any, Callable
from collections import defaultdict, deque
from pathlib import Path
import threading
from contextlib import contextmanager


class PerformanceProfiler:
    """Centralized performance profiler for the rendering system."""

    def __init__(self, max_samples: int = 1000):
        """Initialize the profiler.

        Args:
            max_samples: Maximum number of samples to keep per metric
        """
        self._data = defaultdict(lambda: deque(maxlen=max_samples))
        self._counters = defaultdict(int)
        self._active_timers = {}
        self._thread_local = threading.local()
        self._enabled = True

    def enable(self):
        """Enable profiling."""
        self._enabled = True

    def disable(self):
        """Disable profiling."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if profiling is enabled."""
        return self._enabled

    @contextmanager
    def timer(self, operation: str, metadata: Optional[Dict] = None):
        """Context manager for timing operations.

        Args:
            operation: Name of the operation being timed
            metadata: Additional metadata to include with the timing
        """
        if not self._enabled:
            yield
            return

        start_time = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start_time
            self.record_timing(operation, elapsed, metadata)

    def record_timing(
        self, operation: str, elapsed: float, metadata: Optional[Dict] = None
    ):
        """Record a timing measurement.

        Args:
            operation: Name of the operation
            elapsed: Time elapsed in seconds
            metadata: Additional metadata
        """
        if not self._enabled:
            return

        entry = {
            "timestamp": time.time(),
            "elapsed": elapsed,
            "metadata": metadata or {},
        }
        self._data[operation].append(entry)

    def increment_counter(self, counter: str, value: int = 1):
        """Increment a counter.

        Args:
            counter: Name of the counter
            value: Value to increment by
        """
        if not self._enabled:
            return

        self._counters[counter] += value

    def get_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for an operation.

        Args:
            operation: Name of the operation

        Returns:
            Dictionary containing timing statistics
        """
        if operation not in self._data or not self._data[operation]:
            return {"count": 0, "total": 0, "avg": 0, "min": 0, "max": 0}

        timings = [entry["elapsed"] for entry in self._data[operation]]
        return {
            "count": len(timings),
            "total": sum(timings),
            "avg": sum(timings) / len(timings),
            "min": min(timings),
            "max": max(timings),
            "recent_avg": sum(timings[-10:]) / min(len(timings), 10),
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all operations."""
        stats = {}
        for operation in self._data.keys():
            stats[operation] = self.get_stats(operation)
        return stats

    def get_counters(self) -> Dict[str, int]:
        """Get all counter values."""
        return dict(self._counters)

    def get_report(self) -> str:
        """Generate a performance report."""
        lines = ["=== Performance Report ===", ""]

        # Timing statistics
        lines.append("Timing Statistics:")
        stats = self.get_all_stats()
        if stats:
            lines.append(
                f"{'Operation':<30} {'Count':<8} {'Total(s)':<10} {'Avg(ms)':<10} {'Min(ms)':<10} {'Max(ms)':<10}"
            )
            lines.append("-" * 88)

            # Sort by total time descending
            sorted_ops = sorted(
                stats.items(), key=lambda x: x[1]["total"], reverse=True
            )
            for operation, data in sorted_ops:
                lines.append(
                    f"{operation:<30} {data['count']:<8} {data['total']:<10.3f} "
                    f"{data['avg'] * 1000:<10.2f} {data['min'] * 1000:<10.2f} {data['max'] * 1000:<10.2f}"
                )
        else:
            lines.append("No timing data collected")

        lines.append("")

        # Counters
        lines.append("Counters:")
        counters = self.get_counters()
        if counters:
            for counter, value in sorted(counters.items()):
                lines.append(f"{counter}: {value}")
        else:
            lines.append("No counter data collected")

        return "\n".join(lines)

    def save_report(self, filepath: Path):
        """Save performance report to file.

        Args:
            filepath: Path to save the report
        """
        with open(filepath, "w") as f:
            f.write(self.get_report())

    def export_data(self, filepath: Path):
        """Export raw profiling data to JSON.

        Args:
            filepath: Path to save the data
        """
        data = {
            "timings": {k: list(v) for k, v in self._data.items()},
            "counters": dict(self._counters),
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def clear(self):
        """Clear all profiling data."""
        self._data.clear()
        self._counters.clear()


# Global profiler instance
profiler = PerformanceProfiler()


def profile_function(operation_name: str = None, include_args: bool = False):
    """Decorator to profile function execution time.

    Args:
        operation_name: Custom name for the operation (defaults to function name)
        include_args: Whether to include function arguments in metadata
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not profiler.is_enabled():
                return func(*args, **kwargs)

            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            metadata = {}

            if include_args:
                # Include basic info about arguments
                metadata["arg_count"] = len(args)
                metadata["kwarg_count"] = len(kwargs)

                # Include specific argument info for key functions
                if "entity" in kwargs:
                    entity = kwargs["entity"]
                    if isinstance(entity, dict):
                        metadata["entity_name"] = entity.get("name", "unknown")
                    elif hasattr(entity, "name"):
                        metadata["entity_name"] = entity.name

            with profiler.timer(op_name, metadata):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def profile_method(operation_name: str = None, include_args: bool = False):
    """Decorator to profile method execution time.

    Args:
        operation_name: Custom name for the operation (defaults to class.method)
        include_args: Whether to include method arguments in metadata
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not profiler.is_enabled():
                return func(self, *args, **kwargs)

            op_name = operation_name or f"{self.__class__.__name__}.{func.__name__}"
            metadata = {}

            if include_args:
                metadata["arg_count"] = len(args)
                metadata["kwarg_count"] = len(kwargs)

            with profiler.timer(op_name, metadata):
                return func(self, *args, **kwargs)

        return wrapper

    return decorator
