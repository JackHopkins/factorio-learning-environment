import json
from typing import List

from fle.env.entities import Position
from fle.env.tools import Tool


class GetPath(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        # self.connection = connection
        # self.game_state = game_state

    def __call__(self, path_handle: int, max_attempts: int = 10) -> List[Position]:
        """
        Retrieve a path requested from the game, using backoff polling.
        """

        try:
            # Backoff polling
            wait_time = 0.032  # 32ms
            for attempt in range(max_attempts):
                response, elapsed = self.execute(path_handle)

                if response is None or response == {} or isinstance(response, str):
                    raise Exception("Could not request path (get_path)", response)

                path = json.loads(response)

                if path["status"] == "success":
                    list_of_positions = []
                    for pos in path["waypoints"]:
                        list_of_positions.append(Position(x=pos["x"], y=pos["y"]))
                    return list_of_positions

                elif path["status"] in ["not_found", "invalid_request"]:
                    raise Exception(
                        f"Path not found or invalid request: {path['status']}"
                    )
                elif path["status"] == "busy":
                    raise Exception("Pathfinder is busy, try again later")

                wait_time *= 2  # Exponential backoff

            raise Exception(f"Path request timed out after {max_attempts} attempts")

        except Exception as e:
            raise ConnectionError(
                f"Could not get path with handle {path_handle}"
            ) from e
