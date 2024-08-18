import pytest

from factorio_instance import Direction
from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_rotate_entity(game):
    # Place a transport belt
    transport_belt = game.place_entity(Prototype.TransportBelt, position=(0, 0), direction=Direction.UP)

    # Rotate the transport belt right
    game.rotate_entity(transport_belt, direction=Direction.RIGHT)

    # Assert that the direction of the transport belt has been updated
    assert transport_belt.direction == Direction.RIGHT.value

    game.rotate_entity(transport_belt, direction=Direction.LEFT)

    assert transport_belt.direction == Direction.LEFT.value

    game.rotate_entity(transport_belt, direction=Direction.DOWN)

    assert transport_belt.direction == Direction.DOWN.value

    game.rotate_entity(transport_belt, direction=Direction.UP)

    assert transport_belt.direction == Direction.UP.value

    game.reset()