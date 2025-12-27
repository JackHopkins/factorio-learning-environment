"""Scorers for Factorio Learning Environment evaluations.

Contains scorers for:
- Throughput tasks (quota-based): simple_production_score, throughput_proportion_scorer, comprehensive_factorio_scorer
- Unbounded tasks (open-play): production_score, automated_production_score, production_score_growth
- Achievement scorers: achievements (tracks unique item types produced), technologies (tracks researched technologies)
- Utility scorers: production_score_tracker, step_change_tracker
- Latency scorers: latency_scorer, inference_latency_scorer, sleep_duration_scorer
"""

import logging
from typing import List
from inspect_ai.scorer import (
    scorer,
    Score,
    Target,
    Scorer,
    accuracy,
    mean,
    score,
    stderr,
)
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
                answer=str(total_steps),  # f"{production_score:.2f}",
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
def production_score() -> Scorer:
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


@scorer(metrics=[mean(), stderr()])
def automated_production_score() -> Scorer:
    """Scorer for tracking automated production score (excluding harvested/crafted items).

    This scorer tracks the production score that comes only from automated machines,
    excluding:
    - Raw resources harvested manually or by drills (harvested_value)
    - Net value added by manual crafting (crafted_net_value)

    This is useful for measuring true factory automation performance,
    as it rewards building automated production chains rather than
    manual gathering and crafting.

    Formula: automated_score = total_production_score - harvested_delta - crafted_delta
    """

    async def score(state: AgentState, target: Target) -> Score:
        try:
            trajectory_data = store_as(TrajectoryData)
            automated_score = (
                trajectory_data.final_automated_score
                or trajectory_data.automated_production_score
                or 0.0
            )
            automated_scores = trajectory_data.automated_scores or []
            total_production_score = (
                trajectory_data.final_score or trajectory_data.production_score or 0.0
            )
            error = trajectory_data.error
            total_steps = trajectory_data.total_steps or 0

            # Calculate trajectory metrics
            score_per_step = automated_score / total_steps if total_steps > 0 else 0.0

            # Calculate growth metrics for automated score
            if len(automated_scores) >= 2:
                total_growth = automated_scores[-1] - automated_scores[0]
                avg_growth_per_step = total_growth / (len(automated_scores) - 1)
                max_single_step_gain = max(
                    (
                        automated_scores[i] - automated_scores[i - 1]
                        for i in range(1, len(automated_scores))
                    ),
                    default=0.0,
                )
                # Find when automated production really started (first positive score)
                first_automated_step = next(
                    (i for i, s in enumerate(automated_scores) if s > 0),
                    len(automated_scores),
                )
            else:
                total_growth = 0.0
                avg_growth_per_step = 0.0
                max_single_step_gain = 0.0
                first_automated_step = 0

            # Calculate automation ratio (what % of production is automated)
            automation_ratio = (
                (automated_score / total_production_score * 100)
                if total_production_score > 0
                else 0.0
            )

            explanation_parts = [
                f"Automated score: {automated_score:.2f}",
                f"Total score: {total_production_score:.2f}",
                f"Automation: {automation_ratio:.1f}%",
                f"Steps: {total_steps}",
                f"Score/step: {score_per_step:.3f}",
            ]

            if error:
                explanation_parts.append(f"Error: {error}")

            explanation = ", ".join(explanation_parts)

            return Score(
                value=automated_score,  # Automated production score - higher is better
                answer=f"{automated_score:.2f}",
                explanation=explanation,
                metadata={
                    # Core metrics
                    "automated_production_score": automated_score,
                    "total_production_score": total_production_score,
                    "automation_ratio": automation_ratio,
                    "total_steps": total_steps,
                    "score_per_step": score_per_step,
                    # Growth analysis
                    "total_growth": total_growth,
                    "average_growth_per_step": avg_growth_per_step,
                    "max_single_step_gain": max_single_step_gain,
                    "first_automated_step": first_automated_step,
                    # Trajectory data
                    "automated_scores_count": len(automated_scores),
                    "final_10_automated_scores": automated_scores[-10:]
                    if len(automated_scores) > 10
                    else automated_scores,
                    "first_10_automated_scores": automated_scores[:10]
                    if len(automated_scores) > 10
                    else automated_scores,
                    # Error tracking
                    "has_error": bool(error),
                    "error": error or "",
                    # Task context
                    "task_type": "unbounded_production",
                },
            )

        except Exception as e:
            logger.error(f"Error in automated production scorer: {e}")
            return Score(
                value=0.0,
                answer="0.00",
                explanation=f"Scorer error: {str(e)}",
                metadata={"scorer_error": str(e)},
            )

    return score


@scorer(metrics=[mean(), stderr()])
def production_score_growth() -> Scorer:
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
# Achievement Scorers
# =============================================================================


