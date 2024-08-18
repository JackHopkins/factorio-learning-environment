from controllers._action import Action
from factorio_instance import PLAYER
from factorio_types import Prototype


class CraftItem(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.connection = connection
        self.game_state = game_state

    def __call__(self, entity: Prototype, quantity: int = 1) -> bool:
        """
        Craft an item from a Prototype if the ingredients exist in your inventory.
        :param entity: Entity to craft
        :param quantity: Quantity to craft
        :example craft_item(Prototype.Pipe, 1)
        :return: True if crafting was successful
        """

        if hasattr(entity, 'value'):
            name, _ = entity.value
        else:
            name = entity

        success, elapsed = self.execute(PLAYER, name, quantity)
        if success != {} and success != 1:
            if success is None:
                raise Exception(f"Could not craft a {name} - Ingredients cannot be crafted by hand.")
            else:
                raise Exception(f"Could not craft a {name} - {success}")
        return True
