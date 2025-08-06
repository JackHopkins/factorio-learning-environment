"""
Modular system prompt generation for Factorio Learning Environment.

This package provides a flexible, component-based approach to generating
system prompts for different types of agents, allowing customization of
instructions, constraints, and information density.

Example usage:
    from fle.env.system_prompt import SystemPromptBuilder

    # For throughput tasks
    prompt = (SystemPromptBuilder()
              .for_throughput_task("Build iron plate factory", stats, 50, "iron-plate")
              .build())

    # For MCTS agents
    prompt = SystemPromptBuilder.for_mcts_agent(task_desc, api_docs).build()

    # Custom composition
    prompt = (SystemPromptBuilder()
              .with_task("Custom task")
              .with_constraints(["Rule 1", "Rule 2"])
              .with_response_format("gym")
              .build())
"""

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

from .builder import (
    SystemPromptBuilder,
    build_gym_agent_prompt,
    build_mcts_prompt,
    DEFAULT_COMPONENTS,
)

from .examples import (
    create_concise_throughput_prompt,
    create_verbose_learning_prompt,
    create_mcts_exploration_prompt,
    create_multiagent_coordinator_prompt,
    create_minimal_testing_prompt,
    create_custom_agent_prompt,
    get_example_prompt,
    EXAMPLE_CONFIGS,
    STANDARD_PATTERNS,
)

__all__ = [
    # Core classes
    "SystemPromptComponent",
    "SystemPromptContext",
    "SystemPromptBuilder",
    # Component types
    "TaskDefinitionComponent",
    "ProductionStatisticsComponent",
    "CoreInstructionsComponent",
    "MultiAgentComponent",
    "ResponseFormatComponent",
    "ImplementationPatternsComponent",
    "ConstraintsComponent",
    "APIReferenceComponent",
    # Presets and utilities
    "MINIMAL_COMPONENTS",
    "STANDARD_COMPONENTS",
    "COMPREHENSIVE_COMPONENTS",
    "DEFAULT_COMPONENTS",
    "build_gym_agent_prompt",
    "build_mcts_prompt",
    # Example configurations
    "create_concise_throughput_prompt",
    "create_verbose_learning_prompt",
    "create_mcts_exploration_prompt",
    "create_multiagent_coordinator_prompt",
    "create_minimal_testing_prompt",
    "create_custom_agent_prompt",
    "get_example_prompt",
    "EXAMPLE_CONFIGS",
    "STANDARD_PATTERNS",
]