@scorer(metrics=[mean(), stderr()])
def achievements() -> Scorer:
    """Scorer tracking unique item types produced during the trajectory.

    This scorer reports the number of unique item types that have been
    created (either statically through crafting/harvesting or dynamically
    through automated production).

    The main score value is the count of unique item types.
    The metadata includes the full set of item type names.

    This is useful for measuring:
    - How diverse the agent's production is
    - Whether the agent is exploring the tech tree
    - Progress toward more complex items
    """

    async def score(state: AgentState, target: Target) -> Score:
        try:
            trajectory_data = store_as(TrajectoryData)
            produced_item_types = trajectory_data.produced_item_types or []

            # Convert to set to ensure uniqueness (should already be unique, but just in case)
            unique_items = set(produced_item_types)
            num_unique_items = len(unique_items)

            # Sort for consistent display
            sorted_items = sorted(unique_items)

            # Create a summary of item categories
            raw_resources = [
                i
                for i in sorted_items
                if i
                in {
                    "iron-ore",
                    "copper-ore",
                    "coal",
                    "stone",
                    "wood",
                    "crude-oil",
                    "water",
                    "uranium-ore",
                }
            ]
            basic_intermediates = [
                i
                for i in sorted_items
                if i
                in {
                    "iron-plate",
                    "copper-plate",
                    "steel-plate",
                    "stone-brick",
                    "copper-cable",
                    "iron-gear-wheel",
                    "iron-stick",
                }
            ]
            advanced_items = [
                i for i in sorted_items if i not in raw_resources + basic_intermediates
            ]

            explanation_parts = [
                f"Unique items: {num_unique_items}",
                f"Raw: {len(raw_resources)}",
                f"Basic: {len(basic_intermediates)}",
                f"Advanced: {len(advanced_items)}",
            ]

            return Score(
                value=num_unique_items,
                answer=str(num_unique_items),
                explanation=", ".join(explanation_parts),
                metadata={
                    "num_unique_items": num_unique_items,
                    "produced_item_types": sorted_items,
                    "raw_resources": raw_resources,
                    "basic_intermediates": basic_intermediates,
                    "advanced_items": advanced_items,
                    "num_raw_resources": len(raw_resources),
                    "num_basic_intermediates": len(basic_intermediates),
                    "num_advanced_items": len(advanced_items),
                },
            )

        except Exception as e:
            logger.error(f"Error in achievement scorer: {e}")
            return Score(
                value=0,
                answer="0",
                explanation=f"Scorer error: {str(e)}",
                metadata={"scorer_error": str(e)},
            )

    return score


@scorer(metrics=[mean(), stderr()])
def technologies() -> Scorer:
    """Scorer tracking technologies researched during the trajectory.

    This scorer reports the number of technologies that have been researched
    during the trajectory. Technologies are considered "researched" when their
    research is complete (not just in progress).

    The main score value is the count of researched technologies.
    The metadata includes the full list of technology names.

    This is useful for measuring:
    - How far the agent has progressed in the tech tree
    - Whether the agent is pursuing research actively
    - Progress toward unlocking advanced capabilities
    """

    async def score(state: AgentState, target: Target) -> Score:
        try:
            trajectory_data = store_as(TrajectoryData)
            researched_technologies = trajectory_data.researched_technologies or []

            # Convert to set to ensure uniqueness (should already be unique, but just in case)
            unique_techs = set(researched_technologies)
            num_researched = len(unique_techs)

            # Sort for consistent display
            sorted_techs = sorted(unique_techs)

            # Categorize technologies by tier/type
            # Tier 1: Basic automation and logistics
            tier1_techs = {
                "automation",
                "logistics",
                "optics",
                "turrets",
                "stone-wall",
                "electronics",
                "steel-processing",
            }
            # Tier 2: Intermediate techs
            tier2_techs = {
                "automation-2",
                "logistics-2",
                "fast-inserter",
                "steel-axe",
                "military",
                "military-2",
                "engine",
                "fluid-handling",
                "oil-processing",
                "plastics",
                "sulfur-processing",
            }
            # Tier 3: Advanced techs
            tier3_techs = {
                "automation-3",
                "logistics-3",
                "advanced-electronics",
                "advanced-electronics-2",
                "advanced-oil-processing",
                "chemical-science-pack",
                "production-science-pack",
                "utility-science-pack",
                "rocket-silo",
                "space-science-pack",
            }

            tier1_researched = [t for t in sorted_techs if t in tier1_techs]
            tier2_researched = [t for t in sorted_techs if t in tier2_techs]
            tier3_researched = [t for t in sorted_techs if t in tier3_techs]
            other_researched = [
                t
                for t in sorted_techs
                if t not in tier1_techs | tier2_techs | tier3_techs
            ]

            explanation_parts = [
                f"Researched: {num_researched}",
                f"Tier1: {len(tier1_researched)}",
                f"Tier2: {len(tier2_researched)}",
                f"Tier3: {len(tier3_researched)}",
                f"Other: {len(other_researched)}",
            ]

            return Score(
                value=num_researched,
                answer=str(num_researched),
                explanation=", ".join(explanation_parts),
                metadata={
                    "num_researched_technologies": num_researched,
                    "researched_technologies": sorted_techs,
                    "tier1_technologies": tier1_researched,
                    "tier2_technologies": tier2_researched,
                    "tier3_technologies": tier3_researched,
                    "other_technologies": other_researched,
                    "num_tier1": len(tier1_researched),
                    "num_tier2": len(tier2_researched),
                    "num_tier3": len(tier3_researched),
                    "num_other": len(other_researched),
                },
            )

        except Exception as e:
            logger.error(f"Error in research scorer: {e}")
            return Score(
                value=0,
                answer="0",
                explanation=f"Scorer error: {str(e)}",
                metadata={"scorer_error": str(e)},
            )

    return score


