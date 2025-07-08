from time import sleep

from fle.env.entities import Position
from fle.env.game_types import Resource
from fle.env.tools.agent.get_entity.client import GetEntity
from fle.env.tools.agent.move_to.client import MoveTo
from fle.env.tools.agent.nearest.client import Nearest
from fle.env.tools import Tool


class HarvestResource(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.move_to = MoveTo(connection, game_state)
        self.nearest = Nearest(connection, game_state)
        self.get_entity = GetEntity(connection, game_state)

    def __call__(self, position: Position, quantity=1, radius=10) -> int:
        """
        Harvest a resource at position (x, y) if it exists on the world.
        :param position: Position to harvest resource
        :param quantity: Quantity to harvest
        :example harvest_resource(nearest(Resource.Coal), 5)
        :example harvest_resource(nearest(Resource.Stone), 5)
        :return: The quantity of the resource harvested
        """
        assert isinstance(position, Position), (
            "First argument must be a Position object"
        )

        x, y = self.get_position(position)

        # If not fast mode, we need to identify what resource is at the x, y position
        # Because if the first pass of the harvest doesn't get the necessary
        resource_to_harvest = Resource.IronOre
        if not self.game_state.instance.fast:
            resource_to_harvest = self.get_resource_type_at_position(position)

        # Now we attempt to harvest.
        # In fast mode, this will always be successful (because we don't check if the resource is reachable)
        response, elapsed = self.execute(self.player_index, x, y, quantity, radius)

        if response != {} and response == 0 or isinstance(response, str):
            msg = response.split(":")[-1].strip()
            raise Exception(f"Could not harvest. {msg}")

        # If `fast` is turned off - we need to long poll the game state to ensure the player has moved
        if not self.game_state.instance.fast:
            remaining_steps = self.connection.rcon_client.send_command(
                f"/silent-command rcon.print(global.actions.get_harvest_queue_length({self.player_index}))"
            )
            attempt = 0
            max_attempts = 10
            while remaining_steps != "0" and attempt < max_attempts:
                sleep(0.5)
                remaining_steps = self.connection.rcon_client.send_command(
                    f"/silent-command rcon.print(global.actions.get_harvest_queue_length({self.player_index}))"
                )

            max_attempts = 50
            attempt = 0
            while int(response) < quantity and attempt < max_attempts:
                nearest_resource = self.nearest(resource_to_harvest)

                if not nearest_resource.is_close(self.game_state.player_location, 2):
                    self.move_to(nearest_resource)

                try:
                    harvested = self.__call__(
                        nearest_resource, quantity - int(response)
                    )
                    return int(response) + harvested
                except Exception:
                    attempt += 1

            if int(response) < quantity:
                raise Exception(f"Could not harvest {quantity} {resource_to_harvest}")

        return response

    def get_resource_type_at_position(self, position: Position):
        x, y = self.get_position(position)
        entity_at_position = self.connection.rcon_client.send_command(
            f"/silent-command rcon.print(global.actions.get_resource_name_at_position({self.player_index}, {x}, {y}))"
        )
        if entity_at_position.startswith("tree"):
            return Resource.Wood
        elif entity_at_position.startswith("coal"):
            return Resource.Coal
        elif entity_at_position.startswith("iron"):
            return Resource.IronOre
        elif entity_at_position.startswith("stone"):
            return Resource.Stone
        raise Exception(f"Could not find resource to harvest at {x}, {y}")
