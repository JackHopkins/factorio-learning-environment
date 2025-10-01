# solver.py - Entity status question generation

import random

from inspect_ai.solver import Solver, solver, TaskState, Generate

from fle.env import EntityStatus


# Human-readable status descriptions
STATUS_DESCRIPTIONS = {
    EntityStatus.WORKING: "working",
    EntityStatus.NORMAL: "normal",
    EntityStatus.NO_POWER: "has no power",
    EntityStatus.LOW_POWER: "has low power",
    EntityStatus.NO_FUEL: "has no fuel",
    EntityStatus.EMPTY: "is empty",
    EntityStatus.NOT_PLUGGED_IN_ELECTRIC_NETWORK: "is not plugged into the electric network",
    EntityStatus.CHARGING: "is charging",
    EntityStatus.DISCHARGING: "is discharging",
    EntityStatus.FULLY_CHARGED: "is fully charged",
    EntityStatus.NO_RECIPE: "has no recipe set",
    EntityStatus.NO_INGREDIENTS: "has no ingredients",
    EntityStatus.NOT_CONNECTED: "is not connected",
    EntityStatus.NO_INPUT_FLUID: "has no input fluid",
    EntityStatus.NO_RESEARCH_IN_PROGRESS: "has no research in progress",
    EntityStatus.NO_MINABLE_RESOURCES: "has no minable resources",
    EntityStatus.LOW_INPUT_FLUID: "has low input fluid",
    EntityStatus.FLUID_INGREDIENT_SHORTAGE: "has a fluid ingredient shortage",
    EntityStatus.FULL_OUTPUT: "has full output",
    EntityStatus.FULL_BURNT_RESULT_OUTPUT: "has full burnt result output",
    EntityStatus.ITEM_INGREDIENT_SHORTAGE: "has an item ingredient shortage",
    EntityStatus.MISSING_REQUIRED_FLUID: "is missing required fluid",
    EntityStatus.MISSING_SCIENCE_PACKS: "is missing science packs",
    EntityStatus.WAITING_FOR_SOURCE_ITEMS: "is waiting for source items",
    EntityStatus.WAITING_FOR_SPACE_IN_DESTINATION: "is waiting for space in destination",
    EntityStatus.PREPARING_ROCKET_FOR_LAUNCH: "is preparing rocket for launch",
    EntityStatus.WAITING_TO_LAUNCH_ROCKET: "is waiting to launch rocket",
    EntityStatus.LAUNCHING_ROCKET: "is launching rocket",
    EntityStatus.NO_AMMO: "has no ammo",
    EntityStatus.LOW_TEMPERATURE: "has low temperature",
    EntityStatus.NOT_CONNECTED_TO_RAIL: "is not connected to rail",
}


@solver
def entity_status_questions(
    instance, questions_per_position: int = 5, multiple_choice: bool = True
) -> Solver:
    """
    Generate questions about entity statuses for entities in the rendered scene.
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        # Get entities from the renderer
        entities = state.metadata.get("entities", [])
        state.metadata.get("placed_entities", [])
        image_id = state.metadata.get("image")

        if not entities or not image_id:
            state.metadata["entity_status_questions"] = []
            return state

        questions = []

        # Filter entities that have interesting statuses (not just NORMAL/WORKING)
        entities_with_status = []
        for entity in entities:
            if hasattr(entity, "status") and entity.status:
                # Convert string status to EntityStatus enum if needed
                if isinstance(entity.status, str):
                    try:
                        status = EntityStatus.from_string(entity.status)
                    except:
                        continue
                else:
                    status = entity.status

                # Only include entities with non-normal statuses for more interesting questions
                if status not in [EntityStatus.NORMAL, EntityStatus.WORKING]:
                    entities_with_status.append(entity)

        # If we don't have enough entities with interesting statuses, include some normal ones
        if len(entities_with_status) < questions_per_position:
            normal_entities = [
                e
                for e in entities
                if hasattr(e, "status")
                and e.status in [EntityStatus.NORMAL, EntityStatus.WORKING]
            ]
            entities_with_status.extend(
                random.sample(
                    normal_entities,
                    min(
                        len(normal_entities),
                        questions_per_position - len(entities_with_status),
                    ),
                )
            )

        # Generate questions
        num_questions = min(questions_per_position, len(entities_with_status))
        selected_entities = (
            random.sample(entities_with_status, num_questions)
            if entities_with_status
            else []
        )

        for entity in selected_entities:
            # Get entity status
            if isinstance(entity.status, str):
                status = EntityStatus.from_string(entity.status)
            else:
                status = entity.status

            # Format entity name for display
            entity_display_name = entity.name.replace("-", " ")

            # Create position identifier
            position_str = f"at Position(x={entity.position.x}, y={entity.position.y})"

            if not multiple_choice:
                question = (
                    f"What is the status of the {entity_display_name} {position_str}?"
                )
                answer = STATUS_DESCRIPTIONS.get(status, status.value)

                qa_entry = {
                    "question": question,
                    "answer": answer,
                    "image": image_id,
                    "metadata": {
                        "entity_name": entity.name,
                        "entity_position": {
                            "x": entity.position.x,
                            "y": entity.position.y,
                        },
                        "entity_status": status.value,
                    },
                    "question_type": "open_ended",
                }
            else:
                # Generate status options for multiple choice
                # Include the correct status and 3 other random statuses
                all_statuses = list(STATUS_DESCRIPTIONS.keys())
                other_statuses = [s for s in all_statuses if s != status]

                # Select 3 distractors
                distractors = random.sample(other_statuses, min(3, len(other_statuses)))
                options = [status] + distractors
                random.shuffle(options)

                # Format with letters
                alphabet = ["a", "b", "c", "d"]
                option_strings = [
                    f"{alphabet[i]}) {STATUS_DESCRIPTIONS.get(opt, opt.value)}"
                    for i, opt in enumerate(options)
                ]

                # Find correct answer index
                correct_index = options.index(status)

                # Format question with options
                question = (
                    f"What is the status of the {entity_display_name} {position_str}?\n"
                    f"Provide the correct letter and nothing else.\n"
                    f"{chr(10).join(option_strings)}"
                )

                answer = alphabet[correct_index]

                qa_entry = {
                    "question": question,
                    "answer": answer,
                    "image": image_id,
                    "metadata": {
                        "entity_name": entity.name,
                        "entity_position": {
                            "x": entity.position.x,
                            "y": entity.position.y,
                        },
                        "entity_status": status.value,
                        "options": [s.value for s in options],
                        "correct_index": correct_index,
                    },
                    "question_type": "multiple_choice",
                }

            questions.append(qa_entry)

        # Store the questions in metadata
        state.metadata["entity_status_questions"] = questions

        return state

    return solve
