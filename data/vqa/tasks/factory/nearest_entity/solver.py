# solver.py - Nearest entity question generation with entity placement

import random
import math
from typing import List, Dict, Any, Optional

from inspect_ai.solver import Solver, solver, TaskState, Generate

from data.vqa.image_utils import save_rendered_image
from data.vqa.common_solvers import validate_qa_answerability
from fle.agents.data.screenshots_from_run import create_factorio_instance
from fle.env import Position, Prototype, BuildingBox, Direction
from fle.env.game_types import prototype_by_name


# List of entities suitable for placement
PLACEABLE_ENTITIES = [
    Prototype.AssemblingMachine1,
    Prototype.AssemblingMachine2,
    Prototype.BurnerInserter,
    Prototype.Inserter,
    Prototype.FastInserter,
    Prototype.LongHandedInserter,
    Prototype.BurnerMiningDrill,
    Prototype.ElectricMiningDrill,
    Prototype.StoneFurnace,
    Prototype.SteelFurnace,
    Prototype.ElectricFurnace,
    Prototype.TransportBelt,
    Prototype.OffshorePump,
    Prototype.Boiler,
    Prototype.SteamEngine,
    Prototype.SolarPanel,
    Prototype.WoodenChest,
    Prototype.IronChest,
    Prototype.SteelChest,
    Prototype.SmallElectricPole,
    Prototype.MediumElectricPole,
    Prototype.Lab,
    Prototype.Radar,
    Prototype.GunTurret,
]


@solver
def render_factory(instance) -> Solver:
    """
    Creates a factory instance and prepares for entity placement.
    """

    inv = {e.value[0]: 3 for e in PLACEABLE_ENTITIES}
    instance.set_inventory(inv)
    
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        x, y = state.metadata['x'], state.metadata['y']
        step = 32
        # Generate terrain
        request = f'/c game.surfaces[0].request_to_generate_chunks({{{x*step}, {y*step}}}, 4)'
        instance.rcon_client.send_command(request)
        instance.rcon_client.send_command(f'/c game.player.surface.force_generate_chunk_requests()')
        
        # Move to position
        instance.namespace.move_to(Position(x=x*step, y=y*step))
        
        # Store instance for later use
        #state.metadata['instance'] = instance
        state.metadata['center_position'] = {'x': x*step, 'y': y*step}
        
        return state
    
    return solve


