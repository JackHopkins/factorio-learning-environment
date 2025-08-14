import pytest
import unittest

from fle.env.game.game_types import Prototype, Resource
from fle.env.game import Direction
from fle.env.game.game_state import GameState
from fle.env.game.instance import AgentInstance, FactorioInstance


@pytest.fixture()
def game(instance: FactorioInstance):
    instance.reset()
    yield instance
    instance.reset()


def test_drop_box_chest(instance: AgentInstance):
    instance.agent_instances[0].get_system_prompt()
    instance.namespace.move_to(instance.namespace.nearest(Resource.IronOre))
    drill = instance.namespace.place_entity(
        Prototype.BurnerMiningDrill,
        Direction.UP,
        instance.namespace.nearest(Resource.IronOre),
    )
    instance.namespace.place_entity(
        Prototype.IronChest, Direction.UP, drill.drop_position
    )
    instance.namespace.insert_item(Prototype.Coal, drill, 10)

    instance.namespace.sleep(10)

    drill = instance.namespace.get_entities({Prototype.BurnerMiningDrill})[0]

    state = GameState.from_instance(instance)

    instance.reset(state)

    drill = instance.namespace.get_entities({Prototype.BurnerMiningDrill})[0]

    assert not drill.warnings


def test_full_chest(instance: FactorioInstance):
    instance.set_inventory({"burner-mining-drill": 1, "wooden-chest": 1, "coal": 2000})

    chest = instance.namespace.place_entity(Prototype.WoodenChest, Direction.UP)
    for i in range(16):
        instance.namespace.insert_item(Prototype.Coal, chest, 50)

    state = GameState.from_instance(instance)

    instance.reset(state)

    chest = instance.namespace.get_entities({Prototype.WoodenChest})[0]

    assert chest.warnings[0] == "chest is full"


if __name__ == "__main__":
    unittest.main()
