from time import sleep
from typing import List, Set, Union
from memoization import cached

from fle.env.entities import Position, Entity, EntityGroup
from fle.env.game_types import Prototype
from fle.env.tools.agent.connect_entities.groupable_entities import (
    agglomerate_groupable_entities,
)
from fle.env.tools import Tool


class GetEntities(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    @cached(max_size=16, ttl=0.1)
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
        :param player_only: If True, only player entities are returned, otherwise terrain features too.
        :return: Found entities
        """

        try:
            if not isinstance(position, Position) and position is not None:
                raise ValueError("The second argument must be a Position object")

            if not isinstance(entities, Set):
                entities = set([entities])

            # Handle group prototypes by expanding them to their component types
            expanded_entities = set()
            group_requests = set()

            for entity in entities:
                if entity == Prototype.BeltGroup:
                    # For belt groups, search for all belt types and group them
                    belt_types = {
                        Prototype.TransportBelt,
                        Prototype.FastTransportBelt,
                        Prototype.ExpressTransportBelt,
                        Prototype.UndergroundBelt,
                        Prototype.FastUndergroundBelt,
                        Prototype.ExpressUndergroundBelt,
                    }
                    expanded_entities.update(belt_types)
                    group_requests.add(Prototype.BeltGroup)
                elif entity == Prototype.PipeGroup:
                    # For pipe groups, search for pipe types and group them
                    pipe_types = {Prototype.Pipe, Prototype.UndergroundPipe}
                    expanded_entities.update(pipe_types)
                    group_requests.add(Prototype.PipeGroup)
                elif entity == Prototype.ElectricityGroup:
                    # For electricity groups, search for pole types and group them
                    pole_types = {
                        Prototype.SmallElectricPole,
                        Prototype.MediumElectricPole,
                        Prototype.BigElectricPole,
                    }
                    expanded_entities.update(pole_types)
                    group_requests.add(Prototype.ElectricityGroup)
                else:
                    expanded_entities.add(entity)

            # Use expanded entities for the Lua query
            query_entities = expanded_entities

            # Serialize entity_names as a string
            entity_names = (
                "["
                + ",".join([f'"{entity.value[0]}"' for entity in query_entities])
                + "]"
                if query_entities
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

                # Apply standard filtering - check against expanded entities too
                if (
                    entities
                    and matching_prototype not in entities
                    and matching_prototype not in expanded_entities
                ):
                    continue

                metaclass = matching_prototype.value[1]
                while isinstance(metaclass, tuple):
                    metaclass = metaclass[1]

                # Process nested dictionaries (like inventories)
                for key, value in entity_data.items():
                    if isinstance(value, dict):
                        entity_data[key] = self.process_nested_dict(value)

                entity_data["prototype"] = matching_prototype

                # remove all empty values from the entity_data dictionary
                entity_data = {
                    k: v for k, v in entity_data.items() if v or isinstance(v, int)
                }

                try:
                    if "inventory" in entity_data:
                        if isinstance(entity_data["inventory"], list):
                            for inv in entity_data["inventory"]:
                                entity_data["inventory"] += inv
                        else:
                            inventory_data = {
                                k: v
                                for k, v in entity_data["inventory"].items()
                                if v or isinstance(v, int)
                            }
                            entity_data["inventory"] = inventory_data

                    entity = metaclass(**entity_data)
                    entities_list.append(entity)
                except Exception as e1:
                    print(f"Could not create {entity_data['name']} object: {e1}")

            # Group entities when:
            # 1. User explicitly requests group types, OR
            # 2. User provides a position filter (suggesting they want nearby entities grouped), OR
            # 3. No specific entities requested (get all entities - should be grouped), OR
            # 4. User requests individual pole entities (restore original behavior - poles are always grouped)
            pole_types = {
                Prototype.SmallElectricPole,
                Prototype.MediumElectricPole,
                Prototype.BigElectricPole,
            }
            should_group = (
                not entities  # No filter = group everything
                or any(
                    proto
                    in {
                        Prototype.ElectricityGroup,
                        Prototype.PipeGroup,
                        Prototype.BeltGroup,
                    }
                    for proto in entities
                )  # Explicit group request
                or (
                    entities and position is not None
                )  # Individual entities with position filter = group for convenience
            )

            if should_group:
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

            # Final filtering after grouping is complete
            if entities:
                filtered_entities = []
                for entity in entities_list:
                    # Check entity prototype or group type
                    if hasattr(entity, "prototype") and (
                        entity.prototype in entities
                        or entity.prototype in expanded_entities
                    ):
                        filtered_entities.append(entity)
                    elif hasattr(entity, "__class__"):
                        # Handle group entities
                        if entity.__class__.__name__ == "ElectricityGroup":
                            pole_types = {
                                Prototype.SmallElectricPole,
                                Prototype.MediumElectricPole,
                                Prototype.BigElectricPole,
                            }
                            if Prototype.ElectricityGroup in group_requests:
                                # Explicit group request - return the group
                                filtered_entities.append(entity)
                            elif (
                                any(pole_type in entities for pole_type in pole_types)
                                and position is not None
                            ):
                                # Individual poles requested with position - return group for convenience
                                filtered_entities.append(entity)
                            elif any(pole_type in entities for pole_type in pole_types):
                                # Individual poles requested - return group (restores original behavior)
                                # Power poles are inherently networked, so groups are more useful than individuals
                                filtered_entities.append(entity)
                        elif entity.__class__.__name__ == "PipeGroup":
                            pipe_types = {Prototype.Pipe, Prototype.UndergroundPipe}
                            if Prototype.PipeGroup in group_requests:
                                # Explicit group request - return the group
                                filtered_entities.append(entity)
                            elif (
                                any(pipe_type in entities for pipe_type in pipe_types)
                                and position is not None
                            ):
                                # Individual pipes requested with position - return group for convenience
                                filtered_entities.append(entity)
                            elif any(pipe_type in entities for pipe_type in pipe_types):
                                # Individual pipes requested - return group (restores original behavior)
                                # Pipes are inherently networked, so groups are more useful than individuals
                                filtered_entities.append(entity)
                        elif entity.__class__.__name__ == "BeltGroup":
                            belt_types = {
                                Prototype.TransportBelt,
                                Prototype.FastTransportBelt,
                                Prototype.ExpressTransportBelt,
                                Prototype.UndergroundBelt,
                                Prototype.FastUndergroundBelt,
                                Prototype.ExpressUndergroundBelt,
                            }
                            if Prototype.BeltGroup in group_requests:
                                # Explicit group request - return the group
                                filtered_entities.append(entity)
                            elif (
                                any(belt_type in entities for belt_type in belt_types)
                                and position is not None
                            ):
                                # Individual belts requested with position - return group for convenience
                                filtered_entities.append(entity)
                            elif (
                                any(belt_type in entities for belt_type in belt_types)
                                and position is None
                            ):
                                # Individual belts requested without position - extract individual belts from group
                                for belt in entity.belts:
                                    if (
                                        hasattr(belt, "prototype")
                                        and belt.prototype in entities
                                    ):
                                        filtered_entities.append(belt)
                        elif entity.__class__.__name__ == "WallGroup":
                            # WallGroup doesn't have a corresponding Prototype, but include if present
                            filtered_entities.append(entity)
                entities_list = filtered_entities

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
