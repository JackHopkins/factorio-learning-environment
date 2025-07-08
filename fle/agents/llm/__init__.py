"""LLM utilities for agents package."""

# API and core functionality
from fle.agents.llm.api_factory import APIFactory

# Parsing utilities
from fle.agents.llm.parsing import Policy, PolicyMeta, PythonParser

# Metrics and performance tracking
from fle.agents.llm.metrics import (
    TimingTracker,
    timing_tracker,
    track_timing,
    track_timing_async,
    log_metrics,
    print_metrics,
)

# Utility functions
from fle.agents.llm.utils import (
    format_messages_for_anthropic,
    format_messages_for_openai,
    has_image_content,
    merge_contiguous_messages,
    remove_whitespace_blocks,
)

__all__ = [
    # API
    "APIFactory",
    # Parsing
    "Policy",
    "PolicyMeta",
    "PythonParser",
    # Metrics
    "TimingTracker",
    "timing_tracker",
    "track_timing",
    "track_timing_async",
    "log_metrics",
    "print_metrics",
    # Utils
    "format_messages_for_anthropic",
    "format_messages_for_openai",
    "has_image_content",
    "merge_contiguous_messages",
    "remove_whitespace_blocks",
]