# =============================================================================
# Latency Scorers
# =============================================================================


@scorer(metrics=[mean(), stderr()])
def latency_scorer() -> Scorer:
    """Comprehensive latency scorer tracking all timing metrics.

    Tracks:
    - Inference latency (time for model to generate response)
    - Environment execution latency (time for gym_env.step())
    - Policy execution latency (time for Python code execution)
    - Sleep duration (time environment was blocking during sleep actions)
    - Total step latency (wall-clock time per step)
    """

    async def score(state: AgentState, target: Target) -> Score:
        try:
            trajectory_data = store_as(TrajectoryData)

            # Get latency lists
            inference_latencies = trajectory_data.inference_latencies or []
            env_execution_latencies = trajectory_data.env_execution_latencies or []
            policy_execution_latencies = (
                trajectory_data.policy_execution_latencies or []
            )
            sleep_durations = trajectory_data.sleep_durations or []
            total_step_latencies = trajectory_data.total_step_latencies or []

            if not total_step_latencies:
                return Score(
                    value=0.0,
                    answer="0.00",
                    explanation="No latency data available",
                    metadata={"has_latency_data": False},
                )

            # Calculate summary statistics
            num_steps = len(total_step_latencies)

            # Total latency stats
            total_latency_sum = sum(total_step_latencies)
            avg_total_latency = total_latency_sum / num_steps
            max_total_latency = max(total_step_latencies)
            min_total_latency = min(total_step_latencies)

            # Inference latency stats
            avg_inference = (
                sum(inference_latencies) / len(inference_latencies)
                if inference_latencies
                else 0
            )
            max_inference = max(inference_latencies) if inference_latencies else 0
            total_inference = sum(inference_latencies)

            # Environment execution latency stats
            avg_env = (
                sum(env_execution_latencies) / len(env_execution_latencies)
                if env_execution_latencies
                else 0
            )
            max_env = max(env_execution_latencies) if env_execution_latencies else 0
            total_env = sum(env_execution_latencies)

            # Policy execution latency stats
            avg_policy = (
                sum(policy_execution_latencies) / len(policy_execution_latencies)
                if policy_execution_latencies
                else 0
            )
            max_policy = (
                max(policy_execution_latencies) if policy_execution_latencies else 0
            )
            total_policy = sum(policy_execution_latencies)

            # Sleep duration stats
            total_sleep = sum(sleep_durations)
            avg_sleep = total_sleep / num_steps if num_steps > 0 else 0
            steps_with_sleep = sum(1 for s in sleep_durations if s > 0)

            # Calculate percentage breakdown
            inference_pct = (
                (total_inference / total_latency_sum * 100)
                if total_latency_sum > 0
                else 0
            )
            env_pct = (
                (total_env / total_latency_sum * 100) if total_latency_sum > 0 else 0
            )
            sleep_pct = (
                (total_sleep / total_latency_sum * 100) if total_latency_sum > 0 else 0
            )

            explanation = (
                f"Avg step: {avg_total_latency:.2f}s "
                f"(inference: {avg_inference:.2f}s [{inference_pct:.1f}%], "
                f"env: {avg_env:.2f}s [{env_pct:.1f}%], "
                f"sleep: {avg_sleep:.2f}s [{sleep_pct:.1f}%])"
            )

            return Score(
                value=avg_total_latency,  # Use average step latency as the score value
                answer=f"{avg_total_latency:.2f}",
                explanation=explanation,
                metadata={
                    # Summary stats
                    "num_steps": num_steps,
                    "total_wall_clock_time": total_latency_sum,
                    # Average latencies
                    "avg_total_step_latency": avg_total_latency,
                    "avg_inference_latency": avg_inference,
                    "avg_env_execution_latency": avg_env,
                    "avg_policy_execution_latency": avg_policy,
                    "avg_sleep_duration": avg_sleep,
                    # Max latencies
                    "max_total_step_latency": max_total_latency,
                    "max_inference_latency": max_inference,
                    "max_env_execution_latency": max_env,
                    "max_policy_execution_latency": max_policy,
                    # Min latencies
                    "min_total_step_latency": min_total_latency,
                    # Totals
                    "total_inference_time": total_inference,
                    "total_env_execution_time": total_env,
                    "total_policy_execution_time": total_policy,
                    "total_sleep_time": total_sleep,
                    # Percentages
                    "inference_time_pct": inference_pct,
                    "env_execution_time_pct": env_pct,
                    "sleep_time_pct": sleep_pct,
                    # Sleep specifics
                    "steps_with_sleep": steps_with_sleep,
                    "steps_without_sleep": num_steps - steps_with_sleep,
                    # Last 10 step latencies for analysis
                    "last_10_total_latencies": total_step_latencies[-10:]
                    if len(total_step_latencies) > 10
                    else total_step_latencies,
                    "last_10_inference_latencies": inference_latencies[-10:]
                    if len(inference_latencies) > 10
                    else inference_latencies,
                },
            )

        except Exception as e:
            logger.error(f"Error in latency scorer: {e}")
            return Score(
                value=0.0,
                answer="0.00",
                explanation=f"Scorer error: {str(e)}",
                metadata={"scorer_error": str(e)},
            )

    return score


