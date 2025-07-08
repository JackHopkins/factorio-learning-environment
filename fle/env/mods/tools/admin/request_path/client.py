from fle.env.entities import Position
from fle.env.tools import Tool


class RequestPath(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(
        self,
        start: Position,
        finish: Position,
        max_attempts: int = 10,
        allow_paths_through_own_entities=False,
        radius=0.5,
        entity_size=1,
        resolution=0,
    ) -> int:
        """
        Asynchronously request a path from start to finish from the game.
        """
        assert isinstance(start, Position), "Start position must be a Position object"
        assert isinstance(finish, Position), "Finish position must be a Position object"

        try:
            start_x, start_y = self.get_position(start)
            goal_x, goal_y = finish.x, finish.y

            response, elapsed = self.execute(
                self.player_index,
                start_x,
                start_y,
                goal_x,
                goal_y,
                radius,
                allow_paths_through_own_entities,
                entity_size,
                resolution,
            )

            if response is None or response == {} or isinstance(response, str):
                raise Exception("Could not request path (request_path)", response)

            path_handle = int(response)

            return path_handle

        except Exception as e:
            raise Exception(f"Could not get path from {start} to {finish}", e)
