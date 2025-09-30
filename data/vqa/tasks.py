# ruff: noqa: F403

# Main tasks module - imports all task definitions from subdirectories
from inspect_ai import eval

# Import all tasks from the task modules
from data.vqa.tasks import *
from data.vqa.hook import *
from data.vqa.tasks.blueprints.spatial_reasoning.task import (
    spatial_reasoning_sandbox_task,
    spatial_context_sandbox_task,
)

if __name__ == "__main__":
    model = ["anthropic/claude-opus-4-20250514"]

    # Example: Run a denoising task
    results = eval(
        tasks=[
            spatial_reasoning_sandbox_task(questions_per_blueprint=20),
            spatial_context_sandbox_task(qa_pairs_per_blueprint=20),
            denoising_blueprint_task(qa_pairs_per_blueprint=20),
            denoising_validation_task(qa_pairs_per_blueprint=20),
            contrastive_alignment_task(),
        ],
        model=model,
        limit=1,
        log_dir="./logs",
        hooks=[VQAPairsHook()],
    )
