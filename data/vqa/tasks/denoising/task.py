from inspect_ai import task, Task
from inspect_ai.solver import system_message

from data.vqa.dataset import raw_blueprint_dataset
from data.vqa.tasks.denoising.solver import entity_removal_denoising, validate_denoising_qa


@task
def denoising_blueprint_task(qa_pairs_per_blueprint: int = 5) -> Task:
    """
    Task that creates denoising QA pairs from blueprints.
    
    This task removes entities from blueprints and asks questions about what's missing.
    It's useful for training models to understand blueprint completeness and entity relationships.

    Args:
        qa_pairs_per_blueprint: Number of QA pairs to generate per blueprint (default: 5)
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message(
                """You are an expert at analyzing Factorio blueprints and identifying missing components."""),
            entity_removal_denoising(qa_pairs_per_blueprint=qa_pairs_per_blueprint),
        ],
        scorer=None,  # We're generating data, not scoring
    )


@task 
def denoising_validation_task(qa_pairs_per_blueprint: int = 5) -> Task:
    """
    Task that validates denoising QA pairs by testing if a model can answer them correctly.
    
    This task first generates denoising QA pairs, then validates them by having 
    a model attempt to answer the questions.
    
    Args:
        qa_pairs_per_blueprint: Number of QA pairs to generate per blueprint (default: 5)
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message(
                """You are an expert at analyzing Factorio blueprints and identifying missing components."""),
            entity_removal_denoising(qa_pairs_per_blueprint=qa_pairs_per_blueprint),
            validate_denoising_qa(),
        ],
        scorer=None,  # Custom scorer would evaluate validation accuracy
    )

# Main tasks module - imports all task definitions from subdirectories
from inspect_ai import eval

# Import all tasks from the task modules
from data.vqa.tasks import *
from data.vqa.hook import *

if __name__ == "__main__":
    model = ["anthropic/claude-opus-4-20250514"]

    # Example: Run a denoising task
    results = eval(
        tasks=denoising_validation_task(qa_pairs_per_blueprint=5),
        model=model,
        limit=1,
        log_dir="../../logs",
        hooks=[VQAPairsHook()]
    )