@solver 
def nearest_entity_questions(
    instance,
    questions_per_position: int = 5,
    multiple_choice: bool = True,
) -> Solver:
    """
    Places random entities and generates questions about nearest entity positions.
    """
    
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        #instance = state.metadata['instance']

        center_x = state.metadata['center_position']['x']
        center_y = state.metadata['center_position']['y']
        
        # Place multiple entities around the center position
        placed_entities = []
        num_entities = random.randint(5, 15)
        
        for i in range(num_entities):
            # Try to place an entity
            entity_type = random.choice(PLACEABLE_ENTITIES)
            
            # Random position within a reasonable radius
            radius = random.randint(10, 40)
            angle = random.random() * 2 * 3.14159
            
            offset_x = int(radius * math.cos(angle))
            offset_y = int(radius * math.sin(angle)) 
            
            target_pos = Position(x=center_x + offset_x, y=center_y + offset_y)
            
            try:
                # Find nearest buildable position for this entity type
                building_box = BuildingBox(width=entity_type.WIDTH + 1, height=entity_type.WIDTH + 1)
                buildable_pos = instance.namespace.nearest_buildable(entity_type, building_box, center_position=target_pos)
                
                if buildable_pos:
                    instance.namespace.move_to(buildable_pos.center)
                    # Place the entity
                    placed = instance.namespace.place_entity(
                        entity_type,
                        direction=random.choice([Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]), # Random direction
                        position = buildable_pos.left_top,
                    )

                    instance.namespace.move_to(Position(x=center_x, y=center_y))
                    
                    if placed:
                        placed_entities.append(placed)
                        
            except Exception as e:
                print(f"Failed to place {entity_type}: {e}")
                continue
        
        # Get the player's current position
        player_position = instance.namespace.player_location
        character_position = {'x': player_position.x, 'y': player_position.y}
        
        # Render the scene
        visible_radius = 32
        image, renderer = instance.namespace._render(
            radius=visible_radius,
            position=Position(x=center_x, y=center_y),
            return_renderer=True,
            max_render_radius=visible_radius
        )
        
        # Save image with position-based naming
        state.metadata['position'] = {'x': center_x, 'y': center_y}
        state.metadata['character_position'] = character_position
        image_id = save_rendered_image(image, metadata=state.metadata, is_factory=True)
        
        # Generate questions about nearest entities
        questions = []
        
        # Group entities by type
        entities_by_type = {}
        for entity in placed_entities:
            entity_type = entity.name
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)
        
        # Only ask about entity types that have at least one instance
        valid_entity_types = list(entities_by_type.keys())
        
        if valid_entity_types:
            for _ in range(min(questions_per_position, len(valid_entity_types))):
                # Pick a random entity type to ask about
                query_type = random.choice(valid_entity_types)
                
                # Get all instances of this type
                instances = entities_by_type[query_type]
                
                # Find the one closest to center
                closest = min(instances, key=lambda e: 
                    ((e.position.x - center_x) ** 2 +
                     (e.position.y - center_y) ** 2) ** 0.5
                )
                
                # Format entity name for question (replace hyphens with spaces)
                entity_display_name = query_type.replace('-', ' ')
                
                if not multiple_choice:
                    question = f"What is the position of the nearest {entity_display_name}?"
                    answer = f"Position(x={closest.position.x}, y={closest.position.y})"
                    
                    qa_entry = {
                        "question": question,
                        "answer": answer,
                        "image": image_id,
                        "metadata": {
                            "query_entity_type": query_type,
                            "center_position": state.metadata['center_position'],
                            "placed_entities": placed_entities
                        },
                        "question_type": "open_ended"
                    }
                else:
                    # Generate distractors for multiple choice
                    distractors = []
                    # Add positions of other entities as distractors
                    for entity in placed_entities:
                        if entity != closest:
                            distractors.append(entity.position)
                    
                    # Add some random positions if we need more distractors
                    while len(distractors) < 3:
                        fake_x = center_x + random.randint(-50, 50)
                        fake_y = center_y + random.randint(-50, 50)
                        fake_pos = Position(x=fake_x, y=fake_y)
                        distractors.append(fake_pos)
                    
                    # Create options list with correct answer and 3 distractors
                    options = [closest.position] + random.sample(distractors, 3)
                    random.shuffle(options)
                    
                    # Format with letters
                    alphabet = ['a', 'b', 'c', 'd']
                    option_strings = [
                        f"{alphabet[i]}) Position(x={pos.x}, y={pos.y})"
                        for i, pos in enumerate(options)
                    ]
                    
                    # Find correct answer index
                    correct_index = options.index(closest.position)
                    
                    # Format question with options included
                    question = (
                        f"What is the position of the nearest {entity_display_name}?\n"
                        f"Provide the correct letter and nothing else.\n"
                        f"{chr(10).join(option_strings)}"
                    )
                    
                    answer = alphabet[correct_index]
                    
                    qa_entry = {
                        "question": question,
                        "answer": answer,
                        "image": image_id,
                        "metadata": {
                            "query_entity_type": query_type,
                            "center_position": state.metadata['center_position'],
                            "placed_entities": placed_entities,
                            "options": [{"x": pos.x, "y": pos.y} for pos in options],
                            "correct_index": correct_index
                        },
                        "question_type": "multiple_choice"
                    }
                
                questions.append(qa_entry)

        # Validate questions
        # validated_questions = []
        # for q in questions:
        #     validated = await validate_qa_answerability(
        #         q, state, generate,
        #         validation_question="Is this question answerable and unambiguous?"
        #     )
        #     if validated:
        #         validated_questions.append(validated)
        
        # Store results
        state.metadata['image'] = image_id
        state.metadata['renderer'] = renderer
        state.metadata['entities'] = instance.namespace.get_entities(radius=visible_radius)
        state.metadata["nearest_entity_questions"] = questions
        state.metadata['placed_entities'] = placed_entities
        #state.metadata['questions'] = questions

        # Format output
        # output_lines = []
        # for q in questions:
        #     output_lines.append(f"Q: {q['question']}")
        #     if q.get('choices'):
        #         output_lines.append(f"Choices: {', '.join(q['choices'])}")
        #     output_lines.append(f"A: {q['answer']}")
        #     output_lines.append("")
        
        #state.output = "\n".join(output_lines)
        
        return state
    
    return solve