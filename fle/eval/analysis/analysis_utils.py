"""
Utility functions for evaluation analysis.
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np


def group_results_by_model(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Group results DataFrame by model

    Args:
        df: DataFrame with results containing 'model' column

    Returns:
        Dictionary mapping model names to their data
    """
    if "model" not in df.columns:
        raise ValueError("DataFrame must contain 'model' column")

    return {model: group_data for model, group_data in df.groupby("model")}


def group_results_by_task(
    df: pd.DataFrame, task_column: str = "version_description"
) -> Dict[str, pd.DataFrame]:
    """Group results DataFrame by task

    Args:
        df: DataFrame with results
        task_column: Column name containing task information

    Returns:
        Dictionary mapping task names to their data
    """
    if task_column not in df.columns:
        raise ValueError(f"DataFrame must contain '{task_column}' column")

    # Extract task names from version description
    task_groups = {}
    for _, row in df.iterrows():
        task_desc = row[task_column]

        # Try to extract clean task name
        if "type:" in task_desc:
            task_name = task_desc.split("type:")[1].split("\n")[0].strip()
        else:
            task_name = task_desc

        if task_name not in task_groups:
            task_groups[task_name] = []
        task_groups[task_name].append(row)

    # Convert lists back to DataFrames
    return {task: pd.DataFrame(rows) for task, rows in task_groups.items()}


def calculate_pass_at_k(successes: np.ndarray, k_values: List[int]) -> Dict[int, float]:
    """Calculate pass@k for multiple k values

    Args:
        successes: Boolean array indicating success for each trajectory
        k_values: List of k values to calculate

    Returns:
        Dictionary mapping k to pass@k value
    """
    from .performance_metrics import PerformanceAnalyzer

    results = {}
    for k in k_values:
        results[k] = PerformanceAnalyzer.calculate_pass_at_k(successes, k)
    return results


def get_trajectory_summary(
    df: pd.DataFrame,
    version_col: str = "version",
    instance_col: str = "instance",
    reward_col: str = "value",
    step_col: str = "depth",
) -> pd.DataFrame:
    """Create trajectory-level summary from step-level data

    Args:
        df: DataFrame with step-level results
        version_col: Column name for version/experiment ID
        instance_col: Column name for instance/trajectory ID
        reward_col: Column name for reward values
        step_col: Column name for step numbers

    Returns:
        DataFrame with one row per trajectory
    """
    required_cols = [version_col, instance_col, reward_col, step_col]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"DataFrame missing required columns: {missing_cols}")

    # Group by trajectory (version + instance)
    trajectory_groups = df.groupby([version_col, instance_col])

    summaries = []
    for (version, instance), group in trajectory_groups:
        summary = {
            version_col: version,
            instance_col: instance,
            "final_reward": group[reward_col].max(),
            "final_step": group[step_col].max(),
            "num_steps": len(group),
            "first_positive_reward_step": None,
            "trajectory_length": group[step_col].max() - group[step_col].min() + 1,
        }

        # Find first step with positive reward
        positive_rewards = group[group[reward_col] > 0]
        if not positive_rewards.empty:
            summary["first_positive_reward_step"] = positive_rewards[step_col].min()

        # Add other columns if available
        for col in ["model", "version_description", "token_usage", "created_at"]:
            if col in group.columns:
                summary[col] = group[col].iloc[
                    0
                ]  # Take first value (should be same for all steps)

        # Aggregate token usage if available
        if "token_usage" in group.columns:
            summary["total_tokens"] = group["token_usage"].sum()

        summaries.append(summary)

    return pd.DataFrame(summaries)


def extract_task_metadata(version_description: str) -> Dict[str, Any]:
    """Extract structured metadata from version description

    Args:
        version_description: String containing task metadata

    Returns:
        Dictionary with extracted metadata
    """
    metadata = {}

    if not version_description:
        return metadata

    # Parse key:value pairs separated by newlines
    lines = version_description.split("\n")
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()

    # Extract specific common fields
    if "type" in metadata:
        metadata["task_type"] = metadata["type"]

    if "model" in metadata:
        metadata["model_name"] = metadata["model"]

    if "num_agents" in metadata:
        try:
            metadata["num_agents"] = int(metadata["num_agents"])
        except ValueError:
            pass

    return metadata


