"""
Example system prompt configurations for different agent types.

This module demonstrates how to use the modular system prompt system
to create tailored prompts for various agent architectures and use cases.
"""

from typing import Dict, Any
from .builder import SystemPromptBuilder


# Standard patterns that can be reused across configurations
STANDARD_PATTERNS = {
    "Mining Setup": """
move_to(ore_position)
drill = place_entity(Prototype.BurnerMiningDrill, position=ore_position, direction=Direction.DOWN)
drill = insert_item(Prototype.Coal, drill, 20)
chest = place_entity(Prototype.WoodenChest, position=drill.drop_position)""",
    "Power Generation": """
pump = place_entity(Prototype.OffshorePump, position=water_pos)
boiler = place_entity(Prototype.Boiler, position=safe_pos)
boiler = insert_item(Prototype.Coal, boiler, 20)
engine = place_entity(Prototype.SteamEngine, position=safe_pos)
connect_entities(pump, boiler, Prototype.Pipe)
connect_entities(boiler, engine, Prototype.Pipe)""",
    "Assembly Line": """
assembler = place_entity(Prototype.AssemblingMachine1, position=pos)
set_entity_recipe(assembler, Prototype.TargetItem)
input_inserter = place_entity_next_to(Prototype.BurnerInserter, assembler.position, Direction.RIGHT)
input_inserter = rotate_entity(input_inserter, Direction.LEFT)
output_inserter = place_entity_next_to(Prototype.BurnerInserter, assembler.position, Direction.LEFT)
connect_entities(power_source, assembler, Prototype.SmallElectricPole)""",
}

GYM_CONSTRAINTS = [
    "Write modular Python code (≤30 lines per policy)",
    "Always move_to(position) before placing entities",
    "Update entity variables with function returns",
    "Use detailed print statements for all actions",
    "Arrange factory in organized grid with 10+ spaces between sections",
    "Insert 20+ fuel into burner entities",
    "Place chests at drill drop_positions for direct collection",
]

MCTS_CONSTRAINTS = [
    "Focus on profitable automation over manual resource gathering",
    "Use assert statements for self-verification with specific messages",
    "Don't repeat previous steps - continue from where you left off",
    "Fix errors as they occur and set new objectives when finished",
    "Write code as direct Python interpreter commands",
    "Consider long-term factory expansion in each decision",
]

MINIMAL_CONSTRAINTS = [
    "Write valid Python code",
    "Use ≤30 lines per policy",
    "Focus on the immediate objective",
]


def create_concise_throughput_prompt(
    task_description: str, target_entity: str, quota: int, statistics: str
) -> str:
    """Create a concise system prompt for throughput tasks focused on efficiency."""
    return (
        SystemPromptBuilder()
        .with_task(task_description, target_entity, quota)
        .with_statistics(statistics)
        .with_response_format("gym")
        .with_constraints(
            [
                "Maximum 30 lines per policy",
                "Always move_to() before placing entities",
                "Use print() for all major actions",
                "Build incrementally and verify each step",
            ]
        )
        .build()
    )


def create_verbose_learning_prompt(
    task_description: str, statistics: str, api_docs: str
) -> str:
    """Create a comprehensive prompt for learning agents that need detailed guidance."""
    return (
        SystemPromptBuilder()
        .with_task(task_description)
        .with_statistics(statistics)
        .with_core_instructions("""
### Learning Guidelines
- Experiment with different approaches when stuck
- Use inspect_inventory() frequently to understand state
- Build small test structures before scaling up
- Learn from errors and adjust strategy accordingly
- Document your reasoning in comments
            """)
        .with_response_format("gym")
        .with_patterns(STANDARD_PATTERNS)
        .with_constraints(GYM_CONSTRAINTS)
        .with_api_reference(api_docs, include_full=True)
        .build()
    )


def create_mcts_exploration_prompt(task_description: str, api_docs: str) -> str:
    """Create a prompt optimized for MCTS exploration and planning."""
    return (
        SystemPromptBuilder()
        .with_task(task_description)
        .with_response_format("mcts")
        .with_core_instructions("""
### MCTS Planning Approach
- Think in terms of value maximization and exploration vs exploitation
- Consider multiple potential next steps before committing
- Use modular actions that can be easily composed
- Build towards long-term automation objectives
- Prioritize actions with highest expected utility
            """)
        .with_constraints(MCTS_CONSTRAINTS)
        .with_api_reference(api_docs, include_full=False)
        .build()
    )


