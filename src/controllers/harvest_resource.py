from controllers._action import Action
from controllers.move_to import MoveTo
from factorio_entities import Position
from factorio_instance import PLAYER


class HarvestResource(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.move_to = MoveTo(connection, game_state)

    def __call__(self,
                 position: Position,
                 quantity=1,
                 radius=10
                 ) -> None:
        """
        Harvest a resource at position (x, y) if it exists on the world.
        :param position: Position to harvest resource
        :param quantity: Quantity to harvest
        :example harvest_resource(nearest(Resource.Coal), 5)
        :example harvest_resource(nearest(Resource.Stone), 5)
        :return: True if harvest was successful
        """
        x, y = self.get_position(position)

        response, elapsed = self.execute(PLAYER, x, y, quantity, radius)
        #if isinstance(response, str) and response.endswith("Cannot reach entity"):
        #    response, elapsed = self.execute(PLAYER, x, y, quantity, radius)

        if response != {} and response != 1:
            raise Exception("Could not harvest.", response)
