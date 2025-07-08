"""Conversation formatting utilities for agents package."""

# Base formatter classes and utilities
from fle.agents.formatters.conversation_formatter_abc import (
    ConversationFormatter,
    DefaultFormatter,
    StructurePreservingFormatter,
    CodeProcessor,
    PLANNING_ADDITION_PROMPT,
)

# Advanced recursive formatter
from fle.agents.formatters.recursive_formatter import (
    RecursiveFormatter,
    DEFAULT_INSTRUCTIONS,
)

# Report formatter
from fle.agents.formatters.recursive_report_formatter import RecursiveReportFormatter

__all__ = [
    # Base classes
    "ConversationFormatter",
    "DefaultFormatter",
    "StructurePreservingFormatter",
    "CodeProcessor",
    # Advanced formatters
    "RecursiveFormatter",
    "RecursiveReportFormatter",
    # Constants
    "PLANNING_ADDITION_PROMPT",
    "DEFAULT_INSTRUCTIONS",
]
