"""Inspect AI Hook for logging FLE evaluation metrics to Weights & Biases.

Auto-discovered via setuptools entry points. Fires on on_task_end to extract
all scorer metrics from the EvalLog and log them to WandB.
"""

import logging
import os
from typing import Any, Dict

from inspect_ai.hooks import Hooks, hooks, TaskEnd, SampleEnd

logger = logging.getLogger(__name__)


@hooks(name="fle_wandb_hook", description="Logs FLE eval metrics to WandB")
class FLEWandBHook(Hooks):
    """Hook that logs FLE evaluation metrics to Weights & Biases after each task."""

    def enabled(self) -> bool:
        """Returns True only when wandb is importable and configured."""
        try:
            import wandb  # noqa: F401
        except ImportError:
            return False

        return bool(
            os.environ.get("WANDB_API_KEY")
            or os.environ.get("ENABLE_WANDB", "").lower() in ("true", "1")
        )

    async def on_task_end(self, data: TaskEnd) -> None:
        """Log aggregate results and per-sample metrics to WandB."""
        try:
            import wandb
        except ImportError:
            logger.warning("wandb not installed, skipping WandB logging")
            return

        log = data.log

        # Extract config from eval metadata
        config = self._extract_config(log)
        tags = self._build_tags(log, config)

        project = os.environ.get("WANDB_PROJECT", "fle-inspect-eval")
        entity = os.environ.get("WANDB_ENTITY", None)

        run = wandb.init(
            project=project,
            entity=entity,
            config=config,
            tags=tags,
            reinit=True,
        )

        if run is None:
            logger.error("wandb.init() returned None, skipping logging")
            return

        try:
            # 1. Log aggregate results from scorers
            self._log_aggregate_results(run, log)

            # 2. Log per-sample score metadata
            self._log_sample_metrics(run, log)

            # 3. Log trajectory time-series from milestone_scores
            self._log_trajectory_timeseries(run, log)

            # 4. Log token usage
            self._log_token_usage(run, log)

            logger.info(f"WandB run logged: {run.url}")
        except Exception as e:
            logger.error(f"Error logging to WandB: {e}")
        finally:
            run.finish()

    async def on_sample_end(self, data: SampleEnd) -> None:
        """Reserved for future per-sample logging (no-op)."""
        pass

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _extract_config(self, log) -> Dict[str, Any]:
        """Extract run config from EvalLog."""
        config: Dict[str, Any] = {}

        if log.eval:
            config["model"] = getattr(log.eval, "model", "unknown")
            config["task"] = getattr(log.eval, "task", "unknown")
            config["task_id"] = getattr(log.eval, "task_id", "")

            # Extract task args if available
            task_args = getattr(log.eval, "task_args", {}) or {}
            config.update({f"task_arg/{k}": v for k, v in task_args.items()})

        # Extract from first sample metadata
        if log.samples:
            sample_meta = getattr(log.samples[0], "metadata", {}) or {}
            config["env_id"] = sample_meta.get("env_id", "unknown")
            config["trajectory_length"] = sample_meta.get("trajectory_length", 0)
            config["task_type"] = sample_meta.get("task_type", "unknown")

        # Extract solver info
        config["solver"] = os.environ.get("FLE_SOLVER", "default")

        return config

    def _build_tags(self, log, config: Dict[str, Any]) -> list:
        """Build WandB tags list."""
        tags = ["inspect-eval"]

        task_name = config.get("task", "")
        if task_name:
            tags.append(str(task_name))

        model = config.get("model", "")
        if model:
            # Shorten model name: "openai/gpt-4o-mini" -> "gpt-4o-mini"
            short_model = str(model).split("/")[-1] if "/" in str(model) else str(model)
            tags.append(short_model)

        task_type = config.get("task_type", "")
        if task_type:
            tags.append(str(task_type))

        return tags

    def _log_aggregate_results(self, run, log) -> None:
        """Log aggregate scorer results to WandB summary."""
        if not log.results or not log.results.scores:
            return

        for score_entry in log.results.scores:
            scorer_name = getattr(score_entry, "name", "unknown")
            metrics = getattr(score_entry, "metrics", {}) or {}

            for metric_name, metric_val in metrics.items():
                # metric_val could be a Metric object or a raw value
                value = getattr(metric_val, "value", metric_val)
                if value is not None and isinstance(value, (int, float)):
                    run.summary[f"results/{scorer_name}/{metric_name}"] = value

    def _log_sample_metrics(self, run, log) -> None:
        """Log per-sample score metadata to WandB summary.

        For single-sample runs, logs directly. For multi-sample runs,
        logs the first sample's metrics (aggregate results cover the rest).
        """
        if not log.samples:
            return

        sample = log.samples[0]
        scores = getattr(sample, "scores", {}) or {}

        # Map of scorer_name -> metadata_key -> wandb_key
        metric_mappings = {
            "production_score": {
                "production_score": "sample/production_score",
                "score_per_step": "sample/score_per_step",
                "total_growth": "sample/total_growth",
                "total_steps": "sample/total_steps",
            },
            "automated_production_score": {
                "automated_production_score": "sample/automated_production_score",
                "automation_ratio": "sample/automation_ratio",
            },
            "achievements": {
                "num_unique_items": "sample/achievements/num_unique_items",
            },
            "technologies": {
                "num_researched_technologies": "sample/technologies/num_researched",
            },
            "code": {
                "avg_cyclomatic_complexity": "sample/code/avg_complexity",
                "num_programs": "sample/code/num_programs",
                "total_code_lines": "sample/code/total_code_lines",
            },
            "latency_scorer": {
                "avg_total_step_latency": "sample/latency/avg_step",
                "avg_inference_latency": "sample/latency/avg_inference",
                "total_wall_clock_time": "sample/latency/total_wall_clock",
            },
        }

        for scorer_name, mappings in metric_mappings.items():
            score_obj = scores.get(scorer_name)
            if score_obj is None:
                continue
            metadata = getattr(score_obj, "metadata", {}) or {}
            for meta_key, wandb_key in mappings.items():
                value = metadata.get(meta_key)
                if value is not None and isinstance(value, (int, float)):
                    run.summary[wandb_key] = value

    def _log_trajectory_timeseries(self, run, log) -> None:
        """Log trajectory milestone scores as WandB time-series for line charts."""
        if not log.samples:
            return

        sample = log.samples[0]
        scores = getattr(sample, "scores", {}) or {}

        # Log production_score milestone trajectory
        prod_score = scores.get("production_score")
        if prod_score:
            metadata = getattr(prod_score, "metadata", {}) or {}
            milestone_scores = metadata.get("milestone_scores")
            if milestone_scores and isinstance(milestone_scores, list):
                for i, val in enumerate(milestone_scores):
                    if isinstance(val, (int, float)):
                        run.log(
                            {"trajectory/production_score": val},
                            step=i,
                        )

        # Log automated_production_score milestone trajectory
        auto_score = scores.get("automated_production_score")
        if auto_score:
            metadata = getattr(auto_score, "metadata", {}) or {}
            milestone_scores = metadata.get("milestone_scores")
            if milestone_scores and isinstance(milestone_scores, list):
                for i, val in enumerate(milestone_scores):
                    if isinstance(val, (int, float)):
                        run.log(
                            {"trajectory/automated_production_score": val},
                            step=i,
                        )

    def _log_token_usage(self, run, log) -> None:
        """Log token usage from model stats."""
        if not log.stats or not log.stats.model_usage:
            return

        for model_name, usage in log.stats.model_usage.items():
            prefix = f"tokens/{model_name}"
            input_tokens = getattr(usage, "input_tokens", 0) or 0
            output_tokens = getattr(usage, "output_tokens", 0) or 0
            total_tokens = getattr(usage, "total_tokens", 0) or (
                input_tokens + output_tokens
            )

            run.summary[f"{prefix}/input_tokens"] = input_tokens
            run.summary[f"{prefix}/output_tokens"] = output_tokens
            run.summary[f"{prefix}/total_tokens"] = total_tokens
