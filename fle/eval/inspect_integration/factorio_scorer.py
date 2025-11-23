"""Production scorer for Factorio evaluations."""

import logging
from typing import Any, Dict

from inspect_ai.scorer import scorer, Score, Target, accuracy
from inspect_ai.agent import AgentState

logger = logging.getLogger(__name__)


@scorer
def factorio_production_scorer():
    """Detailed scorer for Factorio production tasks"""

    async def score(state: AgentState, target: Target) -> Score:
        try:
            # Extract results from state.store
            production_score = state.store.get("production_score", 0.0)
            achievements = state.store.get("achievements", {})
            trajectory_data = state.store.get("trajectory_data", {})
            error = state.store.get("error")

            # Get expected quota from target
            task_quota = target.get("expected_production_score", 100.0)

            # Calculate success based on quota achievement
            success = production_score >= task_quota

            # Calculate efficiency metrics
            efficiency = calculate_efficiency(trajectory_data, production_score)
            quota_ratio = production_score / task_quota if task_quota > 0 else 0.0

            # Count completed achievements
            completed_achievements = (
                len(achievements.get("completed", []))
                if isinstance(achievements, dict)
                else 0
            )

            # Create explanation
            explanation_parts = [
                f"Production score: {production_score:.2f}/{task_quota}",
                f"Success: {success}",
                f"Efficiency: {efficiency:.2f}",
                f"Quota ratio: {quota_ratio:.2f}",
                f"Achievements: {completed_achievements}",
            ]

            if error:
                explanation_parts.append(f"Error: {error}")

            explanation = ", ".join(explanation_parts)

            # Log scoring details
            logger.info(
                f"Scoring - Model: {state.input.get('model', 'unknown')}, "
                f"Task: {state.input.get('env_id', 'unknown')}, "
                f"Score: {production_score}, Success: {success}"
            )

            return Score(
                value=production_score,  # Primary metric value
                answer=f"{production_score:.2f}",
                explanation=explanation,
                metadata={
                    "success": success,
                    "efficiency": efficiency,
                    "quota_ratio": quota_ratio,
                    "achievements_count": completed_achievements,
                    "has_error": bool(error),
                    "task_quota": task_quota,
                    "execution_time": trajectory_data.get("execution_time", 0.0),
                    "total_steps": trajectory_data.get("total_steps", 0),
                },
            )

        except Exception as e:
            logger.error(f"Error in scorer: {e}")
            return Score(
                value=0.0,
                answer="0.00",
                explanation=f"Scorer error: {str(e)}",
                metadata={"scorer_error": str(e)},
            )

    return score


@scorer(metrics=[accuracy()])
def factorio_success_scorer():
    """Binary success scorer for Pass@N evaluation"""

    async def score(state: AgentState, target: Target) -> Score:
        try:
            production_score = state.store.get("production_score", 0.0)
            task_quota = target.get("expected_production_score", 100.0)
            success = production_score >= task_quota

            return Score(
                value=success,  # Boolean for accuracy metric
                answer="success" if success else "failure",
                explanation=f"Production score: {production_score:.2f}, Quota: {task_quota}, Success: {success}",
            )

        except Exception as e:
            logger.error(f"Error in success scorer: {e}")
            return Score(
                value=False, answer="failure", explanation=f"Scorer error: {str(e)}"
            )

    return score


def calculate_efficiency(
    trajectory_data: Dict[str, Any], production_score: float
) -> float:
    """Calculate efficiency based on trajectory data and production score"""
    try:
        if not trajectory_data:
            return 0.0

        # Basic efficiency calculation: score per step
        total_steps = trajectory_data.get("total_steps", 1)
        if total_steps == 0:
            return 0.0

        efficiency = production_score / total_steps

        # Could add more sophisticated efficiency calculations here:
        # - Time-based efficiency
        # - Resource utilization efficiency
        # - Goal completion rate

        return efficiency

    except Exception as e:
        logger.error(f"Error calculating efficiency: {e}")
        return 0.0


@scorer
def factorio_detailed_metrics_scorer():
    """Scorer that returns multiple detailed metrics"""

    async def score(state: AgentState, target: Target) -> Score:
        try:
            production_score = state.store.get("production_score", 0.0)
            achievements = state.store.get("achievements", {})
            trajectory_data = state.store.get("trajectory_data", {})
            task_quota = target.get("expected_production_score", 100.0)

            # Calculate all metrics
            success = production_score >= task_quota
            efficiency = calculate_efficiency(trajectory_data, production_score)
            quota_ratio = production_score / task_quota if task_quota > 0 else 0.0
            completed_achievements = (
                len(achievements.get("completed", []))
                if isinstance(achievements, dict)
                else 0
            )
            execution_time = trajectory_data.get("execution_time", 0.0)
            total_steps = trajectory_data.get("total_steps", 0)

            # Calculate steps per minute if we have time data
            steps_per_minute = (
                (total_steps / execution_time * 60) if execution_time > 0 else 0
            )

            return Score(
                value=production_score,
                answer=f"{production_score:.2f}",
                explanation=f"Comprehensive evaluation - Score: {production_score:.2f}, Success: {success}, Efficiency: {efficiency:.3f}",
                metadata={
                    # Core metrics
                    "production_score": production_score,
                    "success": success,
                    "task_quota": task_quota,
                    "quota_ratio": quota_ratio,
                    # Efficiency metrics
                    "efficiency": efficiency,
                    "steps_per_minute": steps_per_minute,
                    # Progress metrics
                    "achievements_count": completed_achievements,
                    "total_steps": total_steps,
                    "execution_time": execution_time,
                    # Task context
                    "model": state.input.get("model", "unknown"),
                    "env_id": state.input.get("env_id", "unknown"),
                    "trial": state.input.get("trial", 0),
                },
            )

        except Exception as e:
            logger.error(f"Error in detailed metrics scorer: {e}")
            return Score(
                value=0.0,
                answer="0.00",
                explanation=f"Scorer error: {str(e)}",
                metadata={"scorer_error": str(e)},
            )