def calculate_efficiency_metrics(
    df: pd.DataFrame,
    success_threshold: float = 0.0,
    reward_col: str = "final_reward",
    token_col: str = "total_tokens",
    time_col: Optional[str] = None,
) -> Dict[str, float]:
    """Calculate efficiency metrics for trajectories

    Args:
        df: DataFrame with trajectory results
        success_threshold: Threshold for considering trajectory successful
        reward_col: Column with final rewards
        token_col: Column with token counts
        time_col: Optional column with execution times

    Returns:
        Dictionary with efficiency metrics
    """
    if df.empty:
        return {}

    metrics = {}

    # Basic efficiency metrics
    if token_col in df.columns:
        metrics["mean_tokens_all"] = df[token_col].mean()
        metrics["median_tokens_all"] = df[token_col].median()

        # Tokens per success
        successful = df[df[reward_col] > success_threshold]
        if not successful.empty:
            metrics["mean_tokens_successful"] = successful[token_col].mean()
            metrics["median_tokens_successful"] = successful[token_col].median()

            # Efficiency ratio (tokens per successful trajectory / tokens per all trajectories)
            metrics["token_efficiency_ratio"] = (
                metrics["mean_tokens_successful"] / metrics["mean_tokens_all"]
            )

    # Time-based metrics if available
    if time_col and time_col in df.columns:
        metrics["mean_time_all"] = df[time_col].mean()
        metrics["median_time_all"] = df[time_col].median()

        successful = df[df[reward_col] > success_threshold]
        if not successful.empty:
            metrics["mean_time_successful"] = successful[time_col].mean()
            metrics["median_time_successful"] = successful[time_col].median()

    # Reward efficiency
    metrics["mean_reward"] = df[reward_col].mean()
    metrics["reward_std"] = df[reward_col].std()
    metrics["reward_efficiency"] = (
        metrics["mean_reward"] / metrics["reward_std"]
        if metrics["reward_std"] > 0
        else 0
    )

    return metrics


