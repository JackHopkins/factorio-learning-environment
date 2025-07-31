from inspect_ai import task, Task
from inspect_ai.solver import system_message

from ...dataset import raw_blueprint_dataset
from .solver import generate_action_sequence, generate_next_action_questions, generate_construction_order_questions
from ...common_solvers import validate_qa_answerability, generate_direction_questions, normalize_position_format, attach_bounding_box


@task
def action_sequence_generation_task(max_actions: int = 10) -> Task:
    """
    Generate construction action sequences from blueprints.
    
    This task converts blueprints into imperative construction steps,
    creating a sequence of "place X at (y, z)" actions.
    
    Args:
        max_actions: Maximum number of construction actions to generate per blueprint
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message("""You are planning the construction sequence for a Factorio blueprint. 
                Convert the blueprint into a logical series of construction steps."""),
            generate_action_sequence(max_actions=max_actions),
        ],
        scorer=None,  # We're generating data, not scoring
    )


@task
def next_action_prediction_task(num_questions: int = 3) -> Task:
    """
    Action prediction VQA task: Predict the next action in a construction sequence.
    
    This task shows N-1 construction actions and asks the model to predict
    the Nth action. It tests understanding of construction logic and blueprints.
    
    Args:
        num_questions: Number of next-action prediction questions per blueprint
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message("""You are an expert at Factorio construction planning. 
                Given a sequence of construction actions, predict what the next logical 
                action should be based on the blueprint and construction principles."""),
            attach_bounding_box(),
            generate_action_sequence(max_actions=10),
            generate_next_action_questions(num_questions=num_questions),
            generate_direction_questions(),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,  # We're generating data, not scoring
    )


@task
def construction_order_task(num_questions: int = 2) -> Task:
    """
    Construction order VQA task: Determine optimal build order for entities.
    
    This task asks about the optimal order to construct multiple entities,
    considering dependencies and efficiency.
    
    Args:
        num_questions: Number of construction order questions per blueprint
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message("""You are an expert at Factorio construction planning. 
                Determine the optimal order to build entities considering power requirements, 
                dependencies, and construction efficiency."""),
            attach_bounding_box(),
            generate_construction_order_questions(num_questions=num_questions),
            generate_direction_questions(),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,  # We're generating data, not scoring
    )


@task
def comprehensive_action_task(max_actions: int = 8, next_action_questions: int = 2, order_questions: int = 1) -> Task:
    """
    Comprehensive action prediction task combining sequence generation and prediction.
    
    Args:
        max_actions: Maximum construction actions to generate
        next_action_questions: Number of next-action prediction questions
        order_questions: Number of construction order questions
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message("""You are an expert at Factorio construction and automation. 
                Plan construction sequences, predict next actions, and determine optimal 
                build orders for efficient factory construction."""),
            attach_bounding_box(),
            generate_action_sequence(max_actions=max_actions),
            generate_next_action_questions(num_questions=next_action_questions),
            generate_construction_order_questions(num_questions=order_questions),
            generate_direction_questions(),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,  # We're generating data, not scoring
    )



# Main tasks module - imports all task definitions from subdirectories
from inspect_ai import eval

# Import all tasks from the task modules
from data.vqa.tasks import *
from data.vqa.hook import *

if __name__ == "__main__":
    model = ["anthropic/claude-opus-4-20250514"]
    dataset = comprehensive_action_task(subset="title")
    # Example: Run a denoising task
    results = eval(
        tasks=[],
        model=model,
        limit=1,
        log_dir="./logs",
        hooks=[VQAPairsHook()]
    )