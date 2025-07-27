import json
import random
from inspect_ai.model import ChatMessageUser
from inspect_ai.solver import Solver, solver, TaskState, Generate
from data.vqa.templates import Templates
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
            modified_blueprint["entities"] = [e for i, e in enumerate(entities) if i != idx]

            # Store the modification details
            position = removed_entity.get("position", {})
            entity_name = removed_entity.get("name", "unknown")

            # Generate a question about the missing entity using template
            question_prompt = Templates.denoising_question(
                position=position,
                entity_name=entity_name
            )

            state.messages = [ChatMessageUser(content=question_prompt)]
            question_response = await generate(state)
            question = question_response.output.completion.strip("\"")

            image: RenderedImage = instance.namespace._render(blueprint=blueprint)
            id = str(hash(str(blueprint)))
            image.save(f"./{id}.jpg")

            # Generate the answer
            answer = entity_name

            # Create QA pair
            qa_pair = {
                "question": question,
                "answer": answer,
                "removed_entity": removed_entity,
                "position": position,
                "modified_blueprint": modified_blueprint,
                "image": id
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
                modified_blueprint=qa_pair['modified_blueprint'],
                question=qa_pair['question']
            )

            # Clear messages and ask the validation model
            state.messages = [ChatMessageUser(content=validation_prompt)]

            validation_response = await generate(state)
            predicted_answer = validation_response.output.completion.strip().lower()

            # Check if the answer is correct
            correct_answer = qa_pair['answer'].lower()
            is_correct = correct_answer in predicted_answer or predicted_answer in correct_answer

            # Add validation result to QA pair
            validated_qa = qa_pair.copy()
            validated_qa["validation_result"] = {
                "predicted": predicted_answer,
                "correct": correct_answer,
                "is_correct": is_correct
            }

            validated_pairs.append(validated_qa)

        state.metadata["qa_pairs"] = validated_pairs
        state.metadata["validation_complete"] = True

        return state

    return solve