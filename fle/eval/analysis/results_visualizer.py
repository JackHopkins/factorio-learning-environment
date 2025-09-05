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
                    success_rate = (subset[metric_col] > success_threshold).mean()
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

        # 1. Model comparison bar chart
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

        # 2. Pass@k curves
        try:
            fig = self.plot_pass_at_k(model_metrics, title="Pass@k Performance Curves")
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
