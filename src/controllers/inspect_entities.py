from typing import Dict, Any, List

from controllers._action import Action
from factorio_entities import Position
from factorio_instance import PLAYER
from models.zero_dict import ZeroDict


class InspectEntities(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.connection = connection
        self.game_state = game_state

    def __call__(self,
                 position: Position = None,
                 radius=10,
                 ) -> List[Dict[str, Any]]:
        """
        Inspect entities in a given radius around your position.
        :param radius: The radius to inspect
        :param position: The position to inspect (if None, use your position)
        :example: entities_around_origin = inspect_entities(10, Position(x=0, y=0))
        :return: A list of entities
        """
        
        if not isinstance(position, Position) and position is not None:
            raise ValueError("The first argument must be a Position object")

        if position is None:
            response, time_elapsed = self.execute(PLAYER, radius)
        else:
            response, time_elapsed = self.execute(PLAYER, radius, position.x, position.y)
        entities = []
        try:
            if isinstance(response, dict):
                entity_list = list(response.values())
                for entity in entity_list:
                    if entity["name"] == "laser_beam":
                        continue
                    position = tuple(entity["position"].values())

                    #if relative:
                    #    position = (position[0] - self.game_state.last_observed_player_location[0],
                    #                position[1] - self.game_state.last_observed_player_location[1])

                    entity_dict = {
                        "name": entity["name"],
                        "direction": entity["direction"],
                        "position": position
                    }

                    if "path_ends" in entity:
                        if len(entity["path_ends"]) > 1:
                            start = position
                            end = None
                            for _, path_end in entity["path_ends"].items():
                                if path_end["unit_number"] == min(
                                        [e["unit_number"] for e in entity["path_ends"].values()]):
                                    end = tuple(path_end["position"].values())
                                    break

                            entity_dict["start_position"] = start
                            entity_dict["end_position"] = end
                            entity_dict["quantity"] = len(entity["path_ends"])

                    if "warnings" in entity and entity['warnings']:
                        entity_dict["warning"] = ". ".join(entity['warnings'].values()).replace("_", " ")

                    if "contents" in entity and entity['contents']:
                        entity_dict["contents"] = {k: v for k, v in entity['contents'].items()}

                    if "crafted_items" in entity and entity['crafted_items']:
                        entity_dict["contents"] = {k: v for k, v in entity['crafted_items'].items()}

                    elif "crafted_items" in entity:
                        contains = {}
                        if entity['crafted_items']:
                            contains.update({k: v for k, v in entity['crafted_items'].items()})
                        if entity['ingredients']:
                            contains.update({k: v for k, v in entity['ingredients'].items()})
                        if contains:
                            entity_dict["contents"] = contains

                    if "status" not in entity_dict:
                        entity_dict["status"] = "empty" if "contents" not in entity_dict else "not empty"

                    entities.append(entity_dict)

            self.last_observed_player_location = (0, 0)
            if entities:
                return entities
            return {}
        except Exception as e:
            print(e)
            return {}
