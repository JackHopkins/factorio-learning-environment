# Main tasks module - imports all task definitions from subdirectories
from inspect_ai import eval

# Import all tasks from the task modules
from data.vqa.tasks import *
from data.vqa.hook import *

if __name__ == "__main__":
    model = ["anthropic/claude-opus-4-20250514"]
    
    # Example: Run a denoising task
    results = eval(
        tasks=contrastive_alignment_task(),
        model=model,
        limit=1,
        log_dir="./logs",
        hooks=[VQAPairsHook()]
    )