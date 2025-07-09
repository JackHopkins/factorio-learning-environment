from time import sleep
from typing import List, Set, Union
from fle.env.entities import Position, Entity, EntityGroup
from fle.env.game_types import Prototype
from fle.env.tools.agent.connect_entities.groupable_entities import (
    agglomerate_groupable_entities,
)
from fle.env.tools import Tool


class GetEntities(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(
        self,
        entities: Union[Set[Prototype], Prototype] = set(),
        position: Position = None,
        radius: float = 1000,
    ) -> List[Union[Entity, EntityGroup]]:
        """
        Get entities within a radius of a given position.
        :param entities: Set of entity prototypes to filter by. If empty, all entities are returned.
        :param position: Position to search around. Can be a Position object or "player" for player's position.
        :param radius: Radius to search within.
        :return: Found entities
        """
        try:
            if not isinstance(position, Position) and position is not None:
                raise ValueError("The second argument must be a Position object")

            if not isinstance(entities, Set):
                entities = set([entities])

                # Serialize entity_names as a string
            entity_names = (
                "[" + ",".join([f'"{entity.value[0]}"' for entity in entities]) + "]"
                if entities
                else "[]"
            )

            # We need to add a small 50ms sleep to ensure that the entities have updated after previous actions
            sleep(0.05)

            if position is None:
                response, time_elapsed = self.execute(
                    self.player_index, radius, entity_names
                )
            else:
                response, time_elapsed = self.execute(
                    self.player_index, radius, entity_names, position.x, position.y
                )

            if not response:
                return []

            if (not isinstance(response, dict) and not response) or isinstance(
                response, str
            ):  # or (isinstance(response, dict) and not response):
                raise Exception("Could not get entities", response)

            entities_list = []
            for raw_entity_data in response:
                if isinstance(raw_entity_data, list):
                    continue

                entity_data = self.clean_response(raw_entity_data)
                # Find the matching Prototype
                matching_prototype = None
                for prototype in Prototype:
                    if prototype.value[0] == entity_data["name"].replace("_", "-"):
                        matching_prototype = prototype
                        break

                if matching_prototype is None:
                    print(
                        f"Warning: No matching Prototype found for {entity_data['name']}"
                    )
                    continue

                if matching_prototype not in entities and entities:
                    continue
                metaclass = matching_prototype.value[1]
                while isinstance(metaclass, tuple):
                    metaclass = metaclass[1]

                # Process nested dictionaries (like inventories)
                for key, value in entity_data.items():
                    if isinstance(value, dict):
                        entity_data[key] = self.process_nested_dict(value)

                entity_data["prototype"] = prototype

                # remove all empty values from the entity_data dictionary
                entity_data = {
                    k: v for k, v in entity_data.items() if v or isinstance(v, int)
                }

                try:
                    entity = metaclass(**entity_data)
                    entities_list.append(entity)
                except Exception as e1:
                    print(f"Could not create {entity_data['name']} object: {e1}")

            # get all pipes into a list
            pipes = [
                entity
                for entity in entities_list
                if hasattr(entity, "prototype")
                and entity.prototype in (Prototype.Pipe, Prototype.UndergroundPipe)
            ]
            group = agglomerate_groupable_entities(pipes)
            [entities_list.remove(pipe) for pipe in pipes]
            entities_list.extend(group)

            poles = [
                entity
                for entity in entities_list
                if hasattr(entity, "prototype")
                and entity.prototype
                in (
                    Prototype.SmallElectricPole,
                    Prototype.BigElectricPole,
                    Prototype.MediumElectricPole,
                )
            ]
            group = agglomerate_groupable_entities(poles)
            [entities_list.remove(pole) for pole in poles]
            entities_list.extend(group)

            walls = [
                entity
                for entity in entities_list
                if hasattr(entity, "prototype")
                and entity.prototype == Prototype.StoneWall
            ]
            group = agglomerate_groupable_entities(walls)
            [entities_list.remove(wall) for wall in walls]
            entities_list.extend(group)

            belt_types = (
                Prototype.TransportBelt,
                Prototype.FastTransportBelt,
                Prototype.ExpressTransportBelt,
                Prototype.UndergroundBelt,
                Prototype.FastUndergroundBelt,
                Prototype.ExpressUndergroundBelt,
            )
            belts = [
                entity
                for entity in entities_list
                if hasattr(entity, "prototype") and entity.prototype in belt_types
            ]
            group = agglomerate_groupable_entities(belts)
            [entities_list.remove(belt) for belt in belts]
            entities_list.extend(group)

            return entities_list

        except Exception as e:
            raise Exception(f"Error in GetEntities: {e}")

    def process_nested_dict(self, nested_dict):
        """Helper method to process nested dictionaries"""
        if isinstance(nested_dict, dict):
            if all(isinstance(key, int) for key in nested_dict.keys()):
                return [
                    self.process_nested_dict(value) for value in nested_dict.values()
                ]
            else:
                return {
                    key: self.process_nested_dict(value)
                    for key, value in nested_dict.items()
                }
        return nested_dict
