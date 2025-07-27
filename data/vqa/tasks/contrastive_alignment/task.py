import random
from typing import Literal

from inspect_ai import task, Task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import includes
from inspect_ai.solver import system_message

from data.vqa.tasks.contrastive_alignment.dataset import raw_blueprint_dataset
from data.vqa.tasks.contrastive_alignment.solver import generate_blueprint_title_and_purpose
from fle.agents.data.screenshots_from_run import create_factorio_instance
from fle.commons.models.rendered_image import RenderedImage


@task
def contrastive_blueprint_labelling_task() -> Task:
    """
    For each blueprint, we run a solver to compute the following metadata for it:
    1. A descriptive label
    2. A descriptive purpose
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message("""You are an expert Factorio player analyzing blueprints. 
                Generate clear, concise titles and purpose descriptions that would help 
                other players understand what each blueprint does."""),
            generate_blueprint_title_and_purpose(),
        ],
        scorer=[includes()]
    )


def contrastive_alignment_dataset(*args,
                                  subset: Literal['title', 'purpose'],
                                  model="anthropic/claude-opus-4-20250514") -> MemoryDataset:
    """
    Task that creates contrastive image-text alignment questions.
    Given a blueprint image, the model must select the correct title/purpose from multiple options.

    Args:
        num_options: Number of options to present (default: 4)
    """
    instance = create_factorio_instance()
    # render = Render(None, FactorioNamespace(F, 1))
    result = eval(
        tasks=contrastive_blueprint_labelling_task(),
        limit=10,
        model=[model]
    )
    choices = []
    for s in result[0].samples:
        choices.append(s.metadata['title'] if subset == 'title' else s.metadata['purpose'])

    samples = []
    for s in result[0].samples:
        correct_answer = s.metadata['title'] if subset == 'title' else s.metadata['purpose']
        pre_existing_choices = choices.copy()
        pre_existing_choices.remove(correct_answer)

        other_options = random.sample(choices, 3)
        all_choices = [correct_answer] + other_options
        random.shuffle(all_choices)
        target = all_choices.index(correct_answer)

        image: RenderedImage = instance.namespace._render(blueprint=s.metadata['blueprint'])
        id = str(hash(str(s.metadata['blueprint'])))
        image.save(f"./{id}.jpg")
        files = {"image": id}
        input = "What is the best title for this blueprint?" if subset == 'title' else "What is the purpose of this blueprint?"
        sample = Sample(choices=all_choices, target=str(target), input=input, files=files)
        samples.append(sample)

    dataset = MemoryDataset(samples)

    return dataset


# Main tasks module - imports all task definitions from subdirectories
from inspect_ai import eval

# Import all tasks from the task modules
from data.vqa.tasks import *
from data.vqa.hook import *

if __name__ == "__main__":
    model = ["anthropic/claude-opus-4-20250514"]
    dataset = contrastive_alignment_dataset(subset="title")
    # Example: Run a denoising task
    results = eval(
        tasks=[],
        model=model,
        limit=1,
        log_dir="./logs",
        hooks=[VQAPairsHook()]
    )