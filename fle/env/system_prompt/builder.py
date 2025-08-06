"""
SystemPromptBuilder for flexible composition of system prompts.

This module provides the main interface for building customized system prompts
from modular components, allowing different agent designs to specify exactly
what information they need.
"""

from typing import Dict, List, Optional, Set
from .components import (
    SystemPromptComponent,
    SystemPromptContext,
    TaskDefinitionComponent,
    ProductionStatisticsComponent,
    CoreInstructionsComponent,
    MultiAgentComponent,
    ResponseFormatComponent,
    ImplementationPatternsComponent,
    ConstraintsComponent,
    APIReferenceComponent,
    MINIMAL_COMPONENTS,
    STANDARD_COMPONENTS,
    COMPREHENSIVE_COMPONENTS,
)


class SystemPromptBuilder:
    """Builder for constructing customized system prompts from components."""

    def __init__(self):
        self.components: Dict[str, SystemPromptComponent] = {}
        self.enabled_components: Set[str] = set()
        self.context = SystemPromptContext()

    def with_task(
        self,
        description: str,
        entity: Optional[str] = None,
        quota: Optional[int] = None,
    ) -> "SystemPromptBuilder":
        """Add task information."""
        self.context.task_description = description
        self.context.target_entity = entity
        self.context.target_quota = quota
        self.add_component(TaskDefinitionComponent())
        return self

    def with_statistics(self, statistics: str) -> "SystemPromptBuilder":
        """Add production statistics."""
        self.add_component(ProductionStatisticsComponent(statistics))
        return self

    def with_core_instructions(self, instructions: str) -> "SystemPromptBuilder":
        """Add core behavioral instructions."""
        self.add_component(CoreInstructionsComponent(instructions))
        return self

    def with_multiagent(self, agent_idx: int, num_agents: int) -> "SystemPromptBuilder":
        """Enable multi-agent coordination."""
        self.context.agent_idx = agent_idx
        self.context.num_agents = num_agents
        self.context.multiagent_enabled = True
        self.add_component(MultiAgentComponent())
        return self

    def with_response_format(self, format_type: str = "gym") -> "SystemPromptBuilder":
        """Specify response format (gym, mcts, etc.)."""
        self.add_component(ResponseFormatComponent(format_type))
        return self

    def with_patterns(self, patterns: Dict[str, str]) -> "SystemPromptBuilder":
        """Add implementation patterns."""
        self.add_component(ImplementationPatternsComponent(patterns))
        return self

    def with_constraints(self, constraints: List[str]) -> "SystemPromptBuilder":
        """Add behavioral constraints."""
        self.add_component(ConstraintsComponent(constraints))
        return self

    def with_api_reference(
        self, api_docs: str, include_full: bool = False
    ) -> "SystemPromptBuilder":
        """Add API documentation."""
        self.add_component(APIReferenceComponent(api_docs, include_full))
        return self

    def with_preset(self, preset: str) -> "SystemPromptBuilder":
        """Use a predefined component set."""
        if preset == "minimal":
            self.enabled_components.update(MINIMAL_COMPONENTS)
        elif preset == "standard":
            self.enabled_components.update(STANDARD_COMPONENTS)
        elif preset == "comprehensive":
            self.enabled_components.update(COMPREHENSIVE_COMPONENTS)
        else:
            raise ValueError(f"Unknown preset: {preset}")
        return self

    def enable_component(self, component_name: str) -> "SystemPromptBuilder":
        """Enable a specific component."""
        self.enabled_components.add(component_name)
        return self

    def disable_component(self, component_name: str) -> "SystemPromptBuilder":
        """Disable a specific component."""
        self.enabled_components.discard(component_name)
        return self

    def add_component(self, component: SystemPromptComponent) -> "SystemPromptBuilder":
        """Add a custom component."""
        self.components[component.name] = component
        self.enabled_components.add(component.name)
        return self

    def set_context(self, **kwargs) -> "SystemPromptBuilder":
        """Set additional context variables."""
        for key, value in kwargs.items():
            setattr(self.context, key, value)
        return self

    def build(self) -> str:
        """Build the final system prompt."""
        # Get enabled components and sort by priority
        enabled = [
            comp
            for name, comp in self.components.items()
            if name in self.enabled_components
        ]
        enabled.sort(key=lambda c: c.priority)

        # Generate content from each component
        sections = []
        for component in enabled:
            content = component.generate(self.context)
            if content.strip():  # Only add non-empty content
                sections.append(content)

        return "\n\n".join(sections)

    @classmethod
    def for_throughput_task(
        cls, task_description: str, statistics: str, quota: int, entity: str
    ) -> "SystemPromptBuilder":
        """Preset builder for throughput tasks."""
        constraints = [
            "Write modular Python code (≤30 lines per policy)",
            "Always move_to(position) before placing entities",
            "Update entity variables with function returns",
            "Use detailed print statements for all actions",
            "Arrange factory in organized grid with 10+ spaces between sections",
            "Insert 20+ fuel into burner entities",
            "Place chests at drill drop_positions for direct collection",
        ]

        return (
            cls()
            .with_preset("standard")
            .with_task(task_description, entity, quota)
            .with_statistics(statistics)
            .with_constraints(constraints)
        )

    @classmethod
    def for_mcts_agent(
        cls, task_description: str, api_docs: str
    ) -> "SystemPromptBuilder":
        """Preset builder for MCTS agents."""
        constraints = [
            "Focus on profitable automation over manual resource gathering",
            "Use assert statements for self-verification",
            "Don't repeat previous steps - continue from where you left off",
            "Fix errors as they occur and set new objectives",
            "Write code as direct Python interpreter commands",
        ]

        return (
            cls()
            .with_task(task_description)
            .with_response_format("mcts")
            .with_constraints(constraints)
            .with_api_reference(api_docs, include_full=False)
        )

    @classmethod
    def minimal_prompt(cls, task_description: str) -> "SystemPromptBuilder":
        """Minimal system prompt for testing or simple tasks."""
        return (
            cls()
            .with_preset("minimal")
            .with_task(task_description)
            .with_constraints(["Write valid Python code", "Use ≤30 lines per policy"])
        )


# Default component instances that can be reused
DEFAULT_COMPONENTS = {
    "task_definition": TaskDefinitionComponent(),
    "multiagent": MultiAgentComponent(),
    "response_format": ResponseFormatComponent("gym"),
    "constraints": ConstraintsComponent([]),
}


def build_gym_agent_prompt(
    task_description: str,
    statistics: str = "",
    constraints: Optional[List[str]] = None,
    agent_idx: Optional[int] = None,
    num_agents: int = 1,
    patterns: Optional[Dict[str, str]] = None,
) -> str:
    """Convenience function for building gym agent prompts."""
    builder = SystemPromptBuilder().with_preset("standard")

    builder.with_task(task_description)

    if statistics:
        builder.with_statistics(statistics)

    if constraints:
        builder.with_constraints(constraints)

    if num_agents > 1 and agent_idx is not None:
        builder.with_multiagent(agent_idx, num_agents)

    if patterns:
        builder.with_patterns(patterns)

    return builder.build()


def build_mcts_prompt(task_description: str, api_docs: str) -> str:
    """Convenience function for building MCTS agent prompts."""
    return SystemPromptBuilder.for_mcts_agent(task_description, api_docs).build()
