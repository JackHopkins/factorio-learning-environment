"""
Example script for analyzing sweep results using the analysis framework.

This script demonstrates how to load, analyze, and visualize results
from completed evaluation sweeps.
"""

import asyncio
import json
import pandas as pd
from pathlib import Path
from typing import List, Optional

from fle.eval.analysis import (
    DatabaseAnalyzer,
    PerformanceAnalyzer,
    ResultsVisualizer,
    group_results_by_model,
    create_leaderboard,
)


async def analyze_recent_results(hours: int = 24):
    """Analyze results from the last N hours

    Args:
        hours: Number of hours to look back
    """
    print(f"Analyzing results from the last {hours} hours...")

    analyzer = DatabaseAnalyzer()

    try:
        # Get recent results
        recent_df = await analyzer.get_recent_results(hours=hours)

        if recent_df.empty:
            print("No recent results found.")
            return

        print(f"Found {len(recent_df)} recent results")

        # Group by model for analysis
        results_by_model = group_results_by_model(recent_df)

        print("\nResults by model:")
        for model, model_df in results_by_model.items():
            success_rate = (model_df["value"] > 0).mean()
            print(f"  {model}: {len(model_df)} runs, {success_rate:.1%} success rate")

        # Get trajectory summaries for more detailed analysis
        versions = recent_df["version"].unique().tolist()
        trajectory_df = await analyzer.get_trajectory_summaries(versions)

        if not trajectory_df.empty:
            print(f"\nTrajectory analysis ({len(trajectory_df)} trajectories):")

            # Calculate performance metrics by model
            model_metrics = {}
            for model in trajectory_df["model"].unique():
                model_data = trajectory_df[trajectory_df["model"] == model]
                metrics = PerformanceAnalyzer.calculate_metrics(
                    model_data,
                    reward_column="final_reward",
                    token_column="total_tokens",
                )
                model_metrics[model] = metrics

                print(f"  {model}:")
                print(f"    Success rate: {metrics.success_rate:.1%}")
                print(f"    Mean reward: {metrics.mean_reward:.3f}")
                print(f"    Pass@1: {metrics.pass_at_1:.3f}")

    finally:
        await analyzer.cleanup()


async def compare_models(
    models: List[str], task_pattern: Optional[str] = None, min_trajectories: int = 5
):
    """Compare performance across specific models

    Args:
        models: List of model names to compare
        task_pattern: Optional task pattern to filter by
        min_trajectories: Minimum trajectories required per model
    """
    print(f"Comparing models: {', '.join(models)}")
    if task_pattern:
        print(f"Filtering by task pattern: {task_pattern}")

    analyzer = DatabaseAnalyzer()

    try:
        # Get model comparison data
        comparison_df = await analyzer.get_model_comparison(
            models=models, task_pattern=task_pattern, min_trajectories=min_trajectories
        )

        if comparison_df.empty:
            print("No data found for model comparison.")
            return

        print("\nModel Comparison Results:")
        print("=" * 50)

        # Sort by success rate
        comparison_df = comparison_df.sort_values("success_rate", ascending=False)

        for _, row in comparison_df.iterrows():
            print(f"\n{row['model']}:")
            print(f"  Trajectories: {row['num_trajectories']}")
            print(f"  Success rate: {row['success_rate']:.1%}")
            print(f"  Mean reward: {row['mean_reward']:.3f} ± {row['std_reward']:.3f}")
            print(f"  Reward range: [{row['min_reward']:.3f}, {row['max_reward']:.3f}]")
            print(f"  Avg tokens/trajectory: {row['mean_tokens_per_trajectory']:.0f}")

        # Statistical significance testing
        print("\n" + "=" * 50)
        print("Statistical Significance Tests:")

        # Get detailed results for statistical testing
        detailed_results = {}
        for model in models:
            model_results = await analyzer.get_results_by_model_and_task(
                model=model, task_pattern=task_pattern or ""
            )
            if not model_results.empty:
                trajectory_summary = await analyzer.get_trajectory_summaries(
                    model_results["version"].unique().tolist()
                )
                model_trajectory_data = trajectory_summary[
                    trajectory_summary["model"] == model
                ]
                detailed_results[model] = model_trajectory_data

        # Pairwise comparisons
        for i, model1 in enumerate(models):
            for model2 in models[i + 1 :]:
                if model1 in detailed_results and model2 in detailed_results:
                    metrics1 = PerformanceAnalyzer.calculate_metrics(
                        detailed_results[model1], reward_column="final_reward"
                    )
                    metrics2 = PerformanceAnalyzer.calculate_metrics(
                        detailed_results[model2], reward_column="final_reward"
                    )

                    test_result = PerformanceAnalyzer.statistical_significance_test(
                        metrics1, metrics2, metric="success_rate"
                    )

                    if "p_value" in test_result:
                        significance = (
                            "***"
                            if test_result["p_value"] < 0.001
                            else "**"
                            if test_result["p_value"] < 0.01
                            else "*"
                            if test_result["p_value"] < 0.05
                            else "ns"
                        )

                        print(
                            f"  {model1} vs {model2}: "
                            f"Δ = {test_result['difference']:.3f}, "
                            f"p = {test_result['p_value']:.4f} {significance}"
                        )

    finally:
        await analyzer.cleanup()


