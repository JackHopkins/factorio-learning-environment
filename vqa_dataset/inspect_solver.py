"""
Inspect AI Solver for Factorio blueprint VQA tasks.
"""

import json
import base64
from pathlib import Path
from typing import Any, Dict, List, Optional

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, Dataset
from inspect_ai.solver import Solver, solver, TaskState, Generate
from inspect_ai.scorer import accuracy
from inspect_ai.model import ChatMessage, ChatMessageUser, ChatMessageAssistant

from vqa_dataset.blueprint_loader import Blueprint, BlueprintLoader
from vqa_dataset.question_generator import VQAExample, QuestionGenerator


@solver
def factorio_vqa_solver() -> Solver:
    """
    Solver for Factorio blueprint VQA tasks.
    
    This solver takes images of Factorio blueprints and their associated questions,
    then generates answers by analyzing the visual content.
    """
    
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        """
        Solve a single VQA example by analyzing the blueprint image and question.
        """
        # Extract the question from the input
        question = state.input_text
        
        # Get the image path from metadata if available
        image_path = state.metadata.get("image_path") if state.metadata else None
        
        # Create the prompt for the model
        system_prompt = """You are an expert at analyzing Factorio game blueprints. You will be shown an image of a Factorio blueprint and asked questions about it. 

Please analyze the image carefully and answer the question accurately. Focus on:
- Counting entities (buildings, belts, inserters, etc.)
- Identifying entity types and their purposes
- Understanding spatial relationships
- Recognizing factory patterns and setups

Your answers should be concise and precise. For counting questions, provide only the number. For yes/no questions, answer only 'yes' or 'no'. For identification questions, provide the specific name or category."""

        # Prepare messages
        messages = [
            ChatMessage(
                role="system",
                content=system_prompt
            )
        ]
        
        # Add the user message with the question
        user_content = f"Question: {question}"
        
        # If we have an image, include it in the message
        if image_path and Path(image_path).exists():
            # For now, we'll include the image path in the prompt
            # In a full implementation, you'd encode the image as base64
            user_content += f"\n\nImage: {image_path}"
            
            # TODO: Implement proper image encoding for vision models
            # with open(image_path, "rb") as f:
            #     image_data = base64.b64encode(f.read()).decode()
            #     user_content = [
            #         {"type": "text", "text": f"Question: {question}"},
            #         {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
            #     ]
        
        messages.append(ChatMessage(
            role="user",
            content=user_content
        ))
        
        # Generate response
        state.messages = messages
        state = await generate(state)
        
        return state
    
    return solve


def create_vqa_dataset(
    blueprints: Dict[str, Blueprint], 
    questions: List[VQAExample],
    rendered_images: Dict[str, str]
) -> Dataset:
    """
    Create an Inspect AI Dataset from VQA examples.
    """
    samples = []
    
    for question in questions:
        # Get the corresponding image path
        image_path = rendered_images.get(question.blueprint_name)
        
        # Create sample metadata
        metadata = {
            "blueprint_name": question.blueprint_name,
            "question_type": question.question_type,
            "image_path": image_path,
            **(question.metadata or {})
        }
        
        # Create the sample
        sample = Sample(
            input=question.question,
            target=question.answer,
            metadata=metadata
        )
        
        samples.append(sample)
    
    return Dataset(samples)


@task
def factorio_blueprint_vqa(
    blueprints_dir: str = "fle/agents/data/blueprints_to_policies/blueprints",
    max_blueprints: int = 50,
    questions_per_blueprint: int = 5,
    blueprint_subdirs: Optional[List[str]] = None
) -> Task:
    """
    Create a Factorio blueprint VQA task.
    
    Args:
        blueprints_dir: Directory containing blueprint JSON files
        max_blueprints: Maximum number of blueprints to process
        questions_per_blueprint: Number of questions to generate per blueprint
        blueprint_subdirs: Subdirectories to load blueprints from
    """
    
    # Default subdirectories
    if blueprint_subdirs is None:
        blueprint_subdirs = ['example', 'other']
    
    # Load blueprints
    loader = BlueprintLoader(blueprints_dir)
    blueprints = loader.load_all_blueprints(blueprint_subdirs)
    
    # Filter blueprints by complexity (avoid very large ones)
    blueprints = loader.filter_blueprints_by_complexity(
        blueprints, 
        min_entities=1, 
        max_entities=200
    )
    
    # Limit number of blueprints
    blueprint_items = list(blueprints.items())[:max_blueprints]
    blueprints = dict(blueprint_items)
    
    print(f"Loaded {len(blueprints)} blueprints for VQA task")
    
    # Generate questions
    generator = QuestionGenerator()
    questions = generator.generate_questions_batch(
        blueprints, 
        num_questions_per_blueprint=questions_per_blueprint
    )
    
    print(f"Generated {len(questions)} VQA questions")
    
    # For now, we'll create a mock rendered_images dict
    # In a full implementation, you'd render the blueprints first
    rendered_images = {name: f"rendered_images/{name.replace('/', '_').replace('.json', '.png')}" 
                      for name in blueprints.keys()}
    
    # Create dataset
    dataset = create_vqa_dataset(blueprints, questions, rendered_images)
    
    # Create and return the task
    return Task(
        dataset=dataset,
        solver=factorio_vqa_solver(),
        scorer=accuracy(),
        metadata={
            "description": "Factorio blueprint visual question answering task",
            "blueprints_count": len(blueprints),
            "questions_count": len(questions),
            "question_types": list(generator.question_templates.keys())
        }
    )


