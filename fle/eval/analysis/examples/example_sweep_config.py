"""
Example sweep configuration for large-scale evaluations.

This script demonstrates how to set up and run a comprehensive sweep
across multiple models and tasks using the analysis framework.
"""

import asyncio
from fle.eval.analysis import SweepManager, SweepConfig
from fle.commons.constants import (
    # Direct API models
    GPT_5,
    GPT_5_MINI,
    O4_MINI,
    CLAUDE_OPUS_4_1,
    CLAUDE_SONNET_4,
    CLAUDE_3_7_SONNET,
    GEMINI_2_5_PRO,
    OR_GPT_5,
    OR_O4_MINI,
    OR_CLAUDE_OPUS_4_1,
    OR_CLAUDE_SONNET_4,
    OR_CLAUDE_3_7_SONNET,
    OR_GEMINI_2_5_PRO,
    OR_GEMINI_2_5_FLASH,
    OR_XAI_GROK_4,
    OR_XAI_GROK_3,
    OR_DEEPSEEK_V3_1,
    OR_DEEPSEEK_R1,
    OR_LLAMA_4_MAVERICK,
    OR_LLAMA_4_SCOUT,
)


async def run_pass_at_k_optimized_sweep():
    """Example: Pass@K optimized sweep with task inner loop and early stopping"""

    config = SweepConfig(
        name="pass_at_k_optimized_sweep",
        description="Pass@K optimized sweep with task cycling and early stopping",
        # Models to evaluate
        models=[
            CLAUDE_SONNET_4,
            CLAUDE_OPUS_4_1,
            CLAUDE_3_7_SONNET,
        ],
        # Tasks to evaluate
        tasks=[
            "iron_ore_throughput",
            "iron_plate_throughput",
            "steel_plate_throughput",
            "automation_science_pack_throughput",
        ],
        # Pass@5 evaluation
        num_trials_per_config=5,
        # Resource management
        max_concurrent_processes=3,
        # Pass@K optimization features
        task_inner_loop_mode=True,  # Cycle through tasks before repeating model-task pairs
        early_stop_on_success=True,  # Skip (model, task) pairs that already succeeded
        # WandB configuration
        enable_wandb=True,
        wandb_project="factorio-pass-at-k-eval",
        # Results management
        output_dir="./sweep_results/pass_at_k_optimized",
        save_intermediate_results=True,
        # Monitoring
        log_interval_minutes=3,  # More frequent logging to see early stopping in action
        # Execution configuration
        shuffle_execution_order=False,  # Disabled when using task inner loop
        retry_failed_runs=True,
        max_retries=2,
        # API configuration
        api_key_config_file="api_keys.json",
    )

    # Create and run sweep
    manager = SweepManager(
        config, existing_sweep_id="pass_at_k_optimized_sweep_20250906_192447_3f8b8a5b"
    )
    results = await manager.run_sweep()

    print("Pass@K optimized sweep completed!")
    print("Key benefits:")
    print("  - Task inner loop: See all task performance quickly on WandB")
    print("  - Early stopping: Save compute budget by skipping successful pairs")
    print(f"Results saved to: {config.output_dir}")

    return results


