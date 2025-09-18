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
    ResultsVisualizer,
    group_results_by_model,
)
from fle.eval.analysis.performance_metrics import PerformanceAnalyzer
from fle.eval.analysis.analysis_utils import create_leaderboard


async def analyze_sweep_by_id(sweep_id: str):
    """Analyze results for a specific sweep ID

    Args:
        sweep_id: The sweep ID to analyze (e.g. 'test_sweep_small_20250904_151635_2e06c621')
    """
    print(f"Analyzing sweep: {sweep_id}")
    print("=" * 60)

    analyzer = DatabaseAnalyzer()

    try:
        await analyzer.ensure_connection()

        # First, try a simple query to get basic sweep data
        print("📊 1. BASIC SWEEP DATA")
        print("-" * 40)

        # Simple query for sweep data
        basic_query = """
        SELECT 
            version, version_description, model, instance, 
            value, raw_reward, depth, token_usage,
            created_at, meta
        FROM programs 
        WHERE meta->>'sweep_id' = %s
        ORDER BY version, instance, created_at
        """

        basic_results = await analyzer.db_client.execute_query(basic_query, (sweep_id,))
        basic_df = pd.DataFrame(basic_results)

        if not basic_df.empty:
            print(f"Found {len(basic_df)} program results for sweep")
            print(f"Models: {basic_df['model'].unique().tolist()}")
            print(f"Instances: {sorted(basic_df['instance'].unique().tolist())}")
            print(
                f"Version descriptions: {basic_df['version_description'].unique().tolist()}"
            )

            # Calculate trajectory summaries manually
            trajectory_summaries = (
                basic_df.groupby(["version", "model", "instance"])
                .agg(
                    {
                        "value": ["max", "count"],
                        "raw_reward": "max",
                        "depth": "max",
                        "token_usage": "sum",
                        "version_description": "first",
                        "created_at": ["min", "max"],
                    }
                )
                .reset_index()
            )

            # Flatten column names
            trajectory_summaries.columns = [
                "version",
                "model",
                "instance",
                "max_reward",
                "num_steps",
                "max_raw_reward",
                "max_depth",
                "total_tokens",
                "version_description",
                "start_time",
                "end_time",
            ]

            # Add success column (assuming success is max_reward > 0)
            trajectory_summaries["success"] = trajectory_summaries["max_reward"] > 0

            print(f"\nTrajectory Overview ({len(trajectory_summaries)} trajectories):")
            display_cols = [
                "model",
                "instance",
                "max_reward",
                "success",
                "total_tokens",
                "num_steps",
            ]
            print(trajectory_summaries[display_cols].head(10))

        else:
            # Try the original method as fallback
            print("No results from basic query, trying original method...")
            trajectory_summaries = await analyzer.get_trajectory_summaries_by_sweep(
                sweep_id
            )

        if not trajectory_summaries.empty:
            print(f"Found {len(trajectory_summaries)} trajectories")
            print("\nTrajectory Overview:")
            display_cols = [
                "model",
                "task",
                "instance",
                "max_reward",
                "success",
                "total_tokens",
            ]
            available_cols = [
                col for col in display_cols if col in trajectory_summaries.columns
            ]
            print(trajectory_summaries[available_cols].head(10))

            # Success rate by model
            success_by_model = trajectory_summaries.groupby("model")["success"].agg(
                ["mean", "count"]
            )
            print("\n📈 Success Rate by Model:")
            for model, stats in success_by_model.iterrows():
                print(f"  {model}: {stats['mean']:.2%} ({stats['count']} trials)")

            # Success rate by task
            if "task" in trajectory_summaries.columns:
                success_by_task = trajectory_summaries.groupby("task")["success"].agg(
                    ["mean", "count"]
                )
                print("\n🎯 Success Rate by Task:")
                for task, stats in success_by_task.iterrows():
                    print(f"  {task}: {stats['mean']:.2%} ({stats['count']} trials)")

            # Create model comparison manually from our data
            print("\n📋 2. DETAILED MODEL COMPARISON")
            print("-" * 40)

            (
                trajectory_summaries.groupby("model")
                .agg(
                    {
                        "max_reward": ["mean", "std", "count"],
                        "success": ["mean", "sum"],
                        "total_tokens": "mean",
                        "num_steps": "mean",
                    }
                )
                .reset_index()
            )

            print("Model Performance Comparison:")
            for model in trajectory_summaries["model"].unique():
                model_data = trajectory_summaries[
                    trajectory_summaries["model"] == model
                ]
                print(f"\n  {model}:")
                print(f"    Trajectories: {len(model_data)}")
                print(f"    Success Rate: {model_data['success'].mean():.2%}")
                print(
                    f"    Mean Reward: {model_data['max_reward'].mean():.2f} ± {model_data['max_reward'].std():.2f}"
                )
                print(
                    f"    Reward Range: [{model_data['max_reward'].min():.1f}, {model_data['max_reward'].max():.1f}]"
                )
                print(f"    Avg Tokens: {model_data['total_tokens'].mean():.0f}")
                print(f"    Avg Steps: {model_data['num_steps'].mean():.1f}")

            # Task breakdown by extracting task from version_description
            print("\n🎯 3. TASK BREAKDOWN")
            print("-" * 40)

            # Extract task from version_description
            trajectory_summaries["task"] = trajectory_summaries[
                "version_description"
            ].str.extract(r"type:([^\\n]+)")

            if "task" in trajectory_summaries.columns:
                print("Task Performance Breakdown:")
                for task in trajectory_summaries["task"].unique():
                    task_data = trajectory_summaries[
                        trajectory_summaries["task"] == task
                    ]
                    if len(task_data) > 0:
                        print(f"\n  {task}:")
                        print(f"    Trajectories: {len(task_data)}")
                        print(f"    Success Rate: {task_data['success'].mean():.2%}")
                        print(
                            f"    Mean Reward: {task_data['max_reward'].mean():.2f} ± {task_data['max_reward'].std():.2f}"
                        )
                        print(f"    Avg Tokens: {task_data['total_tokens'].mean():.0f}")
                        print(f"    Models: {list(task_data['model'].unique())}")
            else:
                print("Could not extract task information from version descriptions")

            # Performance metrics analysis with Pass@K
            print("\n📊 4. PERFORMANCE METRICS ANALYSIS")
            print("-" * 40)

            print("Pass@K Analysis:")
            for model in trajectory_summaries["model"].unique():
                print(f"\n  Model: {model}")
                model_data = trajectory_summaries[
                    trajectory_summaries["model"] == model
                ]

                if "task" in model_data.columns:
                    for task in model_data["task"].unique():
                        task_data = model_data[model_data["task"] == task]
                        _analyze_model_task_performance(task_data, model, task)
                else:
                    _analyze_model_task_performance(model_data, model, "overall")

            # Export results
            print("\n💾 5. EXPORTING RESULTS")
            print("-" * 40)

            # Create sweep-specific directory structure like in create_comprehensive_report
            base_output_path = Path("./analysis_results")
            output_dir = base_output_path / sweep_id
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / "trajectory_summaries.csv"
            trajectory_summaries.to_csv(output_file, index=False)
            print(f"Exported trajectory summaries to: {output_file}")

            # Create version_infos.csv efficiently using SQL aggregation
            # First get the task from version_description since meta->>'task' might not exist
            version_query = """
            WITH version_stats AS (
                SELECT
                    version,
                    model,
                    instance,
                    COALESCE(
                        meta->>'task',
                        TRIM(SUBSTRING(version_description FROM 'type:([^\\n]+)')),
                        'unknown'
                    ) as task,
                    MAX(value) as max_reward,
                    MAX(CASE
                        WHEN meta->>'production_score' ~ '^[0-9]+\.?[0-9]*$'
                        THEN (meta->>'production_score')::float
                        ELSE 0
                    END) as max_production_score,
                    MAX(CASE WHEN state_json IS NOT NULL THEN 1 ELSE 0 END) as has_final_state,
                    COUNT(*) as program_count
                FROM programs
                WHERE meta->>'sweep_id' = %s
                GROUP BY version, model, instance,
                    COALESCE(
                        meta->>'task',
                        TRIM(SUBSTRING(version_description FROM 'type:([^\\n]+)')),
                        'unknown'
                    )
            )
            SELECT
                version,
                model,
                task,
                instance as trial_number,
                max_reward,
                max_production_score,
                CASE WHEN has_final_state = 1 THEN 'completed' ELSE 'partial' END as completion_status,
                CASE
                    WHEN task IN ('advanced_circuit_throughput', 'automation_science_pack_throughput',
                                 'battery_throughput', 'chemical_science_pack_throughput',
                                 'electronic_circuit_throughput', 'engine_unit_throughput',
                                 'inserter_throughput', 'iron_gear_wheel_throughput',
                                 'iron_ore_throughput', 'iron_plate_throughput',
                                 'logistics_science_pack_throughput', 'low_density_structure_throughput',
                                 'military_science_pack_throughput', 'piercing_round_throughput',
                                 'plastic_bar_throughput', 'processing_unit_throughput',
                                 'production_science_pack_throughput', 'steel_plate_throughput',
                                 'stone_wall_throughput', 'sulfur_throughput',
                                 'utility_science_pack_throughput') THEN
                        CASE WHEN max_reward >= 16 THEN 1 ELSE 0 END
                    WHEN task IN ('crude_oil_throughput', 'petroleum_gas_throughput', 'sufuric_acid_throughput') THEN
                        CASE WHEN max_reward >= 400 THEN 1 ELSE 0 END
                    ELSE
                        CASE WHEN max_reward > 0 THEN 1 ELSE 0 END
                END as task_success
            FROM version_stats
            ORDER BY version
            """

            version_results = await analyzer.db_client.execute_query(
                version_query, (sweep_id,)
            )

            if version_results:
                version_infos_df = pd.DataFrame(version_results)
            else:
                # Fallback to trajectory_summaries if SQL query fails
                version_infos_data = []
                for _, row in trajectory_summaries.iterrows():
                    # Extract task from version_description or use task column
                    task = row.get("task", "unknown")
                    if task == "unknown" and "version_description" in row:
                        task_match = pd.Series(
                            [row["version_description"]]
                        ).str.extract(r"type:([^\n]+)")
                        task = (
                            task_match.iloc[0, 0]
                            if not task_match.isna().iloc[0, 0]
                            else "unknown"
                        )

                    version_infos_data.append(
                        {
                            "version": row["version"],
                            "model": row["model"],
                            "task": task,
                            "trial_number": row.get("instance", 0),
                            "max_reward": row.get("max_reward", 0),
                            "max_production_score": 0,  # Not available in trajectory summaries
                            "completion_status": "completed"
                            if row.get("success", False)
                            else "partial",
                            "task_success": 1 if row.get("max_reward", 0) > 0 else 0,
                        }
                    )
                version_infos_df = pd.DataFrame(version_infos_data)

            if not version_infos_df.empty:
                output_file = output_dir / "version_infos.csv"
                version_infos_df.to_csv(output_file, index=False)
                print(f"Exported version infos to: {output_file}")

            # Export model comparison statistics
            model_comparison_data = []
            for model in trajectory_summaries["model"].unique():
                model_data = trajectory_summaries[
                    trajectory_summaries["model"] == model
                ]
                model_comparison_data.append(
                    {
                        "model": model,
                        "trajectories": len(model_data),
                        "success_rate": model_data["success"].mean(),
                        "mean_reward": model_data["max_reward"].mean(),
                        "std_reward": model_data["max_reward"].std(),
                        "min_reward": model_data["max_reward"].min(),
                        "max_reward": model_data["max_reward"].max(),
                        "mean_tokens": model_data["total_tokens"].mean(),
                        "mean_steps": model_data["num_steps"].mean(),
                    }
                )

            model_comparison_df = pd.DataFrame(model_comparison_data)
            output_file = output_dir / "model_comparison.csv"
            model_comparison_df.to_csv(output_file, index=False)
            print(f"Exported model comparison to: {output_file}")

            print(f"\n✅ Analysis complete for sweep: {sweep_id}")
        else:
            print("⚠️  No trajectory summaries found for this sweep")

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await analyzer.cleanup()


