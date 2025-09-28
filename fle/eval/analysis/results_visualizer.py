"""
Visualization utilities for evaluation results analysis.
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import seaborn as sns

    PLOTTING_AVAILABLE = True

    # Set style
    plt.style.use("default")
    sns.set_palette("husl")

except ImportError:
    PLOTTING_AVAILABLE = False

from .performance_metrics import PerformanceMetrics


class ResultsVisualizer:
    """Creates visualizations for evaluation results"""

    def __init__(self, figsize: Tuple[int, int] = (12, 8), dpi: int = 100):
        """Initialize visualizer

        Args:
            figsize: Default figure size
            dpi: Figure DPI for high-quality plots
        """
        self.figsize = figsize
        self.dpi = dpi
        self.enabled = PLOTTING_AVAILABLE

        if not self.enabled:
            print("Plotting not available - install matplotlib and seaborn")

    def _is_task_successful(self, task_name: str, reward: float) -> bool:
        """Determine if a task result is successful based on task-specific criteria

        Args:
            task_name: Name of the task (e.g., 'advanced_circuit_throughput')
            reward: Final reward achieved

        Returns:
            True if the task was successful, False otherwise
        """
        try:
            # For throughput tasks, success is meeting the quota of 16
            if "throughput" in task_name.lower():
                # Most throughput tasks have quota of 16
                if task_name.lower() in [
                    "crude_oil_throughput",
                    "petroleum_gas_throughput",
                    "sufuric_acid_throughput",
                ]:
                    return reward >= 400  # Fluid tasks have higher quotas
                else:
                    return reward >= 16  # Standard throughput tasks

            # For other task types, use positive reward as success criteria
            else:
                return reward > 0

        except Exception:
            # Fallback to simple positive reward check if task config unavailable
            return reward > 0

    def plot_model_comparison(
        self,
        model_metrics: Dict[str, PerformanceMetrics],
        metric: str = "success_rate",
        title: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Optional[plt.Figure]:
        """Create bar plot comparing models

        Args:
            model_metrics: Dictionary mapping model names to PerformanceMetrics
            metric: Metric to plot
            title: Optional plot title
            save_path: Optional path to save figure

        Returns:
            matplotlib Figure object if plotting available
        """
        if not self.enabled:
            return None

        # Extract data
        models = list(model_metrics.keys())
        values = [getattr(model_metrics[model], metric) for model in models]

        # Create plot
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        bars = ax.bar(models, values, color=sns.color_palette("husl", len(models)))

        # Customize plot
        ax.set_xlabel("Model")
        ax.set_ylabel(metric.replace("_", " ").title())
        ax.set_title(title or f"Model Comparison: {metric.replace('_', ' ').title()}")

        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{value:.3f}",
                ha="center",
                va="bottom",
            )

        # Rotate x-axis labels if many models
        if len(models) > 5:
            plt.xticks(rotation=45, ha="right")

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        return fig

    def plot_pass_at_k(
        self,
        model_metrics: Dict[str, PerformanceMetrics],
        k_values: Optional[List[int]] = None,
        title: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Optional[plt.Figure]:
        """Plot pass@k curves for different models

        Args:
            model_metrics: Dictionary mapping model names to PerformanceMetrics
            k_values: List of k values to plot (inferred if None)
            title: Optional plot title
            save_path: Optional path to save figure

        Returns:
            matplotlib Figure object if plotting available
        """
        if not self.enabled:
            return None

        # Infer k_values if not provided
        if k_values is None:
            k_values = set()
            for metrics in model_metrics.values():
                if metrics.pass_at_k:
                    k_values.update(metrics.pass_at_k.keys())
            k_values = sorted(list(k_values))

        if not k_values:
            print("No pass@k data available")
            return None

        # Create plot
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        for model, metrics in model_metrics.items():
            if metrics.pass_at_k:
                k_vals = []
                pass_vals = []
                for k in k_values:
                    if k in metrics.pass_at_k:
                        k_vals.append(k)
                        pass_vals.append(metrics.pass_at_k[k])

                ax.plot(k_vals, pass_vals, marker="o", label=model, linewidth=2)

        ax.set_xlabel("k (number of attempts)")
        ax.set_ylabel("Pass@k")
        ax.set_title(title or "Pass@k Comparison")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Set y-axis to [0, 1] range
        ax.set_ylim(0, 1)

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        return fig

    def plot_reward_distribution(
        self,
        results_df: pd.DataFrame,
        group_by: str = "model",
        reward_col: str = "final_reward",
        title: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Optional[plt.Figure]:
        """Plot reward distributions by group

        Args:
            results_df: DataFrame with results
            group_by: Column to group by
            reward_col: Column containing rewards
            title: Optional plot title
            save_path: Optional path to save figure

        Returns:
            matplotlib Figure object if plotting available
        """
        if not self.enabled:
            return None

        if group_by not in results_df.columns or reward_col not in results_df.columns:
            print(f"Required columns not found: {group_by}, {reward_col}")
            return None

        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        # Create violin plot or box plot
        try:
            sns.violinplot(data=results_df, x=group_by, y=reward_col, ax=ax)
        except Exception:
            # Fallback to box plot if violin plot fails
            sns.boxplot(data=results_df, x=group_by, y=reward_col, ax=ax)

        ax.set_xlabel(group_by.replace("_", " ").title())
        ax.set_ylabel(reward_col.replace("_", " ").title())
        ax.set_title(
            title or f"Reward Distribution by {group_by.replace('_', ' ').title()}"
        )

        # Rotate x-axis labels if needed
        if results_df[group_by].nunique() > 5:
            plt.xticks(rotation=45, ha="right")

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        return fig

    def plot_efficiency_scatter(
        self,
        results_df: pd.DataFrame,
        x_col: str = "total_tokens",
        y_col: str = "final_reward",
        color_by: str = "model",
        title: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Optional[plt.Figure]:
        """Create efficiency scatter plot

        Args:
            results_df: DataFrame with results
            x_col: Column for x-axis (e.g., tokens)
            y_col: Column for y-axis (e.g., reward)
            color_by: Column to color points by
            title: Optional plot title
            save_path: Optional path to save figure

        Returns:
            matplotlib Figure object if plotting available
        """
        if not self.enabled:
            return None

        required_cols = [x_col, y_col, color_by]
        missing_cols = [col for col in required_cols if col not in results_df.columns]
        if missing_cols:
            print(f"Missing columns: {missing_cols}")
            return None

        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        # Create scatter plot
        for group in results_df[color_by].unique():
            group_data = results_df[results_df[color_by] == group]
            ax.scatter(
                group_data[x_col], group_data[y_col], label=group, alpha=0.7, s=50
            )

        ax.set_xlabel(x_col.replace("_", " ").title())
        ax.set_ylabel(y_col.replace("_", " ").title())
        ax.set_title(
            title
            or f"{y_col.replace('_', ' ').title()} vs {x_col.replace('_', ' ').title()}"
        )
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        return fig

    def plot_learning_curves(
        self,
        results_df: pd.DataFrame,
        time_col: str = "created_at",
        metric_col: str = "final_reward",
        group_by: str = "model",
        window: str = "1H",
        title: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Optional[plt.Figure]:
        """Plot learning curves over time

        Args:
            results_df: DataFrame with timestamped results
            time_col: Column with timestamps
            metric_col: Column with metric values
            group_by: Column to group by
            window: Time window for rolling average
            title: Optional plot title
            save_path: Optional path to save figure

        Returns:
            matplotlib Figure object if plotting available
        """
        if not self.enabled:
            return None

        from .analysis_utils import aggregate_results_by_time

        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        for group in results_df[group_by].unique():
            group_data = results_df[results_df[group_by] == group]

            if len(group_data) < 2:
                continue

            try:
                # Aggregate by time windows
                agg_data = aggregate_results_by_time(
                    group_data, time_col, metric_col, window
                )

                if not agg_data.empty:
                    ax.plot(
                        agg_data["timestamp"],
                        agg_data["mean_reward"],
                        label=group,
                        linewidth=2,
                        marker="o",
                    )

                    # Add confidence bands if we have std
                    if "std_reward" in agg_data.columns:
                        ax.fill_between(
                            agg_data["timestamp"],
                            agg_data["mean_reward"] - agg_data["std_reward"],
                            agg_data["mean_reward"] + agg_data["std_reward"],
                            alpha=0.2,
                        )

            except Exception as e:
                print(f"Error plotting learning curve for {group}: {e}")
                continue

        ax.set_xlabel("Time")
        ax.set_ylabel(metric_col.replace("_", " ").title())
        ax.set_title(title or f"{metric_col.replace('_', ' ').title()} Over Time")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Format x-axis for better readability
        fig.autofmt_xdate()

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        return fig

    def plot_task_difficulty_heatmap(
        self,
        results_df: pd.DataFrame,
        model_col: str = "model",
        task_col: str = "version_description",
        metric_col: str = "final_reward",
        success_threshold: float = 0.0,
        title: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Optional[plt.Figure]:
        """Create heatmap of success rates by model and task

        Args:
            results_df: DataFrame with results
            model_col: Column with model names
            task_col: Column with task information
            metric_col: Column with performance metric
            success_threshold: Threshold for success
            title: Optional plot title
            save_path: Optional path to save figure

        Returns:
            matplotlib Figure object if plotting available
        """
        if not self.enabled:
            return None

        # Extract task names from version descriptions
        task_names = []
        for desc in results_df[task_col]:
            if "type:" in desc:
                task_name = desc.split("type:")[1].split("\n")[0].strip()
            else:
                task_name = desc
            task_names.append(task_name)

        results_df = results_df.copy()
        results_df["task_name"] = task_names

        # Calculate success rates for each model-task combination
        models = sorted(results_df[model_col].unique())
        tasks = sorted(results_df["task_name"].unique())

        heatmap_data = np.zeros((len(models), len(tasks)))

        for i, model in enumerate(models):
            for j, task in enumerate(tasks):
                subset = results_df[
                    (results_df[model_col] == model) & (results_df["task_name"] == task)
                ]
                if len(subset) > 0:
                    # Use task-specific success criteria instead of simple threshold
                    successes = []
                    for _, row in subset.iterrows():
                        task_name = row["task_name"]
                        reward = row[metric_col]
                        is_successful = self._is_task_successful(task_name, reward)
                        successes.append(is_successful)

                    success_rate = np.mean(successes) if successes else 0.0
                    heatmap_data[i, j] = success_rate

        # Create heatmap
        fig, ax = plt.subplots(
            figsize=(max(10, len(tasks) * 0.8), max(6, len(models) * 0.5)), dpi=self.dpi
        )

        sns.heatmap(
            heatmap_data,
            xticklabels=tasks,
            yticklabels=models,
            annot=True,
            fmt=".2f",
            cmap="RdYlGn",
            vmin=0,
            vmax=1,
            ax=ax,
        )

        ax.set_xlabel("Task")
        ax.set_ylabel("Model")
        ax.set_title(title or "Success Rate Heatmap: Model × Task")

        plt.xticks(rotation=45, ha="right")
        plt.yticks(rotation=0)
        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        return fig

    def plot_task_success_classification_heatmap(
        self,
        results_df: pd.DataFrame,
        model_col: str = "model",
        task_col: str = "version_description",
        metric_col: str = "final_reward",
        title: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Optional[plt.Figure]:
        """Create heatmap showing success classification by model and task

        Colors:
        - Green (2): At least one full success (meets quota)
        - Yellow (1): Partial success (reward > 0 but below quota)
        - Red (0): No success (all rewards <= 0)

        Args:
            results_df: DataFrame with results
            model_col: Column with model names
            task_col: Column with task information
            metric_col: Column with performance metric
            title: Optional plot title
            save_path: Optional path to save figure

        Returns:
            matplotlib Figure object if plotting available
        """
        if not self.enabled:
            return None

        # Extract task names from version descriptions
        task_names = []
        for desc in results_df[task_col]:
            if "type:" in desc:
                task_name = desc.split("type:")[1].split("\n")[0].strip()
            else:
                task_name = desc
            task_names.append(task_name)

        results_df = results_df.copy()
        results_df["task_name"] = task_names

        # First pass: calculate data for all model-task combinations to determine sorting
        models = sorted(results_df[model_col].unique())
        tasks = sorted(results_df["task_name"].unique())

        # Dictionary to store classifications for sorting
        model_task_data = {}

        for model in models:
            for task in tasks:
                subset = results_df[
                    (results_df[model_col] == model) & (results_df["task_name"] == task)
                ]
                classification = 0  # Default to no success

                if len(subset) > 0:
                    # Classify success levels
                    has_full_success = False
                    has_partial_success = False

                    for _, row in subset.iterrows():
                        task_name = row["task_name"]
                        reward = row[metric_col]

                        # Check for full success
                        if self._is_task_successful(task_name, reward):
                            has_full_success = True
                            break  # No need to check further if we have full success

                        # Check for partial success
                        elif reward > 0:
                            has_partial_success = True

                    # Assign classification:
                    # 2 = Green (at least one full success)
                    # 1 = Yellow (partial success but no full success)
                    # 0 = Red (no success at all)
                    if has_full_success:
                        classification = 2
                    elif has_partial_success:
                        classification = 1
                    else:
                        classification = 0

                model_task_data[(model, task)] = classification

        # Sort models by number of full successes (descending)
        model_scores = {}
        for model in models:
            full_successes = sum(
                1 for task in tasks if model_task_data.get((model, task), 0) == 2
            )
            model_scores[model] = full_successes

        models = sorted(models, key=lambda m: model_scores[m], reverse=True)

        # Sort tasks by weighted score (full success = 2 points, partial = 1 point), descending
        task_scores = {}
        for task in tasks:
            score = sum(model_task_data.get((model, task), 0) for model in models)
            task_scores[task] = score

        tasks = sorted(tasks, key=lambda t: task_scores[t], reverse=True)

        # Now create the heatmap data with sorted order
        heatmap_data = np.zeros((len(models), len(tasks)))

        for i, model in enumerate(models):
            for j, task in enumerate(tasks):
                heatmap_data[i, j] = model_task_data.get((model, task), 0)

        # Create custom colormap: Red -> Yellow -> Green
        from matplotlib.colors import ListedColormap

        colors = ["#d62728", "#ffcc00", "#2ca02c"]  # Red, Yellow, Green
        custom_cmap = ListedColormap(colors)

        # Create heatmap
        fig, ax = plt.subplots(
            figsize=(max(10, len(tasks) * 0.8), max(6, len(models) * 0.5)), dpi=self.dpi
        )

        # Create annotations for the heatmap
        annotations = np.empty((len(models), len(tasks)), dtype=object)
        for i in range(len(models)):
            for j in range(len(tasks)):
                value = heatmap_data[i, j]
                if value == 2:
                    annotations[i, j] = "✓"  # Full success
                elif value == 1:
                    annotations[i, j] = "~"  # Partial success
                else:
                    annotations[i, j] = "✗"  # No success

        sns.heatmap(
            heatmap_data,
            xticklabels=tasks,
            yticklabels=models,
            annot=annotations,
            fmt="",
            cmap=custom_cmap,
            vmin=0,
            vmax=2,
            cbar_kws={"ticks": [0, 1, 2], "label": "Success Level"},
            ax=ax,
        )

        # Customize colorbar labels
        colorbar = ax.collections[0].colorbar
        colorbar.set_ticklabels(["No Success", "Partial Success", "Full Success"])

        ax.set_title(
            title or "Task Success Classification by Model", fontsize=14, pad=20
        )
        ax.set_xlabel("Tasks", fontsize=12)
        ax.set_ylabel("Models", fontsize=12)

        # Rotate x-axis labels for better readability
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        return fig

    def plot_pass_histogram(
        self,
        results_df: pd.DataFrame,
        model_col: str = "model",
        task_col: str = "task",
        reward_col: str = "max_reward",
        success_threshold: float = 0.0,
        max_k: int = 10,
        title: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Optional[plt.Figure]:
        """Create histogram showing number of passes out of k attempts per task per model

        Args:
            results_df: DataFrame with trajectory results
            model_col: Column with model names
            task_col: Column with task names
            reward_col: Column with performance metric
            success_threshold: Threshold for success
            max_k: Maximum number of attempts to consider
            title: Optional plot title
            save_path: Optional path to save figure

        Returns:
            matplotlib Figure object if plotting available
        """
        if not self.enabled:
            return None

        # Calculate pass counts per model-task combination
        pass_data = []

        for model in results_df[model_col].unique():
            model_data = results_df[results_df[model_col] == model]

            for task in model_data[task_col].unique():
                task_data = model_data[model_data[task_col] == task]

                # Count successes out of total attempts
                successes = (task_data[reward_col] > success_threshold).sum()
                total_attempts = len(task_data)

                # Limit to max_k for visualization
                k = min(total_attempts, max_k)
                success_count = min(successes, k)

                pass_data.append(
                    {
                        "model": model,
                        "task": task,
                        "passes": success_count,
                        "attempts": k,
                        "task_model": f"{task}\n({model})",
                    }
                )

        pass_df = pd.DataFrame(pass_data)

        if pass_df.empty:
            print("No data available for pass histogram")
            return None

        # Create histogram
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        # Group data for plotting
        x_positions = []
        labels = []

        models = sorted(pass_df["model"].unique())
        tasks = sorted(pass_df["task"].unique())

        x_pos = 0
        for task in tasks:
            task_data = pass_df[pass_df["task"] == task]
            for i, model in enumerate(models):
                model_task_data = task_data[task_data["model"] == model]
                if not model_task_data.empty:
                    passes = model_task_data["passes"].iloc[0]
                    attempts = model_task_data["attempts"].iloc[0]

                    # Create histogram bar
                    height = passes
                    ax.bar(
                        x_pos,
                        height,
                        width=0.8,
                        color=sns.color_palette("husl", len(models))[i],
                        alpha=0.7,
                        label=model if task == tasks[0] else "",
                    )

                    # Add text showing passes/attempts
                    ax.text(
                        x_pos,
                        height + 0.1,
                        f"{passes}/{attempts}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )

                    x_positions.append(x_pos)
                    labels.append(f"{task}\n({model})")
                    x_pos += 1

            # Add spacing between tasks
            x_pos += 0.5

        # Customize plot
        ax.set_xlabel("Task (Model)")
        ax.set_ylabel("Number of Successes")
        ax.set_title(title or "Success Count per Task per Model")
        ax.set_xticks(x_positions)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.legend()
        ax.grid(True, alpha=0.3, axis="y")

        # Set y-axis to show integer values
        ax.set_ylim(0, max_k)

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        return fig

    def plot_task_specific_pass_at_k(
        self,
        results_df: pd.DataFrame,
        model_col: str = "model",
        task_col: str = "task",
        reward_col: str = "max_reward",
        success_threshold: float = 0.0,
        k_values: Optional[List[int]] = None,
        title: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Optional[plt.Figure]:
        """Plot Pass@K curves broken down by task

        Args:
            results_df: DataFrame with trajectory results
            model_col: Column with model names
            task_col: Column with task names
            reward_col: Column with performance metric
            success_threshold: Threshold for success
            k_values: List of k values to plot
            title: Optional plot title
            save_path: Optional path to save figure

        Returns:
            matplotlib Figure object if plotting available
        """
        if not self.enabled:
            return None

        from .performance_metrics import PerformanceAnalyzer

        k_values = k_values or [1, 2, 3, 5, 8]
        tasks = sorted(results_df[task_col].unique())
        models = sorted(results_df[model_col].unique())

        # Create subplots for each task
        n_tasks = len(tasks)
        n_cols = min(3, n_tasks)
        n_rows = (n_tasks + n_cols - 1) // n_cols

        fig, axes = plt.subplots(
            n_rows, n_cols, figsize=(n_cols * 4, n_rows * 3), dpi=self.dpi
        )
        if n_tasks == 1:
            axes = [axes]
        elif n_rows == 1:
            axes = axes.reshape(1, -1)
        axes = axes.flatten()

        for i, task in enumerate(tasks):
            ax = axes[i]
            task_data = results_df[results_df[task_col] == task]

            for model in models:
                model_task_data = task_data[task_data[model_col] == model]

                if len(model_task_data) >= 2:
                    # Calculate Pass@K for this model-task combination
                    successes = (model_task_data[reward_col] > success_threshold).values

                    pass_at_k_values = []
                    valid_k_values = []

                    for k in k_values:
                        if k <= len(successes):
                            pass_k = PerformanceAnalyzer.calculate_pass_at_k(
                                successes, k
                            )
                            pass_at_k_values.append(pass_k)
                            valid_k_values.append(k)

                    if valid_k_values:
                        ax.plot(
                            valid_k_values,
                            pass_at_k_values,
                            marker="o",
                            label=model,
                            linewidth=2,
                        )

            ax.set_title(f"Task: {task}")
            ax.set_xlabel("k (attempts)")
            ax.set_ylabel("Pass@k")
            ax.set_ylim(0, 1)
            ax.grid(True, alpha=0.3)
            ax.legend()

        # Hide unused subplots
        for i in range(n_tasks, len(axes)):
            axes[i].set_visible(False)

        fig.suptitle(title or "Pass@K by Task", fontsize=14)
        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        return fig

    def create_comprehensive_report(
        self,
        model_metrics: Dict[str, PerformanceMetrics],
        results_df: pd.DataFrame,
        output_dir: str,
        report_name: str = "evaluation_report",
    ) -> Dict[str, str]:
        """Create comprehensive visual report

        Args:
            model_metrics: Dictionary of model performance metrics
            results_df: DataFrame with detailed results
            output_dir: Directory to save plots
            report_name: Base name for report files

        Returns:
            Dictionary mapping plot types to saved file paths
        """
        if not self.enabled:
            print("Plotting not available - cannot create visual report")
            return {}

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_files = {}

        # Extract task information if available
        task_col = None
        if "version_description" in results_df.columns:
            # Extract task from version_description if not already present
            if "task" not in results_df.columns:
                results_df = results_df.copy()
                results_df["task"] = results_df["version_description"].str.extract(
                    r"type:([^\n]+)"
                )
            task_col = "task"

        # 1. Pass histogram instead of model comparison
        try:
            if task_col and task_col in results_df.columns:
                fig = self.plot_pass_histogram(
                    results_df,
                    reward_col="final_reward",
                    title="Success Count per Task per Model",
                )
                if fig:
                    file_path = output_path / f"{report_name}_pass_histogram.png"
                    fig.savefig(file_path, bbox_inches="tight", dpi=self.dpi)
                    plt.close(fig)
                    saved_files["pass_histogram"] = str(file_path)
        except Exception as e:
            print(f"Error creating pass histogram: {e}")

        # 1b. Fallback model comparison if no task data
        if "pass_histogram" not in saved_files:
            try:
                fig = self.plot_model_comparison(
                    model_metrics,
                    metric="success_rate",
                    title="Model Performance Comparison",
                )
                if fig:
                    file_path = output_path / f"{report_name}_model_comparison.png"
                    fig.savefig(file_path, bbox_inches="tight", dpi=self.dpi)
                    plt.close(fig)
                    saved_files["model_comparison"] = str(file_path)
            except Exception as e:
                print(f"Error creating model comparison plot: {e}")

        # 2. Task-specific Pass@k curves
        try:
            if task_col and task_col in results_df.columns:
                fig = self.plot_task_specific_pass_at_k(
                    results_df,
                    reward_col="final_reward",
                    title="Pass@K Analysis by Task",
                )
                if fig:
                    file_path = output_path / f"{report_name}_task_pass_at_k.png"
                    fig.savefig(file_path, bbox_inches="tight", dpi=self.dpi)
                    plt.close(fig)
                    saved_files["task_pass_at_k"] = str(file_path)
        except Exception as e:
            print(f"Error creating task-specific pass@k plot: {e}")

        # 2b. Fallback overall Pass@k if no task data
        if "task_pass_at_k" not in saved_files:
            try:
                fig = self.plot_pass_at_k(
                    model_metrics, title="Pass@k Performance Curves"
                )
                if fig:
                    file_path = output_path / f"{report_name}_pass_at_k.png"
                    fig.savefig(file_path, bbox_inches="tight", dpi=self.dpi)
                    plt.close(fig)
                    saved_files["pass_at_k"] = str(file_path)
            except Exception as e:
                print(f"Error creating pass@k plot: {e}")

        # 3. Reward distributions
        try:
            if "final_reward" in results_df.columns:
                fig = self.plot_reward_distribution(
                    results_df, title="Reward Distribution by Model"
                )
                if fig:
                    file_path = output_path / f"{report_name}_reward_distribution.png"
                    fig.savefig(file_path, bbox_inches="tight", dpi=self.dpi)
                    plt.close(fig)
                    saved_files["reward_distribution"] = str(file_path)
        except Exception as e:
            print(f"Error creating reward distribution plot: {e}")

        # 4. Efficiency scatter plot
        try:
            if (
                "total_tokens" in results_df.columns
                and "final_reward" in results_df.columns
            ):
                fig = self.plot_efficiency_scatter(
                    results_df, title="Efficiency: Reward vs Token Usage"
                )
                if fig:
                    file_path = output_path / f"{report_name}_efficiency_scatter.png"
                    fig.savefig(file_path, bbox_inches="tight", dpi=self.dpi)
                    plt.close(fig)
                    saved_files["efficiency_scatter"] = str(file_path)
        except Exception as e:
            print(f"Error creating efficiency scatter plot: {e}")

        # 5. Task difficulty heatmap
        try:
            if "version_description" in results_df.columns:
                fig = self.plot_task_difficulty_heatmap(
                    results_df, title="Task Difficulty Heatmap"
                )
                if fig:
                    file_path = output_path / f"{report_name}_task_heatmap.png"
                    fig.savefig(file_path, bbox_inches="tight", dpi=self.dpi)
                    plt.close(fig)
                    saved_files["task_heatmap"] = str(file_path)
        except Exception as e:
            print(f"Error creating task heatmap: {e}")

        # 5a. Task success classification heatmap
        try:
            if "version_description" in results_df.columns:
                fig = self.plot_task_success_classification_heatmap(
                    results_df, title="Task Success Classification by Model"
                )
                if fig:
                    file_path = (
                        output_path / f"{report_name}_task_classification_heatmap.png"
                    )
                    fig.savefig(file_path, bbox_inches="tight", dpi=self.dpi)
                    plt.close(fig)
                    saved_files["task_classification_heatmap"] = str(file_path)
        except Exception as e:
            print(f"Error creating task classification heatmap: {e}")

        # 6. Learning curves over time
        try:
            if "created_at" in results_df.columns:
                fig = self.plot_learning_curves(
                    results_df, title="Performance Over Time"
                )
                if fig:
                    file_path = output_path / f"{report_name}_learning_curves.png"
                    fig.savefig(file_path, bbox_inches="tight", dpi=self.dpi)
                    plt.close(fig)
                    saved_files["learning_curves"] = str(file_path)
        except Exception as e:
            print(f"Error creating learning curves: {e}")

        print(f"Visual report saved to: {output_path}")
        print(f"Generated {len(saved_files)} plots")

        return saved_files
