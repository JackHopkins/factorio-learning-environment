"""Scorers for Factorio Learning Environment evaluations.

Contains scorers for:
- Throughput tasks (quota-based): simple_production_score, throughput_proportion_scorer, comprehensive_factorio_scorer
- Unbounded tasks (open-play): unbounded_production_scorer, unbounded_growth_scorer
- Utility scorers: production_score_tracker, step_change_tracker
"""

import logging
from typing import List
from inspect_ai.scorer import scorer, Score, Target, Scorer, accuracy, mean, score
from inspect_ai.agent import AgentState
from inspect_ai.util import store_as

from fle.eval.inspect_integration.solver import TrajectoryData

logger = logging.getLogger(__name__)


# =============================================================================
# Simple/Basic Scorers
# =============================================================================


@scorer(metrics=[accuracy()])
def simple_production_score() -> Scorer:
    """Simple scorer function for production evaluation.

    Returns binary success/failure based on whether production score meets quota.
    """

    async def score(state: AgentState, target: Target) -> Score:
        try:
            # Use typed store to get trajectory data
            trajectory_data = store_as(TrajectoryData)
            production_score = (
                trajectory_data.final_score or trajectory_data.production_score or 0.0
            )
            error = trajectory_data.error

            # Get metadata using the working approach
            metadata = (
                getattr(state, "metadata", {}) if hasattr(state, "metadata") else {}
            )
            expected_score = metadata.get("expected_production_score", 16.0)

            # Calculate success based on quota achievement
            success = production_score >= expected_score and not error

            return Score(
                value=success,  # Boolean for accuracy metric
                answer="success" if success else "failure",
                explanation=f"Production score: {production_score:.1f}/{expected_score}, Success: {success}"
                + (f", Error: {error}" if error else ""),
            )

        except Exception as e:
            return Score(
                value=False, answer="failure", explanation=f"Scorer error: {str(e)}"
            )

    return score


# =============================================================================
# Throughput Task Scorers (Quota-Based)
# =============================================================================


@scorer(metrics=[mean()])
def throughput_proportion_scorer() -> Scorer:
    """Track proportion of desired throughput achieved."""

    async def score(state: AgentState, target: Target) -> Score:
        try:
            trajectory_data = store_as(TrajectoryData)
            production_score = (
                trajectory_data.final_score or trajectory_data.production_score or 0.0
            )

            # Get expected quota from metadata
            metadata = (
                getattr(state, "metadata", {}) if hasattr(state, "metadata") else {}
            )
            expected_score = metadata.get("expected_production_score", 100.0)

            # Calculate proportion (capped at 1.0)
            proportion = (
                min(production_score / expected_score, 1.0)
                if expected_score > 0
                else 0.0
            )

            return Score(
                value=proportion,
                answer=f"{proportion:.3f}",
                explanation=f"Throughput proportion: {production_score:.2f}/{expected_score:.2f} = {proportion:.3f}",
                metadata={
                    "production_score": production_score,
                    "expected_score": expected_score,
                    "proportion": proportion,
                    "quota_achieved": production_score >= expected_score,
                },
            )

        except Exception as e:
            logger.error(f"Error in throughput proportion scorer: {e}")
            return Score(
                value=0.0, answer="0.000", explanation=f"Scorer error: {str(e)}"
            )

    return score


@scorer(metrics=[mean()])
def production_score_tracker() -> Scorer:
    """Track overall production score."""

    async def score(state: AgentState, target: Target) -> Score:
        try:
            trajectory_data = store_as(TrajectoryData)
            production_score = (
                trajectory_data.final_score or trajectory_data.production_score or 0.0
            )

            # Get additional metrics from trajectory
            total_steps = trajectory_data.total_steps or 0
            error = trajectory_data.error

            return Score(
                value=production_score,
                answer=f"{production_score:.2f}",
                explanation=f"Production score: {production_score:.2f} over {total_steps} steps"
                + (f" (Error: {error})" if error else ""),
                metadata={
                    "production_score": production_score,
                    "total_steps": total_steps,
                    "has_error": bool(error),
                    "steps_per_score": total_steps / production_score
                    if production_score > 0
                    else 0,
                    "score_per_step": production_score / total_steps
                    if total_steps > 0
                    else 0,
                },
            )

        except Exception as e:
            logger.error(f"Error in production score tracker: {e}")
            return Score(
                value=0.0, answer="0.00", explanation=f"Scorer error: {str(e)}"
            )

    return score


