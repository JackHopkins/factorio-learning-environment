"""Common solvers used across multiple VQA tasks."""

import json
import re
import random
from inspect_ai.model import ChatMessageUser
from inspect_ai.solver import Solver, solver, TaskState, Generate

from data.vqa.blueprint_transforms import detect_direction_system
from data.vqa.position_utils import normalize_position_references_in_qa
from data.vqa.bounding_box_utils import calculate_blueprint_bounding_box
from data.vqa.direction_utils import Direction
from fle.agents.data.screenshots_from_run import create_factorio_instance
from fle.commons.models.rendered_image import RenderedImage


@solver
def validate_qa_answerability() -> Solver:
    """
    Followup solver that validates if generated questions are answerable and unambiguous.
    
    This solver checks each generated Q&A pair to ensure:
    1. The question is clear and specific
    2. The answer directly addresses the question
    3. There's enough context to answer the question
    4. The question avoids ambiguity
    
    It will regenerate questions that fail validation.
    """
    
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        # Get all question fields from metadata
        question_fields = [
            "basic_questions", "position_questions", "counting_questions",
            "spatial_questions", "state_questions", "inventory_questions",
            "qa_pairs", "next_action_questions", "construction_order_questions",
            "throughput_questions", "bottleneck_questions", "optimization_questions",
            "direction_questions"
        ]
        blueprint = state.metadata['blueprint']
        
        for field in question_fields:
            if field not in state.metadata:
                continue
                
            questions = state.metadata[field]
            if not isinstance(questions, list):
                continue
                
            validated_questions = []
            
            for qa in questions:
                question = qa.get("question", "")
                answer = qa.get("answer", "")
                
                if not question or not answer:
                    continue
                
                # Create validation prompt
                validation_prompt = f"""You are validating a Visual Question Answering (VQA) pair for a Factorio blueprint analysis task.
                
Question: 
```
{question}
```
Answer: `{answer}`

Please evaluate if this Q&A pair meets the following criteria:

1. **Specificity**: Is the question specific enough that it has a single, unambiguous answer?
2. **Visual Answerability**: Can the question be answered by looking at a blueprint image?
3. **Clarity**: Is the question clearly worded without confusing terminology?
4. **Answer Match**: Does the provided answer directly and completely answer the question?
5. **Triviality/Tautology**: Is there actual informational content in the question? Or is it self-referential?

Common issues to check for:
- Vague positional references (e.g., "the inserter" when there are multiple)
- Unclear directional terms (using numbers instead of compass directions)
- Ambiguous entity references without specific positions
- Questions that require game knowledge beyond what's visible

If the Q&A pair has issues, provide a revised version that fixes them.

If the question includes multiple choice - it is critical that you keep them!

Return your response in this exact JSON format:
```json
{{
    "is_valid": true/false,
    "issues": ["list of specific issues if any"],
    "revised_question": "improved question if needed",
    "revised_answer": "improved answer if needed",
    "explanation": "brief explanation of changes"
}}
```"""

                # Validate the Q&A pair
                state.messages = [ChatMessageUser(content=validation_prompt)]
                response = await generate(state)
                
                try:
                    completion = response.output.completion
                    json_match = re.search(r'```json\s*\n(.*?)\n```', completion, re.DOTALL)
                    
                    if json_match:
                        validation_result = json.loads(json_match.group(1))
                        
                        if validation_result.get("is_valid", False):
                            # Keep original if valid
                            validated_questions.append(qa)
                        else:
                            # Use revised version
                            revised_qa = qa.copy()
                            revised_qa["question"] = validation_result.get("revised_question", question)
                            revised_qa["answer"] = validation_result.get("revised_answer", answer)
                            revised_qa["validation_notes"] = {
                                "original_question": question,
                                "original_answer": answer,
                                "issues": validation_result.get("issues", []),
                                "explanation": validation_result.get("explanation", "")
                            }
                            validated_questions.append(revised_qa)
                    else:
                        # If parsing fails, keep original
                        validated_questions.append(qa)
                        
                except (json.JSONDecodeError, AttributeError):
                    # If validation fails, keep original but mark
                    qa["validation_failed"] = True
                    validated_questions.append(qa)
            
            # Update metadata with validated questions
            state.metadata[field] = validated_questions
        
        return state
    
    return solve


