from inspect_ai import task, Task
from inspect_ai.solver import system_message

from ...dataset import raw_blueprint_dataset
from .solver import generate_throughput_questions, generate_bottleneck_questions, generate_optimization_questions
from ...common_solvers import validate_qa_answerability, generate_direction_questions, normalize_position_format, attach_bounding_box


@task
def throughput_prediction_task(num_questions: int = 2) -> Task:
    """
    Productivity planning VQA task: Predict production throughput after connecting entities.
    
    This task analyzes factory setups and predicts the resulting production
    throughput when entities are connected, considering bottlenecks and limits.
    
    Args:
        num_questions: Number of throughput questions to generate per blueprint
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message("""You are an expert at Factorio production planning and optimization. 
                Calculate production throughput, identify bottlenecks, and predict the effects 
                of connecting different entities in factory setups."""),
            attach_bounding_box(),
            generate_throughput_questions(num_questions=num_questions),
            generate_direction_questions(),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,  # We're generating data, not scoring
    )


@task
def bottleneck_analysis_task(num_questions: int = 2) -> Task:
    """
    Bottleneck analysis VQA task: Identify production bottlenecks and limitations.
    
    This task analyzes factory layouts to identify what limits production
    and suggests improvements.
    
    Args:
        num_questions: Number of bottleneck questions to generate per blueprint
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message("""You are analyzing Factorio factory efficiency. Identify 
                bottlenecks, production limits, and areas where throughput is constrained 
                by entity capabilities or layout design."""),
            attach_bounding_box(),
            generate_bottleneck_questions(num_questions=num_questions),
            generate_direction_questions(),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,  # We're generating data, not scoring
    )


@task
def optimization_planning_task(num_questions: int = 2) -> Task:
    """
    Optimization planning VQA task: Suggest improvements for factory efficiency.
    
    This task analyzes factory setups and suggests optimizations to improve
    production rates and efficiency.
    
    Args:
        num_questions: Number of optimization questions to generate per blueprint
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message("""You are a Factorio optimization expert. Analyze factory 
                layouts and suggest improvements to maximize production efficiency, 
                reduce bottlenecks, and optimize resource usage."""),
            attach_bounding_box(),
            generate_optimization_questions(num_questions=num_questions),
            generate_direction_questions(),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,  # We're generating data, not scoring
    )


@task
def comprehensive_productivity_task(throughput_questions: int = 2, bottleneck_questions: int = 1, 
                                  optimization_questions: int = 1) -> Task:
    """
    Comprehensive productivity planning task combining all productivity analysis types.
    
    Args:
        throughput_questions: Number of throughput questions per blueprint
        bottleneck_questions: Number of bottleneck questions per blueprint
        optimization_questions: Number of optimization questions per blueprint
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            system_message("""You are a comprehensive Factorio production expert. Analyze 
                factory setups for throughput calculation, bottleneck identification, and 
                optimization opportunities. Provide detailed insights into production 
                efficiency and improvement strategies."""),
            attach_bounding_box(),
            generate_throughput_questions(num_questions=throughput_questions),
            generate_bottleneck_questions(num_questions=bottleneck_questions), 
            generate_optimization_questions(num_questions=optimization_questions),
            generate_direction_questions(),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        scorer=None,  # We're generating data, not scoring
    )