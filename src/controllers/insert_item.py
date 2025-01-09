from typing import Tuple, Union

import pydantic

from controllers.__action import Action
from factorio_entities import Entity, EntityGroup, Position
from factorio_instance import PLAYER
from factorio_types import Prototype


class InsertItem(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
    def __call__(self, entity: Prototype, target: Union[Entity, EntityGroup, Position], quantity=5) -> Entity:
        """
        The agent inserts an item into a target entity's inventory
        :param entity: Entity type to insert from inventory
        :param target: Entity to insert into
        :param quantity: Quantity to insert
        :example: insert_item(Prototype.IronPlate, nearest(Prototype.IronChest), 5)
        :return: The target entity inserted into
        """
        assert quantity is not None, "Quantity cannot be None"
        assert isinstance(entity, Prototype), "The first argument must be a Prototype"
        assert isinstance(target, Entity) or isinstance(target, EntityGroup), "The second argument must be an Entity or EntityGroup, you passed in a {0}".format(type(target))

        if isinstance(target, Position):
            x, y = target.x, target.y
        else:
            x, y = self.get_position(target.position)

        name, _ = entity.value

        response, elapsed = self.execute(PLAYER, name, quantity, x, y)

        if isinstance(response, str):
            raise Exception("Could not insert", response)

        cleaned_response = self.clean_response(response)
        if isinstance(cleaned_response, dict):
            prototype = Prototype._value2member_map_[(target.name, type(target))]
            target = type(target)(prototype=prototype, **cleaned_response)

        return target
