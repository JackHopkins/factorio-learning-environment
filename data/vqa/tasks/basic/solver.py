import json
import random
import re
from collections import defaultdict
from json import JSONDecodeError

from inspect_ai.model import ChatMessageUser
from inspect_ai.solver import Solver, solver, TaskState, Generate
from data.vqa.templates import Templates
from fle.agents.data.screenshots_from_run import create_factorio_instance
from fle.commons.models.rendered_image import RenderedImage


@solver
def generate_entity_name_questions(questions_per_blueprint: int = 3) -> Solver:
    """
    Generate questions about entity properties using a model to create diverse Q&A pairs.

    Args:
        questions_per_blueprint: Number of questions to generate per blueprint
    """
    instance = create_factorio_instance()
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        entities = blueprint.get("entities", [])

        if not entities:
            state.metadata["error"] = "No entities found in blueprint"
            state.metadata["basic_questions"] = []
            return state

        basic_questions = []

        # Sample entities for question generation
        num_questions = min(questions_per_blueprint, len(entities))
        selected_entities = random.sample(entities, num_questions)

        for entity in selected_entities:
            position = entity.get("position", {})
            entity_name = entity.get("name", "unknown")
            x, y = position.get("x", 0), position.get("y", 0)

            # Extract all entity properties for the model to use
            # entity_properties = {
            #     "name": entity_name,
            #     "position": {"x": x, "y": y},
            #     "direction": entity.get("direction", 0),
            #     "entity_number": entity.get("entity_number"),
            #     "recipe": entity.get("recipe"),
            #     "type": entity.get("type"),
            #     "filters": entity.get("filters", []),
            #     "bar": entity.get("bar"),
            #     "connections": entity.get("connections", {}),
            #     "control_behavior": entity.get("control_behavior", {}),
            #     "items": entity.get("items", {}),
            #     "request_filters": entity.get("request_filters", []),
            # }

            # Remove None values for cleaner prompt
            entity['entity_number'] = None
            entity_properties = {k: v for k, v in entity.items() if v is not None}



            # Create prompt for the model to generate a question/answer pair
            prompt = f"""Given this Factorio entity and its properties, generate a question and answer pair.

Entity Properties:
{entity_properties}

Generate a question that asks about any property of this entity (not just position or name).
Examples of good questions:
- "What entity is located at position ({x}, {y})?"
- "What direction is the {entity_name} at ({x}, {y}) facing?"
- "What recipe is configured in the {entity_name} at position ({x}, {y})?"
- "How many filters are set on the {entity_name} at ({x}, {y})?"
- "What is the entity number of the {entity_name} at position ({x}, {y})?"

Return your response in this exact JSON format:
```json
{{
    "question": "Your question here",
    "answer": "The precise answer"
}}
```"""

            # Clear messages and generate Q&A pair
            state.messages = [ChatMessageUser(content=prompt)]
            response = await generate(state)

            try:
                # Parse the JSON response
                import json
                import re

                completion = response.output.completion
                # Extract JSON from the response
                json_match = re.search(r'```json\s*\n(.*?)\n```', completion, re.DOTALL)
                if json_match:
                    qa_data = json.loads(json_match.group(1))
                    question = qa_data.get("question", f"What entity is at ({x}, {y})?")
                    answer = qa_data.get("answer", entity_name)
                else:
                    # Fallback to default question format
                    question = f"What entity is located at position ({x}, {y})?"
                    answer = entity_name

            except (JSONDecodeError, AttributeError):
                # Fallback to default question format if parsing fails
                question = f"What entity is located at position ({x}, {y})?"
                answer = entity_name

            basic_questions.append({
                "question": question,
                "answer": answer,
                "entity": entity,
                "position": position,
                "entity_properties": entity_properties
            })

        state.metadata["basic_questions"] = basic_questions
        return state

    return solve


@solver
def generate_position_questions(questions_per_blueprint: int = 3) -> Solver:
    """
    Generate questions asking for the position of entities using model-based generation.

    Args:
        questions_per_blueprint: Number of questions to generate per blueprint
    """
    instance = create_factorio_instance()
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        entities = blueprint.get("entities", [])

        if not entities:
            state.metadata["error"] = "No entities found in blueprint"
            state.metadata["position_questions"] = []
            return state

        position_questions = []

        image: RenderedImage = instance.namespace._render(blueprint=blueprint)
        id = str(hash(str(blueprint)))
        image.save(f"./{id}.jpg")
        state.metadata["image"] = id

        # Group entities by name to handle multiple instances
        entities_by_name = defaultdict(list)
        for entity in entities:
            entities_by_name[entity.get("name", "unknown")].append(entity)

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

            # Create prompt for model
            prompt = f"""Given this Factorio entity and context, generate a question asking about its position and provide the answer.

Entity: {entity_name}
Position: ({x}, {y})
Total {entity_name}s in blueprint: {same_type_count}
Nearby entities (within 5 tiles): {nearby_entities[:3] if nearby_entities else "None"}

Generate a creative question that asks about this entity's position. The question should be specific enough to identify this particular instance if there are multiple.

Examples of good position questions:
- "Where is the {entity_name} located?"
- "What are the coordinates of the northernmost {entity_name}?"
- "At what position is the {entity_name} that's closest to the inserter?"
- "Where is the {entity_name} that's 3 tiles east of the assembly machine?"
- "What's the position of the isolated {entity_name}?"

Return your response in this exact JSON format:
```json
{{
    "question": "Your position question here",
    "answer": "({x}, {y})"
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
                    question = qa_data.get("question", f"Where is the {entity_name} located?")
                    answer = qa_data.get("answer", f"({x}, {y})")
                else:
                    question = f"Where is the {entity_name} located?"
                    answer = f"({x}, {y})"

            except (json.JSONDecodeError, AttributeError):
                question = f"Where is the {entity_name} located?"
                answer = f"({x}, {y})"

            position_questions.append({
                "question": question,
                "answer": answer,
                "entity": entity,
                "position": position,
                "context": {
                    "same_type_count": same_type_count,
                    "nearby_entities": nearby_entities[:3]
                }
            })

        state.metadata["position_questions"] = position_questions
        return state

    return solve


@solver
def generate_counting_questions(questions_per_blueprint: int = 2) -> Solver:
    """
    Generate questions about counting entities using model-based generation.

    Args:
        questions_per_blueprint: Number of counting questions to generate per blueprint
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        entities = blueprint.get("entities", [])

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

            # Count by direction
            direction = entity.get("direction", 0)
            entity_by_direction[entity_name][direction] += 1

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
                    question = qa_data.get("question")
                    answer = qa_data.get("answer")
                    explanation = qa_data.get("explanation", "")

                    if question and answer:
                        counting_questions.append({
                            "question": question,
                            "answer": answer,
                            "explanation": explanation,
                            "context": context
                        })
                    else:
                        # Fallback to basic counting
                        entity_name = random.choice(list(entity_counts.keys()))
                        counting_questions.append({
                            "question": f"How many {entity_name}s are in this blueprint?",
                            "answer": str(entity_counts[entity_name]),
                            "explanation": f"Count of {entity_name} entities",
                            "context": context
                        })

            except (json.JSONDecodeError, AttributeError):
                # Fallback to basic counting question
                if entity_counts:
                    entity_name = random.choice(list(entity_counts.keys()))
                    counting_questions.append({
                        "question": f"How many {entity_name}s are in this blueprint?",
                        "answer": str(entity_counts[entity_name]),
                        "explanation": f"Count of {entity_name} entities",
                        "context": context
                    })

        state.metadata["counting_questions"] = counting_questions
        return state

    return solve