# In solvers.py
import json
import random
import re

from inspect_ai.model import ChatMessageUser
from inspect_ai.solver import Solver, solver, TaskState, Generate

from fle.agents.data.screenshots_from_run import create_factorio_instance
from fle.commons.models.rendered_image import RenderedImage
from .templates import Templates


@solver
def generate_blueprint_title_and_purpose() -> Solver:
    """Generate both title and purpose description for blueprints."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})

        # Generate prompt using Jinja2 template
        prompt = Templates.blueprint_title_purpose(blueprint=blueprint)

        state.messages[-1] = ChatMessageUser(content=prompt)

        response = await generate(state)

        completion = response.output.completion

        pattern = r"```json\s*\n(.*?)\n```"
        match = re.search(pattern, completion, re.DOTALL)
        if match:
            json_content = match.group(1)
            data = json.loads(json_content)
            title = data.get("title")
            purpose = data.get("purpose")

            state.metadata["title"] = title
            state.metadata["purpose"] = purpose

        return state

    return solve


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
            question_prompt = Templates.denoising_question(
                position=position, entity_name=entity_name
            )

            state.messages = [ChatMessageUser(content=question_prompt)]
            question_response = await generate(state)
            question = question_response.output.completion.strip()

            # Generate the answer
            answer = entity_name

            # Create QA pair
            qa_pair = {
                "question": question,
                "answer": answer,
                "removed_entity": removed_entity,
                "position": position,
                "modified_blueprint": modified_blueprint,
            }

            qa_pairs.append(qa_pair)

        # Store all QA pairs in metadata
        state.metadata["qa_pairs"] = qa_pairs
        state.metadata["num_qa_pairs"] = len(qa_pairs)

        return state

    return solve


@solver
def validate_denoising_qa() -> Solver:
    """
    Solver that validates if another model can answer the denoising questions correctly.
    This should be run after entity_removal_denoising.
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        qa_pairs = state.metadata.get("qa_pairs", [])
        if not qa_pairs:
            state.metadata["error"] = "No QA pairs found"
            return state

        validated_pairs = []

        for qa_pair in qa_pairs:
            # Prepare validation prompt using template
            validation_prompt = Templates.denoising_validation(
                modified_blueprint=qa_pair["modified_blueprint"],
                question=qa_pair["question"],
            )

            # Clear messages and ask the validation model
            state.messages = [ChatMessageUser(content=validation_prompt)]

            validation_response = await generate(state)
            predicted_answer = validation_response.output.completion.strip().lower()

            # Check if the answer is correct
            correct_answer = qa_pair["answer"].lower()
            is_correct = (
                correct_answer in predicted_answer or predicted_answer in correct_answer
            )

            # Add validation result to QA pair
            validated_qa = qa_pair.copy()
            validated_qa["validation_result"] = {
                "predicted": predicted_answer,
                "correct": correct_answer,
                "is_correct": is_correct,
            }

            validated_pairs.append(validated_qa)

        state.metadata["qa_pairs"] = validated_pairs
        state.metadata["validation_complete"] = True

        return state

    return solve


@solver
def generate_spatial_context_question() -> Solver:
    """
    Alternative solver that generates more complex spatial reasoning questions
    for each QA pair that was already generated.
    """
    instance = create_factorio_instance()

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        qa_pairs = state.metadata.get("qa_pairs", [])
        if not qa_pairs:
            # Run entity removal first if not done
            removal_solver = entity_removal_denoising()
            state = await removal_solver(state, generate)
            qa_pairs = state.metadata.get("qa_pairs", [])

        spatial_qa_pairs = []

        for qa_pair in qa_pairs:
            removed_entity = qa_pair["removed_entity"]
            modified_blueprint = qa_pair["modified_blueprint"]
            entities = modified_blueprint.get("entities", [])

            # Find nearby entities for spatial context
            removed_pos = removed_entity.get("position", {})
            rx, ry = removed_pos.get("x", 0), removed_pos.get("y", 0)

            nearby_entities = []
            for entity in entities:
                pos = entity.get("position", {})
                ex, ey = pos.get("x", 0), pos.get("y", 0)
                distance = abs(ex - rx) + abs(ey - ry)  # Manhattan distance
                if distance <= 5:  # Within 5 tiles
                    nearby_entities.append(
                        {
                            "entity": entity,
                            "distance": distance,
                            "relative_x": ex - rx,
                            "relative_y": ey - ry,
                        }
                    )

            # Sort by distance
            nearby_entities.sort(key=lambda x: x["distance"])

            # Generate spatial context question using template
            context_prompt = Templates.spatial_context_question(
                removed_entity=removed_entity,
                removed_position={"x": rx, "y": ry},
                nearby_entities=[
                    {
                        "name": ne["entity"].get("name"),
                        "relative_position": f"({ne['relative_x']}, {ne['relative_y']}) from missing entity",
                    }
                    for ne in nearby_entities[:3]
                ],
                nearest_entity_name=nearby_entities[0]["entity"].get("name")
                if nearby_entities
                else "nearest entity",
            )

            state.messages = [ChatMessageUser(content=context_prompt)]
            question_response = await generate(state)
            spatial_question = question_response.output.completion.strip()

            # Create enhanced QA pair with spatial question
            spatial_qa = qa_pair.copy()
            spatial_qa["spatial_question"] = spatial_question
            spatial_qa["nearby_entities"] = nearby_entities[:3]  # Keep top 3 nearest
            blueprint = state.metadata.get("blueprint", {})
            image: RenderedImage = instance.namespace._render(blueprint=blueprint)
            from data.vqa.image_utils import save_rendered_image

            image_id = save_rendered_image(
                image, blueprint, state.metadata, "spatial_qa", "../../images"
            )
            spatial_qa["image"] = image_id

            spatial_qa_pairs.append(spatial_qa)

        # Update QA pairs with spatial questions
        state.metadata["qa_pairs"] = spatial_qa_pairs
        state.metadata["spatial_questions_added"] = True

        return state

    return solve
