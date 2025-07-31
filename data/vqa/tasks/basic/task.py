from inspect_ai import task, Task
from inspect_ai.solver import system_message

from data.vqa.dataset import raw_blueprint_dataset
from data.vqa.tasks.basic.solver import generate_entity_name_questions, generate_position_questions, generate_counting_questions
from data.vqa.common_solvers import validate_qa_answerability, generate_direction_questions, normalize_position_format, attach_bounding_box


@task
def basic_entity_name_task(questions_per_blueprint: int = 3) -> Task:
    """
    Basic VQA task: Given a position, predict the entity name.
    
    This task generates questions asking what entity is at a specific position.
    It's the most fundamental VQA task for blueprint understanding.
    
    Args:
        questions_per_blueprint: Number of entity name questions to generate per blueprint
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message("""You are analyzing Factorio blueprints to identify entities. 
                Answer questions about what entities are located at specific positions."""),
            attach_bounding_box(),
            generate_entity_name_questions(questions_per_blueprint=questions_per_blueprint),
            generate_direction_questions(),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,  # We're generating data, not scoring
    )


@task
def basic_position_task(questions_per_blueprint: int = 3) -> Task:
    """
    Basic VQA task: Given an entity name, predict its position.
    
    This task generates questions asking where a specific entity is located.
    It's the inverse of the entity name task.
    
    Args:
        questions_per_blueprint: Number of position questions to generate per blueprint
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message("""You are analyzing Factorio blueprints to locate entities. 
                Answer questions about where specific entities are positioned."""),
            attach_bounding_box(),
            generate_position_questions(questions_per_blueprint=questions_per_blueprint),
            generate_direction_questions(),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,  # We're generating data, not scoring
    )


@task
def basic_counting_task(questions_per_blueprint: int = 2) -> Task:
    """
    Basic VQA task: Count entities of a specific type in the blueprint.
    
    This task generates questions asking how many entities of a given type
    are present in the blueprint.
    
    Args:
        questions_per_blueprint: Number of counting questions to generate per blueprint
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message("""You are analyzing Factorio blueprints to count entities. 
                Answer questions about how many entities of each type are present."""),
            attach_bounding_box(),
            generate_counting_questions(questions_per_blueprint=questions_per_blueprint),
            generate_direction_questions(),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,  # We're generating data, not scoring
    )


@task
def comprehensive_basic_task(entity_questions: int = 2,
                             position_questions: int = 2,
                             counting_questions: int = 1,
                             direction_questions: int = 2) -> Task:
    """
    Comprehensive basic VQA task combining all basic question types.
    
    This task generates entity name, position, and counting questions for each blueprint.
    
    Args:
        entity_questions: Number of entity name questions per blueprint
        position_questions: Number of position questions per blueprint  
        counting_questions: Number of counting questions per blueprint
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message("""You are analyzing Factorio blueprints. Answer questions about 
                entity names, positions, and counts accurately and concisely."""),
            attach_bounding_box(),
            generate_entity_name_questions(questions_per_blueprint=entity_questions),
            generate_position_questions(questions_per_blueprint=position_questions),
            generate_counting_questions(questions_per_blueprint=counting_questions),
            generate_direction_questions(questions_per_blueprint=direction_questions),
            normalize_position_format(),
            validate_qa_answerability(), # Optional: The data will be more expensive, but better
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

    # Example: Run a denoising task
    results = eval(
        tasks=[comprehensive_basic_task()],
        model=model,
        limit=20,
        log_dir="../../logs",
        hooks=[VQAPairsHook()]
    )

    pass