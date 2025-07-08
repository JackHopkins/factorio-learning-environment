import functools
import logging
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Dict, List, Optional

from fle.commons.models.timing_metrics import TimingMetrics

logger = logging.getLogger(__name__)


class TimingTracker:
    """Tracks timing metrics for operations"""

    def __init__(self):
        self.metrics: List[TimingMetrics] = []
        self._current_operation: Optional[TimingMetrics] = None
        self._operation_stack: List[TimingMetrics] = []

    @contextmanager
    def track(self, operation_name: str, **metadata):
        """Context manager for tracking operation timing"""
        metrics = TimingMetrics(
            operation_name=operation_name, start_time=time.time(), metadata=metadata
        )

        if self._current_operation:
            self._current_operation.children.append(metrics)
        else:
            self.metrics.append(metrics)

        self._operation_stack.append(metrics)
        self._current_operation = metrics

        try:
            yield metrics
        finally:
            metrics.end_time = time.time()
            self._operation_stack.pop()
            self._current_operation = (
                self._operation_stack[-1] if self._operation_stack else None
            )

    @asynccontextmanager
    async def track_async(self, operation_name: str, **metadata):
        """Async context manager for tracking operation timing"""
        metrics = TimingMetrics(
            operation_name=operation_name, start_time=time.time(), metadata=metadata
        )

        if self._current_operation:
            self._current_operation.children.append(metrics)
        else:
            self.metrics.append(metrics)

        self._operation_stack.append(metrics)
        self._current_operation = metrics

        try:
            yield metrics
        finally:
            metrics.end_time = time.time()
            self._operation_stack.pop()
            self._current_operation = (
                self._operation_stack[-1] if self._operation_stack else None
            )

    def get_metrics(self) -> List[Dict[str, Any]]:
        """Get all metrics in dictionary format"""
        return [metric.to_dict() for metric in self.metrics]

    def clear(self):
        """Clear all metrics"""
        self.metrics.clear()
        self._current_operation = None
        self._operation_stack.clear()


# Global performance tracker instance
timing_tracker = TimingTracker()


def track_timing(operation_name: Optional[str] = None):
    """Decorator for tracking function performance"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            with timing_tracker.track(
                name, function=func.__name__, args=args, kwargs=kwargs
            ):
                return func(*args, **kwargs)

        return wrapper

    if callable(operation_name):
        # Handle case where decorator is used without parentheses
        func = operation_name
        operation_name = None
        return decorator(func)
    return decorator


def track_timing_async(operation_name: Optional[str] = None):
    """Decorator for tracking async function performance"""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            async with timing_tracker.track_async(name, function=func.__name__):
                return await func(*args, **kwargs)

        return wrapper

    if callable(operation_name):
        # Handle case where decorator is used without parentheses
        func = operation_name
        operation_name = None
        return decorator(func)
    return decorator


def print_metrics(metrics: List[Dict[str, Any]], indent: int = 0):
    """Print metrics in a hierarchical format with proper indentation and colors"""
    indent_str = "  " * indent
    for metric in metrics:
        duration = metric["duration"]
        total_duration = metric["total_duration"]
        operation = metric["operation"]
        metadata = metric.get("metadata", {})

        # Format metadata for display
        meta_str = ""
        if metadata:
            meta_parts = []
            for key, value in metadata.items():
                if key == "tokens":
                    meta_parts.append(f"tokens={value}")
                elif key == "reasoning_length":
                    meta_parts.append(f"reasoning={value}")
                elif key == "llm":
                    meta_parts.append(f"llm={value}")
                elif key == "model":
                    meta_parts.append(f"model={value}")
            if meta_parts:
                meta_str = f" ({', '.join(meta_parts)})"

        # Calculate unaccounted time
        unacc = duration - total_duration
        timing_str = f"{duration:.3f}s"
        if unacc > 0.1:
            timing_str += f" (unacc: {unacc:.3f}s)"

        # Print the metric
        print(f"{indent_str}\033[93m{operation}{meta_str}:\033[0m {timing_str}")

        # Print children
        if metric.get("children"):
            print_metrics(metric["children"], indent + 1)


def log_metrics():
    """Log all collected metrics"""
    metrics = timing_tracker.get_metrics()
    print("\n\033[94mTiming Metrics:\033[0m")
    print_metrics(metrics)
    timing_tracker.clear()
