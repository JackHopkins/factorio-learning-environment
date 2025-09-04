"""
Example sweep configuration for large-scale evaluations.

This script demonstrates how to set up and run a comprehensive sweep
across multiple models and tasks using the analysis framework.
"""

import asyncio
from fle.eval.analysis import SweepManager, SweepConfig


async def run_small_sweep():
    """Example: Small sweep for testing"""

    config = SweepConfig(
        name="test_sweep_small",
        description="Small test sweep with 2 Claude models and 2 tasks",
        # Models to evaluate
        models=["claude-sonnet-4-20250514", "claude-opus-4-20250514"],
        # Tasks to evaluate (these should be valid gym environment IDs)
        tasks=["iron_ore_throughput", "iron_plate_throughput"],
        # Pass@8 evaluation (3 trials per model-task combination)
        num_trials_per_config=3,
        # Resource management
        max_concurrent_processes=2,  # Conservative for testing
        # Enable WandB logging
        enable_wandb=True,
        wandb_project="factorio-eval-test",
        # Save results
        output_dir="./sweep_results/small_test",
        save_intermediate_results=True,
        # Logging configuration
        log_interval_minutes=5,  # Log progress every 15 minutes
        # Retry configuration
        retry_failed_runs=True,
        max_retries=2,
    )

    # Create and run sweep
    manager = SweepManager(config)
    results = await manager.run_sweep()

    print("Sweep completed!")
    print(f"Results saved to: {config.output_dir}")

    return results


async def run_large_production_sweep():
    """Example: Large production sweep with many models and tasks"""

    config = SweepConfig(
        name="production_sweep_v1",
        description="Comprehensive evaluation of multiple models across all throughput tasks",
        # Large set of models
        models=[
            "gpt-4o",
            "gpt-4o-mini",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "gemini-1.5-pro",
            "o1-mini",
        ],
        # All available throughput tasks
        tasks=[
            "Factorio-iron_ore_throughput_16-v0",
            "Factorio-copper_ore_throughput_16-v0",
            "Factorio-iron_plate_throughput_16-v0",
            "Factorio-copper_plate_throughput_16-v0",
            "Factorio-stone_throughput_16-v0",
            "Factorio-coal_throughput_16-v0",
            "Factorio-iron_gear_wheel_throughput_16-v0",
            "Factorio-electronic_circuit_throughput_16-v0",
            # Add more tasks as available
        ],
        # Pass@8 evaluation
        num_trials_per_config=8,
        # Resource management for production
        max_concurrent_processes=8,  # Utilize more resources
        # WandB configuration
        enable_wandb=True,
        wandb_project="factorio-production-eval",
        # Results management
        output_dir="./sweep_results/production_v1",
        save_intermediate_results=True,
        # Monitoring configuration
        log_interval_minutes=30,
        # Execution configuration
        shuffle_execution_order=True,  # Better load distribution
        retry_failed_runs=True,
        max_retries=3,
    )

    # Create and run sweep
    manager = SweepManager(config)
    results = await manager.run_sweep()

    print("Production sweep completed!")
    print(
        f"Total runs: {len(config.models) * len(config.tasks) * config.num_trials_per_config}"
    )
    print(f"Results saved to: {config.output_dir}")

    return results


def create_custom_sweep_config(
    models: list, tasks: list, trials: int = 8, name: str = "custom_sweep"
) -> SweepConfig:
    """Helper function to create custom sweep configurations

    Args:
        models: List of model names to evaluate
        tasks: List of task environment IDs to evaluate
        trials: Number of trials per model-task combination
        name: Name for the sweep

    Returns:
        SweepConfig configured for the custom sweep
    """

    return SweepConfig(
        name=name,
        description=f"Custom sweep: {len(models)} models × {len(tasks)} tasks × {trials} trials",
        models=models,
        tasks=tasks,
        num_trials_per_config=trials,
        # Conservative resource usage
        max_concurrent_processes=4,
        # Enable monitoring
        enable_wandb=True,
        wandb_project=f"factorio-{name}",
        # Results configuration
        output_dir=f"./sweep_results/{name}",
        save_intermediate_results=True,
        log_interval_minutes=20,
        # Execution parameters
        shuffle_execution_order=True,
        retry_failed_runs=True,
        max_retries=2,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "large":
        print("Running large production sweep...")
        asyncio.run(run_large_production_sweep())
    else:
        print("Running small test sweep...")
        asyncio.run(run_small_sweep())
