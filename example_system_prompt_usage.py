#!/usr/bin/env python3
"""
Demonstration of the new modular system prompt architecture.

This script shows how different agent designs can create customized
system prompts using the flexible component-based approach.
"""

from fle.env.system_prompt import (
    SystemPromptBuilder,
    create_mcts_exploration_prompt,
    create_multiagent_coordinator_prompt,
    get_example_prompt,
    STANDARD_PATTERNS,
)
from fle.eval.tasks import CRAFTING_STATISTICS


def demo_basic_usage():
    """Demonstrate basic system prompt building."""
    print("=== Basic System Prompt Building ===\n")

    # Simple task-focused prompt
    prompt = (
        SystemPromptBuilder()
        .with_task("Build an iron plate factory that produces 50 plates per minute")
        .with_response_format("gym")
        .with_constraints(
            [
                "Maximum 30 lines per policy",
                "Always move before placing entities",
                "Use print statements for debugging",
            ]
        )
        .build()
    )

    print("Simple Task Prompt:")
    print(prompt[:300] + "...\n")


def demo_throughput_task():
    """Demonstrate throughput task builder."""
    print("=== Throughput Task Prompt ===\n")

    prompt = SystemPromptBuilder.for_throughput_task(
        task_description="Create an automatic automation-science-pack factory that produces 16 automation-science-packs per 60 seconds",
        statistics=CRAFTING_STATISTICS,
        quota=16,
        entity="automation-science-pack",
    ).build()

    print("Throughput Task Prompt:")
    print(prompt[:400] + "...\n")


def demo_mcts_agent():
    """Demonstrate MCTS agent prompt."""
    print("=== MCTS Agent Prompt ===\n")

    api_docs = (
        "get_entities(), place_entity(), connect_entities(), inspect_inventory()..."
    )

    prompt = create_mcts_exploration_prompt(
        "Maximize iron plate production through automation", api_docs
    )

    print("MCTS Agent Prompt:")
    print(prompt[:400] + "...\n")


def demo_multiagent_coordination():
    """Demonstrate multi-agent coordination prompt."""
    print("=== Multi-Agent Coordination Prompt ===\n")

    prompt = create_multiagent_coordinator_prompt(
        task_description="Build a mega-factory producing multiple science packs",
        agent_idx=0,
        num_agents=3,
        role_description="You are the Mining Specialist. Focus on resource extraction and raw material processing.",
        statistics=CRAFTING_STATISTICS,
    )

    print("Multi-Agent Coordinator Prompt:")
    print(prompt[:400] + "...\n")


def demo_custom_configuration():
    """Demonstrate custom configuration approach."""
    print("=== Custom Configuration ===\n")

    # Custom prompt with specific patterns
    custom_patterns = {
        "Smart Mining": """
resource_pos = nearest(Resource.IronOre)
patch_info = get_resource_patch(Resource.IronOre, resource_pos)
print(f"Found iron patch with {patch_info.size} ore at {resource_pos}")
move_to(resource_pos)
drill = place_entity(Prototype.ElectricMiningDrill, position=resource_pos)
""",
        "Efficient Power": """
# Solar power for day/night cycle
solar = place_entity(Prototype.SolarPanel, position=power_pos)
accumulator = place_entity_next_to(Prototype.Accumulator, solar.position, Direction.DOWN)
connect_entities(solar, accumulator, Prototype.SmallElectricPole)
""",
    }

    prompt = (
        SystemPromptBuilder()
        .with_task("Build an efficient, expandable factory")
        .with_core_instructions(
            "Focus on modularity and efficiency. Plan for expansion."
        )
        .with_patterns(custom_patterns)
        .with_response_format("gym")
        .with_constraints(
            [
                "Design for scalability",
                "Use efficient power solutions",
                "Minimize resource waste",
            ]
        )
        .build()
    )

    print("Custom Configuration Prompt:")
    print(prompt[:400] + "...\n")


def demo_preset_examples():
    """Demonstrate preset example configurations."""
    print("=== Preset Examples ===\n")

    # Concise prompt for efficiency
    concise = get_example_prompt(
        "concise_throughput", task={"quota": 32}, statistics=CRAFTING_STATISTICS
    )
    print("Concise Throughput Example:")
    print(concise[:300] + "...\n")

    # Learning prompt with full guidance
    learning = get_example_prompt(
        "comprehensive_learning",
        task={"description": "Learn advanced factory design"},
        api_docs="[API documentation here]",
    )
    print("Comprehensive Learning Example:")
    print(learning[:300] + "...\n")


def demo_old_vs_new_approach():
    """Compare old monolithic vs new modular approach."""
    print("=== Old vs New Approach Comparison ===\n")

    # Simulate old approach - everything hardcoded together
    print("OLD APPROACH: Monolithic, 3370+ lines, task-coupled")
    print("- Task description hardcoded with statistics")
    print("- Agent instructions mixed with API docs")
    print("- No customization without code changes")
    print("- Difficult to maintain and extend\n")

    # Show new modular approach
    print("NEW APPROACH: Modular, customizable, maintainable")

    # Same task, different agent types with different needs
    task_desc = "Build automation science pack factory"

    # Minimal for testing
    minimal = SystemPromptBuilder().with_preset("minimal").with_task(task_desc).build()

    # Standard for production
    standard = (
        SystemPromptBuilder()
        .with_preset("standard")
        .with_task(task_desc)
        .with_statistics("Key production rates here...")
        .build()
    )

    # Comprehensive for learning
    comprehensive = (
        SystemPromptBuilder()
        .with_preset("comprehensive")
        .with_task(task_desc)
        .with_statistics("Detailed statistics...")
        .with_patterns(STANDARD_PATTERNS)
        .build()
    )

    print(f"- Minimal prompt: {len(minimal)} chars")
    print(f"- Standard prompt: {len(standard)} chars")
    print(f"- Comprehensive prompt: {len(comprehensive)} chars")
    print("- Easy to customize per agent type")
    print("- Components can be reused and extended")
    print("- Task logic separated from prompt generation\n")


if __name__ == "__main__":
    print("🤖 Factorio Learning Environment - Modular System Prompt Demo\n")
    print("This demonstrates how different agent designs can create")
    print("customized system prompts using flexible components.\n")

    demo_basic_usage()
    demo_throughput_task()
    demo_mcts_agent()
    demo_multiagent_coordination()
    demo_custom_configuration()
    demo_preset_examples()
    demo_old_vs_new_approach()

    print("✅ Demo complete! The modular system prompt architecture provides:")
    print("   • Flexible component composition")
    print("   • Agent-specific customization")
    print("   • Separation of concerns")
    print("   • Easy maintenance and extension")
    print("   • Dramatic reduction in prompt size when needed")
    print("   • Preservation of backward compatibility")
