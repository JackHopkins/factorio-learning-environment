import random
from typing import Literal

from inspect_ai import task, Task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import includes
from inspect_ai.solver import system_message

from data.vqa.common_solvers import validate_qa_answerability, generate_direction_questions, normalize_position_format, \
    attach_bounding_box, render_blueprint_image
from data.vqa.dataset import augmented_blueprint_dataset
from data.vqa.tasks.contrastive_alignment.solver import generate_blueprint_title_and_purpose
from fle.agents.data.screenshots_from_run import create_factorio_instance
from fle.commons.models.rendered_image import RenderedImage
from inspect_ai.solver import Solver, solver, TaskState, Generate


@task
def contrastive_blueprint_labelling_task(num_variations: int = 3) -> Task:
    """
    For each blueprint, we run a solver to compute multiple variations of metadata:
    1. Descriptive labels
    2. Descriptive purposes

    Args:
        num_variations: Number of title/purpose variations to generate per blueprint
    """
    return Task(
        dataset=augmented_blueprint_dataset(),
        solver=[
            system_message("""You are an expert Factorio player analyzing blueprints. 
                Generate clear, concise titles and purpose descriptions that would help 
                other players understand what each blueprint does."""),
            attach_bounding_box(),
            # Use the efficient single-prompt version
            generate_blueprint_title_and_purpose(num_variations=num_variations)
        ],
        scorer=[includes()]
    )


@solver
def passthrough_solver():
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        question = state.input
        answer = state.target.text
        alphabet = ['A', 'B', 'C', 'D', 'E']
        choices = [choice.value for choice in state.choices._choices]
        random.shuffle(choices)
        options = "\n".join([f"{alphabet[i]}) {choice}" for i, choice in enumerate(choices)])
        question = question + "\n" + options

        answer_index = choices.index(answer)
        target = alphabet[answer_index]
        state.metadata['contrastive_alignment'] = [{'answer': target, 'question': question}]
        return state

    return solve


@task
def contrastive_alignment_task(subset: Literal['title', 'purpose'] = "title", limit=4, variants=1) -> Task:
    """
    For each blueprint, we run a solver to compute the following metadata for it:
    1. A descriptive label
    2. A descriptive purpose
    """
    dataset = contrastive_alignment_dataset(
        subset=subset,
        limit=limit,
        num_variations=variants  # This will create 3 different titles per blueprint
    )
    return Task(
        name=f"contrastive_alignment_{subset}",
        dataset=dataset,
        solver=[
            render_blueprint_image(),
            passthrough_solver()
        ],
        scorer=[]
    )


def contrastive_alignment_dataset(*args,
                                  subset: Literal['title', 'purpose'],
                                  limit=10,
                                  num_variations=3,
                                  model="anthropic/claude-opus-4-20250514") -> MemoryDataset:
    """
    Task that creates contrastive image-text alignment questions with multiple variations per blueprint.
    Given a blueprint image, the model must select the correct title/purpose from multiple options.

    Args:
        subset: Whether to use 'title' or 'purpose' for questions
        limit: Number of blueprints to process
        num_variations: Number of title/purpose variations to generate per blueprint
        model: Model to use for generation
    """
    instance = create_factorio_instance()
    result = eval(
        tasks=contrastive_blueprint_labelling_task(num_variations=num_variations),
        limit=limit,
        model=[model]
    )

    # Remove duplicates while preserving order
    all_titles = []
    all_purposes = []
    for s in result[0].samples:
        all_titles.append(s.metadata.get('titles', []))
        all_purposes.append(s.metadata.get('purposes', []))



    samples = []
    for i, s in enumerate(result[0].samples):
        # Get the variations for this blueprint
        variations = s.metadata.get('titles' if subset == 'title' else 'purposes', [])
        all_choices = []
        try:
            while len(all_choices) < 3:
                sample_index = random.randint(0, len(all_titles))
                if sample_index != i:
                    if subset == 'title':
                        all_choices.append(random.choice(all_titles[sample_index]))
                    else:
                        all_choices.append(random.choice(all_purposes[sample_index]))
        except IndexError:
            continue


        # Create multiple samples per blueprint using different variations
        for variation_idx, correct_answer in enumerate(variations):
            # Skip if this variation is empty
            if not correct_answer:
                continue

            # Create distractor options from other blueprints' variations
            distractors = [choice for choice in all_choices if choice != correct_answer]

            # Sample 3 distractors
            if len(distractors) >= 3:
                other_options = random.sample(distractors, 3)
            else:
                # If not enough distractors, use what we have and add dummy options
                other_options = distractors.copy()
                dummy_options = [
                    "Belt Balancer System" if subset == 'title' else "Distributes items evenly across multiple belt lanes",
                    "Automated Train Station" if subset == 'title' else "Loading and unloading point for trains with circuit control",
                    "Steam Power Plant" if subset == 'title' else "Generates electricity using steam engines and boilers"
                ]
                while len(other_options) < 3 and dummy_options:
                    other_options.append(dummy_options.pop(0))

            all_choices_for_question = [correct_answer] + other_options
            random.shuffle(all_choices_for_question)

            try:
                image: RenderedImage = instance.namespace._render(blueprint=s.metadata['blueprint'])
                from data.vqa.image_utils import save_rendered_image
                # Add variation index to image ID to make it unique
                image_id = save_rendered_image(
                    image,
                    s.metadata['blueprint'],
                    {**s.metadata, 'variation_idx': variation_idx},
                    f"contrastive_v{variation_idx}",
                    "../../images"
                )
                files = {"image": image_id}
            except Exception as e:
                print(f"Error rendering blueprint: {e}")
                continue

            input_text = (
                "What is the best title for this blueprint?"
                if subset == 'title'
                else "What is the purpose of this blueprint?"
            )

            sample = Sample(
                choices=all_choices_for_question,
                target=str(correct_answer),
                input=input_text,
                files=files,
                metadata={
                    **s.metadata,
                    'variation_idx': variation_idx,
                    'total_variations': len(variations)
                }
            )
            samples.append(sample)

    dataset = MemoryDataset(samples)
    return dataset


# Main tasks module - imports all task definitions from subdirectories
from inspect_ai import eval

# Import all tasks from the task modules
from data.vqa.tasks import *
from data.vqa.hook import *

if __name__ == "__main__":
    model = ["anthropic/claude-sonnet-4-20250514"]

    # Run evaluation
    results = eval(
        tasks=[contrastive_alignment_task(limit=3, subset='title'),
               contrastive_alignment_task(limit=5, subset='purpose')],
        model=model,
        limit=3,
        log_dir="./../logs",
        hooks=[VQAPairsHook()]
    )