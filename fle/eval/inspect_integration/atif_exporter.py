"""ATIF (Agent Trajectory Interchange Format) exporter for FLE trajectories.

This module converts FLE's TrajectoryData (stored in Inspect's store system)
to ATIF format for use with vendor-eval-kit.

ATIF format specification:
- session_id: Unique identifier for the trajectory
- steps: List of step objects with actions, observations, and metadata
- final_metrics: Aggregate statistics for the entire trajectory
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from inspect_ai.log import EvalLog

from fle.eval.inspect_integration.solver_utils import TrajectoryData

logger = logging.getLogger(__name__)


def calculate_timestamp(
    eval_log: EvalLog,
    step_idx: int,
    trajectory_data: TrajectoryData,
) -> str:
    """Calculate ISO8601 timestamp for a trajectory step.

    Args:
        eval_log: Inspect evaluation log
        step_idx: Index of the step
        trajectory_data: Trajectory data with latency information

    Returns:
        ISO8601 timestamp string
    """
    # Start from eval creation time
    base_time = datetime.fromtimestamp(eval_log.eval.created, timezone.utc)

    # Add cumulative latency up to this step
    if step_idx < len(trajectory_data.total_step_latencies):
        cumulative_seconds = sum(trajectory_data.total_step_latencies[: step_idx + 1])
        step_time = base_time + timedelta(seconds=cumulative_seconds)
    else:
        # Fallback if latency data incomplete
        step_time = base_time + timedelta(
            seconds=step_idx * 10
        )  # Estimate 10s per step

    return step_time.isoformat()


def sum_tokens_from_trajectory(eval_log: EvalLog, token_type: str) -> int:
    """Sum token usage from eval log.

    Args:
        eval_log: Inspect evaluation log
        token_type: "prompt", "completion", or "cached"

    Returns:
        Total token count
    """
    # TODO: Implement actual token extraction from Inspect log structure
    # This will depend on how Inspect stores usage statistics
    return 0


def calculate_cost_from_trajectory(eval_log: EvalLog) -> float:
    """Calculate total cost in USD from trajectory.

    Args:
        eval_log: Inspect evaluation log

    Returns:
        Total cost in USD
    """
    # TODO: Implement cost calculation based on token usage and model pricing
    return 0.0


def export_trajectory_to_atif(
    eval_log: EvalLog,
    sample_idx: int = 0,
) -> Optional[dict[str, Any]]:
    """Convert FLE TrajectoryData to ATIF format.

    Args:
        eval_log: Inspect evaluation log
        sample_idx: Index of sample to export

    Returns:
        ATIF-formatted trajectory dictionary, or None if no trajectory data
    """
    try:
        # Get sample
        if sample_idx >= len(eval_log.samples):
            logger.error(
                f"Sample index {sample_idx} out of range (total: {len(eval_log.samples)})"
            )
            return None

        sample = eval_log.samples[sample_idx]

        # Check if trajectory data is in sample metadata
        if not hasattr(sample, "metadata") or not sample.metadata:
            logger.warning("No metadata found in sample")
            return None

        trajectory_meta = sample.metadata.get("trajectory_data")
        if not trajectory_meta:
            logger.warning("No trajectory_data found in sample metadata")
            return None

        # Deserialize trajectory data
        trajectory_data = deserialize_trajectory_from_metadata(sample.metadata)

        # Convert to ATIF format
        return export_trajectory_to_atif_from_data(
            trajectory_data, eval_log, sample_idx
        )

    except Exception as e:
        logger.error(f"Failed to export trajectory to ATIF: {e}")
        import traceback

        logger.debug(traceback.format_exc())
        return None


def export_trajectory_to_atif_from_data(
    trajectory_data: TrajectoryData,
    eval_log: EvalLog,
    sample_idx: int = 0,
) -> dict[str, Any]:
    """Convert FLE TrajectoryData to ATIF format (when data is directly available).

    This is the main conversion function that will be used when we have
    direct access to TrajectoryData (e.g., during execution or from metadata).

    Args:
        trajectory_data: FLE trajectory data
        eval_log: Inspect evaluation log
        sample_idx: Index of sample

    Returns:
        ATIF-formatted trajectory dictionary
    """
    steps = []

    # Convert each step
    num_steps = len(trajectory_data.steps)
    for i in range(num_steps):
        step_data = trajectory_data.steps[i]

        # Extract data for this step
        program_code = (
            trajectory_data.program_codes[i]
            if i < len(trajectory_data.program_codes)
            else ""
        )
        production_score = (
            trajectory_data.scores[i] if i < len(trajectory_data.scores) else 0.0
        )
        automated_score = (
            trajectory_data.automated_scores[i]
            if i < len(trajectory_data.automated_scores)
            else 0.0
        )
        tick = trajectory_data.ticks[i] if i < len(trajectory_data.ticks) else 0
        inference_latency = (
            trajectory_data.inference_latencies[i]
            if i < len(trajectory_data.inference_latencies)
            else 0.0
        )
        env_latency = (
            trajectory_data.env_execution_latencies[i]
            if i < len(trajectory_data.env_execution_latencies)
            else 0.0
        )

        step_obj = {
            "step_id": i,
            "timestamp": calculate_timestamp(eval_log, i, trajectory_data),
            "action": {
                "type": "code_execution",
                "content": program_code,
            },
            "observation": {
                "type": "game_state",
                "content": {
                    "production_score": production_score,
                    "automated_score": automated_score,
                    "tick": tick,
                    "step_result": step_data,  # Full step data
                },
            },
            "metadata": {
                "inference_latency_ms": inference_latency * 1000,  # Convert to ms
                "env_execution_latency_ms": env_latency * 1000,
                "production_score": production_score,
                "automated_production_score": automated_score,
            },
        }
        steps.append(step_obj)

    # Build final metrics
    final_metrics = {
        "total_steps": trajectory_data.total_steps,
        "total_prompt_tokens": sum_tokens_from_trajectory(eval_log, "prompt"),
        "total_completion_tokens": sum_tokens_from_trajectory(eval_log, "completion"),
        "total_cached_tokens": sum_tokens_from_trajectory(eval_log, "cached"),
        "total_cost_usd": calculate_cost_from_trajectory(eval_log),
        "final_production_score": trajectory_data.final_score,
        "final_automated_score": trajectory_data.final_automated_score,
    }

    return {
        "session_id": eval_log.eval.run_id,
        "steps": steps,
        "final_metrics": final_metrics,
    }


def serialize_trajectory_to_metadata(trajectory_data: TrajectoryData) -> dict[str, Any]:
    """Serialize TrajectoryData to a format suitable for sample metadata.

    This helper function converts TrajectoryData to a plain dict that can be
    stored in sample metadata and later retrieved for ATIF export.

    Args:
        trajectory_data: FLE trajectory data

    Returns:
        Serializable dictionary
    """
    return {
        "production_score": trajectory_data.production_score,
        "automated_production_score": trajectory_data.automated_production_score,
        "total_steps": trajectory_data.total_steps,
        "current_score": trajectory_data.current_score,
        "final_score": trajectory_data.final_score,
        "final_automated_score": trajectory_data.final_automated_score,
        "scores": trajectory_data.scores,
        "automated_scores": trajectory_data.automated_scores,
        "steps": trajectory_data.steps,
        "error": trajectory_data.error,
        "ticks": trajectory_data.ticks,
        "produced_item_types": trajectory_data.produced_item_types,
        "researched_technologies": trajectory_data.researched_technologies,
        "inference_latencies": trajectory_data.inference_latencies,
        "env_execution_latencies": trajectory_data.env_execution_latencies,
        "policy_execution_latencies": trajectory_data.policy_execution_latencies,
        "sleep_durations": trajectory_data.sleep_durations,
        "total_step_latencies": trajectory_data.total_step_latencies,
        "program_codes": trajectory_data.program_codes,
    }


def deserialize_trajectory_from_metadata(metadata: dict[str, Any]) -> TrajectoryData:
    """Deserialize TrajectoryData from sample metadata.

    Args:
        metadata: Sample metadata containing serialized trajectory

    Returns:
        TrajectoryData instance
    """
    # Extract trajectory data from metadata
    traj_meta = metadata.get("trajectory_data", {})

    # Reconstruct TrajectoryData
    trajectory_data = TrajectoryData(
        production_score=traj_meta.get("production_score", 0.0),
        automated_production_score=traj_meta.get("automated_production_score", 0.0),
        total_steps=traj_meta.get("total_steps", 0),
        current_score=traj_meta.get("current_score", 0.0),
        final_score=traj_meta.get("final_score", 0.0),
        final_automated_score=traj_meta.get("final_automated_score", 0.0),
        scores=traj_meta.get("scores", []),
        automated_scores=traj_meta.get("automated_scores", []),
        steps=traj_meta.get("steps", []),
        error=traj_meta.get("error", ""),
        ticks=traj_meta.get("ticks", []),
        produced_item_types=traj_meta.get("produced_item_types", []),
        researched_technologies=traj_meta.get("researched_technologies", []),
        inference_latencies=traj_meta.get("inference_latencies", []),
        env_execution_latencies=traj_meta.get("env_execution_latencies", []),
        policy_execution_latencies=traj_meta.get("policy_execution_latencies", []),
        sleep_durations=traj_meta.get("sleep_durations", []),
        total_step_latencies=traj_meta.get("total_step_latencies", []),
        program_codes=traj_meta.get("program_codes", []),
    )

    return trajectory_data
