import pytest
from fle.env import Direction
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "solar-panel": 3,
        "small-electric-pole": 4,
        "burner-mining-drill": 1,
        "long-handed-inserter": 2,
        "filter-inserter": 2,
        "stack-inserter": 2,
        "wooden-chest": 2,
        "iron-chest": 4,
        "steel-chest": 4,
        "coal": 50,
        "iron-plate": 100,
        "copper-plate": 100,
        "electronic-circuit": 100,
    }
    instance.speed(10)
    instance.reset()
    yield instance.namespace


def test_drill_warnings(game):
    """Test long-handed inserter's ability to move items between chests"""
    game.move_to(game.nearest(Resource.IronOre))

    drill = game.place_entity(
        Prototype.BurnerMiningDrill,
        position=game.nearest(Resource.IronOre),
        direction=Direction.UP,
    )
    game.insert_item(Prototype.Coal, drill, 10)
    game.place_entity(
        Prototype.WoodenChest, position=drill.drop_position, direction=Direction.UP
    )
    game.sleep(5)

    drill = game.get_entities({Prototype.BurnerMiningDrill})[0]
    assert not drill.warnings
