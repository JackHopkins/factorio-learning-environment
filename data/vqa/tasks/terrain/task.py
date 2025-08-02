# task.py - Refactored into separate task files

from inspect_ai import task, Task
from inspect_ai.solver import system_message

from data.vqa.common_solvers import (
    normalize_position_format,
    attach_bounding_box
)
# Import all tasks from the task modules
from data.vqa.tasks.terrain.dataset import raw_position_dataset
from data.vqa.tasks.terrain.solver import generate_terrain_questions

@task
def terrain_task() -> Task:
    """
    Entity name task with rotation augmentation.

    Args:
        questions_per_blueprint: Number of questions to generate per blueprint
        multiple_choice: If True, generate multiple choice questions
    """
    multiple_choice = False
    return Task(
        name="terrain_task",
        dataset=raw_position_dataset(),
        solver=[
            system_message("""You are analyzing Factorio blueprints to identify entities. 
                Answer questions about what entities are located at specific positions.
                The blueprints may be rotated."""),
            attach_bounding_box(),
            #render_blueprint_image(),
            generate_terrain_questions(
                multiple_choice=multiple_choice
            ),
            normalize_position_format(),
        ],
        scorer=None,
    )

if __name__ == "__main__":
    from inspect_ai import eval

    model = ["anthropic/claude-sonnet-4-20250514"]

    # Run evaluation
    results = eval(
        tasks=[terrain_task],  # Choose which task set to run
        model=model,
        limit=10,
        log_dir="../../logs/"
    )