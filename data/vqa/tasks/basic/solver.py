import json
import random
import re
from collections import defaultdict
from json import JSONDecodeError

from inspect_ai.model import ChatMessageUser
from inspect_ai.solver import Solver, solver, TaskState, Generate

from data.vqa.blueprint_transforms import detect_direction_system
from data.vqa.direction_utils import convert_numeric_direction
from data.vqa.position_utils import format_position
from fle.agents.data.screenshots_from_run import create_factorio_instance


@solver
def generate_entity_name_questions(questions_per_blueprint: int = 3, multiple_choice: bool = False) -> Solver:
    """
    Generate questions about entity properties using a model to create diverse Q&A pairs.

    Args:
        questions_per_blueprint: Number of questions to generate per blueprint
        multiple_choice: If True, generate multiple choice questions with distractor options
    """
    instance = create_factorio_instance()

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        entities = blueprint.get("entities", [])
        direction_system = detect_direction_system(blueprint)

        if not entities:
            state.metadata["error"] = "No entities found in blueprint"
            state.metadata["basic_questions"] = []
            return state

        basic_questions = []

        # Get all unique entity names for creating distractors
        all_entity_names = list(set(entity.get("name", "unknown") for entity in entities))

        # Sample entities for question generation
        num_questions = min(questions_per_blueprint, len(entities))
        selected_entities = random.sample(entities, num_questions)

        for entity in selected_entities:
            position = entity.get("position", {})
            entity_name = entity.get("name", "unknown")
            x, y = position.get("x", 0), position.get("y", 0)

            # Extract all entity properties for the model to use
            entity['entity_number'] = None
            entity_properties = {k: v for k, v in entity.items() if v is not None}

            # Convert direction to compass if present
            if "direction" in entity_properties:
                dir_value = entity_properties["direction"]
                compass_dir = convert_numeric_direction(dir_value, direction_system)
                entity_properties["direction_compass"] = compass_dir

            if multiple_choice:
                # Create prompt for multiple choice question
                prompt = f"""Given this Factorio entity and its properties, generate a SPECIFIC and UNAMBIGUOUS multiple choice question about the entity.

Entity Properties:
{entity_properties}

All entity types in blueprint: {all_entity_names}

IMPORTANT GUIDELINES:
1. Questions must be answerable from just looking at the blueprint image
2. Always use exact positions when referring to entities (e.g., "at Position(x={x}, y={y})")
3. Create 3 plausible distractor options that could appear in a Factorio blueprint
4. For entity name questions, use other entity types from the blueprint as distractors when possible
5. Make distractors realistic but clearly wrong when examining the blueprint

Examples of GOOD multiple choice questions:
- "What entity is located at Position(x={x}, y={y})?
   A) transport-belt
   B) inserter
   C) assembly-machine-2
   D) {entity_name}"

- "What recipe is configured in the {entity_name} at Position(x={x}, y={y})?
   A) copper-plate
   B) iron-gear-wheel
   C) electronic-circuit
   D) [correct recipe]"

The correct answer should be the option at: {random.choice(['A','B','C','D'])}

Return your response in this exact JSON format:
```json
{{
    "question": "Your specific question here",
    "options": {{
        "A": "First option",
        "B": "Second option", 
        "C": "Third option",
        "D": "Fourth option"
    }},
    "correct_answer": "The letter of the correct option (A, B, C, or D)",
    "answer_text": "The actual answer value"
}}
```"""
            else:
                # Original prompt for open-ended questions
                prompt = f"""Given this Factorio entity and its properties, generate a SPECIFIC and UNAMBIGUOUS question and answer pair about the positioning of the entity.

Entity Properties:
{entity_properties}

IMPORTANT GUIDELINES:
1. Questions must be answerable from just looking at the blueprint image
2. Always use exact positions when referring to entities (e.g., "at Position(x={x}, y={y})")
3. Be specific - if there are multiple entities of the same type, specify which one
4. Avoid vague references like "the inserter" without position

Examples of GOOD questions:
- "What entity is located at Position(x={x}, y={y})?"
- "What recipe is configured in the {entity_name} at Position(x={x}, y={y})?"
- "How many filters are set on the {entity_name} at Position(x={x}, y={y})?"
- "Is there a {entity_name} at Position(x={x}, y={y})?"

Return your response in this exact JSON format:
```json
{{
    "question": "Your specific question here",
    "answer": "The precise answer"
}}
```"""

            # Clear messages and generate Q&A pair
            state.messages = [ChatMessageUser(content=prompt)]
            response = await generate(state)

            try:
                # Parse the JSON response
                completion = response.output.completion
                json_match = re.search(r'```json\s*\n(.*?)\n```', completion, re.DOTALL)
                if json_match:
                    qa_data = json.loads(json_match.group(1))

                    if multiple_choice:
                        question = qa_data.get("question", f"What entity is at {format_position(x, y)}?")
                        options = qa_data.get("options", {})
                        correct_answer = qa_data.get("correct_answer", "D")
                        answer_text = qa_data.get("answer_text", entity_name)

                        # Ensure we have valid options
                        if not options or len(options) != 4:
                            # Fallback: create default options
                            distractors = [name for name in all_entity_names if name != entity_name][:3]
                            if len(distractors) < 3:
                                # Add some common Factorio entities as distractors
                                common_entities = ["transport-belt", "inserter", "assembly-machine-2",
                                                   "electric-mining-drill", "stone-furnace", "splitter"]
                                distractors.extend(
                                    [e for e in common_entities if e != entity_name and e not in distractors])[:3]

                            options = {
                                "A": distractors[0] if len(distractors) > 0 else "transport-belt",
                                "B": distractors[1] if len(distractors) > 1 else "inserter",
                                "C": distractors[2] if len(distractors) > 2 else "assembly-machine-2",
                                "D": entity_name
                            }
                            correct_answer = "D"

                        # Format question with options
                        formatted_question = f"{question}\n"
                        for letter, option in sorted(options.items()):
                            formatted_question += f"   {letter}) {option}\n"

                        answer = correct_answer
                        question = formatted_question.rstrip()
                    else:
                        question = qa_data.get("question", f"What entity is at {format_position(x, y)}?")
                        answer = qa_data.get("answer", entity_name)
                else:
                    # Fallback to default question format
                    if multiple_choice:
                        distractors = [name for name in all_entity_names if name != entity_name][:3]
                        question = f"What entity is located at position {format_position(x, y)}?\n"
                        question += f"   A) {distractors[0] if distractors else 'transport-belt'}\n"
                        question += f"   B) {distractors[1] if len(distractors) > 1 else 'inserter'}\n"
                        question += f"   C) {distractors[2] if len(distractors) > 2 else 'assembly-machine-2'}\n"
                        question += f"   D) {entity_name}"
                        answer = "D"
                    else:
                        question = f"What entity is located at position {format_position(x, y)}?"
                        answer = entity_name

            except (JSONDecodeError, AttributeError):
                # Fallback to default question format if parsing fails
                if multiple_choice:
                    distractors = [name for name in all_entity_names if name != entity_name][:3]
                    question = f"What entity is located at position {format_position(x, y)}?\n"
                    question += f"   A) {distractors[0] if distractors else 'transport-belt'}\n"
                    question += f"   B) {distractors[1] if len(distractors) > 1 else 'inserter'}\n"
                    question += f"   C) {distractors[2] if len(distractors) > 2 else 'assembly-machine-2'}\n"
                    question += f"   D) {entity_name}"
                    answer = "D"
                else:
                    question = f"What entity is located at position {format_position(x, y)}?"
                    answer = entity_name

            qa_entry = {
                "question": question,
                "answer": answer,
                "entity": entity,
                "position": position,
                "entity_properties": entity_properties,
                "question_type": "multiple_choice" if multiple_choice else "open_ended"
            }

            if multiple_choice and 'options' in locals():
                qa_entry["options"] = options
                qa_entry["answer_text"] = answer_text if 'answer_text' in locals() else entity_name

            basic_questions.append(qa_entry)

        state.metadata["basic_questions"] = basic_questions
        return state

    return solve


