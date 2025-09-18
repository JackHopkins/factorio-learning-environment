#!/usr/bin/env python3
"""
Consolidated sweep configuration for large-scale evaluations.

This script consolidates all sweep configurations into a single comprehensive file,
providing multiple sweep profiles for different evaluation scenarios.
"""

import asyncio
import sys
from typing import List, Optional
from fle.eval.infra import SweepManager, SweepConfig
from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import (
    ADVANCED_CIRCUIT_THROUGHPUT,
    AUTOMATION_SCIENCE_PACK_THROUGHPUT,
    BATTERY_THROUGHPUT,
    CHEMICAL_SCIENCE_PACK_THROUGHPUT,
    CRUDE_OIL_THROUGHPUT,
    ELECTRONIC_CIRCUIT_THROUGHPUT,
    ENGINE_UNIT_THROUGHPUT,
    INSERTER_THROUGHPUT,
    IRON_GEAR_WHEEL_THROUGHPUT,
    IRON_ORE_THROUGHPUT,
    IRON_PLATE_THROUGHPUT,
    LOGISTICS_SCIENCE_PACK_THROUGHPUT,
    LOW_DENSITY_STRUCTURE_THROUGHPUT,
    MILITARY_SCIENCE_PACK_THROUGHPUT,
    PETROLEUM_GAS_THROUGHPUT,
    PIERCING_ROUND_THROUGHPUT,
    PLASTIC_BAR_THROUGHPUT,
    PROCESSING_UNIT_THROUGHPUT,
    PRODUCTION_SCIENCE_PACK_THROUGHPUT,
    STEEL_PLATE_THROUGHPUT,
    STONE_WALL_THROUGHPUT,
    SUFURIC_ACID_THROUGHPUT,
    SULFUR_THROUGHPUT,
    UTILITY_SCIENCE_PACK_THROUGHPUT,
)
from fle.commons.constants import (
    # Direct API models
    GPT_5,
    GPT_5_MINI,
    O4_MINI,
    CLAUDE_OPUS_4_1,
    CLAUDE_SONNET_4,
    CLAUDE_3_7_SONNET,
    GEMINI_2_5_PRO,
    OR_GEMINI_2_5_PRO,
    # OpenRouter models
    OR_GPT_5,
    OR_CLAUDE_OPUS_4_1,
    OR_CLAUDE_SONNET_4,
    OR_CLAUDE_3_7_SONNET,
    OR_XAI_GROK_4,
    OR_XAI_GROK_3,
)


