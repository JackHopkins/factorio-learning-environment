from typing import Any, Dict, List, Union, Optional, Tuple
import random
from env.src.entities import Inventory, Entity, Position
from env.src.instance import FactorioInstance, Direction
from env.src.game_types import Prototype
from eval.tasks.scenarios.auto_refueling_coal_scenario import AutorefuelingCoalScenario
from eval.tasks.scenarios.scenario_factory import ScenarioFactory
from eval.tasks.task_abc import TaskABC
from eval.tasks.throughput_task import LAB_PLAY_POPULATED_STARTING_INVENTORY, CRAFTING_STATISTICS
from env.src.utils.achievements import eval_program_with_achievements
from agents import TaskResponse
import copy

INSTRUCTIONS = """
Here is a factory. 

Your job is to identify the positions of the broken parts of the factory.

There are between zero and four mistakes/breaks in this factory.

Mistakes in the factory include:
1. Rotation: Entity is rotated the wrong way
2. Misplacement: Entity is placed 1 tile off
3. Deletion: Missing Entity
4. Addition: Extra unnecessary entity

To submit mistakes to the overseer, use `send_message` to send a message to (kwarg: recipient=0), including the positions and type of mistake in the following format:
`(X,Y)=TYPE[SPACE ](X,Y)=TYPE ...'.

You can submit your mistake message only ONCE - so analyze the environment such that you are very confident of your answers. 
"""

ERROR_TYPE_COLORS = {
    "ROTATION": {"r": 1, "g": 0, "b": 0},  # Red
    "MISPLACEMENT": {"r": 0, "g": 1, "b": 0},  # Green
    "DELETION": {"r": 0, "g": 0, "b": 1},  # Blue
    "ADDITION": {"r": 1, "g": 1, "b": 0}  # Yellow
}

ERROR_TYPES = ["ROTATION", "MISPLACEMENT", "DELETION", "ADDITION"]


