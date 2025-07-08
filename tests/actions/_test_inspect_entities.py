import pytest

from fle.env.entities import Position, Direction, Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "coal": 5,
        "iron-chest": 1,
        "iron-plate": 5,
        "iron-ore": 10,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_inspect_entities(game):
    inventory = game.inspect_inventory()
    coal_count = inventory[Prototype.Coal]
    assert coal_count != 0
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.Coal, chest, quantity=5)

    inspected = game.inspect_entities(
        radius=5, position=Position(x=chest.position.x, y=chest.position.y)
    )

    assert len(inspected.entities) == 2


def test_inspect_inserters(game):
    """Test to ensure that inspected inserters are facing in the correct direction"""

    game.place_entity(
        Prototype.BurnerInserter, Direction.RIGHT, position=Position(x=0, y=0)
    )

    entities = game.inspect_entities(radius=5)

    for entity in entities.entities:
        if entity.name == "burner-inserter":
            assert entity.direction == Direction.RIGHT.value


def test_inspect_burner_inventory(game):
    # Check initial inventory
    iron_position = game.nearest(Resource.Stone)
    game.move_to(iron_position)
    print(f"Moved to iron patch at {iron_position}")
    game.harvest_resource(iron_position, 20)

    game.craft_item(Prototype.StoneFurnace, 3)

    # 1. Place a stone furnace
    stone_furnace = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, iron_position
    )
    assert stone_furnace is not None, "Failed to place stone furnace"

    game.insert_item(Prototype.Coal, stone_furnace, 5)
    game.insert_item(Prototype.IronOre, stone_furnace, 5)

    inspection_result = game.inspect_entities()

    furnace = inspection_result.get_entities(Prototype.StoneFurnace)
    print(furnace)
