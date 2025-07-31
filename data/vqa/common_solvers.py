"""Common solvers used across multiple VQA tasks."""

import json
import re
from inspect_ai.model import ChatMessageUser
from inspect_ai.solver import Solver, solver, TaskState, Generate
from data.vqa.position_utils import normalize_position_references_in_qa


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
            "throughput_questions", "bottleneck_questions", "optimization_questions"
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
                
Question: {question}
Answer: {answer}

Blueprint:{blueprint}

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
            "throughput_questions", "bottleneck_questions", "optimization_questions"
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