@solver  
def convert_directions_to_compass() -> Solver:
    """
    Solver that converts numeric directions to compass directions.
    
    Converts Factorio's numeric direction system:
    - 0 → North/Up
    - 2 → East/Right  
    - 4 → South/Down
    - 6 → West/Left
    """
    
    # Direction mapping
    direction_map = {
        0: "north",
        2: "east", 
        4: "south",
        6: "west"
    }
    
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        # Convert directions in all question types
        question_fields = [
            "basic_questions", "position_questions", "counting_questions",
            "spatial_questions", "qa_pairs"
        ]
        
        for field in question_fields:
            if field not in state.metadata:
                continue
                
            questions = state.metadata[field]
            if not isinstance(questions, list):
                continue
                
            for qa in questions:
                # Update question text
                question = qa.get("question", "")
                answer = qa.get("answer", "")
                
                # Replace direction references
                for num_dir, compass_dir in direction_map.items():
                    # Replace in questions
                    question = re.sub(
                        rf'\b(direction|facing)\s*{num_dir}\b',
                        f'facing {compass_dir}',
                        question,
                        flags=re.IGNORECASE
                    )
                    question = re.sub(
                        rf'\bdirection\s*=\s*{num_dir}\b',
                        f'facing {compass_dir}',
                        question,
                        flags=re.IGNORECASE
                    )
                    
                    # Replace in answers
                    answer = re.sub(
                        rf'\b{num_dir}\b',
                        compass_dir,
                        answer
                    )
                
                qa["question"] = question
                qa["answer"] = answer
                
                # Update entity properties if present
                if "entity_properties" in qa and "direction" in qa["entity_properties"]:
                    direction_value = qa["entity_properties"]["direction"]
                    if isinstance(direction_value, (int, float)) and direction_value in direction_map:
                        qa["entity_properties"]["direction_compass"] = direction_map[direction_value]
        
        return state
    
    return solve


@solver
def normalize_position_format() -> Solver:
    """
    Solver that converts position references from (x, y) format to Position(x={x}, y={y}) format.
    
    This solver ensures consistent position formatting across all QA pairs.
    """
    
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        # Convert positions in all question types
        question_fields = [
            "basic_questions", "position_questions", "counting_questions",
            "spatial_questions", "state_questions", "inventory_questions",
            "qa_pairs", "next_action_questions", "construction_order_questions",
            "throughput_questions", "bottleneck_questions", "optimization_questions",
            "direction_questions"
        ]
        
        for field in question_fields:
            if field not in state.metadata:
                continue
                
            questions = state.metadata[field]
            if not isinstance(questions, list):
                continue
                
            normalized_questions = []
            for qa in questions:
                # Normalize position format in question and answer
                normalized_qa = normalize_position_references_in_qa(qa)
                normalized_questions.append(normalized_qa)
            
            # Update metadata with normalized questions
            state.metadata[field] = normalized_questions
        
        return state
    
    return solve


@solver
def render_blueprint_image() -> Solver:
    """
    Solver that renders and saves the blueprint image once per task.
    
    This solver ensures that only one image is generated per blueprint,
    preventing duplicate images when multiple solvers run on the same blueprint.
    
    Should be run early in the solver chain.
    """
    instance = create_factorio_instance()
    
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        # Check if image is already rendered
        if "image" in state.metadata:
            return state
        
        blueprint = state.metadata.get("blueprint", {})
        if not blueprint:
            return state
        
        # Render the image (use a copy to avoid modifying the original blueprint)
        import copy
        blueprint_copy = copy.deepcopy(blueprint) 
        image: RenderedImage = instance.namespace._render(blueprint=blueprint_copy)
        
        # Save the image using the new folder structure
        from data.vqa.image_utils import save_rendered_image
        image_id = save_rendered_image(image, blueprint, state.metadata)
        
        # Store the image ID in metadata for other solvers to use
        state.metadata["image"] = image_id
        
        return state
    
    return solve


