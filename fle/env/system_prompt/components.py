"""
Modular system prompt components for flexible agent instruction generation.

This module provides a component-based approach to building system prompts,
allowing different agent designs to customize their instructions while
maintaining consistency in core functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class SystemPromptContext:
    """Context information for system prompt generation."""

    task_description: Optional[str] = None
    target_entity: Optional[str] = None
    target_quota: Optional[int] = None
    trajectory_length: Optional[int] = None
    agent_idx: Optional[int] = None
    num_agents: Optional[int] = None
    multiagent_enabled: bool = False
    technologies_researched: bool = False
    starting_inventory: Optional[Dict[str, int]] = None
    additional_context: Optional[Dict[str, Any]] = None


class SystemPromptComponent(ABC):
    """Base class for system prompt components."""

    @abstractmethod
    def generate(self, context: SystemPromptContext) -> str:
        """Generate the component's content."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Component identifier."""
        pass

    @property
    def priority(self) -> int:
        """Component ordering priority (lower = earlier)."""
        return 100


class TaskDefinitionComponent(SystemPromptComponent):
    """Component for task-specific instructions."""

    def __init__(self, task_template: str = "## Task\n{task_description}"):
        self.task_template = task_template

    def generate(self, context: SystemPromptContext) -> str:
        if not context.task_description:
            return ""
        return self.task_template.format(
            task_description=context.task_description,
            target_entity=context.target_entity or "",
            target_quota=context.target_quota or "",
        )

    @property
    def name(self) -> str:
        return "task_definition"

    @property
    def priority(self) -> int:
        return 10


class ProductionStatisticsComponent(SystemPromptComponent):
    """Component for production rate statistics."""

    def __init__(self, statistics: str):
        self.statistics = statistics

    def generate(self, context: SystemPromptContext) -> str:
        return f"## Production Statistics\n{self.statistics}"

    @property
    def name(self) -> str:
        return "production_statistics"

    @property
    def priority(self) -> int:
        return 20


class CoreInstructionsComponent(SystemPromptComponent):
    """Component for core behavioral instructions."""

    def __init__(self, instructions: str):
        self.instructions = instructions

    def generate(self, context: SystemPromptContext) -> str:
        return f"## Core Instructions\n{self.instructions}"

    @property
    def name(self) -> str:
        return "core_instructions"

    @property
    def priority(self) -> int:
        return 30


class MultiAgentComponent(SystemPromptComponent):
    """Component for multi-agent coordination instructions."""

    def generate(self, context: SystemPromptContext) -> str:
        if not context.multiagent_enabled or context.num_agents <= 1:
            return ""

        player_idx = (context.agent_idx or 0) + 1
        return f"""## Multi-Agent Instructions
You are Agent {player_idx} of {context.num_agents} agents in the game.
- Use send_message() to communicate with other agents about activities and challenges
- Start each program with send_message() to explain current actions
- End each program with send_message() to confirm completion
- Coordinate to avoid conflicts and maximize efficiency"""

    @property
    def name(self) -> str:
        return "multiagent"

    @property
    def priority(self) -> int:
        return 40


class ResponseFormatComponent(SystemPromptComponent):
    """Component for response format specifications."""

    def __init__(self, format_type: str = "gym"):
        self.format_type = format_type

    def generate(self, context: SystemPromptContext) -> str:
        if self.format_type == "gym":
            return """## Response Format

### 1. PLANNING Stage
Think through each step, addressing:
- Current game state analysis
- Next logical step of reasonable scope
- Required actions and resources

### 2. POLICY Stage
Write Python code to execute planned actions:
```python
# Your code here (≤30 lines)
```"""

        elif self.format_type == "mcts":
            return """## Response Format

Think step-by-step in Python comments, then write clean code:
```python
# Plan your approach here
your_code_here()
```

Use assert statements for self-verification with specific messages."""

        return ""

    @property
    def name(self) -> str:
        return "response_format"

    @property
    def priority(self) -> int:
        return 50


class ImplementationPatternsComponent(SystemPromptComponent):
    """Component for common implementation patterns."""

    def __init__(self, patterns: Dict[str, str]):
        self.patterns = patterns

    def generate(self, context: SystemPromptContext) -> str:
        if not self.patterns:
            return ""

        content = ["## Implementation Patterns"]
        for pattern_name, pattern_code in self.patterns.items():
            content.append(f"\n### {pattern_name}")
            content.append(f"```python\n{pattern_code}\n```")

        return "\n".join(content)

    @property
    def name(self) -> str:
        return "implementation_patterns"

    @property
    def priority(self) -> int:
        return 60


class ConstraintsComponent(SystemPromptComponent):
    """Component for behavioral constraints and rules."""

    def __init__(self, constraints: List[str]):
        self.constraints = constraints

    def generate(self, context: SystemPromptContext) -> str:
        if not self.constraints:
            return ""

        content = ["## Critical Rules"]
        for constraint in self.constraints:
            content.append(f"- {constraint}")

        return "\n".join(content)

    @property
    def name(self) -> str:
        return "constraints"

    @property
    def priority(self) -> int:
        return 70


class APIReferenceComponent(SystemPromptComponent):
    """Component for API method documentation."""

    def __init__(self, api_docs: str, include_full: bool = False):
        self.api_docs = api_docs
        self.include_full = include_full

    def generate(self, context: SystemPromptContext) -> str:
        if not self.api_docs:
            return ""

        if self.include_full:
            return f"## API Reference\n{self.api_docs}"
        else:
            # Extract just method signatures for conciseness
            lines = self.api_docs.split("\n")
            signatures = [
                line
                for line in lines
                if "(" in line and ")" in line and not line.strip().startswith("#")
            ]
            return "## Available Methods\n" + "\n".join(
                f"- {sig.strip()}" for sig in signatures[:15]
            )

    @property
    def name(self) -> str:
        return "api_reference"

    @property
    def priority(self) -> int:
        return 80


# Predefined component sets for different agent types

MINIMAL_COMPONENTS = ["task_definition", "response_format", "constraints"]

STANDARD_COMPONENTS = [
    "task_definition",
    "production_statistics",
    "core_instructions",
    "multiagent",
    "response_format",
    "constraints",
    "api_reference",
]

COMPREHENSIVE_COMPONENTS = [
    "task_definition",
    "production_statistics",
    "core_instructions",
    "multiagent",
    "response_format",
    "implementation_patterns",
    "constraints",
    "api_reference",
]