class SweepProfiles:
    """Collection of predefined sweep configurations for different scenarios"""

    @staticmethod
    def test_small() -> SweepConfig:
        """Small test sweep for quick validation (2 models, 2 tasks, 3 trials)"""
        return SweepConfig(
            name="test_sweep_small",
            description="Small test sweep for quick validation",
            models=[
                CLAUDE_SONNET_4,
                CLAUDE_OPUS_4_1,
            ],
            tasks=[
                IRON_ORE_THROUGHPUT,
                IRON_PLATE_THROUGHPUT,
            ],
            num_trials_per_config=3,
            max_concurrent_processes=2,
            enable_wandb=True,
            wandb_project="factorio-eval-test",
            output_dir="./sweep_results/test_small",
            save_intermediate_results=True,
            log_interval_minutes=5,
            retry_failed_runs=True,
            max_retries=2,
            api_key_config_file="api_keys.json",
        )

    @staticmethod
    def test_harder_tasks() -> SweepConfig:
        """Test sweep with more challenging tasks"""
        return SweepConfig(
            name="test_sweep_harder",
            description="Test sweep with challenging tasks",
            models=[
                CLAUDE_SONNET_4,
                CLAUDE_OPUS_4_1,
            ],
            tasks=[
                STEEL_PLATE_THROUGHPUT,
                AUTOMATION_SCIENCE_PACK_THROUGHPUT,
            ],
            num_trials_per_config=3,
            max_concurrent_processes=2,
            enable_wandb=True,
            wandb_project="factorio-eval-test",
            output_dir="./sweep_results/test_harder",
            save_intermediate_results=True,
            log_interval_minutes=5,
            retry_failed_runs=True,
            max_retries=2,
            api_key_config_file="api_keys.json",
        )

    @staticmethod
    def pass_at_k_optimized() -> SweepConfig:
        """Pass@K optimized sweep with task cycling and early stopping"""
        return SweepConfig(
            name="pass_at_k_optimized",
            description="Pass@K optimized sweep with task cycling and early stopping",
            models=[
                OR_CLAUDE_SONNET_4,
                OR_CLAUDE_OPUS_4_1,
                OR_CLAUDE_3_7_SONNET,
            ],
            tasks=[
                IRON_ORE_THROUGHPUT,
                IRON_PLATE_THROUGHPUT,
                STEEL_PLATE_THROUGHPUT,
                AUTOMATION_SCIENCE_PACK_THROUGHPUT,
            ],
            num_trials_per_config=5,  # Pass@5 evaluation
            max_concurrent_processes=3,
            # Pass@K optimization features
            task_inner_loop_mode=True,  # Cycle through tasks before repeating model-task pairs
            early_stop_on_success=True,  # Skip (model, task) pairs that already succeeded
            # WandB configuration
            enable_wandb=True,
            wandb_project="factorio-pass-at-k-eval",
            output_dir="./sweep_results/pass_at_k_optimized",
            save_intermediate_results=True,
            log_interval_minutes=3,  # More frequent logging to see early stopping in action
            shuffle_execution_order=False,  # Disabled when using task inner loop
            retry_failed_runs=True,
            max_retries=2,
            api_key_config_file="api_keys.json",
        )

    @staticmethod
    def production_medium() -> SweepConfig:
        """Medium-scale production sweep (6 models, 8 tasks, Pass@8)"""
        return SweepConfig(
            name="production_medium",
            description="Medium-scale production evaluation",
            models=[
                GPT_5,
                GPT_5_MINI,
                CLAUDE_SONNET_4,
                CLAUDE_3_7_SONNET,
                GEMINI_2_5_PRO,
                O4_MINI,
            ],
            tasks=[
                IRON_ORE_THROUGHPUT,
                IRON_PLATE_THROUGHPUT,
                IRON_GEAR_WHEEL_THROUGHPUT,
                ELECTRONIC_CIRCUIT_THROUGHPUT,
            ],
            num_trials_per_config=8,  # Pass@8 evaluation
            max_concurrent_processes=8,
            enable_wandb=True,
            wandb_project="factorio-production-eval",
            output_dir="./sweep_results/production_medium",
            save_intermediate_results=True,
            log_interval_minutes=30,
            shuffle_execution_order=True,  # Better load distribution
            retry_failed_runs=True,
            max_retries=3,
            api_key_config_file="api_keys.json",
        )

    @staticmethod
    def production_large() -> SweepConfig:
        """Large production sweep with comprehensive task coverage"""
        return SweepConfig(
            name="production_large",
            description="Comprehensive evaluation across all throughput tasks",
            models=[
                # Frontier models through openrouter
                OR_GPT_5,
                OR_CLAUDE_OPUS_4_1,
                OR_GEMINI_2_5_PRO,
                OR_XAI_GROK_4,
            ],
            tasks=[
                # All throughput tasks from lab_play folder
                ADVANCED_CIRCUIT_THROUGHPUT,
                AUTOMATION_SCIENCE_PACK_THROUGHPUT,
                BATTERY_THROUGHPUT,
                CHEMICAL_SCIENCE_PACK_THROUGHPUT,
                CRUDE_OIL_THROUGHPUT,
                ELECTRONIC_CIRCUIT_THROUGHPUT,
                ENGINE_UNIT_THROUGHPUT,
                INSERTER_THROUGHPUT,
                IRON_GEAR_WHEEL_THROUGHPUT,
                IRON_ORE_THROUGHPUT,
                IRON_PLATE_THROUGHPUT,
                LOGISTICS_SCIENCE_PACK_THROUGHPUT,
                LOW_DENSITY_STRUCTURE_THROUGHPUT,
                MILITARY_SCIENCE_PACK_THROUGHPUT,
                PETROLEUM_GAS_THROUGHPUT,
                PIERCING_ROUND_THROUGHPUT,
                PLASTIC_BAR_THROUGHPUT,
                PROCESSING_UNIT_THROUGHPUT,
                PRODUCTION_SCIENCE_PACK_THROUGHPUT,
                STEEL_PLATE_THROUGHPUT,
                STONE_WALL_THROUGHPUT,
                SUFURIC_ACID_THROUGHPUT,
                SULFUR_THROUGHPUT,
                UTILITY_SCIENCE_PACK_THROUGHPUT,
            ],
            num_trials_per_config=8,
            max_concurrent_processes=32,
            # Pass@K optimization features
            task_inner_loop_mode=True,  # Cycle through tasks before repeating model-task pairs
            early_stop_on_success=True,  # Skip (model, task) pairs that already succeeded
            enable_wandb=True,
            wandb_project="factorio-production-large",
            output_dir="./sweep_results/production_large",
            save_intermediate_results=True,
            log_interval_minutes=30,
            shuffle_execution_order=False,  # Disabled when using task inner loop
            retry_failed_runs=True,
            max_retries=2,
            api_key_config_file="api_keys.json",
        )

    @staticmethod
    def openrouter_grok_test() -> SweepConfig:
        """Test Grok and other models via OpenRouter"""
        return SweepConfig(
            name="openrouter_grok_test",
            description="Evaluate Grok and other OpenRouter models",
            models=[
                OR_XAI_GROK_4,  # Grok 4 via OpenRouter
                OR_XAI_GROK_3,  # Grok 3 via OpenRouter
                OR_CLAUDE_3_7_SONNET,  # Claude via OpenRouter
                OR_GPT_5,  # GPT-5 via OpenRouter
                # Compare with direct API models
                CLAUDE_SONNET_4,  # Direct Anthropic API
                GPT_5,  # Direct OpenAI API
            ],
            tasks=[
                "iron_ore_throughput",
                "iron_plate_throughput",
                "gear_production",
            ],
            num_trials_per_config=3,
            max_concurrent_processes=3,
            enable_wandb=True,
            wandb_project="openrouter-grok-evaluation",
            output_dir="./sweep_results/openrouter_grok",
            log_interval_minutes=5,
            retry_failed_runs=True,
            max_retries=2,
            api_key_config_file="api_keys.json",
        )

    @staticmethod
    def custom(
        models: List[str],
        tasks: List[str],
        trials: int = 8,
        name: str = "custom_sweep",
        wandb_project: Optional[str] = None,
        max_concurrent: int = 4,
        pass_at_k_optimized: bool = False,
    ) -> SweepConfig:
        """Create a custom sweep configuration

        Args:
            models: List of model names to evaluate
            tasks: List of task environment IDs to evaluate
            trials: Number of trials per model-task combination (default: 8)
            name: Name for the sweep
            wandb_project: WandB project name (default: factorio-{name})
            max_concurrent: Maximum concurrent processes (default: 4)
            pass_at_k_optimized: Enable Pass@K optimization features (default: False)

        Returns:
            SweepConfig configured for the custom sweep
        """
        return SweepConfig(
            name=name,
            description=f"Custom sweep: {len(models)} models × {len(tasks)} tasks × {trials} trials",
            models=models,
            tasks=tasks,
            num_trials_per_config=trials,
            max_concurrent_processes=max_concurrent,
            # Pass@K optimization features (optional)
            task_inner_loop_mode=pass_at_k_optimized,
            early_stop_on_success=pass_at_k_optimized,
            # Enable monitoring
            enable_wandb=True,
            wandb_project=wandb_project or f"factorio-{name}",
            # Results configuration
            output_dir=f"./sweep_results/{name}",
            save_intermediate_results=True,
            log_interval_minutes=20,
            # Execution parameters
            shuffle_execution_order=not pass_at_k_optimized,
            retry_failed_runs=True,
            max_retries=2,
            api_key_config_file="api_keys.json",
        )