@solver
def attach_bounding_box() -> Solver:
    """
    Solver that calculates and attaches the blueprint bounding box to metadata.
    
    This ensures the bounding box information is available for grounding positions
    in questions and answers, and gets included in the JSONL output.
    """
    
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        
        if blueprint:
            # Calculate bounding box
            bounding_box = calculate_blueprint_bounding_box(blueprint)
            
            # Attach to metadata
            state.metadata["bounding_box"] = bounding_box
            
            # Also calculate and attach center point for convenience
            center_x = (bounding_box["min_x"] + bounding_box["max_x"]) / 2
            center_y = (bounding_box["min_y"] + bounding_box["max_y"]) / 2
            state.metadata["blueprint_center"] = {"x": center_x, "y": center_y}
        
        return state
    
    return solve


@solver
def generate_direction_questions(questions_per_blueprint: int = 2) -> Solver:
    """
    Solver that generates questions about entity orientations using Direction enums.
    
    This solver analyzes blueprint entities that have directional properties
    and generates questions about their orientations using the Direction enum.
    
    Args:
        questions_per_blueprint: Number of direction questions to generate per blueprint
    """
    
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        entities = blueprint.get("entities", [])
        direction_system = detect_direction_system(blueprint)
        
        # Filter entities that have direction properties
        directional_entities = []
        for entity in entities:
            if "direction" in entity and entity.get("direction") is not None:
                directional_entities.append(entity)
        
        if not directional_entities:
            # No directional entities, skip generation
            state.metadata["direction_questions"] = []
            return state
        
        # Create prompt for generating direction questions
        entity_info = []
        for entity in directional_entities[:10]:  # Limit to first 10 for prompt length
            pos = entity.get("position", {})
            direction_val = entity.get("direction", 0)
            direction_enum = Direction.from_value(direction_val, direction_system)
            entity_info.append({
                "name": entity.get("name", "unknown"),
                "position": f"Position(x={pos.get('x', 0)}, y={pos.get('y', 0)})",
                "direction": direction_enum.name if direction_enum else f"Direction({direction_val})"
            })
        
        # Generate direction-focused questions
        direction_prompt = f"""You are analyzing a Factorio blueprint and need to generate {questions_per_blueprint} questions about entity orientations.

Blueprint has {len(directional_entities)} entities with directional properties:
{json.dumps(entity_info, indent=2)}

Generate {questions_per_blueprint} questions about entity orientations. Focus on:

1. **Specific entity directions**: Ask about the direction/orientation of specific entities
2. **Relative orientations**: Compare directions between entities  
3. **Direction patterns**: Identify orientation patterns in the layout
4. **Functional directions**: Questions about how entity directions affect function

**Important guidelines:**
- Use Direction enum values in answers: Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST
- Reference entities by their exact positions using Position(x=X, y=Y) format
- Be specific about which entity you're asking about
- Focus on orientations that are visually apparent and functionally relevant

Return your response as a JSON array of question-answer pairs:
```json
[
  {{
    "question": "What direction is the [entity] facing at Position(x=X, y=Y)?",
    "answer": "Direction.NORTH",
    "entity_type": "entity_name",
    "position": {{"x": X, "y": Y}},
    "direction_value": 0,
    "question_type": "entity_direction"
  }}
]
```"""

        # Generate the questions
        state.messages = [ChatMessageUser(content=direction_prompt)]
        response = await generate(state)
        
        try:
            completion = response.output.completion
            json_match = re.search(r'```json\s*\n(.*?)\n```', completion, re.DOTALL)
            
            if json_match:
                direction_questions = json.loads(json_match.group(1))
                
                # Validate and clean up the questions
                validated_questions = []
                for qa in direction_questions[:questions_per_blueprint]:
                    if isinstance(qa, dict) and "question" in qa and "answer" in qa:
                        # Ensure answer uses Direction enum format
                        answer = qa["answer"]
                        if not answer.startswith("Direction."):
                            # Try to convert numeric or string directions to Direction enum
                            direction = Direction.from_value(answer, direction_system)
                            if direction:
                                qa["answer"] = f"Direction.{direction.name}"
                        
                        validated_questions.append(qa)
                
                state.metadata["direction_questions"] = validated_questions
            else:
                state.metadata["direction_questions"] = []
                
        except (json.JSONDecodeError, AttributeError):
            state.metadata["direction_questions"] = []
        
        return state
    
    return solve