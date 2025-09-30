import random
from inspect_ai.solver import Solver, solver, TaskState, Generate
from fle.agents.data.screenshots_from_run import create_factorio_instance
from fle.commons.models.rendered_image import RenderedImage


@solver
def entity_removal_denoising(qa_pairs_per_blueprint: int = 5) -> Solver:
    """
    Solver that:
    1. Loads a blueprint
    2. Generates multiple QA pairs by removing different entities
    3. Stores all QA pairs for the blueprint

    Args:
        qa_pairs_per_blueprint: Number of QA pairs to generate per blueprint
    """

    instance = create_factorio_instance()

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})

        # Initialize QA pairs list
        qa_pairs = []

        # Get entities from blueprint
        entities = blueprint.get("entities", [])
        if not entities:
            state.metadata["error"] = "No entities found in blueprint"
            state.metadata["qa_pairs"] = qa_pairs
            return state

        # Generate specified number of QA pairs
        num_pairs = min(qa_pairs_per_blueprint, len(entities))
        selected_indices = random.sample(range(len(entities)), num_pairs)

        for idx in selected_indices:
            removed_entity = entities[idx].copy()

            # Create modified blueprint with entity removed
            modified_blueprint = blueprint.copy()
            modified_blueprint["entities"] = [
                e for i, e in enumerate(entities) if i != idx
            ]

            # Store the modification details
            position = removed_entity.get("position", {})
            entity_name = removed_entity.get("name", "unknown")

            # Generate a question about the missing entity using template
            question = f"Name the missing entity at: Position(x={position['x']}, y={position['y']})"

            image: RenderedImage = instance.namespace._render(
                blueprint=modified_blueprint
            )
            from data.vqa.image_utils import save_rendered_image

            # Pass modification info to distinguish denoising variants
            modification_info = (
                f"denoising_removed_{removed_entity.get('name', 'unknown')}_{idx}"
            )
            image_id = save_rendered_image(
                image, modified_blueprint, state.metadata, modification_info
            )
            id = image_id

            # Generate the answer
            answer = entity_name

            # Create QA pair
            qa_pair = {
                "question": question,
                "answer": answer,
                "removed_entity": removed_entity,
                "position": position,
                "modified_blueprint": modified_blueprint,
                "image": id,
            }

            qa_pairs.append(qa_pair)

        # Store all QA pairs in metadata
        state.metadata["qa_pairs"] = qa_pairs
        state.metadata["num_qa_pairs"] = len(qa_pairs)

        return state

    return solve