class SweepRunner:
    """Runner for executing sweeps with optional resume capability"""

    @staticmethod
    async def run_sweep(
        config: SweepConfig, existing_sweep_id: Optional[str] = None
    ) -> dict:
        """Run or resume a sweep

        Args:
            config: Sweep configuration
            existing_sweep_id: Optional existing sweep ID to resume

        Returns:
            Results dictionary from the sweep
        """
        if existing_sweep_id:
            print(f"Resuming existing sweep: {existing_sweep_id}")
            manager = SweepManager(config, existing_sweep_id=existing_sweep_id)
        else:
            print(f"Starting new sweep: {config.name}")
            manager = SweepManager(config)

        print(f"Sweep ID: {manager.sweep_id}")
        print(f"Models: {len(config.models)}")
        print(f"Tasks: {len(config.tasks)}")
        print(f"Trials per config: {config.num_trials_per_config}")
        print(
            f"Total runs: {len(config.models) * len(config.tasks) * config.num_trials_per_config}"
        )

        if config.task_inner_loop_mode:
            print("✓ Task inner loop mode enabled")
        if config.early_stop_on_success:
            print("✓ Early stopping on success enabled")

        results = await manager.run_sweep()

        print("\n🎉 Sweep completed!")
        print(f"Results saved to: {config.output_dir}")
        if config.enable_wandb:
            print(f"WandB project: {config.wandb_project}")

        return results

    @classmethod
    async def run_test_small(cls, existing_sweep_id: Optional[str] = None) -> dict:
        """Run test_small sweep with optional resume"""
        config = SweepProfiles.test_small()
        return await cls.run_sweep(config, existing_sweep_id)

    @classmethod
    async def run_test_harder(cls, existing_sweep_id: Optional[str] = None) -> dict:
        """Run test_harder sweep with optional resume"""
        config = SweepProfiles.test_harder()
        return await cls.run_sweep(config, existing_sweep_id)

    @classmethod
    async def run_pass_at_k_optimized(
        cls, existing_sweep_id: Optional[str] = None
    ) -> dict:
        """Run pass_at_k_optimized sweep with optional resume"""
        config = SweepProfiles.pass_at_k_optimized()
        return await cls.run_sweep(config, existing_sweep_id)

    @classmethod
    async def run_production_medium(
        cls, existing_sweep_id: Optional[str] = None
    ) -> dict:
        """Run production_medium sweep with optional resume"""
        config = SweepProfiles.production_medium()
        return await cls.run_sweep(config, existing_sweep_id)

    @classmethod
    async def run_production_large(
        cls, existing_sweep_id: Optional[str] = None
    ) -> dict:
        """Run production_large sweep with optional resume"""
        config = SweepProfiles.production_large()
        return await cls.run_sweep(config, existing_sweep_id)

    @classmethod
    async def run_openrouter_grok_test(
        cls, existing_sweep_id: Optional[str] = None
    ) -> dict:
        """Run openrouter_grok_test sweep with optional resume"""
        config = SweepProfiles.openrouter_grok_test()
        return await cls.run_sweep(config, existing_sweep_id)

    @classmethod
    async def run_openrouter_tournament(
        cls, existing_sweep_id: Optional[str] = None
    ) -> dict:
        """Run openrouter_tournament sweep with optional resume"""
        config = SweepProfiles.openrouter_tournament()
        return await cls.run_sweep(config, existing_sweep_id)