def _analyze_model_task_performance(task_data, model, task):
    """Helper function to analyze performance metrics for a model-task combination"""

    if len(task_data) == 0:
        return

    # Use the PerformanceAnalyzer to calculate metrics properly
    try:
        metrics = PerformanceAnalyzer.calculate_metrics(
            task_data,
            reward_column="max_reward",
            success_threshold=0.0,  # Since all rewards > 0 are successes
            token_column="total_tokens",
            step_column="num_steps",
            k_values=[1, 3, 5, 8],
        )

        print(f"    {task}:")
        print(f"      Success Rate: {metrics.success_rate:.2%}")
        print(f"      Pass@1: {metrics.pass_at_1:.2%}")
        if metrics.pass_at_k:
            for k in [3, 5, 8]:
                if k in metrics.pass_at_k and len(task_data) >= k:
                    print(f"      Pass@{k}: {metrics.pass_at_k[k]:.2%}")
        print(f"      Mean Reward: {metrics.mean_reward:.3f}")
        print(f"      Std Reward: {metrics.std_reward:.3f}")
        if metrics.mean_tokens:
            print(f"      Mean Tokens: {metrics.mean_tokens:.0f}")
        if metrics.tokens_per_success:
            print(f"      Tokens per Success: {metrics.tokens_per_success:.0f}")
    except Exception as e:
        print(f"    {task}: Error calculating metrics - {e}")
        # Fallback to basic analysis
        print(f"      Trajectories: {len(task_data)}")
        if "max_reward" in task_data.columns:
            print(f"      Mean Reward: {task_data['max_reward'].mean():.3f}")
        if "success" in task_data.columns:
            print(f"      Success Rate: {task_data['success'].mean():.2%}")


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
    sweep_id: str, output_dir: str = "./analysis_results"
):
    """Create comprehensive analysis report with visualizations

    Args:
        sweep_id: Sweep identifier to analyze
        output_dir: Directory to save analysis results
    """
    print(f"Creating comprehensive report for sweep: {sweep_id}")
    print(f"Output directory: {output_dir}")

    # Create sweep-specific subfolder
    base_output_path = Path(output_dir)
    output_path = base_output_path / sweep_id
    output_path.mkdir(parents=True, exist_ok=True)

    analyzer = DatabaseAnalyzer()
    visualizer = ResultsVisualizer()

    try:
        # Get comprehensive data using sweep ID
        print("Fetching data...")
        trajectory_df = await analyzer.get_trajectory_summaries_by_sweep(sweep_id)

        if trajectory_df.empty:
            print("No data found for specified sweep.")
            return

        print(f"Analyzing {len(trajectory_df)} trajectories")

        # Extract task information for better analysis
        if (
            "version_description" in trajectory_df.columns
            and "task" not in trajectory_df.columns
        ):
            trajectory_df = trajectory_df.copy()
            trajectory_df["task"] = trajectory_df["version_description"].str.extract(
                r"type:([^\n]+)"
            )

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
                report_name="analysis",
            )

            print("Visualizations saved:")
            for viz_type, file_path in viz_files.items():
                print(f"  {viz_type}: {file_path}")
        else:
            print(
                "Visualization tools not available - install matplotlib and seaborn for plots"
            )

        # Get unique versions from the sweep data
        versions = sorted(trajectory_df["version"].unique().tolist())

        # Create version_infos.csv efficiently using SQL aggregation
        print("Creating version infos...")

        # Use a single efficient SQL query with aggregation to get version summaries
        version_query = """
        WITH version_stats AS (
            SELECT
                version,
                model,
                instance,
                COALESCE(
                    meta->>'task',
                    TRIM(SUBSTRING(version_description FROM 'type:([^\\n]+)')),
                    'unknown'
                ) as task,
                MAX(value) as max_reward,
                MAX(CASE
                    WHEN meta->>'production_score' ~ '^[0-9]+\.?[0-9]*$'
                    THEN (meta->>'production_score')::float
                    ELSE 0
                END) as max_production_score,
                MAX(CASE WHEN state_json IS NOT NULL THEN 1 ELSE 0 END) as has_final_state,
                COUNT(*) as program_count
            FROM programs
            WHERE meta->>'sweep_id' = %s
            GROUP BY version, model, instance,
                COALESCE(
                    meta->>'task',
                    TRIM(SUBSTRING(version_description FROM 'type:([^\\n]+)')),
                    'unknown'
                )
        )
        SELECT
            version,
            model,
            task,
            instance as trial_number,
            max_reward,
            max_production_score,
            CASE WHEN has_final_state = 1 THEN 'completed' ELSE 'partial' END as completion_status,
            CASE WHEN max_reward > 0 THEN 1 ELSE 0 END as task_success
        FROM version_stats
        ORDER BY version
        """

        version_results = await analyzer.db_client.execute_query(
            version_query, (sweep_id,)
        )

        if version_results:
            version_infos_df = pd.DataFrame(version_results)
        else:
            # Fallback to trajectory_summaries if SQL query fails
            print("SQL query failed, using trajectory summaries fallback...")
            version_infos_data = []
            for _, row in trajectory_df.iterrows():
                # Extract task from version_description or use task column
                task = row.get("task", "unknown")
                if task == "unknown" and "version_description" in row:
                    task_match = pd.Series([row["version_description"]]).str.extract(
                        r"type:([^\n]+)"
                    )
                    task = (
                        task_match.iloc[0, 0]
                        if not task_match.isna().iloc[0, 0]
                        else "unknown"
                    )

                version_infos_data.append(
                    {
                        "version": row["version"],
                        "model": row["model"],
                        "task": task,
                        "trial_number": row.get("instance", 0),
                        "max_reward": row.get("final_reward", 0),
                        "max_production_score": 0,  # Not available in trajectory summaries
                        "completion_status": "completed"
                        if row.get("final_reward", 0) > 0
                        else "partial",
                        "task_success": 1 if row.get("final_reward", 0) > 0 else 0,
                    }
                )
            version_infos_df = pd.DataFrame(version_infos_data)

        if not version_infos_df.empty:
            version_infos_df.to_csv(output_path / "version_infos.csv", index=False)

        # Save trajectory summaries
        trajectory_df.to_csv(output_path / "trajectory_summaries.csv", index=False)

        # Save detailed results
        results_summary = {
            "sweep_id": sweep_id,
            "versions_analyzed": versions,
            "total_trajectories": len(trajectory_df),
            "models_analyzed": list(model_metrics.keys()),
            "leaderboard": leaderboard.to_dict("records"),
            "model_metrics": {
                model_name: metrics.to_dict()
                for model_name, metrics in model_metrics.items()
            },
        }

        with open(output_path / "analysis_summary.json", "w") as f:
            json.dump(results_summary, f, indent=2, default=str)

        print(f"\nComprehensive report saved to: {output_path}")
        print("Files generated:")
        print("  - leaderboard.csv")
        print("  - trajectory_summaries.csv")
        print("  - version_infos.csv")
        print("  - analysis_summary.json")
        if visualizer.enabled:
            print("  - Multiple visualization plots with prefix 'analysis_'")

        return str(output_path)

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
        print("  python analyze_sweep_results.py sweep [sweep_id]")
        print("  python analyze_sweep_results.py recent [hours]")
        print("  python analyze_sweep_results.py compare model1 model2 [model3 ...]")
        print("  python analyze_sweep_results.py tasks [model]")
        print("  python analyze_sweep_results.py report [sweep_id]")
        print("  python analyze_sweep_results.py monitor [project_name]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "sweep":
        sweep_id = (
            sys.argv[2]
            if len(sys.argv) > 2
            else "test_sweep_small_20250904_151635_2e06c621"
        )
        asyncio.run(analyze_sweep_by_id(sweep_id))

    elif command == "recent":
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
        sweep_id = (
            sys.argv[2]
            if len(sys.argv) > 2
            else "test_sweep_small_20250904_151635_2e06c621"
        )
        asyncio.run(create_comprehensive_report(sweep_id))

    elif command == "monitor":
        project = sys.argv[2] if len(sys.argv) > 2 else "factorio-learning-environment"
        asyncio.run(monitor_ongoing_sweep(project))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
