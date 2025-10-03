import random
from inspect_ai.solver import Solver, solver, TaskState, Generate
from ....templates import Templates


@solver
def generate_action_sequence(max_actions: int = 10) -> Solver:
    """
    Generate a sequence of construction actions from a blueprint.

    This solver takes a blueprint and converts it into a sequence of imperative
    construction steps that could be used to build the blueprint.

    Args:
        max_actions: Maximum number of actions to generate per blueprint
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        entities = blueprint.get("entities", [])

        if not entities:
            state.metadata["error"] = "No entities found in blueprint"
            state.metadata["action_sequence"] = []
            return state

        # Sort entities by some construction order logic
        # For simplicity, sort by position (left to right, top to bottom)
        sorted_entities = sorted(
            entities,
            key=lambda e: (
                e.get("position", {}).get("y", 0),
                e.get("position", {}).get("x", 0),
            ),
        )

        actions = []

        for i, entity in enumerate(sorted_entities[:max_actions]):
            entity_name = entity.get("name", "unknown")
            position = entity.get("position", {})
            x, y = position.get("x", 0), position.get("y", 0)

            # Generate construction action
            action_types = [
                f"place {entity_name} at ({x}, {y})",
                f"build {entity_name} at position ({x}, {y})",
                f"construct {entity_name} at coordinates ({x}, {y})",
                f"install {entity_name} at location ({x}, {y})",
            ]

            action = random.choice(action_types)
            actions.append(
                {
                    "step": i + 1,
                    "action": action,
                    "entity": entity_name,
                    "position": position,
                }
            )

        state.metadata["action_sequence"] = actions
        state.metadata["total_actions"] = len(actions)

        return state

    return solve


@solver
def generate_next_action_questions(num_questions: int = 3) -> Solver:
    """
    Generate questions asking to predict the next action in a construction sequence.

    This solver uses the action sequence to create questions where N-1 actions
    are shown and the model must predict the Nth action.

    Args:
        num_questions: Number of next-action questions to generate
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        action_sequence = state.metadata.get("action_sequence", [])

        if len(action_sequence) < 2:
            state.metadata["error"] = "Not enough actions for next-action prediction"
            state.metadata["next_action_questions"] = []
            return state

        next_action_questions = []

        for _ in range(min(num_questions, len(action_sequence) - 1)):
            # Choose a random point in the sequence to split
            split_point = random.randint(1, len(action_sequence) - 1)

            previous_actions = action_sequence[:split_point]
            next_action = action_sequence[split_point]

            # Create the question using template
            previous_action_texts = [action["action"] for action in previous_actions]

            blueprint = state.metadata.get("blueprint", {})

            # Generate the question prompt
            prompt = Templates.action_prediction(
                previous_actions=previous_action_texts, blueprint=blueprint
            )

            answer = next_action["action"]

            next_action_questions.append(
                {
                    "previous_actions": previous_actions,
                    "next_action": next_action,
                    "question_prompt": prompt,
                    "answer": answer,
                    "split_point": split_point,
                }
            )

        state.metadata["next_action_questions"] = next_action_questions
        return state

    return solve


@solver
def generate_construction_order_questions(num_questions: int = 2) -> Solver:
    """
    Generate questions about the optimal construction order.

    Args:
        num_questions: Number of construction order questions to generate
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        entities = blueprint.get("entities", [])

        if len(entities) < 3:
            state.metadata["error"] = (
                "Not enough entities for construction order questions"
            )
            state.metadata["construction_order_questions"] = []
            return state

        construction_order_questions = []

        for _ in range(num_questions):
            # Select 3-4 random entities
            selected_entities = random.sample(entities, min(4, len(entities)))

            entity_names = [e.get("name", "unknown") for e in selected_entities]

            question_types = [
                f"What is the optimal order to build these entities: {', '.join(entity_names)}?",
                f"In what sequence should you construct: {', '.join(entity_names)}?",
                f"Which entity should be built first among: {', '.join(entity_names)}?",
                f"What is the recommended construction order for: {', '.join(entity_names)}?",
            ]

            question = random.choice(question_types)

            # Simple heuristic for construction order (power -> production -> logistics)
            priority_order = {
                "electric-pole": 1,
                "power-line": 1,
                "assembly-machine": 2,
                "furnace": 2,
                "electric-furnace": 2,
                "transport-belt": 3,
                "inserter": 3,
                "underground-belt": 3,
                "chest": 4,
                "pipe": 4,
            }

            # Sort by priority
            sorted_entities = sorted(
                selected_entities,
                key=lambda e: priority_order.get(
                    e.get("name", "unknown").split("-")[0], 5
                ),
            )

            answer = ", ".join([e.get("name", "unknown") for e in sorted_entities])

            construction_order_questions.append(
                {
                    "question": question,
                    "answer": answer,
                    "entities": selected_entities,
                    "entity_names": entity_names,
                }
            )

        state.metadata["construction_order_questions"] = construction_order_questions
        return state

    return solve