@solver
def generate_position_questions(questions_per_blueprint: int = 3, multiple_choice: bool = False) -> Solver:
    """
    Generate questions asking for the position of entities using model-based generation.

    Args:
        questions_per_blueprint: Number of questions to generate per blueprint
        multiple_choice: If True, generate multiple choice questions with distractor positions
    """
    instance = create_factorio_instance()

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        entities = blueprint.get("entities", [])
        direction_system = detect_direction_system(blueprint)

        if not entities:
            state.metadata["error"] = "No entities found in blueprint"
            state.metadata["position_questions"] = []
            return state

        position_questions = []

        # Group entities by name to handle multiple instances
        entities_by_name = defaultdict(list)
        for entity in entities:
            entities_by_name[entity.get("name", "unknown")].append(entity)

        # Get all positions for creating distractors
        all_positions = [(e.get("position", {}).get("x", 0), e.get("position", {}).get("y", 0)) for e in entities]

        # Sample entities for question generation
        num_questions = min(questions_per_blueprint, len(entities))
        selected_entities = random.sample(entities, num_questions)

        for entity in selected_entities:
            position = entity.get("position", {})
            entity_name = entity.get("name", "unknown")
            x, y = position.get("x", 0), position.get("y", 0)

            # Count how many entities of this type exist
            same_type_count = len(entities_by_name[entity_name])

            # Get nearby entities for context
            nearby_entities = []
            for other in entities:
                if other != entity:
                    other_pos = other.get("position", {})
                    ox, oy = other_pos.get("x", 0), other_pos.get("y", 0)
                    distance = abs(ox - x) + abs(oy - y)
                    if distance <= 5:  # Within 5 tiles
                        nearby_entities.append({
                            "name": other.get("name", "unknown"),
                            "position": {"x": ox, "y": oy},
                            "distance": distance
                        })

            # Sort by distance
            nearby_entities.sort(key=lambda e: e["distance"])

            if multiple_choice:
                # Create prompt for multiple choice position question
                prompt = f"""Given this Factorio entity and context, generate a SPECIFIC multiple choice question asking about its position.

Entity: {entity_name}
Position: {format_position(x, y)}
Total {entity_name}s in blueprint: {same_type_count}
Nearby entities (within 5 tiles): {nearby_entities[:3] if nearby_entities else "None"}
All positions in blueprint: {all_positions[:10]}  # Show sample of positions

IMPORTANT GUIDELINES:
1. Create 3 distractor positions that are plausible but incorrect
2. Distractors should be actual positions from the blueprint or nearby positions
3. Make the question specific enough to have only one correct answer
4. If there are multiple entities of the same type, use specific identifiers

Examples of GOOD multiple choice position questions:
{f'- "Where is the {entity_name} located?' if same_type_count == 1 else f'- "Where is the northernmost {entity_name} located?'}
   A) Position(x=5, y=2)
   B) Position(x=3, y=-1)
   C) Position(x={x}, y={y})
   D) Position(x=0, y=4)"

Return your response in this exact JSON format:
```json
{{
    "question": "Your specific position question here",
    "options": {{
        "A": "Position(x=?, y=?)",
        "B": "Position(x=?, y=?)", 
        "C": "Position(x=?, y=?)",
        "D": "Position(x=?, y=?)"
    }},
    "correct_answer": "The letter of the correct option (A, B, C, or D)",
    "answer_text": "{format_position(x, y)}"
}}
```"""
            else:
                # Original prompt for open-ended questions
                prompt = f"""Given this Factorio entity and context, generate a SPECIFIC question asking about its position.

Entity: {entity_name}
Position: {format_position(x, y)}
Total {entity_name}s in blueprint: {same_type_count}
Nearby entities (within 5 tiles): {nearby_entities[:3] if nearby_entities else "None"}

IMPORTANT GUIDELINES:
1. If there's only one {entity_name}, the question can be simple
2. If there are multiple, use specific identifiers:
   - Relative positions (northernmost, southernmost, etc.)
   - Distance from other entities with their exact positions
   - Unique characteristics visible in the image
3. Always make the question answerable from just the visual image

Return your response in this exact JSON format:
```json
{{
    "question": "Your specific position question here",
    "answer": "{format_position(x, y)}"
}}
```"""

            # Generate Q&A pair
            state.messages = [ChatMessageUser(content=prompt)]
            response = await generate(state)

            try:
                completion = response.output.completion
                json_match = re.search(r'```json\s*\n(.*?)\n```', completion, re.DOTALL)
                if json_match:
                    qa_data = json.loads(json_match.group(1))

                    if multiple_choice:
                        question = qa_data.get("question", f"Where is the {entity_name} located?")
                        options = qa_data.get("options", {})
                        correct_answer = qa_data.get("correct_answer", "C")
                        answer_text = qa_data.get("answer_text", format_position(x, y))

                        # Ensure we have valid options
                        if not options or len(options) != 4:
                            # Create distractor positions
                            distractor_positions = []
                            for ox, oy in all_positions:
                                if (ox, oy) != (x, y):
                                    distractor_positions.append(format_position(ox, oy))

                            # If not enough real positions, create synthetic ones
                            if len(distractor_positions) < 3:
                                for i in range(3 - len(distractor_positions)):
                                    offset_x = random.randint(-5, 5)
                                    offset_y = random.randint(-5, 5)
                                    if (x + offset_x, y + offset_y) != (x, y):
                                        distractor_positions.append(format_position(x + offset_x, y + offset_y))

                            random.shuffle(distractor_positions)
                            options = {
                                "A": distractor_positions[0],
                                "B": distractor_positions[1],
                                "C": format_position(x, y),
                                "D": distractor_positions[2]
                            }
                            correct_answer = "C"

                        # Format question with options
                        formatted_question = f"{question}\n"
                        for letter, option in sorted(options.items()):
                            formatted_question += f"{letter}) {option}\n"

                        answer = correct_answer
                        question = formatted_question.rstrip()
                    else:
                        question = qa_data.get("question", f"Where is the {entity_name} located?")
                        answer = qa_data.get("answer", format_position(x, y))
                else:
                    if multiple_choice:
                        # Fallback multiple choice
                        distractor_positions = []
                        for ox, oy in random.sample(all_positions, min(3, len(all_positions) - 1)):
                            if (ox, oy) != (x, y):
                                distractor_positions.append(format_position(ox, oy))

                        question = f"Where is the {entity_name} located?\n"
                        options_list = distractor_positions[:3]
                        options_list.append(format_position(x, y))
                        random.shuffle(options_list)

                        correct_idx = options_list.index(format_position(x, y))
                        letters = ["A", "B", "C", "D"]

                        for i, opt in enumerate(options_list):
                            question += f"   {letters[i]}) {opt}\n"

                        answer = letters[correct_idx]
                        question = question.rstrip()
                    else:
                        question = f"Where is the {entity_name} located?"
                        answer = format_position(x, y)

            except (json.JSONDecodeError, AttributeError):
                if multiple_choice:
                    # Simple fallback
                    question = f"Where is the {entity_name} located?\n"
                    question += f"   A) Position(x={x + 1}, y={y})\n"
                    question += f"   B) Position(x={x}, y={y + 1})\n"
                    question += f"   C) Position(x={x}, y={y})\n"
                    question += f"   D) Position(x={x - 1}, y={y - 1})"
                    answer = "C"
                else:
                    question = f"Where is the {entity_name} located?"
                    answer = format_position(x, y)

            qa_entry = {
                "question": question,
                "answer": answer,
                "entity": entity,
                "position": position,
                "context": {
                    "same_type_count": same_type_count,
                    "nearby_entities": nearby_entities[:3]
                },
                "question_type": "multiple_choice" if multiple_choice else "open_ended"
            }

            if multiple_choice and 'options' in locals():
                qa_entry["options"] = options
                qa_entry["answer_text"] = answer_text if 'answer_text' in locals() else format_position(x, y)

            position_questions.append(qa_entry)

        state.metadata["position_questions"] = position_questions
        return state

    return solve


