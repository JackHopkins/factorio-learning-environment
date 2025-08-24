from inspect_ai import task, Task
from inspect_ai.solver import system_message

from data.vqa.common_solvers import attach_bounding_box
from data.vqa.dataset import augmented_blueprint_dataset
from data.vqa.tasks.blueprints.denoising.solver import entity_removal_denoising


@task
def simple_denoising_blueprint_task(qa_pairs_per_blueprint: int = 5) -> Task:
    """
    Task that creates denoising QA pairs from blueprints.
    
    This task removes entities from blueprints and asks questions about what's missing.
    It's useful for training models to understand blueprint completeness and entity relationships.

    Args:
        qa_pairs_per_blueprint: Number of QA pairs to generate per blueprint (default: 5)
    """
    return Task(
        dataset=augmented_blueprint_dataset(),
        solver=[
            system_message(
                """You are an expert at analyzing Factorio blueprints and identifying missing components."""),
            attach_bounding_box(),
            entity_removal_denoising(qa_pairs_per_blueprint=qa_pairs_per_blueprint),
        ],
        scorer=None,  # We're generating data, not scoring
    )


# Main tasks module - imports all task definitions from subdirectories
from inspect_ai import eval

# Import all tasks from the task modules
from data.vqa.tasks import *
from data.vqa.hook import *

if __name__ == "__main__":
    model = ["anthropic/claude-sonnet-4-20250514"]

    # Example: Run a denoising task
    results = eval(
        tasks=simple_denoising_blueprint_task(qa_pairs_per_blueprint=10),
        model=model,
        limit=10,
        log_dir="../../logs",
        hooks=[VQAPairsHook()]
    )

