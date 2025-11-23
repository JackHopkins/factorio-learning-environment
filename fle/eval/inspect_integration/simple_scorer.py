"""Simple scorer for testing Inspect integration."""

from inspect_ai.scorer import scorer, Score, Target, Scorer, accuracy
from inspect_ai.agent import AgentState
from inspect_ai.util import store_as

# Import the typed models from the controlled solver
from fle.eval.inspect_integration.controlled_solver import TrajectoryData


@scorer(metrics=[accuracy()])
def simple_production_score() -> Scorer:
    """Simple scorer function for production evaluation"""

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