@scorer(metrics=[mean()])
def step_change_tracker() -> Scorer:
    """Track change in production score from last step."""

    async def score(state: AgentState, target: Target) -> Score:
        try:
            trajectory_data = store_as(TrajectoryData)
            scores = trajectory_data.scores or []

            if len(scores) < 2:
                # Not enough data for change calculation
                change = 0.0
                final_change = 0.0
            else:
                # Calculate change from last step
                change = scores[-1] - scores[-2] if len(scores) >= 2 else 0.0
                # Calculate total change from first to last
                final_change = scores[-1] - scores[0] if len(scores) >= 2 else 0.0

            # Calculate additional change metrics
            max_single_step_gain = max(
                (scores[i] - scores[i - 1] for i in range(1, len(scores))), default=0.0
            )
            min_single_step_change = min(
                (scores[i] - scores[i - 1] for i in range(1, len(scores))), default=0.0
            )
            avg_step_change = (
                final_change / (len(scores) - 1) if len(scores) > 1 else 0.0
            )

            # Use absolute change as score (to track magnitude of improvement)
            score_value = abs(change)

            return Score(
                value=score_value,
                answer=f"{change:.3f}",
                explanation=f"Step change: {change:.3f}, Total change: {final_change:.3f}, Avg: {avg_step_change:.3f}",
                metadata={
                    "last_step_change": change,
                    "total_change": final_change,
                    "average_step_change": avg_step_change,
                    "max_single_step_gain": max_single_step_gain,
                    "min_single_step_change": min_single_step_change,
                    "total_steps_with_scores": len(scores),
                    "scores_trajectory": scores[-10:]
                    if len(scores) > 10
                    else scores,  # Last 10 scores for analysis
                },
            )

        except Exception as e:
            logger.error(f"Error in step change tracker: {e}")
            return Score(
                value=0.0, answer="0.000", explanation=f"Scorer error: {str(e)}"
            )

    return score


@scorer(metrics=[accuracy(), mean()])
def comprehensive_factorio_scorer() -> Scorer:
    """Comprehensive scorer combining all metrics."""

    async def score(state: AgentState, target: Target) -> Score:
        try:
            trajectory_data = store_as(TrajectoryData)
            production_score = (
                trajectory_data.final_score or trajectory_data.production_score or 0.0
            )
            scores = trajectory_data.scores or []
            error = trajectory_data.error
            total_steps = trajectory_data.total_steps or 0

            # Get expected quota from metadata
            metadata = (
                getattr(state, "metadata", {}) if hasattr(state, "metadata") else {}
            )
            expected_score = metadata.get("expected_production_score", 100.0)

            # Calculate all metrics
            throughput_proportion = (
                min(production_score / expected_score, 1.0)
                if expected_score > 0
                else 0.0
            )
            quota_achieved = production_score >= expected_score and not error

            # Step change metrics
            last_step_change = scores[-1] - scores[-2] if len(scores) >= 2 else 0.0
            total_change = scores[-1] - scores[0] if len(scores) >= 2 else 0.0
            avg_step_change = (
                total_change / (len(scores) - 1) if len(scores) > 1 else 0.0
            )

            # Performance metrics
            score_per_step = production_score / total_steps if total_steps > 0 else 0.0
            max_single_gain = max(
                (scores[i] - scores[i - 1] for i in range(1, len(scores))), default=0.0
            )

            # Overall success metric for accuracy
            success = quota_achieved

            explanation_parts = [
                f"Score: {production_score:.2f}/{expected_score:.2f}",
                f"Proportion: {throughput_proportion:.3f}",
                f"Last change: {last_step_change:+.3f}",
                f"Total change: {total_change:+.3f}",
                f"Steps: {total_steps}",
                f"Success: {success}",
            ]

            if error:
                explanation_parts.append(f"Error: {error}")

            explanation = ", ".join(explanation_parts)

            return Score(
                value=str(
                    throughput_proportion
                ),  # Boolean for accuracy metric, proportion for mean
                answer=str(1) if success else str(throughput_proportion),
                explanation=explanation,
                metadata={
                    # Core metrics you requested
                    "throughput_proportion": throughput_proportion,
                    "production_score": production_score,
                    "last_step_change": last_step_change,
                    # Additional context
                    "expected_score": expected_score,
                    "quota_achieved": quota_achieved,
                    "total_change": total_change,
                    "average_step_change": avg_step_change,
                    "score_per_step": score_per_step,
                    "max_single_step_gain": max_single_gain,
                    "total_steps": total_steps,
                    "has_error": bool(error),
                    "error": error or "",
                    # Trajectory analysis
                    "scores_count": len(scores),
                    "final_10_scores": scores[-10:] if len(scores) > 10 else scores,
                    # Task context
                    "env_id": metadata.get("env_id", "unknown"),
                    "trajectory_length": metadata.get("trajectory_length", 64),
                },
            )

        except Exception as e:
            logger.error(f"Error in comprehensive scorer: {e}")
            return Score(
                value=False,
                answer="failure",
                explanation=f"Scorer error: {str(e)}",
                metadata={"scorer_error": str(e)},
            )

    return score


