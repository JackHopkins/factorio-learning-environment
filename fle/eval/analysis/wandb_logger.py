"""
WandB integration for real-time experiment tracking and visualization.
"""

from typing import Dict, Any, List, Optional
import os

try:
    import wandb

    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False

from .performance_metrics import PerformanceMetrics


class WandBLogger:
    """Handles WandB logging for real-time experiment tracking"""

    def __init__(
        self,
        project: str = "factorio-learning-environment",
        entity: Optional[str] = None,
        run_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        resume: bool = False,
        offline: bool = False,
    ):
        """Initialize WandB logger

        Args:
            project: WandB project name
            entity: WandB entity (team/user)
            run_name: Optional run name
            tags: List of tags for the run
            config: Configuration dictionary to log
            resume: Whether to resume existing run
            offline: Whether to run in offline mode
        """
        self.project = project
        self.entity = entity
        self.run_name = run_name
        self.tags = tags or []
        self.config = config or {}
        self.resume = resume
        self.offline = offline
        self.run = None
        self.enabled = WANDB_AVAILABLE and os.getenv(
            "DISABLE_WANDB", ""
        ).lower() not in ["true", "1"]

        if self.enabled:
            self.initialize_run()
        else:
            print("WandB logging disabled (not installed or DISABLE_WANDB=true)")

    def initialize_run(self):
        """Initialize WandB run"""
        if not self.enabled:
            return

        try:
            wandb_mode = "offline" if self.offline else "online"

            self.run = wandb.init(
                project=self.project,
                entity=self.entity,
                name=self.run_name,
                tags=self.tags,
                config=self.config,
                resume=self.resume,
                mode=wandb_mode,
            )

            print(f"WandB run initialized: {self.run.name}")

        except Exception as e:
            print(f"Failed to initialize WandB: {e}")
            self.enabled = False

    def log_metrics(
        self,
        metrics: Dict[str, Any],
        step: Optional[int] = None,
        prefix: Optional[str] = None,
    ):
        """Log metrics to WandB

        Args:
            metrics: Dictionary of metrics to log
            step: Optional step number
            prefix: Optional prefix for metric names
        """
        if not self.enabled or not self.run:
            return

        try:
            # Add prefix to metric names if provided
            if prefix:
                metrics = {f"{prefix}/{k}": v for k, v in metrics.items()}

            self.run.log(metrics, step=step)

        except Exception as e:
            print(f"Failed to log metrics to WandB: {e}")

    def log_performance_metrics(
        self,
        performance_metrics: PerformanceMetrics,
        model: str,
        task: str,
        step: Optional[int] = None,
    ):
        """Log PerformanceMetrics object to WandB

        Args:
            performance_metrics: PerformanceMetrics to log
            model: Model name for grouping
            task: Task name for grouping
            step: Optional step number
        """
        if not self.enabled:
            return

        metrics_dict = performance_metrics.to_dict()

        # Add model and task info
        metrics_dict["model"] = model
        metrics_dict["task"] = task

        # Create hierarchical logging structure
        formatted_metrics = {}

        # Basic performance metrics
        for metric in ["success_rate", "mean_reward", "pass_at_1"]:
            if metric in metrics_dict:
                formatted_metrics[f"performance/{metric}"] = metrics_dict[metric]
                formatted_metrics[f"by_model/{model}/{metric}"] = metrics_dict[metric]
                formatted_metrics[f"by_task/{task}/{metric}"] = metrics_dict[metric]

        # Pass@k metrics
        if "pass_at_k" in metrics_dict and metrics_dict["pass_at_k"]:
            for k, value in metrics_dict["pass_at_k"].items():
                formatted_metrics[f"pass_at_k/pass_at_{k}"] = value
                formatted_metrics[f"by_model/{model}/pass_at_{k}"] = value

        # Efficiency metrics
        for metric in ["mean_tokens", "tokens_per_success", "mean_steps"]:
            if metric in metrics_dict and metrics_dict[metric] is not None:
                formatted_metrics[f"efficiency/{metric}"] = metrics_dict[metric]

        # Statistical metrics
        for metric in ["num_trajectories", "std_reward"]:
            if metric in metrics_dict:
                formatted_metrics[f"stats/{metric}"] = metrics_dict[metric]

        # Confidence intervals
        if "ci_95_lower" in metrics_dict:
            formatted_metrics["stats/success_rate_ci_95_lower"] = metrics_dict[
                "ci_95_lower"
            ]
            formatted_metrics["stats/success_rate_ci_95_upper"] = metrics_dict[
                "ci_95_upper"
            ]

        self.log_metrics(formatted_metrics, step=step)

    def log_trajectory_progress(
        self,
        version: int,
        instance: int,
        step: int,
        reward: float,
        model: str,
        task: str,
        elapsed_time: Optional[float] = None,
        tokens_used: Optional[int] = None,
    ):
        """Log progress during trajectory execution

        Args:
            version: Version/experiment ID
            instance: Instance/trial number
            step: Current step in trajectory
            reward: Current reward value
            model: Model name
            task: Task name
            elapsed_time: Elapsed time in seconds
            tokens_used: Number of tokens used so far
        """
        if not self.enabled:
            return

        metrics = {
            "trajectory/version": version,
            "trajectory/instance": instance,
            "trajectory/step": step,
            "trajectory/reward": reward,
            "trajectory/model": model,
            "trajectory/task": task,
        }

        if elapsed_time is not None:
            metrics["trajectory/elapsed_time"] = elapsed_time

        if tokens_used is not None:
            metrics["trajectory/tokens_used"] = tokens_used
            metrics["trajectory/tokens_per_step"] = tokens_used / max(step, 1)

        # Use actual step number for readable x-axis
        # Each WandB run corresponds to one trajectory, so step conflicts aren't an issue
        self.log_metrics(metrics, step=step)

    def log_sweep_summary(
        self,
        sweep_config: Dict[str, Any],
        results_by_model: Dict[str, PerformanceMetrics],
        results_by_task: Dict[str, PerformanceMetrics],
        total_trajectories: int,
        total_time: float,
    ):
        """Log summary of a completed sweep

        Args:
            sweep_config: Configuration used for the sweep
            results_by_model: Performance results grouped by model
            results_by_task: Performance results grouped by task
            total_trajectories: Total number of trajectories run
            total_time: Total time in seconds
        """
        if not self.enabled:
            return

        # Log sweep metadata
        sweep_metrics = {
            "sweep/total_trajectories": total_trajectories,
            "sweep/total_time_hours": total_time / 3600,
            "sweep/num_models": len(results_by_model),
            "sweep/num_tasks": len(results_by_task),
            "sweep/avg_time_per_trajectory": total_time / max(total_trajectories, 1),
        }

        # Log best performing model overall
        if results_by_model:
            best_model = max(
                results_by_model.keys(), key=lambda m: results_by_model[m].success_rate
            )
            sweep_metrics["sweep/best_model"] = best_model
            sweep_metrics["sweep/best_model_success_rate"] = results_by_model[
                best_model
            ].success_rate

        # Log hardest task (lowest success rate)
        if results_by_task:
            hardest_task = min(
                results_by_task.keys(), key=lambda t: results_by_task[t].success_rate
            )
            sweep_metrics["sweep/hardest_task"] = hardest_task
            sweep_metrics["sweep/hardest_task_success_rate"] = results_by_task[
                hardest_task
            ].success_rate

        self.log_metrics(sweep_metrics)

        # Log sweep configuration
        if sweep_config:
            self.log_config_update({"sweep_config": sweep_config})

    def log_config_update(self, config: Dict[str, Any]):
        """Update run configuration

        Args:
            config: Configuration dictionary to add/update
        """
        if not self.enabled or not self.run:
            return

        try:
            self.run.config.update(config)
        except Exception as e:
            print(f"Failed to update WandB config: {e}")

    def log_table(
        self, table_name: str, data: List[Dict[str, Any]], step: Optional[int] = None
    ):
        """Log a data table to WandB

        Args:
            table_name: Name of the table
            data: List of dictionaries representing table rows
            step: Optional step number
        """
        if not self.enabled or not self.run:
            return

        try:
            # Convert to WandB table format
            if data:
                columns = list(data[0].keys())
                table_data = [[row[col] for col in columns] for row in data]
                table = wandb.Table(columns=columns, data=table_data)
                self.log_metrics({table_name: table}, step=step)

        except Exception as e:
            print(f"Failed to log table to WandB: {e}")

    def log_model_comparison_table(
        self, model_metrics: Dict[str, PerformanceMetrics], step: Optional[int] = None
    ):
        """Log model comparison as a table

        Args:
            model_metrics: Dictionary mapping model names to PerformanceMetrics
            step: Optional step number
        """
        if not model_metrics:
            return

        table_data = []
        for model_name, metrics in model_metrics.items():
            row = {"model": model_name}
            row.update(metrics.to_dict())
            table_data.append(row)

        self.log_table("model_comparison", table_data, step=step)

    def finish(self):
        """Finish the WandB run"""
        if self.enabled and self.run:
            try:
                self.run.finish()
                print("WandB run finished successfully")
            except Exception as e:
                print(f"Error finishing WandB run: {e}")