@solver
def generate_counting_questions(questions_per_blueprint: int = 2, multiple_choice: bool = False) -> Solver:
    """
    Generate questions about counting entities using model-based generation.

    Args:
        questions_per_blueprint: Number of counting questions to generate per blueprint
        multiple_choice: If True, generate multiple choice questions with distractor counts
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        entities = blueprint.get("entities", [])
        direction_system = detect_direction_system(blueprint)

        if not entities:
            state.metadata["error"] = "No entities found in blueprint"
            state.metadata["counting_questions"] = []
            return state

        # Count entities by various properties
        entity_counts = defaultdict(int)
        entity_by_direction = defaultdict(lambda: defaultdict(int))
        entity_in_regions = defaultdict(lambda: defaultdict(int))
        connected_entities = defaultdict(int)

        for entity in entities:
            entity_name = entity.get("name", "unknown")
            entity_counts[entity_name] += 1

            # Count by direction (convert to compass)
            direction = entity.get("direction", 0)
            compass_dir = convert_numeric_direction(direction, direction_system)
            entity_by_direction[entity_name][compass_dir] += 1

            # Count by region (quadrants)
            pos = entity.get("position", {})
            x, y = pos.get("x", 0), pos.get("y", 0)
            region = f"{'north' if y < 0 else 'south'}-{'west' if x < 0 else 'east'}"
            entity_in_regions[entity_name][region] += 1

            # Count connected entities
            if entity.get("connections"):
                connected_entities[entity_name] += 1

        counting_questions = []

        # Generate diverse counting questions
        for i in range(questions_per_blueprint):
            # Create comprehensive context for the model
            context = {
                "total_entities": len(entities),
                "entity_types": list(entity_counts.keys()),
                "entity_counts": dict(entity_counts),
                "entities_by_direction": {k: dict(v) for k, v in entity_by_direction.items()},
                "entities_by_region": {k: dict(v) for k, v in entity_in_regions.items()},
                "connected_entity_counts": dict(connected_entities)
            }

            if multiple_choice:
                prompt = f"""Given this Factorio blueprint analysis, generate a multiple choice counting question.