async def analyze_task_difficulty(model: Optional[str] = None):
    """Analyze task difficulty across different tasks

    Args:
        model: Optional model filter
    """
    print("Analyzing task difficulty...")
    if model:
        print(f"Filtering by model: {model}")

    analyzer = DatabaseAnalyzer()

    try:
        task_df = await analyzer.get_task_breakdown(model=model)

        if task_df.empty:
            print("No task data found.")
            return

        print("\nTask Difficulty Analysis:")
        print("=" * 50)

        # Sort by success rate (ascending - hardest tasks first)
        task_df = task_df.sort_values("success_rate", ascending=True)

        for _, row in task_df.iterrows():
            print(f"\n{row['task_name']} ({row['task_type']}):")
            print(f"  Trajectories: {row['num_trajectories']}")
            print(f"  Success rate: {row['success_rate']:.1%}")
            print(f"  Mean reward: {row['mean_reward']:.3f} ± {row['std_reward']:.3f}")
            print(f"  Reward range: [{row['min_reward']:.3f}, {row['max_reward']:.3f}]")

        # Summary statistics
        print("\n" + "=" * 50)
        print("Summary:")
        print(f"  Total tasks analyzed: {len(task_df)}")
        print(
            f"  Hardest task: {task_df.iloc[0]['task_name']} ({task_df.iloc[0]['success_rate']:.1%} success)"
        )
        print(
            f"  Easiest task: {task_df.iloc[-1]['task_name']} ({task_df.iloc[-1]['success_rate']:.1%} success)"
        )
        print(f"  Average success rate: {task_df['success_rate'].mean():.1%}")

    finally:
        await analyzer.cleanup()