async def run_sweep_profile(
    profile: str, existing_sweep_id: Optional[str] = None, **custom_kwargs
) -> dict:
    """Convenience function to run any sweep profile programmatically

    Args:
        profile: Name of the sweep profile to run
        existing_sweep_id: Optional sweep ID to resume from
        **custom_kwargs: Additional arguments for custom sweeps

    Returns:
        Results from the sweep

    Example:
        # Run a new sweep
        results = await run_sweep_profile("test_small")

        # Resume an existing sweep
        results = await run_sweep_profile("pass_at_k", existing_sweep_id="pass_at_k_20250106_120000_abc123")

        # Run custom sweep
        results = await run_sweep_profile(
            "custom",
            models=["gpt-5", "claude-3-sonnet"],
            tasks=["iron_ore_throughput"],
            trials=5
        )
    """
    runner = SweepRunner()

    if profile == "test_small":
        return await runner.run_test_small(existing_sweep_id)
    elif profile == "test_harder":
        return await runner.run_test_harder(existing_sweep_id)
    elif profile == "pass_at_k":
        return await runner.run_pass_at_k_optimized(existing_sweep_id)
    elif profile == "production_medium":
        return await runner.run_production_medium(existing_sweep_id)
    elif profile == "production_large":
        return await runner.run_production_large(existing_sweep_id)
    elif profile == "openrouter_grok":
        return await runner.run_openrouter_grok_test(existing_sweep_id)
    elif profile == "openrouter_tournament":
        return await runner.run_openrouter_tournament(existing_sweep_id)
    elif profile == "custom":
        config = SweepProfiles.custom(
            models=custom_kwargs.get("models", []),
            tasks=custom_kwargs.get("tasks", []),
            trials=custom_kwargs.get("trials", 8),
            name=custom_kwargs.get("name", "custom_sweep"),
            wandb_project=custom_kwargs.get("wandb_project"),
            max_concurrent=custom_kwargs.get("max_concurrent", 4),
            pass_at_k_optimized=custom_kwargs.get("pass_at_k_optimized", False),
        )
        return await runner.run_sweep(config, existing_sweep_id)
    else:
        raise ValueError(f"Unknown sweep profile: {profile}")


