"""Vendor-Eval-Kit adapter for FLE Inspect AI results.

This module converts Inspect AI evaluation results into Harbor-compatible
format for use with vendor-eval-kit collection and analysis.

Key functionality:
- Convert Inspect EvalLog to Harbor result.json format
- Extract and map scoring data to reward values (0-1 range)
- Handle token usage and cost tracking
- Support both throughput and unbounded task types
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from inspect_ai.log import EvalLog, read_eval_log

from fle.eval.inspect_integration.atif_exporter import export_trajectory_to_atif

logger = logging.getLogger(__name__)


def convert_score_to_reward(score_data: dict[str, Any]) -> float | None:
    """Convert FLE Score to Harbor reward (0-1 range).

    Args:
        score_data: Score data from Inspect sample (score.value, score.metadata)

    Returns:
        Reward value in [0, 1] range, or None if score cannot be mapped

    Mapping logic:
    - "C" (Correct) → 1.0
    - "I" (Incorrect) → 0.0
    - Numeric value in [0, 1] → pass through (already normalized)
    - throughput_proportion from metadata → use directly
    - Other formats → None (unknown)
    """
    # Get the score value - may be in different formats
    value = score_data.get("value")
    metadata = score_data.get("metadata") or {}

    # Binary correct/incorrect
    if value == "C":
        return 1.0
    elif value == "I":
        return 0.0

    # Throughput proportion from metadata (preferred)
    if "throughput_proportion" in metadata:
        proportion = metadata["throughput_proportion"]
        if isinstance(proportion, (int, float)):
            return float(min(max(proportion, 0.0), 1.0))

    # Direct numeric score (already in 0-1 range for most FLE tasks)
    if isinstance(value, (int, float)):
        return float(min(max(value, 0.0), 1.0))

    # String representation of float
    if isinstance(value, str):
        try:
            numeric_value = float(value)
            return min(max(numeric_value, 0.0), 1.0)
        except (ValueError, TypeError):
            pass

    # Unknown format
    logger.warning(f"Unable to convert score to reward: {score_data}")
    return None


def extract_model_info(eval_log: EvalLog) -> tuple[str, str]:
    """Extract model provider and name from Inspect eval log.

    Args:
        eval_log: Inspect evaluation log

    Returns:
        Tuple of (provider, model_name)
    """
    model_name = eval_log.eval.model

    # Parse provider from model string (e.g., "openai/gpt-4o-mini" → "openai", "gpt-4o-mini")
    if "/" in model_name:
        provider, name = model_name.split("/", 1)
        return provider, name

    # Default to "unknown" provider if no slash
    return "unknown", model_name


def calculate_task_checksum(task_metadata: dict[str, Any]) -> str:
    """Calculate checksum for task configuration.

    Args:
        task_metadata: Task metadata from sample

    Returns:
        SHA256 checksum hex string
    """
    # Create deterministic task config representation
    config_str = json.dumps(task_metadata, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()


def sum_tokens(eval_log: EvalLog, token_type: str) -> int:
    """Sum token usage across all samples in eval log.

    Args:
        eval_log: Inspect evaluation log
        token_type: "input", "output", or "cache"

    Returns:
        Total token count
    """
    total = 0
    for sample in eval_log.samples or []:
        # Check if sample has scores with metadata
        if hasattr(sample, "scores") and sample.scores:
            for score in sample.scores.values():
                if hasattr(score, "metadata") and isinstance(score.metadata, dict):
                    # Token tracking might be in score metadata
                    pass

        # Check sample's own metadata
        if hasattr(sample, "metadata") and isinstance(sample.metadata, dict):
            # Look for token counts in metadata
            pass

    # For now, return 0 - actual implementation will depend on where
    # Inspect stores token usage in the log structure
    # TODO: Implement proper token extraction from Inspect logs
    return total


def calculate_total_cost(eval_log: EvalLog) -> float:
    """Calculate total USD cost from eval log.

    Args:
        eval_log: Inspect evaluation log

    Returns:
        Total cost in USD
    """
    # TODO: Implement cost calculation based on token usage and model pricing
    return 0.0


def build_result_json(
    eval_log: EvalLog,
    sample_idx: int = 0,
    attempt: int = 0,
) -> dict[str, Any]:
    """Build Harbor-compatible result.json from Inspect eval log.

    Args:
        eval_log: Inspect evaluation log
        sample_idx: Index of sample in eval log (for multi-sample tasks)
        attempt: Attempt number (for multi-epoch runs)

    Returns:
        Dictionary conforming to Harbor result.json format
    """
    sample = eval_log.samples[sample_idx]
    metadata = sample.metadata if hasattr(sample, "metadata") else {}

    # Extract basic info
    task_name = eval_log.eval.task

    # Handle both timestamp formats (string ISO8601 or Unix timestamp)
    if isinstance(eval_log.eval.created, str):
        # Parse ISO8601 timestamp
        created_dt = datetime.fromisoformat(
            eval_log.eval.created.replace("Z", "+00:00")
        )
    else:
        # Unix timestamp
        created_dt = datetime.fromtimestamp(eval_log.eval.created, timezone.utc)

    trial_timestamp = created_dt.strftime("%Y%m%d_%H%M%S")
    trial_name = f"trial-{task_name}-{trial_timestamp}-{attempt}"

    # Extract model info
    provider, model_name = extract_model_info(eval_log)

    # Extract scoring
    reward = None
    if hasattr(sample, "scores") and sample.scores:
        # Get the first/main score
        score_name = list(sample.scores.keys())[0]
        score = sample.scores[score_name]
        score_data = {
            "value": score.value,
            "metadata": score.metadata if hasattr(score, "metadata") else {},
        }
        reward = convert_score_to_reward(score_data)

    # Extract error info
    error_type = None
    error_message = None
    error_traceback = None
    if hasattr(sample, "error") and sample.error:
        error_type = type(sample.error).__name__
        error_message = str(sample.error)
        # TODO: Extract traceback if available

    # Calculate timestamps
    started_at = created_dt.isoformat()
    # Completed timestamp - use eval completed time if available
    finished_at = datetime.now(
        timezone.utc
    ).isoformat()  # TODO: Get actual completion time

    # Build result structure
    result = {
        "task_name": task_name,
        "trial_name": trial_name,
        "source": "fle",
        "task_checksum": calculate_task_checksum(metadata),
        "agent_info": {
            "name": "fle_inspect_agent",
            "model_info": {
                "provider": provider,
                "name": model_name,
            },
        },
        "config": {
            "agent": {
                "model_name": f"{provider}/{model_name}",
            }
        },
        "verifier_result": {
            "rewards": {
                "reward": reward,
            }
        },
        "agent_result": {
            "n_input_tokens": sum_tokens(eval_log, "input"),
            "n_output_tokens": sum_tokens(eval_log, "output"),
            "n_cache_tokens": sum_tokens(eval_log, "cache"),
            "cost_usd": calculate_total_cost(eval_log),
        },
        "started_at": started_at,
        "finished_at": finished_at,
    }

    # Add error info if present
    if error_type:
        result["exception_info"] = {
            "exception_type": error_type,
            "exception_message": error_message,
            "exception_traceback": error_traceback or "",
        }

    return result


def create_vendor_eval_structure(
    output_base: Path,
    task_name: str,
    trial_timestamp: str,
    attempt: int,
) -> tuple[Path, Path, Path]:
    """Create vendor-eval compatible directory structure.

    Args:
        output_base: Base output directory
        task_name: Name of the task
        trial_timestamp: Timestamp string (YYYYMMDD_HHMMSS)
        attempt: Attempt number

    Returns:
        Tuple of (trial_dir, result_json_path, agent_dir)
    """
    trial_name = f"trial-{task_name}-{trial_timestamp}-{attempt}"
    trial_dir = output_base / "eval_results" / "vendor-eval" / trial_name
    trial_dir.mkdir(parents=True, exist_ok=True)

    result_json = trial_dir / "result.json"

    agent_dir = trial_dir / "agent"
    agent_dir.mkdir(exist_ok=True)

    return trial_dir, result_json, agent_dir


def export_eval_log(
    eval_log: EvalLog,
    output_dir: Path,
    sample_idx: int = 0,
    attempt: int = 0,
) -> Path:
    """Export a single Inspect eval log to vendor-eval format.

    Args:
        eval_log: Inspect evaluation log
        output_dir: Output directory for vendor-eval format
        sample_idx: Sample index to export
        attempt: Attempt number

    Returns:
        Path to created trial directory
    """
    # Extract task info
    task_name = eval_log.eval.task

    # Handle both timestamp formats (string ISO8601 or Unix timestamp)
    if isinstance(eval_log.eval.created, str):
        created_dt = datetime.fromisoformat(
            eval_log.eval.created.replace("Z", "+00:00")
        )
    else:
        created_dt = datetime.fromtimestamp(eval_log.eval.created, timezone.utc)

    trial_timestamp = created_dt.strftime("%Y%m%d_%H%M%S")

    # Create directory structure
    trial_dir, result_json_path, agent_dir = create_vendor_eval_structure(
        output_dir, task_name, trial_timestamp, attempt
    )

    # Build and write result.json
    result_data = build_result_json(eval_log, sample_idx, attempt)
    with open(result_json_path, "w") as f:
        json.dump(result_data, f, indent=2)

    logger.info(f"✓ Created result.json at {result_json_path}")

    # Export trajectory if available
    trajectory_data = export_trajectory_to_atif(eval_log, sample_idx)
    if trajectory_data:
        trajectory_path = agent_dir / "trajectory.json"
        with open(trajectory_path, "w") as f:
            json.dump(trajectory_data, f, indent=2)
        logger.info(f"✓ Created trajectory.json at {trajectory_path}")

    return trial_dir


def export_inspect_results(
    eval_log_dir: str | Path,
    output_dir: str | Path,
    task_names: list[str] | None = None,
) -> list[Path]:
    """Export Inspect eval results to vendor-eval-kit format.

    Args:
        eval_log_dir: Path to Inspect logs directory (e.g., .fle/inspect_logs/20260327_123456)
        output_dir: Path to output directory for vendor-eval format
        task_names: Optional list of specific tasks to export (default: all)

    Returns:
        List of created trial directories

    Creates structure:
        output_dir/
          eval_results/vendor-eval/
            trial-<task>-<timestamp>-<attempt>/
              result.json
              agent/
                trajectory.json
    """
    eval_log_dir = Path(eval_log_dir)
    output_dir = Path(output_dir)

    logger.info(f"🔄 Exporting Inspect results from {eval_log_dir}")
    logger.info(f"📁 Output directory: {output_dir}")

    # Find all .eval files in the log directory
    eval_files = list(eval_log_dir.glob("**/*.eval"))
    logger.info(f"📊 Found {len(eval_files)} eval files")

    created_trials = []

    for eval_file in eval_files:
        try:
            # Read eval log
            eval_log = read_eval_log(str(eval_file))

            # Filter by task name if specified
            if task_names and eval_log.eval.task not in task_names:
                logger.debug(f"Skipping task {eval_log.eval.task} (not in filter list)")
                continue

            # Export each sample (typically just 1 per eval, but handle multiple)
            for sample_idx in range(len(eval_log.samples)):
                # Handle multiple epochs/attempts if present
                # For now, treat each eval file as attempt 0
                trial_dir = export_eval_log(
                    eval_log,
                    output_dir,
                    sample_idx=sample_idx,
                    attempt=0,
                )
                created_trials.append(trial_dir)

        except Exception as e:
            logger.error(f"Failed to export {eval_file}: {e}")
            continue

    logger.info(f"✅ Successfully exported {len(created_trials)} trials")
    return created_trials