async def create_comprehensive_report(
    versions: List[int], output_dir: str = "./analysis_results"
):
    """Create comprehensive analysis report with visualizations

    Args:
        versions: List of version numbers to analyze
        output_dir: Directory to save analysis results
    """
    print(f"Creating comprehensive report for versions: {versions}")
    print(f"Output directory: {output_dir}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    analyzer = DatabaseAnalyzer()
    visualizer = ResultsVisualizer()

    try:
        # Get comprehensive data
        print("Fetching data...")
        trajectory_df = await analyzer.get_trajectory_summaries(versions)

        if trajectory_df.empty:
            print("No data found for specified versions.")
            return

        print(f"Analyzing {len(trajectory_df)} trajectories")

        # Calculate performance metrics by model
        print("Calculating performance metrics...")
        results_by_model = group_results_by_model(trajectory_df)
        model_metrics = {}

        for model, model_data in results_by_model.items():
            metrics = PerformanceAnalyzer.calculate_metrics(
                model_data,
                reward_column="final_reward",
                token_column="total_tokens",
                step_column="num_steps",
            )
            model_metrics[model] = metrics

        # Create leaderboard
        leaderboard = create_leaderboard(model_metrics)
        print("\nLeaderboard:")
        print(leaderboard.to_string(index=False))

        # Save leaderboard to file
        leaderboard.to_csv(output_path / "leaderboard.csv", index=False)

        # Create visualizations
        print("Creating visualizations...")
        if visualizer.enabled:
            viz_files = visualizer.create_comprehensive_report(
                model_metrics=model_metrics,
                results_df=trajectory_df,
                output_dir=str(output_path),
                report_name="sweep_analysis",
            )

            print("Visualizations saved:")
            for viz_type, file_path in viz_files.items():
                print(f"  {viz_type}: {file_path}")

        # Save detailed results
        results_summary = {
            "versions_analyzed": versions,
            "total_trajectories": len(trajectory_df),
            "models_analyzed": list(model_metrics.keys()),
            "leaderboard": leaderboard.to_dict("records"),
            "model_metrics": {
                model: metrics.to_dict() for model, metrics in model_metrics.items()
            },
        }

        with open(output_path / "analysis_summary.json", "w") as f:
            json.dump(results_summary, f, indent=2, default=str)

        print(f"\nComprehensive report saved to: {output_path}")

    finally:
        await analyzer.cleanup()


async def monitor_ongoing_sweep(
    wandb_project: str = "factorio-learning-environment",
    check_interval_minutes: int = 10,
):
    """Monitor an ongoing sweep with real-time analysis

    Args:
        wandb_project: WandB project name to monitor
        check_interval_minutes: How often to check for new results
    """
    print("Monitoring ongoing sweep...")
    print(f"WandB project: {wandb_project}")
    print(f"Check interval: {check_interval_minutes} minutes")

    analyzer = DatabaseAnalyzer()

    try:
        while True:
            print(f"\n{'=' * 50}")
            print(f"Checking for new results... ({pd.Timestamp.now()})")

            # Get recent results (last 2 * check_interval to ensure we catch everything)
            recent_df = await analyzer.get_recent_results(
                hours=2 * check_interval_minutes / 60
            )

            if not recent_df.empty:
                print(f"Found {len(recent_df)} recent results")

                # Quick analysis
                versions = recent_df["version"].unique()
                if len(versions) > 0:
                    trajectory_df = await analyzer.get_trajectory_summaries(
                        versions.tolist()
                    )

                    if not trajectory_df.empty:
                        # Model performance summary
                        for model in trajectory_df["model"].unique():
                            model_data = trajectory_df[trajectory_df["model"] == model]
                            success_rate = (model_data["final_reward"] > 0).mean()
                            print(
                                f"  {model}: {len(model_data)} trajectories, "
                                f"{success_rate:.1%} success"
                            )
            else:
                print("No new results found")

            # Wait before next check
            print(f"Sleeping for {check_interval_minutes} minutes...")
            await asyncio.sleep(check_interval_minutes * 60)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    finally:
        await analyzer.cleanup()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python analyze_sweep_results.py recent [hours]")
        print("  python analyze_sweep_results.py compare model1 model2 [model3 ...]")
        print("  python analyze_sweep_results.py tasks [model]")
        print(
            "  python analyze_sweep_results.py report version1 version2 [version3 ...]"
        )
        print("  python analyze_sweep_results.py monitor [project_name]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "recent":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        asyncio.run(analyze_recent_results(hours))

    elif command == "compare":
        models = sys.argv[2:]
        if len(models) < 2:
            print("Need at least 2 models to compare")
            sys.exit(1)
        asyncio.run(compare_models(models))

    elif command == "tasks":
        model = sys.argv[2] if len(sys.argv) > 2 else None
        asyncio.run(analyze_task_difficulty(model))

    elif command == "report":
        versions = [int(v) for v in sys.argv[2:]]
        if not versions:
            print("Need at least one version number")
            sys.exit(1)
        asyncio.run(create_comprehensive_report(versions))

    elif command == "monitor":
        project = sys.argv[2] if len(sys.argv) > 2 else "factorio-learning-environment"
        asyncio.run(monitor_ongoing_sweep(project))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
