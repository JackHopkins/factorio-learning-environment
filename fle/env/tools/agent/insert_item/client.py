from time import sleep
from typing import Optional, Union

from fle.env.entities import (
    Entity,
    EntityGroup,
    Position,
    BeltGroup,
    PipeGroup,
    PlaceholderEntity,
)
from fle.env.game_types import Prototype
from fle.env.tools.agent.get_entities.client import GetEntities
from fle.env.tools import Tool
from fle.env.instance import NONE


class InsertItem(Tool):
    def __init__(self, connection, game_state):
        self.get_entities = GetEntities(connection, game_state)
        super().__init__(connection, game_state)

    def __call__(
        self,
        entity: Prototype,
        target: Union[Entity, EntityGroup, PlaceholderEntity],
        quantity=5,
        tick: Optional[int] = None,
    ) -> Entity:
        """
        Insert an item into a target entity's inventory
        :param entity: Type to insert from inventory
        :param target: Entity to insert into (can be Entity, EntityGroup, or PlaceholderEntity)
        :param quantity: Quantity to insert
        :param tick: Game tick to execute this command at (for batch mode)
        :return: The target entity inserted into
        """
        assert quantity is not None, "Quantity cannot be None"
        assert isinstance(entity, Prototype), "The first argument must be a Prototype"

        # Check if PlaceholderEntity is being used with unsupported entity types
        if isinstance(target, PlaceholderEntity):
            # Check for belt group names that aren't supported with PlaceholderEntity
            belt_names = [
                "transport-belt",
                "fast-transport-belt",
                "express-transport-belt",
            ]
            if target.name in belt_names:
                raise Exception(
                    f"PlaceholderEntity cannot be used with belt entities ('{target.name}'). BeltGroup functionality requires actual entities."
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

            # Handle tick parameter - either batch mode or error
            if tick is not None:
                response, elapsed = self.execute_or_batch(
                    tick, self.player_index, name, quantity, x, y, NONE
                )

                # Check if we're in batch mode
                if isinstance(response, dict) and response.get("batched"):
                    # Return the original target as placeholder since we can't process the actual result yet
                    return target
                else:
                    # tick was provided but we're not in batch mode - this is invalid
                    raise Exception(
                        "tick parameter provided but batch mode is not active"
                    )

            # Original iterative approach for non-batch mode (tick is None)
            while items_inserted < quantity:
                response, elapsed = self.execute(self.player_index, name, 1, x, y, NONE)

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

        # Handle tick parameter for regular entities
        if tick is not None:
            response, elapsed = self.execute_or_batch(
                tick, self.player_index, name, quantity, x, y, target_name
            )

            # Check if we're in batch mode
            if isinstance(response, dict) and response.get("batched"):
                # Return the original target as placeholder since we can't process the actual result yet
                return target
            else:
                # tick was provided but we're not in batch mode - this is invalid
                raise Exception("tick parameter provided but batch mode is not active")
        else:
            # Regular execution without tick (non-batch mode)
            response, elapsed = self.execute(
                self.player_index, name, quantity, x, y, target_name
            )

        # Process response for non-batch execution
        if isinstance(response, str):
            raise Exception(f"Could not insert: {response.split(':')[-1].strip()}")

        cleaned_response = self.clean_response(response)
        if isinstance(cleaned_response, dict):
            if not isinstance(target, (BeltGroup, PipeGroup)):
                _type = type(target)

                # Handle PlaceholderEntity specially
                if isinstance(target, PlaceholderEntity):
                    # Find the prototype by name
                    matching_prototype = None
                    for prototype in Prototype:
                        if prototype.value[0] == target.name:
                            matching_prototype = prototype
                            break

                    if matching_prototype is None:
                        raise Exception(
                            f"No matching Prototype found for PlaceholderEntity with name '{target.name}'"
                        )
                    entity_class = matching_prototype.value[1]
                    target = entity_class(
                        prototype=matching_prototype, **cleaned_response
                    )
                else:
                    # Original logic for non-PlaceholderEntity
                    prototype = Prototype._value2member_map_[
                        (target.name, type(target))
                    ]
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
