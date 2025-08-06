"""
Task definitions and evaluation framework for the Factorio Learning Environment.

This module contains the task system used for evaluating agent performance in Factorio.
Tasks define objectives, success conditions, and provide standardized evaluation metrics.

The task system supports various types of challenges including:
- Throughput-based tasks (achieve specific production rates)
- Unbounded optimization tasks (maximize production)
- Custom task definitions loaded from JSON files

Example usage:
    from fle.eval.tasks import TaskFactory, ThroughputTask

    # Create task from JSON definition
    task = TaskFactory.create_task("iron_plate_throughput_16.json")

    # Or create task directly
    task = ThroughputTask(
        trajectory_length=100,
        goal_description="Build an iron plate factory",
        task_key="iron_plate_task",
        throughput_entity="iron-plate",
        quota=50,
        holdout_wait_period=60
    )
"""

# Core task classes
from .default_task import DefaultTask
from .task_abc import TaskABC
from .task_factory import TaskFactory
from .throughput_task import ThroughputTask
from .unbounded_throughput_task import UnboundedThroughputTask

# Shared constants for throughput tasks
LAB_PLAY_POPULATED_STARTING_INVENTORY = {
    "coal": 500,
    "burner-mining-drill": 50,
    "wooden-chest": 10,
    "burner-inserter": 50,
    "inserter": 50,
    "transport-belt": 500,
    "stone-furnace": 10,
    "boiler": 2,
    "offshore-pump": 2,
    "steam-engine": 2,
    "electric-mining-drill": 50,
    "small-electric-pole": 500,
    "pipe": 500,
    "assembling-machine-2": 10,
    "electric-furnace": 10,
    "pipe-to-ground": 100,
    "underground-belt": 100,
    "pumpjack": 10,
    "oil-refinery": 5,
    "chemical-plant": 5,
    "storage-tank": 10,
}

CRAFTING_STATISTICS = """
Crafting speeds for solids
Iron gear wheel - 120 per 60 seconds
Copper Cable - 240 per 60 seconds
Pipe - 120 per 60 seconds
Steel plate - 3.75 per 60 seconds
Engine unit - 6 per 60 seconds
Electronic circuit - 120 per 60 seconds
Electric Engine unit - 6 per 60 seconds
Flying robot frame - 3 per 60 seconds
Sulfur - 120 per 60 seconds. Can only be produced by a chemical plant
Plastic bar - 120 per 60 seconds. Can only be produced by a chemical plant
Advanced circuit - 10 per 60 seconds
Processing unit - 6 per 60 seconds
Low density structure - 4 per 60 seconds
Copper plate - 18.75 per 60 seconds
Iron plate - 18.75 per 60 seconds
Stone brick - 18.75 per 60 seconds
Automation science packs - 12 per 60 seconds
Battery - 20 per 60 seconds. Can only be produced by a chemical plant

Crafting speeds for liquids
Sulfuric acid - 3000 per 60 seconds, can only be gotten with a chemical plant
Lubricant - 600 per 60 seconds. Can only be produced by a chemical plant
Heavy oil - 300 per 60 seconds with advanced oil processing, 1080 per 60 seconds with Coal liquefaction
Light oil - 540 per 60 seconds with advanced oil processing, 240 per 60 seconds with Coal liquefaction, 900 per 60 seconds with Heavy oil cracking
Petroleum gas - 540 per 60 seconds with Basic oil processing, 660 per 60 seconds with advanced oil processing, 120 per 60 seconds with Coal liquefaction

Raw resource extraction speeds
Burner mining drill - Mines 15 resources per 60 seconds
Electric mining drill - Mines 30 resources per 60 seconds
Burner mining drill - Mines 15 resources per 60 seconds
Pumpjack - Extracts 600 crude oil per 60 seconds

Furnace smelting speed modifiers
Stone furnace - 1 (Example: smelts 18.75 copper plates per 60 seconds)
Electronic furnace - 2 (Example: smelts 37.5 copper plates per 60 seconds)
Steel furnace - 2 (Example: smelts 37.5 copper plates per 60 seconds)

Assembling machine crafting speed modifiers
Assembling machine 1 - 0.5 (Example: Crafts 60 iron gear wheels per 60 seconds)
Assembling machine 2 - 0.75 (Example: Crafts 90 iron gear wheels per 60 seconds)
Assembling machine 3 - 1.25 (Example: Crafts 150 iron gear wheels per 60 seconds)

Oil refinery & Chemical plant crafting speed modifiers
Oil refinery - 1 (Example: Creates 540 petroleum gas per 60 seconds with Basic oil processing)
Chemical plant - 1 (Example: Creates 600 Lubricant per 60 seconds)
"""

BOUNDED_INSTRUCTIONS = """
You must create an AUTOMATIC factory that automatically creates a target entity by itself. You are given the entity for which you need to create a factory for. You are also given the target throughput that the factory must achieve
After each step the throughput of the factory is evaluated during 60 seconds of worktime and the results are supplied to you in the response.
"""

UNBOUNDED_INSTRUCTIONS = """
You must create an AUTOMATIC factory that automatically creates a target entity by itself. You are given the entity for which you need to create a factory for. Create the largest factory as you can that automatically creates the target entity
    
After each step the throughput of the factory is evaluated during 60 seconds of worktime and the results are supplied to you in the response. Iteratively expand your factory, i.e first make a small factory step by step and then expand the factory in subsequent steps .
"""


__all__ = [
    # Abstract base and core classes
    "TaskABC",
    "DefaultTask",
    # Throughput-based tasks
    "ThroughputTask",
    "UnboundedThroughputTask",
    # Task creation utilities
    "TaskFactory",
    # Useful constants
    "LAB_PLAY_POPULATED_STARTING_INVENTORY",
    "CRAFTING_STATISTICS",
    "BOUNDED_INSTRUCTIONS",
    "UNBOUNDED_INSTRUCTIONS",
]
