import os
from time import sleep
from typing import List

from fle.env.entities import Position
from fle.env.tools import Tool

# Default budget: 120 backoff polls (~115s wall-clock) instead of 10 (~6.5s).
# Long-distance move_to on fresh worlds has to wait for Factorio's
# chunk-generation before A* can start; 10 polls is not enough, and
# empirically 30 and 60 still miss occasionally. Override at runtime with
# `FLE_GETPATH_MAX_ATTEMPTS`.
_DEFAULT_MAX_ATTEMPTS = int(os.environ.get("FLE_GETPATH_MAX_ATTEMPTS", "120"))


class GetPath(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        # self.connection = connection
        # self.game_state = game_state

    def __call__(
        self,
        path_handle: int,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
    ) -> List[Position]:
        """Retrieve a path requested from the game, using backoff polling.

        The path is computed asynchronously on the Factorio side; this
        method polls `get_path(path_handle)` with exponential backoff
        (50ms → 1s cap) for up to ``max_attempts`` rounds before
        giving up with a timeout exception.

        The default can also be overridden via the
        ``FLE_GETPATH_MAX_ATTEMPTS`` environment variable, which is read
        at module import time.
        """

        try:
            # Backoff polling
            wait_time = 0.05  # 50ms initial wait
            for attempt in range(max_attempts):
                response, elapsed = self.execute(path_handle)

                if response is None or response == {} or isinstance(response, str):
                    raise Exception("Could not request path (get_path)", response)

                path = response

                # Strip quotes from status if present (backwards compatibility)
                status = path.get("status", "")
                if status.startswith('"') and status.endswith('"'):
                    status = status[1:-1]

                if status == "success":
                    list_of_positions = []
                    for pos in path["waypoints"]:
                        list_of_positions.append(Position(x=pos["x"], y=pos["y"]))
                    return list_of_positions

                elif status in ["not_found", "invalid_request"]:
                    raise Exception(f"Path not found or invalid request: {status}")
                elif status == "busy":
                    raise Exception("Pathfinder is busy, try again later")

                # Path is still pending - wait before retrying
                if status == "pending":
                    sleep(wait_time)
                    wait_time = min(
                        wait_time * 2, 1.0
                    )  # Exponential backoff, max 1 second
                    continue

                # Unknown status - wait and retry
                sleep(wait_time)
                wait_time = min(wait_time * 2, 1.0)

            raise Exception(
                f"Path request timed out after {max_attempts} attempts "
                "(set FLE_GETPATH_MAX_ATTEMPTS higher if your world is slow "
                "to chunk-generate)"
            )

        except Exception as e:
            # raise ConnectionError(
            #     f"Could not get path with handle {path_handle}"
            # ) from e
            raise e