# =============================================================================
# Unbounded Task Scorers (Open-Play / Build Biggest Factory)
# =============================================================================


@scorer(metrics=[mean()])
def unbounded_production_scorer() -> Scorer:
    """Scorer for unbounded/open-play tasks that tracks cumulative production score.

    Unlike throughput scorers, this scorer:
    - Has no quota or expected score - higher is always better
    - Tracks cumulative production value (economic worth of all items produced)
    - Designed for comparing agent performance on open-ended tasks
    """

    async def score(state: AgentState, target: Target) -> Score:
        try:
            trajectory_data = store_as(TrajectoryData)
            production_score = (
                trajectory_data.final_score or trajectory_data.production_score or 0.0
            )
            scores = trajectory_data.scores or []
            error = trajectory_data.error
            total_steps = trajectory_data.total_steps or 0

            # Calculate trajectory metrics
            score_per_step = production_score / total_steps if total_steps > 0 else 0.0

            # Calculate growth metrics
            if len(scores) >= 2:
                total_growth = scores[-1] - scores[0]
                avg_growth_per_step = total_growth / (len(scores) - 1)
                max_single_step_gain = max(
                    (scores[i] - scores[i - 1] for i in range(1, len(scores))),
                    default=0.0,
                )
                # Find when production really started (first non-zero score)
                first_production_step = next(
                    (i for i, s in enumerate(scores) if s > 0), len(scores)
                )
            else:
                total_growth = 0.0
                avg_growth_per_step = 0.0
                max_single_step_gain = 0.0
                first_production_step = 0

            explanation_parts = [
                f"Production score: {production_score:.2f}",
                f"Steps: {total_steps}",
                f"Score/step: {score_per_step:.3f}",
                f"Total growth: {total_growth:.2f}",
            ]

            if error:
                explanation_parts.append(f"Error: {error}")

            explanation = ", ".join(explanation_parts)

            return Score(
                value=production_score,  # Raw production score - higher is better
                answer=f"{production_score:.2f}",
                explanation=explanation,
                metadata={
                    # Core metrics
                    "production_score": production_score,
                    "total_steps": total_steps,
                    "score_per_step": score_per_step,
                    # Growth analysis
                    "total_growth": total_growth,
                    "average_growth_per_step": avg_growth_per_step,
                    "max_single_step_gain": max_single_step_gain,
                    "first_production_step": first_production_step,
                    # Trajectory data
                    "scores_count": len(scores),
                    "final_10_scores": scores[-10:] if len(scores) > 10 else scores,
                    "first_10_scores": scores[:10] if len(scores) > 10 else scores,
                    # Error tracking
                    "has_error": bool(error),
                    "error": error or "",
                    # Task context
                    "task_type": "unbounded_production",
                },
            )

        except Exception as e:
            logger.error(f"Error in unbounded production scorer: {e}")
            return Score(
                value=0.0,
                answer="0.00",
                explanation=f"Scorer error: {str(e)}",
                metadata={"scorer_error": str(e)},
            )

    return score