@scorer(metrics=[mean()])
def inference_latency_scorer() -> Scorer:
    """Track inference latency (time for model to generate response)."""

    async def score(state: AgentState, target: Target) -> Score:
        try:
            trajectory_data = store_as(TrajectoryData)
            inference_latencies = trajectory_data.inference_latencies or []

            if not inference_latencies:
                return Score(
                    value=0.0,
                    answer="0.00",
                    explanation="No inference latency data available",
                )

            avg_latency = sum(inference_latencies) / len(inference_latencies)
            total_latency = sum(inference_latencies)
            max_latency = max(inference_latencies)
            min_latency = min(inference_latencies)

            return Score(
                value=avg_latency,
                answer=f"{avg_latency:.2f}",
                explanation=f"Avg inference: {avg_latency:.2f}s, Total: {total_latency:.1f}s, Max: {max_latency:.2f}s",
                metadata={
                    "avg_inference_latency": avg_latency,
                    "total_inference_time": total_latency,
                    "max_inference_latency": max_latency,
                    "min_inference_latency": min_latency,
                    "num_inferences": len(inference_latencies),
                },
            )

        except Exception as e:
            logger.error(f"Error in inference latency scorer: {e}")
            return Score(
                value=0.0, answer="0.00", explanation=f"Scorer error: {str(e)}"
            )

    return score


@scorer(metrics=[mean(), stderr()])
def sleep_duration_scorer() -> Scorer:
    """Track sleep duration (time environment was blocking during sleep actions)."""

    async def score(state: AgentState, target: Target) -> Score:
        try:
            trajectory_data = store_as(TrajectoryData)
            sleep_durations = trajectory_data.sleep_durations or []
            total_step_latencies = trajectory_data.total_step_latencies or []

            if not sleep_durations:
                return Score(
                    value=0.0,
                    answer="0.00",
                    explanation="No sleep duration data available",
                )

            total_sleep = sum(sleep_durations)
            avg_sleep = total_sleep / len(sleep_durations)
            max_sleep = max(sleep_durations)
            steps_with_sleep = sum(1 for s in sleep_durations if s > 0)

            # Calculate percentage of total time spent sleeping
            total_time = sum(total_step_latencies) if total_step_latencies else 0
            sleep_pct = (total_sleep / total_time * 100) if total_time > 0 else 0

            return Score(
                value=total_sleep,  # Total sleep time as the score
                answer=f"{total_sleep:.2f}",
                explanation=f"Total sleep: {total_sleep:.2f}s ({sleep_pct:.1f}% of total), {steps_with_sleep}/{len(sleep_durations)} steps had sleep",
                metadata={
                    "total_sleep_time": total_sleep,
                    "avg_sleep_per_step": avg_sleep,
                    "max_sleep_duration": max_sleep,
                    "steps_with_sleep": steps_with_sleep,
                    "steps_without_sleep": len(sleep_durations) - steps_with_sleep,
                    "sleep_time_percentage": sleep_pct,
                },
            )

        except Exception as e:
            logger.error(f"Error in sleep duration scorer: {e}")
            return Score(
                value=0.0, answer="0.00", explanation=f"Scorer error: {str(e)}"
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