Blueprint Statistics:
- Total entities: {context['total_entities']}
- Entity types and counts: {context['entity_counts']}
- Entities by direction: {context['entities_by_direction']}
- Entities by region: {context['entities_by_region']}
- Connected entities: {context['connected_entity_counts']}

Generate a creative counting question with 4 options. The distractor numbers should be plausible but wrong.

Examples:
- "How many transport-belts are in this blueprint?
   A) 12
   B) 15
   C) 18
   D) 21"

- "Count the number of inserters facing north:
   A) 2
   B) 4
   C) 6
   D) 8"

GUIDELINES FOR DISTRACTORS:
1. Make them close to the correct answer (within ±50%)
2. Avoid obvious wrong answers like 0 or 1000
3. Include common counting mistakes (off by one, double counting, etc.)

The correct answer should be the option at: {random.choice(['A','B','C','D'])}

Return your response in this exact JSON format:
```json
{{
    "question": "Your counting question here",
    "options": {{
        "A": "number",
        "B": "number", 
        "C": "number",
        "D": "number"
    }},
    "correct_answer": "The letter of the correct option (A, B, C, or D)",
    "answer_text": "The numeric answer",
    "explanation": "Brief explanation of what was counted"
}}
```"""
            else:
                prompt = f"""Given this Factorio blueprint analysis, generate a counting question and its answer.

