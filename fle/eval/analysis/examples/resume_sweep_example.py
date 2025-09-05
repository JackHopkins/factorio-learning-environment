"""
Example demonstrating how to resume a failed sweep.

This example shows how to restart a sweep without duplicating completed runs.
"""

from fle.eval.analysis.sweep_manager import SweepManager, SweepConfig
from fle.commons.constants import GPT_5, CLAUDE_3_7_SONNET


async def resume_sweep_example():
    """Example of resuming a failed sweep"""

    # Create the same config as the original sweep
    config = SweepConfig(
        name="my_experiment",
        models=[GPT_5, CLAUDE_3_7_SONNET],
        tasks=["craft_iron_plate", "build_furnace", "mine_coal"],
        num_trials_per_config=8,
        max_concurrent_processes=4,
        api_key_config_file="path/to/api_keys.json",
    )

    # Resume sweep with existing sweep ID
    # You can get the sweep ID from the original run logs or WandB
    existing_sweep_id = "my_experiment_20241201_120000_abcd1234"

    # Method 1: Using the constructor
    sweep_manager = SweepManager(config, existing_sweep_id=existing_sweep_id)

    # Method 2: Using the class method (equivalent)
    # sweep_manager = SweepManager.resume_sweep(config, existing_sweep_id)

    print("Starting sweep resume...")
    results = await sweep_manager.run_sweep()

    print(f"Sweep completed! Results: {results}")


async def new_sweep_example():
    """Example of starting a new sweep (for comparison)"""

    config = SweepConfig(
        name="my_new_experiment",
        models=[GPT_5, CLAUDE_3_7_SONNET],
        tasks=["craft_iron_plate", "build_furnace"],
        num_trials_per_config=4,
    )

    # Create new sweep (no existing_sweep_id)
    sweep_manager = SweepManager(config)

    await sweep_manager.run_sweep()
    print(f"New sweep completed! Sweep ID: {sweep_manager.sweep_id}")


if __name__ == "__main__":
    # To resume a sweep:
    # asyncio.run(resume_sweep_example())

    # To start a new sweep:
    # asyncio.run(new_sweep_example())

    print("Example script - uncomment the appropriate line above to run")
