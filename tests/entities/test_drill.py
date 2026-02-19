import pytest
from fle.env import Direction
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(configure_game):
    return configure_game(
        inventory={
            "solar-panel": 3,
            "small-electric-pole": 4,
            "burner-mining-drill": 1,
            "long-handed-inserter": 2,
            "fast-inserter": 2,
            "bulk-inserter": 2,
            "wooden-chest": 2,
            "iron-chest": 4,
            "steel-chest": 4,
            "coal": 50,
            "iron-plate": 100,
            "copper-plate": 100,
            "electronic-circuit": 100,
        },
        merge=True,
        reset_position=True,
    )


def test_drill_warnings(game):
    """Test that drill warnings are cleared when output is available"""
    game.move_to(game.nearest(Resource.IronOre))

    drill = game.place_entity(
        Prototype.BurnerMiningDrill,
        position=game.nearest(Resource.IronOre),
        direction=Direction.UP,
    )
    game.insert_item(Prototype.Coal, drill, 10)
    # Place chest at the drill's actual drop position (Factorio 2.0 compatible)
    _chest = game.place_entity(Prototype.IronChest, position=drill.drop_position)
    game.sleep(10)

    drill = game.get_entities({Prototype.BurnerMiningDrill})[0]
    assert not drill.warnings or "output blocked" not in str(drill.warnings)