@scorer(metrics=[mean()])
def unbounded_growth_scorer() -> Scorer:
    """Scorer focused on production growth rate for unbounded tasks.

    This scorer emphasizes how quickly the factory scales up production,
    rather than just the final absolute score.
    """

    async def score(state: AgentState, target: Target) -> Score:
        try:
            trajectory_data = store_as(TrajectoryData)
            scores = trajectory_data.scores or []
            total_steps = trajectory_data.total_steps or 0

            if len(scores) < 2:
                return Score(
                    value=0.0,
                    answer="0.00",
                    explanation="Not enough data for growth calculation",
                    metadata={"scores_count": len(scores)},
                )

            # Calculate growth metrics
            total_growth = scores[-1] - scores[0]
            avg_growth_per_step = total_growth / (len(scores) - 1)

            # Calculate compound growth rate (if applicable)
            if scores[0] > 0 and scores[-1] > 0:
                growth_factor = scores[-1] / scores[0]
                steps = len(scores) - 1
                compound_growth_rate = (
                    (growth_factor ** (1 / steps)) - 1 if steps > 0 else 0
                )
            else:
                compound_growth_rate = 0.0

            # Find the step with maximum growth
            step_growths = [scores[i] - scores[i - 1] for i in range(1, len(scores))]
            max_growth_step = (
                step_growths.index(max(step_growths)) + 1 if step_growths else 0
            )

            return Score(
                value=avg_growth_per_step,  # Use average growth as the score
                answer=f"{avg_growth_per_step:.3f}",
                explanation=f"Avg growth/step: {avg_growth_per_step:.3f}, Total growth: {total_growth:.2f}",
                metadata={
                    "average_growth_per_step": avg_growth_per_step,
                    "total_growth": total_growth,
                    "compound_growth_rate": compound_growth_rate,
                    "max_growth_step": max_growth_step,
                    "final_score": scores[-1] if scores else 0.0,
                    "initial_score": scores[0] if scores else 0.0,
                    "total_steps": total_steps,
                },
            )

        except Exception as e:
            logger.error(f"Error in unbounded growth scorer: {e}")
            return Score(
                value=0.0,
                answer="0.00",
                explanation=f"Scorer error: {str(e)}",
                metadata={"scorer_error": str(e)},
            )

    return score


# =============================================================================
# Intermediate Scoring Functions (for real-time trajectory analysis)
# =============================================================================