async def main():
    """Main entry point for running sweeps"""

    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python consolidated_sweep_config.py <profile> [options]")
        print("\nAvailable profiles:")
        print("  test_small        - Small test sweep (2 models, 2 tasks)")
        print("  test_harder       - Test with harder tasks")
        print("  pass_at_k         - Pass@K optimized sweep")
        print("  production_medium - Medium production sweep")
        print("  production_large  - Large production sweep")
        print("  openrouter_grok   - Test Grok models via OpenRouter")
        print("  openrouter_tournament - Full OpenRouter model tournament")
        print("  custom            - Custom configuration (requires additional args)")
        print("\nOptions:")
        print("  --resume <sweep_id>  - Resume an existing sweep")
        print("\nExamples:")
        print("  python consolidated_sweep_config.py test_small")
        print(
            "  python consolidated_sweep_config.py pass_at_k --resume pass_at_k_optimized_20250106_120000_abc123"
        )
        print(
            "  python consolidated_sweep_config.py custom --models gpt-5 claude-3-sonnet --tasks iron_ore_throughput --trials 5"
        )
        sys.exit(1)

    profile = sys.argv[1]

    # Check for resume option
    existing_sweep_id = None
    if "--resume" in sys.argv:
        resume_idx = sys.argv.index("--resume")
        if resume_idx + 1 < len(sys.argv):
            existing_sweep_id = sys.argv[resume_idx + 1]
            print(f"Will resume from sweep ID: {existing_sweep_id}")

    # Get the appropriate configuration
    if profile == "test_small":
        config = SweepProfiles.test_small()
    elif profile == "test_harder":
        config = SweepProfiles.test_harder()
    elif profile == "pass_at_k":
        config = SweepProfiles.pass_at_k_optimized()
    elif profile == "production_medium":
        config = SweepProfiles.production_medium()
    elif profile == "production_large":
        config = SweepProfiles.production_large()
    elif profile == "openrouter_grok":
        config = SweepProfiles.openrouter_grok_test()
    elif profile == "openrouter_tournament":
        config = SweepProfiles.openrouter_tournament()
    elif profile == "custom":
        # Parse custom configuration from command line
        models = []
        tasks = []
        trials = 8
        name = "custom_sweep"

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--models":
                i += 1
                while i < len(sys.argv) and not sys.argv[i].startswith("--"):
                    models.append(sys.argv[i])
                    i += 1
            elif sys.argv[i] == "--tasks":
                i += 1
                while i < len(sys.argv) and not sys.argv[i].startswith("--"):
                    tasks.append(sys.argv[i])
                    i += 1
            elif sys.argv[i] == "--trials":
                i += 1
                if i < len(sys.argv):
                    trials = int(sys.argv[i])
                    i += 1
            elif sys.argv[i] == "--name":
                i += 1
                if i < len(sys.argv):
                    name = sys.argv[i]
                    i += 1
            else:
                i += 1

        if not models or not tasks:
            print("Error: Custom sweep requires --models and --tasks")
            sys.exit(1)

        config = SweepProfiles.custom(models, tasks, trials, name)
    else:
        print(f"Unknown profile: {profile}")
        sys.exit(1)

    # Run the sweep
    runner = SweepRunner()
    await runner.run_sweep(config, existing_sweep_id)


if __name__ == "__main__":
    asyncio.run(main())
