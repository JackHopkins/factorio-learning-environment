from importlib.metadata import metadata

from inspect_ai import task, Task
from inspect_ai.solver import system_message

from data.vqa.dataset import raw_blueprint_dataset
from data.vqa.tasks.spatial_reasoning.solver import (
    generate_spatial_reasoning_with_code,
    generate_spatial_context_with_code
)
from inspect_ai.tool import bash, python
from data.vqa.tasks.denoising.solver import entity_removal_denoising
from inspect_ai.solver import use_tools
from inspect_ai.util import sandbox
from data.vqa.common_solvers import validate_qa_answerability, convert_directions_to_compass, normalize_position_format

from data.vqa.hook import VQAPairsHook


@task
def spatial_reasoning_sandbox_task(questions_per_blueprint: int = 3) -> Task:
    """
    Spatial reasoning task using sandboxed Python execution.

    The agent writes Python code to analyze blueprints and generate
    diverse spatial reasoning questions. This allows for more complex
    analysis including pattern detection, clustering, and path finding.

    Args:
        questions_per_blueprint: Number of questions to generate per blueprint
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            use_tools([bash(), python()]),
            system_message("""You are an expert at spatial analysis in Factorio blueprints.
                You can write Python code to analyze entity positions, calculate distances,
                identify patterns, and generate creative spatial reasoning questions.

                Focus on:
                - Distance calculations (Manhattan, Euclidean)
                - Directional relationships (north/south/east/west)
                - Spatial patterns (lines, grids, clusters)
                - Relative positions and proximity
                - Path finding and connectivity
                - Symmetry and alignment analysis

                Your code has access to the blueprint data and can use standard Python
                libraries for calculations."""),
            generate_spatial_reasoning_with_code(questions_per_blueprint=questions_per_blueprint),
            convert_directions_to_compass(),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        sandbox='docker',  # Use local Python sandbox
        scorer=None,
    )


@task
def spatial_context_sandbox_task(qa_pairs_per_blueprint: int = 5) -> Task:
    """
    Spatial context denoising task using sandboxed Python execution.

    The agent writes Python code to analyze spatial relationships
    around removed entities and generate context-aware questions.
    This enables sophisticated pattern analysis and spatial reasoning.

    Args:
        qa_pairs_per_blueprint: Number of QA pairs to generate
    """
    return Task(
        dataset=raw_blueprint_dataset(),
        solver=[
            use_tools([bash(), python()]),
            system_message("""You are an expert at spatial context analysis in Factorio.
                Write Python code to analyze spatial relationships around missing entities
                and generate questions that use spatial context to identify what's missing.

                Consider:
                - Nearby entity positions and types
                - Patterns that would be broken by the missing entity
                - Functional relationships (e.g., inserters need adjacent targets)
                - Symmetry and alignment in the layout
                - Connection patterns (belts, pipes, power)
                - Production flow and logistics

                Your code should identify sophisticated spatial patterns and generate
                questions that require understanding these relationships."""),
            entity_removal_denoising(qa_pairs_per_blueprint=qa_pairs_per_blueprint),
            generate_spatial_context_with_code(),
            convert_directions_to_compass(),
            normalize_position_format(),
            validate_qa_answerability(),
        ],
        sandbox='docker',
        scorer=None,
    )


"""
Example of using the spatial reasoning sandbox tasks
"""
from inspect_ai import eval
from data.vqa.tasks.spatial_reasoning.task import (
    spatial_reasoning_sandbox_task,
    spatial_context_sandbox_task
)

if __name__ == "__main__":
    # Example 1: Basic spatial reasoning with code generation
    print("Running spatial reasoning with Python code generation...")

    results = eval(
        tasks=spatial_reasoning_sandbox_task(questions_per_blueprint=20),
        #model=["anthropic/claude-opus-4-20250514"],  # or any other model
        model=["anthropic/claude-3-5-haiku-latest"],
        limit=2,  # Process 3 blueprints for testing
        log_dir="../../logs/spatial_sandbox",
        hooks=[VQAPairsHook()]
    )

    # Print some generated questions
    for sample in results[0].samples:
        if "spatial_questions" in sample.metadata:
            print("\nGenerated spatial questions:")
            for qa in sample.metadata["spatial_questions"][:2]:
                print(f"Q: {qa['question']}")
                print(f"A: {qa['answer']}")
                print()
                #if 'metadata' in qa:
                #    print(f"Metadata: {qa['metadata']}")

    # Example 2: Spatial context denoising with code
    print("\n\nRunning spatial context denoising with code generation...")

    results2 = eval(
        tasks=spatial_context_sandbox_task(qa_pairs_per_blueprint=20),
        model=["anthropic/claude-3-5-haiku-latest"],
        limit=2,
        log_dir="../../logs/spatial_context_sandbox",
        hooks=[VQAPairsHook()]
    )

    # Print
    for sample in results2[0].samples:
        queries = sample.metadata['spatial_questions'] if 'spatial_questions' in sample.metadata else []
        qa_pairs = sample.metadata['qa_pairs'] if 'qa_pairs' in sample.metadata else []
        combined = qa_pairs + queries
        pass