async def score_step_intermediate(
    state: AgentState,
    step_num: int,
    production_score: float,
    expected_score: float,
    scores_history: List[float],
) -> List[Score]:
    """
    Score intermediate step during trajectory execution.
    Returns list of scores for different metrics.
    """
    intermediate_scores = []

    try:
        # 1. Throughput Proportion Score
        proportion = (
            min(production_score / expected_score, 1.0) if expected_score > 0 else 0.0
        )
        proportion_score = Score(
            value=proportion,
            answer=f"{proportion:.3f}",
            explanation=f"Step {step_num}: Throughput proportion {production_score:.2f}/{expected_score:.2f} = {proportion:.3f}",
            metadata={
                "step": step_num,
                "metric_type": "throughput_proportion",
                "production_score": production_score,
                "expected_score": expected_score,
                "proportion": proportion,
            },
        )
        intermediate_scores.append(proportion_score)

        # 2. Production Score Tracking
        production_score_obj = Score(
            value=production_score,
            answer=f"{production_score:.2f}",
            explanation=f"Step {step_num}: Production score {production_score:.2f}",
            metadata={
                "step": step_num,
                "metric_type": "production_score",
                "production_score": production_score,
                "score_per_step": production_score / step_num if step_num > 0 else 0,
            },
        )
        intermediate_scores.append(production_score_obj)

        # 3. Step Change Tracking (if we have previous scores)
        if len(scores_history) >= 2:
            last_change = scores_history[-1] - scores_history[-2]
            total_change = scores_history[-1] - scores_history[0]
            avg_change = total_change / (len(scores_history) - 1)

            step_change_score = Score(
                value=abs(last_change),  # Use magnitude for scoring
                answer=f"{last_change:+.3f}",
                explanation=f"Step {step_num}: Change {last_change:+.3f}, Total {total_change:+.3f}",
                metadata={
                    "step": step_num,
                    "metric_type": "step_change",
                    "last_step_change": last_change,
                    "total_change": total_change,
                    "average_change": avg_change,
                    "scores_count": len(scores_history),
                },
            )
            intermediate_scores.append(step_change_score)

        return intermediate_scores

    except Exception as e:
        logger.error(f"Error in intermediate scoring for step {step_num}: {e}")
        error_score = Score(
            value=0.0,
            answer="error",
            explanation=f"Intermediate scoring error at step {step_num}: {str(e)}",
            metadata={"step": step_num, "error": str(e)},
        )
        return [error_score]


async def apply_intermediate_scoring(
    state: AgentState,
    step_num: int,
    production_score: float,
    expected_score: float,
    scores_history: List[float],
):
    """
    Apply intermediate scoring during trajectory execution.
    Uses inspect_ai.scorer.score() function for real-time scoring.
    """
    try:
        # Get intermediate scores for this step
        intermediate_scores = await score_step_intermediate(
            state, step_num, production_score, expected_score, scores_history
        )

        # Apply each score using inspect_ai's score function
        await score(state)

        logger.info(
            f"📊 Step {step_num}: Applied {len(intermediate_scores)} intermediate scores"
        )

    except Exception as e:
        logger.error(f"Error applying intermediate scoring for step {step_num}: {e}")


async def apply_unbounded_intermediate_scoring(
    state: AgentState,
    step_num: int,
    production_score: float,
    scores_history: List[float],
):
    """
    Apply intermediate scoring for unbounded tasks during trajectory execution.

    Unlike throughput tasks, this doesn't compare against a quota - it just
    tracks the cumulative production score and growth metrics.
    """
    try:
        intermediate_scores = []

        # 1. Production Score Tracking
        production_score_obj = Score(
            value=production_score,
            answer=f"{production_score:.2f}",
            explanation=f"Step {step_num}: Cumulative production score {production_score:.2f}",
            metadata={
                "step": step_num,
                "metric_type": "unbounded_production_score",
                "production_score": production_score,
                "score_per_step": production_score / step_num if step_num > 0 else 0,
            },
        )
        intermediate_scores.append(production_score_obj)

        # 2. Growth Tracking (if we have previous scores)
        if len(scores_history) >= 2:
            last_change = scores_history[-1] - scores_history[-2]
            total_change = scores_history[-1] - scores_history[0]
            avg_change = total_change / (len(scores_history) - 1)

            growth_score = Score(
                value=last_change,  # Can be negative if production decreases
                answer=f"{last_change:+.3f}",
                explanation=f"Step {step_num}: Growth {last_change:+.3f}, Total {total_change:+.3f}",
                metadata={
                    "step": step_num,
                    "metric_type": "unbounded_growth",
                    "last_step_change": last_change,
                    "total_change": total_change,
                    "average_change": avg_change,
                    "scores_count": len(scores_history),
                },
            )
            intermediate_scores.append(growth_score)

        # Apply scoring
        await score(state)

        logger.info(
            f"📊 Step {step_num}: Applied {len(intermediate_scores)} unbounded intermediate scores (score={production_score:.1f})"
        )

    except Exception as e:
        logger.error(
            f"Error applying unbounded intermediate scoring for step {step_num}: {e}"
        )
