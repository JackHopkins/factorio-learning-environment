from time import sleep
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
            wait_time = 0.032
            for attempt in range(max_attempts):
                response, elapsed = self.execute(path_handle)

                if response is None or response == {}:
                    raise Exception(
                        f"Could not request path (get_path) - got None or empty response for handle {path_handle}"
                    )

                # Response is already a dict from Lua, no need to parse JSON
                path = response

                if path["status"] == "success":
                    list_of_positions = []
                    waypoints = path["waypoints"]

                    # Handle waypoints as either dict (Lua array with numeric keys) or list
                    if isinstance(waypoints, dict):
                        # Convert dict with numeric keys to sorted list
                        waypoints = [waypoints[k] for k in sorted(waypoints.keys())]

                    for pos in waypoints:
                        list_of_positions.append(Position(x=pos["x"], y=pos["y"]))
                    return list_of_positions

                elif path["status"] == "not_found":
                    # Path couldn't be found - likely async handler hasn't populated it yet
                    # But if we've been waiting too long, the request is stuck
                    if (
                        attempt >= 8
                    ):  # ~5 seconds total (32ms + 64ms + 128ms + 256ms + 512ms + 1s + 1s + 1s)
                        # Request is stuck - path will never appear
                        # This happens with container reuse when the request_id doesn't exist
                        raise Exception(
                            f"Path request {path_handle} stuck after {attempt + 1} attempts (~5s). "
                            f"Likely container reuse issue - path will never be created."
                        )
                    sleep(wait_time)
                    wait_time = min(wait_time * 2, 1.0)
                    continue
                elif path["status"] in ["busy", "pending", "invalid_request"]:
                    # Path is still processing - wait and retry
                    sleep(wait_time)
                    wait_time = min(
                        wait_time * 2, 1.0
                    )  # Exponential backoff, cap at 1s
                    continue

                # Unknown status - wait and retry
                sleep(wait_time)
                wait_time = min(wait_time * 2, 1.0)

            raise Exception(f"Path request timed out after {max_attempts} attempts")

        except Exception as e:
            # Preserve the original exception message for path stuck detection
            raise ConnectionError(
                f"Could not get path with handle {path_handle}: {str(e)}"
            ) from e