Blueprint Statistics:
- Total entities: {context['total_entities']}
- Entity types and counts: {context['entity_counts']}
- Entities by direction: {context['entities_by_direction']}
- Entities by region: {context['entities_by_region']}
- Connected entities: {context['connected_entity_counts']}

Generate a creative counting question. Examples:
- "How many transport-belts are in this blueprint?"
- "Count the number of inserters facing north"
- "How many assembly machines are in the eastern half of the blueprint?"
- "What's the total number of connected entities?"
- "How many different types of entities are used?"
- "Count all entities that can move items"

Think step by step.

Return your response in this exact JSON format:
```json
{{
    "question": "Your counting question here",
    "answer": "The numeric answer",
    "explanation": "Brief explanation of what was counted"
}}
```"""

            # Generate Q&A pair
            state.messages = [ChatMessageUser(content=prompt)]
            response = await generate(state)

            try:
                completion = response.output.completion
                json_match = re.search(r'```json\s*\n(.*?)\n```', completion, re.DOTALL)
                if json_match:
                    qa_data = json.loads(json_match.group(1))

                    if multiple_choice:
                        question = qa_data.get("question")
                        options = qa_data.get("options", {})
                        correct_answer = qa_data.get("correct_answer")
                        answer_text = qa_data.get("answer_text")
                        explanation = qa_data.get("explanation", "")

                        if question and correct_answer and options:
                            # Format question with options
                            formatted_question = f"{question}\n"
                            for letter, option in sorted(options.items()):
                                formatted_question += f"   {letter}) {option}\n"

                            counting_questions.append({
                                "question": formatted_question.rstrip(),
                                "answer": correct_answer,
                                "answer_text": answer_text,
                                "options": options,
                                "explanation": explanation,
                                "context": context,
                                "question_type": "multiple_choice"
                            })
                        else:
                            # Fallback with generated distractors
                            entity_name = random.choice(list(entity_counts.keys()))
                            correct_count = entity_counts[entity_name]

                            # Generate plausible distractors
                            distractors = []
                            distractors.append(max(1, correct_count - random.randint(1, 3)))
                            distractors.append(correct_count + random.randint(1, 3))
                            distractors.append(max(1, int(correct_count * random.uniform(0.7, 0.9))))

                            options_list = distractors + [correct_count]
                            random.shuffle(options_list)

                            options = {
                                "A": str(options_list[0]),
                                "B": str(options_list[1]),
                                "C": str(options_list[2]),
                                "D": str(options_list[3])
                            }

                            correct_idx = options_list.index(correct_count)
                            correct_answer = ["A", "B", "C", "D"][correct_idx]

                            question = f"How many {entity_name}s are in this blueprint?\n"
                            for letter, count in sorted(options.items()):
                                question += f"   {letter}) {count}\n"

                            counting_questions.append({
                                "question": question.rstrip(),
                                "answer": correct_answer,
                                "answer_text": str(correct_count),
                                "options": options,
                                "explanation": f"Count of {entity_name} entities",
                                "context": context,
                                "question_type": "multiple_choice"
                            })
                    else:
                        question = qa_data.get("question")
                        answer = qa_data.get("answer")
                        explanation = qa_data.get("explanation", "")

                        if question and answer:
                            counting_questions.append({
                                "question": question,
                                "answer": answer,
                                "explanation": explanation,
                                "context": context,
                                "question_type": "open_ended"
                            })
                        else:
                            # Fallback to basic counting
                            entity_name = random.choice(list(entity_counts.keys()))
                            counting_questions.append({
                                "question": f"How many {entity_name}s are in this blueprint?",
                                "answer": str(entity_counts[entity_name]),
                                "explanation": f"Count of {entity_name} entities",
                                "context": context,
                                "question_type": "open_ended"
                            })

            except (json.JSONDecodeError, AttributeError):
                # Fallback to basic counting question
                if entity_counts:
                    entity_name = random.choice(list(entity_counts.keys()))

                    if multiple_choice:
                        correct_count = entity_counts[entity_name]

                        # Simple distractor generation
                        options = {
                            "A": str(max(1, correct_count - 2)),
                            "B": str(correct_count + 1),
                            "C": str(correct_count),
                            "D": str(correct_count + 3)
                        }

                        question = f"How many {entity_name}s are in this blueprint?\n"
                        for letter, count in sorted(options.items()):
                            question += f"   {letter}) {count}\n"

                        counting_questions.append({
                            "question": question.rstrip(),
                            "answer": "C",
                            "answer_text": str(correct_count),
                            "options": options,
                            "explanation": f"Count of {entity_name} entities",
                            "context": context,
                            "question_type": "multiple_choice"
                        })
                    else:
                        counting_questions.append({
                            "question": f"How many {entity_name}s are in this blueprint?",
                            "answer": str(entity_counts[entity_name]),
                            "explanation": f"Count of {entity_name} entities",
                            "context": context,
                            "question_type": "open_ended"
                        })

        state.metadata["counting_questions"] = counting_questions
        return state

    return solve