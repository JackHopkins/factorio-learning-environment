from typing import Dict, Any
from controllers._action import Action
from factorio_entities import Position
from factorio_instance import PLAYER, Direction
from factorio_types import InspectionResults, EntityInfo, EntityStatus


class InspectEntities(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self,
                 position: Position = None,
                 radius=10,
                 ) -> InspectionResults:
        """
        Inspect entities in a given radius around your position.
        :param radius: The radius to inspect
        :param position: The position to inspect (if None, use your position)
        :example: entities_around_origin = inspect_entities(10, Position(x=0, y=0))
        :return: An InspectionResults object containing a list of entities
        """

        if not isinstance(position, Position) and position is not None:
            raise ValueError("The first argument must be a Position object")

        if position is None:
            response, time_elapsed = self.execute(PLAYER, radius)
        else:
            response, time_elapsed = self.execute(PLAYER, radius, position.x, position.y)

        return self.from_inspect_entities_response(response, time_elapsed, radius)

    def from_inspect_entities_response(self, response: Dict[str, Any], time_elapsed: float,
                                       radius: float) -> InspectionResults:
        entities = []
        try:
            if isinstance(response, dict):
                for entity in response.values():
                    if entity["name"] == "laser_beam":
                        continue

                    position = tuple(entity["position"].values())

                    # direction is 'west', 'east', 'north', 'south' - we need to convert to 0-3
                    if entity["direction"] == "west":
                        entity["direction"] = Direction.LEFT.value
                    elif entity["direction"] == "east":
                        entity["direction"] = Direction.RIGHT.value
                    elif entity["direction"] == "north":
                        entity["direction"] = Direction.UP.value
                    elif entity["direction"] == "south":
                        entity["direction"] = Direction.DOWN.value

                    entity_info = EntityInfo(
                        name=entity["name"].replace("_", "-"),
                        direction=entity["direction"],
                        position=position
                    )

                    if "path_ends" in entity and len(entity["path_ends"]) > 1:
                        entity_info.start_position = position
                        entity_info.quantity = len(entity["path_ends"])
                        for _, path_end in entity["path_ends"].items():
                            if path_end["unit_number"] == min(e["unit_number"] for e in entity["path_ends"].values()):
                                entity_info.end_position = tuple(path_end["position"].values())
                                break

                    if "warnings" in entity and entity['warnings']:
                        entity_info.warning = ". ".join(entity['warnings'].values()).replace("_", " ")

                    if "contents" in entity and entity['contents']:
                        entity_info.contents = {k: v for k, v in entity['contents'].items()}
                    elif "crafted_items" in entity:
                        contains = {}
                        if entity['crafted_items']:
                            contains.update({k: v for k, v in entity['crafted_items'].items()})
                        if entity.get('ingredients'):
                            contains.update({k: v for k, v in entity['ingredients'].items()})
                        if contains:
                            entity_info.contents = contains

                    entity_info.status = EntityStatus.from_string(entity.get('status', 'normal'))

                    entities.append(entity_info)

            self.last_observed_player_location = (0, 0)
            return InspectionResults(entities=entities, time_elapsed=time_elapsed, radius=radius,
                                     player_position=self.last_observed_player_location)
        except Exception as e:
            print(e)
            return InspectionResults(entities=[], time_elapsed=time_elapsed, radius=radius)