def create_multiagent_coordinator_prompt(
    task_description: str,
    agent_idx: int,
    num_agents: int,
    role_description: str,
    statistics: str,
) -> str:
    """Create a prompt for multi-agent coordination with specific roles."""
    return (
        SystemPromptBuilder()
        .with_task(f"{task_description}\n\n### Your Role\n{role_description}")
        .with_statistics(statistics)
        .with_multiagent(agent_idx, num_agents)
        .with_response_format("gym")
        .with_core_instructions("""
### Coordination Strategy
- Communicate plans before major construction
- Avoid overlapping work areas with other agents
- Share resource discoveries and production outputs
- Coordinate specialized roles (mining, smelting, assembly, power)
- Signal completion of major milestones
            """)
        .with_constraints(
            GYM_CONSTRAINTS
            + [
                "Send message at start and end of each policy",
                "Request resources from other agents when needed",
                "Announce when claiming a work area",
            ]
        )
        .build()
    )


def create_minimal_testing_prompt(task_description: str) -> str:
    """Create a minimal prompt for testing or debugging purposes."""
    return (
        SystemPromptBuilder()
        .with_task(task_description)
        .with_response_format("gym")
        .with_constraints(MINIMAL_CONSTRAINTS)
        .build()
    )


def create_custom_agent_prompt(config: Dict[str, Any]) -> str:
    """Create a custom prompt from a configuration dictionary."""
    builder = SystemPromptBuilder()

    # Core configuration
    if "task" in config:
        builder.with_task(
            config["task"].get("description", ""),
            config["task"].get("entity"),
            config["task"].get("quota"),
        )

    if "preset" in config:
        builder.with_preset(config["preset"])

    # Optional components
    if "statistics" in config:
        builder.with_statistics(config["statistics"])

    if "instructions" in config:
        builder.with_core_instructions(config["instructions"])

    if "response_format" in config:
        builder.with_response_format(config["response_format"])

    if "patterns" in config:
        builder.with_patterns(config["patterns"])

    if "constraints" in config:
        builder.with_constraints(config["constraints"])

    if "multiagent" in config:
        ma = config["multiagent"]
        builder.with_multiagent(ma["agent_idx"], ma["num_agents"])

    if "api_docs" in config:
        builder.with_api_reference(
            config["api_docs"], config.get("include_full_api", False)
        )

    return builder.build()


# Example configurations
EXAMPLE_CONFIGS = {
    "concise_throughput": {
        "preset": "minimal",
        "task": {
            "description": "Build efficient automation-science-pack factory",
            "entity": "automation-science-pack",
            "quota": 16,
        },
        "response_format": "gym",
        "constraints": [
            "≤30 lines per policy",
            "Move before placing",
            "Print all actions",
        ],
    },
    "comprehensive_learning": {
        "preset": "comprehensive",
        "task": {"description": "Learn to build complex factories"},
        "response_format": "gym",
        "patterns": STANDARD_PATTERNS,
        "instructions": "Experiment and learn from mistakes",
        "include_full_api": True,
    },
    "mcts_planner": {
        "preset": "minimal",
        "task": {"description": "Maximize factory throughput"},
        "response_format": "mcts",
        "constraints": MCTS_CONSTRAINTS,
    },
    "multiagent_specialist": {
        "preset": "standard",
        "task": {"description": "Coordinate with team to build mega-factory"},
        "multiagent": {"agent_idx": 0, "num_agents": 3},
        "response_format": "gym",
    },
}


def get_example_prompt(example_name: str, **kwargs) -> str:
    """Get a pre-configured example prompt with optional parameter overrides."""
    if example_name not in EXAMPLE_CONFIGS:
        available = ", ".join(EXAMPLE_CONFIGS.keys())
        raise ValueError(f"Unknown example '{example_name}'. Available: {available}")

    config = EXAMPLE_CONFIGS[example_name].copy()

    # Override with provided kwargs
    for key, value in kwargs.items():
        if key in config:
            if isinstance(config[key], dict) and isinstance(value, dict):
                config[key].update(value)
            else:
                config[key] = value
        else:
            config[key] = value

    return create_custom_agent_prompt(config)