def find_performance_outliers(
    df: pd.DataFrame,
    metric_col: str = "final_reward",
    method: str = "iqr",
    threshold: float = 1.5,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Identify performance outliers in results

    Args:
        df: DataFrame with results
        metric_col: Column to analyze for outliers
        method: Method to use ('iqr' or 'zscore')
        threshold: Threshold for outlier detection

    Returns:
        Tuple of (outliers_df, normal_df)
    """
    if df.empty or metric_col not in df.columns:
        return pd.DataFrame(), df

    values = df[metric_col]

    if method == "iqr":
        Q1 = values.quantile(0.25)
        Q3 = values.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR

        outliers_mask = (values < lower_bound) | (values > upper_bound)

    elif method == "zscore":
        mean = values.mean()
        std = values.std()
        z_scores = np.abs((values - mean) / std)

        outliers_mask = z_scores > threshold

    else:
        raise ValueError(f"Unknown outlier detection method: {method}")

    outliers = df[outliers_mask]
    normal = df[~outliers_mask]

    return outliers, normal


def aggregate_results_by_time(
    df: pd.DataFrame,
    time_col: str = "created_at",
    metric_col: str = "final_reward",
    window: str = "1H",  # pandas time window format
) -> pd.DataFrame:
    """Aggregate results over time windows

    Args:
        df: DataFrame with timestamped results
        time_col: Column with timestamps
        metric_col: Column to aggregate
        window: Time window for aggregation (pandas format)

    Returns:
        DataFrame with time-aggregated results
    """
    if df.empty or time_col not in df.columns:
        return pd.DataFrame()

    # Ensure time column is datetime
    df_copy = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_copy[time_col]):
        df_copy[time_col] = pd.to_datetime(df_copy[time_col])

    # Set time column as index for resampling
    df_copy = df_copy.set_index(time_col)

    # Aggregate by time window
    aggregated = (
        df_copy[metric_col]
        .resample(window)
        .agg(["count", "mean", "std", "min", "max", "median"])
        .reset_index()
    )

    # Rename columns for clarity
    aggregated.columns = [
        "timestamp",
        "num_trajectories",
        "mean_reward",
        "std_reward",
        "min_reward",
        "max_reward",
        "median_reward",
    ]

    # Calculate success rate if reward threshold can be inferred
    success_threshold = 0.0  # Default threshold
    df_copy = df_copy.reset_index()

    success_counts = (
        df_copy[df_copy[metric_col] > success_threshold]
        .set_index(time_col)[metric_col]
        .resample(window)
        .count()
    )
    total_counts = df_copy.set_index(time_col)[metric_col].resample(window).count()

    success_rates = (success_counts / total_counts).fillna(0)
    aggregated["success_rate"] = success_rates.values

    return aggregated


def compare_model_performance_statistical(
    results_dict: Dict[str, pd.DataFrame],
    metric_col: str = "final_reward",
    test_type: str = "mannwhitney",
) -> pd.DataFrame:
    """Statistical comparison of model performance

    Args:
        results_dict: Dictionary mapping model names to their results
        metric_col: Column to compare
        test_type: Statistical test to use ('mannwhitney', 'ttest', 'ks')

    Returns:
        DataFrame with pairwise comparison results
    """
    from scipy import stats

    models = list(results_dict.keys())
    comparisons = []

    for i, model1 in enumerate(models):
        for j, model2 in enumerate(models):
            if i >= j:  # Only do each comparison once
                continue

            data1 = results_dict[model1][metric_col]
            data2 = results_dict[model2][metric_col]

            if len(data1) == 0 or len(data2) == 0:
                continue

            comparison = {
                "model1": model1,
                "model2": model2,
                "n1": len(data1),
                "n2": len(data2),
                "mean1": data1.mean(),
                "mean2": data2.mean(),
                "std1": data1.std(),
                "std2": data2.std(),
                "difference": data1.mean() - data2.mean(),
            }

            try:
                if test_type == "mannwhitney":
                    # Mann-Whitney U test (non-parametric)
                    stat, p_value = stats.mannwhitneyu(
                        data1, data2, alternative="two-sided"
                    )
                    comparison["test"] = "Mann-Whitney U"

                elif test_type == "ttest":
                    # Independent t-test
                    stat, p_value = stats.ttest_ind(data1, data2)
                    comparison["test"] = "t-test"

                elif test_type == "ks":
                    # Kolmogorov-Smirnov test
                    stat, p_value = stats.ks_2samp(data1, data2)
                    comparison["test"] = "Kolmogorov-Smirnov"

                else:
                    raise ValueError(f"Unknown test type: {test_type}")

                comparison["statistic"] = stat
                comparison["p_value"] = p_value
                comparison["significant_05"] = p_value < 0.05
                comparison["significant_01"] = p_value < 0.01

            except Exception as e:
                comparison["error"] = str(e)
                comparison["statistic"] = np.nan
                comparison["p_value"] = np.nan

            comparisons.append(comparison)

    return pd.DataFrame(comparisons)


def create_leaderboard(
    results_dict: Dict[str, Any],
    primary_metric: str = "success_rate",
    secondary_metrics: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Create a leaderboard from model results

    Args:
        results_dict: Dictionary with model results (can contain PerformanceMetrics or dicts)
        primary_metric: Main metric to sort by
        secondary_metrics: Additional metrics to include

    Returns:
        DataFrame with leaderboard
    """
    secondary_metrics = secondary_metrics or [
        "mean_reward",
        "pass_at_1",
        "num_trajectories",
    ]

    rows = []
    for model, results in results_dict.items():
        row = {"model": model}

        # Handle both PerformanceMetrics objects and dictionaries
        if hasattr(results, "to_dict"):
            results_dict_data = results.to_dict()
        else:
            results_dict_data = results

        # Add primary metric
        row[primary_metric] = results_dict_data.get(primary_metric, 0)

        # Add secondary metrics
        for metric in secondary_metrics:
            row[metric] = results_dict_data.get(metric, 0)

        # Calculate rank score (weighted combination)
        rank_score = row[primary_metric]  # Primary metric weight = 1.0
        if "mean_reward" in row:
            rank_score += 0.3 * row["mean_reward"]  # Secondary weight = 0.3
        if "pass_at_1" in row:
            rank_score += 0.2 * row["pass_at_1"]  # Tertiary weight = 0.2

        row["rank_score"] = rank_score
        rows.append(row)

    leaderboard = pd.DataFrame(rows)

    # Sort by primary metric (descending)
    leaderboard = leaderboard.sort_values(primary_metric, ascending=False)

    # Add rank column
    leaderboard["rank"] = range(1, len(leaderboard) + 1)

    # Reorder columns
    column_order = (
        ["rank", "model", primary_metric] + secondary_metrics + ["rank_score"]
    )
    leaderboard = leaderboard[
        [col for col in column_order if col in leaderboard.columns]
    ]

    return leaderboard
