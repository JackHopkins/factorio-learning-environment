from time import sleep
from typing import Union

from fle.env.entities import Entity, EntityGroup, Position, BeltGroup, PipeGroup
from fle.env.game_types import Prototype
from fle.env.tools.agent.get_entities.client import GetEntities
from fle.env.tools import Tool


class InsertItem(Tool):
    def __init__(self, connection, game_state):
        self.get_entities = GetEntities(connection, game_state)
        super().__init__(connection, game_state)

    def __call__(
        self, entity: Prototype, target: Union[Entity, EntityGroup], quantity=5
    ) -> Entity:
        """
        Insert an item into a target entity's inventory
        :param entity: Type to insert from inventory
        :param target: Entity to insert into
        :param quantity: Quantity to insert
        :return: The target entity inserted into
        """
        assert quantity is not None, "Quantity cannot be None"
        assert isinstance(entity, Prototype), "The first argument must be a Prototype"
        assert isinstance(target, Entity) or isinstance(target, EntityGroup), (
            "The second argument must be an Entity or EntityGroup, you passed in a {0}".format(
                type(target)
            )
        )

        if isinstance(target, Position):
            x, y = target.x, target.y
        else:
            x, y = self.get_position(target.position)

        name, _ = entity.value
        target_name = target.name

        # For belt groups, insert items one at a time
        if isinstance(target, BeltGroup):
            items_inserted = 0
            last_response = None
            pos = (
                target.inputs[0].position
                if len(target.inputs) > 0
                else target.outputs[0].position
                if len(target.outputs) > 0
                else (None, None)
            )
            x, y = pos.x, pos.y
            if not x or not y:
                x, y = target.belts[0].position.x, target.belts[0].position.y

            while items_inserted < quantity:
                response, elapsed = self.execute(self.player_index, name, 1, x, y, None)

                if isinstance(response, str):
                    if (
                        "Could not find" not in response
                    ):  # Don't raise if belt is just full
                        raise Exception(
                            "Could not insert: " + response.split(":")[-1].strip()
                        )
                    break

                items_inserted += 1
                last_response = response
                sleep(0.05)

            if last_response:
                group = self.get_entities(
                    {
                        Prototype.TransportBelt,
                        Prototype.FastTransportBelt,
                        Prototype.ExpressTransportBelt,
                    },
                    position=target.position,
                )
                if not group:
                    raise Exception(
                        f"Could not find transport belt at position: {target.position}"
                    )
                return group[0]

            return target

        response, elapsed = self.execute(
            self.player_index, name, quantity, x, y, target_name
        )

        if isinstance(response, str):
            raise Exception(f"Could not insert: {response.split(':')[-1].strip()}")

        cleaned_response = self.clean_response(response)
        if isinstance(cleaned_response, dict):
            if not isinstance(target, (BeltGroup, PipeGroup)):
                _type = type(target)
                prototype = Prototype._value2member_map_[(target.name, type(target))]
                target = _type(prototype=prototype, **cleaned_response)
            elif isinstance(target, BeltGroup):
                group = self.get_entities(
                    {
                        Prototype.TransportBelt,
                        Prototype.FastTransportBelt,
                        Prototype.ExpressTransportBelt,
                    },
                    position=target.position,
                )
                if not group:
                    raise Exception(
                        f"Could not find transport belt at position: {target.position}"
                    )
                return group[0]
            elif isinstance(target, PipeGroup):
                group = self.get_entities({Prototype.Pipe}, position=target.position)
                if not group:
                    raise Exception(
                        f"Could not find pipes at position: {target.position}"
                    )
                return group[0]
            else:
                raise Exception("Unknown Entity Group type")
        return target
