from time import sleep

from controllers._action import Action
from controllers.get_entity import GetEntity
from controllers.move_to import MoveTo
from controllers.nearest import Nearest
from factorio_entities import Position
from factorio_instance import PLAYER
from factorio_types import Resource


class HarvestResource(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.move_to = MoveTo(connection, game_state)
        self.nearest = Nearest(connection, game_state)
        self.get_entity = GetEntity(connection, game_state)

    def __call__(self,
                 position: Position,
                 quantity=1,
                 radius=20
                 ) -> int:
        """
        Harvest a resource at position (x, y) if it exists on the world.
        :param position: Position to harvest resource
        :param quantity: Quantity to harvest
        :example harvest_resource(nearest(Resource.Coal), 5)
        :example harvest_resource(nearest(Resource.Stone), 5)
        :return: The quantity of the resource harvested
        """
        x, y = self.get_position(position)

        # If not fast mode, we need to identify what resource is at the x, y position
        # Because if the first pass of the harvest doesn't get the necessary
        resource_to_harvest = Resource.IronOre
        if not self.game_state.fast:
            resource_to_harvest = self.get_resource_type_at_position(position)

        # Now we attempt to harvest.
        # In fast mode, this will always be successful (because we don't check if the resource is reachable)
        response, elapsed = self.execute(PLAYER, x, y, quantity, radius)

        if response != {} and response == 0 or isinstance(response, str):
            raise Exception("Could not harvest.", response)

        # If `fast` is turned off - we need to long poll the game state to ensure the player has moved
        if not self.game_state.fast:
            remaining_steps = self.connection.send_command(
                f'/silent-command rcon.print(global.actions.get_harvest_queue_length({PLAYER}))')
            attempt = 0
            max_attempts = 10
            while remaining_steps != '0' and attempt < max_attempts:
                sleep(0.5)
                remaining_steps = self.connection.send_command(
                    f'/silent-command rcon.print(global.actions.get_harvest_queue_length({PLAYER}))')

            max_attempts = 5
            attempt = 0
            while int(response) < quantity and attempt < max_attempts:
                nearest_resource = self.nearest(resource_to_harvest)
                self.move_to(nearest_resource)
                try:
                    harvested = self.__call__(nearest_resource, quantity - int(response))
                    return int(response) + harvested
                except Exception as e:
                    attempt += 1

            if int(response) < quantity:
                raise Exception(f"Could not harvest {quantity} {resource_to_harvest}")

        return response

    def get_resource_type_at_position(self, position: Position):
        x, y = self.get_position(position)
        entity_at_position = self.connection.send_command(
            f'/silent-command rcon.print(global.actions.get_resource_name_at_position({PLAYER}, {x}, {y}))')
        if entity_at_position.startswith('tree'):
            return Resource.Wood
        elif entity_at_position.startswith('coal'):
            return Resource.Coal
        elif entity_at_position.startswith('iron'):
            return Resource.IronOre
        elif entity_at_position.startswith('stone'):
            return Resource.Stone
        raise Exception(f"Could not find resource to harvest at {x}, {y}")