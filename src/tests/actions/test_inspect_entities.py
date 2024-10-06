import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        'coal': 5,
        'iron-chest': 1,
        'iron-plate': 5,
    }
    instance.reset()
    yield instance

def test_inspect_entities(game):
    inventory = game.inspect_inventory()
    coal_count = inventory[Prototype.Coal]
    assert coal_count != 0
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.Coal, chest, quantity=5)

    inspected = game.inspect_entities(radius=5, position=Position(x=chest.position.x, y=chest.position.y))

    assert len(inspected.entities) == 2
    game.reset()

def test_inspect_inserters(game):
    """Test to ensure that inspected inserters are facing in the correct direction"""

    inserter = game.place_entity(Prototype.BurnerInserter, Direction.RIGHT, position=Position(x=0, y=0))

    entities = game.inspect_entities(radius=5)

    for entity in entities.entities:
        if entity.name == 'burner-inserter':
            assert entity.direction == Direction.RIGHT.value