class FactorioBlueprintAnalyzer:
    """
    High-level analyzer for Factorio blueprints using Inspect AI.
    """
    
    def __init__(self, model_name: str = "anthropic/claude-3-5-sonnet-20241022"):
        self.model_name = model_name
        self.loader = None
        self.generator = None
    
    def setup(self, blueprints_dir: str):
        """Setup the analyzer with blueprint directory."""
        self.loader = BlueprintLoader(blueprints_dir)
        self.generator = QuestionGenerator()
    
    def analyze_blueprint(
        self, 
        blueprint: Blueprint, 
        blueprint_name: str,
        custom_questions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single blueprint and answer questions about it.
        """
        if custom_questions:
            # Use custom questions
            questions = [
                VQAExample(
                    question=q,
                    answer="",  # Will be filled by model
                    question_type="custom",
                    blueprint_name=blueprint_name
                )
                for q in custom_questions
            ]
        else:
            # Generate standard questions
            questions = self.generator.generate_questions_for_blueprint(
                blueprint, 
                blueprint_name,
                num_questions_per_type=2
            )
        
        # Analyze blueprint structure
        entity_counts = blueprint.get_entity_counts()
        dimensions = blueprint.get_dimensions()
        bounding_box = blueprint.get_bounding_box()
        
        analysis = {
            "blueprint_name": blueprint_name,
            "entity_counts": dict(entity_counts),
            "unique_entity_types": blueprint.get_unique_entity_types(),
            "total_entities": blueprint.get_total_entity_count(),
            "dimensions": {
                "width": dimensions[0],
                "height": dimensions[1]
            },
            "bounding_box": {
                "min_x": bounding_box[0],
                "min_y": bounding_box[1],
                "max_x": bounding_box[2],
                "max_y": bounding_box[3]
            },
            "questions_and_answers": [
                {
                    "question": q.question,
                    "answer": q.answer,
                    "question_type": q.question_type
                }
                for q in questions
            ]
        }
        
        return analysis
    
    def run_evaluation(
        self, 
        blueprints_dir: str,
        output_file: Optional[str] = None,
        max_blueprints: int = 10
    ) -> Dict[str, Any]:
        """
        Run a full evaluation on multiple blueprints.
        """
        self.setup(blueprints_dir)
        
        # Load and filter blueprints
        blueprints = self.loader.load_all_blueprints(['example', 'other'])
        blueprints = self.loader.filter_blueprints_by_complexity(
            blueprints, max_entities=100
        )
        
        # Limit to max_blueprints
        blueprint_items = list(blueprints.items())[:max_blueprints]
        
        results = []
        for name, blueprint in blueprint_items:
            try:
                analysis = self.analyze_blueprint(blueprint, name)
                results.append(analysis)
                print(f"Analyzed blueprint: {name}")
            except Exception as e:
                print(f"Failed to analyze {name}: {e}")
        
        evaluation_results = {
            "total_blueprints": len(results),
            "blueprints": results,
            "statistics": self.loader.get_blueprint_statistics(dict(blueprint_items))
        }
        
        # Save results if output file specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(evaluation_results, f, indent=2)
            print(f"Saved results to {output_file}")
        
        return evaluation_results


# Example usage and testing
if __name__ == "__main__":
    # Test the analyzer
    analyzer = FactorioBlueprintAnalyzer()
    
    try:
        results = analyzer.run_evaluation(
            "fle/agents/data/blueprints_to_policies/blueprints",
            output_file="vqa_dataset/evaluation_results.json",
            max_blueprints=5
        )
        
        print(f"Evaluation completed successfully!")
        print(f"Analyzed {results['total_blueprints']} blueprints")
        
        # Show some sample questions
        if results['blueprints']:
            sample_blueprint = results['blueprints'][0]
            print(f"\nSample questions for '{sample_blueprint['blueprint_name']}':")
            for qa in sample_blueprint['questions_and_answers'][:3]:
                print(f"Q: {qa['question']}")
                print(f"A: {qa['answer']}")
                print(f"Type: {qa['question_type']}")
                print()
                
    except Exception as e:
        print(f"Evaluation failed: {e}")
        import traceback
        traceback.print_exc()