class SpatialReasoningTask(TaskABC):
    def __init__(self,
                 trajectory_length,
                 goal_description: str,
                 task_key: str,
                 scenario: str,
                 agent_instructions: Optional[List[str]] = None,
                 scenario_params: Dict = None,
                 max_errors: int = 4,
                 seed: Optional[int] = None) -> None:

        goal_description += f"\n{INSTRUCTIONS}"
        super().__init__(trajectory_length,
                         starting_inventory=Inventory(),
                         goal_description=goal_description,
                         task_key=task_key,
                         all_technology_researched=True,
                         agent_instructions=agent_instructions)
        self.starting_game_state = None
        self.scenario = scenario
        self.scenario_params = scenario_params
        self.submitted_mistakes = {}
        self.actual_mistakes = {}
        self.max_errors = max_errors
        self.random_seed = seed if seed is not None else random.randint(0, 999999)
        self.rng = random.Random(self.random_seed)

    def draw_error_circles(self, instance: FactorioInstance, positions_with_types: Dict[tuple, str]) -> None:
        """
        Draw circles at positions where errors are detected.

        Args:
            instance: The Factorio instance
            positions_with_types: Dictionary mapping (x,y) positions to error types
        """
        # Clear any previous visualization
        instance.rcon_client.send_command(f'/c rendering.clear()')

        # Draw a circle for each detected error position
        for position, error_type in positions_with_types.items():
            x, y = position
            color = ERROR_TYPE_COLORS.get(error_type, {"r": 1, "g": 1, "b": 1})  # Default to white if type not found

            # Draw circle using Lua rendering (since Python API doesn't have direct drawing functions)
            lua_command = (
                f'/c local surface = game.surfaces[1]; '
                f'rendering.draw_circle{{only_in_alt_mode=false, width = 2, '
                f'color = {{r = {color["r"]}, g = {color["g"]}, b = {color["b"]}}}, '
                f'surface = surface, radius = 0.5, filled = false, '
                f'target = {{x = {x}, y = {y}}}, time_to_live = 60000}}'
            )

            # Execute the command
            instance.rcon_client.send_command(lua_command)

            # Also add a text label with the error type
            label_command = (
                f'/c local surface = game.surfaces[1]; '
                f'rendering.draw_text{{only_in_alt_mode=false, '
                f'color = {{r = {color["r"]}, g = {color["g"]}, b = {color["b"]}}}, '
                f'surface = surface, text = "{error_type}", '
                f'target = {{x = {x}, y = {y - 0.3}}},'  # Slightly above the circle
                f'scale = 0.7, time_to_live = 60000}}'
            )

            instance.rcon_client.send_command(label_command)

    def apply_factory_errors(self, instance: FactorioInstance) -> None:
        """
        Apply 0-4 random errors to random entities in the factory using Python API methods.

        Args:
            instance: The Factorio instance

        Returns:
            None, but populates self.actual_mistakes with the applied errors
        """
        # Reset any previous errors
        self.actual_mistakes = {}

        # Get all entities using the Python get_entities method
        namespace = instance.namespace

        # Get all entities on the map (filtering out characters and resources)
        all_entities = namespace.get_entities()

        # Filter out characters, resources, and item-on-ground entities
        valid_entities = all_entities#[]
        # for entity in all_entities:
        #     # Filter out certain entity types that shouldn't have errors applied
        #     if (entity.entity_type != "character" and
        #             entity.entity_type != "resource" and
        #             entity.entity_type != "item-on-ground" and
        #             hasattr(entity, "position")):
        #         valid_entities.append(entity)

        if not valid_entities or len(valid_entities) < 5:
            # Not enough entities to apply meaningful errors
            print("Not enough valid entities to apply errors")
            return

        # Decide how many errors to apply (0-4)
        num_errors = self.rng.randint(0, min(self.max_errors, len(valid_entities)))

        # Select that many entities randomly without replacement
        selected_entities = self.rng.sample(valid_entities, num_errors)

        # Apply a random error type to each selected entity
        for entity in selected_entities:
            entity_pos = (entity.position.x, entity.position.y)
            error_type = self.rng.choice(ERROR_TYPES)

            # Apply the error based on its type
            self._apply_error(instance, entity, error_type)

            # Record the applied error
            self.actual_mistakes[entity_pos] = error_type

        # Log the actual mistakes for grading
        print(f"Applied {num_errors} errors: {self.actual_mistakes}")

    def _apply_error(self, instance: FactorioInstance, entity: Entity, error_type: str) -> None:
        """
        Apply a specific error to an entity using Python API methods.

        Args:
            instance: The Factorio instance
            entity: Entity object
            error_type: Type of error to apply (ROTATION, MISPLACEMENT, DELETION, ADDITION)
        """
        namespace = instance.namespace

        # Store the entity's properties
        entity_name = entity.name
        entity_position = copy.deepcopy(entity.position)

        # Make entity position a tuple for easier reference
        entity_pos = (entity_position.x, entity_position.y)

        # Get the direction if available (defaulting to UP)
        if hasattr(entity, 'direction'):
            entity_direction = entity.direction
        else:
            entity_direction = Direction.UP

        # Apply the specific error based on type
        if error_type == "ROTATION":
            # Rotate the entity to a random different direction
            possible_dirs = [Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT]

            # Convert current direction to Direction enum for comparison
            current_dir = None
            if hasattr(entity, 'direction'):
                current_dir = entity.direction

            # Remove current direction from possibilities if it exists
            if current_dir in possible_dirs:
                possible_dirs.remove(current_dir)

            # Choose a random new direction
            new_dir = self.rng.choice(possible_dirs)

            try:
                # Use the rotate_entity method to change direction
                namespace.rotate_entity(entity, new_dir)
                print(f"Rotated entity at {entity_pos} from {current_dir} to {new_dir}")
            except Exception as e:
                print(f"Could not rotate entity at {entity_pos}: {e}")

        elif error_type == "MISPLACEMENT":
            # Move the entity 1 tile in a random direction
            # First, decide which direction to move
            offset = self.rng.choice([(0, 1), (1, 0), (0, -1), (-1, 0)])
            new_pos = Position(x=entity_pos[0] + offset[0], y=entity_pos[1] + offset[1])

            try:
                # First pick up the entity
                namespace.pickup_entity(entity)

                # Then place it at the new position with same direction
                # Get the prototype from the entity name
                prototype = None
                for proto in dir(Prototype):
                    if not proto.startswith('_'):  # Skip private attributes
                        proto_value = getattr(Prototype, proto)
                        if hasattr(proto_value, 'value') and proto_value.value[0] == entity_name:
                            prototype = proto_value
                            break

                if prototype:
                    namespace.place_entity(prototype, position=new_pos, direction=entity_direction)
                    print(f"Misplaced entity from {entity_pos} to {(new_pos.x, new_pos.y)}")
                else:
                    print(f"Could not find prototype for entity {entity_name}")
            except Exception as e:
                print(f"Could not misplace entity at {entity_pos}: {e}")

        elif error_type == "DELETION":
            # Simply delete the entity
            try:
                namespace.pickup_entity(entity)
                print(f"Deleted entity at {entity_pos}")
            except Exception as e:
                print(f"Could not delete entity at {entity_pos}: {e}")

        elif error_type == "ADDITION":
            # Add an extra entity of the same type nearby
            # Choose a random position nearby
            for _ in range(4):  # Try up to 4 different positions
                offset = self.rng.choice([(0, 1), (1, 0), (0, -1), (-1, 0)])
                new_pos = Position(x=entity_pos[0] + offset[0], y=entity_pos[1] + offset[1])

                try:
                    # Get the prototype from the entity name
                    prototype = None
                    for proto in dir(Prototype):
                        if not proto.startswith('_'):  # Skip private attributes
                            proto_value = getattr(Prototype, proto)
                            if hasattr(proto_value, 'value') and proto_value.value[0] == entity_name:
                                prototype = proto_value
                                break

                    if prototype:
                        # Check if we can place at this position
                        if namespace.can_place_entity(prototype, position=new_pos):
                            namespace.place_entity(prototype, position=new_pos, direction=entity_direction)
                            print(f"Added duplicate entity at {(new_pos.x, new_pos.y)}")
                            break
                    else:
                        print(f"Could not find prototype for entity {entity_name}")
                        break
                except Exception as e:
                    # Just try the next position
                    continue

    def verify(self, score: float, instance: FactorioInstance, step_statistics: Dict) -> TaskResponse:
        messages = instance.namespaces[0]._get_messages(all_players=True)

        # Get the last message sent by the agent
        if not messages:
            return TaskResponse(success=False,
                                meta={
                                    "nr_of_steps_left": self.trajectory_length - step_statistics["current_step_id"] - 1,
                                    "reason": "No message submitted."})

        last_message = messages[-1]

        # Parse the agent's submission
        self.submitted_mistakes = {}

        try:
            # Split the message by spaces and process each position=type pair
            mistake_entries = [entry.strip() for entry in last_message['message'].split(' ')]

            for entry in mistake_entries:
                # Parse format like "(X,Y)=TYPE"
                if "=" not in entry:
                    continue

                position_part, mistake_type = entry.split('=')

                # Extract X and Y from "(X,Y)"
                position_part = position_part.strip('() ')
                x, y = map(float, position_part.split(','))

                # Store the mistake type at this position
                mistake_type = mistake_type.strip().upper()
                if mistake_type not in ERROR_TYPES:
                    return TaskResponse(success=False,
                                        meta={"nr_of_steps_left": self.trajectory_length - step_statistics[
                                            "current_step_id"] - 1,
                                              "reason": f"Invalid mistake type: {mistake_type}"})

                self.submitted_mistakes[(x, y)] = mistake_type
        except Exception as e:
            # If there's any error in parsing the format
            return TaskResponse(success=False,
                                meta={
                                    "nr_of_steps_left": self.trajectory_length - step_statistics["current_step_id"] - 1,
                                    "reason": f"Error parsing mistake format: {str(e)}"})

        # Draw circles for visualizing the submitted mistakes
        self.draw_error_circles(instance, self.submitted_mistakes)

        # Compare submitted mistakes with actual mistakes
        correct_mistakes = 0
        total_actual_mistakes = len(self.actual_mistakes)

        # Check if the submitted positions match with any actual mistake positions (with some tolerance)
        tolerance = 0.5  # Allow 0.5 tile position difference

        for submitted_pos, submitted_type in self.submitted_mistakes.items():
            # Check if any actual mistake position is close to this submitted position
            for actual_pos, actual_type in self.actual_mistakes.items():
                distance = ((submitted_pos[0] - actual_pos[0]) ** 2 + (submitted_pos[1] - actual_pos[1]) ** 2) ** 0.5
                if distance <= tolerance and submitted_type == actual_type:
                    correct_mistakes += 1
                    break

        # Calculate accuracy
        false_positives = len(self.submitted_mistakes) - correct_mistakes
        false_negatives = total_actual_mistakes - correct_mistakes

        # Determine success based on accuracy threshold
        # For example, requiring 100% accuracy
        success = (correct_mistakes == total_actual_mistakes and false_positives == 0)

        return TaskResponse(success=success,
                            meta={"nr_of_steps_left": self.trajectory_length - step_statistics["current_step_id"] - 1,
                                  "correct_mistakes": correct_mistakes,
                                  "total_mistakes": total_actual_mistakes,
                                  "false_positives": false_positives,
                                  "false_negatives": false_negatives})

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.goal_description,
            "trajectory_length": self.trajectory_length,
            "starting_inventory": self.starting_inventory,
            "initial_state": self.starting_game_state.to_raw() if self.starting_game_state else None,
        }

    def setup_instance(self, instance):
        """Code to provision the task environment"""
        # First set up the base scenario
        ScenarioFactory.create_scenario(self.scenario, **self.scenario_params).deploy(instance)

        # Then apply random errors to the factory
        self.apply_factory_errors(instance)

    def enhance_response_with_task_output(self, response: str, task_response: TaskResponse) -> str:
        task_throughputs = task_response.meta.get("achievements", None)
        number_of_steps_left = task_response.meta.get("nr_of_steps_left", None)
        if task_throughputs:
            response += f"\n\nHere is the current throughput of your factory: {task_throughputs['dynamic']} created per 60 seconds"

        return response