async def run_small_sweep():
    """Example: Small sweep for testing"""

    config = SweepConfig(
        name="test_sweep_small_harder_1",
        description="Small test sweep with 2 Claude models and 2 tasks",
        # Models to evaluate (using direct Anthropic API)
        models=[
            CLAUDE_SONNET_4,
            CLAUDE_OPUS_4_1,
        ],
        # Tasks to evaluate (these should be valid gym environment IDs)
        # tasks=["iron_ore_throughput", "iron_plate_throughput"],
        tasks=["steel_plate_throughput", "automation_science_pack_throughput"],
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
        # Use API key configuration file
        api_key_config_file="api_keys.json",
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
        # Large set of models using updated constants
        models=[
            GPT_5,
            GPT_5_MINI,
            CLAUDE_SONNET_4,
            CLAUDE_3_7_SONNET,
            GEMINI_2_5_PRO,
            O4_MINI,
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


async def run_openrouter_grok_sweep():
    """Example: Test Grok and other models via OpenRouter"""

    config = SweepConfig(
        name="openrouter_grok_evaluation",
        description="Evaluate Grok and other OpenRouter models on Factorio tasks",
        # OpenRouter models (requires OPEN_ROUTER_API_KEY environment variable)
        models=[
            OR_XAI_GROK_4,  # Grok 4 via OpenRouter
            OR_CLAUDE_3_7_SONNET,  # Claude via OpenRouter
            OR_GPT_5,  # GPT-5 via OpenRouter
            # Compare with direct API models
            CLAUDE_SONNET_4,  # Direct Anthropic API
            GPT_5,  # Direct OpenAI API
        ],
        tasks=[
            "iron_ore_throughput",
            "iron_plate_throughput",
        ],
        num_trials_per_config=3,  # Start with fewer trials for testing
        max_concurrent_processes=3,  # Adjust based on your server count
        # Enable tracking
        enable_wandb=True,
        wandb_project="openrouter-grok-evaluation",
        # Configuration
        output_dir="sweep_results/openrouter_grok_evaluation",
        log_interval_minutes=5,
        retry_failed_runs=True,
        max_retries=2,
    )

    # Create and run sweep
    manager = SweepManager(config)
    results = await manager.run_sweep()

    print("OpenRouter Grok sweep completed!")
    print(f"Models tested: {', '.join(config.models)}")
    print(f"Results saved to: {config.output_dir}")

    return results


async def run_openrouter_model_tournament():
    """Example: Large tournament of models via OpenRouter"""

    config = SweepConfig(
        name="openrouter_model_tournament",
        description="Tournament of top models across multiple providers via OpenRouter",
        # Comprehensive model comparison via OpenRouter
        models=[
            # xAI
            OR_XAI_GROK_4,
            OR_XAI_GROK_3,
            # Anthropic
            OR_CLAUDE_3_7_SONNET,
            OR_CLAUDE_SONNET_4,
            OR_CLAUDE_OPUS_4_1,
            # OpenAI
            OR_GPT_5,
            OR_O4_MINI,
            # Meta Llama
            OR_LLAMA_4_MAVERICK,
            OR_LLAMA_4_SCOUT,
            # Google
            OR_GEMINI_2_5_PRO,
            OR_GEMINI_2_5_FLASH,
            # DeepSeek
            OR_DEEPSEEK_V3_1,
            OR_DEEPSEEK_R1,
        ],
        tasks=[
            "iron_ore_throughput",
            "iron_plate_throughput",
            "gear_production",
        ],
        num_trials_per_config=5,  # Reasonable for many models
        max_concurrent_processes=4,
        # Tracking and storage
        enable_wandb=True,
        wandb_project="openrouter-model-tournament",
        output_dir="sweep_results/openrouter_model_tournament",
        log_interval_minutes=15,  # Less frequent logging for long runs
        retry_failed_runs=True,
        max_retries=3,
        # Use API key manager for multiple keys if available
        api_key_config_file="api_keys_config.json",
    )

    # Create and run sweep
    manager = SweepManager(config)
    results = await manager.run_sweep()

    print("OpenRouter model tournament completed!")
    print(f"Models tested: {len(config.models)}")
    print(
        f"Total evaluations: {len(config.models) * len(config.tasks) * config.num_trials_per_config}"
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

    if len(sys.argv) > 1:
        sweep_type = sys.argv[1]

        if sweep_type == "pass_at_k":
            print("Running Pass@K optimized sweep...")
            print("Features: Task inner loop mode + Early stopping on success")
            asyncio.run(run_pass_at_k_optimized_sweep())
        elif sweep_type == "large":
            print("Running large production sweep...")
            asyncio.run(run_large_production_sweep())
        elif sweep_type == "grok":
            print("Running OpenRouter Grok evaluation...")
            print("Make sure you have set OPEN_ROUTER_API_KEY environment variable!")
            asyncio.run(run_openrouter_grok_sweep())
        elif sweep_type == "tournament":
            print("Running OpenRouter model tournament...")
            print("Make sure you have set OPEN_ROUTER_API_KEY environment variable!")
            asyncio.run(run_openrouter_model_tournament())
        else:
            print(f"Unknown sweep type: {sweep_type}")
            print(
                "Available options: small (default), pass_at_k, large, grok, tournament"
            )
            sys.exit(1)
    else:
        print("Running small test sweep...")
        asyncio.run(run_small_sweep())

    print("\n🎉 Sweep completed! Check WandB and the output directory for results.")
