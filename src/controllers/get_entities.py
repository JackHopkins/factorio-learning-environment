from collections import defaultdict
from typing import List, Set, Union
from controllers._action import Action
from factorio_entities import Position, Entity, BeltGroup, TransportBelt
from factorio_instance import PLAYER
from factorio_types import Prototype
from utilities.merge_transport_belts import agglomerate_transport_belts


class GetEntities(Action):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, entities: Set[Prototype] = set(), position: Position = None, radius: int = 1000) -> List[Entity]:
        """
        Get entities within a radius of a given position.
        :param position: Position to search around. Can be a Position object or "player" for player's position.
        :param radius: Radius to search within.
        :param entities: Set of entity prototypes to filter by. If empty, all entities are returned.
        :return: List of Entity objects
        """
        try:
            if not isinstance(position, Position) and position is not None:
                raise ValueError("The second argument must be a Position object")

                # Serialize entity_names as a string
            entity_names = "[" + ",".join(
                    [f'"{entity.value[0]}"' for entity in entities]) + "]" if entities else "[]"

            if position is None:
                response, time_elapsed = self.execute(PLAYER, radius, entity_names)
            else:
                response, time_elapsed = self.execute(PLAYER, radius, entity_names, position.x, position.y)

            if (not isinstance(response, dict) and not response) or isinstance(response, str):# or (isinstance(response, dict) and not response):
                raise Exception("Could not get entities", response)

            entities_list = []
            belt_list = []
            for entity_data in response:
                # Find the matching Prototype
                matching_prototype = None
                for prototype in Prototype:
                    if prototype.value[0] == entity_data['name'].replace('_', '-'):
                        matching_prototype = prototype
                        break

                if matching_prototype is None:
                    print(f"Warning: No matching Prototype found for {entity_data['name']}")
                    continue

                if matching_prototype not in entities and entities:
                    continue
                metaclass = matching_prototype.value[1]

                # Process nested dictionaries (like inventories)
                for key, value in entity_data.items():
                    if isinstance(value, dict):
                        entity_data[key] = self.process_nested_dict(value)

                entity_data['prototype'] = prototype
                try:
                    entity = metaclass(**entity_data)
                    if entity.prototype == Prototype.TransportBelt:
                        belt_list.append(entity)
                    else:
                        entities_list.append(entity)
                except Exception as e1:
                    print(f"Could not create {entity_data['name']} object: {e1}")

            belt_groups = agglomerate_transport_belts(belt_list)
            entities_list.extend(belt_groups)

            return entities_list

        except Exception as e:
            raise Exception(f"Error in GetEntities: {e}")

    def process_nested_dict(self, nested_dict):
        """Helper method to process nested dictionaries"""
        if isinstance(nested_dict, dict):
            if all(isinstance(key, int) for key in nested_dict.keys()):
                return [self.process_nested_dict(value) for value in nested_dict.values()]
            else:
                return {key: self.process_nested_dict(value) for key, value in nested_dict.items()}
        return nested_dict