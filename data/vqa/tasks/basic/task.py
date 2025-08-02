from typing import List
from inspect_ai import task, Task
from inspect_ai.solver import system_message

from data.vqa.dataset import raw_blueprint_dataset, augmented_blueprint_dataset, augmented_blueprint_dataset_with_chunks
from data.vqa.tasks.basic.solver import generate_entity_name_questions, generate_position_questions, \
    generate_counting_questions
from data.vqa.common_solvers import validate_qa_answerability, generate_direction_questions, normalize_position_format, \
    attach_bounding_box, render_blueprint_image

# task.py - Refactored into separate task files

from typing import List
from inspect_ai import task, Task
from inspect_ai.solver import system_message

from data.vqa.dataset import raw_blueprint_dataset, augmented_blueprint_dataset
from data.vqa.tasks.basic.solver import (
    generate_entity_name_questions,
    generate_position_questions,
    generate_counting_questions
)
from data.vqa.common_solvers import (
    validate_qa_answerability,
    generate_direction_questions,
    normalize_position_format,
    attach_bounding_box,
    render_blueprint_image
)

# Main tasks module - imports all task definitions from subdirectories
from inspect_ai import eval

# Import all tasks from the task modules
from data.vqa.tasks import *
from data.vqa.hook import *


# ============= ENTITY NAME TASKS =============

@task
def entity_name_task(questions_per_blueprint: int = 10, multiple_choice: bool = False) -> Task:
    """
    Entity name task with rotation augmentation.

    Args:
        questions_per_blueprint: Number of questions to generate per blueprint
        multiple_choice: If True, generate multiple choice questions
    """
    return Task(
        name="entity_name_task" + ("_mc" if multiple_choice else ""),
        dataset=augmented_blueprint_dataset_with_chunks(),
        solver=[
            system_message("""You are analyzing Factorio blueprints to identify entities. 
                Answer questions about what entities are located at specific positions.
                The blueprints may be rotated."""),
            attach_bounding_box(),
            render_blueprint_image(),
            generate_entity_name_questions(
                questions_per_blueprint=questions_per_blueprint,
                multiple_choice=multiple_choice
            ),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,
    )


@task
def entity_name_mc_task(questions_per_blueprint: int = 10) -> Task:
    """
    Entity name task with multiple choice questions.
    Convenience function that calls entity_name_task with multiple_choice=True.
    """
    return entity_name_task(questions_per_blueprint=questions_per_blueprint, multiple_choice=True)


# ============= POSITION TASKS =============

@task
def position_task(questions_per_blueprint: int = 10, multiple_choice: bool = False) -> Task:
    """
    Position task with rotation augmentation.

    Args:
        questions_per_blueprint: Number of questions to generate per blueprint
        multiple_choice: If True, generate multiple choice questions
    """
    return Task(
        name="position_task" + ("_mc" if multiple_choice else ""),
        dataset=augmented_blueprint_dataset_with_chunks(),
        solver=[
            system_message("""You are analyzing Factorio blueprints to locate entities. 
                Answer questions about where specific entities are positioned.
                The blueprints may be rotated."""),
            attach_bounding_box(),
            render_blueprint_image(),
            generate_position_questions(
                questions_per_blueprint=questions_per_blueprint,
                multiple_choice=multiple_choice
            ),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,
    )


@task
def position_mc_task(questions_per_blueprint: int = 10) -> Task:
    """
    Position task with multiple choice questions.
    Convenience function that calls position_task with multiple_choice=True.
    """
    return position_task(questions_per_blueprint=questions_per_blueprint, multiple_choice=True)


# ============= COUNTING TASKS =============

@task
def counting_task(questions_per_blueprint: int = 10, multiple_choice: bool = False) -> Task:
    """
    Counting task with rotation augmentation.

    Args:
        questions_per_blueprint: Number of questions to generate per blueprint
        multiple_choice: If True, generate multiple choice questions
    """
    return Task(
        name="counting_task" + ("_mc" if multiple_choice else ""),
        dataset=augmented_blueprint_dataset_with_chunks(),
        solver=[
            system_message("""You are analyzing Factorio blueprints to count entities. 
                Answer questions about how many entities of each type are present.
                The blueprints may be rotated."""),
            attach_bounding_box(),
            render_blueprint_image(),
            generate_counting_questions(
                questions_per_blueprint=questions_per_blueprint,
                multiple_choice=multiple_choice
            ),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,
    )


@task
def counting_mc_task(questions_per_blueprint: int = 10) -> Task:
    """
    Counting task with multiple choice questions.
    Convenience function that calls counting_task with multiple_choice=True.
    """
    return counting_task(questions_per_blueprint=questions_per_blueprint, multiple_choice=True)


# ============= DIRECTION TASKS =============

@task
def direction_task(questions_per_blueprint: int = 10, multiple_choice: bool = False) -> Task:
    """
    Direction task with rotation augmentation.

    Args:
        questions_per_blueprint: Number of questions to generate per blueprint
        multiple_choice: If True, generate multiple choice questions
    """
    # Note: You'll need to update generate_direction_questions in common_solvers
    # to support multiple_choice parameter if you want this functionality
    return Task(
        name="direction_task" + ("_mc" if multiple_choice else ""),
        dataset=augmented_blueprint_dataset_with_chunks(),
        solver=[
            system_message("""You are analyzing Factorio blueprints to identify entity directions. 
                Answer questions about which direction entities are facing.
                The blueprints may be rotated."""),
            attach_bounding_box(),
            render_blueprint_image(),
            generate_direction_questions(
                questions_per_blueprint=questions_per_blueprint,
                # multiple_choice=multiple_choice  # Uncomment when implemented
            ),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,
    )


@task
def direction_mc_task(questions_per_blueprint: int = 10) -> Task:
    """
    Direction task with multiple choice questions.
    Currently returns regular direction task - update when MC support is added.
    """
    # For now, return regular task until multiple choice is implemented for directions
    return direction_task(questions_per_blueprint=questions_per_blueprint)



# ============= USAGE EXAMPLES =============

if __name__ == "__main__":
    from inspect_ai import eval

    model = ["anthropic/claude-sonnet-4-20250514"]

    # Example 1: Run open-ended questions
    # open_ended_tasks = [
    #     entity_name_task(questions_per_blueprint=10, multiple_choice=False),
    #     position_task(questions_per_blueprint=10, multiple_choice=False),
    #     counting_task(questions_per_blueprint=10, multiple_choice=False),
    #     direction_task(questions_per_blueprint=10),
    # ]

    # Example 2: Run multiple choice questions
    multiple_choice_tasks = [
        entity_name_mc_task(questions_per_blueprint=2),
        position_mc_task(questions_per_blueprint=2),
        counting_mc_task(questions_per_blueprint=10),
        direction_mc_task(questions_per_blueprint=10),  # When implemented
    ]

    # Example 3: Mix and match
    # mixed_tasks = [
    #     entity_name_task(questions_per_blueprint=5, multiple_choice=False),
    #     entity_name_mc_task(questions_per_blueprint=5),
    #     position_mc_task(questions_per_blueprint=10),
    #     counting_task(questions_per_blueprint=10, multiple_choice=False),
    # ]

    # Run evaluation
    results = eval(
        tasks=multiple_choice_tasks,  # Choose which task set to run
        model=model,
        limit=2,
        log_dir="../../logs/multiple_choice_tasks"
    )