class WandBSweepLogger:
    """Special logger for managing WandB across multiple sweep runs"""

    def __init__(self, project: str = "factorio-learning-environment"):
        self.project = project
        self.enabled = WANDB_AVAILABLE
        self.individual_loggers: Dict[str, WandBLogger] = {}

    def create_run_logger(
        self, run_id: str, model: str, task: str, version: int, **kwargs
    ) -> WandBLogger:
        """Create a logger for an individual run in the sweep

        Args:
            run_id: Unique identifier for this run
            model: Model name
            task: Task name
            version: Version number
            **kwargs: Additional arguments for WandBLogger

        Returns:
            WandBLogger instance for this run
        """
        run_name = f"{model}-{task}-v{version}"
        tags = ["sweep", model, task, f"v{version}"]

        config = {
            "model": model,
            "task": task,
            "version": version,
            **kwargs.get("config", {}),
        }

        logger = WandBLogger(
            project=self.project,
            run_name=run_name,
            tags=tags,
            config=config,
            **{k: v for k, v in kwargs.items() if k != "config"},
        )

        self.individual_loggers[run_id] = logger
        return logger

    def get_logger(self, run_id: str) -> Optional[WandBLogger]:
        """Get logger for a specific run"""
        return self.individual_loggers.get(run_id)

    def finish_all(self):
        """Finish all individual run loggers"""
        for logger in self.individual_loggers.values():
            logger.finish()
        self.individual_loggers.clear()
